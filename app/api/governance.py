"""
MetaPM Governance API
Bootstrap checkpoint verification and sync.
MP-GOVERNANCE-SYNC-001 PTH-G3A1
"""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# Governance state file — simple JSON storage (no DB table needed)
GOVERNANCE_STATE_FILE = Path(__file__).parent.parent.parent / "governance_state.json"

DEFAULT_STATE = {
    "checkpoint": "BOOT-1.5.7-65D6",
    "bootstrap_version": "1.5.7",
    "updated_at": "2026-03-12",
    "source": "project-methodology/templates/CC_Bootstrap_v1.md"
}


def _read_state() -> dict:
    """Read governance state from JSON file, or return defaults."""
    if GOVERNANCE_STATE_FILE.exists():
        try:
            return json.loads(GOVERNANCE_STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read governance state: {e}")
    return DEFAULT_STATE.copy()


def _write_state(state: dict) -> None:
    """Write governance state to JSON file."""
    GOVERNANCE_STATE_FILE.write_text(
        json.dumps(state, indent=2), encoding="utf-8"
    )


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
    CC Phase 0 must call this and confirm its read checkpoint matches."""
    state = _read_state()
    return GovernanceCheckpointResponse(
        checkpoint=state["checkpoint"],
        bootstrap_version=state["bootstrap_version"],
        updated_at=state["updated_at"],
        source=state.get("source", DEFAULT_STATE["source"])
    )


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
