# TEST_PLAN.md Template

**Project**: {{PROJECT_NAME}}  
**Version**: 1.0  
**Last Updated**: {{DATE}}

---

## Testing Philosophy

> If it's in the requirements or user documentation, it MUST be tested.

| Category | What to Test |
|----------|--------------|
| Happy Path | Every documented feature works as described |
| Obvious Exceptions | User-friendly error messages for common mistakes |

---

## Test Environment

### Local Testing
```powershell
# Install test dependencies
pip install pytest pytest-cov pytest-asyncio httpx

# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

### CI Testing
Tests run automatically in GitHub Actions on every push to main.

Coverage threshold: **70%** (enforced in CI)

---

## Test Categories

### 1. Unit Tests

Tests for individual functions and methods.

| Test | Description | Expected Result |
|------|-------------|-----------------|
| `test_example_function` | Description of what's being tested | Expected outcome |

### 2. API Endpoint Tests

Tests for each API endpoint.

#### Health Check
| Test | Endpoint | Method | Expected |
|------|----------|--------|----------|
| `test_health_check` | `/health` | GET | 200, `{"status": "healthy"}` |

#### Core Endpoints
| Test | Endpoint | Method | Auth | Expected |
|------|----------|--------|------|----------|
| `test_create_item` | `/api/v1/items` | POST | Yes | 201, created item |
| `test_get_items` | `/api/v1/items` | GET | Yes | 200, list of items |
| `test_get_item_by_id` | `/api/v1/items/{id}` | GET | Yes | 200, single item |
| `test_update_item` | `/api/v1/items/{id}` | PUT | Yes | 200, updated item |
| `test_delete_item` | `/api/v1/items/{id}` | DELETE | Yes | 204, no content |

### 3. Error Handling Tests

Tests for error cases with user-friendly messages.

| Test | Scenario | Expected Status | Expected Message |
|------|----------|-----------------|------------------|
| `test_item_not_found` | GET non-existent item | 404 | "Item not found" |
| `test_invalid_input` | POST with missing fields | 422 | Validation error details |
| `test_unauthorized` | Request without auth | 401 | "Authentication required" |
| `test_forbidden` | Access other user's item | 403 | "Access denied" |

#### Error Message Quality Standards

```python
# ❌ BAD - Technical error exposed
{"detail": "NoneType has no attribute 'id'"}

# ✅ GOOD - User-friendly message
{"detail": "Item not found. It may have been deleted."}
```

### 4. Integration Tests

Tests for external service integrations.

| Test | Service | Scenario | Expected |
|------|---------|----------|----------|
| `test_database_connection` | Cloud SQL | Connect and query | Success |
| `test_external_api_call` | [API Name] | Make API request | Valid response |

### 5. Authentication Tests (if applicable)

| Test | Scenario | Expected |
|------|----------|----------|
| `test_valid_token` | Request with valid token | 200, authorized |
| `test_invalid_token` | Request with invalid token | 401, unauthorized |
| `test_expired_token` | Request with expired token | 401, unauthorized |
| `test_missing_token` | Request without token | 401, unauthorized |

---

## Test Data

### Fixtures
```python
# tests/conftest.py

import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def sample_item():
    return {
        "name": "Test Item",
        "description": "A test item"
    }
```

### Test Database
- [ ] Uses separate test database, OR
- [ ] Uses mocked database responses, OR
- [ ] Uses in-memory database

---

## Coverage Requirements

### Minimum Coverage: 70%

```yaml
# In GitHub Actions
pytest --cov=app --cov-report=xml --cov-fail-under=70
```

### Coverage Exclusions (if any)
```python
# In pyproject.toml or .coveragerc
[tool.coverage.run]
omit = [
    "*/tests/*",
    "*/migrations/*",
]
```

---

## Test Execution

### Run All Tests
```powershell
pytest -v
```

### Run Specific Test File
```powershell
pytest tests/test_api.py -v
```

### Run Specific Test
```powershell
pytest tests/test_api.py::test_health_check -v
```

### Run with Coverage Report
```powershell
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

---

## CI/CD Integration

### GitHub Actions Workflow
```yaml
- name: Run tests
  run: |
    pytest --cov=app --cov-report=xml --cov-fail-under=70
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

### Test Requirements
Tests must pass before deployment proceeds.

---

## Manual Testing Checklist

For features that require manual verification:

- [ ] Feature 1: [Description]
- [ ] Feature 2: [Description]
- [ ] End-to-end workflow completes successfully
- [ ] Error messages display correctly in UI

---

## Test Maintenance

### Adding New Tests
1. Identify feature or bug fix
2. Write test BEFORE implementing (TDD) or after
3. Ensure test passes locally
4. Verify coverage doesn't decrease
5. Push and confirm CI passes

### Updating Tests
When requirements change:
1. Update TEST_PLAN.md with new test cases
2. Update or add tests
3. Update expected results if behavior changed
4. Document breaking changes

---

## Appendix: Test File Structure

```
tests/
├── __init__.py
├── conftest.py           # Shared fixtures
├── test_api.py           # API endpoint tests
├── test_models.py        # Model/validation tests
├── test_database.py      # Database operation tests
└── test_integration.py   # External service tests
```
