# SESSION CLOSEOUT — MM12-DASHBOARD-FIX-001

## Session Identity
- **PTH**: C91D
- **Sprint**: MM12-DASHBOARD-FIX-001
- **Project**: MetaPM
- **Version**: v2.41.0 -> v2.42.0
- **Date**: 2026-03-24
- **Commit**: 8f5854b

## Requirements Delivered

### MM12-REQ-001 — Prompt detail markdown render on all statuses (FIXED)
- `static/prompt-viewer.html`: Removed `isDraft` ternary that showed raw textarea for draft status
- Now calls `buildCollapsibleContent()` for ALL statuses including draft/prompt_ready
- Draft prompts get rendered markdown + "Edit Source" toggle button to access textarea

### MM12-REQ-002 — Active Jobs STALE items (NO CHANGE NEEDED)
- Phase 0 confirmed STALE items already filtered: `all.filter(j => j.status !== 'stale')` at dashboard.html:3101
- Documented in PK.md

### MM12-REQ-003 — Needs Approval updated_at filter (FIXED)
- `app/api/prompts.py:457`: Changed `p.created_at` to `p.updated_at` in `days` filter
- `app/api/radar.py:55`: Changed `p.created_at` to `p.updated_at` in approve_prompts query
- Old seeds with recent activity no longer slip through the 14-day window

### MM12-REQ-004 — Morning Brief Cloud Scheduler (NO CHANGE NEEDED)
- Phase 0 confirmed: job is `personal-assistant-daily` at `0 13 * * *` America/Chicago = 8am CT
- No `personal-assistant-morning-brief` job exists — the job name differs from prompt assumption

## Files Changed
- `app/api/prompts.py` — days filter: created_at -> updated_at
- `app/api/radar.py` — approve_prompts query: created_at -> updated_at
- `app/core/config.py` — Version bump 2.41.0 -> 2.42.0
- `static/prompt-viewer.html` — Markdown render for all statuses + Edit Source toggle

## Canary Evidence
```
Health: {"status":"healthy","version":"2.42.0","build":"unknown"}
Scheduler: personal-assistant-daily  0 13 * * *  America/Chicago
Commit: 8f5854b
Deploy run: 23512605859 (success)
```

## Handoff
- Handoff ID: 85064F10-60D0-4F6D-AB94-8D05232B33BB
- UAT spec_id: FA9A9F27-D340-48FD-891C-1ED5A3BB68F3
- UAT URL: https://metapm.rentyourcio.com/uat/FA9A9F27-D340-48FD-891C-1ED5A3BB68F3
