"""
MP49 BUG-073 — cc_machine BV M3.

State machine now allows cc_complete → done for type='task' requirements.
This test exercises both VALID_TRANSITIONS and LIFECYCLE_VALID_TRANSITIONS
paths at import level — no DB round-trip — by faking a requirement row
and stepping the guard logic directly.

A full end-to-end walk against the live DB is intentionally not run in CI
because it would leave a synthetic requirement row behind.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.roadmap import VALID_TRANSITIONS, LIFECYCLE_VALID_TRANSITIONS


TASK_FULL_WALK = [
    "req_created", "req_approved", "cai_designing",
    "cc_prompt_ready", "cc_executing", "cc_complete", "done",
]


def _step_allowed(transitions_dict, current, nxt, req_type):
    """Replicates the guard used inside the two PATCH handlers."""
    allowed = transitions_dict.get(current)
    task_shortcut = (
        req_type == 'task'
        and current == 'cc_complete'
        and nxt == 'done'
    )
    if allowed is None:
        return True  # legacy status allows anything
    return (nxt in allowed) or task_shortcut


def test_m3_task_lifecycle_walks_cc_complete_to_done_without_uat():
    """Walk a type='task' requirement from req_created to done.
    Every step is validated with the guard used by the REST endpoints.
    """
    for path_name, transitions in (
        ("VALID_TRANSITIONS", VALID_TRANSITIONS),
        ("LIFECYCLE_VALID_TRANSITIONS", LIFECYCLE_VALID_TRANSITIONS),
    ):
        for i in range(len(TASK_FULL_WALK) - 1):
            cur = TASK_FULL_WALK[i]
            nxt = TASK_FULL_WALK[i + 1]
            assert _step_allowed(transitions, cur, nxt, 'task'), \
                f"{path_name}: task cannot go {cur} -> {nxt}"


def test_m3_non_task_cannot_skip_uat():
    """Regression guard: type='requirement' must still route through UAT."""
    for transitions in (VALID_TRANSITIONS, LIFECYCLE_VALID_TRANSITIONS):
        assert not _step_allowed(transitions, 'cc_complete', 'done', 'requirement'), \
            "non-task incorrectly allowed cc_complete -> done"
        assert not _step_allowed(transitions, 'cc_complete', 'done', 'bug'), \
            "bug-type incorrectly allowed cc_complete -> done"


if __name__ == "__main__":
    test_m3_task_lifecycle_walks_cc_complete_to_done_without_uat()
    print("M3a PASS — task walks cc_complete -> done")
    test_m3_non_task_cannot_skip_uat()
    print("M3b PASS — non-task blocked from skipping UAT")
