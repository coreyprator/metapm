"""
MetaPM Prompts API Router
Endpoints for CC prompt storage, retrieval, and approval.
PF5-MS2-SESSION-A (PTH: PF01A)
AP03 Amendment B: immediate Cloud Run Job trigger on PL approval.
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
import requests as _requests

from app.core.config import settings
from app.core.database import execute_query

logger = logging.getLogger(__name__)


async def trigger_cloud_run_job_immediate(job_name: str = "metapm-loop1-worker",
                                          pth: str = None, handoff_id: str = None,
                                          args_override: list = None):
    """Fire a Cloud Run Job immediately with optional targeted args (AP06).
    Uses GCP metadata server to get identity token, then calls Cloud Run Jobs API.
    Non-blocking — never delays the caller response.
    MM10B: records execution to job_executions table for PTH-aware Jobs panel.
    AP07: args_override allows passing arbitrary arg list (e.g. for loop3_processor).

    Args:
        job_name: Cloud Run Job name to execute.
        pth: If set, passes --pth=<pth> override to loop1_worker (targeted mode).
        handoff_id: If set, passes --handoff-id=<id> override to loop2_reviewer (targeted mode).
        args_override: If set, uses this list of args directly (overrides pth/handoff_id).
    """
    try:
        project = "super-flashcards-475210"
        # Get identity token from metadata server (available in Cloud Run)
        token_resp = _requests.get(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"},
            timeout=5
        )
        token = token_resp.json().get("access_token", "")
        if not token:
            logger.warning("[AP06] Could not obtain identity token — skipping immediate trigger")
            return

        run_url = (f"https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/"
                   f"namespaces/{project}/jobs/{job_name}:run")

        # AP06/AP07: build targeted override args if provided
        body = {}
        if args_override:
            body = {"overrides": {"containerOverrides": [{"args": args_override}]}}
            logger.info(f"[AP07] Triggering {job_name} | args: {args_override}")
        elif pth:
            body = {"overrides": {"containerOverrides": [{"args": [f"--pth={pth}"]}]}}
            logger.info(f"[AP06] Triggering {job_name} targeted | PTH: {pth}")
        elif handoff_id:
            body = {"overrides": {"containerOverrides": [{"args": [f"--handoff-id={handoff_id}"]}]}}
            logger.info(f"[AP06] Triggering {job_name} targeted | Handoff: {handoff_id}")
        else:
            logger.info(f"[AP06] Triggering {job_name} (fallback sweep)")

        resp = _requests.post(run_url,
                              headers={"Authorization": f"Bearer {token}",
                                       "Content-Type": "application/json"},
                              json=body if body else None,
                              timeout=10)
        if resp.status_code in (200, 201, 202):
            logger.info(f"[AP06] Cloud Run trigger fired for {job_name}")
            # MM10B: record to job_executions for PTH-aware Jobs panel
            try:
                exec_data = resp.json()
                exec_name = exec_data.get("metadata", {}).get("name", f"{job_name}-{uuid.uuid4().hex[:8]}")
                job_type = "loop1" if "loop1" in job_name else "loop2"
                execute_query(
                    """INSERT INTO job_executions (id, pth, job_type, handoff_id, status)
                       VALUES (?, ?, ?, ?, 'running')""",
                    (exec_name, pth, job_type, handoff_id), fetch="none"
                )
            except Exception as rec_err:
                logger.warning(f"[MM10B] job_executions record failed (non-fatal): {rec_err}")
        else:
            logger.warning(f"[AP06] Cloud Run trigger failed (non-fatal): {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"[AP06] Cloud Run trigger error (non-fatal): {e}")


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


def _has_localhost_urls(content_md: str) -> list:
    """Return list of localhost URLs found in test_cases URL fields (BA07)."""
    return re.findall(r'"url"\s*:\s*"(http://localhost[^"]*)"', content_md)


def _all_bv_urls_are_root(content_md: str) -> bool:
    """Return True if all test_case URL fields point to app root with no path (BA07)."""
    blocks = re.findall(r'```json\s*(\{.*?\})\s*```', content_md, re.DOTALL)
    for block in blocks:
        try:
            data = json.loads(block)
            cases = data.get('test_cases', [])
            if not cases:
                continue
            non_root = [c for c in cases if re.search(r'https?://[^/"\s]+/[^/"\s]+', c.get('url', ''))]
            if non_root:
                return False  # at least one has a path
            return True  # all are root-only or have no URL
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
    content_md = prompt.content_md or ""
    if bypass != "data_only_sprint" and not _has_uat_spec(content_md):
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

    # BA07: Check A — no localhost URLs in test_cases
    if bypass != "data_only_sprint":
        localhost_urls = _has_localhost_urls(content_md)
        if localhost_urls:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "prompt_localhost_urls",
                    "message": f"UAT spec test_cases must use production URLs, not localhost. Found: {localhost_urls[:3]}",
                    "fix": "Replace localhost URLs with the production service URL (e.g. https://metapm.rentyourcio.com)",
                }
            )

    # BA07: Check B — at least one BV URL must have a non-root path
    if bypass != "data_only_sprint" and _all_bv_urls_are_root(content_md):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "prompt_bv_urls_too_generic",
                "message": "All BV test_case URLs point to the app root. At least one must have a specific path (e.g. /prompts/MM07, /uat/UUID, /api/health).",
                "fix": "Update test_case URLs to point to specific pages or endpoints that verify the feature.",
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
    # Primary lookup: cc_prompts.handoff_id (set by create_handoff auto-complete)
    # Fallback: mcp_handoffs.pth column or metadata JSON
    row = execute_query("""
        SELECT TOP 1 h.id, h.task, h.project, h.version, h.created_at
        FROM mcp_handoffs h
        JOIN cc_prompts p ON p.handoff_id = h.id AND p.pth = ?
        ORDER BY h.created_at DESC
    """, (pth,), fetch="one")

    if not row:
        # Fallback: pth column or metadata LIKE
        row = execute_query("""
            SELECT TOP 1 id, task, project, version, created_at
            FROM mcp_handoffs
            WHERE pth = ? OR metadata LIKE ?
            ORDER BY created_at DESC
        """, (pth, f'%"prompt_pth":"{pth}"%'), fetch="one")

    if not row:
        raise HTTPException(status_code=404, detail=f"No handoff registered for PTH {pth}")

    handoff_id = str(row["id"])

    # Get most recent UAT spec for this PTH
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
                 'executing', 'complete', 'closed', 'rejected', 'cancelled')
        if patch.status not in valid:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid)}")
        set_parts.append("status = ?")
        params.append(patch.status)

        if patch.status == 'approved':
            set_parts.append("approved_at = GETDATE()")
            if patch.approved_by:
                set_parts.append("approved_by = ?")
                params.append(patch.approved_by)
            # AP06: fire Cloud Run Job immediately on PL approval (targeted mode with PTH)
            if patch.approved_by == "PL":
                pth_row = execute_query("SELECT pth FROM cc_prompts WHERE id = ?",
                                        (prompt_id,), fetch="one")
                pth_val = pth_row.get("pth") if pth_row else None
                asyncio.create_task(
                    trigger_cloud_run_job_immediate("metapm-loop1-worker", pth=pth_val)
                )

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


# ── MM10B: Cancel prompt by PTH ──────────────────────────────────────────────

@router.patch("/{pth}/cancel")
async def cancel_prompt(pth: str, _: bool = Depends(verify_api_key)):
    """MM10B: Mark a prompt as cancelled by PTH. Removes it from Active Prompts panel."""
    row = execute_query("SELECT id, pth, status FROM cc_prompts WHERE pth = ?", (pth,), fetch="one")
    if not row:
        raise HTTPException(status_code=404, detail=f"Prompt with PTH '{pth}' not found")
    execute_query(
        "UPDATE cc_prompts SET status='cancelled', updated_at=GETUTCDATE() WHERE pth=?",
        (pth,), fetch="none"
    )
    logger.info(f"[MM10B] Prompt {pth} cancelled")
    return {"pth": pth, "status": "cancelled"}


# ── AP06: Jobs Status API ──

@router.get("/jobs/status")
async def get_jobs_status():
    """AP06: Query Cloud Run Jobs API for recent executions of both loop workers.
    MM10B: enriches with PTH from job_executions table, filters to last 24h.
    """
    from datetime import timezone
    project = "super-flashcards-475210"
    jobs = ["metapm-loop1-worker", "metapm-loop2-reviewer"]
    result = {}

    # MM10B: load job_executions PTH lookup
    pth_by_exec = {}
    try:
        rows = execute_query(
            "SELECT id, pth FROM job_executions WHERE started_at >= DATEADD(hour, -24, GETUTCDATE())",
            fetch="all"
        ) or []
        for r in rows:
            if r.get("id") and r.get("pth"):
                pth_by_exec[r["id"]] = r["pth"]
    except Exception:
        pass  # non-fatal — job_executions may not exist yet

    try:
        token_resp = _requests.get(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"},
            timeout=5
        )
        token = token_resp.json().get("access_token", "")
    except Exception as e:
        return {"error": f"Could not obtain identity token: {e}", "loop1": [], "loop2": []}

    cutoff_24h = datetime.now(timezone.utc).replace(microsecond=0)
    for job_name in jobs:
        key = "loop1" if "loop1" in job_name else "loop2"
        try:
            list_url = (f"https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/"
                        f"namespaces/{project}/executions")
            resp = _requests.get(
                list_url,
                params={"labelSelector": f"run.googleapis.com/job={job_name}", "limit": "10"},
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                filtered = []
                for item in items:
                    exec_name = item.get("metadata", {}).get("name", "")
                    started_str = item.get("metadata", {}).get("creationTimestamp", "")
                    status = _parse_execution_status(item)
                    # MM10B: filter to last 24h
                    if started_str:
                        try:
                            from dateutil.parser import parse as parse_dt
                            started_dt = parse_dt(started_str)
                            if started_dt.tzinfo is None:
                                started_dt = started_dt.replace(tzinfo=timezone.utc)
                            age_hours = (cutoff_24h - started_dt).total_seconds() / 3600
                            if age_hours > 24:
                                continue
                            # MM10B: hide succeeded loop1 older than 2h
                            if key == "loop1" and status == "succeeded" and age_hours > 2:
                                continue
                        except Exception:
                            pass
                    # MM10B: look up PTH from job_executions
                    pth = pth_by_exec.get(exec_name)
                    filtered.append({
                        "name": exec_name,
                        "job": job_name,
                        "status": status,
                        "started": started_str,
                        "pth": pth,
                    })
                result[key] = filtered
            else:
                result[key] = []
        except Exception as e:
            result[key] = []
            logger.warning(f"[AP06] jobs/status error for {job_name}: {e}")

    return result


def _parse_execution_status(execution: dict) -> str:
    conditions = execution.get("status", {}).get("conditions", [])
    for c in conditions:
        if c.get("type") == "Completed":
            return "succeeded" if c.get("status") == "True" else "running"
        if c.get("type") == "Failed" and c.get("status") == "True":
            return "failed"
    return "running"


@router.post("/jobs/launch")
async def launch_job(payload: dict):
    """AP06: Manually launch Loop 1 for a specific PTH (dashboard Launch button)."""
    pth = payload.get("pth")
    if not pth:
        raise HTTPException(status_code=400, detail="pth required")
    await trigger_cloud_run_job_immediate("metapm-loop1-worker", pth=pth)
    return {"launched": True, "pth": pth}
