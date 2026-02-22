# Session Close-Out: 2026-02-22 Sprint HO-MP11 Audit+Cleanup

**Date**: 2026-02-22
**Sprint**: Audit + Cleanup + Build
**Handoff ID**: HO-MP11
**Version Deployed**: v2.3.7
**Revision**: metapm-v2-00090-vtn

---

## What Was Done

### Phase 1 — Audit
- Queried all 89 requirements across all projects (MetaPM, ArtForge, HarmonyLab, Etymython, and others)
- Found 20 in_progress items; verified each against production APIs
- Corrected 12 → done, 6 → backlog, 2 stayed as-is (one fixed in Phase 2, one left in_progress)
- Description integrity: 1 mismatch found (AF-011) — NOT reverted because current description is factually accurate

### Phase 2 — Cleanup
- Fixed `/api/handoffs` SQL ORDER BY error in `app/api/handoff_lifecycle.py`
  - Root cause: `ORDER BY` in subquery without `TOP/OFFSET` violates SQL Server rules
  - Fix: Moved `TOP {limit}` inline to base SELECT; removed subquery wrapper
- Created `tests/test_ui_smoke.py` — 9 production httpx smoke tests
  - Run with: `pytest tests/test_ui_smoke.py -v --noconftest`
  - --noconftest required: conftest.py imports app.main which calls run_migrations() at module load
- Updated CLAUDE.md pytest command to include `--noconftest`

### Phase 3 — Build
- Added `conditional_pass` to UATStatus enum in `app/schemas/mcp.py`
- Marked MP-007 as done in roadmap

---

## Files Changed

| File | Change |
|------|--------|
| `app/api/handoff_lifecycle.py` | Fixed handoffs SQL ORDER BY error |
| `app/schemas/mcp.py` | Added CONDITIONAL_PASS to UATStatus enum |
| `app/core/config.py` | VERSION 2.3.6 → 2.3.7 |
| `tests/test_ui_smoke.py` | New: 9 production smoke tests |
| `CLAUDE.md` | Updated pytest command to include --noconftest |
| `uat/HO-MP11_UAT.json` | UAT results (10 tests) |
| `handoffs/outbox/20260222_HO-MP11_audit-cleanup-sprint.md` | Full handoff with audit table |
| `handoffs/outbox/SESSION_CLOSEOUT_2026-02-22_MP11.md` | This file |
| `PROJECT_KNOWLEDGE.md` | Updated version, session history, requirement counts |

---

## State for Next Session

- **Current version**: v2.3.7
- **Current revision**: metapm-v2-00090-vtn
- **gcloud account**: cc-deploy@super-flashcards-475210.iam.gserviceaccount.com (active)
- **Requirement counts (MetaPM proj-mp after this sprint)**:
  - done: MP-003, MP-004, MP-005, MP-006, MP-007, MP-009 + prior done items
  - backlog: MP-001, MP-014 + prior backlog items + MP-029, MP-030, MP-031
  - in_progress: MP-021 (handoff/UAT visibility) — unchanged

---

## Gotchas for Next Session

1. **conftest.py**: `from app.main import app` triggers `run_migrations()` at import time — hangs without prod credentials. Always use `--noconftest` for smoke tests.
2. **audit_status_updates.py**: Left in repo root as untracked (no sensitive data). Can be deleted or .gitignore'd.
3. **AF-011 description mismatch**: Seed says "Runway Gen-3 only" — current is "provider-agnostic." PL should decide whether to update the seed.
4. **EM-012 IPA status**: Audio 68/70 done; IPA text field not visible in figure API schema — might be in a table not exposed by `/api/v1/figures`. Check Etymython schema.sql before the next EM session.

---

## Open Issues Carried Forward

1. **AF-015**: Battle of the Bands routes still live in ArtForge — needs a dedicated ArtForge sprint to remove
2. **HL-008**: 0 songs in HarmonyLab DB — needs MIDI file import session
3. **EM-012**: IPA text data incomplete — needs verification of what's in the DB
4. **MP-014**: Cross-project dependency links — not started, needs dedicated sprint
5. **MP-001**: GitHub Actions CI/CD — not started, needs dedicated sprint

---

## Definition of Done — Verified

- [x] Phase 1 audit complete: 20 items verified, 18 statuses corrected
- [x] Phase 2 cleanup: handoffs SQL fixed (9/9 smoke tests pass)
- [x] Phase 3 build: conditional_pass shipped in UATStatus enum
- [x] v2.3.7 health check passes
- [x] 9/9 smoke tests pass
- [x] Committed 87e81fc and pushed
- [x] Deployed metapm-v2-00090-vtn
- [x] UAT JSON uploaded to GCS
- [x] Handoff MD uploaded to GCS
- [x] SESSION_CLOSEOUT uploaded to GCS
- [x] PROJECT_KNOWLEDGE.md updated
- [x] gcloud switched back to cc-deploy
