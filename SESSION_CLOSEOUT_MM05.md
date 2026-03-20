# Session Closeout — MM05 Enforcement Gates + UAT UI
Date: 2026-03-20
Version: 2.37.2 → 2.37.3
Commit: ea8684c
Handoff ID: 9C169530-4C5C-4A48-B3E6-0D1DC1551445
UAT URL: https://metapm.rentyourcio.com/uat/64F828B8-EB8C-4296-975A-752333B144A4

## Sprint
PTH: MM05 | MP-MEGA-011

## Items Delivered

### Gate 1 — Handoff requires linked req at cc_complete+ (app/api/mcp.py)
- PATCH /mcp/handoffs blocked with 400 if prompt_pth is linked to a requirement NOT at cc_complete/uat_ready/uat_pass/done/closed
- Bypass: enforcement_bypass="data_only_sprint" skips Gate 1 only
- Gate is a JOIN: roadmap_requirements r JOIN cc_prompts p ON p.requirement_id = r.id WHERE p.pth = ?

### Gate 2 — uat_spec_id required (app/api/mcp.py)
- PATCH /mcp/handoffs blocked with 400 if uat_spec_id is missing
- Also validates: spec must exist in uat_pages with ≥1 test cases (parses test_cases_json)

### REQ-011 — conditional_pass → passed override button (app/api/uat_spec.py + app/api/uat_gen.py)
- `render_spec_uat_page()` now accepts `spec_status: str = "in_progress"` param
- `mark_passed_btn` rendered only when spec_status == "conditional_pass"
- Calls PATCH /api/uat/{spec_id}/override with {status: "passed"} (existing endpoint)
- CSS: .btn-mark-passed { background: #b45309 } (amber)
- uat_gen.py: SELECT now includes `status` column; passes spec_status= to renderer

### REQ-012 — Dashboard UAT status badges (static/dashboard.html)
- renderUatPages() statusBadge now handles: passed (green), failed (red), conditional_pass (amber), in_progress (yellow), ready/other (gray)
- Was: only "submitted" and "in_progress" handled (wrong mapping)

### REQ-013 — Hide-archived toggle wires to include_passed param (static/dashboard.html)
- refreshUatPages() now reads uat-hide-archived checkbox
- When unchecked: appends &include_passed=true to API URL
- Added change event listener for uat-hide-archived → refreshUatPages()

### HandoffCreate schema (app/schemas/mcp.py)
- Added uat_spec_id: Optional[str] and enforcement_bypass: Optional[str]

## Canaries
- C2: POST /mcp/handoffs without uat_spec_id → 400 "uat_spec_id is required" ✅
- C3: POST /mcp/handoffs with enforcement_bypass="data_only_sprint" + valid spec → 201 ✅
- C4: /health → version: 2.37.3 ✅
- C9: GET /api/uat/spec/64F828B8-... → test_count: 7, status: ready ✅

## Files Changed
- app/api/mcp.py — Gate 1 + Gate 2 enforcement blocks in create_handoff
- app/api/uat_spec.py — render_spec_uat_page: spec_status param, mark_passed_btn, CSS, JS
- app/api/uat_gen.py — SELECT includes status; passes spec_status to render_spec_uat_page
- app/schemas/mcp.py — HandoffCreate: uat_spec_id + enforcement_bypass fields
- app/core/config.py — VERSION 2.37.3
- static/dashboard.html — UAT status badges + hide-archived wire-up

## Requirement Transitions
- MP-HANDOFF-GATE-001: cc_executing → cc_complete (E079) → uat_ready (75E4)
