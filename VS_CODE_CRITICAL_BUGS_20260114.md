# MetaPM Critical Bug Report - January 14, 2026

**Status:** ❌ NOT READY FOR SIGN-OFF  
**Reported Issues:** 8 bugs, 2 new requirements  
**Blocking:** Multiple 500 API errors, non-functional filters

---

## CRITICAL: API 500 ERRORS

These are blocking basic functionality. Fix these FIRST.

### 500 Error #1: GET /api/projects/{code}

**Console Error:**
```
/api/projects/TRIP-CANYON:1 Failed to load resource: status 500
/api/projects/AF:1 Failed to load resource: status 500
dashboard.html:1243 Failed to load project: SyntaxError: Unexpected token 'I', "Internal S"...
```

**Impact:** Cannot open any project for editing

**Root Cause:** The `get_project(code)` endpoint in `app/api/projects.py` has a SQL error - likely referencing a column that doesn't exist.

**Debug Steps:**
1. Open `app/api/projects.py`
2. Find the `get_project()` function
3. Check the SELECT statement for invalid columns
4. Compare against actual database schema

**Likely culprits:** `ContentHTML`, `GoalStatement`, `PriorityNextSteps`, `TechStack`, `ProductionURL`, `VSCodePath`, `GitHubURL` - verify these columns exist in the Projects table.

---

### 500 Error #2: POST /api/methodology/violations

**Console Error:**
```
POST https://metapm.rentyourcio.com/api/methodology/violations 500 (Internal Server Error)
```

**Impact:** Cannot log any methodology violations (see screenshot - form shows "Error: Internal Server Error")

**Root Cause:** The `create_violation()` endpoint in `app/api/methodology.py` has a SQL error.

**Debug Steps:**
1. Open `app/api/methodology.py`
2. Find the `create_violation()` function
3. Check the INSERT statement columns
4. Verify MethodologyViolations table schema

**Run this in SSMS to check schema:**
```sql
SELECT COLUMN_NAME, DATA_TYPE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'MethodologyViolations'
ORDER BY ORDINAL_POSITION;
```

---

### 500 Error #3: GET /api/methodology/violations (still broken)

**Impact:** Violations tab shows "Loading violations..." forever

**Same debug approach as above.**

---

## BUG FIXES REQUIRED

### Bug #1: Active Filter Shows Empty List

**Current Behavior:** Clicking "Active" shows "No Tasks found" even when NEW tasks exist

**Expected Behavior:** "Active" should show non-complete tasks (NEW, STARTED, BLOCKED - everything except DONE)

**Problem:** The filter logic is wrong. "Active" is filtering for `status === 'ACTIVE'` but there is no ACTIVE status - the statuses are: NEW, STARTED, BLOCKED, DONE.

**Fix:**
```javascript
// WRONG
if (filter === 'active') {
    filtered = filtered.filter(t => t.status === 'ACTIVE');
}

// CORRECT - Active means "not done"
if (filter === 'active') {
    filtered = filtered.filter(t => t.status !== 'DONE');
}
```

**Definition of Done:**
- [ ] Active filter shows all tasks where status != DONE
- [ ] With 13 NEW tasks, Active should show 13 tasks

---

### Bug #2: AI History Sort Order Not Working

**Current Behavior:** 
- Changing "Newest First" to "Oldest First" doesn't change order
- "Today" filter shows ALL items, not just today's

**Root Cause:** The `loadHistory()` function is not reading/using the sort and date filter values.

**Fix - Check these things:**

1. **Sort order not sent to API:**
```javascript
// Make sure this reads the dropdown
const sortOrder = document.getElementById('historySortOrder').value;
const url = `${API}/api/transactions/conversations?sort_order=${sortOrder}`;
```

2. **Date range not calculated:**
```javascript
// Make sure date range calculates the 'after' parameter
const dateRange = document.getElementById('historyDateRange').value;
let after = '';
if (dateRange === 'today') {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    after = today.toISOString();
} else if (dateRange === 'week') {
    // ... etc
}
const url = `${API}/api/transactions/conversations?sort_order=${sortOrder}&after=${after}`;
```

3. **Event listeners not wired:**
```javascript
// Make sure these call loadHistory()
document.getElementById('historySortOrder').addEventListener('change', loadHistory);
document.getElementById('historyDateRange').addEventListener('change', loadHistory);
```

**Definition of Done:**
- [ ] Selecting "Oldest First" shows oldest conversations first
- [ ] Selecting "Today" shows only today's conversations
- [ ] Selecting "This Week" shows only this week's conversations

---

### Bug #3: Filter Button Order

**Current Order:** All, New, Active, Blocked  
**Required Order:** Active, New, Blocked, All

**Fix:** Reorder the buttons in the HTML.

---

## NEW REQUIREMENTS

### New Requirement #1: Expand/Collapse Tasks Under Project

**Current Behavior:** Projects tab shows project cards with task count badge. Clicking opens edit form.

**Requested Behavior:** 
- Add a "+" button on each project card
- Clicking "+" expands to show all tasks for that project inline
- Clicking "-" collapses back to just the project card

**UI Mockup:**
```
┌─────────────────────────────────────┐
│ META - MetaPM Dashboard        [+]  │  ← Click + to expand
│ Theme: Meta | Status: ACTIVE        │
│ Tasks: 5                            │
└─────────────────────────────────────┘

     ↓ After clicking + ↓

┌─────────────────────────────────────┐
│ META - MetaPM Dashboard        [-]  │
│ Theme: Meta | Status: ACTIVE        │
│ Tasks: 5                            │
├─────────────────────────────────────┤
│   ○ Fix dropdown contrast     NEW   │
│   ○ Add offline sync         NEW   │
│   ○ Update methodology       DONE  │
│   ○ Deploy v2.1              DONE  │
│   ○ Write tests              STARTED│
└─────────────────────────────────────┘
```

**Implementation:**
```javascript
async function toggleProjectTasks(projectCode, element) {
    const tasksContainer = document.getElementById(`tasks-${projectCode}`);
    
    if (tasksContainer.classList.contains('hidden')) {
        // Expand - load tasks
        const res = await fetch(`${API}/api/projects/${projectCode}/tasks`);
        const data = await res.json();
        
        tasksContainer.innerHTML = data.tasks.map(t => `
            <div class="task-row">
                <span class="status-dot status-${t.status.toLowerCase()}"></span>
                ${t.title}
                <span class="badge">${t.status}</span>
            </div>
        `).join('');
        
        tasksContainer.classList.remove('hidden');
        element.textContent = '−';
    } else {
        // Collapse
        tasksContainer.classList.add('hidden');
        element.textContent = '+';
    }
}
```

---

### New Requirement #2: Color-Coded Projects (Peacock Style)

**Context:** Project Lead uses VS Code Peacock extension to color-code project windows. Want same colors in MetaPM.

**Requested Behavior:**
- Each project has an optional `ColorCode` field (hex color like `#FF6B6B`)
- The project badge on Tasks tab uses this color as background
- The project badge on AI History tab uses this color
- Project card on Projects tab has colored left border or header

**Database Change:**
```sql
ALTER TABLE Projects ADD ColorCode NVARCHAR(7);  -- e.g., '#FF6B6B'

-- Example colors matching Peacock
UPDATE Projects SET ColorCode = '#42b883' WHERE ProjectCode = 'META';   -- Vue Green
UPDATE Projects SET ColorCode = '#4FC08D' WHERE ProjectCode = 'EM';     -- Mint
UPDATE Projects SET ColorCode = '#007ACC' WHERE ProjectCode = 'HL';     -- Azure Blue
UPDATE Projects SET ColorCode = '#DD4814' WHERE ProjectCode = 'AF';     -- Ubuntu Orange
UPDATE Projects SET ColorCode = '#CF9FFF' WHERE ProjectCode = 'SF';     -- Lavender
```

**UI Implementation:**
```javascript
// When rendering task badges
function renderTaskBadge(projectCode, colorCode) {
    const bgColor = colorCode || '#6b7280';  // Default gray
    return `<span class="badge" style="background-color: ${bgColor}">${projectCode}</span>`;
}

// When rendering project cards
function renderProjectCard(project) {
    const borderColor = project.colorCode || '#6b7280';
    return `
        <div class="project-card" style="border-left: 4px solid ${borderColor}">
            ...
        </div>
    `;
}
```

**Project Edit Form:**
- Add color picker field to project edit modal
- Show preview of color

---

## PRIORITY ORDER

### Must Fix Now (Blocking)
1. ❌ `/api/projects/{code}` 500 error - Cannot edit projects
2. ❌ `/api/methodology/violations` POST 500 error - Cannot log violations
3. ❌ `/api/methodology/violations` GET 500 error - Cannot view violations
4. ❌ Active filter logic (change to `status !== 'DONE'`)
5. ❌ AI History sort order not working
6. ❌ AI History date range not filtering

### Should Fix
7. ⚠️ Filter button reorder (Active, New, Blocked, All)
8. ⚠️ Add favicon.ico and icon-192.png

### New Features (Next Sprint)
9. 📋 Expand/collapse tasks under project
10. 📋 Color-coded projects

---

## VERIFICATION REQUIRED

Before reporting complete, provide:

1. **Screenshot:** Active filter showing tasks (not empty)
2. **Screenshot:** AI History with "Oldest First" showing different order
3. **Screenshot:** Project edit modal opening successfully (no 500)
4. **Screenshot:** Violation logged successfully (no 500)
5. **Console:** No 500 errors

**Command to verify APIs work:**
```bash
# Test project endpoint
curl https://metapm.rentyourcio.com/api/projects/META

# Test violations GET
curl https://metapm.rentyourcio.com/api/methodology/violations

# Test violations POST
curl -X POST https://metapm.rentyourcio.com/api/methodology/violations \
  -H "Content-Type: application/json" \
  -d '{"ruleId": 1, "projectCode": "META", "context": "Test"}'
```

---

## DO NOT PROCEED TO NEW FEATURES UNTIL:

- [ ] All 500 errors resolved
- [ ] Active filter works correctly
- [ ] AI History sort/filter works
- [ ] Playwright tests verify FUNCTION not existence

The Offline CRUD (Sprint 3) and Violation AI Assistant (Sprint 4) are blocked until current bugs are fixed.
