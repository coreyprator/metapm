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

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.core.database import execute_query
from app.core.state_machine import (
    validate_prompt_transition, write_prompt_history, write_prompt_failure,
    write_requirement_failure, write_failure_event, InvalidTransitionError,
)

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
                "requirement_code": {"type": "string", "description": "MP18 BUG-035: requirement code to link PTH to (REQUIRED)"},
            },
            "required": ["pth", "sprint_id", "project_id", "content_md", "requirement_code"],
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
                "covered_by_pth": {"type": "string", "description": "PTH of the sprint that delivered this requirement, for requirements with null PTH (also-closes). Allows uat_ready advancement without a direct requirement→spec link.", "default": ""},
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
    {
        "name": "get_uat_results_by_pth",
        "description": "Get the most recent UAT results for a PTH. Returns uat_status, submitted_at, and parsed test_cases array. CAI calls this to check UAT outcome without PL OAuth.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pth": {"type": "string", "description": "Prompt tracking hash (e.g. 'SF01')"},
            },
            "required": ["pth"],
        },
    },
    {
        "name": "get_challenge",
        "description": "Generate a one-time challenge token for a sprint PTH. CAI calls this at prompt-creation time and embeds the token in the prompt as required BV evidence. CC must include the exact token in the handoff. CAI verifies via verify_challenge at review time.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pth": {"type": "string", "description": "PTH of the sprint being challenged"},
            },
            "required": ["pth"],
        },
    },
    {
        "name": "verify_challenge",
        "description": "Verify a challenge token submitted by CC in a handoff. Returns valid:true if token matches and hasn't been used. Marks token as used on success.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pth": {"type": "string", "description": "PTH of the sprint"},
                "token": {"type": "string", "description": "Token from CC handoff machine_tests field"},
            },
            "required": ["pth", "token"],
        },
    },
    {
        "name": "post_session_signal",
        "description": "Fire a CC session start/end signal. CC must fire 'started' before implementation and 'completed'/'stopped'/'blocked' at session end. Updates prompt status and session timestamps.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pth": {"type": "string", "description": "PTH of the current sprint"},
                "status": {"type": "string", "enum": ["started", "completed", "stopped", "blocked"], "description": "Session signal type"},
                "timestamp": {"type": "string", "description": "ISO 8601 timestamp of the signal"},
                "reason": {"type": "string", "description": "Required when status is stopped or blocked — one sentence explaining why", "default": ""},
            },
            "required": ["pth", "status", "timestamp"],
        },
    },
    {
        "name": "get_requirement_history",
        "description": "Get the full transition history for a requirement by code and project_code. Returns all state changes with success/failure status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Requirement code (e.g. REQ-035)"},
                "project_code": {"type": "string", "description": "Project code (e.g. MP)"},
            },
            "required": ["code", "project_code"],
        },
    },
    {
        "name": "submit_cc_results",
        "description": "Submit machine BV results with evidence to a UAT spec. CC calls this after running machine tests to record cc_result (pass/fail) and cc_evidence (raw output) for each cc_machine BV.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spec_id": {"type": "string", "description": "UAT spec UUID"},
                "test_cases": {
                    "type": "array",
                    "description": "Array of cc_machine BV results",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "BV ID (e.g. MP19-M01)"},
                            "cc_result": {"type": "string", "enum": ["pass", "fail"], "description": "Machine test result"},
                            "cc_evidence": {"type": "string", "description": "Raw output/JSON proving the result"},
                        },
                        "required": ["id", "cc_result", "cc_evidence"],
                    },
                },
            },
            "required": ["spec_id", "test_cases"],
        },
    },
    {
        "name": "execute_sql_query",
        "description": "Execute a read-only SQL SELECT query against any portfolio database. Use for source code search (code_files table in MetaPM), app content queries, or schema exploration. Max 500 rows returned.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "SELECT statement to execute"},
                "database": {
                    "type": "string",
                    "description": "Target database",
                    "enum": ["MetaPM", "LanguageLearning", "EtymologyGraph", "Etymython", "HarmonyLab", "ArtForge"],
                },
            },
            "required": ["sql", "database"],
        },
    },
    {
        "name": "get_schema",
        "description": "Get live table and column metadata for any portfolio database. Returns table names, column names, data types, nullability, and defaults from INFORMATION_SCHEMA. Use this before writing queries to avoid guessing column names.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "database": {
                    "type": "string",
                    "description": "Target database",
                    "enum": ["MetaPM", "LanguageLearning", "EtymologyGraph", "Etymython", "HarmonyLab", "ArtForge"],
                },
                "table_name": {
                    "type": "string",
                    "description": "Optional — if provided, return only this table's columns. If omitted, return all tables.",
                },
            },
            "required": ["database"],
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
    requirement_code = args.get("requirement_code")

    # MP18 BUG-035: requirement_code is REQUIRED
    if not requirement_code:
        return {"error": "requirement_code is required."}

    # MP18 BUG-035: Look up requirement by code + project
    req_row = execute_query(
        "SELECT r.id, r.code, r.status FROM roadmap_requirements r "
        "JOIN roadmap_projects p ON r.project_id = p.id "
        "WHERE r.code = ? AND p.id = ?",
        (requirement_code, project_id), fetch="one"
    )
    if not req_row:
        return {"error": f"requirement_code {requirement_code} not found in project {project_id}."}
    # MP19 BUG-037: Allow linking at cai_designing or cc_prompt_ready
    linkable_statuses = ("cai_designing", "cc_prompt_ready")
    if req_row["status"] not in linkable_statuses:
        return {"error": f"requirement {requirement_code} is at status {req_row['status']}, expected one of {linkable_statuses}. Cannot link prompt."}

    # MP12B GATE 3: PTH uniqueness — reject if active prompt exists for this PTH
    active = execute_query(
        "SELECT id, status FROM cc_prompts WHERE pth = ? AND project_id = ? "
        "AND status NOT IN ('rejected', 'completed', 'stopped', 'blocked', 'cancelled', 'closed')",
        (pth, project_id), fetch="one"
    )
    if active:
        write_failure_event('duplicate_pth', pth, 'post_prompt',
                            f"PTH '{pth}' already has active prompt (id={active['id']}) in status '{active['status']}'")
        return {"error": f"PTH '{pth}' already has an active prompt in status '{active['status']}'. Reject or complete it first."}

    result = execute_query("""
        SET NOCOUNT ON;
        INSERT INTO cc_prompts
            (sprint_id, project_id, pth, requirement_id, content, content_md,
             estimated_hours, created_by, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'CAI', 'draft');
        SELECT id, pth, sprint_id, status, created_at
        FROM cc_prompts WHERE id = SCOPE_IDENTITY();
    """, (
        sprint_id, project_id, pth, req_row["id"],
        content_md[:500] if content_md else '',
        content_md, estimated_hours,
    ), fetch="one")

    if not result:
        return {"error": "Failed to create prompt"}

    # MP12B: Write initial history row for draft creation
    write_prompt_history(result["id"], pth, None, 'draft', 'CAI', 'post_prompt')

    # MP18 BUG-035 + MP19 BUG-037: Write PTH to requirement, auto-advance only if at cai_designing
    requirement_advanced = False
    try:
        execute_query(
            "UPDATE roadmap_requirements SET pth = ?, updated_at = GETDATE() WHERE id = ?",
            (pth, req_row["id"]), fetch="none"
        )
        if req_row["status"] == "cai_designing":
            execute_query(
                "UPDATE roadmap_requirements SET status = 'cc_prompt_ready', updated_at = GETDATE() WHERE id = ?",
                (req_row["id"],), fetch="none"
            )
            requirement_advanced = True
            logger.info(f"BUG-037: linked PTH {pth} to {requirement_code}, advanced to cc_prompt_ready")
        else:
            logger.info(f"BUG-037: linked PTH {pth} to {requirement_code} (already at {req_row['status']}, no advance needed)")
    except Exception as e:
        logger.warning(f"BUG-037: requirement auto-advance failed (non-fatal): {e}")

    return {
        "id": result["id"],
        "pth": result.get("pth"),
        "sprint_id": result.get("sprint_id"),
        "status": "draft",
        "url": f"https://metapm.rentyourcio.com/prompts/{result['pth']}",
        "created_at": str(result["created_at"]) if result.get("created_at") else None,
        "requirement_advanced": requirement_advanced,
        "requirement_code": requirement_code,
    }


def _tool_get_prompt(args: dict) -> dict:
    pth = args["pth"]
    row = execute_query("""
        SELECT TOP 1 id, sprint_id, project_id, pth, status,
               LEN(content_md) as content_length,
               created_by, approved_by, approved_at, created_at
        FROM cc_prompts WHERE pth = ?
        ORDER BY id DESC
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
        "SELECT TOP 1 id, pth, status FROM cc_prompts WHERE pth = ? ORDER BY id DESC",
        (pth,), fetch="one"
    )
    if not row:
        return {"error": f"Prompt '{pth}' not found"}
    current = row.get("status", "")
    terminal = ("rejected", "completed", "stopped", "closed", "cancelled")
    if current in terminal:
        write_prompt_failure(row["id"], pth, current, 'rejected', 'CAI', 'reject_prompt',
                             f"Cannot reject prompt in terminal status '{current}'.")
        return {"error": f"Cannot reject prompt in terminal status '{current}'."}
    execute_query(
        "UPDATE cc_prompts SET status='rejected', rejection_reason=?, updated_at=GETUTCDATE() WHERE id=?",
        (reason[:500] if reason else None, row["id"]), fetch="none"
    )
    write_prompt_history(row["id"], pth, current, 'rejected', 'CAI', 'reject_prompt')
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
    covered_by_pth = args.get("covered_by_pth", "")

    if pth:
        req = execute_query(
            "SELECT id, status FROM roadmap_requirements WHERE code = ? AND pth = ?",
            (code, pth), fetch="one"
        )
        if not req:
            # Retry: check if requirement exists but has no PTH assigned yet
            exists = execute_query(
                """SELECT r.id, r.status, p.code AS project
                   FROM roadmap_requirements r
                   JOIN roadmap_projects p ON r.project_id = p.id
                   WHERE r.code = ? AND (r.pth IS NULL OR r.pth = '')""",
                (code,), fetch="one"
            )
            if exists:
                return {
                    "error": "no_pth_assigned",
                    "message": f"Requirement '{code}' exists in project '{exists['project']}' but has no PTH yet. "
                               f"Use project_code='{exists['project']}' as discriminator instead, or call post_prompt first to assign a PTH.",
                    "hint": f"patch_requirement_status(code='{code}', project_code='{exists['project']}', status=...)"
                }
            return {"error": f"Requirement '{code}' with pth '{pth}' not found"}
    elif project_code:
        req = execute_query(
            "SELECT r.id, r.status FROM roadmap_requirements r JOIN roadmap_projects p ON r.project_id = p.id WHERE r.code = ? AND p.code = ?",
            (code, project_code), fetch="one"
        )
        if not req:
            return {"error": f"Requirement '{code}' in project '{project_code}' not found"}
    else:
        rows = execute_query(
            """SELECT r.id, r.status, r.pth, p.code AS project_code
               FROM roadmap_requirements r
               JOIN roadmap_projects p ON r.project_id = p.id
               WHERE r.code = ?""",
            (code,), fetch="all"
        ) or []
        if not rows:
            return {"error": f"Requirement '{code}' not found"}
        if len(rows) > 1:
            projects = [r['project_code'] for r in rows]
            return {
                "error": "ambiguous_code",
                "message": f"Requirement code '{code}' exists in multiple projects: {projects}. "
                           f"Provide project_code to disambiguate.",
                "hint": f"patch_requirement_status(code='{code}', project_code='<one of {projects}>', status=...)"
            }
        req = rows[0]

    req_id = req["id"]
    current = req["status"]

    # MP18 BUG-036: State machine enforcement
    from app.api.roadmap import ALLOWED_TRANSITIONS
    allowed = ALLOWED_TRANSITIONS.get(current, [])
    if status not in allowed:
        write_requirement_failure(req_id, current, status, 'MCP', 'patch_requirement_status',
                                  f"illegal_transition: {current} -> {status}")
        return {
            "error": "illegal_transition",
            "current_status": current,
            "requested_status": status,
            "allowed_next": allowed,
        }

    # MP18 BUG-036: "closed" requires a non-empty note
    if status == "closed" and not (note and note.strip()):
        return {"error": "note required when closing from any status."}

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
                reason = f"Handoff incomplete - missing fields: {', '.join(missing)}"
                write_requirement_failure(req_id, current, 'cc_complete', 'CC', 'patch_requirement_status', reason)
                return {
                    "error": f"{reason}. Fill via PATCH {patch_url} before advancing to cc_complete.",
                    "handoff_shell_id": shell_id,
                    "missing_fields": missing,
                }

    # MP31 BUG-064: uat_ready gate — check UAT page + review exist for requirement's PTH
    if status == 'uat_ready':
        has_uat = False
        has_review = False
        req_full = execute_query("SELECT uat_url, pth FROM roadmap_requirements WHERE id = ?", (req_id,), fetch="one")
        # BUG-069: covered_by_pth overrides stored PTH when explicitly provided
        req_pth_val = covered_by_pth or (req_full.get('pth') if req_full else None) or pth
        if not req_pth_val:
            return {"error": "Cannot advance to uat_ready: requirement has no PTH and no covered_by_pth provided."}
        if req_pth_val:
            uat_row = execute_query(
                "SELECT COUNT(*) AS cnt FROM uat_pages WHERE pth = ?",
                (req_pth_val,), fetch="one"
            )
            has_uat = uat_row and uat_row['cnt'] > 0

            review_row = execute_query(
                "SELECT COUNT(*) AS cnt FROM reviews WHERE prompt_pth = ?",
                (req_pth_val,), fetch="one"
            )
            has_review = review_row and review_row['cnt'] > 0

        if not has_uat:
            reason = 'missing_uat: cannot advance to uat_ready without a UAT page for PTH'
            write_requirement_failure(req_id, current, 'uat_ready', 'CAI', 'patch_requirement_status', reason)
            return {"error": "Cannot advance to uat_ready: no UAT found for PTH."}
        if not has_review:
            reason = 'review_required: cannot advance to uat_ready without a CAI review for PTH'
            write_requirement_failure(req_id, current, 'uat_ready', 'MCP', 'patch_requirement_status', reason)
            return {"error": "review_required",
                "message": "Cannot close: no CAI review record for this PTH."}

    # MP24 TSK-016: Close gate — require review if UAT pages exist
    if status in ('done', 'closed', 'uat_pass'):
        req_full = execute_query("SELECT pth FROM roadmap_requirements WHERE id = ?", (req_id,), fetch="one")
        # BUG-069: covered_by_pth overrides stored PTH when explicitly provided
        req_pth = covered_by_pth or (req_full.get("pth") if req_full else None) or pth
        if req_pth:
            uat_exists = execute_query(
                "SELECT TOP 1 id FROM uat_pages WHERE pth = ?",
                (req_pth,), fetch="one"
            )
            if uat_exists:
                review_exists = execute_query(
                    "SELECT TOP 1 id FROM reviews WHERE prompt_pth = ?",
                    (req_pth,), fetch="one"
                )
                if not review_exists:
                    reason = f"review_required: cannot close {code} — UAT pages exist but no review record"
                    write_requirement_failure(req_id, current, status, 'MCP', 'patch_requirement_status', reason)
                    return {
                        "error": "review_required",
                        "message": "Cannot close this requirement — no CAI review record found. CAI must call post_review before closing.",
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
        write_failure_event('empty_test_cases', pth, 'post_uat_spec',
                            'UAT spec rejected: test_cases array was empty. Zero-BV spec produces zero-evidence pass.')
        return {"error": "UAT spec requires at least one test case. A zero-BV spec produces a zero-evidence pass and is not permitted."}

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

    # MP24 BUG-043: Delete all existing BV items before inserting new ones (dedup on re-spec)
    if existing:
        try:
            execute_query("DELETE FROM uat_bv_items WHERE spec_id = ?", (spec_id,), fetch="none")
            logger.info(f"post_uat_spec: deleted old BV items for spec {spec_id} (dedup)")
        except Exception as del_err:
            logger.warning(f"post_uat_spec: BV item cleanup failed: {del_err}")

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

    # Auto-advance linked requirement from cc_complete -> uat_ready
    try:
        req_row = execute_query(
            "SELECT TOP 1 id, code, status FROM roadmap_requirements WHERE pth = ? AND status = 'cc_complete'",
            (pth,), fetch="one"
        )
        if req_row:
            execute_query(
                "UPDATE roadmap_requirements SET status = 'uat_ready', uat_url = ?, updated_at = GETUTCDATE() WHERE id = ?",
                (uat_url, req_row["id"]), fetch="none"
            )
            logger.info(f"post_uat_spec: auto-advanced {req_row['code']} to uat_ready for PTH {pth}")
        else:
            write_failure_event('orphan_pth', pth, 'post_uat_spec',
                                f"No requirement found at cc_complete for PTH '{pth}' during post_uat_spec.")
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

    # Auto-advance linked requirement from cc_executing -> cc_complete
    requirement_advanced = None
    try:
        req_row = execute_query(
            "SELECT TOP 1 id, code, status FROM roadmap_requirements WHERE pth = ? AND status = 'cc_executing'",
            (pth,), fetch="one"
        )
        if req_row:
            execute_query(
                "UPDATE roadmap_requirements SET status = 'cc_complete', updated_at = GETUTCDATE() WHERE id = ?",
                (req_row["id"],), fetch="none"
            )
            requirement_advanced = {"code": req_row["code"], "new_status": "cc_complete"}
            logger.info(f"create_handoff_shell: auto-advanced {req_row['code']} to cc_complete for PTH {pth}")
        else:
            write_failure_event('orphan_pth', pth, 'create_handoff_shell',
                                f"No requirement found at cc_executing for PTH '{pth}' during create_handoff_shell.")
    except Exception as e:
        logger.warning(f"create_handoff_shell: requirement auto-advance failed (non-fatal): {e}")

    return {
        "handoff_id": handoff_id,
        "pth": result["pth"],
        "sprint_id": result["sprint_id"],
        "project_code": result["project_code"],
        "uat_spec_id": result.get("uat_spec_id"),
        "patch_url": patch_url,
        "created_at": str(result["created_at"]) if result.get("created_at") else None,
        "message": f"Handoff shell created. CC fills in via PATCH {patch_url}",
        "requirement_advanced": requirement_advanced,
    }


def _tool_get_uat_results_by_pth(args: dict) -> dict:
    """Get most recent UAT results by PTH. No auth required (read-only)."""
    pth = args["pth"]
    page = execute_query(
        "SELECT TOP 1 id, pth, status, test_cases_json, pl_submitted_at, created_at FROM uat_pages WHERE pth = ? ORDER BY created_at DESC",
        (pth,), fetch="one"
    )
    if not page:
        return {"error": f"No UAT results found for PTH '{pth}'"}

    test_cases = []
    if page.get("test_cases_json"):
        try:
            raw = json.loads(page["test_cases_json"])
            test_cases = [
                {"id": tc.get("id", ""), "title": tc.get("title", ""), "status": tc.get("status", "pending"), "notes": tc.get("notes", "")}
                for tc in raw if not tc.get("id", "").startswith("_")
            ]
        except (json.JSONDecodeError, TypeError):
            pass

    submitted_at = page.get("pl_submitted_at") or page.get("created_at")
    return {
        "pth": pth,
        "spec_id": str(page["id"]),
        "uat_status": page.get("status"),
        "submitted_at": str(submitted_at) if submitted_at else None,
        "test_cases": test_cases,
    }


def _tool_get_challenge(args: dict) -> dict:
    import secrets as _secrets
    pth = args["pth"]
    token = _secrets.token_hex(16)
    execute_query(
        "INSERT INTO challenge_tokens (pth, token) VALUES (?, ?)",
        (pth, token), fetch="none",
    )
    return {"pth": pth, "token": token}


def _tool_verify_challenge(args: dict) -> dict:
    pth = args["pth"]
    token = args["token"]
    row = execute_query(
        "SELECT id, used FROM challenge_tokens WHERE pth = ? AND token = ?",
        (pth, token), fetch="one",
    )
    if not row:
        return {"valid": False, "reason": "token not found"}
    if row["used"]:
        return {"valid": False, "reason": "token already used"}
    execute_query(
        "UPDATE challenge_tokens SET used = 1, used_at = GETDATE() WHERE id = ?",
        (row["id"],), fetch="none",
    )
    return {"valid": True}


def _tool_post_session_signal(args: dict) -> dict:
    pth = args["pth"]
    status = args["status"]
    timestamp = args["timestamp"]
    reason = args.get("reason", "")

    if status in ("stopped", "blocked") and not reason:
        return {"error": "reason is required when status is stopped or blocked"}

    # Find the newest prompt for this PTH
    row = execute_query(
        "SELECT TOP 1 id, status FROM cc_prompts WHERE pth = ? ORDER BY id DESC",
        (pth,), fetch="one"
    )
    if not row:
        return {"error": f"Prompt '{pth}' not found"}

    prompt_id = row["id"]
    from_status = row["status"]
    response = {"pth": pth, "signal": status, "timestamp": timestamp}

    if status == "started":
        new_status = 'executing'
        execute_query("""
            UPDATE cc_prompts
            SET status = 'executing',
                session_started_at = ?,
                session_outcome = 'started',
                updated_at = GETUTCDATE()
            WHERE id = ?
        """, (timestamp, prompt_id), fetch="none")
        write_prompt_history(prompt_id, pth, from_status, new_status, 'CC', 'post_session_signal')

        # MP12B ITEM 6: Auto-advance requirement cc_prompt_ready -> cc_executing
        try:
            req_row = execute_query(
                "SELECT TOP 1 id, code, status FROM roadmap_requirements WHERE pth = ? AND status = 'cc_prompt_ready'",
                (pth,), fetch="one"
            )
            if req_row:
                execute_query(
                    "UPDATE roadmap_requirements SET status = 'cc_executing', updated_at = GETUTCDATE() WHERE id = ?",
                    (req_row["id"],), fetch="none"
                )
                response['requirement_advanced'] = {'code': req_row['code'], 'new_status': 'cc_executing'}
                logger.info(f"post_session_signal: auto-advanced {req_row['code']} to cc_executing for PTH {pth}")
            else:
                write_failure_event('orphan_pth', pth, 'post_session_signal',
                                    f"session-start for PTH '{pth}' found no requirement at cc_prompt_ready.")
        except Exception as e:
            logger.warning(f"post_session_signal: requirement auto-advance failed (non-fatal): {e}")

    elif status == "completed":
        new_status = 'completed'
        execute_query("""
            UPDATE cc_prompts
            SET status = 'completed',
                session_ended_at = ?,
                session_outcome = 'completed',
                updated_at = GETUTCDATE()
            WHERE id = ?
        """, (timestamp, prompt_id), fetch="none")
        write_prompt_history(prompt_id, pth, from_status, new_status, 'CC', 'post_session_signal')

    elif status in ("stopped", "blocked"):
        new_status = 'stopped'
        execute_query("""
            UPDATE cc_prompts
            SET status = 'stopped',
                session_ended_at = ?,
                session_outcome = ?,
                session_stop_reason = ?,
                updated_at = GETUTCDATE()
            WHERE id = ?
        """, (timestamp, status, reason[:500], prompt_id), fetch="none")
        write_prompt_history(prompt_id, pth, from_status, new_status, 'CC', 'post_session_signal')

    response["message"] = f"Session signal '{status}' recorded for {pth}."
    return response


def _tool_get_requirement_history(args: dict) -> dict:
    """MP12B: Get requirement transition history by code and project_code."""
    code = args["code"]
    project_code = args["project_code"]

    req = execute_query(
        "SELECT r.id, r.code FROM roadmap_requirements r "
        "JOIN roadmap_projects p ON r.project_id = p.id "
        "WHERE r.code = ? AND p.code = ?",
        (code, project_code), fetch="one"
    )
    if not req:
        return {"error": f"Requirement '{code}' in project '{project_code}' not found"}

    rows = execute_query("""
        SELECT id, requirement_id, changed_at, changed_by, field_name,
               old_value, new_value, sprint_id, notes, success, blocked_reason
        FROM requirement_history
        WHERE requirement_id = ? AND field_name = 'status'
        ORDER BY changed_at DESC
    """, (req["id"],), fetch="all") or []

    return {
        "code": code,
        "project_code": project_code,
        "count": len(rows),
        "history": [
            {
                "id": r["id"],
                "from_status": r.get("old_value"),
                "to_status": r.get("new_value"),
                "changed_at": str(r["changed_at"]) if r.get("changed_at") else None,
                "changed_by": r.get("changed_by"),
                "notes": r.get("notes"),
                "success": bool(r.get("success", 1)),
                "blocked_reason": r.get("blocked_reason"),
            }
            for r in rows
        ],
    }


def _tool_submit_cc_results(args: dict) -> dict:
    """MP19 REQ-049: Submit machine BV results with evidence."""
    spec_id = args["spec_id"]
    test_cases = args["test_cases"]

    row = execute_query(
        "SELECT id, test_cases_json FROM uat_pages WHERE id = ?",
        (spec_id,), fetch="one"
    )
    if not row:
        return {"error": f"UAT spec {spec_id} not found"}

    import json
    existing_cases = json.loads(row["test_cases_json"]) if row.get("test_cases_json") else []
    updates_by_id = {tc["id"]: tc for tc in test_cases}
    updated_count = 0

    for case in existing_cases:
        if case.get("id", "").startswith("_"):
            continue
        update = updates_by_id.get(case["id"])
        if update and case.get("type") == "cc_machine":
            case["cc_result"] = update["cc_result"]
            case["cc_evidence"] = update["cc_evidence"]
            case["status"] = update["cc_result"]
            updated_count += 1

    execute_query("""
        UPDATE uat_pages SET test_cases_json = ? WHERE id = ?
    """, (json.dumps(existing_cases), spec_id), fetch="none")

    # Persist to uat_bv_items
    for tc in test_cases:
        try:
            execute_query("""
                IF EXISTS (SELECT 1 FROM uat_bv_items WHERE spec_id=? AND bv_id=?)
                    UPDATE uat_bv_items
                    SET status=?, cc_result=?, cc_evidence=?
                    WHERE spec_id=? AND bv_id=?
                ELSE
                    INSERT INTO uat_bv_items (spec_id, bv_id, title, status, cc_result, cc_evidence)
                    VALUES (?, ?, ?, ?, ?, ?)
            """, (
                spec_id, tc["id"],
                tc["cc_result"], tc["cc_result"], tc["cc_evidence"],
                spec_id, tc["id"],
                spec_id, tc["id"], tc["id"],
                tc["cc_result"], tc["cc_result"], tc["cc_evidence"],
            ), fetch="none")
        except Exception as e:
            logger.warning(f"CC BV item upsert failed for {tc['id']}: {e}")

    return {"updated": updated_count, "spec_id": spec_id}


# ── Read-only SQL query tool ──

import re as _re

_ALLOWED_DATABASES = {"MetaPM", "LanguageLearning", "EtymologyGraph", "Etymython", "HarmonyLab", "ArtForge"}
_WRITE_KEYWORDS = _re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|EXEC|TRUNCATE|ALTER|CREATE)\b', _re.IGNORECASE
)
_ROW_CAP = 500


def _tool_execute_sql_query(args: dict) -> dict:
    sql = args.get("sql", "").strip()
    database = args.get("database", "")

    if database not in _ALLOWED_DATABASES:
        return {"error": f"Database '{database}' not allowed. Must be one of: {', '.join(sorted(_ALLOWED_DATABASES))}"}

    if _WRITE_KEYWORDS.search(sql):
        return {"error": "Write operations are not permitted. Only SELECT queries are allowed."}

    if not sql.upper().startswith("SELECT"):
        return {"error": "Only SELECT statements are allowed."}

    try:
        import pyodbc
        from app.core.config import settings

        server = settings.DB_SERVER
        if "," not in server and ":" not in server:
            server = f"{server},1433"

        conn_str = (
            f"DRIVER={{{settings.DB_DRIVER}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={settings.DB_USER};"
            f"PWD={settings.DB_PASSWORD};"
            "TrustServerCertificate=yes;"
        )
        conn = pyodbc.connect(conn_str, timeout=30)
        conn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-16-le')
        conn.setencoding(encoding='utf-16-le')

        cursor = conn.cursor()
        cursor.execute(sql)

        if not cursor.description:
            conn.close()
            return {"database": database, "row_count": 0, "truncated": False, "rows": []}

        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchmany(_ROW_CAP + 1)
        truncated = len(rows) > _ROW_CAP
        if truncated:
            rows = rows[:_ROW_CAP]

        result_rows = []
        for row in rows:
            result_rows.append({
                col: (str(val) if val is not None and not isinstance(val, (str, int, float, bool)) else val)
                for col, val in zip(columns, row)
            })

        conn.close()
        return {
            "database": database,
            "row_count": len(result_rows),
            "truncated": truncated,
            "rows": result_rows,
        }
    except Exception as e:
        logger.error(f"execute_sql_query failed: {e}")
        return {"error": str(e)}


# ── get_schema tool ──

def _tool_get_schema(args: dict) -> dict:
    database = args.get("database", "")
    table_name = args.get("table_name")

    if database not in _ALLOWED_DATABASES:
        return {"error": f"Database '{database}' not allowed. Must be one of: {', '.join(sorted(_ALLOWED_DATABASES))}"}

    try:
        import pyodbc
        from app.core.config import settings

        server = settings.DB_SERVER
        if "," not in server and ":" not in server:
            server = f"{server},1433"

        conn_str = (
            f"DRIVER={{{settings.DB_DRIVER}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={settings.DB_USER};"
            f"PWD={settings.DB_PASSWORD};"
            "TrustServerCertificate=yes;"
        )
        conn = pyodbc.connect(conn_str, timeout=30)
        conn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-16-le')
        conn.setencoding(encoding='utf-16-le')

        cursor = conn.cursor()
        sql = """
            SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE,
                   CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo'
        """
        params = []
        if table_name:
            sql += " AND TABLE_NAME = ?"
            params.append(table_name)
        sql += " ORDER BY TABLE_NAME, ORDINAL_POSITION"

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        tables_dict: dict = {}
        for row in rows:
            tname = row[0]
            if tname not in tables_dict:
                tables_dict[tname] = []
            tables_dict[tname].append({
                "column_name": row[1],
                "data_type": row[2],
                "max_length": row[3],
                "is_nullable": row[4],
                "column_default": row[5],
            })

        tables = [
            {"table_name": tname, "columns": cols}
            for tname, cols in tables_dict.items()
        ]

        return {
            "database": database,
            "table_count": len(tables),
            "tables": tables,
        }
    except Exception as e:
        logger.error(f"get_schema failed for {database}: {e}")
        return {"database": database, "error": "access_denied", "detail": str(e)}


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
    "get_uat_results_by_pth": _tool_get_uat_results_by_pth,
    "get_challenge": _tool_get_challenge,
    "verify_challenge": _tool_verify_challenge,
    "post_session_signal": _tool_post_session_signal,
    "get_requirement_history": _tool_get_requirement_history,
    "submit_cc_results": _tool_submit_cc_results,
    "execute_sql_query": _tool_execute_sql_query,
    "get_schema": _tool_get_schema,
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


# ── REST endpoint: GET /mcp/uat/{pth}/results ──

@router.get("/mcp/uat/{pth}/results")
async def get_uat_results_by_pth_rest(pth: str):
    """Read-only REST endpoint for CAI to fetch UAT results by PTH. No auth required."""
    result = _tool_get_uat_results_by_pth({"pth": pth})
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
