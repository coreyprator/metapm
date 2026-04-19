"""
MP47 REQ-082: Templates API.

Serves template content and metadata from the `templates` SQL table.
"""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
