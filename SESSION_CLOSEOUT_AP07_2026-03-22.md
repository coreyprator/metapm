# Session Closeout — AP07: Loop 3 — UAT Submit Triggers Auto-Processing
Date: 2026-03-22
Version: 2.38.3 → 2.38.4
MetaPM Commit: 0804c0d
project-methodology Commit: ddd4182
Handoff ID: (see below — posted via direct-submit)
UAT URL: https://metapm.rentyourcio.com/uat/F71DB9B5-F834-47E6-A795-5412C959C037

## Sprint
PTH: AP07

## Deliverables

### Fix 1 — loop3_processor.py
- `project-methodology/skills/auto-pickup/cloud/loop3_processor.py` — NEW
  - Args: `--spec-id`, `--handoff-id`, `--pth`
  - Rule-based assessment: all pass → pass, any fail → fail, pass+skip → conditional_pass
  - `post_review()`: calls `POST /mcp/reviews` with assessment + failed BV notes
  - `advance_requirements()`: PATCH spec's linked_requirements to uat_pass on pass/conditional_pass
  - `send_summary_email()`: Anthropic + Gmail MCP email to PL with pass/fail counts
  - `post_session_log()`: stores execution in session_logs table
- `project-methodology/skills/auto-pickup/cloud/Dockerfile` — updated to include loop3_processor.py

### Fix 2 — MetaPM Loop 3 trigger on UAT submit
- `app/api/uat_spec.py`:
  - SELECT updated to also fetch `pth` and `handoff_id` from uat_pages
  - After BV items saved and RAG sync: `asyncio.create_task(trigger_cloud_run_job_immediate("metapm-loop3-processor", args_override=[--spec-id=X, --handoff-id=Y, --pth=Z]))`
- `app/api/prompts.py`:
  - `trigger_cloud_run_job_immediate()` extended with `args_override: list = None`
  - When provided, uses args_override list directly in containerOverrides

### Fix 3 — Loop 2 review_id writeback (duplicate emails)
- `app/api/mcp.py` — `list_handoffs()` updated:
  - Was: `SELECT id, project, task, ... FROM mcp_handoffs`
  - Now: LEFT JOIN reviews + `r.id as review_id, r.assessment`
  - `HandoffResponse` now populated with review_id from JOIN
  - Loop 2 fallback sweep: `not h.get("review_id")` filter now works correctly
  - Root cause: list endpoint never included review_id → all handoffs appeared unreviewed every sweep

### Fix 4 — Cloud Run Job created
- `metapm-loop3-processor` created in us-central1 via `gcloud run jobs create`
- Image: `gcr.io/super-flashcards-475210/metapm-loops:latest` (rebuilt with loop3)
- Env: MCP_API_KEY, ANTHROPIC_API_KEY, PL_EMAIL
- max-retries=1, task-timeout=600s

## Canaries
- C1: `gcloud run jobs list` → metapm-loop3-processor present ✅
- C2: `GET /mcp/handoffs` → review_id field present in response ✅
- C3: `GET /health` → version=2.38.4 ✅
- BV-01/BV-02/BV-03: UAT BVs require PL live testing (Loop 3 trigger, email, Loop 2 dedup)

## PL Actions Required
- BV-01: Submit UAT results on any spec → check GCP Console Cloud Run Jobs for metapm-loop3-processor execution within 10s
- BV-02: Check email after UAT submit (up to 2 min) — expect email with PTH + pass/fail counts
- BV-03: Confirm Loop 2 no longer sends duplicate emails after this deploy

## Notes
- Loop 3 trigger is non-blocking (asyncio.create_task) — UAT submit returns immediately
- If loop3 Cloud Run trigger fails (e.g. metadata server unavailable), it logs warning and continues
- governance.py was modified externally to add REST endpoints for compliance_docs (list/get) — not part of AP07
