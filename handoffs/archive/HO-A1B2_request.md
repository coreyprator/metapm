# [MetaPM] 🔴 / [project-methodology] 🟢 — PromptForge V3 Implementation

> **ID**: HO-A1B2
> **Timestamp**: 2026-02-10-09-00-00
> **From**: Claude.ai (Architect)
> **To**: Claude Code (Command Center)
> **Project**: 🔴 MetaPM + 🟢 project-methodology
> **Task**: Lifecycle Tracking System Implementation
> **Sprint**: Current

---

## Overview

Implement handoff lifecycle tracking system with ID linking, side-by-side comparison, and enhanced roadmap integration.

---

## Phase 1: Templates (CC CLAUDE.md Updates)

### 1.1 Update All Project CLAUDE.md Files

Add this section to every project's CLAUDE.md:

```markdown
## Handoff Lifecycle Protocol

### Receiving Handoffs
1. Note the ID (HO-XXXX) from the handoff header
2. Move handoff from inbox to project archive: `handoffs/archive/`
3. Delete from inbox (garbage collect)

### Completion Response Format

Every completion MUST include this exact format:

| Field | Value |
|-------|-------|
| ID | HO-XXXX (from original request) |
| Project | [Icon] [Name] |
| Task | [Brief description] |
| Status | COMPLETE / PARTIAL / BLOCKED |
| Commit | [hash] |
| Handoff | [Full GCS URL] |

### Summary Section
After the table, include:
- Brief description of what was done
- Files changed (list)
- Inbox cleanup confirmation

### Git Commit Format
Include ID in commit message:
```
feat: [description] (HO-XXXX)
fix: [description] (HO-XXXX)
```

### Garbage Collection Checklist
After processing handoff:
□ Deleted from inbox: handoffs/inbox/*.md
□ Archived to: handoffs/archive/
□ Reminded Corey about Downloads folder cleanup
```

### Projects to Update
- MetaPM
- Super Flashcards
- CashForecast
- HarmonyLab
- ArtForge
- Etymython
- project-methodology

---

## Phase 2: MetaPM Database Schema

### 2.1 New Table: handoff_requests

Tracks the full lifecycle of each handoff.

```sql
CREATE TABLE handoff_requests (
    id VARCHAR(10) PRIMARY KEY,              -- HO-XXXX
    created_at DATETIME NOT NULL,
    project VARCHAR(50) NOT NULL,            -- MetaPM, Super Flashcards, etc.
    roadmap_id VARCHAR(20),                  -- MP-001, HL-002, etc.
    request_type VARCHAR(20) NOT NULL,       -- Requirement, Bug, UAT, Enhancement, Hotfix
    title VARCHAR(200) NOT NULL,
    description TEXT,
    spec_handoff_url VARCHAR(500),           -- GCS URL of original spec
    status VARCHAR(20) NOT NULL DEFAULT 'SPEC',  -- SPEC, PENDING, DELIVERED, UAT, PASSED, FAILED
    updated_at DATETIME
);

-- Status values:
-- SPEC: CAI generated specs, awaiting CC
-- PENDING: CC has received, working
-- DELIVERED: CC completed, awaiting UAT
-- UAT: UAT in progress
-- PASSED: UAT passed, closed
-- FAILED: UAT failed, needs fixes (loops back to PENDING)
```

### 2.2 New Table: handoff_completions

Tracks CC completion responses.

```sql
CREATE TABLE handoff_completions (
    id INT IDENTITY(1,1) PRIMARY KEY,
    handoff_id VARCHAR(10) NOT NULL,         -- FK to handoff_requests
    completed_at DATETIME NOT NULL,
    status VARCHAR(20) NOT NULL,             -- COMPLETE, PARTIAL, BLOCKED
    commit_hash VARCHAR(40),
    completion_handoff_url VARCHAR(500),     -- GCS URL of completion handoff
    notes TEXT,
    FOREIGN KEY (handoff_id) REFERENCES handoff_requests(id)
);
```

### 2.3 New Table: roadmap_handoffs (Junction)

Links roadmap items to handoffs.

```sql
CREATE TABLE roadmap_handoffs (
    roadmap_id VARCHAR(20) NOT NULL,         -- MP-001, HL-002
    handoff_id VARCHAR(10) NOT NULL,         -- HO-XXXX
    relationship VARCHAR(20) NOT NULL,       -- IMPLEMENTS, FIXES, TESTS, ENHANCES
    created_at DATETIME DEFAULT GETDATE(),
    PRIMARY KEY (roadmap_id, handoff_id),
    FOREIGN KEY (handoff_id) REFERENCES handoff_requests(id)
);
```

### 2.4 API Endpoints

```python
# POST /api/handoffs
# Create new handoff request
{
    "id": "HO-A1B2",
    "project": "MetaPM",
    "roadmap_id": "MP-001",  # optional
    "request_type": "Requirement",
    "title": "Add lifecycle tracking",
    "description": "...",
    "spec_handoff_url": "https://storage.googleapis.com/..."
}

# PUT /api/handoffs/{id}/status
# Update status
{
    "status": "DELIVERED",
    "completion_handoff_url": "https://storage.googleapis.com/..."
}

# POST /api/handoffs/{id}/complete
# Record completion
{
    "status": "COMPLETE",
    "commit_hash": "abc1234",
    "completion_handoff_url": "https://...",
    "notes": "Deployed v2.0.5"
}

# GET /api/handoffs/{id}
# Get full handoff details with completions

# GET /api/roadmap/{roadmap_id}/handoffs
# Get all handoffs linked to a roadmap item
```

---

## Phase 3: Side-by-Side Comparison UI

### 3.1 New Page: /compare/{handoff_id}

URL: `https://metapm.rentyourcio.com/compare/HO-A1B2`

```html
<div class="compare-container">
    <div class="compare-header">
        <h1>Handoff Comparison: HO-A1B2</h1>
        <span class="status-badge">DELIVERED</span>
    </div>
    
    <div class="compare-panels">
        <!-- Left Panel: Original Request -->
        <div class="panel request-panel">
            <h2>📤 Original Request</h2>
            <div class="panel-meta">
                <p><strong>ID:</strong> HO-A1B2</p>
                <p><strong>Created:</strong> 2026-02-10 09:00</p>
                <p><strong>Project:</strong> 🔴 MetaPM</p>
                <p><strong>Roadmap:</strong> MP-001</p>
                <p><strong>Type:</strong> Requirement</p>
            </div>
            <div class="panel-content">
                <!-- Rendered markdown from spec_handoff_url -->
                <iframe src="/api/handoffs/HO-A1B2/spec/content"></iframe>
            </div>
            <a href="..." class="view-full-btn">View Full Spec</a>
        </div>
        
        <!-- Right Panel: CC Response -->
        <div class="panel response-panel">
            <h2>📥 CC Response</h2>
            <div class="panel-meta">
                <p><strong>Status:</strong> COMPLETE</p>
                <p><strong>Completed:</strong> 2026-02-10 11:30</p>
                <p><strong>Commit:</strong> abc1234</p>
            </div>
            <div class="panel-content">
                <!-- Rendered markdown from completion_handoff_url -->
                <iframe src="/api/handoffs/HO-A1B2/completion/content"></iframe>
            </div>
            <a href="..." class="view-full-btn">View Full Handoff</a>
        </div>
    </div>
    
    <div class="compare-actions">
        <button class="btn-approve" onclick="approveHandoff('HO-A1B2')">
            ✓ Approve for UAT
        </button>
        <button class="btn-reject" onclick="rejectHandoff('HO-A1B2')">
            ✗ Request Changes
        </button>
    </div>
</div>
```

### 3.2 Comparison Styling

```css
.compare-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}

.compare-panels {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}

.panel {
    background: #1e1e32;
    border-radius: 12px;
    padding: 20px;
    border: 2px solid #3a3a52;
}

.request-panel {
    border-color: #3b82f6;  /* Blue for request */
}

.response-panel {
    border-color: #22c55e;  /* Green for response */
}

.panel-content {
    max-height: 500px;
    overflow-y: auto;
    background: #0f172a;
    border-radius: 8px;
    padding: 16px;
    margin: 16px 0;
}
```

---

## Phase 3 (continued): Roadmap View Enhancement

### 3.3 Update roadmap.html

Add handoff history to each roadmap item:

```html
<div class="roadmap-item" data-id="MP-001">
    <div class="item-header">
        <span class="item-id">MP-001</span>
        <span class="item-title">Fix UAT Submit 500 Error</span>
        <span class="status-badge done">Done</span>
    </div>
    
    <div class="item-details">
        <p>Version: 2.0.4</p>
        <p>Assigned: CC</p>
    </div>
    
    <!-- NEW: Handoff History Section -->
    <div class="handoff-history">
        <h4>📋 Handoff History</h4>
        <ul class="handoff-list">
            <li>
                <span class="handoff-id">HO-8B2F</span>
                <span class="handoff-status spec">SPEC</span>
                <span class="handoff-date">2026-02-09 14:30</span>
                <span class="handoff-direction">→ CC</span>
                <a href="/compare/HO-8B2F">View</a>
            </li>
            <li>
                <span class="handoff-id">HO-8B2F</span>
                <span class="handoff-status complete">COMPLETE</span>
                <span class="handoff-date">2026-02-09 18:51</span>
                <span class="handoff-direction">← CC</span>
                <a href="/compare/HO-8B2F">View</a>
            </li>
            <li>
                <span class="handoff-id">HO-8B2F</span>
                <span class="handoff-status passed">UAT PASSED</span>
                <span class="handoff-date">2026-02-09 19:07</span>
                <a href="/uat/HO-8B2F">View UAT</a>
            </li>
        </ul>
    </div>
</div>
```

### 3.4 API for Roadmap Handoffs

```python
@app.get("/api/roadmap/{roadmap_id}/handoffs")
async def get_roadmap_handoffs(roadmap_id: str):
    """Get all handoffs linked to a roadmap item."""
    query = """
        SELECT h.*, c.completed_at, c.status as completion_status, c.commit_hash
        FROM handoff_requests h
        LEFT JOIN handoff_completions c ON h.id = c.handoff_id
        JOIN roadmap_handoffs rh ON h.id = rh.handoff_id
        WHERE rh.roadmap_id = ?
        ORDER BY h.created_at DESC
    """
    return db.execute(query, roadmap_id)
```

---

## Phase 4: Future Features (Deferred)

### Removed from Roadmap
- ~~Change Journal (4 hrs)~~ — Covered by database tracking

### Remaining on Roadmap
| Task | Effort | Priority |
|------|--------|----------|
| Compliance Gate | 4 hr | Medium |
| Scenario Registry | 4 hr | Low |
| GCS Polling | 8 hr | Low |
| Integrated Forms UI | 8 hr | Medium |

---

## File Structure

```
MetaPM/
├── app/
│   ├── routes/
│   │   ├── handoffs.py      # New: handoff CRUD endpoints
│   │   └── roadmap.py       # Update: add handoff history
│   └── models.py            # Update: add new tables
├── static/
│   ├── compare.html         # New: side-by-side comparison
│   ├── roadmap.html         # Update: add handoff history
│   └── css/
│       └── compare.css      # New: comparison styling
└── migrations/
    └── 003_handoff_tracking.sql  # New: schema changes
```

---

## Deployment

```bash
# Run migrations
python -m app.migrations.003_handoff_tracking

# Deploy
gcloud run deploy metapm-v2 --source . --region us-central1

# Verify
curl https://metapm.rentyourcio.com/health
# Should show new version
```

---

## Definition of Done

### Phase 1: Templates
- [ ] All project CLAUDE.md files updated with handoff protocol
- [ ] CC uses new completion format

### Phase 2: Database
- [ ] handoff_requests table created
- [ ] handoff_completions table created
- [ ] roadmap_handoffs junction table created
- [ ] API endpoints working

### Phase 3: UI
- [ ] /compare/{id} page working
- [ ] Side-by-side view shows spec vs completion
- [ ] Roadmap items show handoff history
- [ ] Approve/Reject buttons functional

---

## Testing

### Test Case 1: Create Handoff
```bash
curl -X POST https://metapm.rentyourcio.com/api/handoffs \
  -H "Content-Type: application/json" \
  -d '{"id":"HO-TEST","project":"MetaPM","request_type":"Test","title":"Test Handoff"}'
```

### Test Case 2: Link to Roadmap
```bash
curl -X POST https://metapm.rentyourcio.com/api/roadmap/MP-001/handoffs \
  -H "Content-Type: application/json" \
  -d '{"handoff_id":"HO-TEST","relationship":"IMPLEMENTS"}'
```

### Test Case 3: View Comparison
Navigate to: `https://metapm.rentyourcio.com/compare/HO-TEST`

---

*ID: HO-A1B2*
*Status: SPEC*
*Awaiting: CC Implementation*
