🔴 MetaPM - Fix UAT Submit Endpoint + Enter UAT Results
Time Stamp: 2026-02-13-09-00-00
__________________________________________________________________________________________

## Context

The UAT Submit button on all UAT templates is failing with HTTP 422:

```
{"detail":[{"type":"missing","loc":["body","results_text"],"msg":"Field required"}]}
```

**Root Cause:** The `/mcp/uat/submit` endpoint requires a `results_text` string field, but the UAT HTML templates send a `results` array of JSON objects. The endpoint schema doesn't match the template payload.

Additionally, two UATs have been completed manually and their results need to be entered into MetaPM.

## Task

### Part 1: Fix the UAT Submit Endpoint

Update `POST /mcp/uat/submit` to accept the payload format that UAT templates actually send:

The templates send:
```json
{
  "project": "ArtForge",
  "version": "Provider Fix HO-AF01",
  "status": "failed",
  "total_tests": 6,
  "passed": 3,
  "failed": 1,
  "blocked": 0,
  "results": [
    {"id": "AF01-01", "title": "...", "status": "passed", "note": "..."},
    {"id": "AF01-02", "title": "...", "status": "failed", "note": "..."}
  ],
  "notes": "General observations...",
  "submitted_at": "2026-02-13T14:14:37.101Z"
}
```

The endpoint currently requires `results_text` (a string). Fix by EITHER:
- Option A (preferred): Update the Pydantic schema to accept `results` as a list of objects AND `results_text` as optional (backward compatible)
- Option B: Accept both field names, convert array to formatted text internally

Also update the status enum to accept: `passed`, `failed`, `blocked`, `partial` (not just `passed`/`failed`).

Validate: `total_tests > 0` and `passed + failed + blocked <= total_tests`.

Test the fix by calling the endpoint with the exact payload above and confirming 200 OK.

### Part 2: Enter ArtForge UAT Results

Manually submit these results to MetaPM (via API or direct DB insert):

```
Project: ArtForge
Version: Provider Fix HO-AF01
Date: 2026-02-13
Status: FAILED (3 passed, 1 failed)
Tester: Corey

Results:
  PASS  AF01-01: Provider dropdown exists on collection
        Note: Confirmed all providers were working. Images created across all providers.
  PASS  AF01-02: Save provider selection
        Note: Images were created across all providers. All selected styles were generated.
  PASS  AF01-03: Provider persists after reload
        Note: All images for all styles and providers were shown after reload.
  FAIL  AF01-04: Change provider and re-save
        Note: Generate Images button hangs at "Generated 15 of 147 images (10%)".
              Recommend removing button for now and designing edit workflow later. Low priority.

UAT Submit Tests:
  FAIL  SUB-01: Submit sends actual results — HTTP 422 (results_text field mismatch)
  FAIL  SUB-02: No HTTP errors on submit — Same 422 error

General Notes: Copy button works. Submit button broken due to schema mismatch.
```

### Part 3: Enter Etymython UAT Results

```
Project: Etymython
Version: Unicode Fix HO-EM02
Date: 2026-02-13
Status: FAILED (3 passed, 4 failed)
Tester: Corey

Results:
  FAIL  EM02-01: Ouranos — Greek text renders correctly
        Note: Apollo page shows "?p?????" — question marks replacing Greek characters.
              Verb "?p????µ?" also corrupted.
  FAIL  EM02-02: Dionysus — Greek text renders correctly
        Note: Fun Facts section is now MISSING from the page entirely.
              Etymology shows partial corruption: "???? (Dios)" and "??sa (nusa)".
  FAIL  EM02-03: Odysseus — Greek text renders correctly
        Note: Shows "?d???µa?" instead of proper Greek verb. Corruption persists.
  FAIL  EM02-04: Rhea — Greek text renders correctly
        Note: Name renders correctly (Ῥέα) but etymology shows "???" and "??d???"
              with Latin-1 mojibake (rhéo shows as "rhÃ©o").
  PASS  EM02-05: Zeus — Greek text still correct
  PASS  EM02-06: Athena — Greek text still correct
  PASS  EM02-07: Family tree graph loads without errors

UAT Submit Tests:
  FAIL  SUB-01: Submit sends actual results — HTTP 422 (results_text field mismatch)
  FAIL  SUB-02: No HTTP errors on submit — Same 422 error

General Notes:
  - Some content cleaned up but Unicode corruption persists on multiple figures.
  - Need comprehensive query to identify ALL bad characters across ALL figures.
  - Recurring defect: UI section expand/collapse state does not persist between
    card navigation or page reloads. If user expands Cognates on Zeus, navigating
    to Hera collapses it. This has been reported multiple times.
```

### Part 4: Verify Results Are Stored

After entering both UAT results, query MetaPM to confirm they're stored:

```
GET /mcp/handoffs/dashboard?limit=5
```

Report the handoff IDs and confirm both ArtForge and Etymython UAT results are visible.

## Deliverable Checklist

- [ ] UAT submit endpoint accepts `results` array (not just `results_text`)
- [ ] Status enum includes `passed`, `failed`, `blocked`, `partial`
- [ ] Endpoint validates total_tests > 0
- [ ] Test call with ArtForge payload returns 200 OK
- [ ] ArtForge UAT results entered in MetaPM with correct pass/fail counts
- [ ] Etymython UAT results entered in MetaPM with correct pass/fail counts
- [ ] Both results visible via dashboard query
- [ ] Fix deployed to metapm-v2
- [ ] Completion report follows 7-section template
- [ ] Handoff uploaded to GCS

## Rules

- Deploy target is `metapm-v2` (NOT `metapm`).
- Read CLAUDE.md first.
- The endpoint fix must be backward compatible — don't break any existing callers that send `results_text`.
- Include the actual curl commands and responses in the completion report.

__________________________________________________________________________________________
CAI REVIEW: Required
(Conductor marks status PENDING-REVIEW, not COMPLETE. Task remains open until CAI confirms.)

CAI CHECKLIST (for your response):
□ Assign ID (HO-XXXX format)
□ Create handoff doc if code/special chars needed
□ CC prompt must be clean (pasteable, no code fences for prompt itself)
□ Include Handoff Bridge link if doc created
□ List files for download
□ Include CC deliverables template in prompt

CC DELIVERABLES (include in CC prompt):
Your deliverables are:
- ID: HO-U9V1
- Status: COMPLETE / PARTIAL / BLOCKED / PENDING-REVIEW
- Handoff URL: Full GCS path
- Summary table: Project, Task, Status, Commit, Handoff URL
- Garbage collect: Delete processed handoff from inbox
- Git: Commit with ID in message

REWORK CONVENTION:
If this is a rework of a prior handoff, use suffix -R1, -R2, etc.
Original handoff stays in GCS. Rework is a new file with updated timestamp.
