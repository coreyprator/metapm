"""
MetaPM MCP API tests
"""

from datetime import datetime

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
