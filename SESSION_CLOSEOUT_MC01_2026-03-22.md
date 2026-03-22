# Session Closeout — MC01: Compliance Documents in SQL + MCP
Date: 2026-03-22
Version: 2.38.2 → 2.38.3
Commits: a9dcb4d (feat: Migration 56 + 3 MCP tools), 0528795 (fix: [checkpoint] reserved keyword)
Handoff ID: 08A92133-75AA-46EB-BF0B-3327CC6EDAA3
UAT URL: https://metapm.rentyourcio.com/uat/C9C7945D-057B-4F40-AC29-94BA56F1F9AF

## Sprint
PTH: MC01

## Deliverables

### Fix 1 — compliance_docs table (Migration 56)
- `app/core/migrations.py` — Migration 56:
  - Creates `compliance_docs` table:
    `id NVARCHAR(50) PK, doc_type, project_code, content_md NVARCHAR(MAX), version, [checkpoint], updated_at, updated_by`
  - Index on `doc_type`
  - Idempotent (TABLE_NAME check before CREATE)
  - Note: `checkpoint` is a SQL Server reserved keyword — quoted as `[checkpoint]` in all DDL/DML

### Fix 2 — 3 MCP Tools
- `app/api/mcp_tools.py` — 3 new tools added to TOOLS + TOOL_HANDLERS:
  - `get_compliance_doc(doc_id)` — returns full row including content_md + content_length
  - `update_compliance_doc(doc_id, content_md, version, checkpoint, doc_type?, project_code?, updated_by?)` — UPSERT: INSERT if not exists, UPDATE if exists
  - `get_checkpoint(doc_id)` — returns checkpoint, version, updated_at, updated_by (no content)

### Fix 3 — governance.py bootstrap-checkpoint
- `app/api/governance.py` — `get_bootstrap_checkpoint()` now tries `compliance_docs` first:
  - `SELECT version, [checkpoint], updated_at FROM compliance_docs WHERE id = 'bootstrap'`
  - Returns `source="compliance_docs_table"` when found
  - Falls back to `governance` table if compliance_docs row missing

### Fix 4 — Seed script
- `scripts/seed_compliance_docs.py` — seeds 11 docs via MCP tools endpoint:
  - bootstrap (64005 chars), cai-outbound, cai-inbound
  - pk-metapm, pk-mp (alias), pk-sf, pk-artforge, pk-harmonylab, pk-etymython,
    pk-portfolio-rag, pk-personal-assistant, pk-project-methodology
  - efg PK.md missing — skipped (file does not exist)

## Canaries
- BV-01: get_compliance_doc("bootstrap") → version=BOOT-1.5.18-BA07, content_length=64005 ✅
- BV-02: get_compliance_doc("pk-mp") → id=pk-mp, content_length=108088 ✅
- BV-03: update_compliance_doc + immediate read → canary-test-marker present ✅
- BV-04: GET /api/governance/bootstrap-checkpoint → checkpoint=BOOT-1.5.18-BA07, source=compliance_docs_table ✅
- BV-05: GET /health → version: 2.38.3 ✅

## Bug Fix — SQL Reserved Keyword
- `checkpoint` is a SQL Server T-SQL statement keyword
- All DDL and DML referencing this column now uses `[checkpoint]` square-bracket quoting
- Fixed in both `migrations.py` (CREATE TABLE) and `mcp_tools.py` + `governance.py` (SELECT/UPDATE/INSERT)
- Two commits: feat (a9dcb4d) + fix (0528795)

## PL Actions Required
- BV-01: Open UAT page → confirm all 5 BVs show pass ✅
- BV-02: Confirm pk-mp and pk-metapm both return valid content via get_compliance_doc

## Notes
- pk-mp is an alias for pk-metapm (both seeded, id=pk-mp used in UAT spec BV-02)
- Seed script is idempotent: running it again updates all rows cleanly
- BV-03 canary test left pk-mp with "canary-test-marker" content — restored to real PK.md content after test
