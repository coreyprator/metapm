# [MetaPM] 🔴 Sprint 5 — Phase 3 Handoff Bridge MCP Endpoints

> **From**: Claude.ai (Architect)
> **To**: Claude Code (Command Center)
> **Project**: 🔴 MetaPM
> **Task**: sprint5-phase3-mcp-spec
> **Timestamp**: 2026-02-07T14:00:00Z
> **Type**: Sprint Specification

---

## Overview

Phase 3 of the Handoff Bridge adds native MCP (Model Context Protocol) endpoints to MetaPM. This enables Claude Code to interact with handoffs programmatically via MCP tools instead of polling GCS buckets.

**Goal**: Zero-copy-paste handoffs with native tool integration

---

## Background: Current State (Phase 2)

```
Current Flow (Phase 2):
┌─────────────┐     GCS Bucket      ┌─────────────┐
│ Claude Code │ ←→ corey-handoff-bridge ←→ │  Claude.ai  │
└─────────────┘     (scripts)       └─────────────┘
```

**Limitations**:
- Requires Python scripts to interact with GCS
- No native tool integration
- Manual polling for new handoffs
- No CRUD for tasks/action items from Claude.ai

---

## Phase 3 Target Architecture

```
Phase 3 Flow:
┌─────────────┐     MCP Protocol     ┌─────────────┐
│ Claude Code │ ←────────────────────→│   MetaPM    │
└─────────────┘   /mcp/* endpoints   │   (API)     │
                                     └─────────────┘
                                           ↑
                                           │ REST API
                                           ↓
                                     ┌─────────────┐
                                     │  Claude.ai  │
                                     │ (web_fetch) │
                                     └─────────────┘
```

---

## MCP Endpoints Specification

### 1. Handoff Endpoints (`/mcp/handoffs/*`)

#### 1.1 Create Handoff
```
POST /mcp/handoffs
Content-Type: application/json
Authorization: Bearer {api_key}

{
  "project": "ArtForge",
  "task": "sprint3-status",
  "direction": "cc_to_ai" | "ai_to_cc",
  "content": "# Handoff Content\n\n...",
  "metadata": {
    "priority": "high" | "medium" | "low",
    "response_to": "uuid-of-previous-handoff" | null
  }
}

Response 201:
{
  "id": "uuid",
  "project": "ArtForge",
  "task": "sprint3-status",
  "direction": "cc_to_ai",
  "status": "pending",
  "created_at": "2026-02-07T14:00:00Z",
  "public_url": "https://metapm.rentyourcio.com/mcp/handoffs/uuid/content"
}
```

#### 1.2 List Pending Handoffs
```
GET /mcp/handoffs?status=pending&direction=ai_to_cc&project=ArtForge
Authorization: Bearer {api_key}

Response 200:
{
  "handoffs": [
    {
      "id": "uuid",
      "project": "ArtForge",
      "task": "sprint3-response",
      "direction": "ai_to_cc",
      "status": "pending",
      "created_at": "2026-02-07T14:30:00Z",
      "summary": "First 100 chars of content..."
    }
  ],
  "count": 1
}
```

#### 1.3 Get Handoff Content
```
GET /mcp/handoffs/{id}
Authorization: Bearer {api_key}

Response 200:
{
  "id": "uuid",
  "project": "ArtForge",
  "task": "sprint3-response",
  "direction": "ai_to_cc",
  "status": "pending",
  "content": "# Full Markdown Content\n\n...",
  "created_at": "2026-02-07T14:30:00Z",
  "metadata": {...}
}
```

#### 1.4 Get Handoff Content (Public - for Claude.ai web_fetch)
```
GET /mcp/handoffs/{id}/content
(No auth required - returns raw markdown)

Response 200:
Content-Type: text/markdown

# Handoff Content
...
```

#### 1.5 Update Handoff Status
```
PATCH /mcp/handoffs/{id}
Authorization: Bearer {api_key}

{
  "status": "acknowledged" | "processed" | "archived"
}

Response 200:
{
  "id": "uuid",
  "status": "processed",
  "updated_at": "2026-02-07T15:00:00Z"
}
```

---

### 2. Task/Action Item Endpoints (`/mcp/tasks/*`)

This enables Claude.ai to create action items that CC can execute.

#### 2.1 Create Task
```
POST /mcp/tasks
Content-Type: application/json
Authorization: Bearer {api_key}

{
  "project": "ArtForge",
  "title": "Implement MP4 video export",
  "description": "Add moviepy to requirements, create video_export_service.py...",
  "priority": "high" | "medium" | "low",
  "assigned_to": "cc" | "corey" | "claude_ai",
  "related_handoff_id": "uuid" | null,
  "tags": ["sprint3", "video", "export"]
}

Response 201:
{
  "id": "uuid",
  "project": "ArtForge",
  "title": "Implement MP4 video export",
  "status": "pending",
  "created_at": "2026-02-07T14:00:00Z"
}
```

#### 2.2 List Tasks
```
GET /mcp/tasks?project=ArtForge&status=pending&assigned_to=cc
Authorization: Bearer {api_key}

Response 200:
{
  "tasks": [...],
  "count": 5
}
```

#### 2.3 Get Task
```
GET /mcp/tasks/{id}
Authorization: Bearer {api_key}

Response 200:
{
  "id": "uuid",
  "project": "ArtForge",
  "title": "Implement MP4 video export",
  "description": "...",
  "status": "pending",
  "priority": "high",
  "assigned_to": "cc",
  "created_at": "...",
  "updated_at": "..."
}
```

#### 2.4 Update Task
```
PATCH /mcp/tasks/{id}
Authorization: Bearer {api_key}

{
  "status": "in_progress" | "completed" | "blocked",
  "notes": "Started implementation, moviepy added to requirements"
}

Response 200:
{
  "id": "uuid",
  "status": "in_progress",
  "updated_at": "..."
}
```

#### 2.5 Delete Task
```
DELETE /mcp/tasks/{id}
Authorization: Bearer {api_key}

Response 204 (No Content)
```

---

### 3. Log Endpoint (`/mcp/log`)

#### 3.1 Get Conversation Log
```
GET /mcp/log?project=ArtForge&limit=50
Authorization: Bearer {api_key}

Response 200:
{
  "entries": [
    {
      "timestamp": "2026-02-07T14:00:00Z",
      "project": "ArtForge",
      "type": "handoff" | "task",
      "action": "created" | "updated" | "completed",
      "summary": "CC sent sprint3-status-report",
      "id": "uuid"
    }
  ],
  "count": 50
}
```

---

## Database Schema

### Table: `mcp_handoffs`

```sql
CREATE TABLE mcp_handoffs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project VARCHAR(100) NOT NULL,
    task VARCHAR(200) NOT NULL,
    direction VARCHAR(20) NOT NULL CHECK (direction IN ('cc_to_ai', 'ai_to_cc')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'acknowledged', 'processed', 'archived')),
    content TEXT NOT NULL,
    metadata JSONB,
    response_to UUID REFERENCES mcp_handoffs(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    INDEX idx_handoffs_project (project),
    INDEX idx_handoffs_status (status),
    INDEX idx_handoffs_direction (direction)
);
```

### Table: `mcp_tasks`

```sql
CREATE TABLE mcp_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'blocked', 'cancelled')),
    assigned_to VARCHAR(50) CHECK (assigned_to IN ('cc', 'corey', 'claude_ai')),
    related_handoff_id UUID REFERENCES mcp_handoffs(id),
    tags TEXT[],
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    INDEX idx_tasks_project (project),
    INDEX idx_tasks_status (status),
    INDEX idx_tasks_assigned (assigned_to)
);
```

---

## Authentication

### Option A: API Key (Recommended for Phase 3)

```
X-API-Key: {stored-in-secret-manager}
```

- Simple, works for both CC and Claude.ai
- Store in GCP Secret Manager as `metapm-mcp-api-key`
- Validate in middleware

### Option B: Service Account (Future)

For native MCP protocol support, may need service account JWT.

---

## Claude Code MCP Integration

Once deployed, CC can register MetaPM as an MCP server:

```bash
claude mcp add --transport http metapm-handoffs https://metapm.rentyourcio.com/mcp
```

Then CC can use native MCP tools:

```python
# In Claude Code
result = mcp.metapm_handoffs.list_pending(project="ArtForge", direction="ai_to_cc")
handoff = mcp.metapm_handoffs.get(id=result[0].id)
mcp.metapm_handoffs.update(id=handoff.id, status="processed")

# Create task
mcp.metapm_tasks.create(
    project="ArtForge",
    title="Fix BUG-010",
    priority="high",
    assigned_to="cc"
)
```

---

## Implementation Steps

### Step 1: Database Migration
- Create `mcp_handoffs` table
- Create `mcp_tasks` table
- Add indexes

### Step 2: Create Router (`/mcp/*`)
- `app/routers/mcp.py`
- Implement all endpoints
- Add API key authentication middleware

### Step 3: Create Services
- `app/services/mcp_handoff_service.py`
- `app/services/mcp_task_service.py`

### Step 4: Create Schemas
- `app/schemas/mcp.py`
- Pydantic models for all requests/responses

### Step 5: Add to Main
- Register router in `main.py`
- Add to OpenAPI docs

### Step 6: Deploy & Test
- Run migrations
- Deploy to Cloud Run
- Test all endpoints
- Update CLAUDE.md

### Step 7: GCS Sync (Optional)
- Keep GCS as backup
- Sync handoffs to bucket after DB write
- Provides redundancy

---

## Definition of Done

- [ ] Database tables created and migrated
- [ ] All 10 endpoints implemented and returning correct responses
- [ ] API key authentication working
- [ ] Public content endpoint (no auth) working for Claude.ai
- [ ] Endpoints return proper error codes (400, 401, 404, 500)
- [ ] OpenAPI docs updated
- [ ] CLAUDE.md updated with MCP instructions
- [ ] End-to-end test: Create handoff via API, fetch via Claude.ai
- [ ] End-to-end test: Create task via API, list and complete
- [ ] Committed to GitHub
- [ ] Deployed to Cloud Run

---

## Estimated Effort

| Task | Hours |
|------|-------|
| Database migration | 1-2 |
| Handoff endpoints (5) | 3-4 |
| Task endpoints (5) | 3-4 |
| Log endpoint (1) | 1 |
| Authentication middleware | 1-2 |
| Schemas and validation | 1-2 |
| Testing | 2-3 |
| Documentation | 1 |
| **Total** | **13-19 hours** |

---

## Questions for CC

1. Should we keep GCS sync as backup, or migrate fully to DB?
2. Any concerns about adding these tables to the MetaPM database?
3. Preference on API key vs service account auth?

---

*Specification prepared by Claude.ai (Architect) for Sprint 5 planning.*
