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
        "SELECT id, project, version, title, task FROM mcp_handoffs WHERE id = ?",
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
    feature_title = handoff.get("title") or handoff.get("task") or None

    # 3. Generate test cases
    test_cases = generate_test_cases(
        work_items=work_item_details,
        project=project,
        version=version,
        cai_review=body.cai_review,
        deploy_url=body.deploy_url
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
            linked_requirements=linked_requirements,
            feature_title=feature_title
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
            linked_requirements=linked_requirements,
            feature_title=feature_title
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
    import re as _re
    where_clauses = []
    params = []

    if handoff_id:
        where_clauses.append("u.handoff_id = ?")
        params.append(handoff_id)
    if project:
        where_clauses.append("u.project = ?")
        params.append(project)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Get total count
    count_row = execute_query(f"""
        SELECT COUNT(*) as total FROM uat_pages u WHERE {where_sql}
    """, tuple(params), fetch="one")
    total = count_row["total"] if count_row else 0

    rows = execute_query(f"""
        SELECT u.id, u.handoff_id, u.project, u.sprint_code, u.version, u.status,
               u.test_cases_json, u.created_at, u.pth,
               h.title as handoff_title, h.task as handoff_task
        FROM uat_pages u
        LEFT JOIN mcp_handoffs h ON u.handoff_id = h.id
        WHERE {where_sql}
        ORDER BY u.created_at DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """, (*params, offset, limit), fetch="all")

    results = []
    for row in (rows or []):
        test_cases = json.loads(row["test_cases_json"]) if row.get("test_cases_json") else []
        title = row.get("handoff_title") or row.get("handoff_task") or f"UAT - {row['project']} v{row.get('version','?')}"
        # Extract PTH from title or from stored pth column
        pth = row.get("pth")
        if not pth:
            m = _re.search(r'PTH-([A-Z0-9]{4})', title or '')
            pth = m.group(1) if m else None
        results.append({
            "uat_id": str(row["id"]),
            "handoff_id": str(row["handoff_id"]),
            "project": row["project"],
            "sprint_code": row.get("sprint_code"),
            "version": row.get("version"),
            "status": row["status"],
            "test_count": len(test_cases),
            "created_at": str(row["created_at"]),
            "uat_url": f"https://metapm.rentyourcio.com/uat/{row['id']}",
            "title": title,
            "pth": pth
        })

    return {"pages": results, "total": total, "count": len(results), "limit": limit, "offset": offset}


# ── GET /lessons/{id} — Standalone lesson detail page ──────────────────

@router.get("/lessons/{lesson_id}")
async def serve_lesson_page(lesson_id: str):
    """Standalone lesson detail page with Approve/Reject buttons."""
    from html import escape
    row = execute_query(
        "SELECT * FROM lessons_learned WHERE id = ?",
        (lesson_id,), fetch="one"
    )
    if not row:
        raise HTTPException(404, f"Lesson {lesson_id} not found")

    status = row["status"]
    status_color = {"draft": "#d97706", "approved": "#3b82f6", "applied": "#22c55e", "rejected": "#ef4444"}.get(status, "#6b7280")
    cat_color = {"process": "#f97316", "technical": "#a855f7", "architecture": "#06b6d4", "quality": "#ef4444"}.get(row["category"], "#6b7280")

    actions = ""
    if status in ("draft", "approved"):
        actions = f'''
        <div class="lesson-actions" id="lesson-actions" style="display:flex;gap:12px;justify-content:center;margin-top:24px">
            <button onclick="approveLesson('{escape(lesson_id)}')" style="background:#22c55e;color:white;padding:12px 32px;border-radius:8px;font-size:1rem;font-weight:600;border:none;cursor:pointer">Approve</button>
            <button onclick="rejectLesson('{escape(lesson_id)}')" style="background:#991b1b;color:white;padding:12px 32px;border-radius:8px;font-size:1rem;font-weight:600;border:none;cursor:pointer">Reject</button>
        </div>
        <div id="action-result" style="display:none;text-align:center;margin-top:24px;font-size:1.1rem;font-weight:600"></div>
        <script>
        async function approveLesson(id) {{
            const res = await fetch('/api/lessons/' + id + '/approve', {{method: 'POST'}});
            if (res.ok) {{
                document.getElementById('lesson-actions').style.display = 'none';
                const r = document.getElementById('action-result');
                r.textContent = 'Lesson approved.';
                r.style.color = '#22c55e';
                r.style.display = 'block';
            }}
        }}
        async function rejectLesson(id) {{
            const res = await fetch('/api/lessons/' + id + '/reject', {{method: 'POST'}});
            if (res.ok) {{
                document.getElementById('lesson-actions').style.display = 'none';
                const r = document.getElementById('action-result');
                r.textContent = 'Lesson rejected.';
                r.style.color = '#ef4444';
                r.style.display = 'block';
            }}
        }}
        </script>'''

    html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(lesson_id)} - Lesson Detail</title>
<style>
body{{font-family:-apple-system,sans-serif;max-width:700px;margin:40px auto;padding:20px;background:#1a1a2e;color:#e5e5e5;line-height:1.6}}
.card{{background:#252538;border-radius:12px;padding:30px;margin-bottom:16px}}
h1{{font-size:1.5rem;margin-bottom:16px}}
.badge{{display:inline-block;padding:3px 10px;border-radius:4px;font-size:0.8rem;font-weight:600;margin-right:6px}}
.lesson-text{{background:#1e1e32;padding:20px;border-radius:8px;margin:16px 0;font-size:0.95rem;line-height:1.7}}
.meta{{font-size:0.85rem;color:#9ca3af;margin-top:12px}}
.meta span{{margin-right:16px}}
a.back{{color:#60a5fa;text-decoration:none;font-weight:600;display:inline-block;margin-top:20px}}
a.back:hover{{text-decoration:underline}}
</style></head>
<body>
<div class="card">
    <h1>{escape(lesson_id)}</h1>
    <div>
        <span class="badge" style="background:{status_color};color:white">{escape(status.upper())}</span>
        <span class="badge" style="background:{cat_color};color:white">{escape(row["category"])}</span>
        <span class="badge" style="background:#374151;color:#d1d5db">{escape(row["project"])}</span>
        <span class="badge" style="background:#374151;color:#d1d5db">-&gt; {escape(row["target"])}</span>
    </div>
    <div class="lesson-text">{escape(row["lesson"])}</div>
    <div class="meta">
        <span>Proposed by: {escape(row.get("proposed_by","?"))}</span>
        {f'<span>Source: {escape(row.get("source_sprint",""))}</span>' if row.get("source_sprint") else ''}
        <span>Created: {str(row.get("created_at",""))[:10]}</span>
        {f'<span>Applied in: {escape(row.get("applied_in_sprint",""))}</span>' if row.get("applied_in_sprint") else ''}
    </div>
    {actions}
    <a class="back" href="/static/dashboard.html">&larr; Back to Dashboard</a>
</div>
</body></html>'''
    return HTMLResponse(html)


# ── POST /api/uat/verify — Handoff verification endpoint (MP-VERIFY-001) ──

class VerifyRequest(BaseModel):
    handoff_id: str

@router.post("/api/uat/verify")
async def verify_handoff_endpoint(body: VerifyRequest):
    """Verify endpoints claimed in a handoff's evidence."""
    from app.services.verification_service import verify_handoff
    result = await verify_handoff(body.handoff_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.get("/api/uat/verify/{handoff_id}")
async def get_verification_status(handoff_id: str):
    """Get the latest verification result for a handoff."""
    row = execute_query("""
        SELECT verification_status, results_json, verified_at
        FROM handoff_verifications
        WHERE handoff_id = ?
        ORDER BY created_at DESC
    """, (handoff_id,), fetch="one")
    if not row:
        return {"handoff_id": handoff_id, "verification_status": "none", "results": []}
    results = json.loads(row["results_json"]) if row.get("results_json") else []
    return {
        "handoff_id": handoff_id,
        "verification_status": row["verification_status"],
        "results": results,
        "verified_at": str(row["verified_at"]) if row.get("verified_at") else None
    }
