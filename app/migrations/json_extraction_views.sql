-- MP53B Phase C.2: JSON Extraction Views
-- Six read-only views extracting structured data from JSON blob columns
-- Created: 2026-04-23

-- View 1: vw_uat_spec_test_cases
-- Purpose: Extract individual test cases from uat_pages.spec_data
-- Usage: Analyze BV distribution, find BVs by type across all specs
CREATE OR ALTER VIEW vw_uat_spec_test_cases AS
SELECT
    up.id AS spec_id,
    up.pth,
    up.project,
    up.sprint_code,
    tc.id AS test_case_id,
    tc.type AS bv_type,
    tc.title AS bv_title,
    tc.expected AS bv_expected
FROM uat_pages up
CROSS APPLY OPENJSON(up.spec_data)
  WITH (
    test_cases nvarchar(max) '$.test_cases' AS JSON
  ) spec
CROSS APPLY OPENJSON(spec.test_cases)
  WITH (
    id nvarchar(50) '$.id',
    type nvarchar(50) '$.type',
    title nvarchar(max) '$.title',
    expected nvarchar(max) '$.expected'
  ) tc
WHERE up.spec_data IS NOT NULL
  AND ISJSON(up.spec_data) = 1;

-- View 2: vw_uat_cai_review_metadata
-- Purpose: Extract CAI review guidance from uat_pages.cai_review_json
-- Usage: Analyze review patterns, risk tracking across sprints
CREATE OR ALTER VIEW vw_uat_cai_review_metadata AS
SELECT
    up.id AS spec_id,
    up.pth,
    focus.value AS focus_area,
    risk.value AS risk,
    regress.value AS regression_zone
FROM uat_pages up
OUTER APPLY OPENJSON(up.cai_review_json, '$.focus_areas') focus
OUTER APPLY OPENJSON(up.cai_review_json, '$.risks') risk
OUTER APPLY OPENJSON(up.cai_review_json, '$.regression_zones') regress
WHERE up.cai_review_json IS NOT NULL
  AND ISJSON(up.cai_review_json) = 1;

-- View 3: vw_uat_general_notes_structured
-- Purpose: Extract structured notes from uat_pages.general_notes (JSON array form only)
-- Usage: Bug classification, failure type analysis from PL notes
-- Note: Skips plain-text notes; only parses JSON-array-structured notes
CREATE OR ALTER VIEW vw_uat_general_notes_structured AS
SELECT
    up.id AS spec_id,
    up.pth,
    up.project,
    note.timestamp,
    note.text AS note_text,
    note.classification,
    note.failure_type
FROM uat_pages up
CROSS APPLY OPENJSON(up.general_notes)
  WITH (
    timestamp datetime2 '$.timestamp',
    text nvarchar(max) '$.text',
    classification nvarchar(50) '$.classification',
    failure_type nvarchar(50) '$.failure_type'
  ) note
WHERE up.general_notes IS NOT NULL
  AND ISJSON(up.general_notes) = 1
  AND LEFT(LTRIM(up.general_notes), 1) = '[';

-- View 4: vw_mcp_handoff_evidence
-- Purpose: Extract evidence items from mcp_handoffs.evidence_json
-- Usage: Machine test result tracking, evidence audit
CREATE OR ALTER VIEW vw_mcp_handoff_evidence AS
SELECT
    h.id AS handoff_id,
    h.pth,
    h.direction,
    ev.code AS evidence_code,
    ev.status AS evidence_status,
    ev.evidence AS evidence_detail
FROM mcp_handoffs h
CROSS APPLY OPENJSON(h.evidence_json)
  WITH (
    code nvarchar(50) '$.code',
    status nvarchar(50) '$.status',
    evidence nvarchar(max) '$.evidence' AS JSON
  ) ev
WHERE h.evidence_json IS NOT NULL
  AND ISJSON(h.evidence_json) = 1;

-- View 5: vw_review_lesson_candidates
-- Purpose: Extract lesson candidates from reviews.lesson_candidates
-- Usage: Governance amendment pipeline, lesson routing to compliance docs
CREATE OR ALTER VIEW vw_review_lesson_candidates AS
SELECT
    r.id AS review_id,
    r.handoff_id,
    r.assessment,
    r.created_at AS review_created_at,
    lc.lesson,
    lc.target,
    lc.severity
FROM reviews r
CROSS APPLY OPENJSON(r.lesson_candidates)
  WITH (
    lesson nvarchar(max) '$.lesson',
    target nvarchar(100) '$.target',
    severity nvarchar(20) '$.severity'
  ) lc
WHERE r.lesson_candidates IS NOT NULL
  AND ISJSON(r.lesson_candidates) = 1;

-- View 6: vw_prompt_also_closes
-- Purpose: Extract also_closes requirement codes from cc_prompts
-- Usage: Sprint scope analysis, secondary requirement tracking (BA44)
CREATE OR ALTER VIEW vw_prompt_also_closes AS
SELECT
    cp.id AS prompt_id,
    cp.pth,
    cp.sprint_id,
    cp.requirement_id AS primary_requirement_id,
    ac.value AS also_closes_code
FROM cc_prompts cp
CROSS APPLY OPENJSON(cp.also_closes) ac
WHERE cp.also_closes IS NOT NULL
  AND ISJSON(cp.also_closes) = 1;

-- End of json_extraction_views.sql
