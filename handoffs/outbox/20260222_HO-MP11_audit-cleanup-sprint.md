# Handoff: HO-MP11 MetaPM v2.3.7 — Audit + Cleanup Sprint

**Date:** 2026-02-22
**Version:** 2.3.7
**Commit:** 87e81fc
**Revision:** metapm-v2-00090-vtn

---

## What Was Done

Three-phase audit + cleanup + build sprint.

### Phase 1 — Audit (Status Corrections)

Queried all 89 requirements across all projects. Found 20 in_progress items. Verified each against production APIs. Applied 18 status corrections:

**→ done (12 items):**
| Code | Name |
|------|------|
| MP-004 | Dashboard standup view (superseded by MP-009) |
| MP-005 | Roadmap CRUD (full GET/POST/PUT/DELETE API + UI) |
| MP-006 | Dashboard UI review (superseded by MP-009) |
| MP-009 | Hierarchical single-page dashboard (filter bar, group by, CRUD) |
| AF-004 | Runway Gen-3 (providers API: available=true) |
| AF-007 | Story import & storyboard generation (routes verified) |
| AF-008 | 11Labs VO with character voice selection (20 voices in API) |
| AF-009 | SFX identification & prompt generation (routes verified) |
| AF-010 | Background music identification & prompts (routes verified) |
| AF-011 | Video clip generation, provider-agnostic (Runway + Seedance) |
| AF-013 | Adobe Premiere XML export (two export routes verified) |
| HL-010 | Default to Analysis page (root serves analysis, no quiz redirect) |

**→ backlog (6 items):**
| Code | Name | Reason |
|------|------|--------|
| MP-001 | GitHub Actions CI/CD | No .github dir, build=unknown |
| MP-007 | Conditional pass UAT status | enum missing (FIXED in Phase 3 → done) |
| MP-014 | Cross-project dependency links | No API routes or UI |
| AF-015 | Deprecate Battle of the Bands | /battle.html still live |
| HL-008 | Import jazz standards | 0 songs in DB |
| HL-015 | Annotated MuseScore export | 404 on /api/export/musescore |

**Stay in_progress (2 items):**
- **MP-003** (handoffs SQL bug) — fixed in Phase 2 → marked done
- **EM-012** (IPA + audio) — audio 97% done, IPA text field still missing

**Description integrity:** 1 mismatch found (AF-011). Seed says "Runway Gen-3 only"; current description says "provider-agnostic" (accurate). Did NOT revert — current description is factually correct.

---

### Phase 2 — Cleanup

**MP-003: /api/handoffs SQL error fixed**
- Root cause: `ORDER BY` was added before wrapping in `SELECT TOP N (...) AS sub`. SQL Server prohibits `ORDER BY` in derived tables without `TOP/OFFSET/FOR XML`.
- Fix: Moved `TOP {limit}` inline to the base SELECT; removed subquery wrapper. `ORDER BY` now at query tail.
- File: `app/api/handoff_lifecycle.py` line 189

**test_ui_smoke.py created**
- 9 production smoke tests using `httpx` against live URL
- Tests: health, version, requirements list, handoffs (verifies SQL fix), projects, roadmap, root redirect, dashboard HTML, architecture redirect
- `--noconftest` required: conftest.py imports `app.main` which calls `run_migrations()` at module load — blocks without prod credentials
- Updated CLAUDE.md to: `pytest tests/test_ui_smoke.py -v --noconftest`

**Description integrity:** No restorations needed. 1 flagged case (AF-011) is an intentional evolution to provider-agnostic architecture.

---

### Phase 3 — Build

**MP-007: Conditional pass UAT status**
- Added `CONDITIONAL_PASS = "conditional_pass"` to `UATStatus` enum in `app/schemas/mcp.py`
- Available in `/api/uat/submit`, `/api/uat/direct-submit`, and all UAT endpoints
- No DB migration needed: column is VARCHAR, no CHECK constraint
- Marked MP-007 as done in roadmap

---

## Verification

**Health check:**
```json
{"status":"healthy","version":"2.3.7","build":"unknown"}
```

**Smoke tests:**
```
9 passed in 3.20s
tests/test_ui_smoke.py::TestHealthAndVersion::test_health_returns_200 PASSED
tests/test_ui_smoke.py::TestHealthAndVersion::test_health_returns_version PASSED
tests/test_ui_smoke.py::TestCoreAPIEndpoints::test_requirements_list PASSED
tests/test_ui_smoke.py::TestCoreAPIEndpoints::test_handoffs_list PASSED
tests/test_ui_smoke.py::TestCoreAPIEndpoints::test_projects_list PASSED
tests/test_ui_smoke.py::TestCoreAPIEndpoints::test_roadmap_requirements PASSED
tests/test_ui_smoke.py::TestStaticPages::test_root_redirects_to_dashboard PASSED
tests/test_ui_smoke.py::TestStaticPages::test_dashboard_loads PASSED
tests/test_ui_smoke.py::TestStaticPages::test_architecture_redirects PASSED
```

**UATStatus enum (confirmed in production OpenAPI):**
`['passed', 'failed', 'pending', 'blocked', 'partial', 'conditional_pass']`

---

## Regression

- Dashboard loads and all CRUD features verified (MP-005, MP-009)
- Architecture redirect: 302 → GCS URL confirmed
- Requirements list: 89 total requirements with correct statuses
- /health: v2.3.7 confirmed

---

## Full Audit Table

| Req ID | Name | Claimed Status | Actual Status | Evidence | Action |
|--------|------|---------------|---------------|----------|--------|
| MP-001 | GitHub Actions CI/CD | in_progress | Not started | No .github dir, build=unknown | → backlog |
| MP-003 | Fix handoff linkage | in_progress | Partially done / bug | /api/handoffs returned SQL error 42000 | → Fixed (Phase 2) → done |
| MP-004 | Dashboard standup view | in_progress | Superseded done | MP-009 ships standup view purpose | → done |
| MP-005 | Roadmap CRUD | in_progress | Done | Full CRUD API + dashboard Add/Edit/Delete | → done |
| MP-006 | Dashboard UI review | in_progress | Superseded done | MP-009 replaces multi-page layout | → done |
| MP-007 | Conditional pass UAT status | in_progress | Not done | enum missing conditional_pass | → Built (Phase 3) → done |
| MP-009 | Hierarchical single-page dashboard | in_progress | Done | Filter bar, group by, CRUD, search all live | → done |
| MP-014 | Cross-project dependency links | in_progress | Not started | No routes or UI for dependencies | → backlog |
| AF-004 | Runway Gen-3 | in_progress | Done | /api/video/providers: runway available=true | → done |
| AF-007 | Story import & storyboard | in_progress | Done | /storyboard, /split-scenes, /enrich routes live | → done |
| AF-008 | 11Labs VO with character voice | in_progress | Done | 20 voices in /api/stories/voices; per-scene chars | → done |
| AF-009 | SFX identification & prompts | in_progress | Done | /api/sfx/library, /sfx/generate routes exist | → done |
| AF-010 | Background music & prompts | in_progress | Done | /api/music/library, /api/music/moods, /stories/.../music | → done |
| AF-011 | Video clip generation provider-agnostic | in_progress | Done | /generate-video, providers API live (Runway+Seedance) | → done |
| AF-013 | Adobe Premiere XML export | in_progress | Done | /export/premiere.xml and /export/premiere-xml both live | → done |
| AF-015 | Deprecate Battle of the Bands | in_progress | Not done | /battle.html, /api/battle/* still in production | → backlog |
| HL-008 | Import jazz standards | in_progress | Not done | 0 songs in HarmonyLab DB | → backlog |
| HL-010 | Default to Analysis page | in_progress | Done | Root 200, loads analysis page (no quiz redirect) | → done |
| HL-015 | Annotated MuseScore export | in_progress | Not done | /api/export/musescore → 404 | → backlog |
| EM-012 | IPA + pronunciation wave files | in_progress | Partial | Audio 68/70 (97%), no ipa field in figure schema | → stay in_progress |

---

## UAT

UAT JSON: `gs://corey-handoff-bridge/MetaPM/outbox/HO-MP11_UAT.json`

---

## What's Next

- **EM-012**: Confirm whether IPA text data is stored in a different field/table or is still pending
- **AF-015**: Remove /battle routes from ArtForge (quick win — feature was deprecated)
- **HL-008**: Load jazz standard MIDI files into HarmonyLab DB
- **MP-001**: GitHub Actions CI/CD — large infrastructure sprint, dedicate a session
- **MP-014**: Cross-project dependency links — data model + API + UI work
- **metapm_descriptions_seed.json**: Consider updating AF-011 entry to reflect provider-agnostic architecture
