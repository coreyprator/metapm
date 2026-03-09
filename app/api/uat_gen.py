"""
UAT Generation API — MP-UAT-GEN
Endpoints for generating and serving UAT pages.
"""
import json
import logging
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.core.database import execute_query
from app.services.uat_generator import generate_test_cases, render_uat_html

logger = logging.getLogger(__name__)
router = APIRouter()


# ---- Pydantic Models ----

class UATGenerateRequest(BaseModel):
    handoff_id: str
    work_items: List[str] = Field(default_factory=list, description="Requirement codes to include")
    project: str
    version: Optional[str] = None
    deploy_url: Optional[str] = None
    sprint_code: Optional[str] = None
    pth: Optional[str] = None
    cai_review: Optional[dict] = None


class UATGenerateResponse(BaseModel):
    uat_id: str
    uat_url: str
    test_count: int
    status: str = "ready"


class UATPageSummary(BaseModel):
    uat_id: str
    handoff_id: str
    project: str
    sprint_code: Optional[str] = None
    version: Optional[str] = None
    status: str
    test_count: int
    created_at: str
    uat_url: str


# ---- Endpoints ----

@router.post("/api/uat/generate", response_model=UATGenerateResponse)
async def generate_uat(body: UATGenerateRequest):
    """Generate a UAT page from handoff and requirements data."""

    # 1. Validate handoff exists in mcp_handoffs
    handoff = execute_query(
        "SELECT id, project, version, title FROM mcp_handoffs WHERE id = ?",
        (body.handoff_id,), fetch="one"
    )
    if not handoff:
        raise HTTPException(404, f"Handoff {body.handoff_id} not found")

    # 2. Fetch requirement details for work items
    work_item_details = []
    linked_requirements = []
    for code in body.work_items:
        req = execute_query(
            "SELECT code, title, description, type FROM roadmap_requirements WHERE code = ?",
            (code,), fetch="one"
        )
        if req:
            work_item_details.append({
                "code": req["code"],
                "title": req["title"],
                "description": req.get("description", ""),
                "type": req.get("type", "feature")
            })
            linked_requirements.append(req["code"])

    # Use handoff version if not provided
    version = body.version or handoff.get("version") or "?"
    project = body.project or handoff.get("project", "unknown")

    # 3. Generate test cases
    test_cases = generate_test_cases(
        work_items=work_item_details,
        project=project,
        version=version,
        cai_review=body.cai_review
    )

    # 4. Check for existing uat_pages record for this handoff (upsert)
    existing = execute_query(
        "SELECT id FROM uat_pages WHERE handoff_id = ?",
        (body.handoff_id,), fetch="one"
    )

    if existing:
        uat_id = str(existing["id"])
        # Re-render HTML with new data
        html = render_uat_html(
            uat_id=uat_id,
            project=project,
            sprint_code=body.sprint_code,
            pth=body.pth,
            version=version,
            deploy_url=body.deploy_url,
            handoff_id=body.handoff_id,
            test_cases=test_cases,
            linked_requirements=linked_requirements
        )
        execute_query("""
            UPDATE uat_pages
            SET test_cases_json = ?, cai_review_json = ?, html_content = ?,
                sprint_code = ?, pth = ?, version = ?, deploy_url = ?,
                status = 'ready'
            WHERE id = ?
        """, (
            json.dumps(test_cases),
            json.dumps(body.cai_review) if body.cai_review else None,
            html,
            body.sprint_code,
            body.pth,
            version,
            body.deploy_url,
            uat_id
        ), fetch="none")
        logger.info(f"Updated UAT page {uat_id} for handoff {body.handoff_id}")
    else:
        # Create new — get the ID via OUTPUT
        # First render with a placeholder, then update
        result = execute_query("""
            INSERT INTO uat_pages (handoff_id, project, sprint_code, pth, version,
                                   deploy_url, test_cases_json, cai_review_json,
                                   html_content)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'placeholder')
        """, (
            body.handoff_id,
            project,
            body.sprint_code,
            body.pth,
            version,
            body.deploy_url,
            json.dumps(test_cases),
            json.dumps(body.cai_review) if body.cai_review else None,
        ), fetch="one")

        if not result:
            raise HTTPException(500, "Failed to create UAT page")

        uat_id = str(result["id"])

        # Now render with the real ID and update
        html = render_uat_html(
            uat_id=uat_id,
            project=project,
            sprint_code=body.sprint_code,
            pth=body.pth,
            version=version,
            deploy_url=body.deploy_url,
            handoff_id=body.handoff_id,
            test_cases=test_cases,
            linked_requirements=linked_requirements
        )
        execute_query(
            "UPDATE uat_pages SET html_content = ? WHERE id = ?",
            (html, uat_id), fetch="none"
        )
        logger.info(f"Created UAT page {uat_id} for handoff {body.handoff_id}")

    uat_url = f"https://metapm.rentyourcio.com/uat/{uat_id}"
    return UATGenerateResponse(
        uat_id=uat_id,
        uat_url=uat_url,
        test_count=len(test_cases),
        status="ready"
    )


@router.get("/uat/{uat_id}")
async def serve_uat_page(uat_id: str):
    """Serve the UAT HTML page."""
    page = execute_query(
        "SELECT html_content, status FROM uat_pages WHERE id = ?",
        (uat_id,), fetch="one"
    )
    if not page:
        raise HTTPException(404, "UAT page not found")

    # Mark as in_progress on first view
    if page["status"] == "ready":
        execute_query(
            "UPDATE uat_pages SET status = 'in_progress' WHERE id = ?",
            (uat_id,), fetch="none"
        )

    return HTMLResponse(content=page["html_content"])


@router.get("/api/uat/pages")
async def list_uat_pages(
    handoff_id: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0)
):
    """List UAT pages with optional filters."""
    where_clauses = []
    params = []

    if handoff_id:
        where_clauses.append("handoff_id = ?")
        params.append(handoff_id)
    if project:
        where_clauses.append("project = ?")
        params.append(project)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    rows = execute_query(f"""
        SELECT id, handoff_id, project, sprint_code, version, status,
               test_cases_json, created_at
        FROM uat_pages
        WHERE {where_sql}
        ORDER BY created_at DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """, (*params, offset, limit), fetch="all")

    results = []
    for row in (rows or []):
        test_cases = json.loads(row["test_cases_json"]) if row.get("test_cases_json") else []
        results.append({
            "uat_id": str(row["id"]),
            "handoff_id": str(row["handoff_id"]),
            "project": row["project"],
            "sprint_code": row.get("sprint_code"),
            "version": row.get("version"),
            "status": row["status"],
            "test_count": len(test_cases),
            "created_at": str(row["created_at"]),
            "uat_url": f"https://metapm.rentyourcio.com/uat/{row['id']}"
        })

    return {"pages": results, "count": len(results)}
