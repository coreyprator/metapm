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
from typing import List, Optional
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


class PLResultsTestCase(BaseModel):
    id: str
    status: str  # pass | fail | skip | pending
    notes: Optional[str] = None
    attachments: Optional[List[dict]] = None  # MP07: image/file evidence
    classification: Optional[str] = None  # MP18 REQ-047: New requirement | Bug | Finding | No-action


class PLResultsSubmit(BaseModel):
    test_cases: List[PLResultsTestCase]
    overall_notes: Optional[str] = None
    general_notes: Optional[str] = None  # Fix 2d: persisted to DB
    general_notes_attachments: Optional[List[dict]] = None  # MP07
    submitted_by: Optional[str] = None


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
        "SELECT TOP 1 id FROM uat_pages WHERE pth = ? AND spec_source = 'cc_spec' ORDER BY created_at DESC",
        (body.pth,), fetch="one"
    )

    if existing:
        # UPDATE existing spec — preserve ID, reset test cases
        spec_id = str(existing["id"])
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

    # MP18 REQ-047: Identify pl_visual vs cc_machine BVs
    pl_visual_ids = set()
    for c in existing_cases:
        if c.get("id", "").startswith("_"):
            continue
        if c.get("type") != "cc_machine":
            pl_visual_ids.add(c["id"])

    # MP18 REQ-047: Server-side validation — all pl_visual BVs must have status and classification
    updates_by_id = {tc.id: tc for tc in body.test_cases}
    missing_classification = []
    pending_bv_ids = []
    for bv_id in pl_visual_ids:
        tc = updates_by_id.get(bv_id)
        if tc:
            if not tc.classification:
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

    # Fix 2d: persist general_notes
    execute_query("""
        UPDATE uat_pages
        SET test_cases_json = ?,
            status = ?,
            pl_submitted_at = GETUTCDATE(),
            general_notes = ?
        WHERE id = ?
    """, (json.dumps(existing_cases), new_status, body.general_notes or body.overall_notes, spec_id), fetch="none")

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

    # MF01: persist individual BV items to uat_bv_items table
    title_lookup = {c["id"]: c.get("title", "") for c in real_cases}
    for tc in body.test_cases:
        try:
            bv_title = title_lookup.get(tc.id, "")
            execute_query("""
                IF EXISTS (SELECT 1 FROM uat_bv_items WHERE spec_id=? AND bv_id=?)
                    UPDATE uat_bv_items
                    SET status=?, notes=?, classification=?, updated_at=GETUTCDATE()
                    WHERE spec_id=? AND bv_id=?
                ELSE
                    INSERT INTO uat_bv_items (spec_id, bv_id, title, status, notes, classification)
                    VALUES (?, ?, ?, ?, ?, ?)
            """, (
                spec_id, tc.id,                                              # EXISTS check
                tc.status or 'pending', tc.notes or '', tc.classification,   # UPDATE SET
                spec_id, tc.id,                                              # UPDATE WHERE
                spec_id, tc.id, bv_title,                                    # INSERT
                tc.status or 'pending', tc.notes or '', tc.classification,   # INSERT values
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
    Resets status to 'ready' and all test case statuses to pending.
    Accepts PL Google OAuth session OR X-API-Key header.
    """
    _validate_uuid(spec_id)
    # Accept either PL session or API key
    api_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    expected_key = settings.MCP_API_KEY or ""
    has_api_key = api_key and api_key == expected_key
    if not is_pl_authenticated(request) and not has_api_key:
        raise HTTPException(status_code=403, detail="PL authentication or API key required")

    row = execute_query(
        "SELECT id, test_cases_json, status FROM uat_pages WHERE id = ?",
        (spec_id,), fetch="one"
    )
    if not row:
        raise HTTPException(404, f"UAT spec {spec_id} not found")

    # Reset test case statuses to pending and clear notes
    existing_cases = json.loads(row["test_cases_json"]) if row.get("test_cases_json") else []
    for case in existing_cases:
        if case.get("id", "").startswith("_"):
            continue
        case["status"] = "pending"
        case["notes"] = ""
        case.pop("attachments", None)

    execute_query("""
        UPDATE uat_pages
        SET status = 'ready',
            test_cases_json = ?,
            pl_submitted_at = NULL,
            general_notes = NULL
        WHERE id = ?
    """, (json.dumps(existing_cases), spec_id), fetch="none")

    logger.info(f"UAT spec {spec_id} reopened — status reset to ready, test cases reset to pending")
    return {"status": "reopened", "spec_id": spec_id}


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
        "general_notes": row.get("general_notes") or "",
    }


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

    execute_query("""
        UPDATE uat_pages
        SET test_cases_json = ?, status = ?, pl_submitted_at = GETUTCDATE(), general_notes = ?
        WHERE id = ?
    """, (json.dumps(existing_cases), new_status, body.general_notes, spec_id), fetch="none")

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
    """Render the interactive UAT page for an authenticated PL session."""
    from html import escape as esc
    _PROJECT_NAMES = {
        'proj-mp': 'MetaPM', 'proj-sf': 'Super Flashcards',
        'proj-hl': 'HarmonyLab', 'proj-af': 'ArtForge',
        'proj-em': 'Etymython', 'proj-efg': 'Etymology Graph',
        'proj-pr': 'Portfolio RAG', 'proj-pa': 'Personal Assistant',
        'proj-pm': 'project-methodology', 'EFG': 'Etymology Graph',
    }
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

    # Build result lookup from current_results (test_cases_json with statuses)
    result_by_id = {tc["id"]: tc for tc in current_results if not tc.get("id", "").startswith("_")}
    submitted_cls = "submitted" if is_submitted else ""
    submitted_badge = '<span class="read-only-badge">✓ Submitted</span>' if is_submitted else ""
    resubmit_btn = f'<button class="btn btn-resubmit" onclick="reopenUAT(\'{spec_id}\')">↩ Reopen &amp; Edit Results</button>' if is_submitted else ""
    # REQ-011: PL-only override button for conditional_pass
    mark_passed_btn = ('<button class="btn btn-mark-passed" onclick="markAsPassed()">'
                       '✅ Mark as Passed</button>') if spec_status == "conditional_pass" else ""

    # MP13A REQ-038: split test cases by type (cc_machine vs pl_visual)
    cc_machine_tcs = [tc for tc in real_test_cases if tc.get("type") == "cc_machine"]
    pl_visual_tcs = [tc for tc in real_test_cases if tc.get("type", "pl_visual") != "cc_machine"]

    def _render_machine_card(tc):
        tid = esc(tc["id"])
        title = esc(tc["title"])
        current = result_by_id.get(tc["id"], {})
        cur_status = current.get("status", "pending")
        cur_notes = esc(current.get("notes", ""))
        status_icons = {"pass": "✓", "fail": "✗", "skip": "○", "pending": "?"}
        icon = status_icons.get(cur_status, "?")
        return f"""
        <div class="test-card result-{cur_status} submitted" data-id="{tid}" data-type="cc_machine">
          <div class="test-header">
            <span class="test-id">{tid}</span>
            <span class="test-name">{title}</span>
          </div>
          <div style="font-size:0.85rem;color:var(--muted);margin-top:4px">{cur_notes}</div>
        </div>"""

    def _render_pl_card(tc):
        tid = esc(tc["id"])
        title = esc(tc["title"])
        url = tc.get("url", "")
        steps = tc.get("steps", [])
        expected = esc(tc.get("expected", ""))
        current = result_by_id.get(tc["id"], {})
        cur_status = current.get("status", "pending")
        cur_notes = esc(current.get("notes", ""))
        cur_class = current.get("classification", "")
        steps_html = "".join(f"<li>{esc(s)}</li>" for s in steps)
        url_html = f'<a href="{esc(url)}" target="_blank" class="bv-url">{esc(url)}</a>' if url else ""
        def checked(val):
            return " checked" if cur_status == val else ""
        def cls_selected(val):
            return " selected" if cur_class == val else ""
        return f"""
        <div class="test-card result-{cur_status} {submitted_cls}" data-id="{tid}">
          <div class="test-header">
            <span class="test-id">{tid}</span>
            <span class="test-name">{title}</span>
          </div>
          {url_html}
          <ol class="test-steps">{steps_html}</ol>
          <div class="expected">Expected: {expected}</div>
          <div class="radio-group">
            <label class="radio-label{' checked-pass' if cur_status=='pass' else ''}">
              <input type="radio" name="{tid}" value="pass"{checked('pass')}> ✓ Pass</label>
            <label class="radio-label{' checked-fail' if cur_status=='fail' else ''}">
              <input type="radio" name="{tid}" value="fail"{checked('fail')}> ✗ Fail</label>
            <label class="radio-label{' checked-skip' if cur_status=='skip' else ''}">
              <input type="radio" name="{tid}" value="skip"{checked('skip')}> ○ Skip</label>
            <label class="radio-label{' checked-pending' if cur_status=='pending' else ''}">
              <input type="radio" name="{tid}" value="pending"{checked('pending')}> ? Pending</label>
          </div>
          <div class="notes-label" style="margin-top:8px">Classification (required)</div>
          <select class="classification-select" data-id="{tid}" style="width:100%;padding:7px 10px;background:#0d1117;border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:0.85rem;margin-bottom:8px">
            <option value="">— Select —</option>
            <option value="New requirement"{cls_selected("New requirement")}>New requirement</option>
            <option value="Bug"{cls_selected("Bug")}>Bug</option>
            <option value="Finding"{cls_selected("Finding")}>Finding</option>
            <option value="No-action"{cls_selected("No-action")}>No-action</option>
          </select>
          <div class="notes-label">Notes</div>
          <textarea class="notes-input" placeholder="Observations...">{cur_notes}</textarea>
          {'' if is_submitted else f'<div class="paste-zone" id="paste-{tid}" data-id="{tid}" tabindex="0" contenteditable="false">📷 Paste screenshot here (Ctrl+V)</div>'}
          <div class="attach-row">
            <label class="attach-btn">📎 Attach file<input type="file" class="attach-input" accept="image/*,.pdf" data-id="{tid}" {'disabled' if is_submitted else ''}></label>
            <span class="attach-name" id="aname-{tid}"></span>
          </div>
          <div class="attach-thumb" id="athumb-{tid}">{''.join(f'<img src="data:{a.get("mime","image/png")};base64,{a["data"]}" title="{esc(a.get("filename","attachment"))}">' for a in (current.get("attachments") or []) if a.get("data"))}</div>
        </div>"""

    # Build section HTML
    machine_section = ""
    if cc_machine_tcs:
        machine_cards = "".join(_render_machine_card(tc) for tc in cc_machine_tcs)
        machine_section = f"""
        <div class="uat-section-machine" style="margin-bottom:20px;opacity:0.85">
          <h3 style="font-size:1rem;color:var(--pass);margin-bottom:8px">✓ Machine-verified by CC — {len(cc_machine_tcs)} items</h3>
          <p style="font-size:0.85rem;color:var(--muted);margin-bottom:12px">These were verified programmatically by CC before handoff. No action required.</p>
          {machine_cards}
        </div>"""

    pl_section = ""
    if pl_visual_tcs:
        pl_cards = "".join(_render_pl_card(tc) for tc in pl_visual_tcs)
        pl_section = f"""
        <div class="uat-section-pl">
          <h3 style="font-size:1rem;color:var(--accent);margin-bottom:12px">Your input required — {len(pl_visual_tcs)} items</h3>
          {pl_cards}
        </div>"""
    elif cc_machine_tcs:
        pl_section = f"""
        <div class="uat-section-pl" style="text-align:center;padding:20px">
          <p style="color:var(--muted);margin-bottom:12px">All BVs were machine-verified. No action required.</p>
          <button class="btn btn-submit" onclick="submitAcknowledge()">Acknowledge &amp; Close</button>
        </div>"""

    cards_html = machine_section + pl_section

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{project} v{version} — UAT</title>
  <style>
    :root {{
      --bg: #0f1117; --card: #161b22; --border: #30363d;
      --accent: #58a6ff; --pass: #3fb950; --fail: #f85149;
      --skip: #8b949e; --pending: #d29922; --text: #c9d1d9; --muted: #8b949e;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: var(--bg); color: var(--text); padding: 24px 16px;
      max-width: 860px; margin: 0 auto; line-height: 1.6; }}
    header {{ background: var(--card); border: 1px solid var(--border);
      border-left: 4px solid var(--accent); border-radius: 8px;
      padding: 20px; margin-bottom: 20px; }}
    header h1 {{ font-size: 1.3rem; color: #e6edf3; }}
    .meta {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }}
    .chip {{ background: rgba(88,166,255,0.1); border: 1px solid rgba(88,166,255,0.3);
      color: var(--accent); font-size: 0.8rem; padding: 3px 10px; border-radius: 12px; }}
    .reqs {{ margin-top: 10px; font-size: 0.85rem; color: var(--muted); }}
    .pl-info {{ font-size: 0.8rem; color: var(--muted); margin-top: 8px; }}
    .summary-bar {{ display: flex; gap: 10px; flex-wrap: wrap;
      background: var(--card); border: 1px solid var(--border);
      border-radius: 8px; padding: 14px 18px; margin-bottom: 20px; align-items: center; }}
    .summary-bar .label {{ font-size: 0.8rem; color: var(--muted); }}
    .count {{ padding: 4px 14px; border-radius: 12px; font-weight: 700; font-size: 0.9rem; }}
    .ct-total {{ background: #21262d; color: var(--text); }}
    .ct-pass {{ background: rgba(63,185,80,0.15); color: var(--pass); }}
    .ct-fail {{ background: rgba(248,81,73,0.15); color: var(--fail); }}
    .ct-skip {{ background: rgba(139,148,158,0.15); color: var(--skip); }}
    .ct-pend {{ background: rgba(210,153,34,0.15); color: var(--pending); }}
    .test-card {{ background: var(--card); border: 1px solid var(--border);
      border-radius: 8px; padding: 14px 16px; margin-bottom: 10px;
      transition: border-color 0.2s; }}
    .test-card.result-pass {{ border-left: 3px solid var(--pass); }}
    .test-card.result-fail {{ border-left: 3px solid var(--fail); }}
    .test-card.result-skip {{ border-left: 3px solid var(--skip); }}
    .test-card.result-pending {{ border-left: 3px solid var(--pending); }}
    .test-header {{ display: flex; gap: 10px; align-items: flex-start; flex-wrap: wrap; margin-bottom: 8px; }}
    .test-id {{ font-family: monospace; font-size: 0.85rem; color: var(--muted); flex-shrink: 0; }}
    .test-name {{ flex: 1; font-weight: 500; color: #e6edf3; }}
    .bv-url {{ display: block; font-size: 0.82rem; color: var(--accent);
      margin-bottom: 8px; text-decoration: none; }}
    .bv-url:hover {{ text-decoration: underline; }}
    .test-steps {{ font-size: 0.85rem; color: var(--muted); padding-left: 18px;
      margin-bottom: 8px; }}
    .expected {{ font-size: 0.82rem; color: #6e7681; font-style: italic;
      margin-bottom: 10px; }}
    .radio-group {{ display: flex; gap: 6px; flex-wrap: wrap; margin: 8px 0; }}
    .radio-label {{ display: flex; align-items: center; gap: 5px;
      padding: 5px 12px; border-radius: 6px; border: 1px solid var(--border);
      cursor: pointer; font-size: 0.85rem; user-select: none; transition: all 0.15s; }}
    .radio-label:hover {{ border-color: var(--accent); }}
    .radio-label input[type=radio] {{ display: none; }}
    .radio-label.checked-pass {{ background: rgba(63,185,80,0.2); border-color: var(--pass); color: var(--pass); font-weight: 600; }}
    .radio-label.checked-fail {{ background: rgba(248,81,73,0.2); border-color: var(--fail); color: var(--fail); font-weight: 600; }}
    .radio-label.checked-skip {{ background: rgba(139,148,158,0.2); border-color: var(--skip); color: var(--skip); font-weight: 600; }}
    .radio-label.checked-pending {{ background: rgba(210,153,34,0.2); border-color: var(--pending); color: var(--pending); font-weight: 600; }}
    .notes-label {{ font-size: 0.75rem; color: var(--muted); margin-bottom: 4px; }}
    .notes-input {{ width: 100%; padding: 7px 10px; background: #0d1117;
      border: 1px solid var(--border); border-radius: 6px; color: var(--text);
      font-family: inherit; font-size: 0.85rem; resize: vertical; min-height: 36px; }}
    .notes-input:focus {{ outline: none; border-color: var(--accent); }}
    .general-notes {{ background: var(--card); border: 1px solid var(--border);
      border-radius: 8px; padding: 16px; margin-bottom: 20px; }}
    .general-notes textarea {{ width: 100%; min-height: 80px; padding: 10px 12px;
      background: #0d1117; border: 1px solid var(--border); border-radius: 6px;
      color: var(--text); font-family: inherit; font-size: 0.9rem; resize: vertical; }}
    .general-notes textarea:focus {{ outline: none; border-color: #bc8cff; }}
    .general-notes-title {{ font-size: 1rem; font-weight: 600; color: #bc8cff;
      border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 12px; }}
    .btn-row {{ display: flex; gap: 12px; justify-content: center; margin-top: 24px; }}
    .btn {{ padding: 11px 28px; border: none; border-radius: 8px;
      font-size: 0.95rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }}
    .btn:hover {{ opacity: 0.85; }}
    .btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
    .btn-submit {{ background: var(--pass); color: #0d1117; }}

    .btn-resubmit {{ background: #21262d; color: var(--text); border: 1px solid var(--border); }}
    .btn-mark-passed {{ background: #b45309; color: #fff; }}
    #submit-result {{ margin-top: 16px; padding: 14px 18px; border-radius: 8px;
      font-size: 0.9rem; display: none; }}
    #submit-result.ok {{ background: rgba(63,185,80,0.15); border: 1px solid var(--pass); }}
    #submit-result.err {{ background: rgba(248,81,73,0.15); border: 1px solid var(--fail); }}
    #submit-result a {{ color: var(--accent); }}
    .read-only-badge {{ display: inline-block; background: rgba(63,185,80,0.15);
      border: 1px solid var(--pass); color: var(--pass); padding: 4px 12px;
      border-radius: 6px; font-size: 0.8rem; font-weight: 600; margin-left: 12px; }}
    .test-card.submitted .radio-label {{ pointer-events: none; opacity: 0.85; }}
    .test-card.submitted .notes-input {{ background: #0a0e17; pointer-events: none; }}
    .paste-zone {{ border: 2px dashed var(--border); border-radius: 6px; padding: 8px 12px;
      margin-top: 8px; font-size: 0.82rem; color: var(--muted); cursor: text;
      transition: border-color 0.2s; user-select: none; }}
    .paste-zone:focus, .paste-zone.drag-over {{ border-color: var(--accent); outline: none; }}
    .paste-zone.has-image {{ border-color: var(--pass); color: var(--pass); }}
    .attach-row {{ display: flex; align-items: center; gap: 8px; margin-top: 6px; }}
    .attach-btn {{ display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px;
      background: #21262d; border: 1px solid var(--border); border-radius: 6px;
      font-size: 0.82rem; cursor: pointer; color: var(--text); }}
    .attach-btn:hover {{ border-color: var(--accent); }}
    .attach-btn input[type=file] {{ display: none; }}
    .attach-name {{ font-size: 0.78rem; color: var(--muted); }}
    .attach-thumb {{ margin-top: 6px; }}
    .attach-thumb img {{ max-width: 160px; max-height: 120px; border-radius: 4px;
      border: 1px solid var(--border); }}
  </style>
</head>
<body>
  <header>
    <h1>{project} v{version} — UAT {submitted_badge}</h1>
    <div class="meta">
      <span class="chip">v{version}</span>
      <span class="chip">PTH: {pth}</span>
      <span class="chip">{sprint}</span>
    </div>
    <div class="reqs"><strong>Requirements:</strong> {esc(reqs)}</div>
    <div class="pl-info">Authenticated as {esc(pl_email)} · <a href="/app/logout" style="color:var(--muted);font-size:0.8rem">Sign out</a></div>
  </header>

  <div class="summary-bar">
    <span class="label">Total</span><span class="count ct-total" id="cnt-total">0</span>
    <span class="label">Pass</span><span class="count ct-pass" id="cnt-pass">0</span>
    <span class="label">Fail</span><span class="count ct-fail" id="cnt-fail">0</span>
    <span class="label">Skip</span><span class="count ct-skip" id="cnt-skip">0</span>
    <span class="label">Pending</span><span class="count ct-pend" id="cnt-pend">0</span>
  </div>

  {cards_html}

  <div class="general-notes">
    <div class="general-notes-title">General Notes</div>
    <textarea id="general-notes" placeholder="Overall observations..." {'readonly' if is_submitted else ''}>{esc(general_notes)}</textarea>
    {'' if is_submitted else '<div class="paste-zone" id="gn-paste-zone" tabindex="0" contenteditable="false">📷 Paste screenshot here (Ctrl+V)</div>'}
    <div class="attach-row">
      <label class="attach-btn">📎 Attach file<input type="file" id="gn-attach-input" accept="image/*,.pdf" {'disabled' if is_submitted else ''}></label>
      <span class="attach-name" id="gn-attach-name"></span>
    </div>
    <div class="attach-thumb" id="gn-attach-thumb">{''.join(f'<img src="data:{a.get("mime","image/png")};base64,{a["data"]}" title="{esc(a.get("filename","attachment"))}">' for a in gn_stored_attachments if a.get("data"))}</div>
  </div>

  <div class="btn-row">
    <button class="btn btn-submit" id="submit-btn" onclick="submitResults()" {'style="display:none"' if is_submitted else ''}>📤 Submit Results</button>
    {resubmit_btn}
    {mark_passed_btn}
  </div>
  {'<div style="font-size:11px;color:#94a3b8;margin-top:6px;text-align:center">⚡ Submitting fires Loop 3 automatically — requirements will be advanced within 2 minutes.</div>' if not is_submitted else ''}
  <div id="submit-result" {'class="ok" style="display:block"' if is_submitted else ''}>{f'Results submitted. <a href="/uat/{spec_id}">View UAT record →</a>' if is_submitted else ''}</div>

  <script>
    const SPEC_ID = "{spec_id}";

    function updateCounts() {{
      const cards = document.querySelectorAll('.test-card:not([data-type="cc_machine"])');
      const machineCards = document.querySelectorAll('.test-card[data-type="cc_machine"]');
      let pass=0,fail=0,skip=0,pend=0;
      cards.forEach(card => {{
        const id = card.dataset.id;
        const checked = card.querySelector(`input[name="${{id}}"]:checked`);
        const val = checked ? checked.value : 'pending';
        card.querySelectorAll('.radio-label').forEach(l => l.className = l.className.replace(/\\bchecked-\\w+/g,''));
        if (checked) checked.closest('.radio-label')?.classList.add(`checked-${{val}}`);
        card.className = card.className.replace(/\\bresult-\\w+/g,'') + ` result-${{val}}`;
        if (val==='pass') pass++; else if(val==='fail') fail++; else if(val==='skip') skip++; else pend++;
      }});
      // Count machine-verified as passes
      machineCards.forEach(card => {{ pass++; }});
      document.getElementById('cnt-total').textContent = cards.length + machineCards.length;
      document.getElementById('cnt-pass').textContent = pass;
      document.getElementById('cnt-fail').textContent = fail;
      document.getElementById('cnt-skip').textContent = skip;
      document.getElementById('cnt-pend').textContent = pend;
    }}

    document.querySelectorAll('.radio-group input[type=radio]').forEach(r => r.addEventListener('change', updateCounts));
    updateCounts();

    // MP16C BUG-034: Replace collapsed textareas with auto-sized divs on submitted UAT pages
    if (document.querySelector('.test-card.submitted')) {{
      document.querySelectorAll('textarea.notes-input').forEach(ta => {{
        if (!ta.value.trim()) {{
          const wrap = ta.closest('.test-card');
          const label = wrap?.querySelector('.notes-label');
          if (label) label.remove();
          ta.remove();
          return;
        }}
        const div = document.createElement('div');
        div.className = 'notes-display';
        div.style.cssText = 'font-size:13px;line-height:1.5;white-space:pre-wrap;word-break:break-word;padding:6px 8px;margin:0;color:var(--text);';
        div.textContent = ta.value.trim();
        ta.parentNode.replaceChild(div, ta);
      }});
      const gn = document.getElementById('general-notes');
      if (gn && gn.hasAttribute('readonly')) {{
        if (!gn.value.trim()) {{
          gn.closest('.general-notes')?.remove();
        }} else {{
          const div = document.createElement('div');
          div.className = 'notes-display';
          div.style.cssText = 'font-size:13px;line-height:1.5;white-space:pre-wrap;word-break:break-word;padding:6px 8px;margin:0;color:var(--text);';
          div.textContent = gn.value.trim();
          gn.parentNode.replaceChild(div, gn);
        }}
      }}
    }}

    // ── Attachment support (MP07) ──
    const attachmentsMap = {{}};
    let generalNotesAttachments = [];

    function blobToBase64(blob) {{
      return new Promise(resolve => {{
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.readAsDataURL(blob);
      }});
    }}

    function showThumbInEl(el, mime, b64) {{
      if (el) el.innerHTML = `<img src="data:${{mime}};base64,${{b64}}">`;
    }}

    document.querySelectorAll('.paste-zone').forEach(zone => {{
      zone.addEventListener('paste', async e => {{
        e.preventDefault();
        const items = Array.from(e.clipboardData.items);
        const imgItem = items.find(i => i.type.startsWith('image/'));
        if (!imgItem) return;
        const b64 = await blobToBase64(imgItem.getAsFile());
        const att = [{{type:'image', mime: imgItem.type, data: b64, filename:'screenshot.png'}}];
        const id = zone.dataset.id;
        if (id) {{
          attachmentsMap[id] = att;
          showThumbInEl(document.getElementById(`athumb-${{id}}`), imgItem.type, b64);
        }} else {{
          generalNotesAttachments = att;
          showThumbInEl(document.getElementById('gn-attach-thumb'), imgItem.type, b64);
        }}
        zone.classList.add('has-image');
        zone.innerHTML = '✅ Screenshot captured <button class="remove-attach" onclick="removeAttach(this)" title="Remove screenshot" style="background:#7f1d1d;color:#fca5a5;border:none;border-radius:4px;padding:1px 6px;cursor:pointer;margin-left:8px;font-size:12px">✕</button>';
      }});
    }});

    function removeAttach(btn) {{
      const zone = btn.closest('.paste-zone');
      if (!zone) return;
      const id = zone.dataset.id;
      if (id) {{
        delete attachmentsMap[id];
        const thumb = document.getElementById(`athumb-${{id}}`);
        if (thumb) thumb.innerHTML = '';
      }} else {{
        generalNotesAttachments = [];
        const thumb = document.getElementById('gn-attach-thumb');
        if (thumb) thumb.innerHTML = '';
      }}
      zone.classList.remove('has-image');
      zone.innerHTML = '📷 Paste screenshot here (Ctrl+V)';
    }}

    document.querySelectorAll('.attach-input').forEach(input => {{
      input.addEventListener('change', async e => {{
        const file = e.target.files[0];
        if (!file) return;
        const b64 = await blobToBase64(file);
        const type = file.type.startsWith('image/') ? 'image' : 'file';
        const att = [{{type, mime: file.type, data: b64, filename: file.name}}];
        const id = input.dataset.id;
        attachmentsMap[id] = att;
        const nameEl = document.getElementById(`aname-${{id}}`);
        nameEl.innerHTML = `${{file.name}} (${{Math.round(file.size/1024)}}KB) <button class="remove-attach" onclick="removeFileAttach(this, '${{id}}')" title="Remove file" style="background:#7f1d1d;color:#fca5a5;border:none;border-radius:4px;padding:1px 6px;cursor:pointer;margin-left:6px;font-size:12px">✕</button>`;
        if (type === 'image') showThumbInEl(document.getElementById(`athumb-${{id}}`), file.type, b64);
      }});
    }});

    function removeFileAttach(btn, id) {{
      delete attachmentsMap[id];
      const nameEl = document.getElementById(`aname-${{id}}`);
      if (nameEl) nameEl.textContent = '';
      const thumb = document.getElementById(`athumb-${{id}}`);
      if (thumb) thumb.innerHTML = '';
      const input = document.querySelector(`.attach-input[data-id="${{id}}"]`);
      if (input) input.value = '';
    }}

    const gnInput = document.getElementById('gn-attach-input');
    if (gnInput) {{
      gnInput.addEventListener('change', async e => {{
        const file = e.target.files[0];
        if (!file) return;
        const b64 = await blobToBase64(file);
        const type = file.type.startsWith('image/') ? 'image' : 'file';
        generalNotesAttachments = [{{type, mime: file.type, data: b64, filename: file.name}}];
        document.getElementById('gn-attach-name').textContent = `${{file.name}} (${{Math.round(file.size/1024)}}KB)`;
        if (type === 'image') showThumbInEl(document.getElementById('gn-attach-thumb'), file.type, b64);
      }});
    }}

    async function reopenUAT(specId) {{
      const confirmed = confirm('Reopen this UAT for editing? Current results will be cleared.');
      if (!confirmed) return;
      const btn = document.querySelector('.btn-resubmit');
      if (btn) {{ btn.disabled = true; btn.textContent = '⏳ Reopening...'; }}
      try {{
        const r = await fetch(`/api/uat/${{specId}}/reopen`, {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}}
        }});
        if (r.ok) {{
          window.location.reload();
        }} else {{
          const data = await r.json();
          alert(`Reopen failed: ${{data.detail || JSON.stringify(data)}}`);
          if (btn) {{ btn.disabled = false; btn.textContent = '↩ Reopen & Edit Results'; }}
        }}
      }} catch(e) {{
        alert(`Reopen error: ${{e.message}}`);
        if (btn) {{ btn.disabled = false; btn.textContent = '↩ Reopen & Edit Results'; }}
      }}
    }}

    async function markAsPassed() {{
      const btn = document.querySelector('.btn-mark-passed');
      if (btn) {{ btn.disabled = true; btn.textContent = '⏳ Overriding...'; }}
      try {{
        const resp = await fetch(`/api/uat/${{SPEC_ID}}/override`, {{
          method: 'PATCH',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{ status: 'passed', override_note: 'PL override: conditional_pass → passed' }})
        }});
        const data = await resp.json();
        if (resp.ok) {{
          const div = document.getElementById('submit-result');
          div.style.display = 'block';
          div.className = 'ok';
          div.innerHTML = `Status overridden to <strong>passed</strong>. <a href="/uat/${{SPEC_ID}}">View UAT record &rarr;</a>`;
          if (btn) btn.style.display = 'none';
        }} else {{
          if (btn) {{ btn.disabled = false; btn.textContent = '✅ Mark as Passed'; }}
          alert(`Override failed: ${{data.detail || JSON.stringify(data)}}`);
        }}
      }} catch(e) {{
        if (btn) {{ btn.disabled = false; btn.textContent = '✅ Mark as Passed'; }}
        alert(`Override error: ${{e.message}}`);
      }}
    }}

    async function submitAcknowledge() {{
      // MP13A REQ-038: all BVs are cc_machine, PL just acknowledges
      if (!confirm('All items were machine-verified. Acknowledge and close?')) return;
      try {{
        const resp = await fetch(`/api/uat/${{SPEC_ID}}/pl-results`, {{
          method: 'PATCH',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{ test_cases: [], general_notes: 'All BVs machine-verified. PL acknowledged.' }})
        }});
        if (resp.ok) {{
          const div = document.getElementById('submit-result');
          div.style.display = 'block';
          div.className = 'ok';
          div.innerHTML = 'Acknowledged. <a href="/uat/' + SPEC_ID + '">View UAT record &rarr;</a>';
        }} else {{
          const data = await resp.json();
          alert('Acknowledge failed: ' + (data.detail || JSON.stringify(data)));
        }}
      }} catch(e) {{ alert('Error: ' + e.message); }}
    }}

    async function submitResults() {{
      // MP-UAT-001: Confirmation dialog before submission
      const confirmed = confirm(
        'Submit UAT results?\\n\\nThis will record your test results. ' +
        'You can reopen and edit results after submission.'
      );
      if (!confirmed) return;

      // MP13A: only submit pl_visual cards (cc_machine are pre-filled)
      const cards = document.querySelectorAll('.test-card:not([data-type="cc_machine"])');
      const test_cases = [];
      let missingClassification = [];
      cards.forEach(card => {{
        const id = card.dataset.id;
        const checked = card.querySelector(`input[name="${{id}}"]:checked`);
        const notes = card.querySelector('.notes-input')?.value || '';
        const attachments = attachmentsMap[id] || [];
        const classSelect = card.querySelector('.classification-select');
        const classification = classSelect ? classSelect.value : '';
        if (!classification) missingClassification.push(id);
        test_cases.push({{ id, status: checked ? checked.value : 'pending', notes, attachments, classification }});
      }});
      // MP18 REQ-047: block submit if classification missing
      if (missingClassification.length > 0) {{
        alert('Classification required for all BVs: ' + missingClassification.join(', '));
        return;
      }}
      const general_notes = document.getElementById('general-notes').value;

      const btn = document.getElementById('submit-btn');
      btn.disabled = true;
      btn.textContent = '⏳ Submitting...';

      try {{
        const resp = await fetch(`/api/uat/${{SPEC_ID}}/pl-results`, {{
          method: 'PATCH',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{ test_cases, general_notes, general_notes_attachments: generalNotesAttachments, submitted_by: '{pl_email}' }})
        }});
        const data = await resp.json();
        const div = document.getElementById('submit-result');
        div.style.display = 'block';
        if (resp.ok) {{
          // MP-UAT-001: POST-Redirect-GET — redirect to GET page
          // This replaces the current history entry so F5 reloads the GET page, not the form
          window.location.replace('/uat/' + SPEC_ID);
          return;
        }} else {{
          btn.disabled = false;
          btn.textContent = '📤 Submit Results';
          div.className = 'err';
          div.textContent = `Error: ${{data.detail || JSON.stringify(data)}}`;
        }}
      }} catch(e) {{
        btn.disabled = false;
        btn.textContent = '📤 Submit Results';
        const div = document.getElementById('submit-result');
        div.style.display = 'block';
        div.className = 'err';
        div.textContent = `Submit failed: ${{e.message}}`;
      }}
    }}
  </script>
</body>
</html>"""
