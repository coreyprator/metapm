# [MetaPM] 🔴 Dashboard — Complete Implementation Required

## Current State

| Component | Status | Notes |
|-----------|--------|-------|
| `static/handoffs.html` | ✅ Exists | Basic UI |
| `GET /mcp/handoffs/dashboard` | ✅ Exists | Basic query |
| `GET /mcp/handoffs/stats` | ✅ Exists | Basic stats |
| `POST /mcp/handoffs/sync` | ✅ Exists | GCS sync |
| GCS sync job | ✅ Exists | Background job |
| **Compliance tracking** | ❌ Missing | Not implemented |
| **SQL as primary store** | ❌ Missing | Not implemented |
| **Full-text search** | ❌ Missing | Not implemented |
| **Log generation** | ❌ Missing | Not implemented |
| **Completion handoff** | ❌ Missing | **VIOLATION** |

---

## CRITICAL: Missing Completion Handoff

The original dashboard was implemented but **NO completion handoff was sent**.

This violates project methodology. Every task completion MUST:
1. Git commit
2. Send handoff via Handoff Bridge with URL

**Do not let this happen again.**

---

## Task: Implement FINAL Dashboard Spec

**Spec file**: `HANDOFF_MetaPM_dashboard-final_20260208_003000.md`
**Location**: `C:\Users\Owner\Downloads\`

This spec SUPERSEDES all previous versions. Key architecture change:

### SQL is Primary Store

```
SQL (mcp_handoffs) ← Primary, single source of truth
    ↓ auto-sync
GCS bucket ← Backup + external access
    ↓ generated
HANDOFF_LOG.md ← Report (not manual entry)
```

---

## What Needs to Be Done

### Phase 1: Database Schema Update

Add/modify columns in `mcp_handoffs`:

```sql
-- Content storage (SQL as primary)
ALTER TABLE mcp_handoffs ADD COLUMN content NVARCHAR(MAX);
ALTER TABLE mcp_handoffs ADD COLUMN content_hash NVARCHAR(64);
ALTER TABLE mcp_handoffs ADD COLUMN summary NVARCHAR(500);

-- Metadata
ALTER TABLE mcp_handoffs ADD COLUMN from_entity NVARCHAR(100);
ALTER TABLE mcp_handoffs ADD COLUMN to_entity NVARCHAR(100);
ALTER TABLE mcp_handoffs ADD COLUMN version NVARCHAR(20);
ALTER TABLE mcp_handoffs ADD COLUMN priority NVARCHAR(20);
ALTER TABLE mcp_handoffs ADD COLUMN type NVARCHAR(50);

-- Timestamps
ALTER TABLE mcp_handoffs ADD COLUMN read_at DATETIME2;
ALTER TABLE mcp_handoffs ADD COLUMN completed_at DATETIME2;

-- Sync status
ALTER TABLE mcp_handoffs ADD COLUMN gcs_synced BIT DEFAULT 0;
ALTER TABLE mcp_handoffs ADD COLUMN gcs_synced_at DATETIME2;

-- Git tracking
ALTER TABLE mcp_handoffs ADD COLUMN git_commit NVARCHAR(50);
ALTER TABLE mcp_handoffs ADD COLUMN git_verified BIT DEFAULT 0;

-- Compliance
ALTER TABLE mcp_handoffs ADD COLUMN compliance_score INT DEFAULT 100;
```

Create full-text search index:
```sql
CREATE FULLTEXT INDEX ON mcp_handoffs(content, title, summary);
```

### Phase 2: API Endpoints (New/Enhanced)

| Endpoint | Status | Action |
|----------|--------|--------|
| `POST /mcp/handoffs` | Enhance | Accept full content, auto-parse metadata |
| `GET /mcp/handoffs/dashboard` | Enhance | Add compliance columns, filters |
| `GET /mcp/handoffs/search` | **NEW** | Full-text search |
| `GET /mcp/handoffs/{id}/content` | Exists | Keep (public access) |
| `GET /mcp/handoffs/export/log` | **NEW** | Generate HANDOFF_LOG.md |
| `POST /mcp/handoffs/export/gdrive` | **NEW** | Save log to GDrive |
| `GET /mcp/handoffs/stats` | Enhance | Add compliance stats |

### Phase 3: Services (New)

| Service | Purpose |
|---------|---------|
| `app/services/handoff_service.py` | CRUD, metadata parsing |
| `app/services/gcs_sync_service.py` | Background GCS sync |
| `app/services/log_generator_service.py` | Generate markdown logs |
| `app/services/search_service.py` | Full-text search |

### Phase 4: Import Existing GCS Handoffs

Create one-time migration script:
```python
# scripts/handoff/import_existing.py
# Scans GCS bucket, imports all handoffs into SQL
# Deduplicates by content_hash
```

### Phase 5: Frontend Enhancement

Update `static/handoffs.html`:
- Add GCS sync status column (✓/✗)
- Add full-text search box
- Add "Export Log" button
- Show compliance indicators
- Improve detail panel (show content, links)

### Phase 6: CC Helper Script

Create `scripts/handoff/send_handoff.py`:
```python
# Usage: python send_handoff.py --project HarmonyLab --task v1.4.5 --file HANDOFF.md --commit abc123
# Posts to API, returns GCS URL
```

---

## Version

Bump to **v1.8.0** (or v1.9.0 if v1.8.0 was already used).

---

## Definition of Done

- [ ] Database schema updated with all new columns
- [ ] Full-text search index created
- [ ] All API endpoints working
- [ ] Import script created and run (existing GCS → SQL)
- [ ] Frontend shows compliance status
- [ ] Full-text search working
- [ ] Export log endpoint generates valid markdown
- [ ] CC helper script created
- [ ] GCS sync job updated for new schema
- [ ] All tests pass
- [ ] Version bumped
- [ ] **Git committed**
- [ ] **Handoff sent via Handoff Bridge with URL** ← MANDATORY

---

## Handoff Bridge Reminder

When complete, send handoff with this format:

```markdown
# [MetaPM] 🔴 v1.8.0 Dashboard Complete

> **From**: Claude Code (Command Center)
> **To**: Claude.ai (Architect) / Corey
> **Project**: 🔴 MetaPM
> **Task**: dashboard-final
> **Timestamp**: [ISO timestamp]
> **Type**: Feature Completion

## Summary
[What was done]

## Deployment
| Service | Revision | Version |
|---------|----------|---------|
| MetaPM | metapm-v2-XXXXX | 1.8.0 |

## Files Created
[List]

## Files Modified
[List]

## Git Status
| Item | Status |
|------|--------|
| Committed | ✅ `[hash]` - "[message]" |
| Pushed | ✅ origin/main |

## Testing
[Results]

## GCS URL
https://storage.googleapis.com/corey-handoff-bridge/metapm/outbox/[timestamp]_dashboard-complete.md
```

**Upload to GCS and provide the URL in your response.**

---

*This task is not complete until a Handoff Bridge URL is provided.*
