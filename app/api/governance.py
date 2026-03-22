"""
MetaPM Governance API
Bootstrap checkpoint verification and sync.
MP-GOVERNANCE-SYNC-001 PTH-G3A1
MM09: Migrated from JSON file to Cloud SQL governance table.
"""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.database import execute_query

logger = logging.getLogger(__name__)

router = APIRouter()

DEFAULT_STATE = {
    "checkpoint": "BOOT-1.5.18-BA07",
    "bootstrap_version": "1.5.18",
    "updated_at": "2026-03-21",
    "source": "project-methodology/templates/CC_Bootstrap_v1.md"
}


def _read_state() -> dict:
    """Read governance state from Cloud SQL governance table."""
    try:
        row = execute_query(
            "SELECT TOP 1 checkpoint, bootstrap_version, updated_at, source FROM governance ORDER BY updated_at DESC",
            fetch="one"
        )
        if row:
            return {
                "checkpoint": row["checkpoint"],
                "bootstrap_version": row["bootstrap_version"],
                "updated_at": str(row["updated_at"])[:10],
                "source": row["source"] or DEFAULT_STATE["source"]
            }
    except Exception as e:
        logger.warning(f"Failed to read governance state from DB: {e}")
    return DEFAULT_STATE.copy()


def _write_state(state: dict) -> None:
    """Write governance state to Cloud SQL governance table (upsert via delete+insert)."""
    try:
        execute_query("DELETE FROM governance", fetch="none")
        execute_query(
            "INSERT INTO governance (checkpoint, bootstrap_version, updated_at, source) VALUES (?, ?, ?, ?)",
            params=(state["checkpoint"], state["bootstrap_version"], state["updated_at"], state.get("source", DEFAULT_STATE["source"])),
            fetch="none"
        )
    except Exception as e:
        logger.error(f"Failed to write governance state to DB: {e}")
        raise


class GovernanceSyncPayload(BaseModel):
    checkpoint: str
    bootstrap_version: str


class GovernanceCheckpointResponse(BaseModel):
    checkpoint: str
    bootstrap_version: str
    updated_at: str
    source: str


class GovernanceSyncResponse(BaseModel):
    status: str
    checkpoint: str
    bootstrap_version: str
    updated_at: str


@router.get(
    "/governance/bootstrap-checkpoint",
    response_model=GovernanceCheckpointResponse,
    summary="Get current canonical Bootstrap checkpoint"
)
async def get_bootstrap_checkpoint():
    """Returns the current canonical Bootstrap checkpoint code and version.
    Tries compliance_docs table first (source=compliance_docs_table), falls back to governance table.
    CC Phase 0 must call this and confirm its read checkpoint matches."""
    # Try compliance_docs table first
    try:
        row = execute_query(
            "SELECT version, [checkpoint], updated_at FROM compliance_docs WHERE id = 'bootstrap'",
            fetch="one"
        )
        if row:
            return GovernanceCheckpointResponse(
                checkpoint=row["checkpoint"],
                bootstrap_version=row["version"],
                updated_at=str(row["updated_at"])[:10],
                source="compliance_docs_table"
            )
    except Exception as e:
        logger.warning(f"compliance_docs lookup failed, falling back to governance table: {e}")

    state = _read_state()
    return GovernanceCheckpointResponse(
        checkpoint=state["checkpoint"],
        bootstrap_version=state["bootstrap_version"],
        updated_at=state["updated_at"],
        source=state.get("source", DEFAULT_STATE["source"])
    )


@router.get(
    "/governance/bootstrap-version",
    summary="Get Bootstrap version string (MP-BUG-001 fix)"
)
async def get_bootstrap_version():
    """Returns the current Bootstrap version string.
    Alias for bootstrap-checkpoint for simpler Phase 0 verification."""
    state = _read_state()
    return {
        "version": state["bootstrap_version"],
        "checkpoint": state["checkpoint"],
        "updated_at": state["updated_at"]
    }


@router.post(
    "/governance/sync",
    response_model=GovernanceSyncResponse,
    summary="Update canonical Bootstrap checkpoint"
)
async def sync_governance(payload: GovernanceSyncPayload):
    """Update the canonical Bootstrap checkpoint after a Bootstrap commit.
    PL or CC calls this after committing a new Bootstrap version."""
    state = _read_state()
    state["checkpoint"] = payload.checkpoint
    state["bootstrap_version"] = payload.bootstrap_version
    state["updated_at"] = str(date.today())
    _write_state(state)
    logger.info(f"Governance checkpoint synced to {payload.checkpoint}")
    return GovernanceSyncResponse(
        status="synced",
        checkpoint=state["checkpoint"],
        bootstrap_version=state["bootstrap_version"],
        updated_at=state["updated_at"]
    )
