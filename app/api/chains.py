"""
Chain Proposal Browse UI — MP54
Read-only GET routes for viewing bug chain proposals and bug details.
REQ-116 / sprint MP54-CHAIN-PROPOSAL-UI-001
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.database import execute_query

logger = logging.getLogger(__name__)

router = APIRouter()

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "chains"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _nav_counts() -> dict:
    """Fetch misclassified and unclassified counts for the shared nav badges."""
    try:
        mis = execute_query(
            "SELECT COUNT(*) AS cnt FROM vw_bug_chain_misclassified", fetch="one"
        ) or {}
        unc = execute_query(
            "SELECT COUNT(*) AS cnt FROM vw_bug_chain_unclassified", fetch="one"
        ) or {}
        return {
            "misclassified_count": int(mis.get("cnt") or 0),
            "unclassified_count": int(unc.get("cnt") or 0),
        }
    except Exception as exc:
        logger.warning(f"_nav_counts failed: {exc}")
        return {"misclassified_count": "?", "unclassified_count": "?"}


def _age_days(ts) -> str:
    """Return elapsed days since ts (naive UTC datetime or ISO string)."""
    if not ts:
        return "—"
    try:
        if isinstance(ts, datetime):
            naive = ts.replace(tzinfo=None)
        else:
            naive = datetime.fromisoformat(str(ts))
        return str(max(0, (datetime.utcnow() - naive).days))
    except Exception:
        return "—"


# ---------------------------------------------------------------------------
# D1 — GET /chains
# ---------------------------------------------------------------------------

@router.get("/chains", response_class=HTMLResponse, include_in_schema=False)
async def chains_index(request: Request):
    chains = execute_query(
        "SELECT chain_label, total_occurrences, expected_outcome, missing_signal, "
        "first_occurrence_at, member_requirement_codes "
        "FROM vw_bug_chain_proposals_seeded ORDER BY total_occurrences DESC"
    ) or []

    for c in chains:
        c["age_days"] = _age_days(c.get("first_occurrence_at"))

    nav = _nav_counts()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "chains": chains, **nav},
    )


# ---------------------------------------------------------------------------
# D4 — GET /chains/misclassified  (must precede /{chain_label})
# ---------------------------------------------------------------------------

@router.get("/chains/misclassified", response_class=HTMLResponse, include_in_schema=False)
async def chains_misclassified(request: Request):
    rows = execute_query(
        "SELECT m.chain_label, m.member_requirement_code, m.bv_id, m.bv_title, "
        "m.bv_status, m.failure_type, m.misclassification_reason, "
        "r.title AS bug_title "
        "FROM vw_bug_chain_misclassified m "
        "LEFT JOIN roadmap_requirements r ON r.code = m.member_requirement_code "
        "ORDER BY m.chain_label, m.member_requirement_code"
    ) or []

    nav = _nav_counts()
    return templates.TemplateResponse(
        "misclassified.html",
        {"request": request, "rows": rows, **nav},
    )


# ---------------------------------------------------------------------------
# D5 — GET /chains/unclassified  (must precede /{chain_label})
# ---------------------------------------------------------------------------

@router.get("/chains/unclassified", response_class=HTMLResponse, include_in_schema=False)
async def chains_unclassified(request: Request):
    rows = execute_query(
        "SELECT code, title "
        "FROM vw_bug_chain_unclassified ORDER BY code"
    ) or []

    nav = _nav_counts()
    return templates.TemplateResponse(
        "unclassified.html",
        {"request": request, "rows": rows, **nav},
    )


# ---------------------------------------------------------------------------
# D6 — GET /chains/arithmetic  (must precede /{chain_label})
# ---------------------------------------------------------------------------

@router.get("/chains/arithmetic", response_class=HTMLResponse, include_in_schema=False)
async def chains_arithmetic(request: Request):
    seeded_row = execute_query(
        "SELECT SUM(total_occurrences) AS cnt FROM vw_bug_chain_proposals_seeded",
        fetch="one",
    ) or {}
    inductive_row = execute_query(
        "SELECT COUNT(*) AS cnt FROM vw_bug_chain_proposals_inductive",
        fetch="one",
    ) or {}
    unclassified_row = execute_query(
        "SELECT COUNT(*) AS cnt FROM vw_bug_chain_unclassified",
        fetch="one",
    ) or {}
    total_row = execute_query(
        "SELECT COUNT(*) AS cnt FROM roadmap_requirements WHERE type='bug'",
        fetch="one",
    ) or {}

    seeded = int(seeded_row.get("cnt") or 0)
    inductive = int(inductive_row.get("cnt") or 0)
    unclassified = int(unclassified_row.get("cnt") or 0)
    total_bugs = int(total_row.get("cnt") or 0)
    chain_sum = seeded + inductive + unclassified
    discrepancy = total_bugs - chain_sum

    nav = _nav_counts()
    return templates.TemplateResponse(
        "arithmetic.html",
        {
            "request": request,
            "seeded": seeded,
            "inductive": inductive,
            "unclassified": unclassified,
            "chain_sum": chain_sum,
            "total_bugs": total_bugs,
            "discrepancy": discrepancy,
            **nav,
        },
    )


# ---------------------------------------------------------------------------
# D2 — GET /chains/{chain_label}  (parameterized — after static paths)
# ---------------------------------------------------------------------------

@router.get("/chains/{chain_label}", response_class=HTMLResponse, include_in_schema=False)
async def chain_detail(request: Request, chain_label: str):
    chain_label = unquote(chain_label)

    chain = execute_query(
        "SELECT chain_label, total_occurrences, expected_outcome, missing_signal, "
        "first_occurrence_at, member_requirement_codes "
        "FROM vw_bug_chain_proposals_seeded WHERE chain_label = ?",
        (chain_label,),
        fetch="one",
    )
    if not chain:
        raise HTTPException(status_code=404, detail=f"Chain '{chain_label}' not found")

    chain["age_days"] = _age_days(chain.get("first_occurrence_at"))

    # Parse member codes and fetch full requirement detail
    codes: list = []
    try:
        codes = json.loads(chain.get("member_requirement_codes") or "[]")
    except Exception as exc:
        logger.warning(f"Failed to parse member_requirement_codes for {chain_label}: {exc}")

    members = []
    if codes:
        placeholders = ",".join(["?" for _ in codes])
        members = execute_query(
            f"SELECT r.code, r.title, LEFT(r.description, 500) AS description_preview, "
            f"r.status, r.priority, r.type "
            f"FROM roadmap_requirements r WHERE r.code IN ({placeholders}) ORDER BY r.code",
            tuple(codes),
        ) or []

    # Inductive proposals with description preview via LEFT JOIN
    inductive = execute_query(
        "SELECT i.proposed_member_code, i.proposed_member_title, i.match_rule, "
        "i.recurrence_count, i.diagnostic_present, "
        "LEFT(r.description, 500) AS description_preview "
        "FROM vw_bug_chain_proposals_inductive i "
        "LEFT JOIN roadmap_requirements r ON r.code = i.proposed_member_code "
        "WHERE i.chain_label = ?",
        (chain_label,),
    ) or []

    nav = _nav_counts()
    return templates.TemplateResponse(
        "chain_detail.html",
        {
            "request": request,
            "chain": chain,
            "members": members,
            "inductive": inductive,
            **nav,
        },
    )


# ---------------------------------------------------------------------------
# D3 — GET /bug/{code}
# ---------------------------------------------------------------------------

@router.get("/bug/{code}", response_class=HTMLResponse, include_in_schema=False)
async def bug_detail(request: Request, code: str):
    bug = execute_query(
        "SELECT * FROM roadmap_requirements WHERE code = ?",
        (code,),
        fetch="one",
    )
    if not bug:
        return HTMLResponse(
            content=(
                f"<html><body style='font-family:sans-serif;background:#0f1117;color:#e0e0e0;padding:32px'>"
                f"<h1>Bug not found</h1>"
                f"<p>No requirement with code <strong>{code}</strong> exists.</p>"
                f"<a href='/chains' style='color:#7eb8ff'>&#8592; Back to Chains</a>"
                f"</body></html>"
            ),
            status_code=404,
        )

    history = execute_query(
        "SELECT changed_at, changed_by, field_name, old_value, new_value "
        "FROM requirement_history WHERE requirement_id = ? ORDER BY changed_at DESC",
        (bug["id"],),
    ) or []

    bvs = execute_query(
        "SELECT u.pth, u.status AS page_status, b.bv_id, b.title AS bv_title, "
        "b.status AS bv_status, b.failure_type "
        "FROM uat_pages u "
        "JOIN uat_bv_items b ON b.spec_id = u.id "
        "WHERE u.pth IN (SELECT pth FROM pth_registry WHERE requirement_id = ?) "
        "AND b.status IN ('fail','skip')",
        (bug["id"],),
    ) or []

    nav = _nav_counts()
    return templates.TemplateResponse(
        "bug_detail.html",
        {"request": request, "bug": bug, "history": history, "bvs": bvs, **nav},
    )
