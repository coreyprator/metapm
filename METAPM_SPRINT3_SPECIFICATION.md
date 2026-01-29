# MetaPM Sprint 3 - Feature Bundle Specification

**Version:** 1.0  
**Date:** January 14, 2026  
**Sprint Duration:** 8-12 days  
**Status:** READY FOR DEVELOPMENT

---

## Sprint Overview

This sprint delivers five features that enhance project visualization, usability, and offline capability.

| # | Feature | Priority | Est. Days |
|---|---------|----------|-----------|
| 1 | Project Color Themes (Peacock Style) | HIGH | 1-2 |
| 2 | Favicon Design & Implementation | MEDIUM | 0.5 |
| 3 | Task Sort by Modified Date | MEDIUM | 0.5 |
| 4 | Theme CRUD for Projects | HIGH | 1 |
| 5 | Offline Sync (PWA) | HIGH | 5-8 |

**Total Estimated Effort:** 8-12 days

---

## Pre-Sprint Checklist

Before starting, verify:
- [ ] Current deployment is stable (`metapm-00063-4tg`)
- [ ] All API endpoints return 200 (no 500 errors)
- [ ] Git is on `main` branch with clean working directory
- [ ] Read METAPM_OFFLINE_SYNC_SPECIFICATION.md in repo

---

## Feature 1: Project Color Themes (Peacock Style)

### 1.1 Requirement

Enable visual association between MetaPM projects and VS Code Peacock color themes. Each project can have a hex color code that appears on:
- Project badges on Tasks tab
- Project badges on AI History tab  
- Project cards on Projects tab (left border)
- Task edit modal project selector

### 1.2 Database Changes

```sql
-- Add ColorCode column to Projects table
ALTER TABLE Projects ADD ColorCode NVARCHAR(7) NULL;

-- Add comment for documentation
EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Hex color code for Peacock-style project theming (e.g., #FF6B6B)',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'TABLE', @level1name = N'Projects',
    @level2type = N'COLUMN', @level2name = N'ColorCode';

-- Sample colors (optional - PL can set via UI)
UPDATE Projects SET ColorCode = '#42b883' WHERE ProjectCode = 'META';   -- Vue Green
UPDATE Projects SET ColorCode = '#007ACC' WHERE ProjectCode = 'HL';     -- Azure Blue
UPDATE Projects SET ColorCode = '#DD4814' WHERE ProjectCode = 'AF';     -- Ubuntu Orange
UPDATE Projects SET ColorCode = '#CF9FFF' WHERE ProjectCode = 'SF';     -- Lavender
UPDATE Projects SET ColorCode = '#4FC08D' WHERE ProjectCode = 'EM';     -- Mint
```

### 1.3 API Changes

**GET /api/projects** - Already returns project data, ensure `colorCode` included:
```json
{
    "projectCode": "META",
    "projectName": "MetaPM Dashboard",
    "colorCode": "#42b883",
    ...
}
```

**PUT /api/projects/{code}** - Accept `colorCode` in update payload:
```json
{
    "colorCode": "#FF6B6B"
}
```

### 1.4 UI Changes

#### Project Badge Component
```javascript
// static/dashboard.html - Update renderTaskBadge function
function renderProjectBadge(projectCode) {
    const project = allProjects.find(p => p.projectCode === projectCode);
    const bgColor = project?.colorCode || '#6b7280';  // Default gray
    const textColor = getContrastColor(bgColor);  // Black or white based on brightness
    
    return `<span class="badge project-badge" 
                  style="background-color: ${bgColor}; color: ${textColor}">
                ${projectCode}
            </span>`;
}

// Helper: Calculate contrasting text color
function getContrastColor(hexColor) {
    const r = parseInt(hexColor.slice(1, 3), 16);
    const g = parseInt(hexColor.slice(3, 5), 16);
    const b = parseInt(hexColor.slice(5, 7), 16);
    const brightness = (r * 299 + g * 587 + b * 114) / 1000;
    return brightness > 128 ? '#000000' : '#ffffff';
}
```

#### Project Card (Projects Tab)
```javascript
function renderProjectCard(project) {
    const borderColor = project.colorCode || '#6b7280';
    return `
        <div class="project-card" style="border-left: 4px solid ${borderColor}">
            <div class="project-header">
                <span class="project-code" style="background-color: ${borderColor}; color: ${getContrastColor(borderColor)}">
                    ${project.projectCode}
                </span>
                <span class="project-name">${project.projectName}</span>
            </div>
            ...
        </div>
    `;
}
```

#### Project Edit Modal - Color Picker
```html
<!-- Add to project edit modal -->
<div class="form-group">
    <label for="projectColor">Project Color (Peacock Theme)</label>
    <div class="color-picker-row">
        <input type="color" id="projectColor" value="#6b7280">
        <input type="text" id="projectColorHex" placeholder="#6b7280" 
               pattern="^#[0-9A-Fa-f]{6}$" maxlength="7">
        <div id="colorPreview" class="color-preview"></div>
    </div>
    <small>Match your VS Code Peacock color for visual association</small>
</div>
```

```javascript
// Sync color picker with hex input
document.getElementById('projectColor').addEventListener('input', (e) => {
    document.getElementById('projectColorHex').value = e.target.value;
    document.getElementById('colorPreview').style.backgroundColor = e.target.value;
});

document.getElementById('projectColorHex').addEventListener('input', (e) => {
    if (/^#[0-9A-Fa-f]{6}$/.test(e.target.value)) {
        document.getElementById('projectColor').value = e.target.value;
        document.getElementById('colorPreview').style.backgroundColor = e.target.value;
    }
});
```

### 1.5 Test Cases

| Test ID | Description | Steps | Expected Result |
|---------|-------------|-------|-----------------|
| COLOR-001 | Color picker updates hex field | Open project edit, use color picker | Hex field shows matching value |
| COLOR-002 | Hex field updates color picker | Type valid hex in field | Color picker updates |
| COLOR-003 | Invalid hex rejected | Type "red" in hex field | Color picker unchanged |
| COLOR-004 | Color saved to database | Set color, save, reload | Color persists |
| COLOR-005 | Task badges show project color | Set META to #FF0000 | META badges are red |
| COLOR-006 | Project card border shows color | Set META to #FF0000 | Left border is red |
| COLOR-007 | Contrast text color | Set dark color (#000080) | Badge text is white |
| COLOR-008 | Contrast text color | Set light color (#FFFF00) | Badge text is black |

### 1.6 Playwright Tests

```python
# tests/test_project_colors.py

def test_color_picker_sync(page):
    """Color picker and hex input stay synchronized."""
    page.goto(f"{BASE_URL}/static/dashboard.html")
    page.click('.tab-btn[data-tab="projects"]')
    page.click('.project-card')  # Open first project
    
    # Set color via picker
    page.fill('#projectColor', '#FF6B6B')
    expect(page.locator('#projectColorHex')).to_have_value('#FF6B6B')

def test_color_persists_after_save(page):
    """Project color saves and loads correctly."""
    page.goto(f"{BASE_URL}/static/dashboard.html")
    page.click('.tab-btn[data-tab="projects"]')
    page.click('.project-card:has-text("META")')
    
    # Set color
    page.fill('#projectColorHex', '#42b883')
    page.click('#saveProjectBtn')
    page.wait_for_timeout(1000)
    
    # Reload and verify
    page.reload()
    page.click('.tab-btn[data-tab="projects"]')
    page.click('.project-card:has-text("META")')
    expect(page.locator('#projectColorHex')).to_have_value('#42b883')

def test_task_badge_uses_project_color(page):
    """Task badges display project color."""
    page.goto(f"{BASE_URL}/static/dashboard.html")
    
    # Get META badge
    badge = page.locator('.badge:has-text("META")').first
    bg_color = badge.evaluate('el => getComputedStyle(el).backgroundColor')
    
    # Should not be default gray
    assert bg_color != 'rgb(107, 114, 128)', "Badge should use project color"
```

---

## Feature 2: Favicon Design & Implementation

### 2.1 Requirement

Create a distinctive favicon for MetaPM that is visible in browser tabs.

### 2.2 Design Specification

**Concept:** Stylized "M" with task checkmark motif

**Sizes Required:**
- favicon.ico (16x16, 32x32, 48x48 multi-size)
- favicon-16x16.png
- favicon-32x32.png
- apple-touch-icon.png (180x180)
- icon-192.png (for PWA manifest)
- icon-512.png (for PWA manifest)

**Color Scheme:**
- Primary: #DC2626 (MetaPM red from existing UI)
- Secondary: #1E293B (dark background)
- Accent: #FFFFFF (white checkmark)

### 2.3 Implementation

#### Create Favicon Files
```bash
# Using ImageMagick or similar tool
# Or use online favicon generator with SVG source
```

**SVG Source for favicon:**
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="4" fill="#DC2626"/>
  <text x="16" y="24" font-family="Arial Black" font-size="22" fill="white" text-anchor="middle">M</text>
  <path d="M22 8 L26 12 L15 23 L10 18 L14 14 L15 15 L22 8" fill="#1E293B" opacity="0.3"/>
</svg>
```

#### Update HTML Head
```html
<!-- static/dashboard.html - Add to <head> -->
<link rel="icon" type="image/x-icon" href="/static/favicon.ico">
<link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/static/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/static/apple-touch-icon.png">
```

#### Update PWA Manifest
```json
// static/manifest.json
{
    "name": "MetaPM",
    "short_name": "MetaPM",
    "icons": [
        {
            "src": "/static/icon-192.png",
            "sizes": "192x192",
            "type": "image/png"
        },
        {
            "src": "/static/icon-512.png",
            "sizes": "512x512",
            "type": "image/png"
        }
    ],
    ...
}
```

### 2.4 Test Cases

| Test ID | Description | Steps | Expected Result |
|---------|-------------|-------|-----------------|
| ICON-001 | Favicon visible in browser | Open dashboard | Icon shows in tab |
| ICON-002 | No 404 for favicon.ico | Check Network tab | 200 response |
| ICON-003 | No 404 for icon-192.png | Check Network tab | 200 response |
| ICON-004 | PWA installable | Click install prompt | App installs with icon |

### 2.5 Playwright Tests

```python
def test_favicon_loads(page):
    """Favicon returns 200."""
    response = page.request.get(f"{BASE_URL}/static/favicon.ico")
    assert response.status == 200

def test_pwa_icon_loads(page):
    """PWA icon returns 200."""
    response = page.request.get(f"{BASE_URL}/static/icon-192.png")
    assert response.status == 200
```

---

## Feature 3: Task Sort by Modified Date

### 3.1 Requirement

Add ability to sort task list by last modified date (UpdatedAt) in addition to existing sorts.

### 3.2 UI Changes

```html
<!-- Add sort dropdown to Tasks tab -->
<div class="task-controls">
    <select id="taskSortOrder" class="form-input">
        <option value="priority">Sort by Priority</option>
        <option value="dueDate">Sort by Due Date</option>
        <option value="modified">Sort by Modified Date</option>
        <option value="created">Sort by Created Date</option>
        <option value="title">Sort by Title</option>
    </select>
    <select id="taskSortDirection" class="form-input">
        <option value="desc">Newest First</option>
        <option value="asc">Oldest First</option>
    </select>
</div>
```

### 3.3 JavaScript Implementation

```javascript
function sortTasks(tasks, sortBy, direction) {
    const sorted = [...tasks].sort((a, b) => {
        let comparison = 0;
        
        switch (sortBy) {
            case 'modified':
                comparison = new Date(a.updatedAt || 0) - new Date(b.updatedAt || 0);
                break;
            case 'created':
                comparison = new Date(a.createdAt || 0) - new Date(b.createdAt || 0);
                break;
            case 'dueDate':
                comparison = new Date(a.dueDate || '9999-12-31') - new Date(b.dueDate || '9999-12-31');
                break;
            case 'priority':
                comparison = (a.priority || 99) - (b.priority || 99);
                break;
            case 'title':
                comparison = (a.title || '').localeCompare(b.title || '');
                break;
        }
        
        return direction === 'desc' ? -comparison : comparison;
    });
    
    return sorted;
}

// Wire up event listeners
document.getElementById('taskSortOrder').addEventListener('change', renderTasks);
document.getElementById('taskSortDirection').addEventListener('change', renderTasks);

function renderTasks() {
    const sortBy = document.getElementById('taskSortOrder').value;
    const direction = document.getElementById('taskSortDirection').value;
    
    let filtered = filterTasks(allTasks);  // Apply existing filters
    let sorted = sortTasks(filtered, sortBy, direction);
    
    // Render sorted tasks...
}
```

### 3.4 API Enhancement (Optional)

If client-side sorting is too slow with large datasets:

```python
# app/api/tasks.py
@router.get("/tasks")
async def list_tasks(
    sort_by: str = "createdAt",  # priority, dueDate, updatedAt, createdAt, title
    sort_order: str = "desc"     # asc, desc
):
    order_column = {
        'priority': 'Priority',
        'dueDate': 'DueDate',
        'updatedAt': 'UpdatedAt',
        'createdAt': 'CreatedAt',
        'title': 'Title'
    }.get(sort_by, 'CreatedAt')
    
    query = f"""
        SELECT * FROM Tasks 
        WHERE IsDeleted = 0 
        ORDER BY {order_column} {sort_order.upper()}
    """
```

### 3.5 Test Cases

| Test ID | Description | Steps | Expected Result |
|---------|-------------|-------|-----------------|
| SORT-001 | Sort by modified date | Select "Modified Date" | Most recently edited first |
| SORT-002 | Sort direction changes | Select "Oldest First" | Order reverses |
| SORT-003 | Sort persists on filter | Sort by modified, then filter by status | Sort order maintained |
| SORT-004 | Sort handles null dates | Tasks without updatedAt | Don't crash, sort to end |

### 3.6 Playwright Tests

```python
def test_sort_by_modified_date(page):
    """Tasks can be sorted by modified date."""
    page.goto(f"{BASE_URL}/static/dashboard.html")
    
    page.select_option('#taskSortOrder', 'modified')
    page.select_option('#taskSortDirection', 'desc')
    
    # Get first two task dates
    tasks = page.locator('#taskList .item-row')
    # Verify first task was modified more recently than second
    # (Implementation depends on how dates are displayed)

def test_sort_direction_toggles(page):
    """Sort direction can be toggled."""
    page.goto(f"{BASE_URL}/static/dashboard.html")
    
    page.select_option('#taskSortOrder', 'title')
    page.select_option('#taskSortDirection', 'asc')
    
    first_task_asc = page.locator('#taskList .item-row').first.text_content()
    
    page.select_option('#taskSortDirection', 'desc')
    first_task_desc = page.locator('#taskList .item-row').first.text_content()
    
    assert first_task_asc != first_task_desc, "Sort direction should change order"
```

---

## Feature 4: Theme CRUD for Projects

### 4.1 Requirement

Enable full CRUD operations for project Themes (e.g., "Creation", "Learning", "Adventure", "Relationships", "Meta").

### 4.2 Database Changes

```sql
-- Create Themes table
CREATE TABLE Themes (
    ThemeID INT IDENTITY(1,1) PRIMARY KEY,
    ThemeName NVARCHAR(100) NOT NULL UNIQUE,
    ThemeCode NVARCHAR(20) NOT NULL UNIQUE,  -- e.g., 'A', 'B', 'C', 'D'
    Description NVARCHAR(500),
    DisplayOrder INT DEFAULT 0,
    ColorCode NVARCHAR(7),  -- Theme-level color (optional)
    IsActive BIT DEFAULT 1,
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    UpdatedAt DATETIME2 DEFAULT GETUTCDATE()
);

-- Seed initial themes
INSERT INTO Themes (ThemeCode, ThemeName, Description, DisplayOrder) VALUES
('A', 'Creation', 'Building and creating things', 1),
('B', 'Learning', 'Education and skill development', 2),
('C', 'Adventure', 'Travel and experiences', 3),
('D', 'Relationships', 'People and connections', 4),
('META', 'Meta', 'Project management and tools', 5);

-- Update Projects to reference Themes table
ALTER TABLE Projects ADD ThemeID INT NULL;

-- Foreign key (optional - allows flexibility)
-- ALTER TABLE Projects ADD CONSTRAINT FK_Projects_Themes 
--     FOREIGN KEY (ThemeID) REFERENCES Themes(ThemeID);

-- Migrate existing theme data
UPDATE p SET ThemeID = t.ThemeID
FROM Projects p
JOIN Themes t ON p.Theme LIKE '%' + t.ThemeName + '%';
```

### 4.3 API Endpoints

```python
# app/api/themes.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/themes", tags=["themes"])

class ThemeCreate(BaseModel):
    themeCode: str
    themeName: str
    description: Optional[str] = None
    displayOrder: Optional[int] = 0
    colorCode: Optional[str] = None

class ThemeUpdate(BaseModel):
    themeName: Optional[str] = None
    description: Optional[str] = None
    displayOrder: Optional[int] = None
    colorCode: Optional[str] = None
    isActive: Optional[bool] = None

@router.get("")
async def list_themes(include_inactive: bool = False):
    """List all themes."""
    query = "SELECT * FROM Themes"
    if not include_inactive:
        query += " WHERE IsActive = 1"
    query += " ORDER BY DisplayOrder"
    
    themes = execute_query(query)
    return {"themes": themes}

@router.get("/{theme_id}")
async def get_theme(theme_id: int):
    """Get single theme."""
    theme = execute_query(
        "SELECT * FROM Themes WHERE ThemeID = ?", 
        [theme_id]
    )
    if not theme:
        raise HTTPException(404, "Theme not found")
    return theme[0]

@router.post("")
async def create_theme(theme: ThemeCreate):
    """Create new theme."""
    result = execute_query("""
        INSERT INTO Themes (ThemeCode, ThemeName, Description, DisplayOrder, ColorCode)
        OUTPUT INSERTED.ThemeID
        VALUES (?, ?, ?, ?, ?)
    """, [theme.themeCode, theme.themeName, theme.description, 
          theme.displayOrder, theme.colorCode])
    
    return {"themeId": result[0]['ThemeID'], "message": "Theme created"}

@router.put("/{theme_id}")
async def update_theme(theme_id: int, theme: ThemeUpdate):
    """Update theme."""
    updates = []
    params = []
    
    if theme.themeName is not None:
        updates.append("ThemeName = ?")
        params.append(theme.themeName)
    if theme.description is not None:
        updates.append("Description = ?")
        params.append(theme.description)
    if theme.displayOrder is not None:
        updates.append("DisplayOrder = ?")
        params.append(theme.displayOrder)
    if theme.colorCode is not None:
        updates.append("ColorCode = ?")
        params.append(theme.colorCode)
    if theme.isActive is not None:
        updates.append("IsActive = ?")
        params.append(theme.isActive)
    
    updates.append("UpdatedAt = GETUTCDATE()")
    params.append(theme_id)
    
    execute_query(f"""
        UPDATE Themes SET {', '.join(updates)} WHERE ThemeID = ?
    """, params)
    
    return {"message": "Theme updated"}

@router.delete("/{theme_id}")
async def delete_theme(theme_id: int, hard_delete: bool = False):
    """Delete theme (soft by default)."""
    if hard_delete:
        # Check for projects using this theme
        projects = execute_query(
            "SELECT COUNT(*) as cnt FROM Projects WHERE ThemeID = ?",
            [theme_id]
        )
        if projects[0]['cnt'] > 0:
            raise HTTPException(400, "Cannot delete theme with associated projects")
        
        execute_query("DELETE FROM Themes WHERE ThemeID = ?", [theme_id])
    else:
        execute_query(
            "UPDATE Themes SET IsActive = 0, UpdatedAt = GETUTCDATE() WHERE ThemeID = ?",
            [theme_id]
        )
    
    return {"message": "Theme deleted"}
```

### 4.4 UI - Theme Management

```html
<!-- Add Themes section to Settings or as sub-tab under Projects -->
<div id="themesManager" class="themes-section">
    <h3>Manage Themes</h3>
    <button id="addThemeBtn" class="btn btn-primary">+ Add Theme</button>
    
    <div id="themesList" class="themes-list">
        <!-- Populated by JS -->
    </div>
</div>

<!-- Theme Edit Modal -->
<div id="themeModal" class="modal-overlay hidden">
    <div class="modal-content">
        <h2 id="themeModalTitle">Edit Theme</h2>
        <form id="themeForm">
            <div class="form-group">
                <label>Theme Code</label>
                <input type="text" id="themeCode" maxlength="20" required>
            </div>
            <div class="form-group">
                <label>Theme Name</label>
                <input type="text" id="themeName" required>
            </div>
            <div class="form-group">
                <label>Description</label>
                <textarea id="themeDescription" rows="2"></textarea>
            </div>
            <div class="form-group">
                <label>Display Order</label>
                <input type="number" id="themeOrder" value="0">
            </div>
            <div class="form-group">
                <label>Theme Color</label>
                <input type="color" id="themeColor">
            </div>
            <div class="form-actions">
                <button type="submit" class="btn btn-primary">Save</button>
                <button type="button" class="btn btn-ghost" onclick="closeThemeModal()">Cancel</button>
                <button type="button" id="deleteThemeBtn" class="btn btn-danger">Delete</button>
            </div>
        </form>
    </div>
</div>
```

### 4.5 Test Cases

| Test ID | Description | Steps | Expected Result |
|---------|-------------|-------|-----------------|
| THEME-001 | List themes | GET /api/themes | Returns theme array |
| THEME-002 | Create theme | POST new theme | Theme created with ID |
| THEME-003 | Update theme | PUT theme changes | Theme updated |
| THEME-004 | Delete theme (soft) | DELETE theme | IsActive = 0 |
| THEME-005 | Delete blocked if projects exist | DELETE theme with projects | 400 error |
| THEME-006 | Theme dropdown populated | Open project edit | Dropdown shows all themes |
| THEME-007 | Theme filter on projects | Filter by theme | Only matching projects shown |

### 4.6 Playwright Tests

```python
def test_themes_crud(page):
    """Can create, read, update, delete themes."""
    page.goto(f"{BASE_URL}/static/dashboard.html")
    
    # Navigate to themes (location TBD)
    page.click('#manageThemesBtn')
    
    # Create
    page.click('#addThemeBtn')
    page.fill('#themeCode', 'TEST')
    page.fill('#themeName', 'Test Theme')
    page.click('#themeForm button[type="submit"]')
    
    expect(page.locator('#themesList')).to_contain_text('Test Theme')
    
    # Update
    page.click('.theme-row:has-text("Test Theme") .edit-btn')
    page.fill('#themeName', 'Updated Theme')
    page.click('#themeForm button[type="submit"]')
    
    expect(page.locator('#themesList')).to_contain_text('Updated Theme')
    
    # Delete
    page.click('.theme-row:has-text("Updated Theme") .edit-btn')
    page.click('#deleteThemeBtn')
    page.click('.confirm-delete')  # Confirmation
    
    expect(page.locator('#themesList')).not_to_contain_text('Updated Theme')
```

---

## Feature 5: Offline Sync (PWA)

### 5.1 Overview

Full specification in: `METAPM_OFFLINE_SYNC_SPECIFICATION.md`

### 5.2 Summary of Components

| Component | File | Purpose |
|-----------|------|---------|
| IndexedDB Service | `static/js/offline-data.js` | Local storage + sync queue |
| Service Worker | `static/sw.js` | Cache API, background sync |
| Sync Status UI | `static/dashboard.html` | Visual indicator |

### 5.3 Implementation Phases

| Phase | Days | Deliverable |
|-------|------|-------------|
| 1 | 2-3 | IndexedDB setup + task CRUD |
| 2 | 2-3 | Sync engine (CREATE/UPDATE/DELETE) |
| 3 | 1-2 | Service worker + API caching |
| 4 | 1 | Sync status indicator UI |
| 5 | 1-2 | Testing + edge cases |

### 5.4 Key Test Cases

| Test ID | Description | Steps | Expected Result |
|---------|-------------|-------|-----------------|
| OFFLINE-001 | Create task offline | Disable network, create task | Task appears in list |
| OFFLINE-002 | Task persists refresh | Create offline, refresh page | Task still visible |
| OFFLINE-003 | Sync on reconnect | Create offline, enable network | Task syncs to server |
| OFFLINE-004 | Sync status shows | Go offline | Status shows "Offline" |
| OFFLINE-005 | Pending indicator | Create offline | Status shows "Pending (1)" |
| OFFLINE-006 | Edit offline | Edit task while offline | Changes persist |
| OFFLINE-007 | Delete offline | Delete task while offline | Task removed, delete syncs |
| OFFLINE-008 | Conflict-free (single user) | Edit same task online/offline | Last write wins |

### 5.5 Playwright Offline Tests

```python
def test_create_task_offline(page, context):
    """Can create task while offline."""
    page.goto(f"{BASE_URL}/static/dashboard.html")
    page.wait_for_load_state("networkidle")
    
    # Go offline
    context.set_offline(True)
    
    # Create task
    page.click('#addTaskBtn')
    page.fill('#taskTitle', 'Offline Test Task')
    page.click('#taskForm button[type="submit"]')
    
    # Verify appears
    expect(page.locator('#taskList')).to_contain_text('Offline Test Task')
    
    # Verify sync status
    expect(page.locator('#syncStatus')).to_contain_text('Offline')

def test_sync_on_reconnect(page, context):
    """Tasks sync when coming back online."""
    page.goto(f"{BASE_URL}/static/dashboard.html")
    context.set_offline(True)
    
    # Create offline
    page.click('#addTaskBtn')
    page.fill('#taskTitle', 'Sync Test Task')
    page.click('#taskForm button[type="submit"]')
    
    # Come back online
    context.set_offline(False)
    page.wait_for_timeout(3000)  # Wait for sync
    
    # Verify synced
    expect(page.locator('#syncStatus')).to_contain_text('Synced')
    
    # Verify on server (refresh to confirm)
    page.reload()
    expect(page.locator('#taskList')).to_contain_text('Sync Test Task')
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] All features implemented
- [ ] All Playwright tests pass
- [ ] No console errors
- [ ] Database migrations run in SSMS

### Deployment Commands
```bash
# Build and deploy
cd "G:\My Drive\Code\Python\metapm"
gcloud run deploy metapm \
    --source . \
    --region us-central1 \
    --allow-unauthenticated

# Verify deployment
curl https://metapm.rentyourcio.com/api/health
curl https://metapm.rentyourcio.com/api/themes
curl https://metapm.rentyourcio.com/api/projects/META
```

### Post-Deployment Verification
- [ ] Favicon visible in browser tab
- [ ] Project colors display correctly
- [ ] Task sort by modified works
- [ ] Theme CRUD works
- [ ] Offline mode works (airplane mode test)
- [ ] Sync status indicator shows correct state

---

## Definition of Done

Sprint is complete when:

1. **All features functional:**
   - [ ] Project color themes with Peacock-style color picker
   - [ ] Favicon displays in browser tab (no 404)
   - [ ] Task sort by modified date works
   - [ ] Theme CRUD (create, read, update, delete)
   - [ ] Offline sync with visual indicator

2. **All tests pass:**
   - [ ] Playwright test suite: 100% pass
   - [ ] No 500 errors in console
   - [ ] No unhandled JavaScript errors

3. **Documentation:**
   - [ ] API endpoints documented
   - [ ] README updated with new features

4. **Deployed:**
   - [ ] Live on Cloud Run
   - [ ] Custom domain working
   - [ ] Version number incremented

---

## Files to Create/Modify

| File | Action | Feature |
|------|--------|---------|
| `static/dashboard.html` | MODIFY | All features |
| `static/js/offline-data.js` | CREATE | Offline sync |
| `static/sw.js` | MODIFY | Offline sync |
| `static/favicon.ico` | CREATE | Favicon |
| `static/icon-192.png` | CREATE | PWA icon |
| `static/icon-512.png` | CREATE | PWA icon |
| `static/manifest.json` | MODIFY | Icons, offline |
| `app/api/themes.py` | CREATE | Theme CRUD |
| `app/api/projects.py` | MODIFY | ColorCode field |
| `app/main.py` | MODIFY | Register themes router |
| `tests/test_sprint3.py` | CREATE | All new tests |

---

## Methodology Compliance

This sprint follows project methodology:

- **LL-008:** Test plan included with test cases
- **LL-014:** Smoke test before user testing
- **LL-030:** Developer tests before handoff
- **LL-031:** Playwright for UI verification
- **LL-037:** Version number verification on deploy

**DO NOT hand off until all tests pass and features are deployed.**
