# Session Closeout — MM07 BUG-007 + BUG-008
Date: 2026-03-20
Version: 2.37.5 → 2.37.6
Commit: 0f0ec96
Handoff ID: B565A1C4-75BC-43B2-95A0-404D6EBF70D8
UAT URL: https://metapm.rentyourcio.com/uat/F87BF88D-7706-489D-88B0-AEA311952A4D

## Sprint
PTH: MM07 | MP-MEGA-013

## Items Delivered

### Item 1 — BUG-007: Not Done filter shows zero project counts
- Root cause: `updateProjectFilterCounts()` in dashboard.html used `r.status !== status`
  which always returns false when status='not_done' (no requirement has literal status 'not_done')
- Fix: Mirror `getFilteredRequirements()` logic — check `CLOSED_STATUSES.includes(r.status)` for not_done
- Before: All project cards show 0 count when Not Done filter selected
- After: Project cards correctly show count of non-closed/done requirements

### Item 2 — BUG-008: PATCH /api/roadmap/requirements/{id} returns 405
- Root cause: `update_requirement` handler in roadmap.py only had `@router.put()` decorators
- Fix: Added `@router.patch()` aliases for both `/requirements/{id}` and `/roadmap/requirements/{id}`
- Before: PATCH {"title": "..."} → 405 Method Not Allowed
- After: PATCH {"title": "..."} → 200 with updated requirement

## Files Changed
- static/dashboard.html — updateProjectFilterCounts not_done handling (3-line fix)
- app/api/roadmap.py — @router.patch() aliases for update_requirement
- app/core/config.py — VERSION 2.37.6

## Canaries
- C1: GET /api/roadmap/requirements?status=not_done → 114 items ✅
- C2: PATCH /api/roadmap/requirements/{uuid} {"title":"..."} → 200 OK ✅
- C3: GET /health → version: 2.37.6 ✅
- C4: UAT spec test_count: 3 ✅

## Requirement Transitions
- BUG-007 (9455176e): req_created → uat_ready ✅
- BUG-008 (d6817176): req_created → uat_ready ✅
