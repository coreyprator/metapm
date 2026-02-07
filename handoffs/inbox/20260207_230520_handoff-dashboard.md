# [MetaPM] 🔴 Phase 4 — Handoff Dashboard

> **From**: Claude.ai (Architect)
> **To**: Claude Code (Command Center)
> **Project**: 🔴 MetaPM
> **Task**: handoff-dashboard-ui
> **Timestamp**: 2026-02-07T21:00:00Z
> **Priority**: HIGH
> **Type**: Feature Spec

---

## Overview

Create a Handoff Dashboard UI in MetaPM that displays all handoffs across all projects. This gives Corey visibility into the "spinning plates" — what's been sent, what's pending, what needs attention.

**Goal**: Single view of all handoffs, sortable and filterable, with quick access to details.

---

## Data Sources

### Option A: Use Existing MCP API (Recommended)

The Phase 3 MCP API already has handoff storage:
- `GET /mcp/handoffs` — List all handoffs
- `GET /mcp/handoffs/{id}` — Get single handoff
- `GET /mcp/handoffs/{id}/content` — Get content (public)

**Gap**: Currently only stores handoffs created via API. Need to also index handoffs from GCS bucket.

### Option B: Index GCS Bucket Directly

Scan `gs://corey-handoff-bridge/*/outbox/*.md` and parse handoff metadata.

**Recommendation**: Hybrid approach
1. Background job scans GCS bucket periodically
2. Imports handoffs into MCP database
3. Dashboard reads from MCP API

---

## UI Specification

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ MetaPM                                           [User] [Settings]       │
├─────────────────────────────────────────────────────────────────────────┤
│ ◀ Dashboard  │  Handoff Bridge                                          │
├──────────────┴──────────────────────────────────────────────────────────┤
│                                                                         │
│  Filters: [All Projects ▼] [All Status ▼] [All Directions ▼] [🔍 Search]│
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ Project    │ Title              │ Status   │ Direction │ Date     ↓ ││
│  ├────────────┼────────────────────┼──────────┼───────────┼────────────┤│
│  │ 🔵 HarmonyLab │ auth-redirect-fix  │ ✅ Done  │ → CC      │ 2/7 7:51pm ││
│  │ 🔴 MetaPM    │ phase3-api-testing │ ✅ Done  │ → CC      │ 2/7 6:03pm ││
│  │ 🟠 ArtForge  │ priority-action    │ 🔄 Pending│ → CC      │ 2/7 7:00pm ││
│  │ 🔒 Security  │ api-key-policy     │ ✅ Done  │ → CC      │ 2/7 6:40pm ││
│  │ 🔵 HarmonyLab │ v1.4.1-auth-complete│ ✅ Done │ ← Claude.ai│ 2/7 6:30pm ││
│  │ 🔵 HarmonyLab │ v1.4.0-complete    │ ✅ Done  │ ← Claude.ai│ 2/7 5:59pm ││
│  │ ...         │                    │          │           │            ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  Showing 1-10 of 24 handoffs                    [◀ Prev] [Next ▶]       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Column Definitions

| Column | Description | Sortable | Filterable |
|--------|-------------|----------|------------|
| Project | Project name with emoji | ✅ A-Z | ✅ Dropdown |
| Title | Handoff task/title | ✅ A-Z | ✅ Search |
| Status | pending/read/done/archived | ✅ | ✅ Dropdown |
| Direction | To CC / To Claude.ai | ✅ | ✅ Dropdown |
| Date | Created timestamp | ✅ Asc/Desc | ✅ Date range |

### Default Sort

**Date Descending** (newest first)

### Hover/Click Details

On row hover or click, show detail panel:

```
┌─────────────────────────────────────────────────────┐
│ [HarmonyLab] 🔵 auth-redirect-fix                   │
├─────────────────────────────────────────────────────┤
│ From: Claude.ai (Architect)                         │
│ To: Claude Code (Command Center)                    │
│ Created: 2026-02-07T20:30:00Z                       │
│ Status: Done                                        │
│                                                     │
│ Preview:                                            │
│ ┌─────────────────────────────────────────────────┐ │
│ │ BUG FIX: Unauthenticated users can see app      │ │
│ │ content. Fix: Create login.html page, add auth  │ │
│ │ check + redirect to ALL pages...                │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ [View Full] [Mark as Done] [Archive]                │
└─────────────────────────────────────────────────────┘
```

### Mobile Responsive

On small screens:
- Stack columns vertically
- Swipe for actions
- Tap to expand details

---

## Backend Changes

### 1. GCS Sync Job

Create background job to sync GCS handoffs to database:

```python
# app/jobs/sync_gcs_handoffs.py

async def sync_gcs_handoffs():
    """Scan GCS bucket and import handoffs to database."""
    bucket = "corey-handoff-bridge"
    projects = ["ArtForge", "harmonylab", "Super-Flashcards", 
                "metapm", "Etymython", "project-methodology"]
    
    for project in projects:
        # Scan outbox
        prefix = f"{project}/outbox/"
        blobs = storage_client.list_blobs(bucket, prefix=prefix)
        
        for blob in blobs:
            if blob.name.endswith('.md'):
                # Parse handoff metadata from content
                content = blob.download_as_text()
                metadata = parse_handoff_metadata(content)
                
                # Upsert to database (idempotent)
                await upsert_handoff(
                    source="gcs",
                    gcs_path=f"gs://{bucket}/{blob.name}",
                    project=metadata.project,
                    task=metadata.task,
                    direction=metadata.direction,
                    content=content,
                    created_at=blob.time_created
                )
```

### 2. Parse Handoff Metadata

Extract from handoff header:

```python
def parse_handoff_metadata(content: str) -> dict:
    """Parse handoff header to extract metadata."""
    # Look for standard header format:
    # > **From**: Claude Code (Command Center)
    # > **To**: Claude.ai (Architect)
    # > **Project**: 🔵 HarmonyLab
    # > **Task**: auth-redirect-fix
    
    patterns = {
        'from': r'\*\*From\*\*:\s*(.+)',
        'to': r'\*\*To\*\*:\s*(.+)',
        'project': r'\*\*Project\*\*:\s*(.+)',
        'task': r'\*\*Task\*\*:\s*(.+)',
        'timestamp': r'\*\*Timestamp\*\*:\s*(.+)',
    }
    # ... extract and return
```

### 3. Database Schema Update

Add fields to `mcp_handoffs` table:

```sql
ALTER TABLE mcp_handoffs ADD COLUMN source NVARCHAR(20) DEFAULT 'api';
ALTER TABLE mcp_handoffs ADD COLUMN gcs_path NVARCHAR(500);
ALTER TABLE mcp_handoffs ADD COLUMN from_entity NVARCHAR(100);
ALTER TABLE mcp_handoffs ADD COLUMN to_entity NVARCHAR(100);
```

### 4. New API Endpoints

```python
# Dashboard-specific endpoints
GET /mcp/handoffs/dashboard
    ?project=HarmonyLab
    &status=pending
    &direction=cc_to_ai
    &sort=created_at
    &order=desc
    &page=1
    &limit=10

GET /mcp/handoffs/stats
    # Returns: { total: 24, by_project: {...}, by_status: {...} }

POST /mcp/handoffs/sync
    # Trigger manual GCS sync
```

---

## Frontend Implementation

### 1. New Page: `frontend/handoffs.html`

Dashboard page with:
- Filter controls
- Sortable data table
- Pagination
- Detail panel (side drawer or modal)

### 2. JavaScript: `frontend/js/handoffs.js`

```javascript
class HandoffDashboard {
    constructor() {
        this.filters = { project: null, status: null, direction: null };
        this.sort = { field: 'created_at', order: 'desc' };
        this.page = 1;
        this.limit = 10;
    }
    
    async loadHandoffs() {
        const params = new URLSearchParams({
            ...this.filters,
            sort: this.sort.field,
            order: this.sort.order,
            page: this.page,
            limit: this.limit
        });
        const response = await fetch(`/mcp/handoffs/dashboard?${params}`);
        return response.json();
    }
    
    renderTable(handoffs) { /* ... */ }
    renderFilters() { /* ... */ }
    renderPagination(total) { /* ... */ }
    showDetail(handoffId) { /* ... */ }
}
```

### 3. Styles: `frontend/css/handoffs.css`

- Table styles with hover states
- Filter bar styling
- Detail panel/drawer
- Responsive breakpoints

---

## Project Emoji Mapping

```javascript
const PROJECT_EMOJI = {
    'ArtForge': '🟠',
    'HarmonyLab': '🔵',
    'harmonylab': '🔵',
    'Super-Flashcards': '🟡',
    'MetaPM': '🔴',
    'metapm': '🔴',
    'Etymython': '🟣',
    'project-methodology': '🟢',
    'Security': '🔒'
};
```

---

## Direction Mapping

| GCS Path | Direction |
|----------|-----------|
| `*/outbox/*` from CC | cc_to_ai (← Claude.ai) |
| `*/outbox/*` from Claude.ai | ai_to_cc (→ CC) |

Parse from `**From**` header in handoff content.

---

## Navigation Integration

Add to MetaPM nav:

```html
<nav>
    <a href="/">Dashboard</a>
    <a href="/projects.html">Projects</a>
    <a href="/handoffs.html" class="active">Handoff Bridge</a>  <!-- NEW -->
    <a href="/settings.html">Settings</a>
</nav>
```

---

## Testing Checklist

| Test | Expected |
|------|----------|
| Page loads with handoffs | Table shows data |
| Sort by date desc (default) | Newest first |
| Sort by date asc | Oldest first |
| Sort by project | Alphabetical |
| Filter by project | Only that project shown |
| Filter by status | Only that status shown |
| Filter by direction | Only that direction shown |
| Click row | Detail panel opens |
| Detail shows preview | First ~200 chars of content |
| View Full link | Opens full handoff content |
| Pagination works | Next/prev navigate pages |
| Mobile responsive | Stacked layout on small screens |
| GCS sync imports handoffs | New handoffs appear after sync |

---

## Version

Bump to **v1.8.0** after implementation.

---

## Files to Create

| File | Description |
|------|-------------|
| `frontend/handoffs.html` | Dashboard page |
| `frontend/js/handoffs.js` | Dashboard logic |
| `frontend/css/handoffs.css` | Dashboard styles |
| `app/jobs/sync_gcs_handoffs.py` | GCS sync background job |

## Files to Modify

| File | Change |
|------|--------|
| `app/routers/mcp.py` | Add dashboard endpoints |
| `app/migrations.py` | Add new columns |
| `frontend/index.html` | Add nav link |
| `main.py` | Version bump, register sync job |

---

## Definition of Done

- [ ] GCS sync job imports all existing handoffs
- [ ] Dashboard page displays handoffs in table
- [ ] All columns sortable (click header)
- [ ] All filters work (project, status, direction)
- [ ] Default sort is date descending
- [ ] Hover/click shows detail panel
- [ ] Detail shows preview + View Full link
- [ ] Pagination works
- [ ] Mobile responsive
- [ ] Version bumped to 1.8.0
- [ ] Deployed and tested
- [ ] Handoff sent with completion report

---

*Feature spec from Claude.ai (Architect)*
*Gives Corey visibility into all handoffs across projects*
