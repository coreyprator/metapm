# MetaPM Dashboard UI Updates - Specification

**Target URL:** https://metapm-67661554310.us-central1.run.app  
**Custom Domain:** https://metapm.rentyourcio.com  
**Dashboard File:** `static/dashboard.html`

---

## UI Update #1: Default Tab = Tasks

**Current Behavior:** Unknown default tab state  
**Expected Behavior:** When dashboard loads, Tasks tab is active and visible by default

**Acceptance Criteria:**
- [ ] On page load, `#tab-tasks` is visible (not hidden)
- [ ] Tasks tab button has `tab-active` class
- [ ] Other tabs (Projects, AI History, Methodology) are hidden
- [ ] Tasks data loads automatically on page load

**Playwright Test:**
```javascript
await page.goto('/static/dashboard.html');
await expect(page.locator('#tab-tasks')).toBeVisible();
await expect(page.locator('.tab-btn[data-tab="tasks"]')).toHaveClass(/tab-active/);
```

---

## UI Update #2: Tasks Tab - Project Filter

**Current Behavior:** Project filter dropdown exists but may not filter correctly  
**Expected Behavior:** Multi-select or dropdown to filter tasks by one or more projects

**Acceptance Criteria:**
- [ ] Project filter dropdown (`#projectFilter`) is visible on Tasks tab
- [ ] Dropdown is populated with all project codes from `/api/projects`
- [ ] Selecting a project filters the task list to only tasks linked to that project
- [ ] Selecting "All Projects" shows all tasks
- [ ] Filter persists during tab navigation (optional enhancement)

**API Endpoint:** `GET /api/tasks?project={projectCode}`

**Playwright Test:**
```javascript
await page.goto('/static/dashboard.html');
await page.selectOption('#projectFilter', 'META');
// Verify task list updates - tasks should have projectCode = META
await expect(page.locator('#taskList .badge:has-text("META")')).toBeVisible();
```

---

## UI Update #3: Projects Tab - Theme/Status Filter

**Current Behavior:** Theme and Status dropdowns exist  
**Expected Behavior:** Filter projects by theme and/or status

**Acceptance Criteria:**
- [ ] Theme filter (`#themeFilter`) dropdown populated with unique themes
- [ ] Status filter (`#statusFilter`) dropdown has options: All, ACTIVE, BLOCKED, PLANNED
- [ ] Selecting a theme filters project list
- [ ] Selecting a status filters project list
- [ ] Filters can be combined (theme AND status)

**Playwright Test:**
```javascript
await page.click('.tab-btn[data-tab="projects"]');
await page.selectOption('#themeFilter', 'Learning');
// Verify only Learning projects visible
await expect(page.locator('#projectList')).toContainText('Learning');
```

---

## UI Update #4: Projects Tab - Show Only Projects with Open Tasks

**Current Behavior:** All projects shown regardless of task status  
**Expected Behavior:** Add checkbox or toggle to show only projects that have non-DONE tasks

**Acceptance Criteria:**
- [ ] Add a checkbox/toggle: "Show only projects with open tasks"
- [ ] When checked, projects with 0 open tasks (NEW, STARTED, BLOCKED) are hidden
- [ ] When unchecked, all projects shown
- [ ] Default: unchecked (show all)

**Implementation Hint:** 
The project list already has `taskCount` - filter client-side or add API param.

**Playwright Test:**
```javascript
await page.click('.tab-btn[data-tab="projects"]');
await page.check('#showOpenTasksOnly'); // or click toggle
// Verify projects with 0 tasks are hidden
```

---

## UI Update #5: AI History Tab - Project Filter (Implement)

**Current Behavior:** Dropdown shows "All Projects" but selecting a project doesn't filter  
**Expected Behavior:** Filter AI History (Conversations) by project

**Acceptance Criteria:**
- [ ] Project filter dropdown (`#historyProjectFilter`) populated from `/api/projects`
- [ ] Selecting a project calls API with `?project_code={code}`
- [ ] History list shows only conversations for that project
- [ ] "All Projects" shows all conversations

**API Endpoint:** `GET /api/transactions/conversations?project_code={code}`

**Playwright Test:**
```javascript
await page.click('.tab-btn[data-tab="history"]');
await page.selectOption('#historyProjectFilter', 'EM');
await page.waitForResponse(resp => resp.url().includes('project_code=EM'));
// Verify results filtered
```

---

## UI Update #6: AI History Tab - Source Filter (Implement)

**Current Behavior:** Dropdown shows "All Sources" only  
**Expected Behavior:** Filter by source: VOICE, WEB, MOBILE

**Acceptance Criteria:**
- [ ] Source filter dropdown (`#historySourceFilter`) has options: All Sources, VOICE, WEB, MOBILE
- [ ] Selecting a source filters the conversation list
- [ ] API called with `?source={source}`

**API Endpoint:** `GET /api/transactions/conversations?source=VOICE`

**Playwright Test:**
```javascript
await page.click('.tab-btn[data-tab="history"]');
await page.selectOption('#historySourceFilter', 'VOICE');
await page.waitForResponse(resp => resp.url().includes('source=VOICE'));
```

---

## UI Update #7: AI History Tab - Date Range Filter

**Current Behavior:** Only "Newest First" option  
**Expected Behavior:** Sort order AND date range filtering

**Acceptance Criteria:**
- [ ] Sort dropdown has: Newest First, Oldest First
- [ ] Add date range dropdown: Today, This Week, This Month, All Time
- [ ] Date range calculates `after` parameter for API
- [ ] Sort order uses `sort_order` parameter

**Date Range Logic:**
- Today: `after = today 00:00:00`
- This Week: `after = Monday 00:00:00`
- This Month: `after = 1st of month 00:00:00`
- All Time: no `after` parameter

**API Endpoint:** `GET /api/transactions/conversations?sort_order=asc&after=2026-01-12T00:00:00Z`

**Playwright Test:**
```javascript
await page.click('.tab-btn[data-tab="history"]');
await page.selectOption('#historySortFilter', 'asc');
await page.selectOption('#historyDateRange', 'today');
```

---

## UI Update #8: Methodology Rules - Verify Loaded

**Status:** ALREADY COMPLETE (per Project Lead)

**Verification Only - No Code Changes:**
- [ ] Navigate to Methodology tab
- [ ] Click "Rules" sub-tab
- [ ] Verify rules list is NOT empty
- [ ] Verify rules display RuleCode, RuleName, Severity

**Expected Data:** 40+ rules in database (run SQL to verify: `SELECT COUNT(*) FROM MethodologyRules WHERE IsActive = 1`)

**Playwright Test:**
```javascript
await page.click('.tab-btn[data-tab="methodology"]');
await page.click('.method-tab[data-subtab="rules"]');
await expect(page.locator('#rulesList')).not.toContainText('No rules defined');
await expect(page.locator('#rulesList .item-row')).toHaveCount({ minimum: 20 });
```

---

## Test Data Setup

**Projects exist in database:**
- META, EM, HL, SF, AF (with tasks)
- Various themes: Creation, Learning, Meta, Adventure, Relationships

**Tasks exist:** Verify with `GET /api/tasks` - should return tasks

**Conversations exist:** Verify with `GET /api/transactions/conversations` - may be empty if no voice captures done

**Methodology Rules:** 40+ rules after running `03_populate_methodology_CORRECTED.sql`

---

## Playwright Test File Structure

```
tests/
├── test_dashboard.py
│   ├── test_default_tab_is_tasks()
│   ├── test_task_project_filter()
│   ├── test_project_theme_filter()
│   ├── test_project_open_tasks_filter()
│   ├── test_history_project_filter()
│   ├── test_history_source_filter()
│   ├── test_history_date_range_filter()
│   └── test_methodology_rules_loaded()
```

---

## Deployment Verification

After deploy, VS Code must:

1. **Check version number** - Visible in app or console
2. **Run Playwright tests** - All 8 tests pass
3. **Report format:**

```
DEPLOYMENT COMPLETE
-------------------
Version: v2.1.0
URL: https://metapm.rentyourcio.com
Revision: metapm-00039-xxx

Playwright Results:
✅ test_default_tab_is_tasks - PASSED
✅ test_task_project_filter - PASSED
✅ test_project_theme_filter - PASSED
✅ test_project_open_tasks_filter - PASSED
✅ test_history_project_filter - PASSED
✅ test_history_source_filter - PASSED
✅ test_history_date_range_filter - PASSED
✅ test_methodology_rules_loaded - PASSED

8/8 tests passed. Ready for review.
```

---

## Summary: 7 Implementations + 1 Verification

| # | Update | Tab | Status |
|---|--------|-----|--------|
| 1 | Default tab = Tasks | All | Implement |
| 2 | Project filter for tasks | Tasks | Implement |
| 3 | Theme/Status filter | Projects | Verify/Fix |
| 4 | Show only projects with open tasks | Projects | Implement |
| 5 | Project filter working | AI History | Implement |
| 6 | Source filter working | AI History | Implement |
| 7 | Date range + sort | AI History | Implement |
| 8 | Rules loaded | Methodology | Verify Only |

**DO NOT report back until all 7 implementations are complete, deployed, and tested.**
