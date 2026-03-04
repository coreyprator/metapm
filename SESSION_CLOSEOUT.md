# SESSION_CLOSEOUT — MP-RECONCILE-001

**Sprint:** MP-RECONCILE-001
**Project:** MetaPM
**Version:** v2.8.0 → v2.8.1
**Date:** 2026-03-03
**Cloud Run Revision:** metapm-v2-00132-77m
**Commit:** (pending)

---

## Phase 0 Findings

### Done Counter Root Cause (MP-034)
The "Open Only" checkbox in `dashboard.html:395` defaults to checked. `getFilteredRequirements()` at line 698 excludes closed items when checked: `if (openOnly && (req.status === 'closed' || req.status === 'deferred')) return false;`. Both `setSummary()` and `renderByProject()` received filtered data, so done counts were always 0 when Open Only was enabled (the default state).

### Duplicate Codes (MP-035)
8 duplicate code groups found, 6 are within-project duplicates:

| Code | Project | Count | Titles |
|------|---------|-------|--------|
| EM-011 | Etymython | 2 | "Generate EM-MS1 formal CC prompt..." / "Shared etymology graph with SF" |
| PM-001 | project-methodology | 2 | "Bootstrap v1" / "Lessons Learned Routing" |
| PM-005 | project-methodology | 2 | "GitHub PAT rate limit fix..." / "Standardize DEPLOYMENT_CHECKLIST" |
| REQ-001 | MetaPM | 2 | "Add the ability to attach files..." / "Persist the last project..." |
| SF-021 | Super-Flashcards | 2 | "Generate SF-MS1 formal CC prompt..." / "manifest.json 404 error" |
| SF-025 | Super-Flashcards | 2 | "Remove duplicate PK.md file" / "Batch enhance endpoint" |

Cross-project REQ-001/REQ-002/REQ-003 duplicates are expected (REQ prefix is per-project). Not counted as duplicates.

Root cause: Manual seeding by CAI/CC created items with explicit codes before the MP-028 uniqueness check was added. The auto-generator uses generic prefixes (REQ/BUG/TSK) and wouldn't create project-specific codes like EM-011.

### Empty Projects
20 projects in roadmap_projects. ~15 have zero requirements. All are real projects (adventures, videos, personal) but create noise in the dashboard.

### Version Labels
6 of 7 active project versions were stale:

| Project | Was | Now (correct) |
|---------|-----|--------------|
| ArtForge | 2.2.1 | 2.4.1 |
| Etymython | 1.2.0 | 0.2.2 |
| HarmonyLab | 1.8.2 | 2.1.1 |
| MetaPM | 2.4.0 | 2.8.0 |
| Portfolio RAG | 0.1.0 | 1.0.0 |
| Super Flashcards | 2.9.0 | 3.0.2 |
| project-methodology | 3.17.0 | 3.17.0 (correct) |

---

## Requirements

### MP-033 | Fix project version labels | DONE
- Updated 6 project versions via `PUT /api/roadmap/projects/{id}` with correct deployed versions.
- Data fix only. No code changes.

### MP-034 | Fix Done counter | DONE
- Root cause: Open Only filter excluded closed items from the data passed to summary/project renderers.
- Fix: `setSummary()` now counts from `state.requirements` (unfiltered) instead of filtered `reqs`. Per-project done count also reads from `state.requirements`. Summary label changed from "Closed" to "Done" and added "Shown" count.
- File: `static/dashboard.html`

### MP-035 | Fix duplicate code generator | DONE
- Added uniqueness loop to `get_next_roadmap_code()` endpoint. After computing candidate code via MAX+1, verifies it doesn't already exist in the project. Loops up to 100 times to find a unique code.
- Added diagnostic endpoint: `GET /api/roadmap/admin/duplicate-codes` returns all codes with more than one occurrence within the same project.
- Existing duplicates documented above. Not renamed (would break references).
- File: `app/api/roadmap.py`

### MP-036 | Archive flag for empty projects | DONE
- Migration 29: Added `archived BIT DEFAULT 0 NOT NULL` column to `roadmap_projects`.
- Schema: Added `archived` field to `ProjectBase`, `ProjectUpdate`, `ProjectResponse`.
- API: List endpoint filters archived projects by default. `include_archived=true` query param shows all. PUT endpoint handles `archived` field.
- Roadmap aggregate endpoint filters `(archived = 0 OR archived IS NULL)` from default view.
- UI: "Show Archived" checkbox in filter bar. Archive/Unarchive button on each project row. Reset filters unchecks Show Archived.
- No projects auto-archived. PL archives manually.
- Files: `app/core/migrations.py`, `app/schemas/roadmap.py`, `app/api/roadmap.py`, `static/dashboard.html`

---

## Smoke Tests

### Health Check
```json
{"status":"healthy","version":"2.8.1","build":"unknown"}
```

### Version Labels
```
ArtForge: 2.4.1, archived: False
HarmonyLab: 2.1.1, archived: False
MetaPM: 2.8.0, archived: False
```

### Duplicate Codes Endpoint
```json
{"duplicates":[...6 groups...],"total_duplicate_groups":6}
```

### Roadmap Stats
```json
{"total":164,"backlog":43,"closed":101,"executing":20,...}
```

---

## Deferred Items

1. **Backlog API code generator** (`app/api/backlog.py`): Uses legacy tables (Bugs, Requirements). Not updated with uniqueness loop. Low risk since dashboard uses roadmap endpoints.
2. **Existing duplicate codes**: 6 within-project duplicate groups documented above. Not renamed to avoid breaking references. Treated as data debt.
3. **SF missing from projects list**: `proj-sf` exists in DB and is queryable directly, but doesn't appear in the paginated list. May be a limit/ordering issue. Version update via PUT succeeded.
