# SESSION_CLOSEOUT — MP-MS4

**Sprint:** MP-MS4
**Project:** MetaPM
**Version:** v2.7.1 → v2.8.0
**Date:** 2026-03-02
**Cloud Run Revision:** metapm-v2-00130-wzl
**Deploy Service:** metapm-v2 (NOT metapm — see Phase 0 findings)

---

## Phase 0 Findings

### Attachment 409 Root Cause
CAI's sprint prompt diagnosed attachment uploads as causing 409 conflicts via code collisions with REQ-001 patterns. **Investigation revealed this was incorrect.** Attachments use auto-increment integer IDs with no code generation — they cannot collide with requirement codes. The only existing 409 in the codebase was in `update_requirement()` at roadmap.py:598, which correctly prevents duplicate codes on update. The actual gap was that `create_requirement()` lacked the same uniqueness check, so duplicate codes could be inserted on creation. Fix: added code uniqueness validation to `create_requirement()`.

### Cloud Run Service Name
Domain `metapm.rentyourcio.com` maps to Cloud Run service `metapm-v2`, NOT `metapm`. Three deploys were wasted targeting the wrong service before this was discovered via `gcloud beta run domain-mappings list`. Confirmed with PINEAPPLE canary test.

### Files Touched
- `app/api/roadmap.py` — MP-028 code uniqueness check
- `app/core/config.py` — version bump to 2.8.0
- `static/dashboard.html` — MP-027 prompt badge, MP-030 Active Prompts helper text/tooltip
- `project-methodology/templates/UAT_Template_v3.html` — MP-029 submit confirmation, MP-031 screenshot paste, MP-032 file attach

---

## Requirements

### MP-027 | Row-level prompt badge on prompt_ready items | DONE
- **Root cause:** `rowHtml()` rendered the prompt badge as a separate grid item (6th child in a 5-column grid), causing layout overflow and the badge to wrap off-screen.
- **Fix:** Moved badge inline with title text in the first grid column. Added `.has-prompt` CSS class with gold left border (`border-left: 3px solid #f0b429`).
- **File:** `static/dashboard.html`

### MP-028 | Attachment upload 409 conflict fix | DONE
- **Root cause:** See Phase 0 above. Not an attachment issue — `create_requirement()` lacked code uniqueness validation.
- **Fix:** Added pre-insert check: `SELECT id FROM roadmap_requirements WHERE project_id = ? AND code = ?`. Returns 409 with descriptive message if duplicate code found.
- **File:** `app/api/roadmap.py`

### MP-029 | Restore UAT submit confirmation link | DONE
- **Root cause:** Template had the link code but it was a single-line append easily missed. API does return `handoff_url`.
- **Fix:** Replaced simple link with prominent green-bordered confirmation box showing success message, clickable "View in MetaPM" link, and handoff ID.
- **File:** `project-methodology/templates/UAT_Template_v3.html`

### MP-030 | Active Prompts panel — tooltip and helper text | DONE
- **Fix:** Added helper text div below panel title: "Prompts ready to deliver to a CC session. Copy the CC Link and paste it into your CC prompt." Added tooltip to Copy CC Link button.
- **File:** `static/dashboard.html`

### MP-031 | UAT template — paste screenshot per test item | DONE
- **Fix:** Added paste zone (`contenteditable div`) per test item. Clipboard paste handler captures images, resizes to max 800px via canvas, stores as base64 in `mediaData` object. Thumbnail displayed inline. Included in POST payload as `screenshot` field per test item.
- **File:** `project-methodology/templates/UAT_Template_v3.html`

### MP-032 | UAT template — file attachment per test item | DONE
- **Fix:** Added file attach button per test item. File handler validates type (jpg, png, pdf, zip, txt) and size (5MB limit). Filename displayed inline. Included in POST payload as `attachment` object with filename, mimetype, data fields.
- **File:** `project-methodology/templates/UAT_Template_v3.html`

---

## Smoke Tests

### Health Check
```json
{"status":"healthy","version":"2.8.0","build":"unknown"}
```

### UAT Submit
```json
{"handoff_id":"...","handoff_url":"https://metapm.rentyourcio.com/handoffs.html#...","status":"submitted"}
```
Returns `handoff_url` correctly — MP-029 confirmation link has data to work with.

### Requirements API
Requirements endpoint responds correctly. Code uniqueness check active on create.

---

## Deferred Items / Anomalies

1. **Deploy account:** Used `cprator@cbsware.com` for Cloud Run deploy (cc-deploy SA lacks permission). Documented in PK.md.
2. **PINEAPPLE canary:** Used to verify deploys were hitting correct service. Added then removed from `app/main.py`. Final deploy (revision metapm-v2-00130-wzl) has no canary.
3. **Untracked sprint files:** MetaPM repo has ~40 untracked sprint prompt/UAT files accumulated over multiple sessions. Not committed — these are working documents, not source code.
