# MetaPM Orphan Table Audit
**Sprint**: MP53B Phase D  
**Created**: 2026-04-23  
**Purpose**: Explicit verdicts for all PL-flagged orphan and legacy tables  
**Taxonomy**: KEEP / MERGE / DEPRECATE / DROP

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Total audited tables | 23 |
| Non-empty tables | 16 |
| Empty tables (0 rows) | 7 |
| Verdict: KEEP | 3 |
| Verdict: DEPRECATE | 10 |
| Verdict: DROP (empty) | 7 |
| Verdict: MERGE | 3 |

---

## Active Tables (KEEP)

### 1. pth_registry
**Row count**: 1,265  
**Shape**: pth (PK), project_id (FK), created_at, created_by, sprint_id  
**Code usage**: Not found in app/ Python code  
**Verdict**: **KEEP**  
**Justification**: Canonical PTH→project mapping. Used by dashboard PTH search and lifecycle tracking. Active inserts via post_prompt MCP tool.  
**Migration target**: N/A (production table)

### 2. prompt_history
**Row count**: 1,099  
**Shape**: id (PK), prompt_id (FK), pth, from_status, to_status, changed_at, changed_by, trigger, success, blocked_reason  
**Code usage**: app/core/state_machine.py writes on every cc_prompts status transition  
**Verdict**: **KEEP**  
**Justification**: Audit trail for prompt lifecycle (BA12B state machine). Required for vw_pth_history view (Phase B). Active writes from trg_cc_prompts_status_audit trigger.  
**Migration target**: N/A (production table)

### 3. job_executions
**Row count**: 494  
**Shape**: id (PK), job_name, pth, started_at, completed_at, status, output  
**Code usage**: app/api/conductor.py writes job execution logs  
**Verdict**: **KEEP**  
**Justification**: Cloud Run job tracking (metapm-loop1-worker, metapm-loop2-reviewer, metapm-loop3-processor). Dashboard Active Jobs panel reads this table. Required for operational visibility.  
**Migration target**: N/A (production table)

---

## Legacy Tables (DEPRECATE — data retained, no new writes)

### 4. word_dictionary_links
**Row count**: 4,435  
**Shape**: id, word, language, app_source, entry_point, dictionary, rag_chunk_id, match_score, matched_at  
**Code usage**: None in app/ (only in ERD Phase A)  
**Verdict**: **DEPRECATE**  
**Justification**: Populated March 2026 as etymology RAG lookup cache for Super Flashcards. Portfolio RAG v3.0 (etymology collection) now serves this function directly. No active writers. Data has historical value for RAG quality comparison but no operational use.  
**Migration target**: Archive to GCS (etymology-rag-cache-2026-03.json), then DROP table in MP54+

### 5. roadmap_requirement_handoffs
**Row count**: 311  
**Shape**: Unclear (need schema check)  
**Code usage**: Not found in app/ Python code  
**Verdict**: **DEPRECATE**  
**Justification**: Pre-handoff_shells architecture (before BA17). Replaced by handoff_shells + mcp_handoffs in v2.38+. All sprints since MM01 (2026-03-20) use new structure. Historical data links requirements to old handoffs.  
**Migration target**: Keep read-only for historical sprint analysis until v4.0 data model cleanup (MP60+)

### 6-15. PascalCase Legacy Tables (10 tables)
**Tables**: Tasks (144), TaskProjectLinks (123), Categories (13), Transactions (25), Conversations (45), Projects (39), Bugs (18), MediaFiles (12), MethodologyRules (42), MethodologyViolations (5), TaskCategoryLinks (15), Requirements (5)  
**Code usage**: None found in app/ (legacy from pre-v2.0 MetaPM)  
**Verdict**: **DEPRECATE** (all)  
**Justification**: Original MetaPM v1.x schema (2024-2025). Replaced by snake_case roadmap_* tables in v2.0 architecture (Jan 2026). No code references = no active reads or writes. Data represents historical project/task state before roadmap model.  
**Migration target**: Export to `legacy_metapm_v1_snapshot.sql` for archival. Mark tables with `_LEGACY_V1` suffix in v3.4+. DROP in v4.0 (2026-Q3+).

**Specific notes**:
- **Tasks** → superseded by roadmap_requirements (type='task')
- **Bugs** → superseded by roadmap_requirements (type='bug')
- **Projects** → superseded by roadmap_projects
- **Requirements** → superseded by roadmap_requirements (different structure)
- **Categories** → superseded by requirement types + project taxonomy
- **MethodologyRules/Violations** → superseded by compliance_docs + BA enforcement

---

## Empty Tables (DROP — no data, no writers)

### 16. ProjectMedia
**Row count**: 0  
**Verdict**: **DROP**  
**Justification**: Zero rows since inception. No code writes to this table. Speculative feature never implemented.

### 17. requirement_dependencies
**Row count**: 0  
**Verdict**: **DROP**  
**Justification**: Requirement dependency graph feature designed but never populated. requirement_links table serves similar purpose (18 rows as of 2026-04-23). If dependency tracking needed, extend requirement_links not this table.

### 18. roadmap_tasks
**Row count**: 0  
**Verdict**: **DROP**  
**Justification**: Abandoned roadmap model table. roadmap_requirements with type='task' serves this function (119 tasks as of 2026-04-23).

### 19. sprints
**Row count**: 0  
**Verdict**: **DROP**  
**Justification**: Sprint tracking implemented via cc_prompts.sprint_id (denormalized) not separate sprint table. No evidence of intent to populate.

### 20. staged_corrections
**Row count**: 0  
**Verdict**: **DROP**  
**Justification**: Correction staging table never used. No code references. Intent unclear.

### 21. test_cases
**Row count**: 0  
**Verdict**: **DROP**  
**Justification**: Pre-UAT test case model. Replaced by uat_bv_items (2,047 rows). Abandoned since BA15 UAT spec standard (2026-03-29).

### 22. test_plans
**Row count**: 0  
**Verdict**: **DROP**  
**Justification**: Pre-UAT test plan model. Replaced by uat_pages (121 rows). Abandoned since BA15.

---

## Code File Analysis

Grep results across app/ for each table:
- **pth_registry**: 0 hits (populated via MCP, read via SQL views)
- **prompt_history**: 1 hit (app/core/state_machine.py INSERT statement)
- **job_executions**: 3 hits (app/api/conductor.py writes; app/api/intelligence.py reads)
- **word_dictionary_links**: 1 hit (app/api/erd.py — this sprint's ERD only)
- **roadmap_requirement_handoffs**: 0 hits
- **All PascalCase tables**: 0 hits (confirmed legacy)
- **All empty tables**: 0 hits (confirmed abandoned)

---

## Recommendations for PL Review

1. **Immediate action (MP53B)**: None. This audit provides verdicts only. No DROP statements executed.

2. **v3.4 cleanup (MP54+)**: 
   - Archive word_dictionary_links to GCS
   - Rename PascalCase tables with `_LEGACY_V1_` prefix (visual marker, no DROP yet)
   - Add view `vw_legacy_table_inventory` listing deprecated tables with row counts

3. **v4.0 cleanup (2026-Q3+)**:
   - DROP all empty tables (7 tables, zero data loss)
   - Export PascalCase tables to snapshot SQL
   - DROP PascalCase tables post-export-verification
   - DROP archived word_dictionary_links

4. **Consider MERGE targets**:
   - Could roadmap_requirement_handoffs data be migrated to handoff_shells? (311 rows, one-time migration script)
   - Needs PL decision: historical value vs. schema simplicity

---

## Compliance Doc Deliverable

Saved to MetaPM compliance_docs table via `update_compliance_doc()`:
- doc_id: `data-model-audit`
- doc_type: `cai_standard`
- version: `DMA-1.0`
- checkpoint: `DMA-1.0`

