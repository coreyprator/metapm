"""
MetaPM MCP API tests
"""

from datetime import datetime
import pytest

from app.api import mcp as mcp_api


def test_mcp_uat_results_alias(client, monkeypatch):
    """Ensure /mcp/uat/results resolves to list results handler."""
    def fake_execute_query(query, params=None, fetch=None):
        if "COUNT(*) as total" in query:
            return {"total": 1}
        if "SELECT u.id" in query:
            return [
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "handoff_id": "22222222-2222-2222-2222-222222222222",
                    "status": "failed",
                    "total_tests": 6,
                    "passed": 3,
                    "failed": 3,
                    "notes_count": 0,
                    "tested_by": "cc",
                    "tested_at": datetime(2026, 2, 15, 0, 0, 0),
                    "results_text": "AF results",
                    "project": "ArtForge",
                    "version": "2.2.1",
                }
            ]
        return None

    monkeypatch.setattr(mcp_api, "execute_query", fake_execute_query)

    response = client.get("/mcp/uat/results")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["results"][0]["project"] == "ArtForge"


def test_mcp_handoffs_list_requires_valid_key(client, monkeypatch):
    """Ensure /mcp/handoffs returns data with a valid API key."""
    def fake_execute_query(query, params=None, fetch=None):
        if "COUNT(*) as total" in query and "mcp_handoffs" in query:
            return {"total": 1}
        if "FROM mcp_handoffs" in query and "SELECT id" in query:
            return [
                {
                    "id": "33333333-3333-3333-3333-333333333333",
                    "project": "project-methodology",
                    "task": "HO-U9V1",
                    "direction": "cc_to_ai",
                    "status": "pending",
                    "metadata": None,
                    "response_to": None,
                    "created_at": datetime(2026, 2, 15, 0, 0, 0),
                    "updated_at": datetime(2026, 2, 15, 0, 0, 0),
                }
            ]
        return None

    monkeypatch.setattr(mcp_api, "execute_query", fake_execute_query)
    monkeypatch.setattr(mcp_api.settings, "MCP_API_KEY", "test-key")

    response = client.get("/mcp/handoffs", headers={"X-API-Key": "test-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["handoffs"][0]["project"] == "project-methodology"


def test_uat_direct_submit_with_results_array(client, monkeypatch):
    """Test UAT submit with results array (no results_text) succeeds."""
    def fake_execute_query(query, params=None, fetch=None):
        if "SELECT id, status FROM mcp_handoffs" in query:
            return None  # No existing handoff
        if "INSERT INTO mcp_handoffs" in query:
            return {"id": "44444444-4444-4444-4444-444444444444"}
        if "INSERT INTO uat_results" in query:
            return {"id": "55555555-5555-5555-5555-555555555555", "tested_at": datetime.utcnow()}
        if "UPDATE mcp_handoffs" in query:
            return None
        return None

    monkeypatch.setattr(mcp_api, "execute_query", fake_execute_query)

    payload = {
        "project": "MetaPM",
        "version": "v2.1.2 UAT Submit Fix HO-U9V1",  # 31 chars - tests max_length
        "status": "passed",
        "total_tests": 3,
        "passed": 3,
        "failed": 0,
        "results": [
            {"id": "TEST-01", "title": "Test with results array", "status": "passed", "note": ""}
        ]
    }

    response = client.post("/mcp/uat/submit", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "passed"
    assert "handoff_id" in data


def test_uat_direct_submit_with_long_version(client, monkeypatch):
    """Test UAT submit with version string up to 200 chars succeeds."""
    def fake_execute_query(query, params=None, fetch=None):
        if "SELECT id, status FROM mcp_handoffs" in query:
            return None
        if "INSERT INTO mcp_handoffs" in query:
            return {"id": "66666666-6666-6666-6666-666666666666"}
        if "INSERT INTO uat_results" in query:
            return {"id": "77777777-7777-7777-7777-777777777777", "tested_at": datetime.utcnow()}
        if "UPDATE mcp_handoffs" in query:
            return None
        return None

    monkeypatch.setattr(mcp_api, "execute_query", fake_execute_query)

    long_version = "v2.1.2 " + ("A" * 50)  # 57 chars
    payload = {
        "project": "MetaPM",
        "version": long_version,
        "status": "failed",
        "total_tests": 5,
        "passed": 2,
        "failed": 3,
        "results_text": "TEST-01: Failed validation"
    }

    response = client.post("/mcp/uat/submit", json=payload)
    assert response.status_code == 201


def test_uat_direct_submit_version_too_long(client):
    """Test UAT submit with version > 200 chars fails validation."""
    long_version = "v" + ("A" * 250)  # 251 chars - exceeds max
    payload = {
        "project": "MetaPM",
        "version": long_version,
        "status": "failed",
        "total_tests": 1,
        "passed": 0,
        "failed": 1,
        "results_text": "TEST-01: Failed"
    }

    response = client.post("/mcp/uat/submit", json=payload)
    assert response.status_code == 422
    assert "version" in response.text.lower() or "string_too_long" in response.text.lower()


def test_uat_direct_submit_missing_results(client):
    """Test UAT submit with no results_text AND no results array fails."""
    payload = {
        "project": "MetaPM",
        "version": "v2.1.2",
        "status": "failed",
        "total_tests": 1,
        "passed": 0,
        "failed": 1
        # Neither results_text nor results provided
    }

    response = client.post("/mcp/uat/submit", json=payload)
    assert response.status_code == 422
    assert "results" in response.text.lower()


def test_uat_direct_submit_counts_exceed_total(client):
    """Test UAT submit where passed+failed+blocked > total_tests fails."""
    payload = {
        "project": "MetaPM",
        "version": "v2.1.2",
        "status": "failed",
        "total_tests": 5,
        "passed": 3,
        "failed": 3,  # 3 + 3 = 6 > 5
        "results_text": "Invalid counts"
    }

    response = client.post("/mcp/uat/submit", json=payload)
    assert response.status_code == 422
    assert "exceeds" in response.text.lower() or "total_tests" in response.text.lower()


def test_uat_direct_submit_with_both_formats(client, monkeypatch):
    """Test UAT submit with both results_text AND results array (should prefer results_text)."""
    def fake_execute_query(query, params=None, fetch=None):
        if "SELECT id, status FROM mcp_handoffs" in query:
            return None
        if "INSERT INTO mcp_handoffs" in query:
            return {"id": "88888888-8888-8888-8888-888888888888"}
        if "INSERT INTO uat_results" in query:
            return {"id": "99999999-9999-9999-9999-999999999999", "tested_at": datetime.utcnow()}
        if "UPDATE mcp_handoffs" in query:
            return None
        return None

    monkeypatch.setattr(mcp_api, "execute_query", fake_execute_query)

    payload = {
        "project": "MetaPM",
        "version": "v2.1.2",
        "status": "passed",
        "total_tests": 2,
        "passed": 2,
        "failed": 0,
        "results_text": "Manual results text",
        "results": [
            {"id": "TEST-01", "title": "Should be ignored", "status": "passed"}
        ]
    }

    response = client.post("/mcp/uat/submit", json=payload)
    assert response.status_code == 201
