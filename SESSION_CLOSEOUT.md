# SESSION_CLOSEOUT — MP-RECONCILE-002

**Sprint:** MP-RECONCILE-002
**Project:** MetaPM
**Version:** v2.8.1 → v2.8.2
**Date:** 2026-03-04
**Cloud Run Revision:** metapm-v2-00137-t92
**Commits:** metapm: 06d5111, 5e671c7 (migration 30), project-methodology: 7e06f2e

---

## Phase 0 Findings

### Version Labels (VER-01 / MP-033)
| Project | Was | Updated To |
|---------|-----|-----------|
| ArtForge | 2.4.1 | 2.5.1 |
| MetaPM | 2.8.0 | 2.8.2 |
| Portfolio RAG | 1.0.0 | 2.0.0 |
| project-methodology | 3.17.0 | 3.17 |
| Etymython | 0.2.2 | (unchanged) |
| HarmonyLab | 2.1.1 | (unchanged) |
| Super-Flashcards | 3.0.2 | (unchanged) |

### Archive Enum (ARC-01 / MP-036)
PUT with `{"status":"archived"}` returned 422: "Input should be 'active', 'stable', 'maintenance' or 'paused'". Fixed by adding `ARCHIVED = "archived"` to ProjectStatus enum.

### Done Count (CNT-02 / MP-034)
Per-project done counts used client-side filtering from `state.requirements`. Added server-side `done_count` subquery to project list API. Dashboard uses API value with client-side fallback.

### UAT Note Length (MP-038)
`UATResultItem.note` had `max_length=2000` at `app/schemas/mcp.py:164`. Truncation at mcp.py:326 also capped at 2000. DB column is `NVARCHAR(MAX)` — no DB change needed.

### Diagnostic Endpoint (DUP-02 / MP-035)
GET /api/admin/duplicate-codes returned 200 OK with 6 duplicate groups. Endpoint working correctly.

---

## Requirements Seeded

| Code | ID | Title |
|------|----|-------|
| MP-037 | f6258e4d-4877-44ce-85de-405f291ceb85 | Vision Board view in MetaPM dashboard |
| MP-038 | a6831d20-9cf8-4b55-9ae0-7a041d0fab3a | UAT submit fails when note field exceeds 2000 characters |
| MP-039 | 923c6079-0196-42f1-be9f-c49fa94f80da | UAT Template: no delete button for attachment or pasted screenshot |
| MP-040 | 67c1958f-5553-41b9-a2ed-46f13c0d16e0 | MetaPM item: no delete button for attachment or pasted screenshot |

---

## Requirements Fixed

### MP-038 | UAT submit note length limit | DONE
- Raised `UATResultItem.note` max_length from 2000 to 10000
- Updated truncation logic from 2000 to 10000
- File: `app/schemas/mcp.py`

### MP-036 | Archive status enum | DONE
- Added `ARCHIVED = "archived"` to `ProjectStatus` enum
- Added `maintenance` to dashboard status dropdown (was missing)
- Archive button now sends both `archived` boolean and `status: "archived"/"active"`
- Sync: setting status to 'archived' auto-sets archived=true, and vice versa
- Files: `app/schemas/roadmap.py`, `app/api/roadmap.py`, `static/dashboard.html`

### MP-034 | Per-project done counts | DONE
- Added `done_count` subquery to project list SQL query
- Added `done_count: int = 0` to `ProjectResponse` schema
- Dashboard uses `p.done_count` from API with client-side fallback
- Files: `app/api/roadmap.py`, `app/schemas/roadmap.py`, `static/dashboard.html`

### MP-033 | Version labels | DONE
- Updated 4 project versions via PUT /api/roadmap/projects/{id}
- Data fix only (same approach as MP-RECONCILE-001)

### MP-035 | Diagnostic endpoint | VERIFIED
- GET /api/roadmap/admin/duplicate-codes returns 200 with 6 groups
- No code changes needed

### MP-039 | UAT template attachment delete | DONE
- Added visible "✕ Clear" button after screenshot paste (replaces click-to-remove on image)
- Added visible "✕" delete button next to file attachment filename
- Both clear media data and reset UI
- File: `project-methodology/templates/UAT_Template_v3.html`

### MP-040 | MetaPM item attachment delete | DONE
- Added DELETE /api/roadmap/requirements/{id}/attachments/{aid} endpoint
- Deletes from both GCS bucket and DB
- Added "✕" delete button per attachment in item detail panel
- Files: `app/api/roadmap.py`, `static/dashboard.html`

---

## Deferred Items

1. **MP-037 (Vision Board)**: Seeded as backlog. Not implemented in this sprint — new feature, not a fix.
2. **proj-sf missing from projects list**: Super Flashcards exists in DB but doesn't appear in paginated list endpoint. Noted in MP-RECONCILE-001, still unresolved.

---

## Lessons Learned

1. **Boolean vs enum for archive**: MP-RECONCILE-001 added `archived` boolean column but didn't add 'archived' to the status enum. Both mechanisms needed to stay in sync — fixed by auto-syncing when status is set.
2. **Server-side counts are more reliable**: Client-side done counts depended on filter state and data loading order. Adding `done_count` as a subquery to the project API eliminates this class of bugs.
3. **Status dropdown completeness**: The dashboard project edit form was missing 'maintenance' from the status dropdown despite it being in the enum. UI forms need to match backend enums exactly.
