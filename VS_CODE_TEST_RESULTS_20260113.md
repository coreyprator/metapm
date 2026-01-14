# MetaPM Testing Results - January 13, 2026

**Tester:** Project Lead  
**Environment:** https://metapm.rentyourcio.com/static/dashboard.html  
**VS Code Reported:** 8/8 Fixed  
**Actual Result:** Multiple issues remain

---

## TEST RESULTS SUMMARY

| # | Test Item | Result | Issue |
|---|-----------|--------|-------|
| 1 | Text Search (all tabs) | ✅ PASS | Works correctly |
| 2 | Task Status/Priority dropdowns | ❌ FAIL | No contrast - items invisible |
| 3 | Categories field | ❓ UNCLEAR | What is this? How to CRUD? |
| 4 | Active filter button | ❌ FAIL | Shows empty list, wrong order |
| 5 | All filter selectors | ❌ FAIL | No contrast - items invisible |
| 6 | AI History sort order | ❌ FAIL | Doesn't change list order |
| 7 | Methodology Violations | ❌ FAIL | 500 error, "Loading violations..." |
| 8 | Console errors | ❌ FAIL | Multiple errors found |

**Actual Pass Rate: 1/8 (12.5%)**

---

## DETAILED FAILURES

### FAILURE #1: Dropdown Contrast Issues (Tasks Tab)

**Location:** Edit Task modal → Status dropdown, Priority dropdown

**Problem:** When clicking the dropdown, the foreground and background colors are the same (or nearly the same). The options are invisible/unreadable.

**Expected:** White or light text on dark background, OR dark text on light background. Must be readable.

**Fix Required:**
```css
/* Ensure dropdown options are visible */
select option {
    background-color: #1e293b;  /* Dark background */
    color: #ffffff;             /* White text */
}

/* Or for light dropdowns */
select option {
    background-color: #ffffff;
    color: #1e293b;
}
```

**Definition of Done:**
- [ ] All dropdown options clearly visible
- [ ] Sufficient contrast ratio (4.5:1 minimum per WCAG)
- [ ] Test on both Chrome and Firefox

---

### FAILURE #2: Categories Field - Undefined

**Location:** Edit Task modal → bottom of form

**Questions:**
1. What is "Categories" supposed to do?
2. How does the user CRUD categories?
3. Is there a Categories table in the database?
4. How are categories different from Projects?

**Action Required:** Either:
- Document what Categories does and how to use it, OR
- Remove if not implemented, OR
- Implement properly with CRUD

---

### FAILURE #3: Active Filter Button (Tasks Tab)

**Current Behavior:**
- Clicking "Active" shows empty list
- Filter order is: All, New, Active, Blocked

**Expected Behavior:**
- "Active" should show non-complete tasks (status != DONE)
- Or show tasks with status = STARTED

**Required Filter Order (left to right):**
```
Active | New | Blocked | All
```

Rationale: Active is the most useful default view.

**Fix Required:**
```javascript
// Active should filter to STARTED status (or non-DONE)
if (filter === 'active') {
    tasks = tasks.filter(t => t.status === 'STARTED');
    // OR: tasks = tasks.filter(t => t.status !== 'DONE');
}
```

**Definition of Done:**
- [ ] Active filter shows tasks with status = STARTED (or non-DONE)
- [ ] Filter buttons reordered: Active, New, Blocked, All
- [ ] Active is visually highlighted as default

---

### FAILURE #4: All Filter Selectors - Contrast Issues

**Location:** All tabs - every dropdown/select element

**Problem:** Same as #1 - dropdown options not visible due to poor color contrast.

**Scope:** This affects:
- Task tab: Project filter, Status filter, Priority filter
- Projects tab: Theme filter, Status filter
- AI History tab: Project filter, Source filter, Sort filter, Date range filter
- Methodology tab: Category filter, Severity filter

**Fix Required:** Global CSS fix for all select elements.

---

### FAILURE #5: AI History Sort Order

**Location:** AI History tab → "Newest First" dropdown

**Problem:** Changing from "Newest First" to "Oldest First" doesn't change the list order.

**Root Cause:** Either:
- `loadHistory()` not reading the sort value, OR
- API not receiving sort parameter, OR
- API ignoring sort parameter

**Debug Steps:**
1. Check if `sort_order` param sent in API request (Network tab)
2. Check if API returns different order
3. Check if UI re-renders after selection

**Definition of Done:**
- [ ] Selecting "Oldest First" shows oldest conversations first
- [ ] Selecting "Newest First" shows newest first
- [ ] Verify with Network tab that `sort_order` param is sent

---

### FAILURE #6: Methodology Violations - 500 Error

**Location:** Methodology tab → Violations sub-tab

**Symptom:** Shows "Loading violations..." forever

**Console Error:**
```
/api/methodology/violations:1 Failed to load resource: status 500
dashboard.html:1612 Load violations failed: SyntaxError: Unexpected token 'I', "Internal S"... is not valid JSON
```

**Root Cause:** The `/api/methodology/violations` endpoint is returning "Internal Server Error" (500).

**Likely Issue:** Same as before - probably a column name mismatch in the SQL query (like the Rationale issue we fixed for rules).

**Debug Steps:**
1. Check `app/api/methodology.py` → `list_violations()` function
2. Compare SELECT columns to actual database schema
3. Check for missing columns: `Resolution`, `ResolvedAt`, `CopilotSessionRef`

**Definition of Done:**
- [ ] `/api/methodology/violations` returns 200 with JSON array
- [ ] Violations tab shows list (even if empty)
- [ ] No console errors

---

### FAILURE #7: Console Errors

**Errors Found:**

| Error | Severity | Fix |
|-------|----------|-----|
| `favicon.ico 404` | Low | Add favicon file |
| `icon-192.png 404` | Medium | Add PWA icon or fix manifest.json path |
| `/api/methodology/violations 500` | **HIGH** | Fix API endpoint |
| `Tailwind CDN warning` | Low | Use production Tailwind (future) |
| `apple-mobile-web-app-capable deprecated` | Low | Update meta tag |
| `message channel closed` | Medium | Service worker issue |

**Priority Fix:** The 500 error on violations API is blocking functionality.

---

## REQUIRED FIXES BEFORE SIGN-OFF

### Critical (Blocking)
1. [ ] Fix `/api/methodology/violations` 500 error
2. [ ] Fix dropdown contrast on ALL select elements

### High Priority
3. [ ] Fix Active filter to show non-complete tasks
4. [ ] Fix AI History sort order
5. [ ] Reorder filter buttons: Active, New, Blocked, All

### Medium Priority
6. [ ] Add favicon.ico
7. [ ] Fix PWA icon path (icon-192.png)
8. [ ] Document or remove Categories field

### Low Priority
9. [ ] Update apple-mobile-web-app-capable meta tag
10. [ ] Fix service worker message channel issue

---

## METHODOLOGY VIOLATIONS API - DEBUG GUIDE

Check `app/api/methodology.py` for the `list_violations` function.

**Current Schema (from earlier sessions):**
```sql
MethodologyViolations:
- ViolationID
- RuleID
- ProjectID  
- Context
- CopilotSessionRef  -- May be missing
- Resolution         -- May be missing
- ResolvedAt         -- May be missing
- CreatedAt
```

**If columns are missing, run:**
```sql
-- Check actual columns
SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'MethodologyViolations';

-- Add missing columns if needed
ALTER TABLE MethodologyViolations ADD CopilotSessionRef NVARCHAR(500);
ALTER TABLE MethodologyViolations ADD Resolution NVARCHAR(MAX);
ALTER TABLE MethodologyViolations ADD ResolvedAt DATETIME2;
```

---

## DO NOT REPORT COMPLETE UNTIL:

1. All dropdowns have visible options (contrast fixed)
2. `/api/methodology/violations` returns 200
3. Active filter shows non-complete tasks
4. AI History sort order works
5. No 500 errors in console
6. Playwright tests verify FUNCTION not just existence

**Report format required:**
```
VERIFIED WORKING:
- Screenshot of dropdown showing visible options
- Network tab showing violations API returning 200
- Active filter showing tasks
- Sort order changing list order
```
