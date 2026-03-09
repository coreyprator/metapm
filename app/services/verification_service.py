"""
Handoff Verification Service — MP-VERIFY-001
Independently verifies endpoints CC claims to have built.
"""
import json
import re
import logging
from datetime import datetime

import httpx

from app.core.database import execute_query

logger = logging.getLogger(__name__)


def extract_url_from_curl(cmd: str) -> str:
    """Extract the first URL from a curl command string."""
    m = re.search(r'https?://[^\s|>\'\"]+', cmd)
    return m.group(0) if m else ""


async def verify_handoff(handoff_id: str) -> dict:
    """
    Verify endpoints claimed in a handoff's evidence_json.
    Returns verification results with per-endpoint match status.
    """
    handoff = execute_query(
        "SELECT id, evidence_json, verification_status FROM mcp_handoffs WHERE id = ?",
        (handoff_id,), fetch="one"
    )
    if not handoff:
        return {"error": f"Handoff {handoff_id} not found"}

    evidence_json = handoff.get("evidence_json")
    if not evidence_json:
        _save_verification(handoff_id, "skipped", [], "no evidence provided")
        return {"handoff_id": handoff_id, "verification_status": "skipped", "reason": "no evidence provided", "results": []}

    try:
        requirements = json.loads(evidence_json)
    except (json.JSONDecodeError, TypeError):
        _save_verification(handoff_id, "skipped", [], "invalid evidence JSON")
        return {"handoff_id": handoff_id, "verification_status": "skipped", "reason": "invalid evidence JSON", "results": []}

    results = []

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for req in requirements:
            if req.get("status") != "complete":
                continue
            evidence = req.get("evidence", {})
            if not evidence:
                continue
            endpoint = extract_url_from_curl(evidence.get("curl_command", ""))
            if not endpoint:
                continue
            try:
                resp = await client.get(endpoint)
                actual = resp.status_code
                claimed = evidence.get("http_status", 200)
                results.append({
                    "requirement_code": req.get("code"),
                    "endpoint": endpoint,
                    "cc_claimed_status": claimed,
                    "actual_status": actual,
                    "match": actual == claimed
                })
            except Exception as e:
                results.append({
                    "requirement_code": req.get("code"),
                    "endpoint": endpoint,
                    "cc_claimed_status": evidence.get("http_status"),
                    "actual_status": None,
                    "match": False,
                    "error": str(e)
                })

    if not results:
        status = "skipped"
    elif all(r["match"] for r in results):
        status = "verified"
    elif any(r["match"] for r in results):
        status = "partial"
    else:
        status = "mismatch"

    _save_verification(handoff_id, status, results)

    return {"handoff_id": handoff_id, "verification_status": status, "results": results}


def _save_verification(handoff_id: str, status: str, results: list, reason: str = None):
    """Save verification results to DB and update handoff."""
    results_data = results if not reason else [{"reason": reason}]
    try:
        execute_query("""
            INSERT INTO handoff_verifications (handoff_id, verification_status, results_json, verified_at)
            VALUES (?, ?, ?, GETDATE())
        """, (handoff_id, status, json.dumps(results_data)), fetch="none")

        execute_query("""
            UPDATE mcp_handoffs SET verification_status = ? WHERE id = ?
        """, (status, handoff_id), fetch="none")
    except Exception as e:
        logger.error(f"Failed to save verification for {handoff_id}: {e}")
