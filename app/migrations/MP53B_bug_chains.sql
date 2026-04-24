-- MP53B Phase E: bug_chains Schema
-- 14-column bug clustering table + roadmap_requirements columns
-- Created: 2026-04-23
--
-- SCOPE: Table creation only. Zero writes to bug_chains in MP53B.
-- MP53C (post-PL-approval) populates bug_chains + updates requirement columns.

-- E.1: CREATE TABLE bug_chains
-- Purpose: Cluster recurring bugs by failure_class_hash (3-tuple: type:module:symptom)
-- Hash is deterministic grouping key. expected_outcome stored separately (not in hash).
CREATE TABLE bug_chains (
    id nvarchar(20) NOT NULL PRIMARY KEY,
    failure_class_hash nvarchar(200) NOT NULL UNIQUE,
    pattern_label nvarchar(200) NULL,
    expected_outcome nvarchar(500) NULL,  -- MP53B addition: what success looks like
    first_occurrence_requirement_code nvarchar(20) NULL,
    first_occurrence_at datetime2 NULL,
    member_requirement_codes nvarchar(max) NULL,  -- JSON array of requirement codes
    total_occurrences int NOT NULL DEFAULT 0,
    status nvarchar(20) NOT NULL DEFAULT 'active',  -- active / resolved / archived
    diagnostic_pth nvarchar(20) NULL,  -- PTH of diagnostic sprint (if any)
    resolution_pth nvarchar(20) NULL,  -- PTH of resolution sprint
    resolved_at datetime2 NULL,
    created_at datetime2 NOT NULL DEFAULT GETUTCDATE(),
    updated_at datetime2 NOT NULL DEFAULT GETUTCDATE()
);

-- Index on hash for fast lookups during bug classification
CREATE INDEX idx_bug_chains_hash ON bug_chains(failure_class_hash);

-- Index on status for active chain queries
CREATE INDEX idx_bug_chains_status ON bug_chains(status) WHERE status = 'active';

-- E.2: ALTER TABLE roadmap_requirements
-- Add columns for bug chain linkage. Stay NULL in MP53B.
-- MP53C populates after PL approves Phase F proposal views.
IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'roadmap_requirements' AND COLUMN_NAME = 'failure_class_hash'
)
BEGIN
    ALTER TABLE roadmap_requirements ADD failure_class_hash nvarchar(200) NULL;
END;

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'roadmap_requirements' AND COLUMN_NAME = 'bug_chain_id'
)
BEGIN
    ALTER TABLE roadmap_requirements ADD bug_chain_id nvarchar(20) NULL;
END;

-- FK constraint from requirements to bug_chains (optional enforcement)
-- Not created yet - wait until MP53C populates chains to avoid orphan FKs
-- ALTER TABLE roadmap_requirements
-- ADD CONSTRAINT FK_requirements_bug_chain
-- FOREIGN KEY (bug_chain_id) REFERENCES bug_chains(id);

-- Index on failure_class_hash for grouping queries
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'idx_requirements_failure_hash' AND object_id = OBJECT_ID('roadmap_requirements')
)
BEGIN
    CREATE INDEX idx_requirements_failure_hash ON roadmap_requirements(failure_class_hash)
    WHERE failure_class_hash IS NOT NULL;
END;

-- End of MP53B_bug_chains.sql
--
-- VERIFICATION:
-- SELECT COUNT(*) FROM bug_chains;  -- Should return 0 (table starts empty)
-- SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
-- WHERE TABLE_NAME = 'bug_chains' ORDER BY ORDINAL_POSITION;  -- Should show 14 columns
-- SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
-- WHERE TABLE_NAME = 'roadmap_requirements'
-- AND COLUMN_NAME IN ('failure_class_hash', 'bug_chain_id');  -- Should show 2 new columns
