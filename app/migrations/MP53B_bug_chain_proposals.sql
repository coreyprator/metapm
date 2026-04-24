-- MP53B Phase F: Bug Chain Proposal Views (Staging Only - No Writes)
-- Deductive seeding + Inductive expansion + Misclass detection + Unclassified residue
-- Created: 2026-04-23
--
-- CRITICAL: These are STAGING VIEWS for PL inspection. Zero writes to bug_chains or
-- roadmap_requirements chain columns in MP53B. MP53C executes writes post-PL-approval.

-- F.2: vw_bug_chain_proposals_seeded
-- Purpose: PL-validated chain seeds with expected_outcome + missing_signal
-- Hash components: failure_type:affected_module:symptom_category (3-tuple, deterministic)
--
-- Seeded chains (2 as of MP53B):
-- 1. BC-UAT-DROPDOWN (BUG-018, BUG-039, BUG-051, BUG-061, BUG-067, BUG-078, BUG-080, BUG-091)
--    Hash: broken_interaction_bug:app/api/uat_spec.py:classification_dropdown_missing
-- 2. BC-CSV-EXPORT (BUG-029, BUG-030, BUG-031, BUG-062, BUG-063)
--    Hash: missing_feature:static/dashboard.html:csv_export_gone
CREATE OR ALTER VIEW vw_bug_chain_proposals_seeded AS
SELECT
    'BC-UAT-DROPDOWN' AS chain_label,
    'broken_interaction_bug:app/api/uat_spec.py:classification_dropdown_missing' AS failure_class_hash,
    'Dropdown renders with classification options populated from uat_classifications table on UAT page load' AS expected_outcome,
    'Dropdown DOM element contains zero options after page load; no network request to classifications endpoint fired' AS missing_signal,
    8 AS total_occurrences,
    '["BUG-018","BUG-039","BUG-051","BUG-061","BUG-067","BUG-078","BUG-080","BUG-091"]' AS member_requirement_codes,
    (SELECT MIN(created_at) FROM roadmap_requirements WHERE code IN ('BUG-018','BUG-039','BUG-051','BUG-061','BUG-067','BUG-078','BUG-080','BUG-091')) AS first_occurrence_at,
    'seeded' AS source

UNION ALL

SELECT
    'BC-CSV-EXPORT' AS chain_label,
    'missing_feature:static/dashboard.html:csv_export_gone' AS failure_class_hash,
    'Click on Export CSV button triggers download of text/csv file with current dashboard filters applied' AS expected_outcome,
    'exportCsvBtn DOM element absent from dashboard.html, OR GET /api/roadmap/export/csv returns 404, OR click handler not bound' AS missing_signal,
    5 AS total_occurrences,
    '["BUG-029","BUG-030","BUG-031","BUG-062","BUG-063"]' AS member_requirement_codes,
    (SELECT MIN(created_at) FROM roadmap_requirements WHERE code IN ('BUG-029','BUG-030','BUG-031','BUG-062','BUG-063')) AS first_occurrence_at,
    'seeded' AS source;

-- F.3: vw_bug_chain_proposals_inductive
-- Purpose: Inductive expansion from seeded chains using deterministic SQL rules
-- Columns: chain_label, proposed_member_code, match_rule, recurrence_count, diagnostic_present
--
-- Inductive rules (simplified for MP53B staging):
-- - BC-UAT-DROPDOWN: title LIKE '%dropdown%' AND title LIKE '%classification%'
-- - BC-CSV-EXPORT: title LIKE '%export%' AND title LIKE '%CSV%'
--
-- recurrence_count: how many times this bug recurred across different requirements
-- diagnostic_present: does the chain have a DIAG sprint linked?
CREATE OR ALTER VIEW vw_bug_chain_proposals_inductive AS
SELECT
    'BC-UAT-DROPDOWN' AS chain_label,
    r.code AS proposed_member_code,
    r.title AS proposed_member_title,
    'title LIKE ''%dropdown%'' AND title LIKE ''%classification%''' AS match_rule,
    (SELECT COUNT(*) FROM roadmap_requirements WHERE code IN ('BUG-018','BUG-039','BUG-051','BUG-061','BUG-067','BUG-078','BUG-080','BUG-091')) AS recurrence_count,
    CASE WHEN EXISTS (SELECT 1 FROM cc_prompts WHERE pth LIKE 'DIAG%' AND requirement_id IN (SELECT id FROM roadmap_requirements WHERE code IN ('BUG-018','BUG-039')))
        THEN 1 ELSE 0 END AS diagnostic_present
FROM roadmap_requirements r
WHERE r.type = 'bug'
  AND r.code NOT IN ('BUG-018','BUG-039','BUG-051','BUG-061','BUG-067','BUG-078','BUG-080','BUG-091')  -- exclude already-seeded
  AND r.title LIKE '%dropdown%'
  AND r.title LIKE '%classification%'

UNION ALL

SELECT
    'BC-CSV-EXPORT' AS chain_label,
    r.code AS proposed_member_code,
    r.title AS proposed_member_title,
    'title LIKE ''%export%'' AND title LIKE ''%CSV%''' AS match_rule,
    (SELECT COUNT(*) FROM roadmap_requirements WHERE code IN ('BUG-029','BUG-030','BUG-031','BUG-062','BUG-063')) AS recurrence_count,
    CASE WHEN EXISTS (SELECT 1 FROM cc_prompts WHERE pth LIKE 'DIAG%' AND requirement_id IN (SELECT id FROM roadmap_requirements WHERE code IN ('BUG-029','BUG-030')))
        THEN 1 ELSE 0 END AS diagnostic_present
FROM roadmap_requirements r
WHERE r.type = 'bug'
  AND r.code NOT IN ('BUG-029','BUG-030','BUG-031','BUG-062','BUG-063')  -- exclude already-seeded
  AND r.title LIKE '%export%'
  AND r.title LIKE '%CSV%';

-- F.4: vw_bug_chain_misclassified
-- Purpose: Surface chains/members where BV typing was wrong
-- Detects: machine_test_sent_to_pl, should_be_machine_test (BA32 violations)
--
-- JOIN logic: uat_bv_items -> uat_pages -> requirement via pth
-- This view depends on uat_bv_items.failure_type being populated with these classifications.
CREATE OR ALTER VIEW vw_bug_chain_misclassified AS
SELECT
    ps.chain_label,
    r.code AS member_requirement_code,
    bv.status AS bv_status,
    bv.bv_id,
    bv.title AS bv_title,
    bv.failure_type,
    CASE
        WHEN bv.failure_type = 'machine_test_sent_to_pl' THEN 'machine test exposed in PL form (BA32 class)'
        WHEN bv.failure_type = 'should_be_machine_test' THEN 'PL-visual BV should have been cc_machine'
        ELSE 'other mistyped BV'
    END AS misclassification_reason
FROM vw_bug_chain_proposals_seeded ps
CROSS APPLY OPENJSON(ps.member_requirement_codes) WITH (code nvarchar(20) '$') members
JOIN roadmap_requirements r ON r.code = members.code
JOIN cc_prompts cp ON cp.requirement_id = r.id
JOIN uat_pages up ON up.pth = cp.pth
JOIN uat_bv_items bv ON bv.spec_id = up.id
WHERE bv.failure_type IN ('machine_test_sent_to_pl', 'should_be_machine_test');

-- F.5: vw_bug_chain_unclassified
-- Purpose: Bugs that don't match any seeded or inductive chain
-- Arithmetic: count(all_bugs) - count(seeded_members) - count(inductive_proposals)
CREATE OR ALTER VIEW vw_bug_chain_unclassified AS
SELECT
    r.code,
    r.title,
    r.status,
    'no_deterministic_hash' AS reason_unclassified
FROM roadmap_requirements r
WHERE r.type = 'bug'
  AND r.code NOT IN (
      -- Seeded members
      SELECT members.code
      FROM vw_bug_chain_proposals_seeded ps
      CROSS APPLY OPENJSON(ps.member_requirement_codes) WITH (code nvarchar(20) '$') members
  )
  AND r.code NOT IN (
      -- Inductive proposals
      SELECT proposed_member_code FROM vw_bug_chain_proposals_inductive
  );

-- End of MP53B_bug_chain_proposals.sql
--
-- VERIFICATION QUERIES (run post-deploy):
-- SELECT * FROM vw_bug_chain_proposals_seeded;  -- Should return 2 rows (BC-UAT-DROPDOWN, BC-CSV-EXPORT)
-- SELECT * FROM vw_bug_chain_proposals_inductive;  -- Returns inductive matches (count varies)
-- SELECT COUNT(*) FROM vw_bug_chain_misclassified;  -- Returns mistyped BVs (0 if clean)
-- SELECT COUNT(*) FROM vw_bug_chain_unclassified;  -- Returns residue bugs
--
-- ARITHMETIC CHECK:
-- (SELECT COUNT(*) FROM roadmap_requirements WHERE type='bug') =
-- (SELECT COUNT(*) FROM (
--     SELECT code FROM vw_bug_chain_proposals_seeded CROSS APPLY OPENJSON(member_requirement_codes) WITH (code nvarchar(20) '$')
--     UNION
--     SELECT proposed_member_code FROM vw_bug_chain_proposals_inductive
--     UNION
--     SELECT code FROM vw_bug_chain_unclassified
-- ) unioned)
