# MetaPM Test Plan - Playwright & API Tests

**Version**: 2.0  
**Project**: MetaPM - Meta Project Manager  
**Methodology**: project-methodology v3.12.1

---

## Overview

This test plan covers:
1. **API Smoke Tests** (pytest + requests) - Verify endpoints respond
2. **API Integration Tests** - Verify data flows correctly
3. **UI Smoke Tests** (Playwright) - Verify web interface works
4. **Voice Capture Tests** - Verify audio → transcription → task flow

---

## Prerequisites

### Install Test Dependencies

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install test packages
pip install pytest pytest-asyncio playwright pytest-playwright httpx --break-system-packages

# Install Playwright browsers
playwright install chromium
```

### Environment Setup

Ensure these are configured:
- Cloud Run URL deployed and accessible
- Database connection working
- GCS bucket created
- API keys in Secret Manager

---

## Test Files to Create

### 1. tests/test_api_smoke.py

```python
"""
MetaPM API Smoke Tests
Run BEFORE any other tests to verify basic connectivity.

Usage: pytest tests/test_api_smoke.py -v
"""

import pytest
import httpx
import os

# Get base URL from environment or use default
BASE_URL = os.getenv("METAPM_URL", "https://metapm-XXXXX-uc.a.run.app")


class TestHealthEndpoints:
    """Verify basic service health."""
    
    def test_root_returns_service_info(self):
        """Root endpoint returns service metadata."""
        response = httpx.get(f"{BASE_URL}/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "MetaPM"
        assert data["status"] == "healthy"
        assert "version" in data or "docs" in data
    
    def test_health_endpoint(self):
        """Health check endpoint for Cloud Run."""
        response = httpx.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_docs_accessible(self):
        """OpenAPI docs are accessible."""
        response = httpx.get(f"{BASE_URL}/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()


class TestTaskEndpoints:
    """Verify task API endpoints respond."""
    
    def test_list_tasks_returns_200(self):
        """GET /api/tasks returns 200."""
        response = httpx.get(f"{BASE_URL}/api/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "total" in data
    
    def test_list_tasks_with_filters(self):
        """GET /api/tasks accepts filter parameters."""
        response = httpx.get(f"{BASE_URL}/api/tasks", params={
            "status": "NEW",
            "priority": 1,
            "pageSize": 10
        })
        assert response.status_code == 200
    
    def test_invalid_task_returns_404(self):
        """GET /api/tasks/99999 returns 404."""
        response = httpx.get(f"{BASE_URL}/api/tasks/99999")
        assert response.status_code == 404


class TestProjectEndpoints:
    """Verify project API endpoints respond."""
    
    def test_list_projects_returns_200(self):
        """GET /api/projects returns 200."""
        response = httpx.get(f"{BASE_URL}/api/projects")
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
    
    def test_get_known_project(self):
        """GET /api/projects/META returns the meta project."""
        response = httpx.get(f"{BASE_URL}/api/projects/META")
        # May be 200 if seeded, 404 if not
        assert response.status_code in [200, 404]
    
    def test_invalid_project_returns_404(self):
        """GET /api/projects/INVALID returns 404."""
        response = httpx.get(f"{BASE_URL}/api/projects/NONEXISTENT")
        assert response.status_code == 404


class TestCategoryEndpoints:
    """Verify category API endpoints respond."""
    
    def test_list_categories_returns_200(self):
        """GET /api/categories returns 200."""
        response = httpx.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 200
        data = response.json()
        assert "task_types" in data or "domains" in data


class TestMethodologyEndpoints:
    """Verify methodology API endpoints respond."""
    
    def test_list_rules_returns_200(self):
        """GET /api/methodology/rules returns 200."""
        response = httpx.get(f"{BASE_URL}/api/methodology/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
    
    def test_violation_summary(self):
        """GET /api/methodology/violations/summary returns 200."""
        response = httpx.get(f"{BASE_URL}/api/methodology/violations/summary")
        assert response.status_code == 200


class TestHistoryEndpoints:
    """Verify transaction history endpoints respond."""
    
    def test_list_conversations_returns_200(self):
        """GET /api/history/conversations returns 200."""
        response = httpx.get(f"{BASE_URL}/api/history/conversations")
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
    
    def test_search_endpoint(self):
        """POST /api/history/search accepts query."""
        response = httpx.post(f"{BASE_URL}/api/history/search", json={
            "query": "test",
            "maxResults": 10
        })
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
    
    def test_analytics_costs(self):
        """GET /api/history/analytics/costs returns 200."""
        response = httpx.get(f"{BASE_URL}/api/history/analytics/costs")
        assert response.status_code == 200
    
    def test_analytics_usage(self):
        """GET /api/history/analytics/usage returns 200."""
        response = httpx.get(f"{BASE_URL}/api/history/analytics/usage")
        assert response.status_code == 200


class TestNoServerErrors:
    """Verify no endpoints return 500 errors."""
    
    ENDPOINTS = [
        "/",
        "/health",
        "/api/tasks",
        "/api/projects",
        "/api/categories",
        "/api/methodology/rules",
        "/api/history/conversations",
        "/api/history/analytics/costs",
    ]
    
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_no_500_error(self, endpoint):
        """Endpoint does not return 500."""
        response = httpx.get(f"{BASE_URL}{endpoint}")
        assert response.status_code != 500, f"500 error on {endpoint}: {response.text}"
```

---

### 2. tests/test_api_integration.py

```python
"""
MetaPM API Integration Tests
Test actual data flows and CRUD operations.

Usage: pytest tests/test_api_integration.py -v
"""

import pytest
import httpx
import os
import uuid

BASE_URL = os.getenv("METAPM_URL", "https://metapm-XXXXX-uc.a.run.app")


class TestTaskCRUD:
    """Test task create, read, update, delete flow."""
    
    @pytest.fixture
    def created_task(self):
        """Create a task for testing, cleanup after."""
        task_data = {
            "title": f"Test Task {uuid.uuid4().hex[:8]}",
            "description": "Created by automated test",
            "priority": 3,
            "projects": ["META"],
            "categories": ["TEST"]
        }
        
        response = httpx.post(f"{BASE_URL}/api/tasks", json=task_data)
        assert response.status_code == 201, f"Failed to create task: {response.text}"
        
        task = response.json()
        yield task
        
        # Cleanup
        httpx.delete(f"{BASE_URL}/api/tasks/{task['taskId']}")
    
    def test_create_task(self, created_task):
        """Task is created with correct data."""
        assert "taskId" in created_task
        assert created_task["title"].startswith("Test Task")
        assert created_task["status"] == "NEW"
        assert created_task["priority"] == 3
    
    def test_read_task(self, created_task):
        """Created task can be retrieved."""
        task_id = created_task["taskId"]
        response = httpx.get(f"{BASE_URL}/api/tasks/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["taskId"] == task_id
        assert data["title"] == created_task["title"]
    
    def test_update_task(self, created_task):
        """Task can be updated."""
        task_id = created_task["taskId"]
        
        response = httpx.put(f"{BASE_URL}/api/tasks/{task_id}", json={
            "status": "STARTED",
            "priority": 1
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "STARTED"
        assert data["priority"] == 1
    
    def test_delete_task(self):
        """Task can be deleted."""
        # Create a task specifically to delete
        response = httpx.post(f"{BASE_URL}/api/tasks", json={
            "title": f"Delete Me {uuid.uuid4().hex[:8]}",
            "priority": 5
        })
        task_id = response.json()["taskId"]
        
        # Delete it
        delete_response = httpx.delete(f"{BASE_URL}/api/tasks/{task_id}")
        assert delete_response.status_code == 204
        
        # Verify it's gone
        get_response = httpx.get(f"{BASE_URL}/api/tasks/{task_id}")
        assert get_response.status_code == 404


class TestQuickCapture:
    """Test the quick capture endpoint."""
    
    def test_quick_capture_creates_task(self):
        """Quick capture creates a task with minimal input."""
        response = httpx.post(f"{BASE_URL}/api/capture", json={
            "title": f"Quick Capture Test {uuid.uuid4().hex[:8]}",
            "project": "META",
            "category": "TEST"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert "taskId" in data
        assert data["message"].startswith("Task captured")
        
        # Cleanup
        httpx.delete(f"{BASE_URL}/api/tasks/{data['taskId']}")
    
    def test_quick_capture_minimal(self):
        """Quick capture works with just title."""
        response = httpx.post(f"{BASE_URL}/api/capture", json={
            "title": f"Minimal Capture {uuid.uuid4().hex[:8]}"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["category"] == "IDEA"  # Default
        
        # Cleanup
        httpx.delete(f"{BASE_URL}/api/tasks/{data['taskId']}")


class TestConversationFlow:
    """Test conversation/transaction history."""
    
    @pytest.fixture
    def conversation(self):
        """Create a conversation for testing."""
        response = httpx.post(f"{BASE_URL}/api/history/conversations", json={
            "source": "API",
            "projectCode": "META",
            "title": f"Test Conversation {uuid.uuid4().hex[:8]}"
        })
        
        assert response.status_code == 201
        conv = response.json()
        yield conv
        
        # No delete endpoint yet, conversation will persist
    
    def test_create_conversation(self, conversation):
        """Conversation is created."""
        assert "conversationGuid" in conversation
        assert conversation["source"] == "API"
    
    def test_get_conversation(self, conversation):
        """Conversation can be retrieved."""
        guid = conversation["conversationGuid"]
        response = httpx.get(f"{BASE_URL}/api/history/conversations/{guid}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["conversationGuid"] == guid


class TestMethodologyRules:
    """Test methodology rule retrieval."""
    
    def test_get_specific_rule(self):
        """Can retrieve a specific methodology rule."""
        # Try to get LL-030 (Developer Tests Before Handoff)
        response = httpx.get(f"{BASE_URL}/api/methodology/rules/LL-030")
        
        # May be 200 if seeded, 404 if not
        if response.status_code == 200:
            data = response.json()
            assert "violationPrompt" in data
            assert "severity" in data
        else:
            assert response.status_code == 404
```

---

### 3. tests/test_ui_smoke.py

```python
"""
MetaPM UI Smoke Tests (Playwright)
Verify the web interface renders and responds.

Usage: pytest tests/test_ui_smoke.py -v
Prerequisites: playwright install chromium
"""

import pytest
import os
from playwright.sync_api import Page, expect

BASE_URL = os.getenv("METAPM_URL", "https://metapm-XXXXX-uc.a.run.app")


class TestUISmoke:
    """Basic UI smoke tests."""
    
    def test_docs_page_loads(self, page: Page):
        """OpenAPI docs page loads without errors."""
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        
        page.goto(f"{BASE_URL}/docs")
        page.wait_for_load_state("networkidle")
        
        # Should see Swagger UI
        expect(page.locator("body")).to_be_visible()
        assert len(errors) == 0, f"Console errors: {errors}"
    
    def test_docs_no_network_failures(self, page: Page):
        """Docs page has no failed network requests."""
        failures = []
        page.on("requestfailed", lambda req: failures.append(f"{req.url}: {req.failure}"))
        
        page.goto(f"{BASE_URL}/docs")
        page.wait_for_load_state("networkidle")
        
        assert len(failures) == 0, f"Network failures: {failures}"
    
    def test_redoc_page_loads(self, page: Page):
        """ReDoc page loads."""
        page.goto(f"{BASE_URL}/redoc")
        page.wait_for_load_state("networkidle")
        
        expect(page.locator("body")).to_be_visible()
    
    def test_api_returns_json(self, page: Page):
        """API endpoint returns valid JSON."""
        response = page.request.get(f"{BASE_URL}/api/tasks")
        
        assert response.status == 200
        data = response.json()
        assert "tasks" in data


class TestAPIViaPlaywright:
    """Test API calls through Playwright's request context."""
    
    def test_create_and_verify_task(self, page: Page):
        """Create a task via API and verify it exists."""
        import uuid
        
        # Create task
        create_response = page.request.post(f"{BASE_URL}/api/tasks", data={
            "title": f"Playwright Test {uuid.uuid4().hex[:8]}",
            "priority": 2
        })
        
        assert create_response.status == 201
        task = create_response.json()
        task_id = task["taskId"]
        
        # Verify it exists
        get_response = page.request.get(f"{BASE_URL}/api/tasks/{task_id}")
        assert get_response.status == 200
        
        # Cleanup
        page.request.delete(f"{BASE_URL}/api/tasks/{task_id}")
    
    def test_health_check(self, page: Page):
        """Health endpoint via Playwright."""
        response = page.request.get(f"{BASE_URL}/health")
        
        assert response.status == 200
        assert response.json()["status"] == "healthy"
```

---

### 4. tests/conftest.py (Updated)

```python
"""
MetaPM Test Configuration
Pytest fixtures and setup
"""

import pytest
import os
from playwright.sync_api import Page
from fastapi.testclient import TestClient

# Set test URL
os.environ.setdefault("METAPM_URL", "https://metapm-XXXXX-uc.a.run.app")


@pytest.fixture(scope="session")
def base_url():
    """Base URL for API tests."""
    return os.getenv("METAPM_URL")


@pytest.fixture
def sample_task():
    """Sample task data for testing."""
    import uuid
    return {
        "title": f"Test task {uuid.uuid4().hex[:8]}",
        "description": "This is a test task",
        "priority": 2,
        "projects": ["META"],
        "categories": ["TEST"]
    }


@pytest.fixture
def sample_quick_capture():
    """Sample quick capture request."""
    import uuid
    return {
        "title": f"Quick capture {uuid.uuid4().hex[:8]}",
        "project": "META",
        "category": "IDEA"
    }
```

---

## Running Tests

### Before Running

1. Update `BASE_URL` in test files or set environment variable:
   ```powershell
   $env:METAPM_URL = "https://metapm-your-id-uc.a.run.app"
   ```

2. Ensure database is seeded with projects and categories

### Run All Tests

```powershell
# Run all tests with verbose output
pytest tests/ -v

# Run only smoke tests (fast)
pytest tests/test_api_smoke.py -v

# Run integration tests
pytest tests/test_api_integration.py -v

# Run Playwright UI tests
pytest tests/test_ui_smoke.py -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html
```

### Expected Results

| Test File | Expected Passing | Notes |
|-----------|------------------|-------|
| test_api_smoke.py | 15+ tests | All should pass if deployed |
| test_api_integration.py | 10+ tests | Requires DB with seed data |
| test_ui_smoke.py | 5+ tests | Requires Playwright installed |

---

## Handoff Checklist

Before handing off to Project Lead:

- [ ] All smoke tests pass
- [ ] All integration tests pass
- [ ] Playwright UI tests pass
- [ ] No console errors in browser
- [ ] No network failures
- [ ] Test output included in handoff report

---

## Handoff Report Template

```markdown
## Test Results: MetaPM v2.0

**Deployed to**: [CLOUD_RUN_URL]
**Tested at**: [TIMESTAMP]

### Smoke Tests
```
pytest tests/test_api_smoke.py -v
# Output:
# test_root_returns_service_info PASSED
# test_health_endpoint PASSED
# ... (paste full output)
# 15 passed in 2.34s
```

### Integration Tests
```
pytest tests/test_api_integration.py -v
# Output:
# ... (paste full output)
# 10 passed in 4.56s
```

### Playwright UI Tests
```
pytest tests/test_ui_smoke.py -v
# Output:
# ... (paste full output)
# 5 passed in 8.12s
```

### Summary
- [x] All smoke tests pass
- [x] All integration tests pass
- [x] Playwright tests pass
- [x] No 500 errors on any endpoint
- [x] No console errors in browser

Ready for Project Lead review.
```

---

**Test Plan Version**: 2.0  
**Last Updated**: January 2026  
**Methodology**: project-methodology v3.12.1
