-- MP56 - Bug Classifier Inspector Schema Migration
-- Version: v3.4.0 to v3.5.0
-- Date: 2026-04-26
--
-- This migration:
-- 1. Adds legacy_classification_note column to uat_bv_items
-- 2. Migrates failure_type values to classification column (62 rows)
-- 3. Renames failure_types table to classifications
-- 4. Renames columns (type_code→code, display_label→name, help_text→description, is_active→active)
-- 5. Adds display_order column
-- 6. Inserts 6 net-new classifications
-- 7. Creates bug_classifications join table (M:N bug→classifications)
-- 8. Creates bug_chain_members join table (M:N bug→chains)
-- 9. Drops failure_type columns from uat_results and uat_bv_items

-- === PHASE A.2 - Migrate uat_bv_items.failure_type to classification ===

-- Add column to preserve legacy classification values during migration
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('uat_bv_items') AND name = 'legacy_classification_note')
  ALTER TABLE uat_bv_items ADD legacy_classification_note NVARCHAR(50) NULL;

-- Preserve legacy classification values (Bug, no_action, No-action) before overwriting
UPDATE uat_bv_items
SET legacy_classification_note = classification
WHERE failure_type IS NOT NULL
  AND classification IS NOT NULL
  AND classification IN ('Bug','no_action','No-action');

-- Migrate failure_type values into classification column
UPDATE uat_bv_items
SET classification = failure_type
WHERE failure_type IS NOT NULL
  AND (classification IS NULL OR classification IN ('Bug','no_action','No-action'));

-- Expected: 62 rows affected

-- === PHASE A.3 - Rename failure_types table and columns ===

EXEC sp_rename 'failure_types', 'classifications';
EXEC sp_rename 'classifications.type_code', 'code', 'COLUMN';
EXEC sp_rename 'classifications.display_label', 'name', 'COLUMN';
EXEC sp_rename 'classifications.help_text', 'description', 'COLUMN';
EXEC sp_rename 'classifications.is_active', 'active', 'COLUMN';
ALTER TABLE classifications ADD display_order INT NULL;

-- === PHASE A.4 - Insert 6 net-new classifications ===

INSERT INTO classifications (code, category_code, name, description, active, display_order)
VALUES
  ('regression_same_root', 'bug', 'Regression - same root', 'Bug recurrence with identical root cause as predecessor', 1, 21),
  ('frontend_not_updated', 'bug', 'Frontend not updated', 'Backend change shipped but frontend not synced', 1, 22),
  ('render_template', 'bug', 'Render / Template', 'Template renders incorrectly or omits required field', 1, 23),
  ('state_machine', 'bug', 'State Machine', 'Lifecycle/state transition violation', 1, 24),
  ('config_secrets', 'bug', 'Config / Secrets', 'Misconfiguration or secret rotation issue', 1, 25),
  ('broken_interaction_root', 'bug', 'Broken Interaction', 'Root cause variant of broken_interaction_bug at bug-level', 1, 26);

-- Expected: 6 rows inserted, total classifications = 26

-- === PHASE A.5 - Create bug_classifications join table ===

CREATE TABLE bug_classifications (
  id INT IDENTITY PRIMARY KEY,
  bug_requirement_id NVARCHAR(50) NOT NULL,
  classification_code NVARCHAR(100) NOT NULL,
  created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
  created_by NVARCHAR(50) NULL,
  CONSTRAINT fk_bc_classification FOREIGN KEY (classification_code) REFERENCES classifications(code),
  CONSTRAINT uq_bc UNIQUE (bug_requirement_id, classification_code)
);
CREATE INDEX ix_bc_bug ON bug_classifications(bug_requirement_id);
CREATE INDEX ix_bc_cls ON bug_classifications(classification_code);

-- === PHASE A.6 - Create bug_chain_members join table ===

CREATE TABLE bug_chain_members (
  id INT IDENTITY PRIMARY KEY,
  bug_requirement_id NVARCHAR(50) NOT NULL,
  chain_id NVARCHAR(20) NOT NULL,
  created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
  created_by NVARCHAR(50) NULL,
  CONSTRAINT fk_bcm_chain FOREIGN KEY (chain_id) REFERENCES bug_chains(id),
  CONSTRAINT uq_bcm UNIQUE (bug_requirement_id, chain_id)
);
CREATE INDEX ix_bcm_bug ON bug_chain_members(bug_requirement_id);
CREATE INDEX ix_bcm_chain ON bug_chain_members(chain_id);

-- === PHASE A.7 - Drop failure_type columns ===

ALTER TABLE uat_results DROP COLUMN failure_type;
ALTER TABLE uat_bv_items DROP COLUMN failure_type;

-- === PHASE A.8 - Update view vw_bug_chain_misclassified ===
-- View references uat_bv_items.failure_type which is now classification

CREATE OR ALTER VIEW vw_bug_chain_misclassified AS
SELECT
    ps.chain_label,
    r.code AS member_requirement_code,
    bv.status AS bv_status,
    bv.bv_id,
    bv.title AS bv_title,
    bv.classification AS failure_type, -- Alias for backward compat
    CASE
        WHEN bv.classification = 'machine_test_sent_to_pl' THEN 'machine test exposed in PL form (BA32 class)'
        WHEN bv.classification = 'should_be_machine_test' THEN 'PL-visual BV should have been cc_machine'
        ELSE 'other mistyped BV'
    END AS misclassification_reason
FROM vw_bug_chain_proposals_seeded ps
CROSS APPLY OPENJSON(ps.member_requirement_codes) WITH (code nvarchar(20) '$') members
JOIN roadmap_requirements r ON r.code = members.code
JOIN cc_prompts cp ON cp.requirement_id = r.id
JOIN uat_pages up ON up.pth = cp.pth
JOIN uat_bv_items bv ON bv.spec_id = up.id
WHERE bv.classification IN ('machine_test_sent_to_pl', 'should_be_machine_test');

-- === Verification queries ===
-- Run these to verify migration success:
--
-- SELECT COUNT(*) FROM sys.columns WHERE object_id=OBJECT_ID('uat_results') AND name='failure_type';  -- expect 0
-- SELECT COUNT(*) FROM sys.columns WHERE object_id=OBJECT_ID('uat_bv_items') AND name='failure_type';  -- expect 0
-- SELECT COUNT(*) FROM classifications;  -- expect 26
-- SELECT COUNT(*) FROM bug_classifications;  -- expect 0 (populated in Phase E)
-- SELECT COUNT(*) FROM bug_chain_members;  -- expect 0 (populated in Phase E)
