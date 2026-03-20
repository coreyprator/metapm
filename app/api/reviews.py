"""
MetaPM Reviews API Router
Endpoints for CAI handoff review storage and retrieval.
PF5-MS2-SESSION-B (PTH: PF01B)
"""

import json
import logging
import secrets
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.database import execute_query

logger = logging.getLogger(__name__)

router = APIRouter()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(x_api_key: Optional[str] = Depends(api_key_header)) -> bool:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    expected = settings.MCP_API_KEY or settings.API_KEY
    if not expected:
        raise HTTPException(status_code=503, detail="API key not configured")
    if x_api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True


class LessonCandidate(BaseModel):
    lesson: str
    target: str = "bootstrap"
    severity: str = "medium"


class ReviewCreate(BaseModel):
    handoff_id: str
    prompt_pth: Optional[str] = None
    assessment: str = Field(..., pattern="^(pass|conditional_pass|fail)$")
    focus_areas: Optional[List[str]] = None
    risks: Optional[List[str]] = None
    regression_zones: Optional[List[str]] = None
    lesson_candidates: Optional[List[LessonCandidate]] = None
    rework_needed: bool = False
    notes: Optional[str] = None


def _row_to_response(row: dict) -> dict:
    def parse_json(val):
        if not val:
            return None
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val

    return {
        "id": str(row["id"]),
        "handoff_id": row.get("handoff_id"),
        "prompt_pth": row.get("prompt_pth"),
        "assessment": row.get("assessment"),
        "focus_areas": parse_json(row.get("focus_areas")),
        "risks": parse_json(row.get("risks")),
        "regression_zones": parse_json(row.get("regression_zones")),
        "lesson_candidates": parse_json(row.get("lesson_candidates")),
        "rework_needed": bool(row.get("rework_needed")),
        "notes": row.get("notes"),
        "created_at": str(row["created_at"]) if row.get("created_at") else None,
    }


@router.post("", status_code=201)
async def create_review(review: ReviewCreate, _: bool = Depends(verify_api_key)):
    """Create a new handoff review (CAI calls this after reviewing)."""
    # Verify handoff exists
    handoff = execute_query(
        "SELECT id FROM mcp_handoffs WHERE id = ?",
        (review.handoff_id,), fetch="one"
    )
    if not handoff:
        raise HTTPException(status_code=404, detail=f"Handoff {review.handoff_id} not found")

    focus_json = json.dumps(review.focus_areas) if review.focus_areas else None
    risks_json = json.dumps(review.risks) if review.risks else None
    regr_json = json.dumps(review.regression_zones) if review.regression_zones else None
    lc_json = json.dumps([lc.model_dump() for lc in review.lesson_candidates]) if review.lesson_candidates else None

    result = execute_query("""
        INSERT INTO reviews (handoff_id, prompt_pth, assessment, focus_areas, risks,
                             regression_zones, lesson_candidates, rework_needed, notes)
        OUTPUT INSERTED.id, INSERTED.handoff_id, INSERTED.prompt_pth, INSERTED.assessment,
               INSERTED.focus_areas, INSERTED.risks, INSERTED.regression_zones,
               INSERTED.lesson_candidates, INSERTED.rework_needed, INSERTED.notes,
               INSERTED.created_at
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        review.handoff_id, review.prompt_pth, review.assessment,
        focus_json, risks_json, regr_json, lc_json,
        1 if review.rework_needed else 0, review.notes
    ), fetch="one")

    if not result:
        raise HTTPException(status_code=500, detail="Failed to create review")

    # Auto-create draft lessons from lesson_candidates
    if review.lesson_candidates:
        # Determine project from handoff
        ho = execute_query("SELECT project FROM mcp_handoffs WHERE id = ?",
                           (review.handoff_id,), fetch="one")
        project = ho['project'] if ho else 'MetaPM'

        for lc in review.lesson_candidates:
            ll_id = f"LL-{secrets.token_hex(3).upper()}"
            target = lc.target if lc.target in ('bootstrap', 'pk.md', 'cai_memory', 'standards') else 'bootstrap'
            try:
                execute_query("""
                    INSERT INTO lessons_learned
                    (id, project, category, lesson, source_sprint, target, status, proposed_by)
                    VALUES (?, ?, 'process', ?, ?, ?, 'draft', 'cai')
                """, (ll_id, project, lc.lesson, review.prompt_pth or '', target), fetch="none")
                logger.info(f"Auto-created lesson {ll_id} from review")
            except Exception as ll_err:
                logger.warning(f"Lesson creation failed (non-fatal): {ll_err}")

    return {
        "id": str(result["id"]),
        "assessment": result.get("assessment"),
        "created_at": str(result["created_at"]) if result.get("created_at") else None,
    }


@router.get("/{handoff_id}")
async def get_review_by_handoff(handoff_id: str):
    """Get review for a handoff (public read)."""
    row = execute_query("""
        SELECT * FROM reviews WHERE handoff_id = ?
        ORDER BY created_at DESC
    """, (handoff_id,), fetch="one")

    if not row:
        raise HTTPException(status_code=404, detail=f"No review found for handoff {handoff_id}")

    return _row_to_response(row)
