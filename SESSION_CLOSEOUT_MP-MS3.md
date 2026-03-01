# SESSION CLOSEOUT: MP-MS3 — WIP Lifecycle Tracking + Portfolio RAG Integration

## Sprint Summary
- **Sprint**: MP-MS3
- **Project**: MetaPM
- **Version**: 2.6.0 → 2.7.0
- **Date**: 2026-02-28
- **Status**: Complete

## Deliverables

### Phase 1: Status Migration + History Table + WIP Dashboard
- **Migration 23**: Status data migration (in_progress→executing, done→closed) for 135 items
- **Migration 24**: Added WIP tracking fields (prompt_url, portfolio_rag_url, status_updated_at)
- **Migration 25**: Created requirement_history table + trg_requirement_history auto-tracking trigger
- **Dashboard**: WIP nav button, pipeline-order status grouping, filter groupings, new status CSS colors
- **Fix**: DROP CHECK constraint before data migration (constraint rejected new values during UPDATE)

### Phase 2: Status Transition API + History Timeline
- `PATCH /api/roadmap/requirements/{id}/status` — validated status transitions
- `PATCH /api/roadmap/requirements/status/batch` — bulk status updates
- `GET /api/roadmap/requirements/{id}/history` — chronological history
- `GET /api/roadmap/wip` — pipeline counts + active sprints
- Dashboard: history timeline in drawer

### Phase 3: Document Attachments + CC Prompt Approval
- **Migration 26**: requirement_attachments table
- **Migration 27**: cc_prompts table (NVARCHAR(36) FK to roadmap_projects)
- Attachment endpoints: POST/GET `/api/roadmap/requirements/{id}/attachments` (GCS upload)
- Prompt endpoints: POST/GET `/api/roadmap/prompts`, approve, handoff (raw markdown)
- Dashboard: attachment upload widget, prompt review/approve in drawer

### Phase 4: Portfolio RAG Integration
- **Migration 28**: requirement_links table
- RAG proxy: `/api/rag/query`, `/api/rag/documents`, `/api/rag/latest/{type}`, `/api/rag/checkpoints`
- Link endpoints: POST/GET `/api/roadmap/requirements/{id}/links`
- New config: PORTFOLIO_RAG_URL

### Phase 5: Deterministic Lesson Routing
- `POST /api/lessons/apply` — reads GitHub file, finds section, inserts lesson, commits via API
- `GET /api/lessons/recent` — last 20 applied lessons
- Safety: duplicate detection, section validation, known repo list
- GitHub token from Secret Manager (portfolio-rag-github-token)

### Phase 6: UAT Checkpoint Enforcement
- UATDirectSubmit accepts uat_checkpoint + uat_verification_hash
- Server-side sha256 verification: `sha256(checkpoint + project + version + total_tests)`
- Returns checkpoint_verified: true/false in response
- Backward compatible — fields are optional

## Pipeline Status Values (10)
backlog → draft → prompt_ready → approved → executing → handoff → uat → closed
(Side states: needs_fixes, deferred)

## New Tables
1. requirement_history (migration 25)
2. requirement_attachments (migration 26)
3. cc_prompts (migration 27)
4. requirement_links (migration 28)

## New Files
- `app/api/rag.py` — Portfolio RAG proxy router
- `app/api/lessons.py` — Deterministic lesson routing router

## Git Commits
1. `01fd128` — feat: MP-MS3 Phase 1 (status migration + WIP dashboard)
2. `ea10a14` — fix: drop CHECK constraint before status migration
3. `bec7a1f` — feat: MP-MS3 Phase 2 (status transition API + history)
4. `69d154f` — feat: MP-MS3 Phase 3 (attachments + CC prompt approval)
5. `0e25e1b` — feat: MP-MS3 Phase 4 (RAG proxy + requirement links)
6. `265de9d` — feat: MP-MS3 Phase 5 (lesson routing via GitHub API)
7. `dd50412` — feat: MP-MS3 Phase 6 (UAT checkpoint verification)
8. Final commit — feat: MP-MS3 Phase 7 (version bump v2.7.0)

## Verification
| # | Check | Result |
|---|-------|--------|
| 1 | Status migration | 135 items, no old values (backlog:36, closed:86, executing:13) |
| 2 | WIP nav button | Groups by status in pipeline order, excludes closed+deferred |
| 3 | Status transition | PATCH validates transitions, records history |
| 4 | History timeline | Item expand shows status change log |
| 5 | WIP summary | /api/roadmap/wip returns pipeline counts |
| 6 | Attachments | Upload/list endpoints functional |
| 7 | Prompt approval | Create → review → approve → handoff URL works |
| 8 | RAG proxy | /api/rag/query returns search results, /api/rag/latest/bootstrap returns v1.4.4 |
| 9 | Lesson apply | POST endpoint deployed with safety rules |
| 10 | UAT checkpoint | Hash verification field added, backward compatible |
| 11 | /health | v2.7.0 |

## Lessons Learned
1. **SQL CHECK constraints must be dropped BEFORE data migration** — UPDATE with new values fails against old constraint
2. **NVARCHAR(36) FKs** — all MetaPM IDs are NVARCHAR(36), not INT. FKs must match.
3. **Secret Manager token needs .strip()** — whitespace in PAT causes auth failures
