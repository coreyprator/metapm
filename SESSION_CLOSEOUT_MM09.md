# Session Closeout — MM09: Not Done Filter Fix + Governance Cloud SQL Migration
Date: 2026-03-21
Version: 2.37.7 → 2.37.8
Commit: 5a063ed
Handoff ID: 76BF048B-A40A-4AF7-A52C-59EBC24A08E7
UAT URL: https://metapm.rentyourcio.com/uat/4DC78254-1906-475D-8BB3-7147474694C0

## Sprint
PTH: MM09 | MP-MM09

## Deliverables

### Fix 1 — dashboard.html: Not Done activeItems filter
- Added `not_done` guard before else-if chain at lines 1154-1162 in `renderByProject`
- `activeItems` already filtered to non-closed/non-backlog items — guard is a no-op, prevents false-empty
- Fixes project card active count showing 0 when Not Done selected in Dashboard view

### Fix 2 — governance.py: Cloud SQL migration
- Replaced `_read_state()` / `_write_state()` file I/O with `execute_query()` on `governance` table
- `DEFAULT_STATE` updated to `BOOT-1.5.18-BA07` (current canonical checkpoint)
- Removed `json`, `Path` imports; added `database` import
- Checkpoint now survives redeploys — no more stale `BOOT-1.5.10-Q7A2` mismatch warnings

### Migration 52 — governance table
- `CREATE TABLE governance (id INT IDENTITY PK, checkpoint, bootstrap_version, updated_at, source)`
- Seeded on first run: `BOOT-1.5.18-BA07 | 1.5.18 | 2026-03-21`
- Idempotent — skips if table already exists

### config.py: VERSION 2.37.7 → 2.37.8

## Files Changed
- `static/dashboard.html` — not_done guard in activeItems filter
- `app/api/governance.py` — file I/O replaced with Cloud SQL
- `app/core/migrations.py` — Migration 52 governance table + seed
- `app/core/config.py` — VERSION 2.37.8

## Canaries
- C1: GET /health → version: 2.37.8 ✅
- C2: GET /api/governance/bootstrap-checkpoint → checkpoint: BOOT-1.5.18-BA07, bootstrap_version: 1.5.18 ✅
- C3: GET /api/roadmap/requirements?status=not_done → count: 115 ✅
- C4: governance checkpoint from DB after fresh deploy: BOOT-1.5.18-BA07 (not stale file default) ✅
- C5: curl dashboard.html | grep not_done → 4 occurrences ✅

## Requirement
- MP-MM09: cc_complete (ECA6) ✅
