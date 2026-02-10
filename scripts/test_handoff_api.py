#!/usr/bin/env python3
"""
Handoff API Test Script (HO-G7H8)
Tests the handoff lifecycle API endpoints.
"""

import requests
import sys
import json
from datetime import datetime

# Configuration
BASE_URL = "https://metapm.rentyourcio.com"
# Note: handoff_requests.id is VARCHAR(10), so keep test ID short
TEST_ID = f"HO-T{datetime.now().strftime('%H%M')}"


def test_endpoint(name: str, method: str, url: str, expected_status: int, json_data=None):
    """Test an API endpoint and return pass/fail."""
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=json_data, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=json_data, timeout=10)
        else:
            return False, f"Unknown method: {method}"

        passed = response.status_code == expected_status
        status_text = "PASS" if passed else "FAIL"
        print(f"  [{status_text}] {name}")
        print(f"       {method} {url}")
        print(f"       Status: {response.status_code} (expected {expected_status})")

        if not passed:
            try:
                print(f"       Response: {response.text[:200]}")
            except:
                pass

        return passed, response

    except Exception as e:
        print(f"  [FAIL] {name}")
        print(f"       Error: {e}")
        return False, None


def main():
    print("=" * 60)
    print("MetaPM Handoff API Test Suite")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Test ID: {TEST_ID}")
    print()

    all_passed = True
    results = []

    # Test 1: Health Check
    print("1. Health Check")
    passed, response = test_endpoint(
        "GET /health",
        "GET",
        f"{BASE_URL}/health",
        200
    )
    results.append(("Health Check", passed))
    if not passed:
        all_passed = False
    print()

    # Test 2: Create Handoff
    print("2. Create Handoff (POST /api/handoffs)")
    test_handoff = {
        "id": TEST_ID,
        "project": "MetaPM",
        "roadmap_id": "MP-TEST",
        "request_type": "Bug",
        "title": "API Test Handoff",
        "description": "Created by test_handoff_api.py"
    }
    passed, response = test_endpoint(
        f"POST /api/handoffs",
        "POST",
        f"{BASE_URL}/api/handoffs",
        200,
        test_handoff
    )
    results.append(("Create Handoff", passed))
    if not passed:
        all_passed = False
    print()

    # Test 3: Read Handoff
    print("3. Read Handoff (GET /api/handoffs/{id})")
    passed, response = test_endpoint(
        f"GET /api/handoffs/{TEST_ID}",
        "GET",
        f"{BASE_URL}/api/handoffs/{TEST_ID}",
        200
    )
    results.append(("Read Handoff", passed))
    if not passed:
        all_passed = False
    else:
        try:
            data = response.json()
            print(f"       Handoff: {data.get('handoff', {}).get('title', 'N/A')}")
        except:
            pass
    print()

    # Test 4: Update Status
    print("4. Update Status (PUT /api/handoffs/{id}/status)")
    passed, response = test_endpoint(
        f"PUT /api/handoffs/{TEST_ID}/status",
        "PUT",
        f"{BASE_URL}/api/handoffs/{TEST_ID}/status",
        200,
        {"status": "PENDING"}
    )
    results.append(("Update Status", passed))
    if not passed:
        all_passed = False
    print()

    # Test 5: Verify Update
    print("5. Verify Update (GET /api/handoffs/{id})")
    passed, response = test_endpoint(
        f"GET /api/handoffs/{TEST_ID}",
        "GET",
        f"{BASE_URL}/api/handoffs/{TEST_ID}",
        200
    )
    if passed:
        try:
            data = response.json()
            status = data.get('handoff', {}).get('status')
            if status == 'PENDING':
                print(f"       Status correctly updated to: {status}")
            else:
                print(f"       WARNING: Status is {status}, expected PENDING")
                passed = False
        except:
            pass
    results.append(("Verify Update", passed))
    if not passed:
        all_passed = False
    print()

    # Test 6: Record Completion
    print("6. Record Completion (POST /api/handoffs/{id}/complete)")
    passed, response = test_endpoint(
        f"POST /api/handoffs/{TEST_ID}/complete",
        "POST",
        f"{BASE_URL}/api/handoffs/{TEST_ID}/complete",
        200,
        {
            "status": "COMPLETE",
            "commit_hash": "test123",
            "notes": "Test completion"
        }
    )
    results.append(("Record Completion", passed))
    if not passed:
        all_passed = False
    print()

    # Test 7: Get Existing Handoff (HO-A1B2)
    print("7. Get HO-A1B2 (seeded data)")
    passed, response = test_endpoint(
        "GET /api/handoffs/HO-A1B2",
        "GET",
        f"{BASE_URL}/api/handoffs/HO-A1B2",
        200
    )
    results.append(("Get HO-A1B2", passed))
    if passed:
        try:
            data = response.json()
            print(f"       Title: {data.get('handoff', {}).get('title', 'N/A')}")
            print(f"       Status: {data.get('handoff', {}).get('status', 'N/A')}")
            completions = data.get('completions', [])
            print(f"       Completions: {len(completions)}")
        except:
            pass
    if not passed:
        all_passed = False
    print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed_count = sum(1 for _, p in results if p)
    total = len(results)
    print(f"Passed: {passed_count}/{total}")
    print()
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
    print()

    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)

    # Cleanup note
    print()
    print(f"Note: Test handoff {TEST_ID} was created in the database.")
    print("You may want to clean it up manually if needed.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
