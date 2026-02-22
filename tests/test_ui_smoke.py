"""
MetaPM UI Smoke Tests — HO-MP11
Production smoke tests against live MetaPM deployment.
Uses httpx to verify critical endpoints; does NOT use Playwright or local DB.

Run: pytest tests/test_ui_smoke.py -v
"""

import pytest
import httpx

BASE_URL = "https://metapm.rentyourcio.com"
TIMEOUT = 30.0


class TestHealthAndVersion:
    """Verify the service is up and version is current."""

    def test_health_returns_200(self):
        """GET /health should return 200 with status=healthy."""
        resp = httpx.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "healthy"

    def test_health_returns_version(self):
        """GET /health should include a version field."""
        resp = httpx.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        data = resp.json()
        assert "version" in data
        assert data["version"], "version must not be empty"


class TestCoreAPIEndpoints:
    """Verify essential API endpoints respond correctly."""

    def test_requirements_list(self):
        """GET /api/requirements should return a requirements list."""
        resp = httpx.get(f"{BASE_URL}/api/requirements?limit=10", timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        reqs = data.get("requirements", data) if isinstance(data, dict) else data
        assert isinstance(reqs, list), "Expected a list of requirements"
        assert len(reqs) > 0, "No requirements returned"

    def test_handoffs_list(self):
        """GET /api/handoffs should return 200 without SQL errors."""
        resp = httpx.get(f"{BASE_URL}/api/handoffs?limit=5", timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert "handoffs" in data, f"Expected 'handoffs' key in response, got: {data}"

    def test_projects_list(self):
        """GET /api/projects should return a list of projects."""
        resp = httpx.get(f"{BASE_URL}/api/projects", timeout=TIMEOUT)
        assert resp.status_code == 200

    def test_roadmap_requirements(self):
        """GET /api/roadmap/requirements should return roadmap data."""
        resp = httpx.get(f"{BASE_URL}/api/roadmap/requirements?project_id=proj-mp&limit=5", timeout=TIMEOUT)
        assert resp.status_code == 200


class TestStaticPages:
    """Verify key static pages load."""

    def test_root_redirects_to_dashboard(self):
        """GET / should redirect to /static/dashboard.html."""
        resp = httpx.get(f"{BASE_URL}/", timeout=TIMEOUT, follow_redirects=False)
        assert resp.status_code in (301, 302, 307, 308), f"Expected redirect, got {resp.status_code}"
        location = resp.headers.get("location", "")
        assert "dashboard" in location.lower(), f"Expected dashboard redirect, got location: {location}"

    def test_dashboard_loads(self):
        """GET /static/dashboard.html should return HTML with key markers."""
        resp = httpx.get(f"{BASE_URL}/static/dashboard.html", timeout=TIMEOUT)
        assert resp.status_code == 200
        assert "MetaPM" in resp.text or "metapm" in resp.text.lower()

    def test_architecture_redirects(self):
        """GET /architecture should redirect to GCS stable URL."""
        resp = httpx.get(f"{BASE_URL}/architecture", timeout=TIMEOUT, follow_redirects=False)
        assert resp.status_code in (301, 302, 307)
        location = resp.headers.get("location", "")
        assert "storage.googleapis.com" in location, f"Expected GCS redirect, got: {location}"
