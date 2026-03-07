-- Migration 032: PF5-MS1 — Extend status CHECK to include lifecycle values
-- Applied via app/core/migrations.py migration 32 at startup
-- Date: 2026-03-06

-- Drop existing status constraint on roadmap_requirements (dynamic name lookup)
DECLARE @constraint_name NVARCHAR(256)
SELECT @constraint_name = cc.name
FROM sys.check_constraints cc
JOIN sys.columns col ON cc.parent_object_id = col.object_id AND cc.parent_column_id = col.column_id
WHERE OBJECT_NAME(cc.parent_object_id) = 'roadmap_requirements' AND col.name = 'status'

IF @constraint_name IS NOT NULL
    EXEC('ALTER TABLE roadmap_requirements DROP CONSTRAINT [' + @constraint_name + ']')

-- Add new constraint with legacy + 11 lifecycle values
ALTER TABLE roadmap_requirements ADD CONSTRAINT chk_req_status
CHECK (status IN (
    -- Legacy values (unchanged)
    'backlog', 'executing', 'closed', 'archived',
    -- Lifecycle values (PF5-MS1)
    'req_created', 'cai_processing', 'cc_prompt_ready', 'approved',
    'cc_processing', 'cc_handoff_ready', 'cai_review',
    'uat_submitted', 'cai_final_review', 'done', 'rework'
));
