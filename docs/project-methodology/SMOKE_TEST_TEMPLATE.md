# Smoke Test Template

**Purpose**: Verify deployed app is functional before user testing.

> ⚠️ **"Deployed" ≠ "Working"**
> 
> Smoke tests catch 500 errors and broken deployments before users encounter them.

---

## When to Run Smoke Tests

- ✅ After every deployment to Cloud Run
- ✅ Before any user testing session
- ✅ When debugging "Internal Server Error" issues
- ✅ After infrastructure changes (secrets, database, etc.)

---

## Test Layers

Smoke tests are organized in layers, from basic to complex:

### Layer 1: App Running
Verify the application starts and responds.

| Test | Endpoint | Expected |
|------|----------|----------|
| Health check | `GET /health` | 200 OK |
| Homepage | `GET /` | 200 OK (not 500) |
| API docs | `GET /docs` | 200 OK |

### Layer 2: Database Connected
Verify database connectivity and data access.

| Test | Endpoint | Expected |
|------|----------|----------|
| List endpoint | `GET /api/v1/[resource]` | 200 with data (not empty) |
| Single item | `GET /api/v1/[resource]/1` | 200 with item |

### Layer 3: Auth Configured
Verify authentication endpoints work (if applicable).

| Test | Endpoint | Expected |
|------|----------|----------|
| Auth status | `GET /api/v1/auth/status` | 200 or 401 (not 500) |
| OAuth redirect | `GET /api/v1/auth/login` | 302 redirect (not 500) |

### Layer 4: Protected Endpoints
Verify authorization works correctly.

| Test | Endpoint | Condition | Expected |
|------|----------|-----------|----------|
| Without auth | `GET /api/v1/protected` | No token | 401 Unauthorized |
| With auth | `GET /api/v1/protected` | Valid token | 200 OK |

### Layer 5: Error Handling
Verify errors return appropriate status codes (not 500).

| Test | Endpoint | Expected |
|------|----------|----------|
| Not found | `GET /api/v1/[resource]/99999` | 404 Not Found |
| Invalid input | `POST /api/v1/[resource]` with bad data | 400 or 422 |

### Layer 6: Ready Check
Combined verification that app is ready for users.

| Test | Description | Expected |
|------|-------------|----------|
| Full workflow | Complete a core user action | Success |

---

## Sample Smoke Test Code (pytest)

```python
# tests/test_smoke.py
"""
Smoke tests for {{PROJECT_NAME}}
Run against deployed URL to verify deployment works.

Usage:
    export BASE_URL=https://your-app-xxxxx-uc.a.run.app
    pytest tests/test_smoke.py -v
"""

import os
import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")


class TestLayer1AppRunning:
    """Layer 1: Verify app starts and responds"""
    
    def test_health_endpoint(self):
        """Health endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
    
    def test_homepage_loads(self):
        """Homepage loads without 500 error"""
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code != 500, f"Homepage returned 500: {response.text}"
    
    def test_api_docs_accessible(self):
        """API docs are accessible"""
        response = requests.get(f"{BASE_URL}/docs")
        assert response.status_code == 200, f"API docs failed: {response.text}"


class TestLayer2DatabaseConnected:
    """Layer 2: Verify database connectivity"""
    
    def test_data_endpoint_returns_data(self):
        """Data endpoint returns data (not empty)"""
        response = requests.get(f"{BASE_URL}/api/v1/items")  # Adjust endpoint
        assert response.status_code == 200, f"Data endpoint failed: {response.text}"
        # Optionally verify data exists
        # data = response.json()
        # assert len(data) > 0, "No data returned"


class TestLayer3AuthConfigured:
    """Layer 3: Verify auth endpoints respond (not 500)"""
    
    @pytest.mark.skipif(not os.environ.get("HAS_AUTH"), reason="No auth configured")
    def test_auth_endpoint_responds(self):
        """Auth endpoint responds (200 or 401, not 500)"""
        response = requests.get(f"{BASE_URL}/api/v1/auth/status")
        assert response.status_code in [200, 401], f"Auth returned {response.status_code}: {response.text}"


class TestLayer4ProtectedEndpoints:
    """Layer 4: Verify protected endpoints return 401 without auth"""
    
    @pytest.mark.skipif(not os.environ.get("HAS_AUTH"), reason="No auth configured")
    def test_protected_returns_401_without_auth(self):
        """Protected endpoint returns 401 without auth (not 500)"""
        response = requests.get(f"{BASE_URL}/api/v1/protected")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"


class TestLayer5ErrorHandling:
    """Layer 5: Verify error handling returns proper status codes"""
    
    def test_not_found_returns_404(self):
        """Non-existent resource returns 404 (not 500)"""
        response = requests.get(f"{BASE_URL}/api/v1/items/99999999")  # Adjust endpoint
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"


class TestLayer6ReadyCheck:
    """Layer 6: Combined readiness verification"""
    
    def test_app_is_ready(self):
        """App is ready for user testing"""
        # Health check
        health = requests.get(f"{BASE_URL}/health")
        assert health.status_code == 200, "Health check failed"
        
        # Can load main page
        main = requests.get(f"{BASE_URL}/")
        assert main.status_code != 500, "Main page returns 500"
        
        print("✅ App is ready for user testing")


def quick_check():
    """Quick smoke test for manual verification"""
    print(f"Testing {BASE_URL}...")
    
    checks = [
        ("Health", f"{BASE_URL}/health"),
        ("Homepage", f"{BASE_URL}/"),
        ("Docs", f"{BASE_URL}/docs"),
    ]
    
    all_passed = True
    for name, url in checks:
        try:
            response = requests.get(url, timeout=10)
            status = "✅" if response.status_code != 500 else "❌"
            print(f"  {status} {name}: {response.status_code}")
            if response.status_code == 500:
                all_passed = False
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            all_passed = False
    
    if all_passed:
        print("\n✅ All smoke tests passed - ready for user testing")
    else:
        print("\n❌ Smoke tests failed - fix before user testing")
    
    return all_passed


if __name__ == "__main__":
    quick_check()
```

---

## Running Smoke Tests

### Prerequisites

```bash
pip install requests pytest
```

### Set Base URL

```bash
# Get Cloud Run URL
export BASE_URL=$(gcloud run services describe [SERVICE_NAME] --region=us-central1 --format="value(status.url)")

# Or set manually
export BASE_URL=https://your-app-xxxxx-uc.a.run.app
```

### Run All Smoke Tests

```bash
pytest tests/test_smoke.py -v
```

### Quick Manual Check

```bash
python -c "from tests.test_smoke import quick_check; quick_check()"
```

### Run Specific Layer

```bash
pytest tests/test_smoke.py::TestLayer1AppRunning -v
pytest tests/test_smoke.py::TestLayer2DatabaseConnected -v
```

---

## Smoke Test Results Template

| Layer | Status | Notes |
|-------|--------|-------|
| 1. App Running | ☐ Pass / ☐ Fail | |
| 2. Database Connected | ☐ Pass / ☐ Fail | |
| 3. Auth Configured | ☐ Pass / ☐ Fail / ☐ N/A | |
| 4. Protected Endpoints | ☐ Pass / ☐ Fail / ☐ N/A | |
| 5. Error Handling | ☐ Pass / ☐ Fail | |
| 6. Ready Check | ☐ Pass / ☐ Fail | |

**Result**: ☐ Ready for user testing / ☐ Needs fixes

---

## Common Issues

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| All tests return 500 | App not starting | Check Cloud Run logs |
| Health passes, data fails | Database not connected | Verify secrets, connection string |
| Auth returns 500 | OAuth misconfigured | Check redirect URIs, client ID |
| 404 instead of expected data | Routes not registered | Check FastAPI router imports |
| Connection timeout | Cloud Run not deployed | Verify deployment succeeded |

---

## Integration with CI/CD

Add smoke tests to GitHub Actions (optional, after deployment):

```yaml
# In deploy.yml, after deployment step
- name: Run Smoke Tests
  run: |
    export BASE_URL=$(gcloud run services describe $SERVICE_NAME --region=us-central1 --format="value(status.url)")
    pip install requests pytest
    pytest tests/test_smoke.py -v --tb=short
```

---

**Template Version**: 3.7  
**Last Updated**: December 2025  
**Methodology**: [coreyprator/project-methodology](https://github.com/coreyprator/project-methodology)
