# MetaPM UI Testing - FAILURE REPORT & REMEDIATION REQUIRED

**Date:** January 13, 2026  
**Tester:** Project Lead (Manual Verification)  
**Environment:** https://metapm.rentyourcio.com/static/dashboard.html

---

## CRITICAL ISSUE: Tests Check Existence, Not Function

Your Playwright tests are checking "does element exist" NOT "does element work."

**Example of BAD test:**
```python
# This passes even if dropdown is empty!
await expect(page.locator('#projectFilter')).toBeVisible()
```

**Example of GOOD test:**
```python
# This verifies the dropdown has actual options
await expect(page.locator('#projectFilter option')).toHaveCount({ minimum: 2 })
# This verifies selecting an option actually filters
await page.selectOption('#projectFilter', 'META')
await expect(page.locator('#taskList .badge:has-text("META")')).toBeVisible()
await expect(page.locator('#taskList .badge:has-text("AF")')).not.toBeVisible()
```

**Definition of Done for a Filter:**
1. Dropdown is populated with options from API
2. Selecting an option calls the API with filter parameter
3. The displayed list changes to show only matching items
4. Selecting "All" removes the filter

---

## TEST RESULTS - ACTUAL VERIFICATION

| Test | VS Code Result | PL Manual Result | Issue |
|------|----------------|------------------|-------|
| test_default_tab_is_tasks | ✅ Passed | ✅ PASS | Works correctly |
| test_task_project_filter | ✅ Passed | ❌ **FAIL** | Dropdown is EMPTY - no project options |
| test_project_theme_filter | ? | ❌ **FAIL** | Not clear what was tested |
| test_project_open_tasks_filter | ✅ Passed | ✅ PASS | Checkbox works |
| test_history_project_filter | ✅ Passed | ❌ **FAIL** | Dropdown is EMPTY - no project options |
| test_history_source_filter | ✅ Passed | ❌ **FAIL** | Only shows "Web" - missing VOICE, MOBILE, All Sources |
| test_history_date_range_filter | ✅ Passed | ❌ **FAIL** | Missing date ranges: Today, This Week, This Month |
| test_methodology_rules_loaded | ✅ Passed | ✅ PASS | Rules display correctly |

**Actual Pass Rate: 3/8 (37.5%)** - NOT 8/8 as reported

---

## DETAILED FAILURES WITH SCREENSHOTS

### FAILURE #1: Task Project Filter (Screenshot 1)

**What I See:**
- Dropdown shows "All Projects" 
- When clicked, dropdown is EMPTY (no project options)
- Scrollbar visible but nothing to scroll

**Root Cause:** `populateProjectFilters()` is not being called, OR the API call to `/api/projects` is failing, OR the options are not being inserted into the SELECT element.

**Definition of Done:**
- [ ] Dropdown shows: All Projects, META, EM, HL, SF, AF, etc. (all project codes)
- [ ] Selecting "META" filters task list to only META tasks
- [ ] Selecting "All Projects" shows all tasks

**Fix Required:**
```javascript
// Verify this runs on page load
async function populateProjectFilters() {
    const res = await fetch(`${API}/api/projects`);
    const data = await res.json();
    const select = document.getElementById('projectFilter');
    select.innerHTML = '<option value="">All Projects</option>' +
        data.projects.map(p => `<option value="${p.projectCode}">${p.projectCode}</option>`).join('');
}
// Must be called in init
populateProjectFilters();
```

---

### FAILURE #2: AI History Project Filter (Screenshot 2)

**What I See:**
- Dropdown shows "All Projects"
- When clicked, dropdown is EMPTY

**Root Cause:** Same as above - `#historyProjectFilter` not populated

**Definition of Done:**
- [ ] Dropdown populated with all project codes
- [ ] Selecting a project filters conversation list
- [ ] API called with `?project_code=XXX`

---

### FAILURE #3: AI History Source Filter (Screenshot 3)

**What I See:**
- Dropdown shows "All Sources"
- When clicked, only shows "Web"
- Missing: VOICE, MOBILE

**Root Cause:** Hardcoded options missing or incomplete

**Definition of Done:**
- [ ] Dropdown shows: All Sources, VOICE, WEB, MOBILE
- [ ] Selecting "VOICE" shows only voice captures
- [ ] Selecting "WEB" shows only web captures

**Fix Required:**
```html
<select id="historySourceFilter" class="form-input">
    <option value="">All Sources</option>
    <option value="VOICE">Voice</option>
    <option value="WEB">Web</option>
    <option value="MOBILE">Mobile</option>
</select>
```

---

### FAILURE #4: AI History Date Range Filter (Screenshot 4)

**What I See:**
- Only "Newest First" and "All Time" visible
- Missing: Today, This Week, This Month, Oldest First

**Definition of Done:**
- [ ] Sort options: Newest First, Oldest First
- [ ] Date range options: Today, This Week, This Month, All Time
- [ ] Selecting "Today" filters to today's conversations only
- [ ] Selecting "This Week" filters to current week

**Fix Required:**
```html
<select id="historySortFilter" class="form-input">
    <option value="desc">Newest First</option>
    <option value="asc">Oldest First</option>
</select>
<select id="historyDateRange" class="form-input">
    <option value="">All Time</option>
    <option value="today">Today</option>
    <option value="week">This Week</option>
    <option value="month">This Month</option>
</select>
```

```javascript
// Date range logic
function getDateRangeAfter(range) {
    const now = new Date();
    switch(range) {
        case 'today':
            return new Date(now.getFullYear(), now.getMonth(), now.getDate()).toISOString();
        case 'week':
            const monday = new Date(now);
            monday.setDate(now.getDate() - now.getDay() + 1);
            monday.setHours(0,0,0,0);
            return monday.toISOString();
        case 'month':
            return new Date(now.getFullYear(), now.getMonth(), 1).toISOString();
        default:
            return null;
    }
}
```

---

## NEW BUG DISCOVERED

### BUG: Task Duplication on Create

**Steps to Reproduce:**
1. Click "Add new task..."
2. Fill in task details
3. Click Save
4. Task appears TWICE in the list

**Expected:** Task appears once

**Root Cause Hypothesis:** 
- Form submit handler firing twice (missing `e.preventDefault()`?)
- Or `loadTasks()` being called before API returns, then again after
- Or event listener registered twice

**Fix Required:** Debug the task creation flow. Check for:
```javascript
document.getElementById('taskForm').addEventListener('submit', async e => {
    e.preventDefault();  // Must be present
    e.stopPropagation(); // Add this
    // ... rest of handler
});
```

---

## NEW REQUIREMENT: Full Text Search

**Requirement:** Add full text search to each tab

### Tasks Tab
- Search box filters tasks by title and description
- Real-time filtering as user types (debounced)
- API: `GET /api/tasks?search=keyword`

### Projects Tab  
- Search box filters projects by name, code, description
- API: `GET /api/projects?search=keyword`

### AI History Tab
- Search conversations by title/content
- API: `GET /api/transactions/conversations?search=keyword`

### Methodology Tab
- Search rules by code, name, description
- API: `GET /api/methodology/rules?search=keyword`

**UI Pattern:**
```html
<input type="text" id="taskSearch" class="form-input" placeholder="Search tasks...">
```

```javascript
document.getElementById('taskSearch').addEventListener('input', 
    debounce(e => filterTasks(e.target.value), 300)
);
```

**Note:** Full-text search indexes already exist in database (per previous sessions).

---

## REQUIRED PLAYWRIGHT TESTS - CORRECTED

Replace your tests with these that verify FUNCTION not just EXISTENCE:

```python
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "https://metapm.rentyourcio.com"

def test_task_project_filter_has_options(page: Page):
    """Verify project filter dropdown is populated"""
    page.goto(f"{BASE_URL}/static/dashboard.html")
    page.wait_for_load_state("networkidle")
    
    # Dropdown must have more than just "All Projects"
    options = page.locator('#projectFilter option')
    expect(options).to_have_count(greater_than=1)
    
    # Verify at least one project code exists
    expect(page.locator('#projectFilter')).to_contain_text('META')

def test_task_project_filter_works(page: Page):
    """Verify selecting a project filters the task list"""
    page.goto(f"{BASE_URL}/static/dashboard.html")
    page.wait_for_load_state("networkidle")
    
    # Select META project
    page.select_option('#projectFilter', 'META')
    page.wait_for_timeout(500)  # Wait for filter
    
    # All visible tasks should be META
    task_badges = page.locator('#taskList .badge')
    for i in range(task_badges.count()):
        expect(task_badges.nth(i)).to_have_text('META')

def test_history_source_filter_has_all_options(page: Page):
    """Verify source filter has VOICE, WEB, MOBILE options"""
    page.goto(f"{BASE_URL}/static/dashboard.html")
    page.click('.tab-btn[data-tab="history"]')
    
    select = page.locator('#historySourceFilter')
    expect(select).to_contain_text('VOICE')
    expect(select).to_contain_text('WEB')
    expect(select).to_contain_text('MOBILE')

def test_history_date_range_has_options(page: Page):
    """Verify date range filter has Today, This Week, This Month"""
    page.goto(f"{BASE_URL}/static/dashboard.html")
    page.click('.tab-btn[data-tab="history"]')
    
    select = page.locator('#historyDateRange')
    expect(select).to_contain_text('Today')
    expect(select).to_contain_text('This Week')
    expect(select).to_contain_text('This Month')

def test_task_creation_no_duplicates(page: Page):
    """Verify creating a task doesn't create duplicates"""
    page.goto(f"{BASE_URL}/static/dashboard.html")
    page.wait_for_load_state("networkidle")
    
    # Count tasks before
    initial_count = page.locator('#taskList .item-row').count()
    
    # Create a task
    page.click('#addTaskBtn')
    page.fill('#taskTitle', f'Test Task {datetime.now().timestamp()}')
    page.click('#taskForm button[type="submit"]')
    page.wait_for_timeout(1000)
    
    # Count tasks after - should be exactly +1
    final_count = page.locator('#taskList .item-row').count()
    assert final_count == initial_count + 1, f"Expected {initial_count + 1} tasks, got {final_count}"
```

---

## ACTION REQUIRED

1. **Fix the 4 broken filters** - populate dropdowns, wire up event handlers
2. **Fix task duplication bug** - debug form submission
3. **Add full-text search** - new requirement
4. **Rewrite Playwright tests** - test FUNCTION not EXISTENCE
5. **Deploy and verify** - with REAL test output

**Do NOT report back until:**
- All filters are populated AND functional
- Task duplication bug is fixed
- Playwright tests verify actual behavior
- You provide screenshots or test output proving it works

---

## METHODOLOGY REFERENCE

- **LL-030:** Developer Tests Before Handoff - YOU must verify it works
- **LL-031:** VS Code Cannot Manually Test - Use Playwright to verify
- **LL-020:** External Verification - Your tests passed but feature didn't work = bad tests
- **TEST-HUMAN-VISIBLE:** Tests must verify actual human-visible functionality
