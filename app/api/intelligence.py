"""Intelligence Tab API — staged_corrections CRUD for Staging Queue."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.database import execute_query

router = APIRouter(prefix="/api/intelligence", tags=["Intelligence"])


class CorrectionUpdate(BaseModel):
    status: str  # 'approved' or 'dismissed'


@router.get("/staged-corrections")
async def list_staged_corrections():
    """List pending staged corrections."""
    rows = execute_query(
        "SELECT id, word, old_root, new_root, source_app, created_at, status "
        "FROM staged_corrections WHERE status = 'pending' ORDER BY created_at DESC"
    )
    return rows or []


@router.patch("/staged-corrections/{correction_id}")
async def update_staged_correction(correction_id: int, body: CorrectionUpdate):
    """Approve or dismiss a staged correction."""
    if body.status not in ("approved", "dismissed"):
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'dismissed'")
    execute_query(
        "UPDATE staged_corrections SET status = ? WHERE id = ?",
        (body.status, correction_id),
        fetch="none",
    )
    return {"id": correction_id, "status": body.status}
