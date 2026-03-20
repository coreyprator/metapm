"""
UAT Generation API — MP-UAT-GEN
Endpoints for generating and serving UAT pages.
"""
import json
import logging
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from app.core.database import execute_query
from app.services.uat_generator import generate_test_cases, render_uat_html
from app.schemas.mcp import UATResultsUpdate, BulkArchiveRequest

logger = logging.getLogger(__name__)
router = APIRouter()


def _render_fallback_uat(row: dict) -> str:
    """Render a minimal UAT results page from handoff/uat_results data.
    Used when no uat_pages record exists (e.g. direct-submit without generate)."""
    from html import escape
    project = escape(str(row.get("project", "Unknown")))
    version = escape(str(row.get("version", "?")))
    status = escape(str(row.get("status", "unknown")))
    total = row.get("total_tests", 0)
    passed = row.get("passed", 0)
    failed = row.get("failed", 0)
    tested_by = escape(str(row.get("tested_by", "unknown")))
    tested_at = escape(str(row.get("tested_at", "")))
    results_text = escape(str(row.get("results_text", "")))
    handoff_id = escape(str(row.get("handoff_id", "")))
    status_color = "#22c55e" if status == "passed" else "#ef4444" if status == "failed" else "#eab308"
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>UAT Results — {project} {version}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #1a1a2e; color: #e5e5e5; padding: 2rem; }}
.card {{ background: #252538; border-radius: 12px; padding: 2rem; max-width: 800px; margin: 0 auto; }}
h1 {{ color: #818cf8; margin-bottom: 0.5rem; }}
.status {{ display: inline-block; padding: 4px 12px; border-radius: 6px; background: {status_color}; color: #fff; font-weight: 600; }}
.meta {{ color: #9ca3af; margin: 1rem 0; }}
.results {{ background: #1a1a2e; padding: 1rem; border-radius: 8px; margin-top: 1rem; white-space: pre-wrap; }}
</style></head><body>
<div class="card">
<h1>{project} {version}</h1>
<span class="status">{status.upper()}</span>
<div class="meta">Tested by: {tested_by} | {tested_at}<br>Tests: {total} total, {passed} passed, {failed} failed<br>Handoff: {handoff_id}</div>
<div class="results">{results_text}</div>
</div></body></html>"""


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
async def serve_uat_page(request: Request, uat_id: str):
    """Serve the UAT HTML page.

    For cc_spec UATs: requires Google OAuth PL session (cprator@cbsware.com).
    For legacy UATs: no auth required (existing behavior).

    Lookup chain: uat_pages.id → uat_pages.handoff_id →
    uat_results.id→handoff_id→uat_pages → render fallback from handoff data.
    """
    from fastapi import Request as _Request
    # 1. Primary: uat_pages by id
    page = execute_query(
        "SELECT id, html_content, status, pth, spec_source, spec_data, test_cases_json FROM uat_pages WHERE id = ?",
        (uat_id,), fetch="one"
    )

    # Check for cc_spec auth BEFORE the legacy fallback chain
    if page and page.get("spec_source") == "cc_spec":
        from app.api.auth import is_pl_authenticated, get_session_email, render_login_required_page
        if not is_pl_authenticated(request):
            html = render_login_required_page(f"/uat/{uat_id}", uat_id)
            return HTMLResponse(content=html, status_code=200)
        # PL is authenticated — render interactive spec page
        # Fetch full row including general_notes and pl_submitted_at
        full_page = execute_query(
            "SELECT id, spec_data, test_cases_json, general_notes, pl_submitted_at, status FROM uat_pages WHERE id = ?",
            (uat_id,), fetch="one"
        ) or page
        from app.api.uat_spec import render_spec_uat_page
        email = get_session_email(request) or ""
        spec_data = json.loads(full_page.get("spec_data") or page.get("spec_data") or "{}") if (full_page.get("spec_data") or page.get("spec_data")) else {}
        tc_json = json.loads(full_page.get("test_cases_json") or page.get("test_cases_json") or "[]") if (full_page.get("test_cases_json") or page.get("test_cases_json")) else []
        # Strip to spec fields only (no result leakage for spec definition)
        spec_tests = [
            {"id": tc["id"], "title": tc["title"], "url": tc.get("url"),
             "steps": tc.get("steps", []), "expected": tc.get("expected")}
            for tc in tc_json
            if not tc.get("id", "").startswith("_")
        ]
        general_notes = full_page.get("general_notes") or ""
        is_submitted = bool(full_page.get("pl_submitted_at"))
        html = render_spec_uat_page(
            spec_id=uat_id,
            spec_data=spec_data,
            test_cases=spec_tests,
            current_results=tc_json,
            pl_email=email,
            general_notes=general_notes,
            is_submitted=is_submitted,
            spec_status=full_page.get("status", "in_progress"),
        )
        return HTMLResponse(content=html)

    # 2. Fallback: uat_pages by handoff_id
    if not page:
        page = execute_query(
            "SELECT id, html_content, status, pth FROM uat_pages WHERE handoff_id = ?",
            (uat_id,), fetch="one"
        )

    # 3. Fallback: uat_results.id → handoff_id → uat_pages
    if not page:
        uat_result = execute_query(
            "SELECT handoff_id FROM uat_results WHERE id = ?",
            (uat_id,), fetch="one"
        )
        if uat_result:
            page = execute_query(
                "SELECT id, html_content, status, pth FROM uat_pages WHERE handoff_id = ?",
                (uat_result["handoff_id"],), fetch="one"
            )

    # 4. Last resort: render minimal page from handoff/uat_results data
    if not page:
        fallback = execute_query("""
            SELECT u.id as result_id, u.status, u.total_tests, u.passed, u.failed,
                   u.tested_by, u.tested_at, u.results_text,
                   h.id as handoff_id, h.project, h.version
            FROM uat_results u
            JOIN mcp_handoffs h ON u.handoff_id = h.id
            WHERE u.id = ? OR h.id = ?
        """, (uat_id, uat_id), fetch="one")
        if fallback:
            return HTMLResponse(content=_render_fallback_uat(fallback))
        raise HTTPException(404, "UAT page not found")

    # Mark as in_progress on first view
    if page["status"] == "ready":
        execute_query(
            "UPDATE uat_pages SET status = 'in_progress' WHERE id = ?",
            (page["id"],), fetch="none"
        )

    html = page["html_content"]

    # MP-UAT-DASHBOARD-FIX-001: Inject pre-populate script into existing pages
    if 'loadSavedResults' not in html and '</script>' in html:
        prepopulate_js = """
        // Pre-populate saved results on page load (injected by serve endpoint)
        (async function loadSavedResults() {
            try {
                const pageId = UAT_CONFIG?.uat_page_id;
                if (!pageId) return;
                const res = await fetch(
                    'https://metapm.rentyourcio.com/api/uat/' + pageId + '/results'
                );
                if (!res.ok) return;
                const data = await res.json();
                (data.test_cases || []).forEach(tc => {
                    if (!tc.status || tc.status === 'pending') return;
                    const item = document.querySelector('.test-item[data-test="' + tc.id + '"]');
                    if (!item) return;
                    const btnClass = tc.status === 'pass' ? 'btn-pass' : tc.status === 'fail' ? 'btn-fail' : 'btn-skip';
                    const btn = item.querySelector('.' + btnClass);
                    if (btn) setResult(btn, tc.status);
                    if (tc.notes) {
                        const textarea = item.querySelector('.notes-input');
                        if (textarea) textarea.value = tc.notes;
                    }
                });
            } catch(e) {
                console.log('Could not load saved results:', e);
            }
        })();
"""
        # Insert before the last </script> tag
        last_script_close = html.rfind('</script>')
        if last_script_close > 0:
            html = html[:last_script_close] + prepopulate_js + html[last_script_close:]

    # MP-UAT-UI-001: Inject footer (duplicate header) into existing pages
    import re as _re_serve
    if '<footer' not in html and '<header>' in html:
        header_match = _re_serve.search(r'<header>(.*?)</header>', html, _re_serve.DOTALL)
        if header_match:
            footer_html = f'<footer style="background:linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent), black 15%));padding:20px;border-radius:12px;margin-top:24px;">{header_match.group(1).strip()}</footer>'
            # Insert before the status-bar div
            status_bar_pos = html.find('<div class="status-bar">')
            if status_bar_pos > 0:
                html = html[:status_bar_pos] + footer_html + '\n\n    ' + html[status_bar_pos:]

    # MP-UAT-UI-001: Fix header format — move PTH inline with version on line 1
    # Old: <h1>🔴 MetaPM v2.23.4 — MP-UAT-SUBMIT-001: desc</h1>\n<p>PTH: UG04 | N test cases</p>
    # New: <h1>🔴 MetaPM v2.23.4 PTH: UG04 — MP-UAT-SUBMIT-001</h1>\n<p>desc | N test cases</p>
    header_fix = _re_serve.search(
        r'(<h1>)(.*?)\s*—\s*([\w-]+):\s*(.*?)(</h1>\s*<p>)PTH:\s*(\w+)\s*\|\s*(\d+ test cases)(</p>)',
        html, _re_serve.DOTALL
    )
    if header_fix:
        prefix = header_fix.group(2)  # emoji + project + version
        sprint = header_fix.group(3)  # sprint code
        desc = header_fix.group(4)    # feature description
        pth_val = header_fix.group(6) # PTH value
        tc_count = header_fix.group(7) # "N test cases"
        new_header = f'<h1>{prefix} PTH: {pth_val} — {sprint}</h1>\n        <p>{desc} | {tc_count}</p>'
        html = html[:header_fix.start()] + new_header + html[header_fix.end():]
        # Also fix the footer copy if it was injected above
        if '<footer' in html:
            html = _re_serve.sub(
                r'(<footer[^>]*>.*?<h1>)(.*?)\s*—\s*([\w-]+):\s*(.*?)(</h1>\s*<p>)PTH:\s*(\w+)\s*\|\s*(\d+ test cases)(</p>)',
                lambda m: f'{m.group(1)}{m.group(2)} PTH: {m.group(6)} — {m.group(3)}</h1>\n        <p>{m.group(4)} | {m.group(7)}</p>',
                html, count=1, flags=_re_serve.DOTALL
            )

    # MP-UAT-UI-001: Fix button labels — add PTH to Copy CC Link
    if 'Copy Results' in html or 'Copy CC Link' in html:
        pth_col = page.get("pth") if "pth" in (page or {}) else None
        if not pth_col:
            # Try to extract PTH from page content
            pth_match = _re_serve.search(r'pth:\s*["\'](\w+)["\']', html)
            pth_col = pth_match.group(1) if pth_match else None
        if pth_col:
            html = html.replace('>Copy Results<', f'>Copy CC Link ({pth_col})<')
            html = html.replace('>Copy CC Link<', f'>Copy CC Link ({pth_col})<')
        else:
            html = html.replace('>Copy Results<', '>Copy CC Link<')
    if '>Submit to MetaPM<' in html:
        html = html.replace('>Submit to MetaPM<', '>Submit Final<')

    return HTMLResponse(content=html)


@router.get("/api/uat/pages")
async def list_uat_pages(
    handoff_id: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    include_passed: bool = Query(False),  # Fix 2f: show passed/archived when True
    limit: int = Query(20, le=100),
    offset: int = Query(0)
):
    """List UAT pages with optional filters.

    status filter behavior:
      - status=pending  → open pages only (in_progress, pending, submitted, ready, active)
      - status=archived → archived pages only
      - status=<value>  → exact match on that status
      - (omitted)       → all pages
    """
    import re as _re
    where_clauses = []
    params = []

    if handoff_id:
        where_clauses.append("u.handoff_id = ?")
        params.append(handoff_id)
    if project:
        where_clauses.append("u.project = ?")
        params.append(project)
    if status:
        if status == "pending":
            # "Open Only" — exclude archived pages
            where_clauses.append("u.status IN ('in_progress','pending','submitted','ready','active')")
        elif status == "archived":
            where_clauses.append("u.status = 'archived'")
        else:
            where_clauses.append("u.status = ?")
            params.append(status)
    elif include_passed:
        # Show all non-archived when explicitly requested
        where_clauses.append("u.status NOT IN ('archived', 'approved')")
    else:
        # Fix 2f: exclude passed, archived, approved by default — hide completed UATs
        where_clauses.append("u.status NOT IN ('archived', 'approved', 'passed', 'conditional_pass')")

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
        test_cases_raw = json.loads(row["test_cases_json"]) if row.get("test_cases_json") else []
        pth = row.get("pth")
        proj = row["project"]
        ver = row.get("version") or "?"
        sprint_code = row.get("sprint_code") or ""
        # Fix 2e: title includes PTH so UATs are searchable by sprint name
        if pth and sprint_code:
            title = f"PTH: {pth} | {proj} v{ver} — {sprint_code}"
        elif pth:
            title = f"PTH: {pth} | {proj} v{ver}"
        else:
            title = row.get("handoff_title") or row.get("handoff_task") or f"UAT — {proj} v{ver}"
        if not pth:
            m = _re.search(r'PTH-([A-Z0-9]{4})', title or '')
            pth = m.group(1) if m else None
        # Strip test case result values for list view (id/title/status only)
        test_cases_stripped = [
            {"id": tc.get("id", ""), "title": tc.get("title", ""), "status": tc.get("status", "pending")}
            for tc in test_cases_raw
        ]
        results.append({
            "uat_id": str(row["id"]),
            "handoff_id": str(row["handoff_id"]),
            "project": proj,
            "sprint_code": sprint_code,
            "version": ver,
            "status": row["status"],
            "test_count": len(test_cases_raw),
            "created_at": str(row["created_at"]),
            "uat_url": f"https://metapm.rentyourcio.com/uat/{row['id']}",
            "title": title,
            "pth": pth,
            "test_cases": test_cases_stripped,  # Fix 1c: included for roadmap-drill BV display
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


# ── PATCH /api/uat/{id}/status — UAT page status update / archive (MP-PTH-FIELD-001 PTH-9) ──

class UATStatusUpdate(BaseModel):
    status: str = Field(..., description="New status: active, archived, pending, passed, failed")
    notes: Optional[str] = None


@router.patch("/api/uat/{uat_id}/status")
async def update_uat_status(uat_id: str, body: UATStatusUpdate):
    """Update UAT page status (e.g. archive a legacy page)."""
    valid_statuses = {'active', 'archived', 'pending', 'passed', 'failed', 'ready', 'in_progress', 'submitted', 'approved'}
    if body.status not in valid_statuses:
        raise HTTPException(400, f"Invalid status '{body.status}'. Valid: {sorted(valid_statuses)}")

    page = execute_query(
        "SELECT id, status FROM uat_pages WHERE id = ?",
        (uat_id,), fetch="one"
    )
    if not page:
        raise HTTPException(404, f"UAT page {uat_id} not found")

    previous = page['status']
    execute_query(
        "UPDATE uat_pages SET status = ? WHERE id = ?",
        (body.status, uat_id), fetch="none"
    )
    logger.info(f"UAT page {uat_id} status: {previous} -> {body.status}")
    return {"uat_id": uat_id, "status": body.status, "previous_status": previous}


# ── GET /api/search — Universal PTH search (MP-PTH-FIELD-001 PTH-8) ──

@router.get("/api/search")
async def universal_search(q: str = Query(..., min_length=1, max_length=100)):
    """Search across requirements, UAT pages, handoffs, and lessons by PTH or keyword."""
    results = {"query": q, "requirements": [], "uat_pages": [], "handoffs": [], "lessons": []}

    # Search requirements by pth or code/title
    reqs = execute_query("""
        SELECT r.id, r.code, r.title, r.status, r.pth, r.project_id,
               p.code as project_code, p.name as project_name
        FROM roadmap_requirements r
        LEFT JOIN roadmap_projects p ON r.project_id = p.id
        WHERE r.pth = ? OR r.code LIKE ? OR r.title LIKE ?
        ORDER BY CASE WHEN r.pth = ? THEN 0 ELSE 1 END, r.updated_at DESC
    """, (q, f"%{q}%", f"%{q}%", q), fetch="all") or []
    for r in reqs:
        results["requirements"].append({
            "id": r["id"], "code": r["code"], "title": r["title"],
            "status": r["status"], "pth": r.get("pth"),
            "project_code": r.get("project_code"), "project_name": r.get("project_name")
        })

    # Search UAT pages by pth or title/project
    pages = execute_query("""
        SELECT u.id, u.project, u.version, u.status, u.pth, u.created_at,
               h.title as handoff_title
        FROM uat_pages u
        LEFT JOIN mcp_handoffs h ON u.handoff_id = h.id
        WHERE u.pth = ? OR u.project LIKE ? OR h.title LIKE ?
        ORDER BY u.created_at DESC
    """, (q, f"%{q}%", f"%{q}%"), fetch="all") or []
    for p in pages:
        results["uat_pages"].append({
            "uat_id": str(p["id"]), "project": p["project"], "version": p.get("version"),
            "status": p["status"], "pth": p.get("pth"),
            "title": p.get("handoff_title") or f"UAT: {p['project']} v{p.get('version','?')}",
            "uat_url": f"https://metapm.rentyourcio.com/uat/{p['id']}"
        })

    # Search handoffs by pth or title/project
    handoffs = execute_query("""
        SELECT id, project, title, task, version, status, pth, created_at
        FROM mcp_handoffs
        WHERE pth = ? OR title LIKE ? OR project LIKE ? OR task LIKE ?
        ORDER BY created_at DESC
        OFFSET 0 ROWS FETCH NEXT 20 ROWS ONLY
    """, (q, f"%{q}%", f"%{q}%", f"%{q}%"), fetch="all") or []
    for h in handoffs:
        results["handoffs"].append({
            "id": str(h["id"]), "project": h["project"],
            "title": h.get("title") or h.get("task"),
            "version": h.get("version"), "status": h["status"], "pth": h.get("pth")
        })

    # Search lessons by pth in notes/lesson text or source_sprint
    lessons = execute_query("""
        SELECT id, project, category, lesson, source_sprint, status, target
        FROM lessons_learned
        WHERE lesson LIKE ? OR source_sprint LIKE ? OR id LIKE ?
        ORDER BY created_at DESC
        OFFSET 0 ROWS FETCH NEXT 20 ROWS ONLY
    """, (f"%{q}%", f"%{q}%", f"%{q}%"), fetch="all") or []
    for ll in lessons:
        results["lessons"].append({
            "id": ll["id"], "project": ll["project"], "category": ll["category"],
            "lesson": ll["lesson"][:200], "source_sprint": ll.get("source_sprint"),
            "status": ll["status"]
        })

    results["total"] = sum(len(v) for k, v in results.items() if isinstance(v, list))
    return results


# ── GET /api/uat/{id}/results — Fetch current test case results (MP-UAT-DASHBOARD-FIX-001) ──

@router.get("/api/uat/{uat_id}/results")
async def get_uat_results(uat_id: str):
    """Get current test case results for a UAT page. Used by page JS to pre-populate on load."""
    page = execute_query(
        "SELECT id, test_cases_json, status FROM uat_pages WHERE id = ?",
        (uat_id,), fetch="one"
    )
    if not page:
        raise HTTPException(404, f"UAT page {uat_id} not found")

    test_cases = json.loads(page["test_cases_json"]) if page.get("test_cases_json") else []
    return {
        "uat_id": uat_id,
        "status": page["status"],
        "test_cases": test_cases
    }


# ── PATCH /api/uat/{id}/results — Update test case results (MP-UAT-GEN-001 Part 3) ──

@router.patch("/api/uat/{uat_id}/results")
async def update_uat_results(uat_id: str, body: UATResultsUpdate):
    """Update individual test case results from PL interaction.
    Updates test_cases_json in uat_pages and re-renders HTML."""
    page = execute_query(
        "SELECT id, test_cases_json, handoff_id, project, pth, version FROM uat_pages WHERE id = ?",
        (uat_id,), fetch="one"
    )
    if not page:
        raise HTTPException(404, f"UAT page {uat_id} not found")

    # Parse existing test cases
    existing_cases = json.loads(page["test_cases_json"]) if page.get("test_cases_json") else []

    # Build lookup of updates
    updates_by_id = {tc.id: tc for tc in body.test_cases}

    # Apply updates
    for case in existing_cases:
        update = updates_by_id.get(case["id"])
        if update:
            case["status"] = update.status
            if update.result is not None:
                case["result"] = update.result
            if update.notes is not None:
                case["notes"] = update.notes

    # Check if all test cases are resolved (no pending)
    all_resolved = all(
        c.get("status") in ("pass", "fail", "skip")
        for c in existing_cases
        if c.get("type", "pl_visual") == "pl_visual"
    )

    # Update status — auto-approve when client sends overall_status=approved (all-pass)
    new_status = page.get("status", "in_progress")
    if body.overall_status:
        if body.overall_status == "approved":
            # Verify server-side: all pl_visual cases must be pass
            if all(c.get("status") == "pass" for c in existing_cases if c.get("type", "pl_visual") == "pl_visual"):
                new_status = "approved"
            else:
                new_status = "passed" if all_resolved else "in_progress"
        elif body.overall_status == "passed":
            new_status = "passed"
        elif body.overall_status == "failed":
            new_status = "failed"
        elif all_resolved:
            new_status = "submitted"
    elif all_resolved:
        new_status = "submitted"

    submitted_at = "GETUTCDATE()" if new_status in ("passed", "failed", "submitted", "approved") else "NULL"

    execute_query(f"""
        UPDATE uat_pages
        SET test_cases_json = ?,
            status = ?,
            submitted_at = {submitted_at}
        WHERE id = ?
    """, (json.dumps(existing_cases), new_status, uat_id), fetch="none")

    # Count results
    pl_cases = [c for c in existing_cases if c.get("type", "pl_visual") == "pl_visual"]
    passed = sum(1 for c in pl_cases if c.get("status") == "pass")
    failed = sum(1 for c in pl_cases if c.get("status") == "fail")
    skipped = sum(1 for c in pl_cases if c.get("status") == "skip")
    pending = len(pl_cases) - passed - failed - skipped

    logger.info(f"UAT {uat_id} results updated: {passed}P/{failed}F/{skipped}S/{pending} pending, status={new_status}")

    return {
        "uat_id": uat_id,
        "status": new_status,
        "total": len(pl_cases),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pending": pending,
        "updated": len(updates_by_id)
    }


# ── POST /api/uat/bulk-archive — Archive old UAT records (MP-UAT-GEN-001 Part 5) ──

@router.post("/api/uat/bulk-archive")
async def bulk_archive_uats(body: BulkArchiveRequest):
    """Archive multiple UAT records. Sets status to 'archived' on both uat_pages and uat_results."""
    if not body.uat_ids:
        raise HTTPException(400, "uat_ids list cannot be empty")

    archived_pages = 0
    archived_results = 0
    not_found = []
    for uid in body.uat_ids:
        found = False
        # Archive in uat_pages if present
        page = execute_query(
            "SELECT id FROM uat_pages WHERE id = ?",
            (uid,), fetch="one"
        )
        if page:
            execute_query(
                "UPDATE uat_pages SET status = 'archived' WHERE id = ?",
                (uid,), fetch="none"
            )
            archived_pages += 1
            found = True

        # Archive in uat_results if present
        result = execute_query(
            "SELECT id FROM uat_results WHERE id = ?",
            (uid,), fetch="one"
        )
        if result:
            execute_query(
                "UPDATE uat_results SET status = 'archived' WHERE id = ?",
                (uid,), fetch="none"
            )
            archived_results += 1
            found = True

        if not found:
            not_found.append(uid)

    total_archived = archived_pages + archived_results
    logger.info(f"Bulk archived {archived_pages} pages + {archived_results} results. Reason: {body.reason}")
    return {
        "archived": total_archived,
        "archived_pages": archived_pages,
        "archived_results": archived_results,
        "not_found": len(not_found),
        "reason": body.reason
    }
