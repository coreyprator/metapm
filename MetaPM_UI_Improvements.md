# [MetaPM] 🔴 UI Improvements — Tighten Up Layout

**Version**: Current → Next patch  
**Date**: 2026-02-03  
**Priority**: P2 (UX polish)

---

## Overview

Tighten up the MetaPM UI for better information density and usability. Currently too much vertical space used, hard to scan items quickly.

---

## Current Issues

1. **Title bar**: Version # low contrast, elements spread across multiple lines
2. **Filters/sorts**: Take up too much vertical space
3. **Item rows**: Multi-line, wasted space, hard to scan
4. **No alternating row colors**: Hard to track across wide rows
5. **Multi-select controls**: Scroll off screen, lose context
6. **Task types**: Only differentiated by title prefix, not a proper field

---

## Design Changes

### 1. Title Bar (Single Line)

**Before** (multiple lines):
```
Tue, Feb 3
✓ Synced
[☀️] [🌙] [🖥️]

[Tasks] [Projects] [AI History] [Methodology] [📋 Backlog]
[Active] [New] [Blocked] [All]
```

**After** (condensed):
```
┌────────────────────────────────────────────────────────────────────────────┐
│ MetaPM v4.x.x        ✓ Synced   [☀️🌙🖥️]     [Tasks▼] [+ Add Task]        │
├────────────────────────────────────────────────────────────────────────────┤
│ Status: [All▼]  Priority: [All▼]  Project: [All▼]  Type: [All▼]  🔍 Search│
└────────────────────────────────────────────────────────────────────────────┘
```

**Implementation**:

```html
<header class="title-bar">
    <div class="title-section">
        <span class="app-name">MetaPM</span>
        <span class="version">v4.2.0</span>
    </div>
    
    <div class="sync-section">
        <span class="sync-status synced">✓ Synced</span>
        <span class="sync-time">Feb 3, 2:30 PM</span>
    </div>
    
    <div class="theme-section">
        <button class="theme-btn" data-theme="light">☀️</button>
        <button class="theme-btn" data-theme="dark">🌙</button>
        <button class="theme-btn" data-theme="system">🖥️</button>
    </div>
    
    <div class="tab-section">
        <select id="view-select" class="view-dropdown">
            <option value="tasks">Tasks</option>
            <option value="projects">Projects</option>
            <option value="ai-history">AI History</option>
            <option value="methodology">Methodology</option>
            <option value="backlog">📋 Backlog</option>
        </select>
    </div>
    
    <div class="add-section">
        <button id="add-btn" class="add-button">+ Add Task</button>
    </div>
</header>
```

**CSS**:
```css
.title-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 16px;
    background: var(--header-bg);
    border-bottom: 1px solid var(--border-color);
    gap: 16px;
}

.version {
    color: var(--text-secondary);
    font-size: 0.85rem;
    opacity: 0.8;
    background: var(--badge-bg);
    padding: 2px 8px;
    border-radius: 4px;
    margin-left: 8px;
}

/* Make version more visible */
.version {
    color: #ffffff;
    background: rgba(255,255,255,0.2);
}

/* Dark theme */
[data-theme="dark"] .version {
    background: rgba(255,255,255,0.15);
    color: #e5e7eb;
}
```

---

### 2. Filter Bar (Line 2)

**Compact horizontal filters**:

```html
<div class="filter-bar">
    <div class="filter-group">
        <label>Status:</label>
        <select id="filter-status">
            <option value="">All</option>
            <option value="new">New</option>
            <option value="active">Active</option>
            <option value="blocked">Blocked</option>
            <option value="done">Done</option>
        </select>
    </div>
    
    <div class="filter-group">
        <label>Priority:</label>
        <select id="filter-priority">
            <option value="">All</option>
            <option value="P1">P1</option>
            <option value="P2">P2</option>
            <option value="P3">P3</option>
        </select>
    </div>
    
    <div class="filter-group">
        <label>Project:</label>
        <select id="filter-project">
            <option value="">All</option>
            <option value="artforge">🟠 ArtForge</option>
            <option value="harmonylab">🔵 HarmonyLab</option>
            <option value="superflashcards">🟢 Super-Flashcards</option>
            <option value="etymython">🟣 Etymython</option>
            <option value="metapm">🔴 MetaPM</option>
        </select>
    </div>
    
    <div class="filter-group">
        <label>Type:</label>
        <select id="filter-type">
            <option value="">All</option>
            <option value="task">Task</option>
            <option value="bug">🐛 Bug</option>
            <option value="requirement">📋 Requirement</option>
        </select>
    </div>
    
    <div class="filter-group">
        <label>Sort:</label>
        <select id="sort-by">
            <option value="priority">Priority</option>
            <option value="created">Created</option>
            <option value="updated">Updated</option>
            <option value="status">Status</option>
        </select>
        <button id="sort-direction" class="sort-btn">↑</button>
    </div>
    
    <div class="search-group">
        <input type="text" id="search" placeholder="🔍 Search...">
    </div>
</div>
```

**CSS**:
```css
.filter-bar {
    display: flex;
    align-items: center;
    padding: 8px 16px;
    gap: 16px;
    background: var(--filter-bg);
    border-bottom: 1px solid var(--border-color);
    flex-wrap: wrap;
}

.filter-group {
    display: flex;
    align-items: center;
    gap: 6px;
}

.filter-group label {
    font-size: 0.8rem;
    color: var(--text-secondary);
    white-space: nowrap;
}

.filter-group select {
    padding: 4px 8px;
    border-radius: 4px;
    border: 1px solid var(--border-color);
    background: var(--input-bg);
    font-size: 0.85rem;
    min-width: 80px;
}

.search-group {
    margin-left: auto;
}

.search-group input {
    padding: 6px 12px;
    border-radius: 6px;
    border: 1px solid var(--border-color);
    background: var(--input-bg);
    width: 200px;
}
```

---

### 3. Item Rows (Single Line, Alternating Colors)

**Before** (multi-line, same color):
```
┌──────────────────────────────────────────────────────────┐
│ BUG-011: Stability AI 400 error on strength < 30%        │
│                                                          │
│ NEW                                                      │
│ P1                                                       │
└──────────────────────────────────────────────────────────┘
```

**After** (single line, alt colors):
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 🐛 │ BUG-011: Stability AI 400 error on strength < 30%  │ NEW │ P1 │ ArtForge│
├──────────────────────────────────────────────────────────────────────────────┤
│ 🐛 │ BUG-010: Stability AI 400 error on images > 1024px │ NEW │ P1 │ ArtForge│
├──────────────────────────────────────────────────────────────────────────────┤
│ 📋 │ REQ-007: Scene Iteration (Multi-version)           │ WIP │ P1 │ ArtForge│
└──────────────────────────────────────────────────────────────────────────────┘
```

**HTML Structure**:
```html
<div class="task-list">
    <div class="task-row odd" data-id="94">
        <div class="task-checkbox">
            <input type="checkbox" class="select-task">
        </div>
        <div class="task-type">
            <span class="type-badge bug">🐛</span>
        </div>
        <div class="task-title">
            BUG-011: Stability AI 400 error on strength < 30%
        </div>
        <div class="task-status">
            <span class="status-badge new">NEW</span>
        </div>
        <div class="task-priority">
            <span class="priority-badge p1">P1</span>
        </div>
        <div class="task-project">
            <span class="project-badge artforge">🟠 AF</span>
        </div>
        <div class="task-actions">
            <button class="action-btn">⋮</button>
        </div>
    </div>
    
    <div class="task-row even" data-id="95">
        <!-- ... -->
    </div>
</div>
```

**CSS**:
```css
.task-list {
    display: flex;
    flex-direction: column;
}

.task-row {
    display: grid;
    grid-template-columns: 40px 50px 1fr 80px 50px 80px 40px;
    align-items: center;
    padding: 10px 16px;
    border-bottom: 1px solid var(--border-color);
    cursor: pointer;
    transition: background 0.15s;
}

.task-row:hover {
    background: var(--hover-bg);
}

/* Alternating row colors */
.task-row.odd {
    background: var(--row-odd);
}

.task-row.even {
    background: var(--row-even);
}

/* Dark theme */
[data-theme="dark"] {
    --row-odd: #1f2937;
    --row-even: #111827;
    --hover-bg: #374151;
}

/* Light theme */
[data-theme="light"] {
    --row-odd: #ffffff;
    --row-even: #f9fafb;
    --hover-bg: #f3f4f6;
}

/* Type badges */
.type-badge {
    font-size: 1rem;
}

.type-badge.bug::before { content: '🐛'; }
.type-badge.requirement::before { content: '📋'; }
.type-badge.task::before { content: '✓'; }

/* Status badges */
.status-badge {
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 500;
    text-transform: uppercase;
}

.status-badge.new { background: #3b82f6; color: white; }
.status-badge.active { background: #22c55e; color: white; }
.status-badge.started { background: #f59e0b; color: white; }
.status-badge.blocked { background: #ef4444; color: white; }
.status-badge.done { background: #6b7280; color: white; }

/* Priority badges */
.priority-badge {
    font-size: 0.75rem;
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 600;
}

.priority-badge.p1 { background: #fecaca; color: #991b1b; }
.priority-badge.p2 { background: #fef3c7; color: #92400e; }
.priority-badge.p3 { background: #d1fae5; color: #065f46; }

/* Project badges */
.project-badge {
    font-size: 0.75rem;
    padding: 2px 6px;
    border-radius: 4px;
}

.task-title {
    font-size: 0.9rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
```

---

### 4. Bottom Status Bar (Fixed)

**Always visible at bottom**:

```html
<footer class="status-bar">
    <div class="selection-info">
        <span id="selection-count">0 selected</span>
        <button id="delete-selected" class="action-btn" disabled>🗑️ Delete</button>
        <button id="clear-selection" class="action-btn" disabled>✕ Clear</button>
    </div>
    
    <div class="stats-info">
        <span class="stat">51 New</span>
        <span class="stat">6 Active</span>
        <span class="stat">0 Blocked</span>
        <span class="stat">18 Done</span>
    </div>
</footer>
```

**CSS**:
```css
.status-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 16px;
    background: var(--statusbar-bg);
    border-top: 1px solid var(--border-color);
    z-index: 100;
}

.selection-info {
    display: flex;
    align-items: center;
    gap: 12px;
}

.selection-info button {
    padding: 4px 12px;
    border-radius: 4px;
    font-size: 0.85rem;
}

.selection-info button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.stats-info {
    display: flex;
    gap: 16px;
    font-size: 0.85rem;
    color: var(--text-secondary);
}

/* Add padding to main content so it doesn't hide behind status bar */
.task-list {
    padding-bottom: 60px;
}
```

---

### 5. Context-Aware Add Button

**JavaScript**:
```javascript
const viewSelect = document.getElementById('view-select');
const addBtn = document.getElementById('add-btn');

const addLabels = {
    'tasks': '+ Add Task',
    'projects': '+ Add Project',
    'ai-history': '+ Add Entry',
    'methodology': '+ Add Doc',
    'backlog': '+ Add Backlog Item'
};

viewSelect.addEventListener('change', (e) => {
    const view = e.target.value;
    addBtn.textContent = addLabels[view] || '+ Add';
    
    // Also update the type options in the add modal
    updateAddModalForView(view);
});

function updateAddModalForView(view) {
    // If on backlog, default type to 'backlog'
    // If adding from task view, show type selector (task, bug, requirement)
    const typeSelector = document.getElementById('add-type');
    
    if (view === 'backlog') {
        typeSelector.value = 'backlog';
        typeSelector.disabled = true;
    } else {
        typeSelector.disabled = false;
    }
}
```

---

### 6. Database Schema: Task Type Field

**Add TaskType column**:

```sql
-- Add TaskType column if not exists
IF NOT EXISTS (
    SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'Tasks' AND COLUMN_NAME = 'TaskType'
)
BEGIN
    ALTER TABLE Tasks ADD TaskType NVARCHAR(20) DEFAULT 'task';
END

-- Update existing tasks based on title prefix
UPDATE Tasks SET TaskType = 'bug' WHERE Title LIKE 'BUG-%';
UPDATE Tasks SET TaskType = 'requirement' WHERE Title LIKE 'REQ-%';

-- Create index for filtering
CREATE INDEX IX_Tasks_TaskType ON Tasks(TaskType);
```

**Update Task model**:
```python
class Task(Base):
    # ... existing fields ...
    task_type = Column(String(20), default='task')  # 'task', 'bug', 'requirement', 'backlog'
```

**Update API**:
```python
# When creating task
@router.post("/tasks")
async def create_task(task: TaskCreate):
    # Auto-generate prefix based on type
    if task.task_type == 'bug':
        next_num = get_next_bug_number()
        task.title = f"BUG-{next_num:03d}: {task.title}"
    elif task.task_type == 'requirement':
        next_num = get_next_req_number()
        task.title = f"REQ-{next_num:03d}: {task.title}"
    
    # ... create task
```

---

## Summary of Changes

| Area | Change |
|------|--------|
| **Title bar** | Single line: name, version (high contrast), sync, theme, view dropdown, add button |
| **Filter bar** | Horizontal dropdowns: Status, Priority, Project, Type, Sort, Search |
| **Item rows** | Single-line grid, alternating colors, type/status/priority badges |
| **Status bar** | Fixed bottom: selection count, delete/clear buttons, stats |
| **Add button** | Context-aware label based on current view |
| **Task type** | New database field, auto-prefix generation |

---

## Files to Modify

| File | Changes |
|------|---------|
| `frontend/index.html` | New layout structure |
| `frontend/styles.css` | All CSS changes above |
| `frontend/app.js` | Context-aware add button, selection handling |
| `app/models.py` | Add TaskType field |
| `app/migrations.py` | Add column, migrate existing data |
| `app/routers/tasks.py` | Filter by type, auto-prefix |
| `app/schemas.py` | Add task_type to schemas |

---

## Visual Mockup (Dark Theme)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ MetaPM [v4.2.0]     ✓ Synced 2:30 PM    [☀🌙🖥]    [Tasks ▼]    [+ Add Task] │
├────────────────────────────────────────────────────────────────────────────────┤
│ Status: [All ▼]  Priority: [All ▼]  Project: [All ▼]  Type: [All ▼]  🔍 Search│
├────────────────────────────────────────────────────────────────────────────────┤
│ ☐ │ 🐛 │ BUG-011: Stability AI 400 error on strength < 30% │ NEW │ P1 │ 🟠 AF │
│ ☐ │ 🐛 │ BUG-010: Stability AI 400 error on images > 1024px│ NEW │ P1 │ 🟠 AF │
│ ☐ │ 📋 │ REQ-007: Scene Iteration (Multi-version)          │ WIP │ P1 │ 🟠 AF │
│ ☐ │ 📋 │ REQ-005: Reference Image Support (img2img)        │ WIP │ P1 │ 🟠 AF │
│ ☐ │ 📋 │ REQ-004: Character Sheets                         │ WIP │ P1 │ 🟠 AF │
│ ☐ │ 🐛 │ BUG-016: Scene titles not editable                │ NEW │ P2 │ 🟠 AF │
│ ☐ │ 🐛 │ BUG-013: Reference image needs preview            │ NEW │ P2 │ 🟠 AF │
│ ☐ │ 📋 │ REQ-008: Reference image picker from Scene Vers.  │ NEW │ P2 │ 🟠 AF │
│ ☐ │ 🐛 │ BUG-009: Strength slider not persisting           │ NEW │ P2 │ 🟠 AF │
│ ☐ │ 🐛 │ BUG-007: Reference image not persisting           │ NEW │ P2 │ 🟠 AF │
│                                                                                │
│                          (scrollable list area)                                │
│                                                                                │
├────────────────────────────────────────────────────────────────────────────────┤
│ 0 selected  [🗑️ Delete] [✕ Clear]          51 New  6 Active  0 Blocked  18 Done│
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## Acceptance Criteria

- [ ] Title bar on single line with high-contrast version
- [ ] Theme buttons grouped horizontally
- [ ] View selector as dropdown (saves horizontal space)
- [ ] Add button changes label based on view
- [ ] Filter bar with dropdowns: Status, Priority, Project, Type, Sort
- [ ] Search field on right side of filter bar
- [ ] Item rows are single-line with grid layout
- [ ] Alternating row colors (odd/even)
- [ ] Type shown as icon badge (🐛 📋 ✓)
- [ ] Status, Priority, Project as compact badges
- [ ] Fixed bottom status bar
- [ ] Selection count updates live
- [ ] Delete/Clear buttons enable when items selected
- [ ] Stats (New/Active/Blocked/Done) always visible
- [ ] TaskType field in database
- [ ] Auto-prefix generation for bugs/requirements
- [ ] Filter by type works

---

## Version

Bump version after changes.
