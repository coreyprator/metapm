# Session Closeout — AP08: Loop 2/3 Final Fixes + AutoHotkey + Active Jobs PTH
Date: 2026-03-22
Version: 2.38.5 → 2.38.6
MetaPM Commit: aa19378
project-methodology Commit: e445873
Handoff ID: (see below — posted via direct-submit)
UAT URL: https://metapm.rentyourcio.com/uat/AA6BCB56-F49E-408D-8028-4A76E5168B01

## Sprint
PTH: AP08

## Deliverables

### Fix 1 — Loop 2 email PTH and UAT URL (root cause fix)
- `app/schemas/mcp.py`: Added `pth: Optional[str]` and `uat_spec_id: Optional[str]` to `HandoffResponse`
- `app/api/mcp.py` — `list_handoffs()` updated:
  - SELECT now includes `h.pth`
  - Added `LEFT JOIN uat_pages u ON u.handoff_id = h.id` to get `u.id as uat_spec_id`
  - `HandoffResponse` populated with both new fields
  - Root cause: list endpoint SELECT never included `h.pth` or uat_pages JOIN → always None → email showed N/A + /uat/None

### Fix 2 — Loop 2 fallback sweep: server-side `?unreviewed=true` filter
- `app/api/mcp.py` — `list_handoffs()`:
  - New param: `unreviewed: bool = Query(False)`
  - When True: `AND r.id IS NULL` appended to WHERE (LEFT JOIN reviews already present from AP07)
  - Count query uses LEFT JOIN with `unreviewed_sql` too
- `project-methodology/skills/auto-pickup/cloud/loop2_reviewer.py`:
  - `get_pending_handoffs()` now calls `GET /mcp/handoffs?unreviewed=true`
  - Removed client-side `[h for h in handoffs if not h.get("review_id")]` filter (server does it)

### Fix 3 — Loop 3: remove email, add fix prompt authoring
- `project-methodology/skills/auto-pickup/cloud/loop3_processor.py`:
  - Removed `send_summary_email()` function and call
  - Added `post_fix_prompt(pth, analysis, spec_id)`:
    - Only fires when `analysis['assessment'] == 'fail'`
    - Calls Anthropic claude-opus-4-6 to write a fix prompt for the failed BVs
    - POSTs to `POST /api/prompts` as status=draft with PTH=`{PTH}F` (e.g. AP08F)
    - Payload: `pth`, `sprint_id`, `content_md`, `created_by=loop3`, `enforcement_bypass=data_only_sprint`

### Fix 4 — AutoHotkey + Copy PTH button
- `project-methodology/tools/paste_pth_to_cc.ahk` — NEW
  - Win+Shift+P hotkey
  - Reads clipboard, validates PTH format (regex `^[A-Z]{1,3}\d{1,4}[A-Z]?$`)
  - Activates VS Code window (`ahk_exe Code.exe`)
  - Types `PTH: {clipboard}` into active editor
- `static/prompt-viewer.html`:
  - PTH badge now has `cursor:pointer` + `onclick="copyPTH(...)"` + tooltip
  - Added `copyPTH()` function: copies PTH to clipboard, flashes "Copied!" on badge for 1.2s

### Fix 5 — Active Jobs panel: loop3 support + PTH extraction
- `app/api/prompts.py` — `trigger_cloud_run_job_immediate()`:
  - `job_type` detection now handles loop3: `"loop3"` if `"loop3"` in `job_name`
  - Extracts `effective_pth` from `args_override` list when `--pth=` arg present
  - Records correct `pth` and `job_type` in `job_executions` table for loop3 runs
- `app/api/prompts.py` — `get_jobs_status()`:
  - Added `metapm-loop3-processor` to jobs list
  - Key detection handles loop3: `"loop3"` if `"loop3"` in `job_name`
  - Error return now includes `"loop3": []`
- `static/dashboard.html`:
  - Loads `loop3 = data.loop3 || []`
  - Adds loop3 entries to `all` array with label `'Loop 3 (UAT)'`

### Fix 6 — UAT submit note
- `app/api/uat_spec.py` — `render_uat_page()`:
  - Added note below btn-row (only shown before submit):
    `⚡ Submitting fires Loop 3 automatically — requirements will be advanced within 2 minutes.`

### Docker image rebuild
- `gcr.io/super-flashcards-475210/metapm-loops:latest` rebuilt with updated loop2 + loop3

## Canaries
- C1: `GET /health` → version=2.38.6 ✅
- C2: `GET /mcp/handoffs?limit=1` → pth field=True, uat_spec_id field=True ✅
- C3: `GET /mcp/handoffs?unreviewed=true` → 5 handoffs returned, all review_id=None ✅
- C4: `GET /api/prompts/jobs/status` → loop3 key present, loop1=10, loop2=10, loop3=3 ✅
- C5: UAT submit note in source code ✅
- C6: copyPTH function in prompt-viewer.html ✅
- C7: paste_pth_to_cc.ahk exists ✅

## PL Actions Required
- BV-01: Trigger Loop 2 review on any handoff with PTH set → check email for PTH + UAT URL (not N/A)
- BV-02: Call `GET /mcp/handoffs?unreviewed=true` → all returned handoffs should have review_id=null
- BV-03: Submit UAT with one failing BV → wait 2 min → check GET /api/prompts for PTH=AP08F draft
- BV-04: Copy a PTH to clipboard, run AHK script, press Win+Shift+P in VS Code → "PTH: XXXX" typed
- BV-05: Submit UAT to trigger loop3 → Dashboard Active Jobs → Loop 3 (UAT) entry appears
- BV-06: Open any unsubmitted UAT page → note visible below Submit button about Loop 3

## Notes
- Phase 0-C audit confirmed: pth/uat_url were N/A because list endpoint SELECT never included h.pth or uat_pages JOIN
- AP07 LEFT JOIN reviews fix was correct — fallback duplicates were resolved; AP08 adds server-side filter for efficiency
- Loop 3 email removed by PL request — PL prefers dashboard visibility over email noise
- AHK script uses win+shift+p; validate PTH regex before sending to prevent garbage input
- version was already at 2.38.5 (EG05 sprint ran in between AP07 and AP08)
