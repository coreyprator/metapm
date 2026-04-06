"""
Challenge Token endpoints — Tier 2 anti-fabrication.
Sprint: MP-CHALLENGE-TOKEN-001 (PTH: MPCH1)

GET /api/challenge/{pth}        — generate a one-time challenge token
GET /api/challenge/{pth}/verify — verify and consume a token
"""

import secrets
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import APIKeyHeader

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


@router.get("/{pth}")
async def get_challenge(pth: str, _: bool = Depends(verify_api_key)):
    """Generate a one-time challenge token for a sprint PTH."""
    token = secrets.token_hex(16)  # 32-char hex
    execute_query(
        "INSERT INTO challenge_tokens (pth, token) VALUES (?, ?)",
        (pth, token),
        fetch="none",
    )
    logger.info(f"Challenge token created for PTH {pth}")
    return {"pth": pth, "token": token}


@router.get("/{pth}/verify")
async def verify_challenge(
    pth: str,
    token: str = Query(...),
    _: bool = Depends(verify_api_key),
):
    """Verify and consume a challenge token. Single-use."""
    row = execute_query(
        "SELECT id, used FROM challenge_tokens WHERE pth = ? AND token = ?",
        (pth, token),
        fetch="one",
    )
    if not row:
        return {"valid": False, "reason": "token not found"}
    if row["used"]:
        return {"valid": False, "reason": "token already used"}
    execute_query(
        "UPDATE challenge_tokens SET used = 1, used_at = GETDATE() WHERE id = ?",
        (row["id"],),
        fetch="none",
    )
    logger.info(f"Challenge token verified for PTH {pth}")

    # MP18 REQ-046 Gate 2: check for session-start signal
    session_start_missing = True
    try:
        session_row = execute_query(
            "SELECT id FROM cc_sessions WHERE pth = ? AND signal = 'started'",
            (pth,), fetch="one"
        )
        if session_row:
            session_start_missing = False
    except Exception:
        pass  # table may not exist — default to warning

    return {"valid": True, "session_start_missing": session_start_missing}
