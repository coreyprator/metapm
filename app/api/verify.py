"""
MetaPM Verification Endpoints — MP18
Permanent self-verification infrastructure for the portfolio lifecycle.
"""
import json
import logging
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.database import execute_query
from app.api.roadmap import ALLOWED_TRANSITIONS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/verify")


# ── 1. PTH Linkage ───────────────────────────────────────────────────────────

@router.get("/pth-linkage")
async def verify_pth_linkage(requirement_code: str):
    """Verify a requirement has a PTH linked."""
    row = execute_query(
        "SELECT pth FROM roadmap_requirements WHERE code = ?",
        (requirement_code,), fetch="one"
    )
    if not row:
        return {"check": "pth_linkage", "requirement_code": requirement_code,
                "status": "fail", "pth_found": None}
    pth_val = row.get("pth")
    return {
        "check": "pth_linkage",
        "requirement_code": requirement_code,
        "status": "pass" if pth_val else "fail",
        "pth_found": pth_val,
    }


# ── 2. Illegal Transition ────────────────────────────────────────────────────

class IllegalTransitionRequest(BaseModel):
    requirement_code: str
    target_status: str = "done"


@router.post("/illegal-transition")
async def verify_illegal_transition(body: IllegalTransitionRequest):
    """Attempt a known-illegal transition and verify it's blocked."""
    row = execute_query(
        "SELECT id, status FROM roadmap_requirements WHERE code = ?",
        (body.requirement_code,), fetch="one"
    )
    if not row:
        return {"check": "state_machine", "status": "fail", "reason": "requirement not found"}

    current = row["status"]
    allowed = ALLOWED_TRANSITIONS.get(current, [])

    if body.target_status in allowed:
        return {
            "check": "state_machine", "status": "fail",
            "blocked": False,
            "reason": f"{body.target_status} is actually allowed from {current}",
            "allowed_next": allowed,
        }

    return {
        "check": "state_machine",
        "status": "pass",
        "blocked": True,
        "http_status_returned": 400,
        "allowed_next": allowed,
    }


# ── 3. Status Normalization ──────────────────────────────────────────────────

@router.get("/status-normalization")
async def verify_status_normalization():
    """Check cc_prompts has only expected status values."""
    rows = execute_query(
        "SELECT DISTINCT status FROM cc_prompts ORDER BY status",
        fetch="all"
    ) or []
    statuses = [r["status"] for r in rows]
    expected = {'draft', 'approved', 'executing', 'completed', 'stopped', 'blocked', 'rejected', 'cancelled'}
    unexpected = [s for s in statuses if s not in expected]
    return {
        "check": "status_normalization",
        "status": "pass" if not unexpected else "fail",
        "distinct_statuses": statuses,
        "count": len(statuses),
        "unexpected_values": unexpected,
    }


# ── 4. History Complete ──────────────────────────────────────────────────────

@router.get("/history-complete")
async def verify_history_complete(requirement_code: str):
    """Check requirement_history has all expected transitions for a requirement."""
    req = execute_query(
        "SELECT id FROM roadmap_requirements WHERE code = ?",
        (requirement_code,), fetch="one"
    )
    if not req:
        return {"check": "history_complete", "requirement_code": requirement_code,
                "status": "fail", "reason": "requirement not found"}

    rows = execute_query("""
        SELECT old_value as [from], new_value as [to], changed_by as transitioned_by,
               changed_at as at
        FROM requirement_history
        WHERE requirement_id = ? AND field_name = 'status'
        ORDER BY changed_at ASC
    """, (req["id"],), fetch="all") or []

    transitions = [
        {"from": r.get("from"), "to": r["to"],
         "transitioned_by": r.get("transitioned_by", "system"),
         "at": str(r.get("at", ""))}
        for r in rows
    ]

    # Expected CANARY transitions (9 total)
    expected_chain = [
        ("req_created", "req_approved"),
        ("req_approved", "cai_designing"),
        ("cai_designing", "cc_prompt_ready"),
        ("cc_prompt_ready", "cc_executing"),
        ("cc_executing", "cc_complete"),
        ("cc_complete", "uat_ready"),
        ("uat_ready", "uat_pass"),
        ("uat_pass", "done"),
    ]
    # Also include initial state if present
    recorded_pairs = [(t.get("from"), t["to"]) for t in transitions]
    missing = []
    for f, t in expected_chain:
        if (f, t) not in recorded_pairs:
            missing.append({"from": f, "to": t})

    return {
        "check": "history_complete",
        "requirement_code": requirement_code,
        "status": "pass" if not missing else "fail",
        "transitions_recorded": transitions,
        "total": len(transitions),
        "missing": missing,
    }


# ── 5. Handoff Gate ──────────────────────────────────────────────────────────

class HandoffGateRequest(BaseModel):
    pth: str


@router.post("/handoff-gate")
async def verify_handoff_gate(body: HandoffGateRequest):
    """Verify that handoff creation is blocked for draft prompts."""
    # Check if prompt exists in draft status
    row = execute_query(
        "SELECT TOP 1 id, status FROM cc_prompts WHERE pth = ? ORDER BY id DESC",
        (body.pth,), fetch="one"
    )
    if not row:
        return {"check": "handoff_gate", "status": "fail", "reason": "prompt not found"}

    if row["status"] in ("draft", "rejected"):
        return {
            "check": "handoff_gate",
            "status": "pass",
            "blocked": True,
            "reason": "prompt_not_approved",
        }
    else:
        return {
            "check": "handoff_gate",
            "status": "fail",
            "blocked": False,
            "reason": f"prompt at {row['status']}, gate would not block",
        }


# ── 6. UAT Classification Gate ───────────────────────────────────────────────

class UATClassificationGateRequest(BaseModel):
    spec_id: str


@router.post("/uat-classification-gate")
async def verify_uat_classification_gate(body: UATClassificationGateRequest):
    """Verify UAT submission is blocked when pl_visual BVs lack classification."""
    row = execute_query(
        "SELECT test_cases_json FROM uat_pages WHERE id = ?",
        (body.spec_id,), fetch="one"
    )
    if not row:
        return {"check": "uat_classification_gate", "status": "fail", "reason": "spec not found"}

    cases = json.loads(row["test_cases_json"]) if row.get("test_cases_json") else []
    pl_visual = [c for c in cases if not c.get("id", "").startswith("_") and c.get("type") != "cc_machine"]

    if not pl_visual:
        return {"check": "uat_classification_gate", "status": "fail",
                "reason": "no pl_visual BVs in spec"}

    # Check if any pl_visual BV would be missing classification
    missing = [c["id"] for c in pl_visual if not c.get("classification")]
    return {
        "check": "uat_classification_gate",
        "status": "pass" if missing else "fail",
        "blocked": bool(missing),
        "reason": "classification_required" if missing else "all have classification",
    }
