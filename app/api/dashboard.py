"""
MetaPM Dashboard API — C2-C8 endpoints
Sprint: MP58C-DASHBOARD-PRODUCTION-MEGA-001
"""
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.mcp import verify_api_key_or_pl_session
from app.core.database import execute_query

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── helpers ──────────────────────────────────────────────────────────────────

def _safe_str(v) -> Optional[str]:
    return str(v) if v is not None else None


def _row_to_item(row: dict) -> dict:
    return {
        "id":          _safe_str(row.get("id")),
        "project_id":  _safe_str(row.get("project_id")),
        "code":        row.get("code"),
        "title":       row.get("title"),
        "description": row.get("description"),
        "type":        row.get("type"),
        "priority":    row.get("priority"),
        "status":      row.get("status"),
        "pth":         row.get("pth"),
        "sprint_id":   _safe_str(row.get("sprint_id")),
        "target_version": row.get("target_version"),
        "created_at":  _safe_str(row.get("created_at")),
        "updated_at":  _safe_str(row.get("updated_at")),
    }


def _stale_hours(governance_kv: list, item: dict) -> bool:
    """Return True if item is stale based on governance_kv thresholds."""
    kv = {g["key"]: g["value"] for g in governance_kv}
    typ = item.get("type", "task")
    threshold_key = f"stale_hours_{typ}"
    default_hours = {
        "bug": 48, "feature": 168, "task": 96, "enhancement": 168,
    }
    try:
        hours = int(kv.get(threshold_key, default_hours.get(typ, 96)))
    except (ValueError, TypeError):
        hours = 96
    updated = item.get("updated_at")
    if not updated:
        return False
    try:
        dt = datetime.fromisoformat(str(updated).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        return age_h > hours
    except Exception:
        return False


def _age_hours(updated_at) -> float:
    if not updated_at:
        return 0
    try:
        dt = datetime.fromisoformat(str(updated_at).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    except Exception:
        return 0


# ─── C2: bootstrap ────────────────────────────────────────────────────────────

@router.get("/api/bootstrap", tags=["Dashboard"])
async def get_bootstrap(project_id: Optional[str] = Query(default=None)):
    """
    C2: Bootstrap — returns all static/semi-static data the SPA needs on load.
    projects, types, statuses, categories, templates, tools, governance_kv,
    lifecycle_counts, in_flight, version.
    """
    try:
        # Projects
        proj_rows = execute_query(
            "SELECT id, name, code, category_id, status FROM roadmap_projects ORDER BY name",
            fetch="all"
        ) or []
        projects = [{"id": _safe_str(r["id"]), "name": r["name"], "code": r.get("code"),
                     "category_id": _safe_str(r.get("category_id")), "status": r.get("status")} for r in proj_rows]

        # Categories
        cat_rows = execute_query(
            "SELECT id, name, NULL as color FROM roadmap_categories ORDER BY name",
            fetch="all"
        ) or []
        categories = [{"id": _safe_str(r["id"]), "name": r["name"], "color": r.get("color")} for r in cat_rows]

        # Governance KV
        gov_rows = execute_query(
            "SELECT key_name, value_json, updated_at FROM governance_kv ORDER BY key_name",
            fetch="all"
        ) or []
        governance = [{"key": r["key_name"], "value": r["value_json"],
                       "updated_at": _safe_str(r.get("updated_at"))} for r in gov_rows]

        # Templates (summary — no body to keep payload small)
        tpl_rows = execute_query(
            "SELECT id, name, version, display_order FROM templates ORDER BY display_order, name",
            fetch="all"
        ) or []
        templates = [{"id": _safe_str(r["id"]), "name": r["name"],
                      "version": r.get("version"), "display_order": r.get("display_order")} for r in tpl_rows]

        # MCP tool metadata
        tool_rows = execute_query(
            "SELECT tool_name, server, category, when_to_use, forbidden_uses, gotchas, updated_at "
            "FROM mcp_tool_metadata ORDER BY category, tool_name",
            fetch="all"
        ) or []
        tools = [{
            "id": f"{r.get('server','')}.{r.get('tool_name','')}",
            "name": r.get("tool_name"), "server": r.get("server"),
            "category": r.get("category"), "when": r.get("when_to_use"),
            "desc": r.get("forbidden_uses"), "sig": None,
            "updated_at": _safe_str(r.get("updated_at")),
        } for r in tool_rows]

        # Lifecycle counts (by project, by status-phase)
        # Build a count map: project_id → {phase: count}
        proj_filter_sql = ""
        proj_filter_params: tuple = ()
        if project_id:
            proj_filter_sql = "WHERE r.project_id = ?"
            proj_filter_params = (project_id,)

        # We use status as a proxy for phase — frontend maps status → phase
        lc_rows = execute_query(
            f"""SELECT r.project_id, r.status, COUNT(*) as cnt
                FROM roadmap_requirements r
                {proj_filter_sql}
                GROUP BY r.project_id, r.status""",
            proj_filter_params if proj_filter_params else (),
            fetch="all"
        ) or []

        lifecycle_counts: dict = {}
        for r in lc_rows:
            pid = _safe_str(r["project_id"])
            status = r["status"]
            cnt = r["cnt"]
            if pid not in lifecycle_counts:
                lifecycle_counts[pid] = {}
            lifecycle_counts[pid][status] = lifecycle_counts[pid].get(status, 0) + cnt

        # In-flight (items needing PL attention)
        inflight = _compute_in_flight(governance, project_id)

        # Types and statuses are frontend-only lookups (not stored in DB as lookup tables)
        # They come from the React defaults; we return an empty array here and the frontend
        # falls back to its DEFAULT_TYPES / DEFAULT_STATUSES constants.
        types = []
        statuses = []

        from app.core.config import settings as _s
        version = getattr(_s, "VERSION", "3.6.0")

        return {
            "projects":        projects,
            "categories":      categories,
            "governance":      governance,
            "templates":       templates,
            "tools":           tools,
            "lifecycle_counts": lifecycle_counts,
            "in_flight":       inflight,
            "types":           types,
            "statuses":        statuses,
            "version":         version,
        }

    except Exception as e:
        logger.error(f"Bootstrap error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Bootstrap failed: {e}")


# ─── C3: items list ───────────────────────────────────────────────────────────

@router.get("/api/items", tags=["Dashboard"])
async def list_items(
    project_id: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
):
    """C3: Paginated items list with optional full-text / filter."""
    try:
        clauses = []
        params: list = []

        if project_id:
            clauses.append("r.project_id = ?")
            params.append(project_id)
        if type:
            clauses.append("r.type = ?")
            params.append(type)
        if status:
            clauses.append("r.status = ?")
            params.append(status)
        if q:
            # Parameterised LIKE (CONTAINS not available without full-text index)
            like = f"%{q}%"
            clauses.append("(r.code LIKE ? OR r.title LIKE ? OR r.description LIKE ?)")
            params += [like, like, like]

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        # params for count query
        count_row = execute_query(
            f"SELECT COUNT(*) as cnt FROM roadmap_requirements r {where}",
            tuple(params),
            fetch="one"
        ) or {}
        total = count_row.get("cnt", 0)

        params_page = params + [offset, limit]
        rows = execute_query(
            f"""SELECT r.id, r.project_id, r.code, r.title, r.description,
                       r.type, r.priority, r.status, r.pth, r.sprint_id,
                       r.target_version, r.created_at, r.updated_at
                FROM roadmap_requirements r
                {where}
                ORDER BY r.updated_at DESC
                OFFSET ? ROWS FETCH NEXT ? ROWS ONLY""",
            tuple(params_page),
            fetch="all"
        ) or []

        return {
            "items": [_row_to_item(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"items list error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ─── C4: single item ──────────────────────────────────────────────────────────

@router.get("/api/items/{code}", tags=["Dashboard"])
async def get_item(code: str):
    """C4: Single item by code, with history + UAT walks if applicable."""
    row = execute_query(
        """SELECT r.id, r.project_id, r.code, r.title, r.description,
                  r.type, r.priority, r.status, r.pth, r.sprint_id,
                  r.target_version, r.created_at, r.updated_at
           FROM roadmap_requirements r
           WHERE r.code = ?""",
        (code,), fetch="one"
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"Item {code} not found")

    item = _row_to_item(row)

    # History
    history_rows = execute_query(
        """SELECT ph.from_status, ph.to_status, ph.changed_by, ph.trigger,
                  ph.success, ph.blocked_reason, ph.changed_at
           FROM prompt_history ph
           JOIN cc_prompts p ON p.id = ph.prompt_id
           JOIN roadmap_requirements r ON r.id = p.requirement_id
           WHERE r.code = ?
           ORDER BY ph.changed_at DESC""",
        (code,), fetch="all"
    ) or []
    item["history"] = [
        {
            "from_status": h["from_status"], "to_status": h["to_status"],
            "changed_by": h["changed_by"], "trigger": h["trigger"],
            "success": bool(h["success"]) if h["success"] is not None else None,
            "blocked_reason": h.get("blocked_reason"),
            "created_at": _safe_str(h.get("changed_at")),
        }
        for h in history_rows
    ]

    # UAT walks (if pth set) — from uat_bv_items joined via uat_pages
    if item.get("pth"):
        uat_rows = execute_query(
            """SELECT u.bv_id, u.title as bv_title, u.classification,
                      u.cc_result, u.cc_evidence as actual_result, u.updated_at
               FROM uat_bv_items u
               JOIN uat_pages p ON p.id = u.spec_id
               WHERE p.pth = ?
               ORDER BY u.updated_at DESC""",
            (item["pth"],), fetch="all"
        ) or []
        item["uat_walks"] = [
            {
                "bv_code": _safe_str(u.get("bv_id")),
                "bv_title": u.get("bv_title"),
                "classification": u.get("classification"),
                "passed": (u.get("cc_result") == "pass") if u.get("cc_result") else None,
                "actual_result": u.get("actual_result"),
                "created_at": _safe_str(u.get("updated_at")),
            }
            for u in uat_rows
        ]
    else:
        item["uat_walks"] = []

    return item


# ─── C5: in-flight ────────────────────────────────────────────────────────────

def _compute_in_flight(governance: list, project_id: Optional[str]) -> list:
    """Items currently blocked on PL: status in (cc_complete, uat_ready, in_uat)."""
    blocked_statuses = ("cc_complete", "uat_ready", "in_uat", "needs_fixes")
    placeholders = ",".join("?" * len(blocked_statuses))

    extra_clause = ""
    extra_params: tuple = ()
    if project_id:
        extra_clause = "AND r.project_id = ?"
        extra_params = (project_id,)

    rows = execute_query(
        f"""SELECT r.code, r.type, r.status, r.project_id, r.updated_at
            FROM roadmap_requirements r
            WHERE r.status IN ({placeholders})
            {extra_clause}
            ORDER BY r.updated_at ASC""",
        blocked_statuses + extra_params,
        fetch="all"
    ) or []

    result = []
    for r in rows:
        age_h = _age_hours(r.get("updated_at"))
        stale = _stale_hours(governance, r)
        result.append({
            "code":       r["code"],
            "kind":       r["status"],
            "type":       r["type"],
            "project":    _safe_str(r.get("project_id")),
            "age_h":      round(age_h),
            "stale":      stale,
        })
    return result


@router.get("/api/in_flight", tags=["Dashboard"])
async def get_in_flight(project_id: Optional[str] = Query(default=None)):
    """C5: Items currently blocked on PL with stale computation."""
    try:
        gov_rows = execute_query(
            "SELECT key_name, value_json FROM governance_kv",
            fetch="all"
        ) or []
        governance = [{"key": r["key_name"], "value": r["value_json"]} for r in gov_rows]
        return _compute_in_flight(governance, project_id)
    except Exception as e:
        logger.error(f"in_flight error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ─── C6: template patch ───────────────────────────────────────────────────────

class TemplatePatchPayload(BaseModel):
    body: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None


@router.patch("/api/templates/{template_id}", tags=["Dashboard"])
async def patch_template(
    template_id: str,
    payload: TemplatePatchPayload,
    _: bool = Depends(verify_api_key_or_pl_session),
):
    """C6: Patch a template body/name/category. Requires PL session or API key."""
    row = execute_query(
        "SELECT id, version FROM templates WHERE id = ?",
        (template_id,), fetch="one"
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    updates = []
    params = []
    if payload.body is not None:
        updates.append("content_md = ?")
        params.append(payload.body)
    if payload.name is not None:
        updates.append("name = ?")
        params.append(payload.name)
    if payload.category is not None:
        updates.append("category = ?")
        params.append(payload.category)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = GETUTCDATE()")
    params.append(template_id)

    execute_query(
        f"UPDATE templates SET {', '.join(updates)} WHERE id = ?",
        tuple(params), fetch="none"
    )
    logger.info(f"Template {template_id} patched: {list(payload.dict(exclude_none=True).keys())}")
    return {"ok": True, "id": template_id}


# ─── C7: governance KV patch ──────────────────────────────────────────────────

class GovernanceKVPatch(BaseModel):
    value: str


@router.patch("/api/governance/{key}", tags=["Dashboard"])
async def patch_governance_kv(
    key: str,
    payload: GovernanceKVPatch,
    _: bool = Depends(verify_api_key_or_pl_session),
):
    """C7: Update a governance_kv entry. Requires PL session or API key."""
    existing = execute_query(
        "SELECT key_name FROM governance_kv WHERE key_name = ?",
        (key,), fetch="one"
    )
    if not existing:
        raise HTTPException(status_code=404, detail=f"governance key '{key}' not found")

    execute_query(
        "UPDATE governance_kv SET value_json = ?, updated_at = GETUTCDATE() WHERE key_name = ?",
        (payload.value, key), fetch="none"
    )
    logger.info(f"governance_kv[{key}] = {payload.value!r}")
    return {"ok": True, "key": key, "value": payload.value}


# ─── C8: post item stub ───────────────────────────────────────────────────────

@router.post("/api/items", status_code=201, tags=["Dashboard"])
async def post_item(
    _: bool = Depends(verify_api_key_or_pl_session),
):
    """C8: STUB — item creation via dashboard is not implemented (BUG-102, P3).
    Use MCP post_requirement() from a CAI session instead."""
    raise HTTPException(
        status_code=501,
        detail="Item creation via dashboard UI is not implemented (BUG-102, P3). Use MCP post_requirement()."
    )
