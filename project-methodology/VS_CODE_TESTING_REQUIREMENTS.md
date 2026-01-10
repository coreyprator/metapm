# VS Code Testing Requirements Before Handoff

**Purpose**: Define exactly what VS Code AI must do to verify code works BEFORE handing off to Project Lead.

> ⚠️ **Core Rule**: VS Code cannot manually test. It must use automated tools to verify its own work. "I think it works" is not acceptable. "Tests pass" is required.

---

## The Problem

VS Code AI literally **cannot**:
- Open a browser
- See the UI render
- Click buttons
- Check DevTools console
- Verify visual appearance
- Test on mobile viewports

**Therefore**: VS Code must use automated testing tools (Playwright, pytest, curl) to verify its work. Without automated tests, VS Code is coding blind and the Project Lead becomes the only tester.

---

## Mandatory Testing By Work Type

### Frontend/UI Work

**Required Tool**: Playwright

**Setup** (if not already installed):
```powershell
pip install playwright pytest-playwright --break-system-packages
playwright install chromium
```

**VS Code Must Run These Tests Before Handoff**:

```python
# tests/test_ui_smoke.py
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "https://[YOUR-CLOUD-RUN-URL]"  # Update per project

class TestUISmoke:
    """VS Code runs these BEFORE every handoff."""
    
    def test_page_loads_without_console_errors(self, page: Page):
        """REQUIRED: Page loads without JavaScript errors."""
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        assert len(errors) == 0, f"Console errors found: {errors}"
    
    def test_no_network_failures(self, page: Page):
        """REQUIRED: No failed network requests."""
        failures = []
        page.on("requestfailed", lambda req: failures.append(f"{req.url}: {req.failure}"))
        
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        assert len(failures) == 0, f"Network failures: {failures}"
    
    def test_key_elements_visible(self, page: Page):
        """REQUIRED: Key UI elements render."""
        page.goto(BASE_URL)
        
        # Verify page structure exists
        expect(page.locator("body")).to_be_visible()
        # Add project-specific selectors:
        # expect(page.locator("#app")).to_be_visible()
        # expect(page.locator("header")).to_be_visible()
        # expect(page.locator("main")).to_be_visible()
    
    def test_mobile_viewport(self, page: Page):
        """REQUIRED: Works on mobile (375x667)."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        expect(page.locator("body")).to_be_visible()
    
    def test_desktop_viewport(self, page: Page):
        """REQUIRED: Works on desktop (1920x1080)."""
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        expect(page.locator("body")).to_be_visible()
```

**Run Command**:
```powershell
pytest tests/test_ui_smoke.py -v
```

**Handoff Criteria**: ALL tests must pass. If any test fails, DO NOT hand off.

---

### Feature-Specific UI Tests

For each feature VS Code implements, add specific tests:

```python
# tests/test_feature_[name].py

def test_feature_renders(self, page: Page):
    """The feature I implemented actually appears on screen."""
    page.goto(f"{BASE_URL}/feature-page")
    
    # Replace with actual selectors for your feature
    expect(page.locator("#my-feature-container")).to_be_visible()
    expect(page.locator("#my-feature-button")).to_be_visible()

def test_feature_interaction(self, page: Page):
    """The feature responds to user interaction."""
    page.goto(f"{BASE_URL}/feature-page")
    
    # Click the button I implemented
    page.locator("#my-feature-button").click()
    
    # Verify expected result
    expect(page.locator("#result-container")).to_be_visible()
    # Or check for specific text:
    # expect(page.locator("#result")).to_contain_text("Success")

def test_feature_data_loads(self, page: Page):
    """Data from API actually displays."""
    page.goto(f"{BASE_URL}/feature-page")
    
    # Wait for data to load
    page.wait_for_selector("#data-list li", timeout=5000)
    
    # Verify data rendered (not empty)
    items = page.locator("#data-list li")
    assert items.count() > 0, "No data items rendered"
```

---

### API Endpoint Work

**Required Tool**: pytest + requests (or curl)

```python
# tests/test_api_smoke.py
import requests
import pytest

BASE_URL = "https://[YOUR-CLOUD-RUN-URL]"

class TestAPISmoke:
    """VS Code runs these BEFORE every API handoff."""
    
    def test_health_endpoint(self):
        """REQUIRED: Health check returns 200."""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
    
    def test_api_returns_json(self):
        """REQUIRED: API returns valid JSON."""
        response = requests.get(f"{BASE_URL}/api/v1/[endpoint]")
        assert response.status_code == 200
        data = response.json()  # Will fail if not valid JSON
        assert data is not None
    
    def test_no_500_errors(self):
        """REQUIRED: No internal server errors."""
        endpoints = [
            "/health",
            "/api/v1/[endpoint1]",
            "/api/v1/[endpoint2]",
        ]
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}")
            assert response.status_code != 500, f"500 error on {endpoint}"
```

**Run Command**:
```powershell
pytest tests/test_api_smoke.py -v
```

---

### Database Changes

**Required**: Run verification query after changes

```python
# tests/test_db_changes.py
import pyodbc

def test_schema_change_applied():
    """Verify schema change exists."""
    conn = get_connection()  # Your connection function
    cursor = conn.cursor()
    
    # Example: Verify column exists
    cursor.execute("""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'my_table' AND COLUMN_NAME = 'new_column'
    """)
    result = cursor.fetchone()
    assert result is not None, "Column 'new_column' does not exist"

def test_data_migration_complete():
    """Verify data migration ran correctly."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Example: Verify no nulls in required field
    cursor.execute("""
        SELECT COUNT(*) FROM my_table WHERE required_field IS NULL
    """)
    null_count = cursor.fetchone()[0]
    assert null_count == 0, f"{null_count} records have NULL required_field"
```

---

### Script/Automation Work

**Required**: Run the script and verify output

```python
# tests/test_script.py
import subprocess

def test_script_runs_without_error():
    """Script executes successfully."""
    result = subprocess.run(
        ["python", "scripts/my_script.py", "--dry-run"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"

def test_script_produces_expected_output():
    """Script output matches expectations."""
    result = subprocess.run(
        ["python", "scripts/my_script.py", "--dry-run"],
        capture_output=True,
        text=True
    )
    assert "Expected output text" in result.stdout
```

---

## Pre-Deploy Code Review Checklist

Before deploying, VS Code must verify no incomplete code:

```powershell
# Find TODOs/FIXMEs
Select-String -Path "*.py","*.js","*.html" -Pattern "TODO|FIXME|stub|not implemented" -Recurse

# Find empty functions
Select-String -Path "*.js" -Pattern "function.*\{\s*\}" -Recurse
```

**Checklist**:
- [ ] No `TODO` in production code paths
- [ ] No `FIXME` in production code paths  
- [ ] No empty function bodies
- [ ] No `console.log("not implemented")`
- [ ] Every `onclick` handler calls a function that exists
- [ ] Every function called actually does something

**Rule**: If you wrote `// TODO` or an empty function, it's not ready to deploy.

---

## Handoff Report Template

VS Code MUST provide this report with every handoff:

```markdown
## Handoff: [Feature/Fix Name]

**Version**: v[X.Y.Z] (verify at [location])
**Deployed to**: [CLOUD_RUN_URL]

### What was implemented
[Description of changes]

### Automated Tests Run
```
pytest tests/test_ui_smoke.py -v
# Output:
# test_page_loads_without_console_errors PASSED
# test_no_network_failures PASSED
# test_key_elements_visible PASSED
# test_mobile_viewport PASSED
# test_desktop_viewport PASSED
# 
# 5 passed in 3.42s
```

### Feature-Specific Tests
```
pytest tests/test_feature_[name].py -v
# Output:
# test_feature_renders PASSED
# test_feature_interaction PASSED
#
# 2 passed in 1.23s
```

### Self-Verification Completed
- [x] All smoke tests pass
- [x] Feature-specific tests pass
- [x] No console errors (verified by Playwright)
- [x] No network failures (verified by Playwright)
- [x] Feature renders on desktop viewport
- [x] Feature renders on mobile viewport
- [x] No TODO/FIXME in code

### Known Limitations
[Any caveats or edge cases not covered]

### Ready for Review
Yes - all automated tests pass.
```

---

## What VS Code Cannot Say

These are NOT acceptable handoff statements:

| ❌ Unacceptable | Why |
|-----------------|-----|
| "I think it works" | No automated verification |
| "It should work" | No automated verification |
| "Please test and let me know" | Shifts testing burden to PL |
| "I can't test the UI" | Must use Playwright |
| "The code looks correct" | Code review ≠ testing |
| "Ready for testing" | YOU must test first |

---

## What VS Code Must Say

These ARE acceptable handoff statements:

| ✅ Acceptable | Why |
|---------------|-----|
| "All 7 Playwright tests pass" | Automated verification |
| "pytest output shows 0 failures" | Automated verification |
| "Health endpoint returns 200" | Verified with actual request |
| "Console error test captured 0 errors" | Playwright verified |
| "Feature click test passed" | Interaction verified |

---

## Violation Response

If VS Code hands off code without running automated tests:

```
METHODOLOGY VIOLATION: You handed off untested code.

Per LL-030 and LL-031:
- VS Code cannot manually test UI
- Playwright is REQUIRED for UI work
- Automated tests must PASS before handoff

BEFORE asking me to review:
1. Write Playwright tests for this feature
2. Run: pytest tests/test_[feature].py -v
3. ALL tests must pass
4. Provide test output in handoff report

Do not hand off until you have passing automated tests.
```

---

## Quick Reference: Test Commands

```powershell
# Install Playwright (once)
pip install playwright pytest-playwright --break-system-packages
playwright install chromium

# Run all UI smoke tests
pytest tests/test_ui_smoke.py -v

# Run feature-specific tests
pytest tests/test_feature_*.py -v

# Run API tests
pytest tests/test_api_*.py -v

# Run all tests
pytest tests/ -v

# Find incomplete code
Select-String -Path "*.py","*.js","*.html" -Pattern "TODO|FIXME" -Recurse
```

---

## Summary

| Before Handoff | VS Code Must |
|----------------|--------------|
| **UI work** | Run Playwright tests, all pass |
| **API work** | Run pytest API tests, all pass |
| **Database work** | Run verification queries, all pass |
| **Scripts** | Run script, verify output |
| **Any code** | Search for TODO/FIXME, find none |
| **Handoff report** | Include test output, version number |

**The Rule**: No test output = no handoff.

---

**Template Version**: 3.12.1  
**Last Updated**: January 2026  
**Methodology**: [coreyprator/project-methodology](https://github.com/coreyprator/project-methodology)
