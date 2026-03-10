# SESSION CLOSEOUT — MP-UAT-TAB-001
**Date**: 2026-03-09
**Sprint**: MP-UAT-TAB-001 (UAT Tab + Dashboard Visibility + cai_review Fix)
**Version**: v2.15.0 -> v2.16.0
**PTH**: 2B8D

## Summary
Added UAT tab to MetaPM dashboard with PTH search, fixed UAT title inheritance from handoff feature field, added uat_url field to requirements, and verified cai_review was already working correctly.

## What Was Built

1. **Migration 38** — `uat_url NVARCHAR(500) NULL` on `roadmap_requirements`
2. **UAT Tab** — 🧪 UAT button in dashboard nav; table with PTH search, project filter, status filter, clickable Open links
3. **UAT title inheritance** — `render_uat_html()` accepts `feature_title` from handoff title/task
4. **PTH extraction** — `/api/uat/pages` JOINs with mcp_handoffs, extracts PTH from title via regex
5. **uat_url in requirements** — RequirementResponse includes uat_url, dashboard shows [Run UAT →] button
6. **mcp.py auto-gen** — passes feature_title from handoff to render_uat_html

## Files Modified
- `app/core/config.py` — VERSION 2.16.0
- `app/core/migrations.py` — Migration 38 (uat_url column)
- `app/api/uat_gen.py` — feature_title in generate, JOIN + PTH in list_uat_pages
- `app/api/roadmap.py` — uat_url in list/get requirement queries + responses
- `app/api/mcp.py` — feature_title in auto-gen render_uat_html call
- `app/services/uat_generator.py` — feature_title parameter in render_uat_html
- `app/schemas/roadmap.py` — uat_url field on RequirementResponse
- `static/dashboard.html` — UAT tab (button, panel, search, filters, table), [Run UAT →] button on requirement rows

## Canary Results
- CANARY 1 — total UAT pages: 5
- CANARY 2 — PTH values found: ['2C5F']
- CANARY 3 — cai_review uat_id returned: DB08A794-A206-461B-9360-93E6A12EB245
- CANARY 4 — UAT tab in nav HTML: found (🧪 UAT)

## MetaPM State
- MP-060 (UAT Tab): cc_complete (5F38)
- Revision: metapm-v2-00165-n95

## Deviations
- cai_review was NOT broken — Phase 0 confirmed it returns 404 only on fake handoff_id, accepts fine with real ID. No fix needed.
- Only 1/5 UAT pages has PTH in title (older pages generated before title inheritance fix)
- Auto-walk to uat_ready on generate (Fix A from sprint prompt) not implemented — lower priority per intent boundaries
