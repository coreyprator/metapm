# [MetaPM] 🔴 UI Fixes Based on UAT (v1.6.1)

**UAT Date**: 2026-02-03  
**Current Version**: 1.6.0  
**Target Version**: 1.6.1

---

## UAT Results Summary

| Area | Status | Issue |
|------|--------|-------|
| Title Bar | ❌ **FAIL** | 6 lines instead of 1 |
| Version Badge | ❌ **FAIL** | Poor contrast, shows "(unknown)" |
| View Selector | ✅ Pass | Tabs OK (user preference) |
| Filter Bar | ✅ Pass | Working |
| Task Rows | ⚠️ **Needs Polish** | Tighter padding, add borders |
| Column Order | ❌ **FAIL** | Status/Priority/Project should be LEFT of title |
| Status Bar | ✅ Pass | Fixed at bottom |
| Multi-Select | ✅ Pass | + New requirement below |
| Auto-Prefix | ❌ **FAIL** | BUG-XXX / REQ-XXX not generated |
| Row Colors | ⚠️ **Needs Polish** | Need more contrast |

---

## BUGS TO FIX

### 1. Title Bar — Condense to Single Line (P1)

**Current** (6 lines):
```
MetaPM v1.6.0 (unknown)
✓ Synced
Tue, Feb 3
☀️🌙💻
Tasks Projects AI History Methodology Backlog + Add Task
Status: Active  Priority: All  Project: All ...
```

**Expected** (2 lines max):
```
MetaPM v1.6.0  ✓ Synced  Tue, Feb 3  [☀️][🌙][💻]  [+ Add Task]
[Tasks] [Projects] [AI History] [Methodology] [Backlog]    Status: [All▼] Priority: [All▼] ...
```

**Fix**: Use flexbox with `flex-wrap: nowrap` and proper spacing:

```css
.title-bar {
    display: flex;
    flex-direction: row;
    flex-wrap: nowrap;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 8px 16px;
    white-space: nowrap;
}

.title-bar > * {
    flex-shrink: 0;
}

/* Group related items */
.title-section {
    display: flex;
    align-items: center;
    gap: 8px;
}

.sync-section {
    display: flex;
    align-items: center;
    gap: 8px;
}

.theme-section {
    display: flex;
    align-items: center;
    gap: 4px;
}
```

**HTML structure**:
```html
<header class="title-bar">
    <div class="title-section">
        <span class="app-name">MetaPM</span>
        <span class="version-badge">v1.6.1</span>
    </div>
    <span class="sync-status">✓ Synced</span>
    <span class="date">Tue, Feb 3</span>
    <div class="theme-section">
        <button class="theme-btn">☀️</button>
        <button class="theme-btn">🌙</button>
        <button class="theme-btn">💻</button>
    </div>
    <button class="add-btn">+ Add Task</button>
</header>

<nav class="tab-bar">
    <button class="tab-btn active">Tasks</button>
    <button class="tab-btn">Projects</button>
    <!-- ... -->
</nav>

<div class="filter-bar">
    <!-- filters -->
</div>
```

---

### 2. Version Badge — Fix Contrast & Remove "(unknown)" (P2)

**Current**: Dark purple on black, shows "v1.6.0 (unknown)"

**Issues**:
1. "(unknown)" should not appear — this is likely an unset variable
2. Colors have poor contrast

**Fix the "(unknown)"** — find where version is set:
```python
# In config.py or main.py, ensure VERSION is properly defined
VERSION = "1.6.1"  # Not VERSION = os.getenv("VERSION", "unknown")
```

Or in frontend:
```javascript
// If version is fetched from API, ensure it's displayed correctly
const version = data.version || "1.6.1";
document.querySelector('.version-badge').textContent = `v${version}`;
// Remove any "(unknown)" suffix
```

**Fix the contrast** — use high-contrast colors:
```css
.version-badge {
    background: #4ade80;  /* Bright green */
    color: #000000;       /* Black text */
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.85rem;
    font-weight: 600;
}

/* Or for dark theme with light badge */
.version-badge {
    background: rgba(255, 255, 255, 0.9);
    color: #1f2937;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.85rem;
    font-weight: 600;
}
```

---

### 3. Task Row Column Order — Move Status/Priority/Project to LEFT (P2)

**Current order**:
```
☐ | 🐛 | Title text here... | NEW | P1 | ArtForge | ⋮
```

**Expected order** (badges BEFORE title):
```
☐ | 🐛 | NEW | P1 | AF | Title text here...                    | ⋮
```

**Fix CSS grid**:
```css
.task-row {
    display: grid;
    /* Old: checkbox, type, title, status, priority, project, actions */
    /* New: checkbox, type, status, priority, project, title, actions */
    grid-template-columns: 40px 40px 70px 50px 70px 1fr 40px;
    align-items: center;
    gap: 8px;
}
```

**Fix HTML order**:
```html
<div class="task-row">
    <div class="task-checkbox"><input type="checkbox"></div>
    <div class="task-type">🐛</div>
    <div class="task-status"><span class="badge new">NEW</span></div>
    <div class="task-priority"><span class="badge p1">P1</span></div>
    <div class="task-project"><span class="badge">AF</span></div>
    <div class="task-title">Title text here...</div>
    <div class="task-actions">⋮</div>
</div>
```

---

### 4. Task Rows — Tighter Padding & Grid Borders (P3)

**Current**: Too much padding, no visual grid lines

**Fix padding**:
```css
.task-row {
    padding: 6px 12px;  /* Reduced from 10px 16px */
}

.task-row .badge {
    padding: 2px 6px;   /* Compact badges */
    font-size: 0.7rem;
}
```

**Add grid borders**:
```css
.task-list {
    border: 1px solid var(--border-color);
    border-radius: 8px;
    overflow: hidden;
}

.task-row {
    border-bottom: 1px solid var(--border-color);
}

.task-row:last-child {
    border-bottom: none;
}

/* Optional: vertical dividers between columns */
.task-row > div:not(:last-child) {
    border-right: 1px solid var(--border-subtle);
}

/* Define border colors for dark theme */
:root {
    --border-color: #374151;
    --border-subtle: #1f2937;
}
```

---

### 5. Alternating Row Colors — Increase Contrast (P3)

**Current**: Too subtle difference between odd/even rows

**Fix** — increase the difference by 25%+:
```css
/* Dark theme */
.task-row.odd {
    background: #1f2937;  /* Darker */
}

.task-row.even {
    background: #111827;  /* Even darker, or */
    background: #293548;  /* Lighter alternative for more contrast */
}

/* Better contrast option */
.task-row.odd {
    background: #1e293b;  /* Slate-800 */
}

.task-row.even {
    background: #0f172a;  /* Slate-900 */
}

/* Or use a slight tint for one */
.task-row.odd {
    background: #1f2937;
}

.task-row.even {
    background: rgba(59, 130, 246, 0.08);  /* Slight blue tint */
}
```

---

### 6. Auto-Prefix Not Working (P1)

**Current**: Creating a Bug doesn't add "BUG-XXX:" prefix to title

**Expected**: 
- Create Bug with title "Test" → Saved as "BUG-001: Test"
- Create Requirement with title "Feature" → Saved as "REQ-001: Feature"

**Debug**: Check the backend task creation logic:

```python
# In tasks.py or wherever tasks are created
@router.post("/tasks")
async def create_task(task: TaskCreate, db = Depends(get_db)):
    title = task.title
    
    # Auto-prefix based on type
    if task.task_type == 'bug':
        # Get next bug number
        result = db.execute("""
            SELECT MAX(CAST(
                SUBSTRING(Title, 5, PATINDEX('%[^0-9]%', SUBSTRING(Title, 5, 10) + 'X') - 1)
            AS INT))
            FROM Tasks WHERE Title LIKE 'BUG-%'
        """).fetchone()
        next_num = (result[0] or 0) + 1
        title = f"BUG-{next_num:03d}: {task.title}"
        
    elif task.task_type == 'requirement':
        result = db.execute("""
            SELECT MAX(CAST(
                SUBSTRING(Title, 5, PATINDEX('%[^0-9]%', SUBSTRING(Title, 5, 10) + 'X') - 1)
            AS INT))
            FROM Tasks WHERE Title LIKE 'REQ-%'
        """).fetchone()
        next_num = (result[0] or 0) + 1
        title = f"REQ-{next_num:03d}: {task.title}"
    
    # Create task with prefixed title
    new_task = Task(
        title=title,
        task_type=task.task_type,
        # ... other fields
    )
```

**Simpler approach** using Python:
```python
def get_next_prefix_number(db, prefix: str) -> int:
    """Get next number for BUG-XXX or REQ-XXX prefix."""
    import re
    
    # Get all titles with this prefix
    result = db.execute(
        "SELECT Title FROM Tasks WHERE Title LIKE ?",
        (f"{prefix}-%",)
    ).fetchall()
    
    max_num = 0
    pattern = re.compile(rf'^{prefix}-(\d+)')
    
    for row in result:
        match = pattern.match(row['Title'])
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)
    
    return max_num + 1


@router.post("/tasks")
async def create_task(task: TaskCreate, db = Depends(get_db)):
    title = task.title
    
    if task.task_type == 'bug' and not title.startswith('BUG-'):
        next_num = get_next_prefix_number(db, 'BUG')
        title = f"BUG-{next_num:03d}: {title}"
        
    elif task.task_type == 'requirement' and not title.startswith('REQ-'):
        next_num = get_next_prefix_number(db, 'REQ')
        title = f"REQ-{next_num:03d}: {title}"
    
    # ... create task with title
```

---

### 7. NEW: Bulk Status Update Dropdown (P2 — Enhancement)

**Requirement**: When items are selected, show a dropdown to bulk-update status

**UI Addition** — in the status bar:
```html
<footer class="status-bar">
    <div class="selection-info">
        <span id="selection-count">0 selected</span>
        
        <!-- NEW: Bulk status update -->
        <select id="bulk-status" disabled>
            <option value="">Set Status...</option>
            <option value="new">New</option>
            <option value="active">Active</option>
            <option value="blocked">Blocked</option>
            <option value="done">Done</option>
        </select>
        
        <button id="delete-selected" disabled>🗑️ Delete</button>
        <button id="clear-selection" disabled>✕ Clear</button>
    </div>
    <!-- ... stats on right -->
</footer>
```

**JavaScript**:
```javascript
const bulkStatusSelect = document.getElementById('bulk-status');

// Enable/disable based on selection
function updateSelectionUI() {
    const count = getSelectedCount();
    document.getElementById('selection-count').textContent = `${count} selected`;
    
    const hasSelection = count > 0;
    bulkStatusSelect.disabled = !hasSelection;
    document.getElementById('delete-selected').disabled = !hasSelection;
    document.getElementById('clear-selection').disabled = !hasSelection;
}

// Handle bulk status change
bulkStatusSelect.addEventListener('change', async (e) => {
    const newStatus = e.target.value;
    if (!newStatus) return;
    
    const selectedIds = getSelectedTaskIds();
    if (selectedIds.length === 0) return;
    
    // Confirm
    if (!confirm(`Update ${selectedIds.length} items to "${newStatus}"?`)) {
        e.target.value = '';
        return;
    }
    
    // Bulk update
    try {
        await fetch('/api/tasks/bulk-status', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_ids: selectedIds,
                status: newStatus
            })
        });
        
        // Refresh list
        await loadTasks();
        clearSelection();
        
    } catch (error) {
        alert('Bulk update failed: ' + error.message);
    }
    
    // Reset dropdown
    e.target.value = '';
});
```

**Backend endpoint**:
```python
@router.put("/tasks/bulk-status")
async def bulk_update_status(
    request: BulkStatusRequest,  # { task_ids: List[int], status: str }
    db = Depends(get_db)
):
    task_ids = request.task_ids
    new_status = request.status
    
    # Validate status
    valid_statuses = ['new', 'active', 'blocked', 'done']
    if new_status not in valid_statuses:
        raise HTTPException(400, f"Invalid status: {new_status}")
    
    # Update all selected tasks
    placeholders = ','.join('?' * len(task_ids))
    db.execute(
        f"UPDATE Tasks SET Status = ?, UpdatedAt = GETDATE() WHERE TaskID IN ({placeholders})",
        [new_status] + task_ids
    )
    db.commit()
    
    return {"updated": len(task_ids), "status": new_status}
```

---

## Summary of Fixes

| Priority | Issue | Fix |
|----------|-------|-----|
| P1 | Title bar 6 lines | Flexbox single line layout |
| P1 | Auto-prefix not working | Fix backend prefix generation |
| P2 | Version "(unknown)" | Remove conditional, hardcode version |
| P2 | Version contrast | High-contrast badge colors |
| P2 | Column order | Move status/priority/project LEFT of title |
| P2 | Bulk status update | NEW dropdown in status bar |
| P3 | Row padding | Reduce padding |
| P3 | Grid borders | Add row/column borders |
| P3 | Row contrast | Increase odd/even color difference |

---

## Acceptance Criteria

- [ ] Title bar is 1-2 lines max (header + tabs/filters)
- [ ] Version badge shows "v1.6.1" with high contrast (no "(unknown)")
- [ ] Task rows show: ☐ Type Status Priority Project | Title | Actions
- [ ] Creating Bug auto-generates "BUG-XXX:" prefix
- [ ] Creating Requirement auto-generates "REQ-XXX:" prefix
- [ ] Row padding is tighter
- [ ] Rows have visible borders/grid lines
- [ ] Alternating row colors have more contrast
- [ ] Bulk status dropdown works when items selected

---

## Version Bump

After fixes: **1.6.0 → 1.6.1**

---

## Files to Modify

| File | Changes |
|------|---------|
| `dashboard.html` | Layout restructure, bulk status dropdown |
| `styles.css` (or inline) | Flexbox layout, colors, borders, padding |
| `tasks.py` | Auto-prefix logic, bulk status endpoint |
| `config.py` | Ensure VERSION is hardcoded |
| `main.py` | VERSION constant |
