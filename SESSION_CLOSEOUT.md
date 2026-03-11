# SESSION CLOSEOUT — MP-LESSON-INBOX-001
**Date**: 2026-03-10
**Sprint**: MP-LESSON-INBOX-001 (Lessons API: Field Validation + CRUD + Response Enhancement)
**Version**: v2.17.0 -> v2.18.0
**PTH**: C9F1

## Summary
Added Pydantic enum validation to lessons POST, soft delete (DELETE endpoint + deleted column), expanded PATCH to support all editable fields, and added edit/delete UI controls in dashboard lessons tab.

## What Was Built

1. **Migration 39** — `deleted BIT DEFAULT 0` on lessons_learned + expanded CHECK constraints
2. **Pydantic enums** — LessonCategory, LessonTarget, LessonBy, LessonStatus replace manual validation
3. **Field aliases** — `text`↔`lesson`, `by`↔`proposed_by` for backward compat
4. **POST returns 201** — includes `id` (LL-NNN) and `status` in response
5. **DELETE /api/lessons/{id}** — soft delete, excluded from all list queries
6. **PATCH expanded** — now supports category, target, project, proposed_by, source_sprint
7. **Dashboard UI** — Edit/Delete buttons on lesson cards, inline edit form with enum dropdowns
8. **RequirementUpdate schema** — added uat_url field for closeout gate

## Files Modified
- `app/api/lessons.py` — enums, aliases, DELETE endpoint, expanded PATCH, soft-delete filters
- `app/core/config.py` — VERSION 2.18.0
- `app/core/migrations.py` — Migration 39
- `app/schemas/roadmap.py` — uat_url in RequirementUpdate
- `app/api/roadmap.py` — uat_url in PUT handler
- `static/dashboard.html` — edit/delete controls, expanded filter dropdowns
- `PROJECT_KNOWLEDGE.md` — sprint update

## Canary Results
- CANARY 1 — POST missing fields → 422 with field-level errors: PASS
- CANARY 2 — POST valid → LL-056, status: draft: PASS
- CANARY 3 — DELETE soft-deletes, excluded from list: PASS (HTTP:200)
- CANARY 4 — PATCH updates source_sprint field: PASS (HTTP:200)

## MetaPM State
- MP-061: cc_complete (EB65)
- Revision: metapm-v2-00173-dk2
- Handoff ID: 1C6C5379-CDA1-4122-9E78-7BFB1CB2E345
- UAT URL: https://metapm.rentyourcio.com/uat/EDD507F3-D842-4F71-9093-701726ED87BD
