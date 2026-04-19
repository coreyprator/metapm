"""
MetaPM Quality API — MP23 REQ-048
Sprint quality model endpoints for quality dashboard.
"""
import logging
from fastapi import APIRouter, HTTPException
from app.core.database import execute_query

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/config/uat-classifications")
async def get_uat_classifications():
    """BUG-091 (MP49): UAT classification options for pl_visual BV cards.

    loadClassifications() in uat_payload.py depends on this endpoint. A prior
    404 caused `resp.json()` to return {"detail":"Not Found"}, which is not
    iterable — so .forEach threw after innerHTML had already been reset to the
    placeholder on the first select, leaving B1 empty while the outer loop
    halted before touching B2..Bn.
    """
    return [
        {"display_label": "New requirement",
         "help_text": "Missing feature that should be added as a new requirement."},
        {"display_label": "Bug",
         "help_text": "Existing feature broken or behaving incorrectly."},
        {"display_label": "Finding",
         "help_text": "Observation worth noting but not an immediate bug or requirement."},
        {"display_label": "No-action",
         "help_text": "Accepted as-is — no follow-up work needed."},
        {"display_label": "Out of scope",
         "help_text": "Belongs to a different sprint or project; defer."},
    ]


@router.get("/api/config/failure-schema")
async def get_failure_schema():
    """Return full failure type schema from DB, including help_text for cheat sheet."""
    rows = execute_query(
        """SELECT c.category_code, c.display_label AS cat_label, c.sort_order,
                  t.type_code, t.display_label AS type_label, t.help_text
           FROM failure_categories c
           JOIN failure_types t ON t.category_code = c.category_code
           WHERE t.is_active = 1
           ORDER BY c.sort_order, t.type_code""",
        fetch="all"
    )
    if not rows:
        raise HTTPException(status_code=500, detail="No failure types found in database")
    schema = {}
    for row in rows:
        cat = row["category_code"]
        if cat not in schema:
            schema[cat] = {"label": row["cat_label"], "types": []}
        schema[cat]["types"].append({
            "value": row["type_code"],
            "text":  row["type_label"],
            "help":  row["help_text"]
        })
    return schema


@router.get("/api/quality/sprint/{pth}")
async def get_sprint_quality(pth: str):
    """Quality data for one sprint, including per-BV results."""
    row = execute_query("""
        SELECT TOP 1
            cp.pth,
            cp.sprint_id,
            cp.five_q_applied,
            cp.root_cause_method,
            rr.code AS project_code,
            rr.title AS sprint_title,
            up.id AS spec_id,
            up.status AS uat_status,
            up.pl_submitted_at,
            up.attempt_number,
            ur.failure_type AS sprint_failure_type
        FROM cc_prompts cp
        LEFT JOIN roadmap_requirements rr ON cp.requirement_id = rr.id
        LEFT JOIN uat_pages up ON up.pth = cp.pth
        LEFT JOIN uat_results ur ON ur.handoff_id = up.handoff_id
        WHERE cp.pth = ?
        ORDER BY cp.created_at DESC
    """, (pth,), fetch="one")

    if not row:
        raise HTTPException(404, f"No sprint found for PTH {pth}")

    spec_id = row.get("spec_id")
    bv_results = []
    if spec_id:
        bv_rows = execute_query("""
            SELECT bv_id, title, status, failure_type, notes
            FROM uat_bv_items
            WHERE spec_id = ?
            ORDER BY bv_id
        """, (str(spec_id),), fetch="all") or []
        bv_results = [
            {
                "bv_id": b["bv_id"],
                "title": b.get("title", ""),
                "status": b.get("status", "pending"),
                "failure_type": b.get("failure_type"),
                "notes": b.get("notes", ""),
            }
            for b in bv_rows
        ]

    total_bvs = len(bv_results) if bv_results else 0
    passed_bvs = sum(1 for b in bv_results if b["status"] == "pass")
    bv_pass_rate = round((passed_bvs / total_bvs) * 100, 1) if total_bvs > 0 else 0.0

    # Parse version from sprint_id (e.g. "MP23-QUALITY-MODEL-001" → look at cc_prompts content)
    sprint_id = row.get("sprint_id") or ""

    return {
        "pth": row["pth"],
        "sprint_id": sprint_id,
        "project_code": row.get("project_code") or "",
        "sprint_title": row.get("sprint_title") or "",
        "five_q_applied": bool(row.get("five_q_applied")),
        "root_cause_method": row.get("root_cause_method"),
        "attempt_number": row.get("attempt_number"),
        "failure_type": row.get("sprint_failure_type"),
        "bv_pass_rate": bv_pass_rate,
        "overall_status": row.get("uat_status") or "pending",
        "submitted_at": str(row["pl_submitted_at"]) if row.get("pl_submitted_at") else None,
        "bv_results": bv_results,
    }


@router.get("/api/quality/portfolio")
async def get_portfolio_quality():
    """Sprint-level quality data for all sprints, newest first. Max 500."""
    rows = execute_query("""
        SELECT TOP 500
            cp.pth,
            cp.sprint_id,
            cp.five_q_applied,
            cp.root_cause_method,
            rp.code AS project_code,
            rp.name AS project_name,
            rr.title AS sprint_title,
            up.id AS spec_id,
            up.status AS uat_status,
            up.pl_submitted_at,
            up.attempt_number,
            ur.failure_type AS sprint_failure_type,
            (SELECT COUNT(*) FROM uat_bv_items bi WHERE bi.spec_id = up.id) AS total_bvs,
            (SELECT COUNT(*) FROM uat_bv_items bi WHERE bi.spec_id = up.id AND bi.status = 'pass') AS passed_bvs
        FROM cc_prompts cp
        LEFT JOIN roadmap_requirements rr ON cp.requirement_id = rr.id
        LEFT JOIN roadmap_projects rp ON rr.project_id = rp.id
        LEFT JOIN uat_pages up ON up.pth = cp.pth
        LEFT JOIN uat_results ur ON ur.handoff_id = up.handoff_id
        WHERE cp.status IN ('complete', 'closed', 'executing', 'cc_complete')
           OR up.pl_submitted_at IS NOT NULL
        ORDER BY COALESCE(up.pl_submitted_at, cp.created_at) DESC
    """, fetch="all") or []

    results = []
    for r in rows:
        total = r.get("total_bvs") or 0
        passed = r.get("passed_bvs") or 0
        bv_pass_rate = round((passed / total) * 100, 1) if total > 0 else 0.0
        results.append({
            "pth": r["pth"],
            "sprint_id": r.get("sprint_id") or "",
            "project_code": r.get("project_code") or "",
            "project_name": r.get("project_name") or "",
            "sprint_title": r.get("sprint_title") or "",
            "spec_id": str(r["spec_id"]) if r.get("spec_id") else None,
            "five_q_applied": bool(r.get("five_q_applied")),
            "root_cause_method": r.get("root_cause_method"),
            "attempt_number": r.get("attempt_number"),
            "failure_type": r.get("sprint_failure_type"),
            "bv_pass_rate": bv_pass_rate,
            "overall_status": r.get("uat_status") or "pending",
            "submitted_at": str(r["pl_submitted_at"]) if r.get("pl_submitted_at") else None,
        })

    return results


@router.get("/api/quality/projects")
async def get_quality_projects():
    """BUG-047: All projects for quality filter dropdown."""
    rows = execute_query(
        "SELECT DISTINCT code, name FROM roadmap_projects ORDER BY name",
        fetch="all"
    ) or []
    return [{"code": r["code"], "name": r["name"]} for r in rows]


@router.get("/api/quality/symptom-detector")
async def get_symptom_chasing():
    """Detect repeat bug patterns — features with 3+ bugs in 30 days."""
    rows = execute_query("""
        SELECT
            rp.code AS project_code,
            LEFT(rr.title, 40) AS feature_prefix,
            COUNT(*) AS bug_count
        FROM roadmap_requirements rr
        LEFT JOIN roadmap_projects rp ON rr.project_id = rp.id
        WHERE rr.type = 'bug'
          AND rr.created_at >= DATEADD(day, -30, GETUTCDATE())
        GROUP BY rp.code, LEFT(rr.title, 40)
        HAVING COUNT(*) >= 3
        ORDER BY COUNT(*) DESC
    """, fetch="all") or []

    return [
        {
            "project_code": r.get("project_code") or "",
            "feature_prefix": r.get("feature_prefix") or "",
            "bug_count": r["bug_count"],
        }
        for r in rows
    ]
