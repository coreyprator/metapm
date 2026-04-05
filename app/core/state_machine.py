"""
MetaPM State Machine — MP12B
Defense-in-depth: atomic prompt/requirement transitions with history tracking.
Layer 1: Application-level writes (this module).
Layer 2: SQL Server DB triggers (migration 62d).
Layer 3: Failure history (blocked transitions recorded with success=0).
"""

import logging
from app.core.database import execute_query, get_db

logger = logging.getLogger(__name__)


# ── Prompt transition rules ──

PROMPT_VALID_TRANSITIONS = {
    'draft':     {'approved', 'rejected'},
    'approved':  {'executing', 'rejected'},
    'executing': {'completed', 'stopped', 'blocked'},
    'stopped':   {'approved'},
    'blocked':   {'approved'},
    'completed': set(),
    'rejected':  set(),
}


class InvalidTransitionError(Exception):
    pass


def validate_prompt_transition(from_status: str, to_status: str, pth: str):
    """Raise InvalidTransitionError if transition is not allowed."""
    valid = PROMPT_VALID_TRANSITIONS.get(from_status, set())
    if to_status not in valid:
        raise InvalidTransitionError(
            f"Invalid transition for PTH '{pth}': '{from_status}' -> '{to_status}'. "
            f"Valid next states: {sorted(valid) or ['none - terminal state']}"
        )


def transition_prompt_status(pth: str, new_status: str, changed_by: str, trigger: str):
    """Atomically update prompt status and write history. Returns (prompt_id, from_status)."""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT TOP 1 id, status, pth FROM cc_prompts WHERE pth = ? ORDER BY id DESC",
                (pth,)
            )
            cols = [c[0] for c in cursor.description]
            row_raw = cursor.fetchone()
            if not row_raw:
                raise ValueError(f"Prompt with PTH '{pth}' not found")
            row = dict(zip(cols, row_raw))

            prompt_id = row['id']
            from_status = row['status']

            validate_prompt_transition(from_status, new_status, pth)

            cursor.execute(
                "UPDATE cc_prompts SET status = ?, updated_at = GETUTCDATE() WHERE id = ?",
                (new_status, prompt_id)
            )

            cursor.execute(
                "INSERT INTO prompt_history (prompt_id, pth, from_status, to_status, changed_by, [trigger], success) "
                "VALUES (?, ?, ?, ?, ?, ?, 1)",
                (prompt_id, pth, from_status, new_status, changed_by, trigger)
            )

            return prompt_id, from_status

        except Exception:
            raise


def write_prompt_history(prompt_id: int, pth: str, from_status: str, to_status: str,
                         changed_by: str, trigger: str, success: bool = True,
                         blocked_reason: str = None):
    """Write a prompt history row (success or failure)."""
    execute_query(
        "INSERT INTO prompt_history (prompt_id, pth, from_status, to_status, changed_by, [trigger], success, blocked_reason) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (prompt_id, pth, from_status, to_status, changed_by, trigger,
         1 if success else 0, blocked_reason),
        fetch="none"
    )


def write_prompt_failure(prompt_id: int, pth: str, from_status: str,
                         attempted_to: str, changed_by: str, trigger: str, reason: str):
    """Write a failure history row for a blocked/invalid transition attempt."""
    write_prompt_history(
        prompt_id, pth, from_status, attempted_to,
        changed_by, trigger, success=False, blocked_reason=reason
    )


def write_requirement_failure(req_id: str, from_status: str, attempted_to: str,
                              changed_by: str, trigger: str, reason: str):
    """Write a failure history row for a blocked requirement transition."""
    execute_query(
        "INSERT INTO requirement_history (requirement_id, field_name, old_value, new_value, changed_by, notes, success, blocked_reason) "
        "VALUES (?, 'status', ?, ?, ?, ?, 0, ?)",
        (req_id, from_status, attempted_to, changed_by, f"BLOCKED: {trigger}", reason),
        fetch="none"
    )


def write_failure_event(event_type: str, pth: str, trigger: str, details: str):
    """Write a failure_events row for orphan PTHs, data quality issues, etc."""
    execute_query(
        "INSERT INTO failure_events (event_type, pth, [trigger], details) VALUES (?, ?, ?, ?)",
        (event_type, pth, trigger, details[:1000] if details else None),
        fetch="none"
    )
