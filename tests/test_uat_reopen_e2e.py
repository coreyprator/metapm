"""MP48 M3 — end-to-end submit → reopen → render test for BUG-087.

Exercises the full flow on the deployed MetaPM service:
  1. Create a fresh UAT spec (POST /api/uat/spec, X-API-Key)
  2. Simulate a PL submission via /admin-backfill
  3. Reopen via /reopen
  4. Fetch /pl-results and assert prior values survived
  5. Fetch the rendered /uat/{spec_id} HTML (unauthenticated redirect) and
     confirm the endpoint is wired (login-required page returned, not 404)
  6. Verify the upsert guard: re-posting the same PTH after a submission
     returns 409 spec_has_prior_submission (this is the fix that prevents
     the blank-form regression)

Run standalone:
  MCP_API_KEY=$(gcloud secrets versions access latest --secret=metapm-api-key \
    --project=super-flashcards-475210) python tests/test_uat_reopen_e2e.py

Exits 0 when all assertions pass; non-zero on first failure.
"""

import json
import os
import sys
import time
import uuid

import httpx

BASE = os.environ.get("METAPM_BASE_URL", "https://metapm.rentyourcio.com")
API_KEY = os.environ.get("MCP_API_KEY") or os.environ.get("METAPM_API_KEY")
if not API_KEY:
    print("ERROR: MCP_API_KEY env var is required", file=sys.stderr)
    sys.exit(2)

H = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


def step(name):
    print(f"\n=== {name} ===")


def assert_eq(actual, expected, label):
    if actual != expected:
        print(f"FAIL [{label}]: expected {expected!r}, got {actual!r}")
        sys.exit(1)
    print(f"  ok {label} = {expected!r}")


def assert_true(cond, label):
    if not cond:
        print(f"FAIL [{label}]")
        sys.exit(1)
    print(f"  ok {label}")


def main():
    pth = f"MP48TEST-{uuid.uuid4().hex[:8].upper()}"
    print(f"E2E test PTH: {pth}")

    step("1. Create fresh UAT spec")
    body = {
        "project": "proj-mp",
        "version": "3.0.0",
        "sprint": "MP48-REOPEN-E2E",
        "pth": pth,
        "linked_requirements": ["BUG-087"],
        "test_cases": [
            {"id": "TC01", "title": "First test case", "steps": ["Step 1"],
             "expected": "First passes", "type": "pl_visual"},
            {"id": "TC02", "title": "Second test case", "steps": ["Step 1"],
             "expected": "Second fails", "type": "pl_visual"},
        ],
    }
    r = httpx.post(f"{BASE}/api/uat/spec", headers=H, json=body, timeout=60)
    assert_eq(r.status_code, 201, "POST /api/uat/spec")
    spec_id = r.json()["spec_id"]
    print(f"  spec_id = {spec_id}")

    step("2. Simulate PL submission via admin-backfill")
    backfill = {
        "test_cases": [
            {"id": "TC01", "status": "pass", "notes": "TC01 works as designed"},
            {"id": "TC02", "status": "fail", "notes": "TC02 broken on reload"},
        ],
        "general_notes": "[{\"timestamp\":\"2026-04-19T00:00:00Z\",\"text\":\"gn1\",\"classification\":\"bug\"}]",
        "backfill_reason": "MP48 M3 e2e test — simulating PL submission for reopen validation",
    }
    r = httpx.post(f"{BASE}/api/uat/{spec_id}/admin-backfill", headers=H, json=backfill, timeout=60)
    assert_eq(r.status_code, 200, "admin-backfill")
    assert_eq(r.json()["status"], "failed", "post-submit spec.status (1 fail)")

    step("3. Reopen the spec")
    r = httpx.post(f"{BASE}/api/uat/{spec_id}/reopen", headers=H, timeout=30)
    assert_eq(r.status_code, 200, "POST /api/uat/{spec_id}/reopen")
    assert_true(r.json().get("results_preserved") is True, "reopen.results_preserved")

    step("4. Verify /pl-results shows prior submission preserved")
    r = httpx.get(f"{BASE}/api/uat/{spec_id}/pl-results", headers=H, timeout=30)
    assert_eq(r.status_code, 200, "GET /api/uat/{spec_id}/pl-results")
    data = r.json()
    assert_true(data["has_prior_submission"], "has_prior_submission (BUG-087 fix)")
    by_id = {c["id"]: c for c in data["test_cases"]}
    assert_eq(by_id["TC01"]["status"], "pass", "TC01.status preserved")
    assert_eq(by_id["TC01"]["notes"], "TC01 works as designed", "TC01.notes preserved")
    assert_eq(by_id["TC02"]["status"], "fail", "TC02.status preserved")
    assert_eq(by_id["TC02"]["notes"], "TC02 broken on reload", "TC02.notes preserved")
    gn = data.get("general_notes") or []
    assert_true(len(gn) >= 1 and "gn1" in gn[0].get("text", ""), "general_notes preserved")

    step("5. Verify /uat/{spec_id} endpoint is wired (login-required expected for unauth)")
    r = httpx.get(f"{BASE}/uat/{spec_id}", timeout=30, follow_redirects=False)
    assert_true(r.status_code in (200, 302, 307), "GET /uat/{spec_id} returns 2xx/3xx")
    assert_true("/api/uat" in r.text or "Sign in" in r.text or "login" in r.text.lower()
                or len(r.text) > 100, "render pathway returns HTML (not 404)")

    step("6. Verify upsert guard: re-posting same PTH after submit returns 409")
    r = httpx.post(f"{BASE}/api/uat/spec", headers=H, json=body, timeout=30)
    assert_eq(r.status_code, 409, "re-post same PTH blocked")
    err = r.json().get("detail") or r.json()
    err_code = err.get("error") if isinstance(err, dict) else ""
    assert_eq(err_code, "spec_has_prior_submission", "error code")

    step("All assertions passed")
    print(f"\nE2E spec {spec_id} (PTH {pth}) left in DB for audit. Clean up manually if desired.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
