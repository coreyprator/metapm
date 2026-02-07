# [MetaPM] 🔴 Phase 3: Native MCP Endpoints Specification

**Version**: Sprint 5 Target  
**Status**: APPROVED by CC — Awaiting Corey's Review  
**Date**: 2026-02-07  

---

## Executive Summary

Add native MCP (Model Context Protocol) endpoints to MetaPM so Claude Code can interact directly with the task management system instead of using file-based handoffs.

### Current State (Phase 2)
- CC and Claude.ai communicate via GCS bucket + Python scripts
- Manual polling for new handoffs
- No way for Claude.ai to create tasks/action items in MetaPM

### Phase 3 Target
- Native REST API endpoints following MCP patterns
- Claude Code registers MetaPM as an MCP server
- Direct API calls replace file polling
- Claude.ai can create action items via REST API

---

## Database Schema

### New Table: `mcp_handoffs`

```sql
CREATE TABLE mcp_handoffs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project VARCHAR(100) NOT NULL,
    task VARCHAR(200) NOT NULL,
    direction VARCHAR(20) NOT NULL CHECK (direction IN ('cc_to_ai', 'ai_to_cc')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'read', 'processed', 'archived')),
    content TEXT NOT NULL,
    metadata JSONB,
    response_to UUID REFERENCES mcp_handoffs(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_handoffs_project ON mcp_handoffs(project);
CREATE INDEX idx_handoffs_status ON mcp_handoffs(status);
CREATE INDEX idx_handoffs_direction ON mcp_handoffs(direction);
CREATE INDEX idx_handoffs_created ON mcp_handoffs(created_at DESC);
```

### New Table: `mcp_tasks`

```sql
CREATE TABLE mcp_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'blocked', 'done', 'cancelled')),
    assigned_to VARCHAR(50) CHECK (assigned_to IN ('cc', 'corey', 'claude_ai')),
    related_handoff_id UUID REFERENCES mcp_handoffs(id),
    tags TEXT[],
    notes TEXT,
    due_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_tasks_project ON mcp_tasks(project);
CREATE INDEX idx_tasks_status ON mcp_tasks(status);
CREATE INDEX idx_tasks_assigned ON mcp_tasks(assigned_to);
CREATE INDEX idx_tasks_priority ON mcp_tasks(priority);
```

---

## API Endpoints

### Authentication

**Method**: API Key in header  
**Header**: `X-API-Key: {key}` OR `Authorization: Bearer {key}`  
**Storage**: GCP Secret Manager as `metapm-mcp-api-key`

**Public endpoints** (no auth required):
- `GET /mcp/handoffs/{id}/content` — For Claude.ai's web_fetch

### Handoff Endpoints

#### Create Handoff
```
POST /mcp/handoffs
Authorization: Bearer {api_key}
Content-Type: application/json

{
    "project": "ArtForge",
    "task": "sprint3-status-report",
    "direction": "cc_to_ai",
    "content": "# Status Report\n\n...",
    "metadata": {
        "version": "2.2.0",
        "priority": "high"
    },
    "response_to": "uuid-of-previous-handoff"  // optional
}

Response: 201 Created
{
    "id": "uuid",
    "project": "ArtForge",
    "task": "sprint3-status-report",
    "direction": "cc_to_ai",
    "status": "pending",
    "public_url": "https://metapm.rentyourcio.com/mcp/handoffs/{id}/content",
    "created_at": "2026-02-07T15:00:00Z"
}
```

#### List Handoffs
```
GET /mcp/handoffs?project=ArtForge&status=pending&direction=ai_to_cc&limit=20
Authorization: Bearer {api_key}

Response: 200 OK
{
    "handoffs": [...],
    "total": 5,
    "has_more": false
}
```

#### Get Handoff (Authenticated)
```
GET /mcp/handoffs/{id}
Authorization: Bearer {api_key}

Response: 200 OK
{
    "id": "uuid",
    "project": "ArtForge",
    "task": "sprint3-status-report",
    "direction": "cc_to_ai",
    "status": "pending",
    "content": "# Status Report\n\n...",
    "metadata": {...},
    "response_to": null,
    "created_at": "...",
    "updated_at": "..."
}
```

#### Get Handoff Content (PUBLIC — No Auth)
```
GET /mcp/handoffs/{id}/content

Response: 200 OK
Content-Type: text/markdown

# Status Report

...raw markdown content...
```

This endpoint is PUBLIC so Claude.ai can use `web_fetch` to read handoffs without authentication.

#### Update Handoff Status
```
PATCH /mcp/handoffs/{id}
Authorization: Bearer {api_key}
Content-Type: application/json

{
    "status": "processed"
}

Response: 200 OK
```

---

### Task Endpoints

#### Create Task
```
POST /mcp/tasks
Authorization: Bearer {api_key}
Content-Type: application/json

{
    "project": "ArtForge",
    "title": "Fix BUG-010: Large image resize",
    "description": "Images >1024px cause 400 error from Stability AI",
    "priority": "critical",
    "assigned_to": "cc",
    "tags": ["bug", "p1", "blocker"],
    "related_handoff_id": "uuid"  // optional
}

Response: 201 Created
{
    "id": "uuid",
    "project": "ArtForge",
    "title": "Fix BUG-010: Large image resize",
    "status": "pending",
    "priority": "critical",
    "created_at": "..."
}
```

#### List Tasks
```
GET /mcp/tasks?project=ArtForge&status=pending&assigned_to=cc&limit=50
Authorization: Bearer {api_key}

Response: 200 OK
{
    "tasks": [...],
    "total": 12,
    "has_more": false
}
```

#### Get Task
```
GET /mcp/tasks/{id}
Authorization: Bearer {api_key}

Response: 200 OK
{...full task object...}
```

#### Update Task
```
PATCH /mcp/tasks/{id}
Authorization: Bearer {api_key}
Content-Type: application/json

{
    "status": "in_progress",
    "notes": "Started investigating resize function"
}

Response: 200 OK
```

#### Delete Task
```
DELETE /mcp/tasks/{id}
Authorization: Bearer {api_key}

Response: 204 No Content
```

---

### Log Endpoint

```
GET /mcp/log?project=ArtForge&limit=50
Authorization: Bearer {api_key}

Response: 200 OK
{
    "entries": [
        {
            "timestamp": "2026-02-07T15:00:00Z",
            "type": "handoff",
            "project": "ArtForge",
            "summary": "CC → AI: sprint3-status-report",
            "id": "uuid"
        },
        {
            "timestamp": "2026-02-07T14:30:00Z",
            "type": "task",
            "project": "ArtForge",
            "summary": "Task created: Fix BUG-010",
            "id": "uuid"
        }
    ]
}
```

---

## Claude Code MCP Integration

After Phase 3 is deployed, CC registers MetaPM as an MCP server:

```bash
claude mcp add --transport http metapm-handoffs https://metapm.rentyourcio.com/mcp
```

Then CC can use native MCP tools:

```python
# List pending handoffs from Claude.ai
handoffs = mcp.metapm_handoffs.list(
    project="ArtForge",
    status="pending",
    direction="ai_to_cc"
)

# Create a task
task = mcp.metapm_tasks.create(
    project="ArtForge",
    title="Fix BUG-010: Large image resize",
    priority="critical",
    assigned_to="cc"
)

# Update task status
mcp.metapm_tasks.update(
    id=task.id,
    status="done",
    notes="Fixed in commit abc123"
)

# Create handoff response
mcp.metapm_handoffs.create(
    project="ArtForge",
    task="sprint3-status-complete",
    direction="cc_to_ai",
    content="# Sprint 3 Complete\n\n...",
    response_to=original_handoff.id
)
```

---

## GCS Sync (Backup)

**Decision**: Keep GCS sync as redundant backup.

After each database write:
1. Write to PostgreSQL (primary)
2. Async upload to GCS bucket (backup)
3. Log result

This provides:
- Redundancy if DB is down
- Existing Phase 2 scripts work as fallback
- Raw files for manual inspection

---

## Implementation Estimate

| Component | Est. Hours |
|-----------|------------|
| Database migration | 1-2 |
| Pydantic schemas | 1-2 |
| Handoff endpoints | 3-4 |
| Task endpoints | 3-4 |
| Log endpoint | 1 |
| Auth middleware | 1-2 |
| GCS sync integration | 1 |
| Testing | 2-3 |
| Documentation | 1 |
| **Total** | **14-20 hours** |

---

## CC's Review Comments (Approved)

From CC's review handoff:

| Question | CC's Answer |
|----------|-------------|
| Concerns about new tables? | ✅ None — schema is well-designed |
| API Key vs Service Account? | ✅ **API Key** recommended |
| Keep GCS sync? | ✅ **Yes** — for redundancy |

**Additional suggestions from CC:**
- Support both `Authorization: Bearer` AND `X-API-Key` headers
- Add `/mcp/health` endpoint for monitoring
- Consider `expires_at` field for auto-archiving old handoffs

---

## Acceptance Criteria

### Phase 3 Complete When:

- [ ] Database tables created (`mcp_handoffs`, `mcp_tasks`)
- [ ] All endpoints implemented and tested
- [ ] API key stored in Secret Manager
- [ ] Auth middleware working
- [ ] Public content endpoint working (for Claude.ai)
- [ ] GCS backup sync working
- [ ] Claude Code can register as MCP server
- [ ] End-to-end test: CC creates handoff → Claude.ai reads it
- [ ] End-to-end test: Claude.ai creates task → CC sees it

---

## Timeline

**Sprint 5** (after current priorities):
- ArtForge Sprint 3 completion
- HarmonyLab v1.3.1 fixes
- Then Phase 3 MCP implementation

---

## Questions for Corey

1. **Priority**: Should Phase 3 start after current work, or is there urgency?
2. **Scope**: Any features to add/remove from this spec?
3. **Task schema**: Are the fields sufficient for your tracking needs?
4. **Projects list**: Should we have a projects table, or keep project as free-text?

---

*Specification prepared by Claude.ai (Architect)*  
*Reviewed and approved by Claude Code (Command Center)*  
*Awaiting approval from Corey (Project Lead)*
