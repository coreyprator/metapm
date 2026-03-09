# SESSION CLOSEOUT — MP-UAT-GEN
**Date**: 2026-03-09
**Sprint**: MP-UAT-GEN (Server-Side UAT Generation)
**Version**: v2.12.0 -> v2.13.0
**Revision**: metapm-v2-00156-xvl
**Handoff**: 77F76B3F | Checkpoint: BD34
**PTH**: 2C5F

## Summary
Moved UAT HTML generation from CAI to MetaPM. The system now generates complete UAT checklist pages from handoff data and requirement acceptance criteria. Pages match the UAT_Template_v3 dark theme and submit results to the existing /api/uat/submit endpoint.

## What Was Built
1. **Migration 35**: `uat_pages` table with status CHECK constraint, 2 indexes (handoff_id, project).
2. **Test Case Generator** (app/services/uat_generator.py):
   - Parses acceptance criteria from requirement descriptions (checklists, numbered lists, bullet points)
   - Always includes deploy_verify (health check) and smoke (console errors) tests
   - CAI review adds focus_areas, risks, and regression_zones as test cases
   - 7 category types with color-coded badges
3. **HTML Renderer** (app/services/uat_generator.py):
   - Matches UAT_Template_v3 dark theme exactly (CSS vars, section/test-item structure)
   - Pass/Fail/Skip buttons, notes textarea, screenshot paste zone
   - Submit to MetaPM button (POSTs to /api/uat/submit)
   - Copy Results button for text export
4. **API Endpoints** (app/api/uat_gen.py):
   - POST /api/uat/generate — creates/upserts UAT page for handoff
   - GET /uat/{uat_id} — serves HTML, marks in_progress
   - GET /api/uat/pages — list with handoff_id and project filters
5. **Auto-generation hook** (app/api/mcp.py):
   - After handoff creation, extracts requirement codes from content
   - Generates UAT page best-effort (non-blocking)
6. **Dashboard** (static/dashboard.html):
   - Handoff links show "UAT READY" badge and "Run UAT" link

## Files Modified
- `app/core/config.py` — VERSION bump to 2.13.0
- `app/core/migrations.py` — Migration 35 (uat_pages table)
- `app/services/uat_generator.py` — NEW: test case gen + HTML renderer
- `app/api/uat_gen.py` — NEW: 3 API endpoints
- `app/api/mcp.py` — Auto-gen hook in create_handoff
- `app/main.py` — Router registration for uat_gen
- `static/dashboard.html` — Run UAT button in handoff links
- `PROJECT_KNOWLEDGE.md` — Updated to v2.13.0

## Smoke Test Results
- POST /api/uat/generate: 8 test cases generated (DV-01, SM-01, AC-01-01, CF-01, CF-02, RC-01, RG-01, RG-02)
- GET /uat/{id}: 200 OK, full HTML page
- GET /api/uat/pages: Returns list with status and test counts
- Upsert: Same URL maintained on regenerate
- UAT URL: https://metapm.rentyourcio.com/uat/DE6049D6-47F5-4C5B-B534-66FC055B8995

## MetaPM State
- MP-055 (Server-Side UAT Generation): cc_complete (BD34)
- UAT: Submitted, handoff 77F76B3F

## Deliverable Report
```
SESSION COMPLETE
================
PTH: 2C5F | Sprint: MP-UAT-GEN
MetaPM version: 2.12.0 -> 2.13.0
MetaPM code: MP-055
Revision: metapm-v2-00156-xvl

Smoke test UAT URL: https://metapm.rentyourcio.com/uat/DE6049D6-47F5-4C5B-B534-66FC055B8995
Test cases generated: 8
  - deploy_verify: 1
  - smoke: 1
  - acceptance: 1
  - cai_focus: 2
  - risk_check: 1
  - regression: 2

Dashboard "Run UAT" button visible: Y
Auto-generate on handoff receipt: Y

Deviations: None
```
