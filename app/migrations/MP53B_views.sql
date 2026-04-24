-- MP53B Phase B: SQL Views for Data Model Inspection
-- Five operational views for MetaPM v3.3.0
-- Created: 2026-04-23

-- View 1: vw_project_pth_items
-- Purpose: Full hierarchy from project -> pth -> requirement -> status
-- Usage: Dashboard aggregations, sprint tracking
CREATE OR ALTER VIEW vw_project_pth_items AS
SELECT
    p.id AS project_id,
    p.code AS project_code,
    p.name AS project_name,
    p.emoji AS project_emoji,
    r.id AS requirement_id,
    r.code AS requirement_code,
    r.title AS requirement_title,
    r.type AS requirement_type,
    r.status AS requirement_status,
    r.priority AS requirement_priority,
    r.pth,
    r.sprint_id,
    cp.id AS prompt_id,
    cp.status AS prompt_status,
    cp.approved_at,
    cp.approved_by,
    r.created_at AS requirement_created_at,
    r.updated_at AS requirement_updated_at
FROM roadmap_projects p
LEFT JOIN roadmap_requirements r ON p.id = r.project_id
LEFT JOIN cc_prompts cp ON r.pth = cp.pth
WHERE r.id IS NOT NULL;

-- View 2: vw_pth_history
-- Purpose: Unified audit trail for PTH lifecycle (requirements + prompts)
-- Usage: Lifecycle analysis, state transition debugging
CREATE OR ALTER VIEW vw_pth_history AS
SELECT
    r.pth,
    'requirement' AS source,
    rh.old_value AS from_status,
    rh.new_value AS to_status,
    rh.changed_at AS transition_at,
    rh.changed_by AS changed_by,
    rh.notes AS transition_note,
    rh.field_name
FROM requirement_history rh
JOIN roadmap_requirements r ON rh.requirement_id = r.id
WHERE r.pth IS NOT NULL AND rh.field_name = 'status'

UNION ALL

SELECT
    pth,
    'prompt' AS source,
    ph.from_status AS from_status,
    ph.to_status AS to_status,
    ph.changed_at AS transition_at,
    ph.changed_by AS changed_by,
    ph.blocked_reason AS transition_note,
    'status' AS field_name
FROM prompt_history ph
WHERE ph.pth IS NOT NULL;

-- View 3: vw_pth_handoffs
-- Purpose: Handoff completion status with UAT pass/fail/pending counts
-- Usage: Sprint closeout dashboard, handoff quality metrics
CREATE OR ALTER VIEW vw_pth_handoffs AS
SELECT
    hs.pth,
    hs.sprint_id,
    hs.project_id,
    p.name AS project_name,
    hs.id AS handoff_shell_id,
    hs.created_at AS handoff_created_at,
    hs.uat_spec_id,
    up.status AS uat_status,
    up.submitted_at AS uat_submitted_at,
    up.pl_submitted_at,
    (SELECT COUNT(*) FROM uat_bv_items bv WHERE bv.spec_id = up.id AND bv.status IN ('passed', 'pass')) AS pass_count,
    (SELECT COUNT(*) FROM uat_bv_items bv WHERE bv.spec_id = up.id AND bv.status IN ('failed', 'fail')) AS fail_count,
    (SELECT COUNT(*) FROM uat_bv_items bv WHERE bv.spec_id = up.id AND bv.status = 'pending') AS pending_count,
    (SELECT COUNT(*) FROM uat_bv_items bv WHERE bv.spec_id = up.id) AS total_bv_count
FROM handoff_shells hs
LEFT JOIN uat_pages up ON hs.uat_spec_id = up.id
LEFT JOIN roadmap_projects p ON hs.project_id = p.id;

-- View 4: vw_quality_trend_weekly
-- Purpose: Weekly quality metrics by project (pass rate trends)
-- Usage: Quality dashboard, trend analysis, project health reports
CREATE OR ALTER VIEW vw_quality_trend_weekly AS
SELECT
    DATEADD(week, DATEDIFF(week, 0, bv.updated_at), 0) AS week_start,
    p.code AS project_code,
    p.name AS project_name,
    COUNT(CASE WHEN bv.status IN ('passed', 'pass') THEN 1 END) AS pass_count,
    COUNT(CASE WHEN bv.status IN ('failed', 'fail') THEN 1 END) AS fail_count,
    COUNT(CASE WHEN bv.status = 'pending' THEN 1 END) AS skip_count,
    COUNT(*) AS total_count,
    CASE
        WHEN COUNT(*) > 0
        THEN CAST(100.0 * COUNT(CASE WHEN bv.status IN ('passed', 'pass') THEN 1 END) / COUNT(*) AS DECIMAL(5,2))
        ELSE 0.0
    END AS pass_rate_pct
FROM uat_bv_items bv
JOIN uat_pages up ON bv.spec_id = up.id
JOIN roadmap_projects p ON up.project = p.code
WHERE bv.updated_at IS NOT NULL
GROUP BY
    DATEADD(week, DATEDIFF(week, 0, bv.updated_at), 0),
    p.code,
    p.name;

-- View 5: vw_bug_chains
-- Purpose: Bug chain summary (returns 0 rows until MP53C populates bug_chains table)
-- Usage: Bug clustering analysis, recurrence detection, chain health dashboard
CREATE OR ALTER VIEW vw_bug_chains AS
SELECT
    bc.id AS chain_id,
    bc.pattern_label,
    bc.expected_outcome,
    bc.failure_class_hash,
    bc.first_occurrence_requirement_code,
    bc.first_occurrence_at,
    bc.total_occurrences,
    bc.status AS chain_status,
    bc.diagnostic_pth,
    bc.resolution_pth,
    bc.resolved_at,
    DATEDIFF(day, bc.first_occurrence_at, COALESCE(bc.resolved_at, GETUTCDATE())) AS age_days,
    bc.member_requirement_codes AS members_json
FROM bug_chains bc;

-- End of MP53B_views.sql
