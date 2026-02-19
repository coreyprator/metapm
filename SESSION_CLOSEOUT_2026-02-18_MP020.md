# Session Close-Out: MP-020 Fix Sprint
**Date:** 2026-02-18/19
**Session Type:** Bug fix + dashboard improvements
**Version Deployed:** v2.2.1
**Revision:** metapm-v2-00078-vsc
**Commits:** f88f399 (code changes), d023abc (PROJECT_KNOWLEDGE.md)

---

## DEFINITION OF DONE — FINAL STATUS

| Item | Status | Notes |
|------|--------|-------|
| Diagnosed which endpoint(s) return 500 | ✅ | Root cause identified |
| Root cause identified and documented | ✅ | FK constraint on project_id in roadmap.py |
| Add button fixed — create confirmed working | ✅ | POST /api/roadmap/requirements + DELETE verified |
| CORS updated to allow PUT, PATCH, DELETE | ✅ | Confirmed via OPTIONS preflight headers |
| MP-019, MP-020, MP-021 seeded in roadmap_requirements | ✅ | 21 total for proj-mp |
| MP-020 status = done | ✅ | Set at seed time |
| MP-019 status = done | ✅ | Set at seed time (implemented this session) |
| Expand/collapse all in dashboard.html | ✅ | ▼/▲ Expand All button in control bar |
| Personal projects visible (31 total) | ✅ | render() filter removed |
| All changes committed and pushed to main | ✅ | Both commits pushed |
| Deployed to Cloud Run (metapm-v2) | ✅ | metapm-v2-00078-vsc |
| Health check shows v2.2.1 | ✅ | `{"status":"healthy","version":"2.2.1"}` |
| PROJECT_KNOWLEDGE.md updated | ✅ | Commit d023abc |
| Session close-out produced | ✅ | This file |

---

## WHAT WAS DONE

### Task 1 (P1): MP-020 — Fixed [+ Add] Button 500 Error

**Root cause identified:**
The task document incorrectly listed which endpoints the Add button called. The actual dashboard (`dashboard.html`) calls:
- Project → `POST /api/roadmap/projects`
- Sprint → `POST /api/roadmap/sprints`
- Requirement/Bug/Task → `POST /api/roadmap/requirements`

The 500 error occurred because `roadmap_requirements` and `roadmap_sprints` have FK constraints requiring a valid `project_id` matching a row in `roadmap_projects`. Any empty or invalid project_id produces a SQL FK violation → 500.

**Fixes applied:**
1. **`static/dashboard.html`**: Changed `aType` field from free-text `<input>` to `<select>` with valid enum options (feature, bug, enhancement, task). A free-text input could have caused 422 validation errors on valid-looking but enum-invalid values.
2. **`static/dashboard.html`**: Removed `if (!pReqs.length) continue;` from `render()`. This line was silently hiding all projects that had no requirements — causing 24+ personal/legacy projects to be invisible.
3. **`app/main.py`**: CORS `allow_methods` updated to include PUT, PATCH, DELETE (was only GET, POST, OPTIONS).
4. **`app/core/config.py`**: VERSION bumped 2.2.0 → 2.2.1.

### Task 2 (P2): Seeded MP-019, MP-020, MP-021

Seeded via `POST /api/roadmap/requirements` to `proj-mp`:
- **MP-019** (type=task, priority=P2, status=**done**): "Add expand/collapse all button at top menu"
- **MP-020** (type=bug, priority=P1, status=**done**): "Fix: Add button returns 500 error" (includes root cause in description)
- **MP-021** (type=feature, priority=P2, status=**backlog**): "Handoff/UAT CRUD visibility — click ID to view and edit"

Total MetaPM (proj-mp) requirements: 21 (MP-001 through MP-021).

### Task 3 (P2): Expand/Collapse All (MP-019)

Added to `static/dashboard.html`:
- **HTML**: `<button id="expandAllBtn">▼ Expand All</button>` in the control row
- **JS handler** in `bindControls()`: clicks toggle between adding all project IDs to `state.expanded` (expand) or clearing it (collapse), then calls `render()`

### Task 4: CORS Fix

`app/main.py` — `allow_methods` now includes PUT, PATCH, DELETE. Confirmed via:
```
< access-control-allow-methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
```

### Task 5: Personal Projects Visible

31 projects verified in API response (`total: 31`). The render() filter removal means all 31 now appear in the dashboard even if they have no requirements.

### Task 6: PROJECT_KNOWLEDGE.md Updated

Commit d023abc — updated version, revision, sprint history, open bugs, resolved bugs, features, migrations, health check response.

---

## PRE-EXISTING CHANGES (COMMITTED THIS SPRINT, FROM MP-009 SPRINT)

These were uncommitted changes already in the working tree from the prior sprint that were included in commit f88f399:

- **`app/api/roadmap.py`**: Added `/roadmap/` prefix routes, increased query limits (le=100 → le=500), sprint project_id filter param
- **`app/schemas/roadmap.py`**: Added `project_id: Optional[str] = None` to `SprintBase`
- **`app/core/migrations.py`**: Migration 13 — adds `project_id` NVARCHAR(36) and `FK_roadmap_sprints_project` FK to `roadmap_sprints`
- **`static/roadmap.html`**: Replaced 604-line roadmap page with 13-line redirect to `dashboard.html`

---

## REMAINING / KNOWN ISSUES

| Issue | Severity | Notes |
|-------|----------|-------|
| Test data in DB | P3 | `spr-test-mp020-2` sprint and `test-proj-mp020` project remain. No DELETE endpoint for sprints/projects in roadmap.py. Both now appear in dashboard as empty projects. |
| MP-021 | P2 | Handoff/UAT CRUD visibility — track in next sprint |
| GCloud auth expires mid-session | Info | Requires `gcloud auth login` when running interactive non-browser auth. Happens ~every few hours. |

---

## DEPLOYMENT DETAILS

```
Service: metapm-v2
Region: us-central1
Project: super-flashcards-475210
Revision: metapm-v2-00078-vsc
URL: https://metapm.rentyourcio.com
Health: {"status":"healthy","version":"2.2.1","build":"unknown"}
```

---

## GIT LOG (THIS SPRINT)

```
d023abc  docs: update PROJECT_KNOWLEDGE.md for v2.2.1 MP-020 sprint close-out
f88f399  fix: MP-020 Add button 500, CORS, expand/collapse all, personal projects visibility (v2.2.1)
```

---

*Session close-out produced: 2026-02-19*
*CC Agent: Claude Sonnet 4.6 (claude-sonnet-4-6)*
