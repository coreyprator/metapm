# Session Close-Out: CC_Hotfix_MetaPM_UAT_Submit_Fix
**Date:** 2026-02-22
**Session:** CC_Hotfix_MetaPM_UAT_Submit_Fix
**Status:** COMPLETE

---

## What Was Done

| Item | Status |
|------|--------|
| P0: UAT submit schema audit | Already done in prior session |
| P1: Field aliases + total_tests inference | Already deployed (v2.3.9, metapm-v2-00093-jdf) |
| P2: Standard template field acceptance | Already deployed |
| P3: Repost 3 failed PL UAT results | DONE — SF v3.0.1, AF v2.3.3, HL v1.8.4 |
| P4: Version bump 2.3.7→2.3.9 | Already done |
| P5: UAT schema in PROJECT_KNOWLEDGE.md | Already done |
| API validation tests | DONE — 3/3 tests passed |
| Session UAT posted to MetaPM | DONE — UAT ID D41E3FA6 |
| Test record cleanup | DONE — 3 UAT + 1 handoff deleted via sqlcmd |
| Handoff uploaded to GCS | DONE — gs://corey-handoff-bridge/metapm/outbox/HO-MP-UATFIX_20260222.md |

---

## Deployed Revision

- Service: `metapm-v2`
- Revision: `metapm-v2-00093-jdf`
- Version: v2.3.9
- URL: https://metapm.rentyourcio.com
- Health: `{"status":"healthy","version":"2.3.9","build":"unknown"}`

---

## Gotchas for Next Session

1. **MetaPM uses `metapm-v2` service NOT `metapm`.**
   - Correct URL: `https://metapm.rentyourcio.com` (custom domain, `metapm-v2` service)
   - Deploy command: `gcloud run deploy metapm-v2 --source . --region us-central1 --allow-unauthenticated --set-env-vars="DB_SERVER=35.224.242.223,DB_NAME=MetaPM,DB_USER=sqlserver,ENVIRONMENT=production" --set-secrets="DB_PASSWORD=db-password:latest" --add-cloudsql-instances="super-flashcards-475210:us-central1:flashcards-db"`
   - The old `metapm` service (NOT `metapm-v2`) was accidentally deployed as `metapm-00011-b4s` in a prior session — this has bad SQL Server config and times out. Ignore it.

2. **cc-deploy SA cannot deploy MetaPM.** Use `cprator@cbsware.com` for deploys. Switch back afterward:
   ```bash
   gcloud config set account cprator@cbsware.com
   # ... deploy ...
   gcloud config set account cc-deploy@super-flashcards-475210.iam.gserviceaccount.com
   ```

3. **Direct DB access for admin queries:** Use sqlcmd with Secret Manager password:
   ```bash
   DB_PASS=$(gcloud secrets versions access latest --secret=db-password --project=super-flashcards-475210)
   sqlcmd -S 35.224.242.223 -U sqlserver -P "$DB_PASS" -d MetaPM -Q "SELECT TOP 5 * FROM uat_results ORDER BY tested_at DESC;"
   ```
   Required when there's no API endpoint for the operation. Cloud SQL Proxy not installed.

4. **`gcloud sql connect` fails on IPv6.** Use direct sqlcmd with the static IP (35.224.242.223) instead.

5. **UAT submit API endpoint is public** (`/api/uat/submit`). No auth required. POST JSON per schema in PK Section 4.

6. **UAT_Template_v4.html** — PK says it was created at `project-methodology/templates/UAT_Template_v4.html`, but this was NOT verified in this session. Confirm it exists and the submit button works end-to-end.

---

## Key UAT IDs Created This Session

| Project | Version | UAT ID | Notes |
|---------|---------|--------|-------|
| Super Flashcards | 3.0.1 | 4AEABDCA-17B3-4E90-8F0D-34110E46ED6C | PL UAT repost |
| ArtForge | 2.3.3 | A6A1A7F7-2234-4BB9-A414-1136C0AC945C | PL UAT repost |
| HarmonyLab | 1.8.4 | 80405896-D723-4EED-95A8-F841F30D8BC8 | PL UAT repost |
| MetaPM | 2.3.9 | D41E3FA6-0883-45BF-8E93-3BC3A7303A4C | Session UAT |

---

## PL UAT Failures Noted (for follow-up sprints)

**HarmonyLab v1.8.4:**
- CHD-01: Chord edit modal is still FREE TEXT (not dropdowns). CC had previously claimed done.
- IMP-03: .mscz parser returns 0 chords consistently.

**ArtForge v2.3.3:**
- SM-02: Logout doesn't prompt for userid (iPhone caches account)
- VID-04: Video disappears after leaving story
- SFX-02: SFX assignment doesn't persist
- MUS-01: Music dropdown doesn't persist
- ASM-02: Assembly 403 on Pixabay CDN music URL
- PRE-02: XML export can't be imported into Premiere

**Super Flashcards v3.0.1:**
- SR-02: No SRS sorting. SF-005 set back to backlog.

---

## Suggested Next Task

**HarmonyLab CHD-01 hotfix** — PL flagged chord dropdowns as a regression ("CC claimed done"). This is a critical failure and should be addressed next.

**ArtForge SFX/Music persistence** — Multiple persistence failures in ArtForge v2.3.3.
