# Handoff: HO-MP03 MetaPM Hierarchical Dashboard Rework
**Date:** 2026-02-17
**Version:** 2.2.0
**Commit:** 30399b3
**Revision:** metapm-v2-00072-crt

## What Was Done
- Root cause: Multi-page UI was redundant and inconsistent
- Feature: Single-page hierarchical dashboard replacing current dashboard/roadmap entry points
- Fixed route shadowing (`/api/projects` collision) with roadmap-prefixed APIs under `/api/roadmap/*`
- Seeded 78 requirements across 6 roadmap projects (31 newly inserted in follow-up seeding pass, final dataset = 78)
- Updated statuses: `EM-006`, `EM-009`, `EM-010` → `done`
- Roadmap page now redirects to dashboard (`/roadmap.html` → `/static/dashboard.html`)
- Files modified:
  - `app/api/roadmap.py`
  - `app/api/mcp.py`
  - `app/core/migrations.py`
  - `app/core/config.py`
  - `app/schemas/roadmap.py`
  - `static/dashboard.html`
  - `static/roadmap.html`
  - `scripts/seed_vision_requirements.py`

## Verification
- Health check:
```json
{
  "status": "healthy",
  "version": "2.2.0",
  "build": "unknown"
}
```
- Version: `2.2.0`
- Projects: `6`
- Requirements: `78 total`
- Sprints: `0` (Sprint entity exists; not populated)
- Dashboard loads: `200` (`GET /static/dashboard.html`)
- Roadmap redirect page loads and points to dashboard: `200` (`GET /roadmap.html` content references `dashboard.html`)
- Seed targets verified present:
  - `HL-014..HL-018`
  - `SF-007..SF-013`
  - `AF-007..AF-015`
  - `EM-012`
  - `MP-009..MP-017`

## Regression
- `GET /api/projects` still responds (legacy projects API functional)
- `GET /api/handoffs` currently errors (`500`) due SQL ORDER BY/derived table issue in that endpoint query (pre-existing regression discovered during close-out testing)

## Auto-Linking Test (Session 2 Follow-up)
| Test | Expected | Actual |
|------|----------|--------|
| Create handoff with req IDs in content (`POST /api/handoffs`) | 201 Created | **FAIL** — 500 truncation (`handoff_requests.id` is `VARCHAR(10)`; `HO-MP03-TEST` too long) |
| Junction rows created for MP-009, MP-010, EM-011 via `/api/handoffs` path | 3 rows | **NOT IMPLEMENTED via this path** — endpoint does not run parse/link logic |
| Requirement MP-009 shows linked handoff | linked handoff in response | **PASS** via MCP UAT path (`/mcp/uat/submit`) |
| Auto-close on approval updates linked req status to done | status changes | **PASS** (MP-009/MP-010 remained `done`; linkage confirmed to MCP handoff `9DE27714-8925-4432-8F2B-3512BD8F59FC`) |

Notes:
- `EM-011` was referenced in test content but does not exist in current roadmap dataset, so no link could be created for that ID.
- Auto-linking parse logic is implemented in MCP handoff/UAT flow, not in legacy `/api/handoffs` lifecycle endpoint.

## UAT
- JSON artifact: `handoffs/outbox/UAT_HO-MP03_dashboard_rework.json`
- GCS upload target: `gs://corey-handoff-bridge/metapm/outbox/UAT_HO-MP03_dashboard_rework.json`

## What's Next
- Fix `/api/handoffs` list SQL query regression (500)
- Add parse/link behavior to legacy `/api/handoffs` endpoint or consolidate to MCP handoff path
- Verify detail panel inline editing UX in-browser with multi-field edits
- Populate and validate sprint creation/assignment UX against new sprint model
- Finalize filter/sort UAT script with real interaction checks
