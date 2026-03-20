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
        "description": "Advance a requirement to a new status. Use to close a requirement after UAT passes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Requirement code (e.g. 'MP-064')"},
                "status": {"type": "string", "description": "Target status (e.g. 'uat_ready', 'done', 'closed')"},
                "note": {"type": "string", "description": "Optional note", "default": ""},
            },
            "required": ["code", "status"],
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


def _tool_list_projects(args: dict) -> dict:
    rows = execute_query("""
        SELECT id, code, name, production_url
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
                "production_url": r.get("production_url") or "",
            }
            for r in rows
        ],
    }


def _tool_patch_requirement_status(args: dict) -> dict:
    code = args["code"]
    status = args["status"]
    note = args.get("note", "")

    req = execute_query(
        "SELECT id, status FROM roadmap_requirements WHERE code = ?",
        (code,), fetch="one"
    )
    if not req:
        return {"error": f"Requirement '{code}' not found"}

    req_id = req["id"]
    current = req["status"]

    execute_query(
        "UPDATE roadmap_requirements SET status = ?, updated_at = GETDATE() WHERE id = ?",
        (status, req_id), fetch="none"
    )

    checkpoint = hashlib.sha256(f"{req_id}:{status}".encode()).hexdigest()[:4].upper()
    return {"code": code, "previous_status": current, "status": status, "checkpoint": checkpoint, "note": note}


# Tool dispatch map
TOOL_HANDLERS = {
    "post_prompt": _tool_post_prompt,
    "get_prompt": _tool_get_prompt,
    "post_review": _tool_post_review,
    "get_uat_results": _tool_get_uat_results,
    "trigger_rag_sync": _tool_trigger_rag_sync,
    "list_requirements": _tool_list_requirements,
    "patch_requirement_status": _tool_patch_requirement_status,
    "list_projects": _tool_list_projects,
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
            "serverInfo": {"name": "metapm", "version": "2.37.4"},
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
