# SESSION_CLOSEOUT — EG07
**Date:** 2026-03-23
**Sprint:** EG07 — Compliance Docs Viewer + UAT Project Name Fix
**Version:** 2.38.7 → 2.38.8
**Handoff ID:** 9C4B56E1-9E34-4D77-8701-2CC6928BDAC5
**UAT URL:** https://metapm.rentyourcio.com/uat/CB366362-5956-4545-B919-38923EC07870
**Deploy URL:** https://metapm.rentyourcio.com
**Commit:** 05110d6

## Root Causes Found (Phase 0-C)

### BV-01 Root Cause
`loadDocLibrary()` was calling `https://portfolio-rag-57478301787.us-central1.run.app/api/pk-status` — the Portfolio RAG chunk index, not the compliance docs SQL table. `/api/compliance-docs` already existed and was correct.

### BV-02 Status
`/docs` standalone page already has correct client-side `formatTimestamp()` JS that formats ISO dates to `MM/DD/YYYY, HH:mm:ss`. No Python change needed.

### BV-03 Root Cause
`serve_uat_page` SELECT didn't include `project` column. When `spec_data` JSON was empty (HM12 spec created before spec_data field was populated), `render_spec_uat_page()` received `spec_data = {}` and displayed "Unknown" instead of "HarmonyLab".

## Fixes Applied

### Fix 1 — `static/dashboard.html`
- Rewrote `loadDocLibrary()` to call `/api/compliance-docs` (SQL table)
- Rows clickable → `/docs/{id}` in new tab
- Added `_fmtDocTs()` helper for timestamp display
- Updated panel title from "Document Library — Project Knowledge" to "Compliance Documents"

### Fix 3 — `app/api/uat_gen.py`
- Added `project` to initial page SELECT
- Added `project` to full_page SELECT (line 248)
- After parsing spec_data: inject `project` from uat_pages if spec_data lacks it
- Result: HM12 UAT gets `proj-hl` in spec_data → `_PROJECT_NAMES['proj-hl'] = 'HarmonyLab'`

## Canaries
- C1: `/api/compliance-docs` → bootstrap + 11 other entries ✅
- C2: `/docs` HTML contains `fetch('/api/compliance-docs')` ✅
- C3: `/docs/bootstrap` renders via `marked.parse(doc.content_md)` ✅
- C4: HM12 UAT → no ISE, auth gate (correct for cc_spec) ✅
- C5: version 2.38.8, dashboard grep → `compliance-docs` (no `pk-status`) ✅
