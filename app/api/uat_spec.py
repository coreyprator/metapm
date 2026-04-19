"""
MetaPM UAT Spec API — MP-UAT-SERVER-001
Spec-first, authenticated server-side UAT system.
"""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, List, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import httpx

from app.core.config import settings
from app.core.database import execute_query
from app.api.auth import is_pl_authenticated, render_login_required_page
from app.api.prompts import trigger_cloud_run_job_immediate

logger = logging.getLogger(__name__)
router = APIRouter()


def strip_surrogates(text: str) -> str:
    """BUG-072: Remove surrogate pairs that break UTF-8 encoding."""
    if not text:
        return text
    return text.encode('utf-16', 'surrogatepass').decode('utf-16', 'ignore')


def _validate_uuid(value: str) -> str:
    """Validate UUID format. Returns value or raises 400."""
    try:
        uuid.UUID(value)
        return value
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {value}")


async def sync_uat_to_rag(spec_id: str):
    """Fix 7 (MP08): Fire-and-forget — trigger Portfolio RAG re-ingestion after UAT submit."""
    # MF01: rewired from /ingest/metapm (does not exist) to /api/rag/sync on MetaPM itself
    rag_sync_url = "https://metapm.rentyourcio.com/api/rag/sync"
    mcp_key = os.getenv("MCP_API_KEY")
    if not mcp_key:
        logger.warning("MCP_API_KEY not set — skipping UAT RAG sync")
        return
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(rag_sync_url, headers={"X-API-Key": mcp_key})
            logger.info(f"RAG sync after UAT {spec_id}: {resp.status_code}")
    except Exception as e:
        logger.warning(f"RAG sync failed (non-fatal): {e}")


# ── Pydantic models ──────────────────────────────────────────────────────────

class TestCaseSpec(BaseModel):
    id: str
    title: str
    url: Optional[str] = None
    steps: List[str] = Field(default_factory=list)
    expected: Optional[str] = None
    type: str = "browser"


class UATSpecCreate(BaseModel):
    project: str
    version: str
    sprint: str
    pth: str = Field(..., max_length=20)
    linked_requirements: List[str] = Field(default_factory=list)
    test_cases: List[TestCaseSpec] = Field(..., min_length=1)


class UATSpecResponse(BaseModel):
    spec_id: str
    uat_url: str
    test_count: int
    status: str = "spec_created"


def get_allowed_failure_types() -> set:
    """MP27: Load allowed failure types from DB at validation time (not module load)."""
    try:
        rows = execute_query(
            "SELECT type_code FROM failure_types WHERE is_active = 1",
            fetch="all"
        )
        if rows:
            return {r["type_code"] for r in rows}
    except Exception:
        pass
    # Fallback to hardcoded set if DB tables don't exist yet
    return {
        "wrong_spec", "regression", "environment", "unclear_bv",
        "machine_test_sent_to_pl", "no_5q_applied", "incomplete_spec",
        "missing_acceptance_criteria", "incomplete_handoff", "other",
        "ui_rendering_bug", "data_mapping_bug", "filter_query_bug",
        "gate_validation_bug", "navigation_routing_bug", "api_contract_bug",
        "state_management_bug", "performance_bug",
    }


class PLResultsTestCase(BaseModel):
    id: str
    status: str  # pass | fail | skip | pending
    notes: Optional[str] = None
    attachments: Optional[List[dict]] = None  # MP07: image/file evidence
    classification: Optional[str] = None  # MP18 REQ-047: New requirement | Bug | Finding | No-action
    failure_type: Optional[str] = None  # MP23 REQ-048: reason for failure


class PLResultsSubmit(BaseModel):
    test_cases: List[PLResultsTestCase]
    overall_notes: Optional[str] = None
    general_notes: Optional[Any] = None  # MP24 REQ-057: List[dict] (timestamped entries) or legacy str
    failure_type: Optional[str] = None  # MP23: sprint-level failure_type for conditional_pass
    general_notes_attachments: Optional[List[dict]] = None  # MP07
    submitted_by: Optional[str] = None


# MP19 REQ-049: CC machine BV results
class CCMachineResult(BaseModel):
    id: str
    cc_result: str  # pass | fail
    cc_evidence: str  # raw output / JSON response proving the result


class CCResultsSubmit(BaseModel):
    test_cases: List[CCMachineResult]


# ── POST /api/uat/spec ───────────────────────────────────────────────────────

@router.post("/api/uat/spec", response_model=UATSpecResponse, status_code=201)
async def create_uat_spec(body: UATSpecCreate):
    """
    Create or update a UAT spec. Upserts by PTH — second POST with same PTH updates
    the existing spec rather than creating a duplicate (AP04 Fix 4).
    No auth required (CC runs this as SA).
    """
    # REQ-002 (BA15): reject empty UAT specs at handler level (belt-and-suspenders with Field min_length)
    if not body.test_cases:
        raise HTTPException(status_code=400, detail="UAT spec must contain at least one test case (BA15).")

    now = datetime.utcnow()
    spec_data = body.model_dump()

    # Build minimal test_cases_json for compatibility with existing uat_pages queries
    tc_json = json.dumps([
        {
            "id": tc.id,
            "title": tc.title,
            "url": tc.url,
            "steps": tc.steps,
            "expected": tc.expected,
            "type": tc.type or "browser",
            "status": "pending",
            "notes": ""
        }
        for tc in body.test_cases
    ])

    # AP04 Fix 4: Check if spec already exists for this PTH (upsert by PTH)
    existing = execute_query(
        "SELECT TOP 1 id, pl_submitted_at FROM uat_pages WHERE pth = ? AND spec_source = 'cc_spec' ORDER BY created_at DESC",
        (body.pth,), fetch="one"
    )

    if existing:
        spec_id = str(existing["id"])
        # MP48 BUG-087 Phase C guard: refuse to clobber a spec that has a prior
        # PL submission. Re-posting after submit would wipe test_cases_json +
        # uat_bv_items and destroy PL's recorded pass/fail/notes — this is the
        # root cause of "Reopen & Edit shows blank" that MP47's reopen fix could
        # not address on its own. Caller must archive the spec before re-posting.
        if existing.get("pl_submitted_at") is not None:
            logger.warning(
                f"post_uat_spec blocked: PTH={body.pth} spec={spec_id} has prior PL submission "
                f"(pl_submitted_at={existing['pl_submitted_at']}). Refusing to clobber."
            )
            raise HTTPException(status_code=409, detail={
                "error": "spec_has_prior_submission",
                "message": (
                    "This UAT spec already has a PL submission recorded. Re-posting would "
                    "erase pass/fail results and notes. Archive the existing spec before "
                    "creating a replacement, or update via the override/reopen endpoints."
                ),
                "pth": body.pth,
                "spec_id": spec_id,
                "pl_submitted_at": str(existing["pl_submitted_at"]),
                "existing_uat_url": f"https://metapm.rentyourcio.com/uat/{spec_id}",
            })
        # UPDATE existing unsubmitted spec — preserve ID, reset test cases
        try:
            execute_query("""
                UPDATE uat_pages SET
                    project = ?, sprint_code = ?, version = ?,
                    test_cases_json = ?, html_content = 'spec_created',
                    status = 'ready', spec_data = ?
                WHERE id = ?
            """, (
                body.project,
                body.sprint,
                body.version,
                tc_json,
                json.dumps(spec_data),
                spec_id,
            ), fetch="none")
            logger.info(f"Updated existing UAT spec {spec_id} for PTH {body.pth} ({len(body.test_cases)} tests)")
        except Exception as e:
            logger.error(f"UAT spec update failed: {e}")
            raise HTTPException(500, f"Failed to update UAT spec: {e}")
    else:
        # INSERT new spec
        spec_id = str(uuid.uuid4()).upper()
        placeholder_handoff_id = spec_id  # reuse spec_id as placeholder
        try:
            execute_query("""
                INSERT INTO uat_pages
                    (id, handoff_id, project, sprint_code, pth, version,
                     test_cases_json, html_content, status,
                     spec_source, spec_locked_at, spec_data)
                VALUES (?, ?, ?, ?, ?, ?,
                        ?, 'spec_created', 'ready',
                        'cc_spec', ?, ?)
            """, (
                spec_id,
                placeholder_handoff_id,
                body.project,
                body.sprint,
                body.pth,
                body.version,
                tc_json,
                now,
                json.dumps(spec_data),
            ), fetch="none")
            logger.info(f"Created new UAT spec {spec_id} for {body.project} {body.version} ({len(body.test_cases)} tests)")
        except Exception as e:
            logger.error(f"UAT spec insert failed: {e}")
            raise HTTPException(500, f"Failed to create UAT spec: {e}")

    uat_url = f"https://metapm.rentyourcio.com/uat/{spec_id}"
    logger.info(f"UAT spec upsert complete: {spec_id} PTH={body.pth}")

    # MM14-REQ-001: Auto-advance linked requirement from cc_complete → uat_ready
    if body.pth:
        try:
            req_row = execute_query(
                "SELECT TOP 1 id, code, status FROM roadmap_requirements WHERE pth = ? AND status = 'cc_complete'",
                (body.pth,), fetch="one"
            )
            if req_row:
                execute_query(
                    "UPDATE roadmap_requirements SET status = 'uat_ready', uat_url = ?, updated_at = GETUTCDATE() WHERE id = ?",
                    (uat_url, req_row["id"]), fetch="none"
                )
                logger.info(f"Auto-advanced {req_row['code']} to uat_ready on UAT spec creation for PTH {body.pth}")
        except Exception as e:
            logger.warning(f"Auto-advance to uat_ready failed (non-fatal): {e}")

    return UATSpecResponse(
        spec_id=spec_id,
        uat_url=uat_url,
        test_count=len(body.test_cases),
        status="spec_created"  # logical status returned to CC
    )


# ── GET /api/uat/spec/{spec_id} ──────────────────────────────────────────────

@router.get("/api/uat/spec/{spec_id}")
async def get_uat_spec(spec_id: str):
    """
    Get UAT spec metadata and test case list. CC uses this as canary after POST.
    Does NOT return result values (those are PL-only).
    """
    _validate_uuid(spec_id)
    row = execute_query(
        """SELECT id, project, sprint_code, pth, version, status,
                  spec_source, spec_locked_at, spec_data, test_cases_json
           FROM uat_pages WHERE id = ?""",
        (spec_id,), fetch="one"
    )
    if not row:
        raise HTTPException(404, f"UAT spec {spec_id} not found")
    if row.get("spec_source") != "cc_spec":
        raise HTTPException(404, f"UAT {spec_id} is not a cc_spec UAT")

    spec_data = json.loads(row["spec_data"]) if row.get("spec_data") else {}
    tc_json = json.loads(row["test_cases_json"]) if row.get("test_cases_json") else []

    # Strip result values from test cases — CC must not see results
    tc_stripped = [
        {"id": tc["id"], "title": tc["title"], "url": tc.get("url"),
         "steps": tc.get("steps", []), "expected": tc.get("expected"), "type": tc.get("type")}
        for tc in tc_json
    ]

    return {
        "spec_id": spec_id,
        "uat_url": f"https://metapm.rentyourcio.com/uat/{spec_id}",
        "project": row["project"],
        "sprint": row.get("sprint_code"),
        "pth": row.get("pth"),
        "version": row.get("version"),
        "status": row["status"],
        "spec_source": row.get("spec_source"),
        "spec_locked_at": str(row.get("spec_locked_at") or ""),
        "test_count": len(tc_stripped),
        "linked_requirements": spec_data.get("linked_requirements", []),
        "test_cases": tc_stripped
    }


# ── PATCH /api/uat/{spec_id}/pl-results ─────────────────────────────────────

@router.patch("/api/uat/{spec_id}/pl-results")
async def submit_pl_results(spec_id: str, body: PLResultsSubmit, request: Request):
    """
    PL-only endpoint to record UAT results after browser testing.
    Requires Google OAuth session (cprator@cbsware.com).
    Returns 403 if accessed without valid PL session — CC/SA cannot submit results.
    """
    _validate_uuid(spec_id)
    if not is_pl_authenticated(request):
        raise HTTPException(
            status_code=403,
            detail="PL authentication required. Access this endpoint via the browser UAT page after signing in with Google."
        )

    row = execute_query(
        "SELECT id, test_cases_json, spec_source, status, pth, handoff_id FROM uat_pages WHERE id = ?",
        (spec_id,), fetch="one"
    )
    if not row:
        raise HTTPException(404, f"UAT spec {spec_id} not found")
    if row.get("spec_source") != "cc_spec":
        raise HTTPException(400, "This endpoint is only for cc_spec UATs")

    existing_cases = json.loads(row["test_cases_json"]) if row.get("test_cases_json") else []

    # MP18 REQ-047 + MP20 BUG-039: Identify pl_visual BVs only (skip cc_machine)
    pl_visual_ids = set()
    for c in existing_cases:
        if c.get("id", "").startswith("_"):
            continue
        if c.get("type") == "pl_visual":
            pl_visual_ids.add(c["id"])

    # MP18 REQ-047: Server-side validation — all pl_visual BVs must have status and classification
    updates_by_id = {tc.id: tc for tc in body.test_cases}
    missing_classification = []
    pending_bv_ids = []
    for bv_id in pl_visual_ids:
        tc = updates_by_id.get(bv_id)
        if tc:
            if not tc.classification:
                if tc.status == 'pass':
                    tc.classification = 'No-action'   # BUG-061: Auto-assign, never block pass
                else:
                    missing_classification.append(bv_id)
            if not tc.status or tc.status == "pending":
                pending_bv_ids.append(bv_id)
        else:
            pending_bv_ids.append(bv_id)
            missing_classification.append(bv_id)

    if missing_classification:
        raise HTTPException(status_code=400, detail={
            "error": "classification_required",
            "missing_bv_ids": missing_classification,
        })
    if pending_bv_ids:
        raise HTTPException(status_code=400, detail={
            "error": "all_bvs_required",
            "pending_bv_ids": pending_bv_ids,
        })

    # MP23 REQ-048 + MP27: Quality gate — failed BVs require valid failure_type, skipped/pending require notes
    allowed_types = get_allowed_failure_types()
    failed_no_type = []
    invalid_type = []
    skip_no_notes = []
    for tc in body.test_cases:
        if tc.id not in pl_visual_ids:
            continue
        if tc.status == "fail" and not tc.failure_type:
            failed_no_type.append(tc.id)
        elif tc.status == "fail" and tc.failure_type and tc.failure_type not in allowed_types:
            invalid_type.append(tc.id)
        if tc.status in ("skip", "pending") and not (tc.notes and tc.notes.strip()):
            skip_no_notes.append(tc.id)
    if failed_no_type:
        raise HTTPException(status_code=400, detail={
            "error": "failure_type_required",
            "message": "Please select a failure type for each failed test \u2014 this helps track why sprints fail.",
            "missing_bv_ids": failed_no_type,
        })
    if invalid_type:
        raise HTTPException(status_code=400, detail={
            "error": "invalid_failure_type",
            "message": "One or more failure types are not recognized. Please select from the dropdown.",
            "invalid_bv_ids": invalid_type,
        })
    if skip_no_notes:
        raise HTTPException(status_code=400, detail={
            "error": "notes_required_for_skip",
            "message": "Please add a note explaining why this test was skipped or left pending.",
            "missing_bv_ids": skip_no_notes,
        })

    for case in existing_cases:
        if case.get("id", "").startswith("_"):
            continue
        update = updates_by_id.get(case["id"])
        if update:
            case["status"] = update.status
            if update.classification:
                case["classification"] = update.classification
            if update.notes is not None:
                case["notes"] = update.notes
            if update.attachments:
                case["attachments"] = update.attachments
            if update.failure_type:
                case["failure_type"] = update.failure_type

    # Store general notes attachments as sentinel entry (id starts with _)
    if body.general_notes_attachments:
        gn_idx = next((i for i, c in enumerate(existing_cases) if c.get("id") == "_general_notes"), None)
        if gn_idx is not None:
            existing_cases[gn_idx]["attachments"] = body.general_notes_attachments
        else:
            existing_cases.append({"id": "_general_notes", "attachments": body.general_notes_attachments})

    real_cases = [c for c in existing_cases if not c.get("id", "").startswith("_")]
    passed = sum(1 for c in real_cases if c.get("status") == "pass")
    failed = sum(1 for c in real_cases if c.get("status") == "fail")
    skipped = sum(1 for c in real_cases if c.get("status") == "skip")
    total = len(real_cases)

    # Fix 2b: conditional_pass for mix of pass/skip with no fails
    if failed > 0:
        new_status = "failed"
    elif passed == total:
        new_status = "passed"
    elif failed == 0 and (passed + skipped) == total:
        new_status = "conditional_pass"
    else:
        new_status = "in_progress"

    # MP23 REQ-048: conditional_pass gate — requires sprint-level failure_type
    if new_status == "conditional_pass" and not body.failure_type:
        raise HTTPException(status_code=400, detail={
            "error": "failure_type_required_conditional",
            "message": "Conditional pass requires a failure type. Please select one for this sprint.",
        })

    # MP23 REQ-048: Derive sprint-level failure_type from BV-level if not explicitly set
    sprint_failure_type = body.failure_type
    if not sprint_failure_type and failed > 0:
        bv_failure_types = [tc.failure_type for tc in body.test_cases if tc.status == "fail" and tc.failure_type]
        if bv_failure_types:
            sprint_failure_type = bv_failure_types[0]

    # MP23 REQ-048: Calculate attempt_number for this requirement
    attempt_number = None
    try:
        spec_pth_for_attempt = row.get("pth")
        if spec_pth_for_attempt:
            prior_count_row = execute_query("""
                SELECT COUNT(*) as cnt FROM uat_pages up
                JOIN cc_prompts cp ON up.pth = cp.pth
                WHERE cp.requirement_id = (
                    SELECT TOP 1 requirement_id FROM cc_prompts WHERE pth = ?
                )
                AND up.pl_submitted_at IS NOT NULL
                AND up.id != ?
            """, (spec_pth_for_attempt, spec_id), fetch="one")
            attempt_number = (prior_count_row["cnt"] if prior_count_row else 0) + 1
    except Exception as e:
        logger.warning(f"attempt_number calculation failed: {e}")

    # Fix 2d: persist general_notes + attempt_number
    # MP24 REQ-057: general_notes stored as JSON array of timestamped entries
    gn_value = body.general_notes or body.overall_notes
    if isinstance(gn_value, list):
        gn_value = json.dumps(gn_value)
    execute_query("""
        UPDATE uat_pages
        SET test_cases_json = ?,
            status = ?,
            pl_submitted_at = GETUTCDATE(),
            general_notes = ?,
            attempt_number = ?
        WHERE id = ?
    """, (json.dumps(existing_cases), new_status, gn_value, attempt_number, spec_id), fetch="none")

    # MP23 REQ-048: Write sprint-level failure_type to uat_results
    if sprint_failure_type:
        try:
            handoff_id = row.get("handoff_id")
            if handoff_id:
                execute_query("""
                    UPDATE uat_results SET failure_type = ? WHERE handoff_id = ?
                """, (sprint_failure_type, str(handoff_id)), fetch="none")
        except Exception as e:
            logger.warning(f"uat_results failure_type update failed: {e}")

    logger.info(f"PL submitted results for spec {spec_id}: {passed}P/{failed}F/{skipped}S, status={new_status}")

    # MP18 REQ-045: Auto-advance linked requirement based on UAT outcome
    spec_pth_val = row.get("pth")
    requirement_advance_result = {}
    if spec_pth_val and new_status in ("passed", "failed", "conditional_pass"):
        try:
            req_row = execute_query(
                "SELECT TOP 1 id, code, status FROM roadmap_requirements WHERE pth = ?",
                (spec_pth_val,), fetch="one"
            )
            if req_row and req_row["status"] == "uat_ready":
                if new_status == "passed":
                    # uat_ready → uat_pass (history row via trigger)
                    execute_query(
                        "UPDATE roadmap_requirements SET status = 'uat_pass', updated_at = GETUTCDATE() WHERE id = ?",
                        (req_row["id"],), fetch="none"
                    )
                    logger.info(f"REQ-045: {req_row['code']} advanced to uat_pass")
                    # uat_pass → done (second auto-chain)
                    execute_query(
                        "UPDATE roadmap_requirements SET status = 'done', updated_at = GETUTCDATE() WHERE id = ?",
                        (req_row["id"],), fetch="none"
                    )
                    logger.info(f"REQ-045: {req_row['code']} auto-chained to done")
                    requirement_advance_result = {
                        "requirement_advanced": True,
                        "new_status": "done",
                        "requirement_code": req_row["code"],
                    }
                elif new_status == "conditional_pass":
                    # Advance to uat_pass only — do NOT advance to done
                    execute_query(
                        "UPDATE roadmap_requirements SET status = 'uat_pass', updated_at = GETUTCDATE() WHERE id = ?",
                        (req_row["id"],), fetch="none"
                    )
                    logger.info(f"REQ-045: {req_row['code']} advanced to uat_pass (conditional — requires CAI review)")
                    requirement_advance_result = {
                        "requirement_advanced": True,
                        "new_status": "uat_pass",
                        "requirement_code": req_row["code"],
                        "requires_cai_review": True,
                    }
                elif new_status == "failed":
                    # uat_ready → uat_fail
                    execute_query(
                        "UPDATE roadmap_requirements SET status = 'uat_fail', updated_at = GETUTCDATE() WHERE id = ?",
                        (req_row["id"],), fetch="none"
                    )
                    logger.info(f"REQ-045: {req_row['code']} advanced to uat_fail")
                    requirement_advance_result = {
                        "requirement_advanced": True,
                        "new_status": "uat_fail",
                        "requirement_code": req_row["code"],
                    }
            elif req_row:
                logger.info(f"Requirement {req_row['code']} at {req_row['status']}, not uat_ready — skipping auto-advance")
        except Exception as e:
            logger.warning(f"REQ-045 auto-advance failed: {e}")
            requirement_advance_result = {"requirement_advance_error": str(e)}
    elif new_status == "in_progress":
        logger.info(f"UAT {spec_id} incomplete: {failed} fail, {total - passed - skipped} pending — no auto-advance")

    # MF01: persist individual BV items to uat_bv_items table (MP23: +failure_type)
    title_lookup = {c["id"]: c.get("title", "") for c in real_cases}
    for tc in body.test_cases:
        try:
            bv_title = title_lookup.get(tc.id, "")
            execute_query("""
                IF EXISTS (SELECT 1 FROM uat_bv_items WHERE spec_id=? AND bv_id=?)
                    UPDATE uat_bv_items
                    SET status=?, notes=?, classification=?, failure_type=?, updated_at=GETUTCDATE()
                    WHERE spec_id=? AND bv_id=?
                ELSE
                    INSERT INTO uat_bv_items (spec_id, bv_id, title, status, notes, classification, failure_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                spec_id, tc.id,                                                          # EXISTS check
                tc.status or 'pending', tc.notes or '', tc.classification, tc.failure_type,  # UPDATE SET
                spec_id, tc.id,                                                          # UPDATE WHERE
                spec_id, tc.id, bv_title,                                                # INSERT
                tc.status or 'pending', tc.notes or '', tc.classification, tc.failure_type,  # INSERT values
            ), fetch="none")
        except Exception as bv_err:
            logger.warning(f"BV item upsert failed for {tc.id}: {bv_err}")

    # Fix 7 (MP08): trigger RAG re-ingestion so CAI can query results immediately
    asyncio.create_task(sync_uat_to_rag(spec_id))

    # AP07: trigger Loop 3 to auto-process UAT results (post review + email PL)
    spec_pth = row.get("pth") or "N/A"
    spec_handoff_id = str(row["handoff_id"]) if row.get("handoff_id") else "none"
    asyncio.create_task(trigger_cloud_run_job_immediate(
        "metapm-loop3-processor",
        args_override=[
            f"--spec-id={spec_id}",
            f"--handoff-id={spec_handoff_id}",
            f"--pth={spec_pth}",
        ]
    ))
    logger.info(f"[AP07] Loop 3 triggered for spec {spec_id} PTH={spec_pth}")

    response = {
        "status": new_status,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "uat_url": f"https://metapm.rentyourcio.com/uat/{spec_id}",
    }
    response.update(requirement_advance_result)
    return response


# ── PATCH /api/uat/{spec_id}/cc-results — MP19 REQ-049 ─────────────────────

@router.patch("/api/uat/{spec_id}/cc-results")
async def submit_cc_results(spec_id: str, body: CCResultsSubmit):
    """
    CC-only endpoint to record machine BV results with evidence.
    No PL auth required — CC submits after running machine tests.
    """
    _validate_uuid(spec_id)

    row = execute_query(
        "SELECT id, test_cases_json FROM uat_pages WHERE id = ?",
        (spec_id,), fetch="one"
    )
    if not row:
        raise HTTPException(404, f"UAT spec {spec_id} not found")

    existing_cases = json.loads(row["test_cases_json"]) if row.get("test_cases_json") else []
    updates_by_id = {tc.id: tc for tc in body.test_cases}
    updated_count = 0

    for case in existing_cases:
        if case.get("id", "").startswith("_"):
            continue
        update = updates_by_id.get(case["id"])
        if update and case.get("type") == "cc_machine":
            case["cc_result"] = update.cc_result
            case["cc_evidence"] = strip_surrogates(update.cc_evidence)
            case["status"] = update.cc_result  # sync status with cc_result
            updated_count += 1

    execute_query("""
        UPDATE uat_pages SET test_cases_json = ? WHERE id = ?
    """, (json.dumps(existing_cases), spec_id), fetch="none")

    # Also persist to uat_bv_items
    for tc in body.test_cases:
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
                spec_id, tc.id,
                tc.cc_result, tc.cc_result, strip_surrogates(tc.cc_evidence),
                spec_id, tc.id,
                spec_id, tc.id, tc.id,
                tc.cc_result, tc.cc_result, strip_surrogates(tc.cc_evidence),
            ), fetch="none")
        except Exception as e:
            logger.warning(f"CC BV item upsert failed for {tc.id}: {e}")

    logger.info(f"CC submitted {updated_count} machine BV results for spec {spec_id}")
    return {"updated": updated_count, "spec_id": spec_id}


class UATOverride(BaseModel):
    status: str  # passed | conditional_pass | failed
    override_note: Optional[str] = None


@router.patch("/api/uat/{spec_id}/override")
async def override_uat_status(spec_id: str, body: UATOverride, request: Request):
    """
    PL-only: Override UAT result status (e.g. conditional_pass → passed).
    Requires PL Google auth session.
    """
    _validate_uuid(spec_id)
    if not is_pl_authenticated(request):
        raise HTTPException(status_code=403, detail="PL authentication required")
    allowed = {"passed", "conditional_pass", "failed", "in_progress"}
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of {allowed}")
    row = execute_query("SELECT id, status FROM uat_pages WHERE id = ?", (spec_id,), fetch="one")
    if not row:
        raise HTTPException(status_code=404, detail=f"UAT spec {spec_id} not found")
    try:
        execute_query("""
            UPDATE uat_pages SET status = ?, override_note = ?, override_at = GETDATE()
            WHERE id = ?
        """, (body.status, body.override_note or "", spec_id), fetch="none")
    except Exception:
        # Fallback: columns may not exist yet — update only status
        execute_query("UPDATE uat_pages SET status = ? WHERE id = ?",
                      (body.status, spec_id), fetch="none")
    return {"spec_id": spec_id, "status": body.status, "override_note": body.override_note}


# ── POST /api/uat/{spec_id}/reopen ─────────────────────────────────────────

@router.post("/api/uat/{spec_id}/reopen")
async def reopen_uat(spec_id: str, request: Request):
    """
    MP-UAT-001: Reopen a submitted UAT for editing.
    MP47 BUG-087: Preserves prior pl-results so the form pre-populates on reload.
    Flips status back to 'ready' and clears pl_submitted_at (so the form is editable
    again) but KEEPS test_cases_json and general_notes intact. The existing renderer
    reads those fields to restore pass/fail radios, notes, classifications, and
    failure types for each BV.
    Accepts PL Google OAuth session OR X-API-Key header.
    """
    _validate_uuid(spec_id)
    api_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    expected_key = settings.MCP_API_KEY or ""
    has_api_key = api_key and api_key == expected_key
    if not is_pl_authenticated(request) and not has_api_key:
        raise HTTPException(status_code=403, detail="PL authentication or API key required")

    row = execute_query(
        "SELECT id, status FROM uat_pages WHERE id = ?",
        (spec_id,), fetch="one"
    )
    if not row:
        raise HTTPException(404, f"UAT spec {spec_id} not found")

    execute_query("""
        UPDATE uat_pages
        SET status = 'ready',
            pl_submitted_at = NULL
        WHERE id = ?
    """, (spec_id,), fetch="none")

    logger.info(f"UAT spec {spec_id} reopened (BUG-087) — prior results preserved for pre-fill")
    return {"status": "reopened", "spec_id": spec_id, "results_preserved": True}


@router.get("/api/uat/{spec_id}/pl-results")
async def get_pl_results(spec_id: str):
    """
    MP47 BUG-087 M1: Return the current pl_visual test_cases with their prior
    status/notes/classification/failure_type and the general_notes array. Used by
    the reopen flow to pre-populate the form. Returns {} when the spec has no
    prior submission (caller renders a blank form).
    """
    _validate_uuid(spec_id)
    row = execute_query(
        "SELECT id, test_cases_json, general_notes, status, pl_submitted_at "
        "FROM uat_pages WHERE id = ?",
        (spec_id,), fetch="one"
    )
    if not row:
        raise HTTPException(404, f"UAT spec {spec_id} not found")

    cases = json.loads(row["test_cases_json"]) if row.get("test_cases_json") else []
    pl_cases = [
        {
            "id": c.get("id"),
            "status": c.get("status", "pending"),
            "notes": c.get("notes", "") or "",
            "classification": c.get("classification", "") or "",
            "failure_type": c.get("failure_type", "") or "",
        }
        for c in cases
        if not c.get("id", "").startswith("_")
        and c.get("type", "pl_visual") != "cc_machine"
    ]
    has_prior = any(
        c["status"] not in ("pending", "") or c["notes"] or c["classification"]
        for c in pl_cases
    )
    return {
        "spec_id": str(row["id"]),
        "status": row.get("status", "pending"),
        "pl_submitted_at": str(row["pl_submitted_at"]) if row.get("pl_submitted_at") else None,
        "has_prior_submission": has_prior,
        "test_cases": pl_cases,
        "general_notes": _parse_general_notes(row.get("general_notes")),
    }


@router.get("/api/uat/{spec_id}/results")
async def get_uat_results(spec_id: str):
    """
    Public read-only endpoint for submitted UAT results.
    CC and CAI can query this after PL submits.
    """
    _validate_uuid(spec_id)
    row = execute_query("""
        SELECT id, project, pth, status, test_cases_json, general_notes,
               pl_submitted_at, spec_json
        FROM uat_pages WHERE id = ?
    """, (spec_id,), fetch="one")
    if not row:
        raise HTTPException(404, f"UAT spec {spec_id} not found")

    spec_data = json.loads(row["spec_json"]) if row.get("spec_json") else {}
    cases = json.loads(row["test_cases_json"]) if row.get("test_cases_json") else []
    real_cases = [c for c in cases if not c.get("id", "").startswith("_")]

    passed = sum(1 for c in real_cases if c.get("status") == "pass")
    failed = sum(1 for c in real_cases if c.get("status") == "fail")
    skipped = sum(1 for c in real_cases if c.get("status") == "skip")
    pending = sum(1 for c in real_cases if not c.get("status") or c.get("status") == "pending")

    return {
        "spec_id": str(row["id"]),
        "project": row.get("project") or spec_data.get("project", ""),
        "version": spec_data.get("version", ""),
        "pth": row.get("pth") or spec_data.get("pth", ""),
        "sprint": spec_data.get("sprint", ""),
        "status": row.get("status", "pending"),
        "submitted_at": str(row["pl_submitted_at"]) if row.get("pl_submitted_at") else None,
        "summary": {"total": len(real_cases), "passed": passed, "failed": failed, "skipped": skipped, "pending": pending},
        "test_cases": [
            {
                "id": c.get("id"),
                "title": c.get("title", ""),
                "status": c.get("status", "pending"),
                "notes": c.get("notes", ""),
            }
            for c in real_cases
        ],
        "general_notes": _parse_general_notes(row.get("general_notes")),
    }


def _parse_general_notes(raw):
    """MP24 REQ-057: Parse general_notes — JSON array or legacy plain string."""
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    # Legacy plain string — wrap as single entry
    return [{"timestamp": None, "text": raw, "classification": None}]


# ── POST /api/uat/{spec_id}/admin-backfill ───────────────────────────────────

class AdminBackfillResult(BaseModel):
    id: str
    status: str  # pass | fail | skip | pending
    notes: Optional[str] = None


class AdminBackfillRequest(BaseModel):
    test_cases: List[AdminBackfillResult]
    general_notes: Optional[str] = None
    backfill_reason: str  # required — must document why backfill is needed


@router.post("/api/uat/{spec_id}/admin-backfill")
async def admin_backfill_uat_results(spec_id: str, body: AdminBackfillRequest, request: Request):
    """
    API-key-authenticated admin endpoint for backfilling historical UAT results
    when PL browser session is unavailable. Use only for documented historical records.
    REQ-004 (MP-UAT-001): backfill HM22 and HM24 empty specs.
    """
    _validate_uuid(spec_id)
    api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    if not api_key or api_key not in (settings.MCP_API_KEY, settings.API_KEY):
        raise HTTPException(status_code=403, detail="API key required for admin backfill")

    row = execute_query(
        "SELECT id, test_cases_json, spec_source, status, pth FROM uat_pages WHERE id = ?",
        (spec_id,), fetch="one"
    )
    if not row:
        raise HTTPException(404, f"UAT spec {spec_id} not found")
    if row.get("spec_source") != "cc_spec":
        raise HTTPException(400, "Admin backfill only allowed for cc_spec UATs")

    existing_cases = json.loads(row["test_cases_json"]) if row.get("test_cases_json") else []
    updates_by_id = {tc.id: tc for tc in body.test_cases}

    for case in existing_cases:
        if case.get("id", "").startswith("_"):
            continue
        update = updates_by_id.get(case["id"])
        if update:
            case["status"] = update.status
            if update.notes is not None:
                case["notes"] = update.notes

    real_cases = [c for c in existing_cases if not c.get("id", "").startswith("_")]
    passed = sum(1 for c in real_cases if c.get("status") == "pass")
    failed = sum(1 for c in real_cases if c.get("status") == "fail")
    skipped = sum(1 for c in real_cases if c.get("status") == "skip")
    total = len(real_cases)

    if failed > 0:
        new_status = "failed"
    elif passed == total:
        new_status = "passed"
    elif failed == 0 and (passed + skipped) == total:
        new_status = "conditional_pass"
    else:
        new_status = "in_progress"

    # MP24 REQ-057: serialize general_notes as JSON if list
    admin_gn = body.general_notes
    if isinstance(admin_gn, list):
        admin_gn = json.dumps(admin_gn)
    execute_query("""
        UPDATE uat_pages
        SET test_cases_json = ?, status = ?, pl_submitted_at = GETUTCDATE(), general_notes = ?
        WHERE id = ?
    """, (json.dumps(existing_cases), new_status, admin_gn, spec_id), fetch="none")

    # Persist individual BV items to uat_bv_items table
    title_lookup = {c["id"]: c.get("title", "") for c in real_cases}
    for tc in body.test_cases:
        try:
            bv_title = title_lookup.get(tc.id, "")
            execute_query("""
                IF EXISTS (SELECT 1 FROM uat_bv_items WHERE spec_id=? AND bv_id=?)
                    UPDATE uat_bv_items SET status=?, notes=?, updated_at=GETUTCDATE()
                    WHERE spec_id=? AND bv_id=?
                ELSE
                    INSERT INTO uat_bv_items (spec_id, bv_id, title, status, notes)
                    VALUES (?, ?, ?, ?, ?)
            """, (
                spec_id, tc.id,
                tc.status or "pending", tc.notes or "",
                spec_id, tc.id,
                spec_id, tc.id, bv_title,
                tc.status or "pending", tc.notes or "",
            ), fetch="none")
        except Exception as bv_err:
            logger.warning(f"BV item upsert failed for {tc.id}: {bv_err}")

    logger.info(f"[ADMIN-BACKFILL] spec={spec_id} PTH={row.get('pth')} reason='{body.backfill_reason}' "
                f"status={new_status} {passed}P/{failed}F/{skipped}S")

    return {
        "spec_id": spec_id,
        "status": new_status,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "backfill_reason": body.backfill_reason,
    }


# ── UAT spec interactive page renderer ──────────────────────────────────────

def render_spec_uat_page(spec_id: str, spec_data: dict, test_cases: list,
                          current_results: list, pl_email: str,
                          general_notes: str = "", is_submitted: bool = False,
                          spec_status: str = "in_progress") -> str:
    """Render the interactive UAT page for an authenticated PL session.

    MP44 REQ-080: Refactored to orchestrate extracted modules.
    Card rendering → uat_renderer, notes → uat_notes, page assembly → uat_payload.
    """
    from html import escape as esc
    from app.api.uat_renderer import render_bv_cards_section
    from app.api.uat_notes import render_general_notes
    from app.api.uat_payload import build_page_html, _PROJECT_NAMES

    _raw_project = spec_data.get("project") or spec_data.get("project_id") or "Unknown"
    project = esc(_PROJECT_NAMES.get(_raw_project, _raw_project))
    version = esc(spec_data.get("version", "?"))
    sprint = esc(spec_data.get("sprint", ""))
    pth = esc(spec_data.get("pth", ""))
    reqs = ", ".join(spec_data.get("linked_requirements", []))

    # Separate sentinel entries (general notes attachments) from real test cases
    real_test_cases = [tc for tc in test_cases if not tc.get("id", "").startswith("_")]
    gn_sentinel = next((tc for tc in test_cases if tc.get("id") == "_general_notes"), None)
    gn_stored_attachments = gn_sentinel.get("attachments", []) if gn_sentinel else []

    # Build result lookup
    result_by_id = {tc["id"]: tc for tc in current_results if not tc.get("id", "").startswith("_")}
    submitted_cls = "submitted" if is_submitted else ""

    # Render BV cards via uat_renderer
    cards_html = render_bv_cards_section(real_test_cases, result_by_id,
                                         submitted_cls, is_submitted)

    # Render general notes via uat_notes
    notes_html = render_general_notes(gn_stored_attachments, is_submitted)

    # Pre-populate existing notes JSON for JS
    general_notes_json = json.dumps(_parse_general_notes(general_notes))

    # Assemble full page via uat_payload
    return build_page_html(
        project=project, version=version, sprint=sprint, pth=pth,
        reqs=reqs, pl_email=pl_email, spec_id=spec_id,
        cards_html=cards_html, notes_html=notes_html,
        is_submitted=is_submitted, spec_status=spec_status,
        general_notes_json=general_notes_json,
    )
