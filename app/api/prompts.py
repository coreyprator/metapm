"""
MetaPM Prompts API Router
Endpoints for CC prompt storage, retrieval, and approval.
PF5-MS2-SESSION-A (PTH: PF01A)
"""

import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
import httpx

from app.core.config import settings
from app.core.database import execute_query

logger = logging.getLogger(__name__)


async def notify_pa(event_type: str, data: dict):
    """Fire-and-forget webhook to Personal Assistant."""
    pa_url = os.getenv("PA_WEBHOOK_URL",
        "https://personal-assistant-57478301787.us-central1.run.app/api/webhook/handoff")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(pa_url, json={
                "pth": data.get("pth", ""),
                "project": data.get("project", "MetaPM"),
                "title": f"{event_type}: {data.get('sprint', data.get('pth', ''))}",
                "description": data.get("description", ""),
                "handoff_url": data.get("handoff_url", ""),
                "uat_url": data.get("uat_url", ""),
                "handoff_id": data.get("handoff_id", ""),  # MP-EMAIL-COMPLETE
                "secret": os.getenv("PA_WEBHOOK_SECRET", "")
            }, headers={"Content-Type": "application/json"})
            logger.info(f"PA notified: {event_type}")
    except Exception as e:
        logger.warning(f"PA notification failed (non-fatal): {e}")

router = APIRouter()

# API Key auth (reuse pattern from mcp.py)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(x_api_key: Optional[str] = Depends(api_key_header)) -> bool:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    expected = settings.MCP_API_KEY or settings.API_KEY
    if not expected:
        raise HTTPException(status_code=503, detail="API key not configured")
    if x_api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True


# ── MP-CAI-OUTBOUND-GATE (MM06): UAT spec presence check ─────────────────────

def _has_uat_spec(content_md: str) -> bool:
    """Return True if content_md contains a ```json block with a test_cases array."""
    blocks = re.findall(r'```json\s*(\{.*?\})\s*```', content_md, re.DOTALL)
    for block in blocks:
        try:
            data = json.loads(block)
            if isinstance(data.get('test_cases'), list) and len(data['test_cases']) > 0:
                return True
        except Exception:
            continue
    return False


# Schemas
class PromptCreate(BaseModel):
    requirement_id: Optional[str] = None
    sprint_id: str
    pth: str = Field(..., max_length=10)
    content_md: str
    project_id: Optional[str] = None
    estimated_hours: Optional[float] = None
    created_by: str = "CAI"
    enforcement_bypass: Optional[str] = None  # "data_only_sprint" skips UAT spec gate


class PromptPatch(BaseModel):
    status: Optional[str] = None
    approved_by: Optional[str] = None
    content_md: Optional[str] = None


class PromptResponse(BaseModel):
    id: int
    sprint_id: str
    project_id: Optional[str] = None
    pth: Optional[str] = None
    requirement_id: Optional[str] = None
    content_md: Optional[str] = None
    content: Optional[str] = None
    status: str
    estimated_hours: Optional[float] = None
    created_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    handoff_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    url: Optional[str] = None
    project_name: Optional[str] = None
    project_emoji: Optional[str] = None


def _row_to_response(row: dict) -> dict:
    """Convert a DB row to a PromptResponse dict."""
    return {
        "id": row["id"],
        "sprint_id": row.get("sprint_id", ""),
        "project_id": row.get("project_id"),
        "pth": row.get("pth"),
        "requirement_id": row.get("requirement_id"),
        "content_md": row.get("content_md"),
        "content": row.get("content"),
        "status": row.get("status", "draft"),
        "estimated_hours": float(row["estimated_hours"]) if row.get("estimated_hours") else None,
        "created_by": row.get("created_by"),
        "approved_by": row.get("approved_by"),
        "approved_at": str(row["approved_at"]) if row.get("approved_at") else None,
        "handoff_id": row.get("handoff_id"),
        "created_at": str(row["created_at"]) if row.get("created_at") else None,
        "updated_at": str(row["updated_at"]) if row.get("updated_at") else None,
        "url": f"https://metapm.rentyourcio.com/prompts/{row['pth']}" if row.get("pth") else None,
        "project_name": row.get("project_name"),
        "project_emoji": row.get("project_emoji"),
    }


@router.post("", status_code=201)
async def create_prompt(prompt: PromptCreate, _: bool = Depends(verify_api_key)):
    """Create a new CC prompt."""
    # MP-CAI-OUTBOUND-GATE: require UAT spec JSON block in content_md
    bypass = (prompt.enforcement_bypass or "").strip().lower()
    if bypass != "data_only_sprint" and not _has_uat_spec(prompt.content_md or ""):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "prompt_missing_uat_spec",
                "message": (
                    "content_md must include a UAT spec JSON block with a test_cases array "
                    "containing at least 1 BV item. CAI compliance requires UAT specs in every "
                    "prompt (BOOT-1.5.10)."
                ),
                "fix": "Add a ```json {..., \"test_cases\": [{...}]} ``` block to the prompt content.",
            }
        )

    # Default project_id to MetaPM if not provided
    project_id = prompt.project_id or "proj-mp"

    result = execute_query("""
        INSERT INTO cc_prompts
            (sprint_id, project_id, pth, requirement_id, content, content_md,
             estimated_hours, created_by, status)
        OUTPUT INSERTED.id, INSERTED.sprint_id, INSERTED.project_id, INSERTED.pth,
               INSERTED.requirement_id, INSERTED.content_md, INSERTED.status,
               INSERTED.estimated_hours, INSERTED.created_by, INSERTED.created_at
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft')
    """, (
        prompt.sprint_id,
        project_id,
        prompt.pth,
        prompt.requirement_id,
        prompt.content_md[:500] if prompt.content_md else '',
        prompt.content_md,
        prompt.estimated_hours,
        prompt.created_by,
    ), fetch="one")

    if not result:
        raise HTTPException(status_code=500, detail="Failed to create prompt")

    # Fire-and-forget PA notification
    asyncio.create_task(notify_pa("Prompt created", {
        "pth": result.get("pth", ""),
        "project": "MetaPM",
        "sprint": result.get("sprint_id", ""),
        "description": f"New prompt {result.get('pth')} ready for review",
        "handoff_url": f"https://metapm.rentyourcio.com/prompts/{result.get('pth', '')}",
    }))

    return {
        "id": result["id"],
        "pth": result.get("pth"),
        "sprint_id": result.get("sprint_id"),
        "status": result.get("status", "draft"),
        "created_at": str(result["created_at"]) if result.get("created_at") else None,
        "url": f"https://metapm.rentyourcio.com/prompts/{result['pth']}" if result.get("pth") else None,
    }


@router.get("/{pth}")
async def get_prompt_by_pth(pth: str):
    """Get a prompt by PTH code (public read)."""
    row = execute_query("""
        SELECT p.*, proj.name as project_name, proj.emoji as project_emoji
        FROM cc_prompts p
        LEFT JOIN roadmap_projects proj ON p.project_id = proj.id
        WHERE p.pth = ?
        ORDER BY p.created_at DESC
    """, (pth,), fetch="one")

    if not row:
        raise HTTPException(status_code=404, detail=f"Prompt with PTH '{pth}' not found")

    resp = _row_to_response(row)

    # Artifact chain: find linked handoff via prompt_pth on mcp_handoffs
    try:
        handoff = execute_query("""
            SELECT TOP 1 h.id, r.id as review_id, r.assessment
            FROM mcp_handoffs h
            LEFT JOIN reviews r ON r.handoff_id = h.id
            WHERE h.metadata LIKE ?
            ORDER BY h.created_at DESC
        """, (f'%"prompt_pth":"{pth}"%',), fetch="one")
    except Exception:
        handoff = None

    if handoff:
        resp["handoff_id"] = str(handoff["id"])
        resp["handoff_url"] = f"https://metapm.rentyourcio.com/mcp/handoffs/{handoff['id']}/content"
        resp["review_id"] = str(handoff["review_id"]) if handoff.get("review_id") else None
        resp["review_assessment"] = handoff.get("assessment")
    else:
        resp["handoff_id"] = None
        resp["handoff_url"] = None
        resp["review_id"] = None
        resp["review_assessment"] = None

    # Find linked UAT page
    try:
        uat = execute_query("""
            SELECT TOP 1 id FROM uat_pages WHERE pth = ? ORDER BY created_at DESC
        """, (pth,), fetch="one")
        resp["uat_url"] = f"https://metapm.rentyourcio.com/uat/{uat['id']}" if uat else None
    except Exception:
        resp["uat_url"] = None

    return resp


@router.get("/{pth}/handoff")
async def get_handoff_by_pth(pth: str):
    """MP-GET-HO-BY-PTH: Return most recent handoff registered for a PTH code.
    CAI calls this to get handoff_id + UAT URL without asking PL for UUIDs."""
    # Look up by pth column on mcp_handoffs (set by create_handoff when prompt_pth is provided),
    # OR by metadata JSON match as fallback
    row = execute_query("""
        SELECT TOP 1 h.id, h.task, h.project, h.version, h.created_at,
               u.id as uat_spec_id, u.id as uat_page_id
        FROM mcp_handoffs h
        LEFT JOIN uat_pages u ON u.pth = ? AND u.spec_source = 'cc_spec'
        WHERE h.pth = ? OR h.metadata LIKE ?
        ORDER BY h.created_at DESC
    """, (pth, pth, f'%"prompt_pth":"{pth}"%'), fetch="one")

    if not row:
        raise HTTPException(status_code=404, detail=f"No handoff registered for PTH {pth}")

    handoff_id = str(row["id"])
    uat_spec_id = str(row["uat_spec_id"]) if row.get("uat_spec_id") else None

    # Get the most recent spec uat_url separately if not found via join
    if not uat_spec_id:
        uat_row = execute_query(
            "SELECT TOP 1 id FROM uat_pages WHERE pth = ? ORDER BY created_at DESC",
            (pth,), fetch="one"
        )
        uat_spec_id = str(uat_row["id"]) if uat_row else None

    return {
        "pth": pth,
        "handoff_id": handoff_id,
        "uat_url": f"https://metapm.rentyourcio.com/uat/{uat_spec_id}" if uat_spec_id else None,
        "uat_spec_id": uat_spec_id,
        "sprint": row.get("task", ""),
        "version": row.get("version", ""),
        "project": row.get("project", ""),
        "registered_at": str(row["created_at"]) if row.get("created_at") else None,
    }


@router.get("")
async def list_prompts(
    status: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """List prompts with optional filters (public read)."""
    where_parts = []
    params = []

    if status:
        where_parts.append("p.status = ?")
        params.append(status)
    if project:
        where_parts.append("(proj.code = ? OR proj.name = ? OR p.project_id = ?)")
        params.extend([project, project, project])

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    params.append(limit)

    rows = execute_query(f"""
        SELECT TOP (?) p.*, proj.name as project_name, proj.emoji as project_emoji
        FROM cc_prompts p
        LEFT JOIN roadmap_projects proj ON p.project_id = proj.id
        {where_clause}
        ORDER BY p.created_at DESC
    """, (*params[-1:], *params[:-1]), fetch="all") or []

    # SQL Server TOP needs to be first param
    return [_row_to_response(r) for r in rows]


@router.patch("/{prompt_id}")
async def update_prompt(prompt_id: int, patch: PromptPatch):
    """Update prompt status (approve/reject/execute/complete). No auth required for PL browser approval."""
    set_parts = []
    params = []

    if patch.status:
        valid = ('draft', 'prompt_ready', 'approved', 'sent', 'completed',
                 'executing', 'complete', 'closed', 'rejected')
        if patch.status not in valid:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid)}")
        set_parts.append("status = ?")
        params.append(patch.status)

        if patch.status == 'approved':
            set_parts.append("approved_at = GETDATE()")
            if patch.approved_by:
                set_parts.append("approved_by = ?")
                params.append(patch.approved_by)

    if patch.approved_by and patch.status != 'approved':
        set_parts.append("approved_by = ?")
        params.append(patch.approved_by)

    if patch.content_md is not None:
        # Only allow content edits on draft prompts
        current = execute_query("SELECT status FROM cc_prompts WHERE id = ?", (prompt_id,), fetch="one")
        if current and current['status'] not in ('draft', 'prompt_ready'):
            raise HTTPException(status_code=400, detail="Content can only be edited when prompt is in draft status")
        set_parts.append("content_md = ?")
        params.append(patch.content_md)
        set_parts.append("content = ?")
        params.append(patch.content_md[:500] if patch.content_md else '')

    if not set_parts:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_parts.append("updated_at = GETDATE()")
    params.append(prompt_id)

    execute_query(f"""
        UPDATE cc_prompts SET {', '.join(set_parts)} WHERE id = ?
    """, tuple(params), fetch="none")

    row = execute_query("""
        SELECT p.*, proj.name as project_name, proj.emoji as project_emoji
        FROM cc_prompts p
        LEFT JOIN roadmap_projects proj ON p.project_id = proj.id
        WHERE p.id = ?
    """, (prompt_id,), fetch="one")

    if not row:
        raise HTTPException(status_code=404, detail="Prompt not found")

    return _row_to_response(row)
