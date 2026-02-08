# [MetaPM] 🔴 Phase 4 — Handoff Dashboard (Final Architecture)

> **From**: Claude.ai (Architect)
> **To**: Claude Code (Command Center)
> **Project**: 🔴 MetaPM
> **Task**: handoff-dashboard-final
> **Timestamp**: 2026-02-08T00:30:00Z
> **Priority**: HIGH
> **Type**: Feature Spec (FINAL)

---

## Architecture Decision

**SQL is the primary store. Everything else is derived.**

| Store | Role | Sync Direction |
|-------|------|----------------|
| **SQL (mcp_handoffs)** | **Primary** — single source of truth | — |
| GCS bucket | Backup + external access (web_fetch) | SQL → GCS |
| GDrive HANDOFF_LOG.md | **Generated report** | SQL → Markdown |

### Benefits

1. **Single source of truth** — no compliance gaps
2. **Query everything** — full-text search, filters, analytics
3. **Automatic compliance** — data in DB = compliant
4. **No manual logging** — logs generated from SQL
5. **Simplified CC workflow** — write to one place

---

## Database Schema

### mcp_handoffs (Enhanced)

```sql
CREATE TABLE mcp_handoffs (
    -- Identity
    id NVARCHAR(36) PRIMARY KEY DEFAULT NEWID(),
    
    -- Core fields
    project NVARCHAR(50) NOT NULL,           -- ArtForge, HarmonyLab, etc.
    task NVARCHAR(100) NOT NULL,             -- auth-redirect-fix, v1.4.5-progress
    title NVARCHAR(255),                     -- Human-readable title
    direction NVARCHAR(20) NOT NULL,         -- 'to_cc' or 'to_claude_ai'
    status NVARCHAR(20) DEFAULT 'pending',   -- pending, read, done, archived
    priority NVARCHAR(20),                   -- critical, high, medium, low
    type NVARCHAR(50),                       -- feature, bug_fix, policy, audit
    
    -- Content
    content NVARCHAR(MAX) NOT NULL,          -- Full markdown content
    content_hash NVARCHAR(64),               -- SHA-256 for dedup
    summary NVARCHAR(500),                   -- Auto-extracted or manual
    
    -- Metadata from handoff header
    from_entity NVARCHAR(100),               -- "Claude Code (Command Center)"
    to_entity NVARCHAR(100),                 -- "Claude.ai (Architect)"
    version NVARCHAR(20),                    -- v1.4.5, v2.2.1
    
    -- Timestamps
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),
    read_at DATETIME2,
    completed_at DATETIME2,
    
    -- Sync status
    gcs_synced BIT DEFAULT 0,
    gcs_url NVARCHAR(500),
    gcs_synced_at DATETIME2,
    
    -- Git tracking (for completion handoffs)
    git_commit NVARCHAR(50),
    git_verified BIT DEFAULT 0,
    
    -- Compliance
    compliance_score INT DEFAULT 100,        -- 0-100
    
    -- Indexes
    INDEX idx_project (project),
    INDEX idx_status (status),
    INDEX idx_created (created_at DESC),
    INDEX idx_direction (direction)
);
```

### Full-Text Search Index

```sql
CREATE FULLTEXT CATALOG HandoffCatalog AS DEFAULT;
CREATE FULLTEXT INDEX ON mcp_handoffs(content, title, summary) 
    KEY INDEX PK_mcp_handoffs ON HandoffCatalog;
```

---

## API Endpoints

### Create Handoff (Primary Entry Point)

```python
POST /mcp/handoffs

Request:
{
    "project": "HarmonyLab",
    "task": "v1.4.5-progress-fix",
    "direction": "to_claude_ai",
    "content": "# [HarmonyLab] 🔵 v1.4.5 Progress Page Fix\n\n...",
    "git_commit": "7f90d74"  // Optional
}

Response:
{
    "id": "abc-123",
    "project": "HarmonyLab",
    "task": "v1.4.5-progress-fix",
    "status": "pending",
    "gcs_url": "gs://corey-handoff-bridge/harmonylab/outbox/20260207_230000_v145-progress-fix.md",
    "created_at": "2026-02-07T23:00:00Z"
}
```

The endpoint:
1. Parses metadata from content header
2. Generates content hash (dedup)
3. Saves to SQL
4. Triggers async GCS sync
5. Returns created record

### Dashboard Query

```python
GET /mcp/handoffs/dashboard
    ?project=HarmonyLab
    &status=pending,done
    &direction=to_claude_ai
    &search=oauth
    &date_from=2026-02-01
    &date_to=2026-02-08
    &sort=created_at
    &order=desc
    &page=1
    &limit=20

Response:
{
    "items": [...],
    "total": 45,
    "page": 1,
    "pages": 3,
    "compliance_summary": {
        "overall": 94,
        "synced": 43,
        "pending_sync": 2
    }
}
```

### Full-Text Search

```python
GET /mcp/handoffs/search?q=OAuth%20redirect%20cookie

Response:
{
    "items": [
        {
            "id": "abc-123",
            "project": "HarmonyLab",
            "title": "v1.4.4 OAuth Complete",
            "snippet": "...changed SessionMiddleware same_site='lax' → same_site='none'. With lax, browsers don't send cookies for cross-site **OAuth** **redirects**...",
            "relevance": 0.95
        }
    ],
    "total": 3
}
```

### Get Single Handoff

```python
GET /mcp/handoffs/{id}

Response:
{
    "id": "abc-123",
    "project": "HarmonyLab",
    "task": "v1.4.5-progress-fix",
    "content": "# [HarmonyLab] 🔵 v1.4.5...",
    "status": "done",
    "gcs_synced": true,
    "gcs_url": "https://storage.googleapis.com/corey-handoff-bridge/...",
    "git_commit": "7f90d74",
    ...
}
```

### Get Handoff Content (Public — for web_fetch)

```python
GET /mcp/handoffs/{id}/content

Response: Raw markdown (no auth required)
```

### Update Status

```python
PATCH /mcp/handoffs/{id}

Request:
{
    "status": "done",
    "git_commit": "abc1234"
}
```

### Generate Log Report

```python
GET /mcp/handoffs/export/log?project=HarmonyLab&format=markdown

Response: Generated HANDOFF_LOG.md content

# HarmonyLab Handoff Log
Generated: 2026-02-08T00:30:00Z

## 2026-02-07

### v1.4.5 Progress Page Fix
- **Direction**: CC → Claude.ai
- **Status**: Done
- **Git**: 7f90d74
- **GCS**: [Link](https://storage.googleapis.com/...)

### v1.4.4 OAuth Complete
...
```

### Sync to GDrive (Trigger)

```python
POST /mcp/handoffs/export/gdrive?project=HarmonyLab

# Generates markdown and saves to:
# G:\My Drive\Code\Python\HarmonyLab\handoffs\log\HANDOFF_LOG.md
```

### Stats & Analytics

```python
GET /mcp/handoffs/stats

Response:
{
    "total": 156,
    "by_project": {
        "ArtForge": { "total": 32, "pending": 2, "done": 30 },
        "HarmonyLab": { "total": 28, "pending": 1, "done": 27 },
        ...
    },
    "by_direction": {
        "to_cc": 78,
        "to_claude_ai": 78
    },
    "avg_completion_hours": 4.2,
    "this_week": 24,
    "gcs_sync_status": {
        "synced": 154,
        "pending": 2
    }
}
```

---

## Background Jobs

### 1. GCS Sync Job

Syncs new/updated handoffs to GCS bucket:

```python
async def gcs_sync_job():
    """Run every 5 minutes."""
    unsynced = await db.query(
        "SELECT * FROM mcp_handoffs WHERE gcs_synced = 0"
    )
    
    for handoff in unsynced:
        # Generate filename
        timestamp = handoff.created_at.strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{handoff.task}.md"
        path = f"{handoff.project}/outbox/{filename}"
        
        # Upload to GCS
        bucket = storage_client.bucket("corey-handoff-bridge")
        blob = bucket.blob(path)
        blob.upload_from_string(handoff.content, content_type="text/markdown")
        
        # Update record
        await db.execute("""
            UPDATE mcp_handoffs 
            SET gcs_synced = 1, 
                gcs_url = @url,
                gcs_synced_at = GETDATE()
            WHERE id = @id
        """, {"id": handoff.id, "url": f"gs://corey-handoff-bridge/{path}"})
```

### 2. Import Existing GCS Handoffs (One-time)

Import existing handoffs from GCS into SQL:

```python
async def import_existing_handoffs():
    """One-time import of existing GCS handoffs."""
    bucket = storage_client.bucket("corey-handoff-bridge")
    projects = ["ArtForge", "harmonylab", "Super-Flashcards", 
                "metapm", "Etymython", "project-methodology"]
    
    for project in projects:
        blobs = bucket.list_blobs(prefix=f"{project}/outbox/")
        
        for blob in blobs:
            if not blob.name.endswith('.md'):
                continue
                
            content = blob.download_as_text()
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            # Check for duplicate
            existing = await db.query(
                "SELECT id FROM mcp_handoffs WHERE content_hash = @hash",
                {"hash": content_hash}
            )
            
            if existing:
                continue
            
            # Parse metadata from content
            metadata = parse_handoff_header(content)
            
            # Insert
            await db.execute("""
                INSERT INTO mcp_handoffs 
                (project, task, direction, content, content_hash, 
                 from_entity, to_entity, version, created_at,
                 gcs_synced, gcs_url, gcs_synced_at)
                VALUES (...)
            """)
```

### 3. GDrive Log Generation (On-demand or Scheduled)

```python
async def generate_gdrive_log(project: str):
    """Generate HANDOFF_LOG.md from SQL data."""
    handoffs = await db.query("""
        SELECT * FROM mcp_handoffs 
        WHERE project = @project 
        ORDER BY created_at DESC
    """, {"project": project})
    
    # Generate markdown
    md = f"# {project} Handoff Log\n"
    md += f"Generated: {datetime.now().isoformat()}\n\n"
    
    current_date = None
    for h in handoffs:
        date = h.created_at.strftime("%Y-%m-%d")
        if date != current_date:
            md += f"\n## {date}\n\n"
            current_date = date
        
        md += f"### {h.task}\n"
        md += f"- **Direction**: {h.direction}\n"
        md += f"- **Status**: {h.status}\n"
        if h.git_commit:
            md += f"- **Git**: {h.git_commit}\n"
        if h.gcs_url:
            md += f"- **GCS**: [{h.task}]({h.gcs_url.replace('gs://', 'https://storage.googleapis.com/')})\n"
        md += "\n"
    
    # Save to GDrive
    log_path = f"G:\\My Drive\\Code\\Python\\{project}\\handoffs\\log\\HANDOFF_LOG.md"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, 'w') as f:
        f.write(md)
    
    return md
```

---

## CC Workflow (Simplified)

### Before (3 steps, error-prone)

```
1. Write handoff markdown
2. Upload to GCS manually
3. Update HANDOFF_LOG.md manually  ← Often skipped!
4. Git commit
```

### After (2 steps, automated)

```
1. POST /mcp/handoffs with content
   → SQL saved
   → GCS synced automatically
   → Log generated automatically
2. Git commit
```

CC can use a helper script:

```python
# scripts/handoff/send_handoff.py

import requests

def send_handoff(project: str, task: str, content: str, git_commit: str = None):
    response = requests.post(
        "https://metapm.rentyourcio.com/mcp/handoffs",
        headers={"X-API-Key": os.environ["METAPM_API_KEY"]},
        json={
            "project": project,
            "task": task,
            "direction": "to_claude_ai",
            "content": content,
            "git_commit": git_commit
        }
    )
    
    result = response.json()
    print(f"✅ Handoff created: {result['id']}")
    print(f"   GCS: {result['gcs_url']}")
    return result

# Usage:
send_handoff(
    project="HarmonyLab",
    task="v1.4.5-progress-fix",
    content=open("HANDOFF_v145.md").read(),
    git_commit="7f90d74"
)
```

---

## Frontend Dashboard

### Main View

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ MetaPM                                              [User] [Settings]        │
├─────────────────────────────────────────────────────────────────────────────┤
│ ◀ Dashboard  │  Handoff Bridge                              📊 Stats        │
├──────────────┴──────────────────────────────────────────────────────────────┤
│                                                                              │
│  [All Projects ▼] [All Status ▼] [All Directions ▼] [🔍 Search handoffs...] │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────────┐│
│  │ Project       │ Task              │ Direction │ Status │ GCS │ Date    ↓ ││
│  ├───────────────┼───────────────────┼───────────┼────────┼─────┼──────────┤│
│  │ 🔵 HarmonyLab │ v1.4.5-progress   │ ← Claude  │ ✅ Done│ ✓   │ 2/7 11pm ││
│  │ 🟢 proj-meth  │ git-commit-policy │ → CC      │ ✅ Done│ ✓   │ 2/7 11pm ││
│  │ 🔵 HarmonyLab │ v1.4.4-oauth      │ ← Claude  │ ✅ Done│ ✓   │ 2/7 9pm  ││
│  │ 🟠 ArtForge   │ v2.2.1-uat-fixes  │ ← Claude  │ ✅ Done│ ✓   │ 2/7 9pm  ││
│  │ 🔴 MetaPM     │ phase3-api-test   │ ← Claude  │ ✅ Done│ ✓   │ 2/7 6pm  ││
│  │ 🔵 HarmonyLab │ auth-redirect-fix │ → CC      │ ✅ Done│ ✓   │ 2/7 8pm  ││
│  └──────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  Showing 1-6 of 156 handoffs                        [◀ Prev] [Next ▶]       │
│                                                                              │
│  [📥 Export Log] [🔄 Sync to GCS] [📊 Analytics]                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Detail Panel (Click Row)

```
┌─────────────────────────────────────────────────────────────┐
│ [HarmonyLab] 🔵 v1.4.5-progress-fix              [✕ Close]  │
├─────────────────────────────────────────────────────────────┤
│ Direction: CC → Claude.ai                                   │
│ Status: Done                                                │
│ Created: 2026-02-07 23:00                                   │
│ Git: 7f90d74                                                │
│                                                             │
│ Links:                                                      │
│ • [GCS] https://storage.googleapis.com/corey-handoff-bri... │
│ • [GitHub] View commit                                      │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ # [HarmonyLab] 🔵 v1.4.5 Progress Page Fix              │ │
│ │                                                         │ │
│ │ > **From**: Claude Code (Command Center)                │ │
│ │ > **To**: Claude.ai (Architect) / Corey                 │ │
│ │ > **Project**: 🔵 HarmonyLab                            │ │
│ │ ...                                                     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ [View Full] [Mark Done] [Archive]                           │
└─────────────────────────────────────────────────────────────┘
```

### Stats View

```
┌─────────────────────────────────────────────────────────────┐
│ 📊 Handoff Analytics                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Total Handoffs: 156          This Week: 24                 │
│  Avg Completion: 4.2 hours    GCS Synced: 100%              │
│                                                             │
│  By Project:                                                │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 🟠 ArtForge        ████████████████░░░░  32 (21%)      │ │
│  │ 🔵 HarmonyLab      ██████████████░░░░░░  28 (18%)      │ │
│  │ 🟡 Super-Flashcards████████████░░░░░░░░  24 (15%)      │ │
│  │ 🔴 MetaPM          ████████████░░░░░░░░  24 (15%)      │ │
│  │ 🟣 Etymython       ██████████░░░░░░░░░░  20 (13%)      │ │
│  │ 🟢 project-meth    ██████████████░░░░░░  28 (18%)      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  Direction:  → CC: 78 (50%)  |  ← Claude.ai: 78 (50%)       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Files to Create

| File | Description |
|------|-------------|
| `app/models/handoff.py` | SQLAlchemy model |
| `app/routers/handoffs.py` | API endpoints (replaces/extends mcp.py) |
| `app/services/handoff_service.py` | Business logic |
| `app/services/gcs_sync_service.py` | GCS sync |
| `app/services/log_generator_service.py` | Markdown log generation |
| `app/jobs/gcs_sync_job.py` | Background sync |
| `frontend/handoffs.html` | Dashboard page |
| `frontend/js/handoffs.js` | Dashboard logic |
| `frontend/css/handoffs.css` | Dashboard styles |
| `scripts/handoff/send_handoff.py` | CC helper script |
| `scripts/handoff/import_existing.py` | One-time GCS import |

---

## Migration Plan

### Phase 1: Database + API
1. Create mcp_handoffs table (enhanced schema)
2. Create API endpoints
3. Test CRUD operations

### Phase 2: Import Existing
1. Run import script to pull existing GCS handoffs into SQL
2. Verify counts match

### Phase 3: Frontend
1. Build dashboard UI
2. Test all features

### Phase 4: CC Integration
1. Deploy send_handoff.py helper
2. Update CC workflow to use API
3. Deprecate manual GCS uploads

### Phase 5: Log Generation
1. Enable GDrive log generation
2. Set up scheduled export (optional)

---

## Testing Checklist

| Test | Expected |
|------|----------|
| Create handoff via API | Saved to SQL, GCS synced |
| Dashboard loads | Shows all handoffs |
| Filter by project | Correct results |
| Full-text search | Finds by content |
| View detail | Shows full content + links |
| Export log | Generates valid markdown |
| Import existing | All GCS handoffs in SQL |
| GCS sync job | Pending items synced |

---

## Version

Bump to **v1.8.0** after implementation.

---

## Definition of Done

- [ ] Database schema created
- [ ] All API endpoints working
- [ ] Existing GCS handoffs imported
- [ ] Dashboard UI complete
- [ ] GCS sync job running
- [ ] Log export working
- [ ] CC helper script deployed
- [ ] Full-text search working
- [ ] All tests pass
- [ ] Version bumped to 1.8.0
- [ ] Git committed
- [ ] Handoff sent via new system! 🎉

---

*Final architecture spec from Claude.ai (Architect)*
*SQL as primary store — everything else derived*
