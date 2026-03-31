"""
MetaPM MCP Tools — JSON-RPC 2.0 endpoint for Claude.ai integration.
Exposes MetaPM operations as MCP tools so CAI can interact without PL terminal.
Sprint: MP09-MEGA-001 (PTH: MP09)

Implements MCP protocol (tools/list + tools/call) without the mcp library
to avoid starlette version conflicts with FastAPI 0.109.
"""

import hashlib
import json
import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.core.database import execute_query

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Tool definitions (MCP tools/list schema) ──

TOOLS = [
    {
        "name": "post_prompt",
        "description": "Create a new CC sprint prompt in MetaPM. CAI calls this to post the full prompt content. Returns the prompt URL for PL to review and approve.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pth": {"type": "string", "description": "Prompt tracking hash (e.g. 'E2E02')"},
                "sprint_id": {"type": "string", "description": "Sprint identifier (e.g. 'MP09-MEGA-001')"},
                "project_id": {"type": "string", "description": "Project short code (e.g. 'proj-mp')"},
                "content_md": {"type": "string", "description": "Full markdown prompt content"},
                "estimated_hours": {"type": "number", "description": "Estimated hours (default 1.0)", "default": 1.0},
            },
            "required": ["pth", "sprint_id", "project_id", "content_md"],
        },
    },
    {
        "name": "get_prompt",
        "description": "Get a prompt by PTH code. Returns status, content length, and approval info.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pth": {"type": "string", "description": "Prompt tracking hash to look up"},
            },
            "required": ["pth"],
        },
    },
    {
        "name": "post_review",
        "description": "Post CAI's structured review of a handoff. assessment: 'pass', 'conditional_pass', or 'fail'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "handoff_id": {"type": "string", "description": "UUID of the handoff to review"},
                "pth": {"type": "string", "description": "PTH code linking review to sprint"},
                "assessment": {"type": "string", "enum": ["pass", "conditional_pass", "fail"]},
                "notes": {"type": "string", "description": "Free-text review notes"},
                "lesson_candidates": {"type": "string", "description": "JSON array of {lesson, target, severity}", "default": "[]"},
            },
            "required": ["handoff_id", "pth", "assessment", "notes"],
        },
    },
    {
        "name": "get_uat_results",
        "description": "Get submitted UAT results by spec_id. Returns BV items with pass/fail/pending status and notes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spec_id": {"type": "string", "description": "UUID of the UAT spec page"},
            },
            "required": ["spec_id"],
        },
    },
    {
        "name": "trigger_rag_sync",
        "description": "Trigger a full MetaPM requirements sync to Portfolio RAG. CAI calls this after UAT submits or sprint closes to get current data in RAG.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "list_requirements",
        "description": "List requirements filtered by status and/or project. Returns code, title, status, pth, priority.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter by status (e.g. 'cc_executing', 'uat_ready'). Empty = all.", "default": ""},
                "project_code": {"type": "string", "description": "Filter by project code (e.g. 'MP', 'SF'). Empty = all.", "default": ""},
                "limit": {"type": "integer", "description": "Max results (default 20, max 100)", "default": 20},
            },
        },
    },
    {
        "name": "patch_requirement_status",
        "description": "Advance a requirement to a new status. Use to close a requirement after UAT passes. Provide pth or project_code to disambiguate when multiple requirements share the same code.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Requirement code (e.g. 'MP-064' or 'REQ-001')"},
                "status": {"type": "string", "description": "Target status (e.g. 'uat_ready', 'done', 'closed')"},
                "note": {"type": "string", "description": "Optional note", "default": ""},
                "pth": {"type": "string", "description": "Optional PTH discriminator (e.g. '91C1'). When provided, filters to the specific requirement matching both code and pth.", "default": ""},
                "project_code": {"type": "string", "description": "Optional project code discriminator (e.g. 'AF', 'MP', 'SF'). When provided, filters to the specific requirement in that project.", "default": ""},
            },
            "required": ["code", "status"],
        },
    },
    {
        "name": "get_compliance_doc",
        "description": "Retrieve a compliance document from the MetaPM compliance_docs table. Use doc_id values like 'bootstrap', 'pk-metapm', 'pk-sf', 'cai-outbound', 'cai-inbound'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "doc_id": {"type": "string", "description": "Document ID (e.g. 'bootstrap', 'pk-metapm', 'cai-outbound')"},
            },
            "required": ["doc_id"],
        },
    },
    {
        "name": "update_compliance_doc",
        "description": "Upsert a compliance document in the MetaPM compliance_docs table. Creates if not exists, updates if exists.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "doc_id": {"type": "string", "description": "Document ID to upsert (e.g. 'bootstrap', 'pk-metapm')"},
                "content_md": {"type": "string", "description": "New markdown content"},
                "version": {"type": "string", "description": "New version string (e.g. 'BOOT-1.5.19-BA08')"},
                "checkpoint": {"type": "string", "description": "New checkpoint code"},
                "doc_type": {"type": "string", "description": "Document type: 'bootstrap', 'pk', or 'cai_standard'", "default": "unknown"},
                "project_code": {"type": "string", "description": "Project code if applicable (e.g. 'proj-mp'), null for cross-project docs"},
                "updated_by": {"type": "string", "description": "Who made the update (e.g. 'PL', 'CC', 'CAI')", "default": "CC"},
            },
            "required": ["doc_id", "content_md", "version", "checkpoint"],
        },
    },
    {
        "name": "get_checkpoint",
        "description": "Get the checkpoint and version for a compliance document without fetching full content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "doc_id": {"type": "string", "description": "Document ID (e.g. 'bootstrap')"},
            },
            "required": ["doc_id"],
        },
    },
    {
        "name": "reject_prompt",
        "description": "Mark a draft CC prompt as rejected/superseded. Use when CAI has posted a better version or the sprint scope changed. Removes from PL approval queue.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pth": {"type": "string", "description": "Prompt tracking hash to reject (e.g. 'W9A3')"},
                "reason": {"type": "string", "description": "Why it is being rejected (e.g. 'superseded by W9A3B — scope corrected')"},
            },
            "required": ["pth", "reason"],
        },
    },
    {
        "name": "list_projects",
        "description": "List all portfolio projects. Returns project UUID, code, and name. Use the 'id' field as project_id when calling post_prompt.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "post_uat_spec",
        "description": "Post a UAT spec with BVs to MetaPM. CAI calls this at prompt-creation time. Returns spec_id and uat_url. CC never writes a UAT spec — CAI creates it here.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pth": {"type": "string", "description": "Prompt tracking hash (e.g. 'HM24')"},
                "sprint_id": {"type": "string", "description": "Sprint identifier (e.g. 'HM24-ACCEPT-DELEGATION-FIX-001')"},
                "project_code": {"type": "string", "description": "Project short code e.g. 'HL', 'AF', 'SF', 'MP'"},
                "version": {"type": "string", "description": "Version string e.g. '2.28.0 to 2.29.0'"},
                "test_cases": {
                    "type": "array",
                    "description": "Array of BV objects",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "type": {"type": "string", "default": "pl_visual"},
                            "expected": {"type": "string"},
                        },
                        "required": ["id", "title", "expected"],
                    },
                },
            },
            "required": ["pth", "sprint_id", "project_code", "version", "test_cases"],
        },
    },
    {
        "name": "post_requirement",
        "description": "Create a new requirement in MetaPM. CAI calls this to seed backlog items directly from conversation without PL having to use the UI. Auto-generates the next sequential code for the project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_code": {"type": "string", "description": "Project short code (e.g. 'MP', 'AF', 'SF', 'EM', 'HL', 'EFG')"},
                "title": {"type": "string", "description": "Requirement title"},
                "description": {"type": "string", "description": "Optional longer description", "default": ""},
                "priority": {"type": "string", "description": "P1, P2, or P3 (default P2)", "enum": ["P1", "P2", "P3"], "default": "P2"},
                "type": {"type": "string", "description": "Requirement type", "enum": ["feature", "bug", "task", "enhancement", "vision"], "default": "feature"},
                "sprint_id": {"type": "string", "description": "Optional sprint assignment", "default": ""},
            },
            "required": ["project_code", "title"],
        },
    },
    {
        "name": "create_handoff_shell",
        "description": "Pre-create a handoff shell UUID that CC will fill in at closeout. CAI calls this at prompt-creation time alongside post_uat_spec. Returns handoff_id and patch_url for CC to use.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pth": {"type": "string", "description": "Prompt tracking hash (e.g. 'HM24')"},
                "sprint_id": {"type": "string", "description": "Sprint identifier"},
                "project_code": {"type": "string", "description": "Project short code e.g. 'HL', 'AF', 'SF', 'MP'"},
                "uat_spec_id": {"type": "string", "description": "UUID of UAT spec created by post_uat_spec (optional, pre-fills shell)", "default": ""},
            },
            "required": ["pth", "sprint_id", "project_code"],
        },
    },
]


# ── Tool implementations ──

def _tool_post_prompt(args: dict) -> dict:
    pth = args["pth"]
    sprint_id = args["sprint_id"]
    project_id = args["project_id"]
    content_md = args["content_md"]
    estimated_hours = args.get("estimated_hours", 1.0)

    result = execute_query("""
        INSERT INTO cc_prompts
            (sprint_id, project_id, pth, content, content_md,
             estimated_hours, created_by, status)
        OUTPUT INSERTED.id, INSERTED.pth, INSERTED.sprint_id, INSERTED.status,
               INSERTED.created_at
        VALUES (?, ?, ?, ?, ?, ?, 'CAI', 'draft')
    """, (
        sprint_id, project_id, pth,
        content_md[:500] if content_md else '',
        content_md, estimated_hours,
    ), fetch="one")

    if not result:
        return {"error": "Failed to create prompt"}

    return {
        "id": result["id"],
        "pth": result.get("pth"),
        "sprint_id": result.get("sprint_id"),
        "status": "draft",
        "url": f"https://metapm.rentyourcio.com/prompts/{result['pth']}",
        "created_at": str(result["created_at"]) if result.get("created_at") else None,
    }


def _tool_get_prompt(args: dict) -> dict:
    pth = args["pth"]
    row = execute_query("""
        SELECT id, sprint_id, project_id, pth, status,
               LEN(content_md) as content_length,
               created_by, approved_by, approved_at, created_at
        FROM cc_prompts WHERE pth = ?
    """, (pth,), fetch="one")

    if not row:
        return {"error": f"Prompt '{pth}' not found"}

    return {
        "id": row["id"],
        "pth": row["pth"],
        "sprint_id": row.get("sprint_id"),
        "project_id": row.get("project_id"),
        "status": row.get("status"),
        "content_length": row.get("content_length"),
        "created_by": row.get("created_by"),
        "approved_by": row.get("approved_by"),
        "approved_at": str(row["approved_at"]) if row.get("approved_at") else None,
        "created_at": str(row["created_at"]) if row.get("created_at") else None,
        "url": f"https://metapm.rentyourcio.com/prompts/{row['pth']}",
    }


def _tool_post_review(args: dict) -> dict:
    handoff_id = args["handoff_id"]
    pth = args["pth"]
    assessment = args["assessment"]
    notes = args["notes"]
    lesson_candidates = args.get("lesson_candidates", "[]")

    if assessment not in ('pass', 'conditional_pass', 'fail'):
        return {"error": f"Invalid assessment '{assessment}'"}

    # BA17 fix: try handoff_shells first (BA17 flow), fall back to mcp_handoffs (pre-BA17)
    handoff = execute_query(
        "SELECT id FROM handoff_shells WHERE id = ?",
        (handoff_id,), fetch="one"
    )
    if not handoff:
        handoff = execute_query(
            "SELECT id FROM mcp_handoffs WHERE id = ?",
            (handoff_id,), fetch="one"
        )
    if not handoff:
        return {"error": f"Handoff {handoff_id} not found"}

    lc_parsed = json.loads(lesson_candidates) if lesson_candidates else []
    lc_json = json.dumps(lc_parsed) if lc_parsed else None

    result = execute_query("""
        INSERT INTO reviews (handoff_id, prompt_pth, assessment, lesson_candidates, notes)
        OUTPUT INSERTED.id, INSERTED.handoff_id, INSERTED.assessment, INSERTED.created_at
        VALUES (?, ?, ?, ?, ?)
    """, (handoff_id, pth, assessment, lc_json, notes), fetch="one")

    if not result:
        return {"error": "Failed to create review"}

    return {
        "id": str(result["id"]),
        "handoff_id": result.get("handoff_id"),
        "assessment": result.get("assessment"),
        "created_at": str(result["created_at"]) if result.get("created_at") else None,
    }


def _tool_get_uat_results(args: dict) -> dict:
    spec_id = args["spec_id"]
    page = execute_query(
        "SELECT id, project, sprint_code, version, status, pth FROM uat_pages WHERE id = ?",
        (spec_id,), fetch="one"
    )
    if not page:
        return {"error": f"UAT spec {spec_id} not found"}

    items = execute_query(
        "SELECT id, title, status, notes FROM uat_bv_items WHERE spec_id = ? ORDER BY bv_id",
        (spec_id,), fetch="all"
    ) or []

    return {
        "spec_id": spec_id,
        "project": page.get("project"),
        "sprint": page.get("sprint_code"),
        "version": page.get("version"),
        "status": page.get("status"),
        "pth": page.get("pth"),
        "test_cases": [
            {"id": item["id"], "title": item.get("title", ""), "status": item.get("status", "pending"), "notes": item.get("notes", "")}
            for item in items
        ],
        "url": f"https://metapm.rentyourcio.com/uat/{spec_id}",
    }


def _tool_trigger_rag_sync(args: dict) -> dict:
    import httpx
    import os
    mcp_key = os.getenv("MCP_API_KEY", "")
    if not mcp_key:
        return {"status": "error", "message": "MCP_API_KEY not set on server"}
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                "https://metapm.rentyourcio.com/api/rag/sync",
                headers={"X-API-Key": mcp_key}
            )
            resp.raise_for_status()
            result = resp.json()
            return {
                "tool": "trigger_rag_sync",
                "status": "success",
                "synced_count": result.get("synced", result.get("count", "unknown")),
                "message": "Portfolio RAG metapm collection updated",
            }
    except Exception as e:
        return {"tool": "trigger_rag_sync", "status": "error", "message": str(e)}


def _tool_list_requirements(args: dict) -> dict:
    status = args.get("status", "")
    project_code = args.get("project_code", "")
    limit = min(args.get("limit", 20), 100)

    where = []
    params = []
    if status:
        where.append("r.status = ?")
        params.append(status)
    if project_code:
        where.append("p.code = ?")
        params.append(project_code)

    where_sql = " AND ".join(where) if where else "1=1"
    params.append(limit)

    rows = execute_query(f"""
        SELECT r.code, r.title, r.status, r.pth, r.priority, r.type,
               p.code as project_code, p.name as project_name
        FROM roadmap_requirements r
        JOIN roadmap_projects p ON r.project_id = p.id
        WHERE {where_sql}
        ORDER BY r.updated_at DESC
        OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
    """, tuple(params), fetch="all") or []

    return {
        "count": len(rows),
        "requirements": [
            {k: r.get(k) for k in ("code", "title", "status", "pth", "priority", "type", "project_code", "project_name")}
            for r in rows
        ],
    }


def _tool_reject_prompt(args: dict) -> dict:
    pth = args["pth"]
    reason = args.get("reason", "")
    row = execute_query(
        "SELECT id, pth, status FROM cc_prompts WHERE pth = ?", (pth,), fetch="one"
    )
    if not row:
        return {"error": f"Prompt '{pth}' not found"}
    current = row.get("status", "")
    if current not in ("draft", "prompt_ready"):
        return {"error": f"Cannot reject prompt in status '{current}'. Must be draft or prompt_ready."}
    execute_query(
        "UPDATE cc_prompts SET status='rejected', rejection_reason=?, updated_at=GETUTCDATE() WHERE pth=?",
        (reason[:500] if reason else None, pth), fetch="none"
    )
    return {
        "pth": pth,
        "status": "rejected",
        "reason": reason,
        "message": f"Prompt {pth} rejected and removed from PL approval queue.",
    }


def _tool_list_projects(args: dict) -> dict:
    rows = execute_query("""
        SELECT id, code, name, deploy_url
        FROM roadmap_projects
        ORDER BY code
    """, fetch="all") or []

    return {
        "count": len(rows),
        "projects": [
            {
                "project_id_for_post_prompt": str(r["id"]),
                "code": r.get("code"),
                "name": r.get("name"),
                "deploy_url": r.get("deploy_url") or "",
            }
            for r in rows
        ],
    }


def _tool_patch_requirement_status(args: dict) -> dict:
    code = args["code"]
    status = args["status"]
    note = args.get("note", "")
    pth = args.get("pth", "")
    project_code = args.get("project_code", "")

    if pth:
        req = execute_query(
            "SELECT id, status FROM roadmap_requirements WHERE code = ? AND pth = ?",
            (code, pth), fetch="one"
        )
        if not req:
            return {"error": f"Requirement '{code}' with pth '{pth}' not found"}
    elif project_code:
        req = execute_query(
            "SELECT id, status FROM roadmap_requirements WHERE code = ? AND project_code = ?",
            (code, project_code), fetch="one"
        )
        if not req:
            return {"error": f"Requirement '{code}' in project '{project_code}' not found"}
    else:
        req = execute_query(
            "SELECT id, status FROM roadmap_requirements WHERE code = ?",
            (code,), fetch="one"
        )
        if not req:
            return {"error": f"Requirement '{code}' not found"}

    req_id = req["id"]
    current = req["status"]

    # BA17 Closeout gate: block cc_complete if handoff shell exists for this PTH and is incomplete
    if status == "cc_complete" and pth:
        shell = execute_query(
            "SELECT id, version_from, version_to, commit_hash, deploy_url, machine_tests, deviations FROM handoff_shells WHERE pth = ?",
            (pth,), fetch="one"
        )
        if shell:
            missing = []
            for field in ["version_from", "version_to", "commit_hash", "deploy_url", "machine_tests", "deviations"]:
                val = shell.get(field)
                if not val or (isinstance(val, str) and not val.strip()):
                    missing.append(field)
            if missing:
                shell_id = str(shell["id"])
                patch_url = f"https://metapm.rentyourcio.com/mcp/handoffs/{shell_id}"
                return {
                    "error": f"Handoff incomplete — missing fields: {', '.join(missing)}. Fill via PATCH {patch_url} before advancing to cc_complete.",
                    "handoff_shell_id": shell_id,
                    "missing_fields": missing,
                }

    execute_query(
        "UPDATE roadmap_requirements SET status = ?, updated_at = GETDATE() WHERE id = ?",
        (status, req_id), fetch="none"
    )

    checkpoint = hashlib.sha256(f"{req_id}:{status}".encode()).hexdigest()[:4].upper()
    return {"code": code, "previous_status": current, "status": status, "checkpoint": checkpoint, "note": note}


def _tool_get_compliance_doc(args: dict) -> dict:
    doc_id = args["doc_id"]
    row = execute_query(
        "SELECT id, doc_type, project_code, content_md, version, [checkpoint], updated_at, updated_by FROM compliance_docs WHERE id = ?",
        (doc_id,), fetch="one"
    )
    if not row:
        return {"error": f"Compliance doc '{doc_id}' not found"}
    return {
        "id": row["id"],
        "doc_type": row.get("doc_type"),
        "project_code": row.get("project_code"),
        "version": row.get("version"),
        "checkpoint": row.get("checkpoint"),
        "updated_at": str(row["updated_at"]) if row.get("updated_at") else None,
        "updated_by": row.get("updated_by"),
        "content_md": row.get("content_md") or "",
        "content_length": len(row.get("content_md") or ""),
    }


def _tool_update_compliance_doc(args: dict) -> dict:
    doc_id = args["doc_id"]
    content_md = args["content_md"]
    version = args["version"]
    checkpoint = args["checkpoint"]
    updated_by = args.get("updated_by", "CC")
    doc_type = args.get("doc_type", "unknown")
    project_code = args.get("project_code", None)

    existing = execute_query(
        "SELECT id FROM compliance_docs WHERE id = ?", (doc_id,), fetch="one"
    )
    if existing:
        execute_query("""
            UPDATE compliance_docs
            SET content_md = ?, version = ?, [checkpoint] = ?, updated_at = GETUTCDATE(), updated_by = ?
            WHERE id = ?
        """, (content_md, version, checkpoint, updated_by, doc_id), fetch="none")
        status = "updated"
    else:
        execute_query("""
            INSERT INTO compliance_docs (id, doc_type, project_code, content_md, version, [checkpoint], updated_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (doc_id, doc_type, project_code, content_md, version, checkpoint, updated_by), fetch="none")
        status = "created"

    return {
        "id": doc_id,
        "version": version,
        "checkpoint": checkpoint,
        "updated_by": updated_by,
        "content_length": len(content_md),
        "status": status,
    }


def _tool_get_checkpoint(args: dict) -> dict:
    doc_id = args["doc_id"]
    row = execute_query(
        "SELECT id, version, [checkpoint], updated_at, updated_by FROM compliance_docs WHERE id = ?",
        (doc_id,), fetch="one"
    )
    if not row:
        return {"error": f"Compliance doc '{doc_id}' not found"}
    return {
        "id": row["id"],
        "version": row.get("version"),
        "checkpoint": row.get("checkpoint"),
        "updated_at": str(row["updated_at"]) if row.get("updated_at") else None,
        "updated_by": row.get("updated_by"),
    }


def _tool_post_uat_spec(args: dict) -> dict:
    """BA17: CAI posts UAT spec at prompt-creation time."""
    import uuid as _uuid
    from datetime import datetime

    pth = args["pth"]
    sprint_id = args["sprint_id"]
    project_code = args["project_code"]
    version = args["version"]
    test_cases_raw = args.get("test_cases", [])

    if not test_cases_raw:
        return {"error": "test_cases must not be empty (BA15 guard)"}

    tc_json = json.dumps([
        {
            "id": tc.get("id", ""),
            "title": tc.get("title", ""),
            "url": tc.get("url"),
            "steps": tc.get("steps", []),
            "expected": tc.get("expected", ""),
            "type": tc.get("type", "pl_visual"),
            "status": "pending",
            "notes": "",
        }
        for tc in test_cases_raw
    ])

    spec_data = json.dumps({
        "project": project_code,
        "sprint": sprint_id,
        "pth": pth,
        "version": version,
        "test_cases": test_cases_raw,
    })

    # Upsert by PTH (same as POST /api/uat/spec)
    existing = execute_query(
        "SELECT TOP 1 id FROM uat_pages WHERE pth = ? AND spec_source = 'cc_spec' ORDER BY created_at DESC",
        (pth,), fetch="one"
    )

    if existing:
        spec_id = str(existing["id"])
        execute_query("""
            UPDATE uat_pages SET
                project = ?, sprint_code = ?, version = ?,
                test_cases_json = ?, html_content = 'spec_created',
                status = 'ready', spec_data = ?
            WHERE id = ?
        """, (project_code, sprint_id, version, tc_json, spec_data, spec_id), fetch="none")
    else:
        spec_id = str(_uuid.uuid4()).upper()
        execute_query("""
            INSERT INTO uat_pages
                (id, handoff_id, project, sprint_code, pth, version,
                 test_cases_json, html_content, status,
                 spec_source, spec_locked_at, spec_data)
            VALUES (?, ?, ?, ?, ?, ?,
                    ?, 'spec_created', 'ready',
                    'cc_spec', ?, ?)
        """, (
            spec_id, spec_id, project_code, sprint_id, pth, version,
            tc_json, datetime.utcnow(), spec_data,
        ), fetch="none")

    uat_url = f"https://metapm.rentyourcio.com/uat/{spec_id}"

    # BA17 fix: persist individual BV items to uat_bv_items (so get_uat_results can read them)
    for tc in test_cases_raw:
        try:
            bv_id = tc.get("id", "")
            bv_title = tc.get("title", "")
            execute_query("""
                IF EXISTS (SELECT 1 FROM uat_bv_items WHERE spec_id=? AND bv_id=?)
                    UPDATE uat_bv_items
                    SET title=?, status='pending', notes='', updated_at=GETUTCDATE()
                    WHERE spec_id=? AND bv_id=?
                ELSE
                    INSERT INTO uat_bv_items (spec_id, bv_id, title, status, notes)
                    VALUES (?, ?, ?, 'pending', '')
            """, (
                spec_id, bv_id,            # EXISTS check
                bv_title,                   # UPDATE SET
                spec_id, bv_id,            # UPDATE WHERE
                spec_id, bv_id, bv_title,  # INSERT
            ), fetch="none")
        except Exception as bv_err:
            logger.warning(f"post_uat_spec BV item upsert failed for {bv_id}: {bv_err}")

    # Auto-advance linked requirement to uat_ready
    try:
        req_row = execute_query(
            "SELECT TOP 1 id, code, status FROM roadmap_requirements WHERE pth = ?",
            (pth,), fetch="one"
        )
        if req_row and req_row["status"] not in {"uat_ready", "done", "closed"}:
            execute_query(
                "UPDATE roadmap_requirements SET status = 'uat_ready', uat_url = ?, updated_at = GETUTCDATE() WHERE id = ?",
                (uat_url, req_row["id"]), fetch="none"
            )
    except Exception as e:
        logger.warning(f"post_uat_spec: requirement auto-advance failed (non-fatal): {e}")

    return {
        "spec_id": spec_id,
        "uat_url": uat_url,
        "test_count": len(test_cases_raw),
        "pth": pth,
        "status": "spec_created",
    }


def _tool_post_requirement(args: dict) -> dict:
    """MF003: Create a requirement via project_code. Auto-generates next sequential code."""
    import uuid as _uuid

    project_code = args["project_code"].upper()
    title = args["title"]
    description = args.get("description", "") or ""
    priority = args.get("priority", "P2") or "P2"
    req_type = args.get("type", "feature") or "feature"
    sprint_id = args.get("sprint_id", "") or None

    # 1. Resolve project_code → project_id
    proj = execute_query(
        "SELECT id FROM roadmap_projects WHERE code = ?",
        (project_code,), fetch="one"
    )
    if not proj:
        return {"error": f"Project '{project_code}' not found. Use list_projects to see valid codes."}
    project_id = str(proj["id"])

    # 2. Auto-generate next sequential code
    prefix_map = {
        "feature": "REQ", "enhancement": "REQ",
        "bug": "BUG", "task": "TSK", "vision": "VIS",
    }
    prefix = prefix_map.get(req_type.lower(), "REQ")

    max_row = execute_query("""
        SELECT MAX(
            TRY_CAST(
                SUBSTRING(r.code, CHARINDEX('-', r.code) + 1, LEN(r.code)) AS INT
            )
        ) as maxNum
        FROM roadmap_requirements r
        WHERE r.project_id = ? AND r.code LIKE ?
    """, (project_id, f"{prefix}-%"), fetch="one")

    next_num = (max_row["maxNum"] or 0) + 1 if max_row else 1

    # Skip over existing codes (uniqueness loop)
    code = None
    for _ in range(100):
        candidate = f"{prefix}-{next_num:03d}"
        existing = execute_query(
            "SELECT id FROM roadmap_requirements WHERE project_id = ? AND code = ?",
            (project_id, candidate), fetch="one"
        )
        if not existing:
            code = candidate
            break
        next_num += 1

    if not code:
        return {"error": "Could not generate unique code after 100 attempts"}

    # 3. Insert requirement
    req_id = str(_uuid.uuid4())
    status = "req_created"

    execute_query("""
        INSERT INTO roadmap_requirements
            (id, project_id, code, title, description, type, priority, status,
             target_version, sprint_id, handoff_id, uat_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?,
                NULL, ?, NULL, NULL)
    """, (
        req_id, project_id, code, title, description,
        req_type.lower(), priority, status, sprint_id,
    ), fetch="none")

    url = f"https://metapm.rentyourcio.com/requirements/{req_id}"
    return {
        "id": req_id,
        "code": code,
        "title": title,
        "project_code": project_code,
        "status": status,
        "priority": priority,
        "type": req_type.lower(),
        "url": url,
    }


def _tool_create_handoff_shell(args: dict) -> dict:
    """BA17: CAI pre-creates a handoff shell UUID. CC fills in fields via PATCH."""
    pth = args["pth"]
    sprint_id = args["sprint_id"]
    project_code = args["project_code"]
    uat_spec_id = args.get("uat_spec_id") or None

    result = execute_query("""
        INSERT INTO handoff_shells (pth, sprint_id, project_code, uat_spec_id)
        OUTPUT INSERTED.id, INSERTED.pth, INSERTED.sprint_id, INSERTED.project_code,
               INSERTED.uat_spec_id, INSERTED.created_at
        VALUES (?, ?, ?, ?)
    """, (pth, sprint_id, project_code, uat_spec_id), fetch="one")

    if not result:
        return {"error": "Failed to create handoff shell"}

    handoff_id = str(result["id"])
    patch_url = f"https://metapm.rentyourcio.com/mcp/handoffs/{handoff_id}"

    return {
        "handoff_id": handoff_id,
        "pth": result["pth"],
        "sprint_id": result["sprint_id"],
        "project_code": result["project_code"],
        "uat_spec_id": result.get("uat_spec_id"),
        "patch_url": patch_url,
        "created_at": str(result["created_at"]) if result.get("created_at") else None,
        "message": f"Handoff shell created. CC fills in via PATCH {patch_url}",
    }


# Tool dispatch map
TOOL_HANDLERS = {
    "post_prompt": _tool_post_prompt,
    "get_prompt": _tool_get_prompt,
    "post_review": _tool_post_review,
    "get_uat_results": _tool_get_uat_results,
    "trigger_rag_sync": _tool_trigger_rag_sync,
    "list_requirements": _tool_list_requirements,
    "patch_requirement_status": _tool_patch_requirement_status,
    "reject_prompt": _tool_reject_prompt,
    "list_projects": _tool_list_projects,
    "get_compliance_doc": _tool_get_compliance_doc,
    "update_compliance_doc": _tool_update_compliance_doc,
    "get_checkpoint": _tool_get_checkpoint,
    "post_uat_spec": _tool_post_uat_spec,
    "post_requirement": _tool_post_requirement,
    "create_handoff_shell": _tool_create_handoff_shell,
}


# ── JSON-RPC 2.0 endpoint (MCP protocol) ──

def _jsonrpc_error(req_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _jsonrpc_result(req_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


@router.post("/mcp-tools")
async def mcp_jsonrpc(request: Request):
    """MCP JSON-RPC 2.0 endpoint — no auth (Claude.ai cannot send custom headers)."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(_jsonrpc_error(None, -32700, "Parse error"))

    req_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params", {})

    if method == "initialize":
        return JSONResponse(_jsonrpc_result(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "metapm", "version": Settings().VERSION},
        }))

    if method == "tools/list":
        return JSONResponse(_jsonrpc_result(req_id, {"tools": TOOLS}))

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        handler = TOOL_HANDLERS.get(tool_name)
        if not handler:
            return JSONResponse(_jsonrpc_error(req_id, -32601, f"Unknown tool: {tool_name}"))

        try:
            result = handler(arguments)
            return JSONResponse(_jsonrpc_result(req_id, {
                "content": [{"type": "text", "text": json.dumps(result)}],
            }))
        except Exception as e:
            logger.error(f"MCP tool {tool_name} failed: {e}")
            return JSONResponse(_jsonrpc_result(req_id, {
                "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                "isError": True,
            }))

    return JSONResponse(_jsonrpc_error(req_id, -32601, f"Unknown method: {method}"))
