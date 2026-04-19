"""
MP47 REQ-085: Self-documenting MCP tool inventory.

- GET  /api/mcp-tool-inventory      — merged live + curated inventory
- GET  /api/mcp-tool-metadata       — admin list (CRUD source of truth)
- POST /api/mcp-tool-metadata       — upsert a row
- DELETE /api/mcp-tool-metadata/{server}/{tool_name}
"""

import logging
from typing import List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import execute_query

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────────────

def _metapm_live_tool_names() -> List[str]:
    """Live list of MetaPM MCP tools — enumerated from the TOOLS registry."""
    try:
        from app.api.mcp_tools import TOOLS  # type: ignore
        return [t["name"] for t in TOOLS if isinstance(t, dict) and t.get("name")]
    except Exception as e:
        logger.warning(f"MetaPM live tool enumeration failed: {e}")
        return []


def _portfolio_rag_live_tool_names() -> Optional[List[str]]:
    """Best-effort live query of Portfolio RAG tools/list. Returns None on error."""
    url = "https://portfolio-rag-57478301787.us-central1.run.app/mcp/tools/list"
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(url)
            if r.status_code != 200:
                return None
            data = r.json()
            tools = data.get("tools") or data.get("result", {}).get("tools") or []
            names = [t["name"] for t in tools if isinstance(t, dict) and t.get("name")]
            return names or None
    except Exception as e:
        logger.info(f"Portfolio RAG live tools/list unreachable (falling back to curated): {e}")
        return None


def _load_curated() -> dict:
    """Return {(tool_name, server): row} for every curated metadata row."""
    rows = execute_query(
        "SELECT tool_name, server, category, when_to_use, forbidden_uses, gotchas, updated_at "
        "FROM mcp_tool_metadata",
        fetch="all"
    ) or []
    return {(r["tool_name"], r["server"]): r for r in rows}


def _merge_server(server: str, live_names: Optional[List[str]], curated: dict) -> dict:
    """Produce one server block in the response."""
    curated_rows = [
        r for (t, s), r in curated.items() if s == server
    ]
    curated_names = {r["tool_name"] for r in curated_rows}

    if live_names is None:
        source = "curated-only"
        all_names = sorted(curated_names)
    else:
        source = "live" if live_names else "curated-only"
        all_names = sorted(set(live_names) | curated_names)

    tools_out = []
    for name in all_names:
        row = curated.get((name, server))
        tools_out.append({
            "tool_name": name,
            "live": (live_names is not None and name in (live_names or [])),
            "curated": row is not None,
            "category": row["category"] if row else None,
            "when_to_use": row["when_to_use"] if row else None,
            "forbidden_uses": row["forbidden_uses"] if row else None,
            "gotchas": row["gotchas"] if row else None,
        })
    return {"name": server, "source": source, "tools": tools_out, "count": len(tools_out)}


def _build_inventory_impl() -> dict:
    curated = _load_curated()

    metapm_live = _metapm_live_tool_names()
    rag_live = _portfolio_rag_live_tool_names()

    servers = [
        _merge_server("metapm", metapm_live, curated),
        _merge_server("portfolio-rag", rag_live, curated),
        _merge_server("gmail", None, curated),
        _merge_server("calendar", None, curated),
        _merge_server("drive", None, curated),
    ]

    total = sum(s["count"] for s in servers)
    return {"servers": servers, "total_tools": total}


# ── Public HTTP endpoint ───────────────────────────────────────────────────

@router.get("/api/mcp-tool-inventory")
def mcp_tool_inventory_http():
    """Merged live + curated inventory of every MCP tool CC may call."""
    return _build_inventory_impl()


# Alias for MCP tool callers — same impl (sync, safe to call from any context)
def get_tool_inventory_impl() -> dict:
    return _build_inventory_impl()


# ── Admin CRUD ─────────────────────────────────────────────────────────────

class ToolMetadataUpsert(BaseModel):
    tool_name: str
    server: str
    category: str
    when_to_use: Optional[str] = None
    forbidden_uses: Optional[str] = None
    gotchas: Optional[str] = None


def _require_api_key(request: Request):
    key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    expected = settings.MCP_API_KEY or ""
    if not key or key != expected:
        raise HTTPException(status_code=403, detail="API key required")


@router.get("/api/mcp-tool-metadata")
async def list_tool_metadata():
    rows = execute_query(
        "SELECT tool_name, server, category, when_to_use, forbidden_uses, gotchas, "
        "       updated_at, updated_by "
        "FROM mcp_tool_metadata ORDER BY server, tool_name",
        fetch="all"
    ) or []
    return {
        "count": len(rows),
        "rows": [
            {
                "tool_name": r["tool_name"],
                "server": r["server"],
                "category": r["category"],
                "when_to_use": r.get("when_to_use"),
                "forbidden_uses": r.get("forbidden_uses"),
                "gotchas": r.get("gotchas"),
                "updated_at": str(r.get("updated_at") or ""),
                "updated_by": r.get("updated_by") or "",
                "needs_curation": not r.get("when_to_use"),
            }
            for r in rows
        ],
    }


@router.post("/api/mcp-tool-metadata")
async def upsert_tool_metadata(body: ToolMetadataUpsert, request: Request):
    _require_api_key(request)
    exists = execute_query(
        "SELECT COUNT(*) as cnt FROM mcp_tool_metadata WHERE tool_name = ? AND server = ?",
        (body.tool_name, body.server), fetch="one"
    )
    if exists and exists["cnt"] > 0:
        execute_query(
            "UPDATE mcp_tool_metadata SET category = ?, when_to_use = ?, "
            "forbidden_uses = ?, gotchas = ?, updated_at = GETUTCDATE(), updated_by = 'PL' "
            "WHERE tool_name = ? AND server = ?",
            (body.category, body.when_to_use, body.forbidden_uses, body.gotchas,
             body.tool_name, body.server), fetch="none"
        )
        action = "updated"
    else:
        execute_query(
            "INSERT INTO mcp_tool_metadata "
            "(tool_name, server, category, when_to_use, forbidden_uses, gotchas, updated_by) "
            "VALUES (?, ?, ?, ?, ?, ?, 'PL')",
            (body.tool_name, body.server, body.category,
             body.when_to_use, body.forbidden_uses, body.gotchas), fetch="none"
        )
        action = "inserted"
    return {"action": action, "tool_name": body.tool_name, "server": body.server}


@router.delete("/api/mcp-tool-metadata/{server}/{tool_name}")
async def delete_tool_metadata(server: str, tool_name: str, request: Request):
    _require_api_key(request)
    execute_query(
        "DELETE FROM mcp_tool_metadata WHERE tool_name = ? AND server = ?",
        (tool_name, server), fetch="none"
    )
    return {"deleted": True, "tool_name": tool_name, "server": server}
