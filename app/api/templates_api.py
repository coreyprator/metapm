"""
MP47 REQ-082: Templates API.

Serves template content and metadata from the `templates` SQL table.
MP49 REQ-086: Adds admin-authenticated PUT for content/questions editing
with automatic version bumping (1.0 → 1.1 → 1.2 …).
"""

import json
import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api.mcp import verify_api_key
from app.core.database import execute_query

logger = logging.getLogger(__name__)
router = APIRouter()


class TemplateSummary(BaseModel):
    id: str
    name: str
    version: str
    display_order: int


class TemplateDetail(BaseModel):
    id: str
    name: str
    version: str
    content_md: str
    questions: List[dict]
    display_order: int


@router.get("/api/templates", response_model=List[TemplateSummary])
async def list_templates():
    rows = execute_query(
        "SELECT id, name, version, display_order FROM templates ORDER BY display_order, id",
        fetch="all"
    ) or []
    return [
        TemplateSummary(
            id=r["id"],
            name=r["name"],
            version=r.get("version") or "1.0",
            display_order=r.get("display_order") or 0,
        )
        for r in rows
    ]


@router.get("/api/templates/{template_id}", response_model=TemplateDetail)
async def get_template(template_id: str, v: Optional[str] = None):
    """Return a single template. The optional ?v= query is honored for future
    historical versioning — today it is validated for format but the current
    row is always served."""
    row = execute_query(
        "SELECT id, name, version, content_md, questions_json, display_order "
        "FROM templates WHERE id = ?",
        (template_id,), fetch="one"
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    try:
        questions = json.loads(row.get("questions_json") or "[]")
    except (ValueError, TypeError):
        questions = []
    return TemplateDetail(
        id=row["id"],
        name=row["name"],
        version=row.get("version") or "1.0",
        content_md=row.get("content_md") or "",
        questions=questions,
        display_order=row.get("display_order") or 0,
    )


# ── MP49 REQ-086: Admin template editing ──

class TemplateUpdate(BaseModel):
    content_md: str
    questions_json: Optional[Any] = None  # accepts list (preferred) or JSON string


def _bump_version(current: str) -> str:
    """1.0 → 1.1 → 1.2 … 1.9 → 1.10. Majors are left alone.

    Any version that can't be parsed (e.g. 'draft') is treated as 1.0 → 1.1.
    """
    try:
        major_str, minor_str = (current or "1.0").split(".", 1)
        return f"{int(major_str)}.{int(minor_str) + 1}"
    except (ValueError, AttributeError):
        return "1.1"


@router.put("/api/templates/{template_id}", response_model=TemplateDetail)
async def update_template(
    template_id: str,
    body: TemplateUpdate,
    _auth: bool = Depends(verify_api_key),
):
    """Admin PUT — replace content_md / questions_json and auto-bump version.

    questions_json is accepted either as a list/dict or a pre-serialized
    JSON string (the DB column stores the string form).
    """
    current = execute_query(
        "SELECT id, version FROM templates WHERE id = ?",
        (template_id,), fetch="one"
    )
    if not current:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    if body.questions_json is None:
        q_json_str = None
    elif isinstance(body.questions_json, str):
        try:
            json.loads(body.questions_json)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="questions_json is not valid JSON")
        q_json_str = body.questions_json
    else:
        q_json_str = json.dumps(body.questions_json)

    new_version = _bump_version(current.get("version") or "1.0")

    if q_json_str is None:
        execute_query(
            "UPDATE templates SET content_md = ?, version = ?, updated_at = GETUTCDATE() "
            "WHERE id = ?",
            (body.content_md, new_version, template_id),
            fetch="none",
        )
    else:
        execute_query(
            "UPDATE templates SET content_md = ?, questions_json = ?, version = ?, "
            "updated_at = GETUTCDATE() WHERE id = ?",
            (body.content_md, q_json_str, new_version, template_id),
            fetch="none",
        )

    logger.info(f"Template {template_id} updated to version {new_version}")
    return await get_template(template_id)


@router.get("/template-admin")
async def template_admin_page():
    """BA48: serve the admin editor HTML from /static/template_admin.html."""
    import os
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(here, "static", "template_admin.html")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="template_admin.html missing")
    return FileResponse(path, media_type="text/html")
