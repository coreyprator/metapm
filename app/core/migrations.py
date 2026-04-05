"""
MetaPM Database Migrations
Idempotent schema migrations run at startup.
"""

import logging
from app.core.database import execute_query

logger = logging.getLogger(__name__)


def run_migrations():
    """Run all idempotent migrations."""
    logger.info("Running database migrations...")

    # Migration 1: Add TaskType column to Tasks
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'Tasks' AND COLUMN_NAME = 'TaskType'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 1: Adding TaskType column to Tasks...")
            execute_query(
                "ALTER TABLE Tasks ADD TaskType NVARCHAR(20) DEFAULT 'task'",
                fetch="none"
            )
            # Backfill existing tasks based on title prefix
            execute_query(
                "UPDATE Tasks SET TaskType = 'bug' WHERE Title LIKE 'BUG-%'",
                fetch="none"
            )
            execute_query(
                "UPDATE Tasks SET TaskType = 'requirement' WHERE Title LIKE 'REQ-%'",
                fetch="none"
            )
            # Set remaining to 'task'
            execute_query(
                "UPDATE Tasks SET TaskType = 'task' WHERE TaskType IS NULL",
                fetch="none"
            )
            logger.info("  Migration 1: TaskType column added and backfilled.")
        else:
            logger.info("  Migration 1: TaskType column already exists.")
    except Exception as e:
        logger.warning(f"  Migration 1 warning: {e}")

    # Migration 2: Create mcp_handoffs table
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'mcp_handoffs'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 2: Creating mcp_handoffs table...")
            execute_query("""
                CREATE TABLE mcp_handoffs (
                    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
                    project NVARCHAR(100) NOT NULL,
                    task NVARCHAR(200) NOT NULL,
                    direction NVARCHAR(20) NOT NULL CHECK (direction IN ('cc_to_ai', 'ai_to_cc')),
                    status NVARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'read', 'processed', 'archived')),
                    content NVARCHAR(MAX) NOT NULL,
                    metadata NVARCHAR(MAX),
                    response_to UNIQUEIDENTIFIER NULL,
                    created_at DATETIME2 DEFAULT GETUTCDATE(),
                    updated_at DATETIME2 DEFAULT GETUTCDATE(),
                    CONSTRAINT FK_handoffs_response FOREIGN KEY (response_to) REFERENCES mcp_handoffs(id)
                )
            """, fetch="none")
            # Create indexes
            execute_query("CREATE INDEX idx_handoffs_project ON mcp_handoffs(project)", fetch="none")
            execute_query("CREATE INDEX idx_handoffs_status ON mcp_handoffs(status)", fetch="none")
            execute_query("CREATE INDEX idx_handoffs_direction ON mcp_handoffs(direction)", fetch="none")
            execute_query("CREATE INDEX idx_handoffs_created ON mcp_handoffs(created_at DESC)", fetch="none")
            logger.info("  Migration 2: mcp_handoffs table created.")
        else:
            logger.info("  Migration 2: mcp_handoffs table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 2 warning: {e}")

    # Migration 3: Create mcp_tasks table
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'mcp_tasks'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 3: Creating mcp_tasks table...")
            execute_query("""
                CREATE TABLE mcp_tasks (
                    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
                    project NVARCHAR(100) NOT NULL,
                    title NVARCHAR(500) NOT NULL,
                    description NVARCHAR(MAX),
                    priority NVARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('critical', 'high', 'medium', 'low')),
                    status NVARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'blocked', 'done', 'cancelled')),
                    assigned_to NVARCHAR(50) CHECK (assigned_to IN ('cc', 'corey', 'claude_ai')),
                    related_handoff_id UNIQUEIDENTIFIER NULL,
                    tags NVARCHAR(MAX),
                    notes NVARCHAR(MAX),
                    due_date DATETIME2,
                    created_at DATETIME2 DEFAULT GETUTCDATE(),
                    updated_at DATETIME2 DEFAULT GETUTCDATE(),
                    completed_at DATETIME2,
                    CONSTRAINT FK_tasks_handoff FOREIGN KEY (related_handoff_id) REFERENCES mcp_handoffs(id)
                )
            """, fetch="none")
            # Create indexes
            execute_query("CREATE INDEX idx_mcp_tasks_project ON mcp_tasks(project)", fetch="none")
            execute_query("CREATE INDEX idx_mcp_tasks_status ON mcp_tasks(status)", fetch="none")
            execute_query("CREATE INDEX idx_mcp_tasks_assigned ON mcp_tasks(assigned_to)", fetch="none")
            execute_query("CREATE INDEX idx_mcp_tasks_priority ON mcp_tasks(priority)", fetch="none")
            logger.info("  Migration 3: mcp_tasks table created.")
        else:
            logger.info("  Migration 3: mcp_tasks table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 3 warning: {e}")

    # Migration 4: Add source/gcs columns to mcp_handoffs for dashboard
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'mcp_handoffs' AND COLUMN_NAME = 'source'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 4: Adding dashboard columns to mcp_handoffs...")
            execute_query(
                "ALTER TABLE mcp_handoffs ADD source NVARCHAR(20) DEFAULT 'api'",
                fetch="none"
            )
            execute_query(
                "ALTER TABLE mcp_handoffs ADD gcs_path NVARCHAR(500)",
                fetch="none"
            )
            execute_query(
                "ALTER TABLE mcp_handoffs ADD from_entity NVARCHAR(100)",
                fetch="none"
            )
            execute_query(
                "ALTER TABLE mcp_handoffs ADD to_entity NVARCHAR(100)",
                fetch="none"
            )
            # Create index on gcs_path for deduplication
            execute_query("CREATE INDEX idx_handoffs_gcs_path ON mcp_handoffs(gcs_path)", fetch="none")
            logger.info("  Migration 4: Dashboard columns added.")
        else:
            logger.info("  Migration 4: Dashboard columns already exist.")
    except Exception as e:
        logger.warning(f"  Migration 4 warning: {e}")

    # Migration 5: Add final dashboard columns to mcp_handoffs (v1.9.0)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'mcp_handoffs' AND COLUMN_NAME = 'content_hash'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 5: Adding final dashboard columns to mcp_handoffs...")
            # Content tracking
            execute_query("ALTER TABLE mcp_handoffs ADD content_hash NVARCHAR(64)", fetch="none")
            execute_query("ALTER TABLE mcp_handoffs ADD summary NVARCHAR(500)", fetch="none")
            execute_query("ALTER TABLE mcp_handoffs ADD title NVARCHAR(255)", fetch="none")
            # Metadata
            execute_query("ALTER TABLE mcp_handoffs ADD version NVARCHAR(20)", fetch="none")
            execute_query("ALTER TABLE mcp_handoffs ADD priority NVARCHAR(20)", fetch="none")
            execute_query("ALTER TABLE mcp_handoffs ADD type NVARCHAR(50)", fetch="none")
            # Timestamps
            execute_query("ALTER TABLE mcp_handoffs ADD read_at DATETIME2", fetch="none")
            execute_query("ALTER TABLE mcp_handoffs ADD completed_at DATETIME2", fetch="none")
            # GCS sync status
            execute_query("ALTER TABLE mcp_handoffs ADD gcs_synced BIT DEFAULT 0", fetch="none")
            execute_query("ALTER TABLE mcp_handoffs ADD gcs_url NVARCHAR(500)", fetch="none")
            execute_query("ALTER TABLE mcp_handoffs ADD gcs_synced_at DATETIME2", fetch="none")
            # Git tracking
            execute_query("ALTER TABLE mcp_handoffs ADD git_commit NVARCHAR(50)", fetch="none")
            execute_query("ALTER TABLE mcp_handoffs ADD git_verified BIT DEFAULT 0", fetch="none")
            # Compliance
            execute_query("ALTER TABLE mcp_handoffs ADD compliance_score INT DEFAULT 100", fetch="none")
            # Index for dedup
            execute_query("CREATE INDEX idx_handoffs_content_hash ON mcp_handoffs(content_hash)", fetch="none")
            logger.info("  Migration 5: Final dashboard columns added.")
        else:
            logger.info("  Migration 5: Final dashboard columns already exist.")
    except Exception as e:
        logger.warning(f"  Migration 5 warning: {e}")

    # Migration 6: Create uat_results table and update handoff status constraint
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'uat_results'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 6: Creating uat_results table...")
            execute_query("""
                CREATE TABLE uat_results (
                    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
                    handoff_id UNIQUEIDENTIFIER NOT NULL,

                    -- Results
                    status NVARCHAR(20) NOT NULL CHECK (status IN ('passed', 'failed')),
                    total_tests INT,
                    passed INT,
                    failed INT,
                    notes_count INT,

                    -- Full results text
                    results_text NVARCHAR(MAX),

                    -- Metadata
                    tested_by NVARCHAR(100) DEFAULT 'Corey',
                    tested_at DATETIME2 DEFAULT GETUTCDATE(),

                    -- Checklist reference
                    checklist_path NVARCHAR(500),

                    CONSTRAINT FK_uat_handoff FOREIGN KEY (handoff_id) REFERENCES mcp_handoffs(id)
                )
            """, fetch="none")
            # Create indexes
            execute_query("CREATE INDEX idx_uat_handoff ON uat_results(handoff_id)", fetch="none")
            execute_query("CREATE INDEX idx_uat_status ON uat_results(status)", fetch="none")
            logger.info("  Migration 6: uat_results table created.")

            # Update handoff status CHECK constraint to include new values
            logger.info("  Migration 6: Updating handoff status constraint...")
            # First drop the existing constraint (find its name dynamically)
            execute_query("""
                DECLARE @constraint_name NVARCHAR(128)
                SELECT @constraint_name = name
                FROM sys.check_constraints
                WHERE parent_object_id = OBJECT_ID('mcp_handoffs')
                  AND definition LIKE '%status%'

                IF @constraint_name IS NOT NULL
                BEGIN
                    EXEC('ALTER TABLE mcp_handoffs DROP CONSTRAINT ' + @constraint_name)
                END
            """, fetch="none")
            # Add new constraint with additional status values
            execute_query("""
                ALTER TABLE mcp_handoffs
                ADD CONSTRAINT CK_handoffs_status
                CHECK (status IN ('pending', 'read', 'processed', 'archived', 'pending_uat', 'needs_fixes', 'done'))
            """, fetch="none")
            logger.info("  Migration 6: Handoff status constraint updated.")
        else:
            logger.info("  Migration 6: uat_results table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 6 warning: {e}")

    # Migration 7: Add uat_status column to mcp_handoffs
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'mcp_handoffs' AND COLUMN_NAME = 'uat_status'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 7: Adding UAT columns to mcp_handoffs...")
            execute_query("ALTER TABLE mcp_handoffs ADD uat_status NVARCHAR(20)", fetch="none")
            execute_query("ALTER TABLE mcp_handoffs ADD uat_passed INT", fetch="none")
            execute_query("ALTER TABLE mcp_handoffs ADD uat_failed INT", fetch="none")
            execute_query("ALTER TABLE mcp_handoffs ADD uat_date DATETIME2", fetch="none")
            logger.info("  Migration 7: UAT columns added to mcp_handoffs.")
        else:
            logger.info("  Migration 7: UAT columns already exist.")
    except Exception as e:
        logger.warning(f"  Migration 7 warning: {e}")

    # Migration 8: Create roadmap_projects table (v2.0.0 Roadmap Feature)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'roadmap_projects'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 8: Creating roadmap_projects table...")
            execute_query("""
                CREATE TABLE roadmap_projects (
                    id NVARCHAR(36) PRIMARY KEY,
                    code NVARCHAR(10) NOT NULL UNIQUE,
                    name NVARCHAR(100) NOT NULL,
                    emoji NVARCHAR(10),
                    color NVARCHAR(20),
                    current_version NVARCHAR(20),
                    status NVARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'stable', 'maintenance', 'paused')),
                    repo_url NVARCHAR(500),
                    deploy_url NVARCHAR(500),
                    created_at DATETIME2 DEFAULT GETDATE(),
                    updated_at DATETIME2 DEFAULT GETDATE()
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_roadmap_projects_code ON roadmap_projects(code)", fetch="none")
            execute_query("CREATE INDEX idx_roadmap_projects_status ON roadmap_projects(status)", fetch="none")
            logger.info("  Migration 8: roadmap_projects table created.")
        else:
            logger.info("  Migration 8: roadmap_projects table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 8 warning: {e}")

    # Migration 9: Create roadmap_sprints table (v2.0.0 Roadmap Feature)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'roadmap_sprints'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 9: Creating roadmap_sprints table...")
            execute_query("""
                CREATE TABLE roadmap_sprints (
                    id NVARCHAR(36) PRIMARY KEY,
                    name NVARCHAR(100) NOT NULL,
                    description NVARCHAR(MAX),
                    status NVARCHAR(20) DEFAULT 'planned' CHECK (status IN ('planned', 'active', 'complete')),
                    start_date DATE,
                    end_date DATE,
                    created_at DATETIME2 DEFAULT GETDATE()
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_roadmap_sprints_status ON roadmap_sprints(status)", fetch="none")
            logger.info("  Migration 9: roadmap_sprints table created.")
        else:
            logger.info("  Migration 9: roadmap_sprints table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 9 warning: {e}")

    # Migration 10: Create roadmap_requirements table (v2.0.0 Roadmap Feature)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'roadmap_requirements'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 10: Creating roadmap_requirements table...")
            execute_query("""
                CREATE TABLE roadmap_requirements (
                    id NVARCHAR(36) PRIMARY KEY,
                    project_id NVARCHAR(36) NOT NULL,
                    code NVARCHAR(20) NOT NULL,
                    title NVARCHAR(200) NOT NULL,
                    description NVARCHAR(MAX),
                    type NVARCHAR(20) DEFAULT 'task' CHECK (type IN ('feature', 'bug', 'enhancement', 'task')),
                    priority NVARCHAR(10) DEFAULT 'P2' CHECK (priority IN ('P1', 'P2', 'P3')),
                    status NVARCHAR(20) DEFAULT 'backlog' CHECK (status IN ('backlog', 'planned', 'in_progress', 'uat', 'needs_fixes', 'done')),
                    target_version NVARCHAR(20),
                    sprint_id NVARCHAR(36),
                    handoff_id UNIQUEIDENTIFIER,
                    uat_id UNIQUEIDENTIFIER,
                    created_at DATETIME2 DEFAULT GETDATE(),
                    updated_at DATETIME2 DEFAULT GETDATE(),
                    CONSTRAINT FK_roadmap_req_project FOREIGN KEY (project_id) REFERENCES roadmap_projects(id),
                    CONSTRAINT FK_roadmap_req_sprint FOREIGN KEY (sprint_id) REFERENCES roadmap_sprints(id),
                    CONSTRAINT FK_roadmap_req_handoff FOREIGN KEY (handoff_id) REFERENCES mcp_handoffs(id),
                    CONSTRAINT FK_roadmap_req_uat FOREIGN KEY (uat_id) REFERENCES uat_results(id)
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_roadmap_req_project ON roadmap_requirements(project_id)", fetch="none")
            execute_query("CREATE INDEX idx_roadmap_req_status ON roadmap_requirements(status)", fetch="none")
            execute_query("CREATE INDEX idx_roadmap_req_sprint ON roadmap_requirements(sprint_id)", fetch="none")
            execute_query("CREATE INDEX idx_roadmap_req_code ON roadmap_requirements(code)", fetch="none")
            logger.info("  Migration 10: roadmap_requirements table created.")
        else:
            logger.info("  Migration 10: roadmap_requirements table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 10 warning: {e}")

    # Migration 11: Update uat_results status constraint to allow 'pending' (v2.0.4)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM sys.check_constraints
            WHERE parent_object_id = OBJECT_ID('uat_results')
              AND definition LIKE '%pending%'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 11: Updating uat_results status constraint...")
            # Drop the existing constraint
            execute_query("""
                DECLARE @constraint_name NVARCHAR(128)
                SELECT @constraint_name = name
                FROM sys.check_constraints
                WHERE parent_object_id = OBJECT_ID('uat_results')
                  AND definition LIKE '%status%'

                IF @constraint_name IS NOT NULL
                BEGIN
                    EXEC('ALTER TABLE uat_results DROP CONSTRAINT ' + @constraint_name)
                END
            """, fetch="none")
            # Add new constraint with 'pending' value
            execute_query("""
                ALTER TABLE uat_results
                ADD CONSTRAINT CK_uat_results_status
                CHECK (status IN ('passed', 'failed', 'pending'))
            """, fetch="none")
            logger.info("  Migration 11: uat_results status constraint updated to allow 'pending'.")
        else:
            logger.info("  Migration 11: uat_results status constraint already includes 'pending'.")
    except Exception as e:
        logger.warning(f"  Migration 11 warning: {e}")

    # Migration 12: Create handoff lifecycle tracking tables (HO-A1B2)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'handoff_requests'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 12: Creating handoff lifecycle tracking tables...")

            # Table 1: handoff_requests - tracks full lifecycle of each handoff
            execute_query("""
                CREATE TABLE handoff_requests (
                    id VARCHAR(10) PRIMARY KEY,
                    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
                    project VARCHAR(50) NOT NULL,
                    roadmap_id VARCHAR(20),
                    request_type VARCHAR(20) NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    description NVARCHAR(MAX),
                    spec_handoff_url VARCHAR(500),
                    status VARCHAR(20) NOT NULL DEFAULT 'SPEC',
                    updated_at DATETIME2 DEFAULT GETDATE(),
                    CONSTRAINT CK_handoff_req_type CHECK (request_type IN ('Requirement', 'Bug', 'UAT', 'Enhancement', 'Hotfix')),
                    CONSTRAINT CK_handoff_req_status CHECK (status IN ('SPEC', 'PENDING', 'DELIVERED', 'UAT', 'PASSED', 'FAILED'))
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_handoff_req_project ON handoff_requests(project)", fetch="none")
            execute_query("CREATE INDEX idx_handoff_req_status ON handoff_requests(status)", fetch="none")
            execute_query("CREATE INDEX idx_handoff_req_roadmap ON handoff_requests(roadmap_id)", fetch="none")
            logger.info("  Migration 12: handoff_requests table created.")

            # Table 2: handoff_completions - tracks CC completion responses
            execute_query("""
                CREATE TABLE handoff_completions (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    handoff_id VARCHAR(10) NOT NULL,
                    completed_at DATETIME2 NOT NULL DEFAULT GETDATE(),
                    status VARCHAR(20) NOT NULL,
                    commit_hash VARCHAR(40),
                    completion_handoff_url VARCHAR(500),
                    notes NVARCHAR(MAX),
                    CONSTRAINT CK_completion_status CHECK (status IN ('COMPLETE', 'PARTIAL', 'BLOCKED')),
                    CONSTRAINT FK_completion_handoff FOREIGN KEY (handoff_id) REFERENCES handoff_requests(id)
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_completion_handoff ON handoff_completions(handoff_id)", fetch="none")
            logger.info("  Migration 12: handoff_completions table created.")

            # Table 3: roadmap_handoffs - junction table linking roadmap items to handoffs
            execute_query("""
                CREATE TABLE roadmap_handoffs (
                    roadmap_id VARCHAR(20) NOT NULL,
                    handoff_id VARCHAR(10) NOT NULL,
                    relationship VARCHAR(20) NOT NULL,
                    created_at DATETIME2 DEFAULT GETDATE(),
                    CONSTRAINT PK_roadmap_handoffs PRIMARY KEY (roadmap_id, handoff_id),
                    CONSTRAINT CK_roadmap_handoff_rel CHECK (relationship IN ('IMPLEMENTS', 'FIXES', 'TESTS', 'ENHANCES')),
                    CONSTRAINT FK_roadmap_handoff_ho FOREIGN KEY (handoff_id) REFERENCES handoff_requests(id)
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_roadmap_ho_roadmap ON roadmap_handoffs(roadmap_id)", fetch="none")
            execute_query("CREATE INDEX idx_roadmap_ho_handoff ON roadmap_handoffs(handoff_id)", fetch="none")
            logger.info("  Migration 12: roadmap_handoffs table created.")

            logger.info("  Migration 12: All handoff lifecycle tables created successfully.")
        else:
            logger.info("  Migration 12: handoff_requests table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 12 warning: {e}")

    # Migration 13: Ensure roadmap_sprints has project_id and FK/index (MP-011)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'roadmap_sprints' AND COLUMN_NAME = 'project_id'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 13: Adding project_id to roadmap_sprints...")
            execute_query("ALTER TABLE roadmap_sprints ADD project_id NVARCHAR(36) NULL", fetch="none")
            execute_query("""
                IF NOT EXISTS (
                    SELECT 1
                    FROM sys.foreign_keys
                    WHERE name = 'FK_roadmap_sprints_project'
                )
                BEGIN
                    ALTER TABLE roadmap_sprints
                    ADD CONSTRAINT FK_roadmap_sprints_project
                    FOREIGN KEY (project_id) REFERENCES roadmap_projects(id)
                END
            """, fetch="none")
            execute_query("""
                IF NOT EXISTS (
                    SELECT 1
                    FROM sys.indexes
                    WHERE name = 'idx_roadmap_sprints_project'
                      AND object_id = OBJECT_ID('roadmap_sprints')
                )
                BEGIN
                    CREATE INDEX idx_roadmap_sprints_project ON roadmap_sprints(project_id)
                END
            """, fetch="none")
            logger.info("  Migration 13: project_id added to roadmap_sprints.")
        else:
            logger.info("  Migration 13: roadmap_sprints.project_id already exists.")
    except Exception as e:
        logger.warning(f"  Migration 13 warning: {e}")

    # Migration 14: Ensure roadmap_requirements.description exists (MP-010)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'roadmap_requirements' AND COLUMN_NAME = 'description'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 14: Adding description to roadmap_requirements...")
            execute_query("ALTER TABLE roadmap_requirements ADD description NVARCHAR(MAX) NULL", fetch="none")
            logger.info("  Migration 14: description added to roadmap_requirements.")
        else:
            logger.info("  Migration 14: roadmap_requirements.description already exists.")
    except Exception as e:
        logger.warning(f"  Migration 14 warning: {e}")

    # Migration 15: Fix roadmap_handoffs handoff_id size/type compatibility (MP-003)
    try:
        type_result = execute_query("""
            SELECT DATA_TYPE as data_type, CHARACTER_MAXIMUM_LENGTH as max_len
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'roadmap_handoffs' AND COLUMN_NAME = 'handoff_id'
        """, fetch="one")
        if type_result and type_result.get('max_len') == 10:
            logger.info("  Migration 15: Expanding roadmap_handoffs.handoff_id to NVARCHAR(36)...")
            execute_query("""
                DECLARE @fk_name NVARCHAR(128)
                SELECT @fk_name = fk.name
                FROM sys.foreign_keys fk
                JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
                JOIN sys.columns c ON fkc.parent_object_id = c.object_id AND fkc.parent_column_id = c.column_id
                WHERE fk.parent_object_id = OBJECT_ID('roadmap_handoffs')
                  AND c.name = 'handoff_id'

                IF @fk_name IS NOT NULL
                BEGIN
                    EXEC('ALTER TABLE roadmap_handoffs DROP CONSTRAINT ' + @fk_name)
                END
            """, fetch="none")
            execute_query("ALTER TABLE roadmap_handoffs ALTER COLUMN handoff_id NVARCHAR(36) NOT NULL", fetch="none")
            logger.info("  Migration 15: roadmap_handoffs.handoff_id type updated.")
        else:
            logger.info("  Migration 15: roadmap_handoffs.handoff_id already compatible.")
    except Exception as e:
        logger.warning(f"  Migration 15 warning: {e}")

    # Migration 16: Create requirement↔handoff UUID junction table (MP-003/MP-015)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'roadmap_requirement_handoffs'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 16: Creating roadmap_requirement_handoffs table...")
            execute_query("""
                CREATE TABLE roadmap_requirement_handoffs (
                    requirement_id NVARCHAR(36) NOT NULL,
                    handoff_id UNIQUEIDENTIFIER NOT NULL,
                    source NVARCHAR(20) DEFAULT 'content_parse',
                    created_at DATETIME2 DEFAULT GETDATE(),
                    CONSTRAINT PK_roadmap_requirement_handoffs PRIMARY KEY (requirement_id, handoff_id),
                    CONSTRAINT FK_rrh_requirement FOREIGN KEY (requirement_id) REFERENCES roadmap_requirements(id),
                    CONSTRAINT FK_rrh_handoff FOREIGN KEY (handoff_id) REFERENCES mcp_handoffs(id)
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_rrh_handoff ON roadmap_requirement_handoffs(handoff_id)", fetch="none")
            execute_query("CREATE INDEX idx_rrh_requirement ON roadmap_requirement_handoffs(requirement_id)", fetch="none")
            logger.info("  Migration 16: roadmap_requirement_handoffs table created.")
        else:
            logger.info("  Migration 16: roadmap_requirement_handoffs already exists.")
    except Exception as e:
        logger.warning(f"  Migration 16 warning: {e}")

    # Migration 17: Create roadmap_categories table + link to roadmap_projects (MP-021)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'roadmap_categories'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 17: Creating roadmap_categories table...")
            execute_query("""
                CREATE TABLE roadmap_categories (
                    id NVARCHAR(36) PRIMARY KEY DEFAULT NEWID(),
                    name NVARCHAR(100) NOT NULL UNIQUE,
                    display_order INT DEFAULT 0,
                    created_at DATETIME2 DEFAULT GETDATE()
                )
            """, fetch="none")
            # Seed initial categories
            execute_query("""
                INSERT INTO roadmap_categories (id, name, display_order) VALUES
                ('cat-software', 'software', 1),
                ('cat-personal', 'personal', 2),
                ('cat-infrastructure', 'infrastructure', 3)
            """, fetch="none")
            logger.info("  Migration 17: roadmap_categories table created and seeded.")
        else:
            logger.info("  Migration 17: roadmap_categories table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 17 warning: {e}")

    # Migration 17b: Add category_id FK to roadmap_projects (MP-021)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'roadmap_projects' AND COLUMN_NAME = 'category_id'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 17b: Adding category_id to roadmap_projects...")
            execute_query(
                "ALTER TABLE roadmap_projects ADD category_id NVARCHAR(36) NULL",
                fetch="none"
            )
            execute_query("""
                IF NOT EXISTS (
                    SELECT 1 FROM sys.foreign_keys
                    WHERE name = 'FK_roadmap_projects_category'
                )
                BEGIN
                    ALTER TABLE roadmap_projects
                    ADD CONSTRAINT FK_roadmap_projects_category
                    FOREIGN KEY (category_id) REFERENCES roadmap_categories(id)
                END
            """, fetch="none")
            # Backfill existing projects with categories
            execute_query("""
                UPDATE roadmap_projects SET category_id = 'cat-software'
                WHERE code IN ('HL', 'AF', 'EM', 'SF', 'MP')
            """, fetch="none")
            execute_query("""
                UPDATE roadmap_projects SET category_id = 'cat-infrastructure'
                WHERE code = 'PM'
            """, fetch="none")
            execute_query("""
                UPDATE roadmap_projects SET category_id = 'cat-personal'
                WHERE category_id IS NULL
            """, fetch="none")
            logger.info("  Migration 17b: category_id added and backfilled.")
        else:
            logger.info("  Migration 17b: roadmap_projects.category_id already exists.")
    except Exception as e:
        logger.warning(f"  Migration 17b warning: {e}")

    # Migration 18: Create roadmap_tasks table (MP-012)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'roadmap_tasks'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 18: Creating roadmap_tasks table...")
            execute_query("""
                CREATE TABLE roadmap_tasks (
                    id NVARCHAR(36) PRIMARY KEY DEFAULT NEWID(),
                    requirement_id NVARCHAR(36) NOT NULL,
                    title NVARCHAR(500) NOT NULL,
                    description NVARCHAR(MAX),
                    status NVARCHAR(20) DEFAULT 'backlog'
                        CHECK (status IN ('backlog', 'in_progress', 'done')),
                    priority NVARCHAR(10) DEFAULT 'P2'
                        CHECK (priority IN ('P1', 'P2', 'P3')),
                    assignee NVARCHAR(100),
                    created_at DATETIME2 DEFAULT GETDATE(),
                    updated_at DATETIME2 DEFAULT GETDATE(),
                    CONSTRAINT FK_roadmap_tasks_req FOREIGN KEY (requirement_id)
                        REFERENCES roadmap_requirements(id)
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_roadmap_tasks_req ON roadmap_tasks(requirement_id)", fetch="none")
            execute_query("CREATE INDEX idx_roadmap_tasks_status ON roadmap_tasks(status)", fetch="none")
            logger.info("  Migration 18: roadmap_tasks table created.")
        else:
            logger.info("  Migration 18: roadmap_tasks table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 18 warning: {e}")

    # Migration 19: Create test_plans + test_cases tables (MP-013)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'test_plans'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 19: Creating test_plans and test_cases tables...")
            execute_query("""
                CREATE TABLE test_plans (
                    id NVARCHAR(36) PRIMARY KEY DEFAULT NEWID(),
                    requirement_id NVARCHAR(36) NOT NULL,
                    name NVARCHAR(200) NOT NULL,
                    created_at DATETIME2 DEFAULT GETDATE(),
                    CONSTRAINT FK_test_plans_req FOREIGN KEY (requirement_id)
                        REFERENCES roadmap_requirements(id)
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_test_plans_req ON test_plans(requirement_id)", fetch="none")
            execute_query("""
                CREATE TABLE test_cases (
                    id NVARCHAR(36) PRIMARY KEY DEFAULT NEWID(),
                    test_plan_id NVARCHAR(36) NOT NULL,
                    title NVARCHAR(500) NOT NULL,
                    expected_result NVARCHAR(MAX),
                    status NVARCHAR(20) DEFAULT 'pending'
                        CHECK (status IN ('pending', 'pass', 'fail', 'conditional_pass')),
                    executed_at DATETIME2,
                    CONSTRAINT FK_test_cases_plan FOREIGN KEY (test_plan_id)
                        REFERENCES test_plans(id)
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_test_cases_plan ON test_cases(test_plan_id)", fetch="none")
            logger.info("  Migration 19: test_plans and test_cases tables created.")
        else:
            logger.info("  Migration 19: test_plans table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 19 warning: {e}")

    # Migration 20: Create requirement_dependencies table (MP-014)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'requirement_dependencies'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 20: Creating requirement_dependencies table...")
            execute_query("""
                CREATE TABLE requirement_dependencies (
                    id NVARCHAR(36) PRIMARY KEY DEFAULT NEWID(),
                    requirement_id NVARCHAR(36) NOT NULL,
                    depends_on_id NVARCHAR(36) NOT NULL,
                    created_at DATETIME2 DEFAULT GETDATE(),
                    CONSTRAINT FK_reqdep_req FOREIGN KEY (requirement_id)
                        REFERENCES roadmap_requirements(id),
                    CONSTRAINT FK_reqdep_dep FOREIGN KEY (depends_on_id)
                        REFERENCES roadmap_requirements(id),
                    CONSTRAINT UQ_reqdep UNIQUE (requirement_id, depends_on_id)
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_reqdep_req ON requirement_dependencies(requirement_id)", fetch="none")
            execute_query("CREATE INDEX idx_reqdep_dep ON requirement_dependencies(depends_on_id)", fetch="none")
            logger.info("  Migration 20: requirement_dependencies table created.")
        else:
            logger.info("  Migration 20: requirement_dependencies table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 20 warning: {e}")

    # Migration 21: Update uat_results status to include conditional_pass (MP-007)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM sys.check_constraints
            WHERE parent_object_id = OBJECT_ID('uat_results')
              AND definition LIKE '%conditional_pass%'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 21: Updating uat_results status for conditional_pass...")
            execute_query("""
                DECLARE @constraint_name NVARCHAR(128)
                SELECT @constraint_name = name
                FROM sys.check_constraints
                WHERE parent_object_id = OBJECT_ID('uat_results')
                  AND definition LIKE '%status%'

                IF @constraint_name IS NOT NULL
                BEGIN
                    EXEC('ALTER TABLE uat_results DROP CONSTRAINT ' + @constraint_name)
                END
            """, fetch="none")
            execute_query("""
                ALTER TABLE uat_results
                ADD CONSTRAINT CK_uat_results_status_v2
                CHECK (status IN ('passed', 'failed', 'pending', 'conditional_pass'))
            """, fetch="none")
            logger.info("  Migration 21: uat_results now supports conditional_pass.")
        else:
            logger.info("  Migration 21: uat_results already supports conditional_pass.")
    except Exception as e:
        logger.warning(f"  Migration 21 warning: {e}")

    # Migration 22: Expand roadmap_requirements status CHECK to include conditional_pass, blocked, superseded (MP-MS2)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM sys.check_constraints
            WHERE parent_object_id = OBJECT_ID('roadmap_requirements')
              AND definition LIKE '%conditional_pass%'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 22: Expanding roadmap_requirements status CHECK constraint...")
            # Drop the existing status constraint dynamically
            execute_query("""
                DECLARE @constraint_name NVARCHAR(128)
                SELECT @constraint_name = name
                FROM sys.check_constraints
                WHERE parent_object_id = OBJECT_ID('roadmap_requirements')
                  AND definition LIKE '%status%'

                IF @constraint_name IS NOT NULL
                BEGIN
                    EXEC('ALTER TABLE roadmap_requirements DROP CONSTRAINT ' + @constraint_name)
                END
            """, fetch="none")
            # Recreate with all valid statuses
            execute_query("""
                ALTER TABLE roadmap_requirements
                ADD CONSTRAINT CK_roadmap_requirements_status
                CHECK (status IN ('backlog', 'planned', 'in_progress', 'uat', 'needs_fixes', 'done', 'blocked', 'superseded', 'conditional_pass'))
            """, fetch="none")
            logger.info("  Migration 22: roadmap_requirements status constraint expanded.")
        else:
            logger.info("  Migration 22: roadmap_requirements status constraint already includes conditional_pass.")
    except Exception as e:
        logger.warning(f"  Migration 22 warning: {e}")

    # Migration 23: Migrate old status values to new pipeline states + update CHECK constraint (MP-MS3)
    try:
        # Check if migration already ran by looking for new status values in constraint
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM sys.check_constraints
            WHERE parent_object_id = OBJECT_ID('roadmap_requirements')
              AND definition LIKE '%executing%'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 23: Migrating status values to pipeline states...")

            # Count before
            before = execute_query("SELECT status, COUNT(*) as cnt FROM roadmap_requirements GROUP BY status", fetch="all") or []
            total_before = sum(int(r.get('cnt', 0)) for r in before)
            for r in before:
                logger.info(f"    Before: {r['status']} = {r['cnt']}")
            logger.info(f"    Total before: {total_before}")

            # MUST drop old CHECK constraint FIRST — new values violate old constraint
            execute_query("""
                DECLARE @constraint_name NVARCHAR(128)
                SELECT @constraint_name = name
                FROM sys.check_constraints
                WHERE parent_object_id = OBJECT_ID('roadmap_requirements')
                  AND definition LIKE '%status%'

                IF @constraint_name IS NOT NULL
                BEGIN
                    EXEC('ALTER TABLE roadmap_requirements DROP CONSTRAINT ' + @constraint_name)
                END
            """, fetch="none")
            logger.info("    Old CHECK constraint dropped.")

            # Migrate status values (constraint-free now)
            execute_query("UPDATE roadmap_requirements SET status = 'executing' WHERE status = 'in_progress'", fetch="none")
            execute_query("UPDATE roadmap_requirements SET status = 'closed' WHERE status = 'done'", fetch="none")
            execute_query("UPDATE roadmap_requirements SET status = 'backlog' WHERE status = 'planned'", fetch="none")
            execute_query("UPDATE roadmap_requirements SET status = 'needs_fixes' WHERE status = 'blocked'", fetch="none")
            execute_query("UPDATE roadmap_requirements SET status = 'executing' WHERE status = 'active'", fetch="none")
            execute_query("UPDATE roadmap_requirements SET status = 'deferred' WHERE status = 'superseded'", fetch="none")
            execute_query("UPDATE roadmap_requirements SET status = 'uat' WHERE status = 'conditional_pass'", fetch="none")
            # 'backlog' stays 'backlog', 'deferred' stays 'deferred'

            # Add new CHECK constraint with 10 pipeline states
            execute_query("""
                ALTER TABLE roadmap_requirements
                ADD CONSTRAINT CK_roadmap_requirements_status_v3
                CHECK (status IN ('backlog','draft','prompt_ready','approved','executing','handoff','uat','closed','needs_fixes','deferred'))
            """, fetch="none")

            # Count after
            after = execute_query("SELECT status, COUNT(*) as cnt FROM roadmap_requirements GROUP BY status", fetch="all") or []
            total_after = sum(int(r.get('cnt', 0)) for r in after)
            for r in after:
                logger.info(f"    After: {r['status']} = {r['cnt']}")
            logger.info(f"    Total after: {total_after}")

            if total_before != total_after:
                logger.error(f"  Migration 23: COUNT MISMATCH! Before={total_before}, After={total_after}")
            else:
                logger.info(f"  Migration 23: Status migration complete. {total_after} items, no data loss.")
        else:
            logger.info("  Migration 23: Status values already migrated to pipeline states.")
    except Exception as e:
        logger.warning(f"  Migration 23 warning: {e}")

    # Migration 24: Add WIP tracking fields to roadmap_requirements (MP-MS3)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'roadmap_requirements' AND COLUMN_NAME = 'status_updated_at'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 24: Adding WIP tracking fields to roadmap_requirements...")
            execute_query("ALTER TABLE roadmap_requirements ADD prompt_url NVARCHAR(500) NULL", fetch="none")
            execute_query("ALTER TABLE roadmap_requirements ADD portfolio_rag_url NVARCHAR(500) NULL", fetch="none")
            execute_query("ALTER TABLE roadmap_requirements ADD status_updated_at DATETIME2 DEFAULT GETDATE()", fetch="none")
            logger.info("  Migration 24: WIP tracking fields added.")
        else:
            logger.info("  Migration 24: WIP tracking fields already exist.")
    except Exception as e:
        logger.warning(f"  Migration 24 warning: {e}")

    # Migration 25: Create requirement_history table + auto-tracking trigger (MP-MS3)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'requirement_history'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 25: Creating requirement_history table...")
            execute_query("""
                CREATE TABLE requirement_history (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    requirement_id NVARCHAR(36) NOT NULL,
                    changed_at DATETIME2 DEFAULT GETDATE(),
                    changed_by NVARCHAR(50) NOT NULL DEFAULT 'system',
                    field_name NVARCHAR(50) NOT NULL,
                    old_value NVARCHAR(500) NULL,
                    new_value NVARCHAR(500) NULL,
                    sprint_id NVARCHAR(50) NULL,
                    notes NVARCHAR(1000) NULL,
                    CONSTRAINT FK_req_history_req FOREIGN KEY (requirement_id) REFERENCES roadmap_requirements(id)
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_req_history_req_id ON requirement_history(requirement_id)", fetch="none")
            execute_query("CREATE INDEX idx_req_history_changed_at ON requirement_history(changed_at)", fetch="none")
            logger.info("  Migration 25: requirement_history table created.")

            # Create trigger for automatic history tracking
            logger.info("  Migration 25: Creating auto-history trigger...")
            execute_query("""
                CREATE TRIGGER trg_requirement_history
                ON roadmap_requirements
                AFTER UPDATE
                AS
                BEGIN
                    SET NOCOUNT ON;

                    INSERT INTO requirement_history (requirement_id, changed_by, field_name, old_value, new_value)
                    SELECT i.id, 'system', 'status', d.status, i.status
                    FROM inserted i
                    JOIN deleted d ON i.id = d.id
                    WHERE ISNULL(i.status, '') != ISNULL(d.status, '');

                    INSERT INTO requirement_history (requirement_id, changed_by, field_name, old_value, new_value)
                    SELECT i.id, 'system', 'priority', d.priority, i.priority
                    FROM inserted i
                    JOIN deleted d ON i.id = d.id
                    WHERE ISNULL(i.priority, '') != ISNULL(d.priority, '');

                    UPDATE r SET status_updated_at = GETDATE()
                    FROM roadmap_requirements r
                    JOIN inserted i ON r.id = i.id
                    JOIN deleted d ON r.id = d.id
                    WHERE ISNULL(i.status, '') != ISNULL(d.status, '');
                END
            """, fetch="none")
            logger.info("  Migration 25: Auto-history trigger created.")
        else:
            logger.info("  Migration 25: requirement_history table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 25 warning: {e}")

    # Migration 26: Create requirement_attachments table (MP-MS3 Phase 3)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'requirement_attachments'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 26: Creating requirement_attachments table...")
            execute_query("""
                CREATE TABLE requirement_attachments (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    requirement_id NVARCHAR(36) NOT NULL,
                    filename NVARCHAR(255) NOT NULL,
                    content_type NVARCHAR(100) NOT NULL,
                    file_size INT NOT NULL,
                    storage_key NVARCHAR(500) NOT NULL,
                    uploaded_by NVARCHAR(50) NOT NULL,
                    description NVARCHAR(500) NULL,
                    created_at DATETIME2 DEFAULT GETDATE(),
                    CONSTRAINT FK_req_attach_req FOREIGN KEY (requirement_id) REFERENCES roadmap_requirements(id)
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_req_attach_req_id ON requirement_attachments(requirement_id)", fetch="none")
            logger.info("  Migration 26: requirement_attachments table created.")
        else:
            logger.info("  Migration 26: requirement_attachments table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 26 warning: {e}")

    # Migration 27: Create cc_prompts table (MP-MS3 Phase 3)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'cc_prompts'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 27: Creating cc_prompts table...")
            execute_query("""
                CREATE TABLE cc_prompts (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    sprint_id NVARCHAR(50) NOT NULL,
                    project_id NVARCHAR(36) NOT NULL,
                    content NVARCHAR(MAX) NOT NULL,
                    status NVARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft','prompt_ready','approved','sent','completed')),
                    version_before NVARCHAR(20) NULL,
                    version_after NVARCHAR(20) NULL,
                    estimated_hours DECIMAL(4,1) NULL,
                    approved_at DATETIME2 NULL,
                    approved_by NVARCHAR(50) NULL,
                    handoff_id NVARCHAR(100) NULL,
                    created_at DATETIME2 DEFAULT GETDATE(),
                    updated_at DATETIME2 DEFAULT GETDATE(),
                    CONSTRAINT FK_cc_prompts_project FOREIGN KEY (project_id) REFERENCES roadmap_projects(id)
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_cc_prompts_sprint ON cc_prompts(sprint_id)", fetch="none")
            execute_query("CREATE INDEX idx_cc_prompts_status ON cc_prompts(status)", fetch="none")
            logger.info("  Migration 27: cc_prompts table created.")
        else:
            logger.info("  Migration 27: cc_prompts table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 27 warning: {e}")

    # Migration 28: Create requirement_links table (MP-MS3 Phase 4)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'requirement_links'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 28: Creating requirement_links table...")
            execute_query("""
                CREATE TABLE requirement_links (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    requirement_id NVARCHAR(36) NOT NULL,
                    url NVARCHAR(500) NOT NULL,
                    link_type NVARCHAR(50) NOT NULL,
                    description NVARCHAR(500) NULL,
                    created_at DATETIME2 DEFAULT GETDATE(),
                    CONSTRAINT FK_req_links_req FOREIGN KEY (requirement_id) REFERENCES roadmap_requirements(id)
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_req_links_req_id ON requirement_links(requirement_id)", fetch="none")
            logger.info("  Migration 28: requirement_links table created.")
        else:
            logger.info("  Migration 28: requirement_links table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 28 warning: {e}")

    # Migration 29: Add archived column to roadmap_projects (MP-036)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'roadmap_projects' AND COLUMN_NAME = 'archived'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 29: Adding archived column to roadmap_projects...")
            execute_query("""
                ALTER TABLE roadmap_projects ADD archived BIT DEFAULT 0 NOT NULL
            """, fetch="none")
            logger.info("  Migration 29: archived column added.")
        else:
            logger.info("  Migration 29: archived column already exists.")
    except Exception as e:
        logger.warning(f"  Migration 29 warning: {e}")

    # Migration 30: Update roadmap_projects status CHECK constraint to include 'archived' (MP-036/MP-RECONCILE-002)
    try:
        # Check if constraint already allows 'archived'
        result = execute_query("""
            SELECT cc.definition
            FROM sys.check_constraints cc
            JOIN sys.columns col ON cc.parent_object_id = col.object_id AND cc.parent_column_id = col.column_id
            WHERE OBJECT_NAME(cc.parent_object_id) = 'roadmap_projects' AND col.name = 'status'
        """, fetch="one")
        if result and 'archived' not in (result.get('definition') or ''):
            logger.info("  Migration 30: Updating roadmap_projects status CHECK to include 'archived'...")
            # Find and drop the existing constraint
            constraints = execute_query("""
                SELECT cc.name
                FROM sys.check_constraints cc
                JOIN sys.columns col ON cc.parent_object_id = col.object_id AND cc.parent_column_id = col.column_id
                WHERE OBJECT_NAME(cc.parent_object_id) = 'roadmap_projects' AND col.name = 'status'
            """, fetch="all") or []
            for c in constraints:
                execute_query(f"ALTER TABLE roadmap_projects DROP CONSTRAINT [{c['name']}]", fetch="none")
            # Add new constraint with 'archived'
            execute_query("""
                ALTER TABLE roadmap_projects ADD CONSTRAINT CK_roadmap_projects_status
                CHECK (status IN ('active','stable','maintenance','paused','archived'))
            """, fetch="none")
            logger.info("  Migration 30: roadmap_projects status constraint updated to include 'archived'.")
        else:
            logger.info("  Migration 30: roadmap_projects status constraint already includes 'archived'.")
    except Exception as e:
        logger.warning(f"  Migration 30 warning: {e}")

    # Migration 31: Add 'vision' to roadmap_requirements type CHECK constraint (MP-VISION-ITEM)
    try:
        result = execute_query("""
            SELECT cc.definition
            FROM sys.check_constraints cc
            JOIN sys.columns col ON cc.parent_object_id = col.object_id AND cc.parent_column_id = col.column_id
            WHERE OBJECT_NAME(cc.parent_object_id) = 'roadmap_requirements' AND col.name = 'type'
        """, fetch="one")
        if result and 'vision' not in (result.get('definition') or ''):
            logger.info("  Migration 31: Updating roadmap_requirements type CHECK to include 'vision'...")
            constraints = execute_query("""
                SELECT cc.name
                FROM sys.check_constraints cc
                JOIN sys.columns col ON cc.parent_object_id = col.object_id AND cc.parent_column_id = col.column_id
                WHERE OBJECT_NAME(cc.parent_object_id) = 'roadmap_requirements' AND col.name = 'type'
            """, fetch="all") or []
            for c in constraints:
                execute_query(f"ALTER TABLE roadmap_requirements DROP CONSTRAINT [{c['name']}]", fetch="none")
            execute_query("""
                ALTER TABLE roadmap_requirements ADD CONSTRAINT CK_roadmap_requirements_type
                CHECK (type IN ('feature','bug','enhancement','task','vision'))
            """, fetch="none")
            logger.info("  Migration 31: roadmap_requirements type constraint updated to include 'vision'.")
        else:
            logger.info("  Migration 31: roadmap_requirements type constraint already includes 'vision'.")
    except Exception as e:
        logger.warning(f"  Migration 31 warning: {e}")

    # Migration 32: PF5-MS1 — Extend status CHECK to include lifecycle values
    try:
        result = execute_query("""
            SELECT cc.definition
            FROM sys.check_constraints cc
            JOIN sys.columns col ON cc.parent_object_id = col.object_id AND cc.parent_column_id = col.column_id
            WHERE OBJECT_NAME(cc.parent_object_id) = 'roadmap_requirements' AND col.name = 'status'
        """, fetch="one")
        if result and 'req_created' not in (result.get('definition') or ''):
            logger.info("  Migration 32: Extending roadmap_requirements status CHECK to lifecycle values (PF5-MS1)...")
            constraints = execute_query("""
                SELECT cc.name
                FROM sys.check_constraints cc
                JOIN sys.columns col ON cc.parent_object_id = col.object_id AND cc.parent_column_id = col.column_id
                WHERE OBJECT_NAME(cc.parent_object_id) = 'roadmap_requirements' AND col.name = 'status'
            """, fetch="all") or []
            for c in constraints:
                execute_query(f"ALTER TABLE roadmap_requirements DROP CONSTRAINT [{c['name']}]", fetch="none")
            execute_query("""
                ALTER TABLE roadmap_requirements ADD CONSTRAINT chk_req_status
                CHECK (status IN (
                    'backlog', 'executing', 'closed', 'archived',
                    'req_created', 'cai_processing', 'cc_prompt_ready', 'approved',
                    'cc_processing', 'cc_handoff_ready', 'cai_review',
                    'uat_submitted', 'cai_final_review', 'done', 'rework'
                ))
            """, fetch="none")
            logger.info("  Migration 32: status constraint extended to include lifecycle values.")
        else:
            logger.info("  Migration 32: status constraint already includes lifecycle values.")
    except Exception as e:
        logger.warning(f"  Migration 32 warning: {e}")

    # Migration 33: PF5-MS1 v2 — Update status CHECK to new 11 lifecycle states
    try:
        result = execute_query("""
            SELECT cc.definition
            FROM sys.check_constraints cc
            JOIN sys.columns col ON cc.parent_object_id = col.object_id AND cc.parent_column_id = col.column_id
            WHERE OBJECT_NAME(cc.parent_object_id) = 'roadmap_requirements' AND col.name = 'status'
        """, fetch="one")
        if result and 'req_approved' not in (result.get('definition') or ''):
            logger.info("  Migration 33: Updating status CHECK to new lifecycle states (PF5-MS1 v2)...")
            constraints = execute_query("""
                SELECT cc.name
                FROM sys.check_constraints cc
                JOIN sys.columns col ON cc.parent_object_id = col.object_id AND cc.parent_column_id = col.column_id
                WHERE OBJECT_NAME(cc.parent_object_id) = 'roadmap_requirements' AND col.name = 'status'
            """, fetch="all") or []
            for c in constraints:
                execute_query(f"ALTER TABLE roadmap_requirements DROP CONSTRAINT [{c['name']}]", fetch="none")
            # First migrate existing data from old lifecycle states to new ones
            migrations_map = {
                'cai_processing': 'cai_designing',
                'approved': 'req_approved',
                'cc_processing': 'cc_executing',
                'cc_handoff_ready': 'cc_complete',
                'cai_review': 'uat_ready',
                'uat_submitted': 'uat_pass',
                'cai_final_review': 'uat_fail',
                'archived': 'closed',
            }
            for old_val, new_val in migrations_map.items():
                execute_query(
                    f"UPDATE roadmap_requirements SET status = ? WHERE status = ?",
                    (new_val, old_val), fetch="none"
                )
            execute_query("""
                ALTER TABLE roadmap_requirements ADD CONSTRAINT chk_req_status_v2
                CHECK (status IN (
                    'req_created', 'req_approved', 'cai_designing', 'cc_prompt_ready',
                    'cc_executing', 'cc_complete', 'uat_ready', 'uat_pass', 'uat_fail',
                    'done', 'rework',
                    'backlog', 'executing', 'closed'
                ))
            """, fetch="none")
            logger.info("  Migration 33: status constraint updated to new lifecycle states.")
        else:
            logger.info("  Migration 33: status constraint already has new lifecycle states.")
    except Exception as e:
        logger.warning(f"  Migration 33 warning: {e}")

    # Migration 34: Create lessons_learned table (MP-LL-001)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'lessons_learned'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 34: Creating lessons_learned table...")
            execute_query("""
                CREATE TABLE lessons_learned (
                    id                NVARCHAR(20)   PRIMARY KEY,
                    project           NVARCHAR(50)   NOT NULL,
                    category          NVARCHAR(20)   NOT NULL
                        CHECK (category IN ('process','technical','architecture','quality')),
                    lesson            NVARCHAR(MAX)  NOT NULL,
                    source_sprint     NVARCHAR(50)   NULL,
                    target            NVARCHAR(30)   NOT NULL
                        CHECK (target IN ('bootstrap','pk.md','cai_memory','standards')),
                    target_file       NVARCHAR(255)  NULL,
                    status            NVARCHAR(20)   NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft','approved','applied','rejected')),
                    proposed_by       NVARCHAR(10)   NOT NULL DEFAULT 'cc'
                        CHECK (proposed_by IN ('cc','cai','pl')),
                    created_at        DATETIME       NOT NULL DEFAULT GETDATE(),
                    approved_at       DATETIME       NULL,
                    applied_at        DATETIME       NULL,
                    applied_in_sprint NVARCHAR(50)   NULL,
                    rag_ingested      BIT            NOT NULL DEFAULT 0,
                    rag_ingested_at   DATETIME       NULL
                )
            """, fetch="none")
            execute_query("CREATE INDEX ix_ll_project ON lessons_learned(project)", fetch="none")
            execute_query("CREATE INDEX ix_ll_status ON lessons_learned(status)", fetch="none")
            execute_query("CREATE INDEX ix_ll_project_status ON lessons_learned(project, status)", fetch="none")
            logger.info("  Migration 34: lessons_learned table created with indexes.")
        else:
            logger.info("  Migration 34: lessons_learned table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 34 warning: {e}")

    # Migration 35: Create uat_pages table (MP-UAT-GEN)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'uat_pages'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 35: Creating uat_pages table...")
            execute_query("""
                CREATE TABLE uat_pages (
                    id               UNIQUEIDENTIFIER  PRIMARY KEY DEFAULT NEWID(),
                    handoff_id       UNIQUEIDENTIFIER  NOT NULL,
                    project          NVARCHAR(50)      NOT NULL,
                    sprint_code      NVARCHAR(50)      NULL,
                    pth              NVARCHAR(10)      NULL,
                    version          NVARCHAR(20)      NULL,
                    deploy_url       NVARCHAR(500)     NULL,
                    test_cases_json  NVARCHAR(MAX)     NOT NULL,
                    cai_review_json  NVARCHAR(MAX)     NULL,
                    html_content     NVARCHAR(MAX)     NOT NULL,
                    status           NVARCHAR(20)      NOT NULL DEFAULT 'ready'
                        CHECK (status IN ('ready','in_progress','submitted')),
                    created_at       DATETIME2         NOT NULL DEFAULT GETDATE(),
                    submitted_at     DATETIME2         NULL
                )
            """, fetch="none")
            execute_query("CREATE INDEX ix_uat_pages_handoff ON uat_pages(handoff_id)", fetch="none")
            execute_query("CREATE INDEX ix_uat_pages_project ON uat_pages(project)", fetch="none")
            logger.info("  Migration 35: uat_pages table created with indexes.")
        else:
            logger.info("  Migration 35: uat_pages table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 35 warning: {e}")

    # Migration 36: Create handoff_verifications table + add columns to mcp_handoffs (MP-VERIFY-001)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'handoff_verifications'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 36: Creating handoff_verifications table...")
            execute_query("""
                CREATE TABLE handoff_verifications (
                    id                  UNIQUEIDENTIFIER  PRIMARY KEY DEFAULT NEWID(),
                    handoff_id          UNIQUEIDENTIFIER  NOT NULL,
                    verification_status NVARCHAR(20)      NOT NULL DEFAULT 'pending'
                        CHECK (verification_status IN ('pending','verified','mismatch','partial','skipped')),
                    results_json        NVARCHAR(MAX)     NULL,
                    verified_at         DATETIME2         NULL,
                    created_at          DATETIME2         NOT NULL DEFAULT GETDATE()
                )
            """, fetch="none")
            execute_query("CREATE INDEX ix_handoff_verif ON handoff_verifications(handoff_id)", fetch="none")
            logger.info("  Migration 36: handoff_verifications table created.")
        else:
            logger.info("  Migration 36: handoff_verifications table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 36 warning: {e}")

    # Migration 37: Add verification_status and evidence_json columns to mcp_handoffs (MP-VERIFY-001)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'mcp_handoffs' AND COLUMN_NAME = 'verification_status'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 37: Adding verification columns to mcp_handoffs...")
            execute_query("ALTER TABLE mcp_handoffs ADD verification_status NVARCHAR(20) NULL", fetch="none")
            execute_query("ALTER TABLE mcp_handoffs ADD evidence_json NVARCHAR(MAX) NULL", fetch="none")
            logger.info("  Migration 37: verification columns added.")
        else:
            logger.info("  Migration 37: verification columns already exist.")
    except Exception as e:
        logger.warning(f"  Migration 37 warning: {e}")

    # Migration 38: Add uat_url column to roadmap_requirements (MP-UAT-TAB-001)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'roadmap_requirements' AND COLUMN_NAME = 'uat_url'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 38: Adding uat_url column to roadmap_requirements...")
            execute_query("ALTER TABLE roadmap_requirements ADD uat_url NVARCHAR(500) NULL", fetch="none")
            logger.info("  Migration 38: uat_url column added.")
        else:
            logger.info("  Migration 38: uat_url column already exists.")
    except Exception as e:
        logger.warning(f"  Migration 38 warning: {e}")

    # Migration 39: Add pth column to roadmap_requirements (MP-PTH-FIELD-001)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'roadmap_requirements' AND COLUMN_NAME = 'pth'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 39: Adding pth column to roadmap_requirements...")
            execute_query("ALTER TABLE roadmap_requirements ADD pth NVARCHAR(4) NULL", fetch="none")
            execute_query("CREATE INDEX idx_requirements_pth ON roadmap_requirements(pth)", fetch="none")
            logger.info("  Migration 39: pth column and index added.")
        else:
            logger.info("  Migration 39: pth column already exists.")
    except Exception as e:
        logger.warning(f"  Migration 39 warning: {e}")

    # Migration 40: Create pth_registry table (MP-PTH-FIELD-001)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'pth_registry'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 40: Creating pth_registry table...")
            execute_query("""
                CREATE TABLE pth_registry (
                    pth              NVARCHAR(4)   NOT NULL PRIMARY KEY,
                    requirement_code NVARCHAR(50)  NOT NULL,
                    requirement_id   NVARCHAR(100) NOT NULL,
                    assigned_at      DATETIME2     NOT NULL DEFAULT GETDATE(),
                    assigned_by      NVARCHAR(20)  NOT NULL
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_pth_registry_req ON pth_registry(requirement_code)", fetch="none")
            logger.info("  Migration 40: pth_registry table created.")
        else:
            logger.info("  Migration 40: pth_registry table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 40 warning: {e}")

    # Migration 41: Backfill all requirements with null pth (MP-PTH-FIELD-001)
    try:
        null_count = execute_query("""
            SELECT COUNT(*) as cnt FROM roadmap_requirements WHERE pth IS NULL
        """, fetch="one")
        if null_count and null_count['cnt'] > 0:
            logger.info(f"  Migration 41: Backfilling {null_count['cnt']} requirements with PTH codes...")
            rows = execute_query("""
                SELECT id, code FROM roadmap_requirements WHERE pth IS NULL
            """, fetch="all") or []

            import secrets
            existing_pths = set()
            # Load existing PTH values from registry
            existing = execute_query("SELECT pth FROM pth_registry", fetch="all") or []
            for e in existing:
                existing_pths.add(e['pth'])

            backfilled = 0
            for row in rows:
                # Generate unique 4-char hex code
                attempts = 0
                while True:
                    candidate = ''.join(secrets.choice('0123456789ABCDEF') for _ in range(4))
                    if candidate not in existing_pths:
                        break
                    attempts += 1
                    if attempts > 1000:
                        logger.error("  Migration 41: Too many PTH collisions, stopping.")
                        break

                if candidate in existing_pths:
                    continue

                existing_pths.add(candidate)
                # Update requirement
                execute_query(
                    "UPDATE roadmap_requirements SET pth = ? WHERE id = ?",
                    (candidate, row['id']), fetch="none"
                )
                # Insert into registry
                try:
                    execute_query("""
                        INSERT INTO pth_registry (pth, requirement_code, requirement_id, assigned_by)
                        VALUES (?, ?, ?, 'backfill')
                    """, (candidate, row['code'], row['id']), fetch="none")
                except Exception as reg_err:
                    logger.warning(f"  Migration 41: Registry insert failed for {row['code']}: {reg_err}")
                backfilled += 1

            logger.info(f"  Migration 41: Backfilled {backfilled} requirements with PTH codes.")
        else:
            logger.info("  Migration 41: All requirements already have PTH codes.")
    except Exception as e:
        logger.warning(f"  Migration 41 warning: {e}")

    # Migration 42: Expand uat_pages status CHECK to include 'archived' (MP-PTH-FIELD-001 PTH-9)
    try:
        # Drop old CHECK constraint and recreate with 'archived' added
        result = execute_query("""
            SELECT name FROM sys.check_constraints
            WHERE parent_object_id = OBJECT_ID('uat_pages') AND definition LIKE '%status%'
        """, fetch="one")
        if result:
            constraint_name = result['name']
            # Check if 'archived' is already in the constraint
            chk = execute_query(f"""
                SELECT definition FROM sys.check_constraints WHERE name = '{constraint_name}'
            """, fetch="one")
            if chk and 'archived' not in chk.get('definition', ''):
                logger.info(f"  Migration 42: Expanding uat_pages status CHECK ({constraint_name})...")
                execute_query(f"ALTER TABLE uat_pages DROP CONSTRAINT [{constraint_name}]", fetch="none")
                execute_query("""
                    ALTER TABLE uat_pages ADD CONSTRAINT chk_uat_pages_status_v2
                    CHECK (status IN ('ready','in_progress','submitted','archived','active','passed','failed','pending'))
                """, fetch="none")
                logger.info("  Migration 42: uat_pages status CHECK updated.")
            else:
                logger.info("  Migration 42: uat_pages status CHECK already includes 'archived'.")
        else:
            logger.info("  Migration 42: No status CHECK constraint found on uat_pages.")
    except Exception as e:
        logger.warning(f"  Migration 42 warning: {e}")

    # Migration 43: Add pth column to mcp_handoffs for propagation (MP-PTH-FIELD-001)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'mcp_handoffs' AND COLUMN_NAME = 'pth'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 43: Adding pth column to mcp_handoffs...")
            execute_query("ALTER TABLE mcp_handoffs ADD pth NVARCHAR(4) NULL", fetch="none")
            logger.info("  Migration 43: pth column added to mcp_handoffs.")
        else:
            logger.info("  Migration 43: mcp_handoffs.pth already exists.")
    except Exception as e:
        logger.warning(f"  Migration 43 warning: {e}")

    # Migration 44: Expand uat_results status CHECK to include 'archived' (MP-UAT-GEN-FIXUP-001)
    try:
        result = execute_query("""
            SELECT name, definition FROM sys.check_constraints
            WHERE parent_object_id = OBJECT_ID('uat_results')
              AND definition LIKE '%status%'
        """, fetch="one")
        if result:
            if 'archived' not in (result.get('definition') or ''):
                constraint_name = result['name']
                logger.info(f"  Migration 44: Expanding uat_results status CHECK ({constraint_name})...")
                execute_query(f"ALTER TABLE uat_results DROP CONSTRAINT [{constraint_name}]", fetch="none")
                execute_query("""
                    ALTER TABLE uat_results
                    ADD CONSTRAINT CK_uat_results_status_v3
                    CHECK (status IN ('passed', 'failed', 'pending', 'conditional_pass', 'archived'))
                """, fetch="none")
                logger.info("  Migration 44: uat_results status CHECK updated to include 'archived'.")
            else:
                logger.info("  Migration 44: uat_results status CHECK already includes 'archived'.")
        else:
            logger.info("  Migration 44: No status CHECK constraint found on uat_results.")
    except Exception as e:
        logger.warning(f"  Migration 44 warning: {e}")

    # Migration 45: Add spec columns to uat_pages (MP-UAT-SERVER-001 / MP04)
    for col_name, col_def in [
        ("spec_source", "NVARCHAR(20)"),
        ("spec_locked_at", "DATETIME"),
        ("pl_submitted_at", "DATETIME"),
        ("spec_data", "NVARCHAR(MAX)"),
    ]:
        try:
            result = execute_query("""
                SELECT COUNT(*) as cnt
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'uat_pages' AND COLUMN_NAME = ?
            """, (col_name,), fetch="one")
            if result and result['cnt'] == 0:
                logger.info(f"  Migration 45: Adding {col_name} column to uat_pages...")
                execute_query(f"ALTER TABLE uat_pages ADD {col_name} {col_def}", fetch="none")
                logger.info(f"  Migration 45: {col_name} column added.")
            else:
                logger.info(f"  Migration 45: {col_name} already exists.")
        except Exception as e:
            logger.warning(f"  Migration 45 ({col_name}) warning: {e}")

    # Migration 46: Add conditional_pass to uat_pages status CHECK (MP-MEGA-005)
    try:
        result = execute_query("""
            SELECT name, definition
            FROM sys.check_constraints
            WHERE OBJECT_NAME(parent_object_id) = 'uat_pages'
            AND definition LIKE '%status%'
        """, fetch="one")
        if result and 'conditional_pass' not in (result.get('definition') or ''):
            constraint_name = result['name']
            logger.info(f"  Migration 46: Expanding uat_pages status CHECK ({constraint_name})...")
            execute_query(f"ALTER TABLE uat_pages DROP CONSTRAINT [{constraint_name}]", fetch="none")
            execute_query("""
                ALTER TABLE uat_pages
                ADD CONSTRAINT chk_uat_pages_status_v3
                CHECK (status IN ('active','archived','pending','passed','failed','ready',
                                  'in_progress','submitted','approved','conditional_pass'))
            """, fetch="none")
            logger.info("  Migration 46: uat_pages status CHECK updated to include 'conditional_pass'.")
        else:
            logger.info("  Migration 46: uat_pages status CHECK already includes 'conditional_pass' or no constraint found.")
    except Exception as e:
        logger.warning(f"  Migration 46 warning: {e}")

    # Migration 47: Add general_notes column to uat_pages (MP-MEGA-005 Fix 2d)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'uat_pages' AND COLUMN_NAME = 'general_notes'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 47: Adding general_notes column to uat_pages...")
            execute_query("ALTER TABLE uat_pages ADD general_notes NVARCHAR(MAX)", fetch="none")
            logger.info("  Migration 47: general_notes column added.")
        else:
            logger.info("  Migration 47: general_notes already exists.")
    except Exception as e:
        logger.warning(f"  Migration 47 warning: {e}")

    # Migration 48: Bulk archive phantom pending UAT records (MP-MEGA-005 Fix 2h)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt FROM uat_pages
            WHERE status = 'pending'
            AND created_at < DATEADD(day, -7, GETDATE())
            AND pth IN (
                SELECT pth FROM uat_pages
                WHERE status NOT IN ('pending', 'archived')
                AND pth IS NOT NULL
            )
        """, fetch="one")
        phantom_count = result['cnt'] if result else 0
        if phantom_count > 0:
            logger.info(f"  Migration 48: Archiving {phantom_count} phantom pending UAT records...")
            execute_query("""
                UPDATE uat_pages SET status = 'archived'
                WHERE status = 'pending'
                AND created_at < DATEADD(day, -7, GETDATE())
                AND pth IN (
                    SELECT pth FROM uat_pages
                    WHERE status NOT IN ('pending', 'archived')
                    AND pth IS NOT NULL
                )
            """, fetch="none")
            logger.info(f"  Migration 48: Archived {phantom_count} phantom records.")
        else:
            logger.info("  Migration 48: No phantom pending UAT records to archive.")
    except Exception as e:
        logger.warning(f"  Migration 48 warning: {e}")

    # Migration 49: Add handoff_ref_id to mcp_handoffs for BA04 custom handoff IDs (MP-MEGA-006)
    try:
        existing = execute_query("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'mcp_handoffs' AND COLUMN_NAME = 'handoff_ref_id'
        """, fetch="one")
        if not existing:
            logger.info("  Migration 49: Adding handoff_ref_id column to mcp_handoffs...")
            execute_query("ALTER TABLE mcp_handoffs ADD handoff_ref_id NVARCHAR(100)", fetch="none")
            execute_query("CREATE INDEX idx_handoffs_ref_id ON mcp_handoffs(handoff_ref_id)", fetch="none")
            logger.info("  Migration 49: handoff_ref_id column added.")
        else:
            logger.info("  Migration 49: handoff_ref_id already exists.")
    except Exception as e:
        logger.warning(f"  Migration 49 warning: {e}")

    # Migration 50: PF5-MS2 — Extend cc_prompts for prompt storage + viewer + approval
    try:
        # Add pth column
        col = execute_query("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'cc_prompts' AND COLUMN_NAME = 'pth'
        """, fetch="one")
        if col and col['cnt'] == 0:
            logger.info("  Migration 50: Adding pth column to cc_prompts...")
            execute_query("ALTER TABLE cc_prompts ADD pth NVARCHAR(10) NULL", fetch="none")
            execute_query("CREATE INDEX idx_prompts_pth ON cc_prompts(pth)", fetch="none")

        # Add requirement_id column
        col = execute_query("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'cc_prompts' AND COLUMN_NAME = 'requirement_id'
        """, fetch="one")
        if col and col['cnt'] == 0:
            logger.info("  Migration 50: Adding requirement_id column to cc_prompts...")
            execute_query("ALTER TABLE cc_prompts ADD requirement_id NVARCHAR(36) NULL", fetch="none")

        # Add content_md column
        col = execute_query("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'cc_prompts' AND COLUMN_NAME = 'content_md'
        """, fetch="one")
        if col and col['cnt'] == 0:
            logger.info("  Migration 50: Adding content_md column to cc_prompts...")
            execute_query("ALTER TABLE cc_prompts ADD content_md NVARCHAR(MAX) NULL", fetch="none")

        # Add created_by column
        col = execute_query("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'cc_prompts' AND COLUMN_NAME = 'created_by'
        """, fetch="one")
        if col and col['cnt'] == 0:
            logger.info("  Migration 50: Adding created_by column to cc_prompts...")
            execute_query("ALTER TABLE cc_prompts ADD created_by NVARCHAR(50) DEFAULT 'CAI'", fetch="none")

        # Update status CHECK constraint to include new statuses
        # Drop old constraint and add new one
        try:
            execute_query("""
                DECLARE @constraint_name NVARCHAR(200)
                SELECT @constraint_name = name FROM sys.check_constraints
                WHERE parent_object_id = OBJECT_ID('cc_prompts') AND definition LIKE '%status%'
                IF @constraint_name IS NOT NULL
                    EXEC('ALTER TABLE cc_prompts DROP CONSTRAINT ' + @constraint_name)
            """, fetch="none")
            execute_query("""
                ALTER TABLE cc_prompts ADD CONSTRAINT CK_cc_prompts_status
                CHECK (status IN ('draft','prompt_ready','approved','sent','completed',
                                  'executing','complete','closed','rejected'))
            """, fetch="none")
            logger.info("  Migration 50: Status constraint updated.")
        except Exception as ck_err:
            logger.warning(f"  Migration 50: Status constraint update skipped: {ck_err}")

        # Add index on status
        try:
            execute_query("CREATE INDEX idx_prompts_status ON cc_prompts(status)", fetch="none")
        except Exception:
            pass  # Index may already exist

        logger.info("  Migration 50: cc_prompts extension complete.")
    except Exception as e:
        logger.warning(f"  Migration 50 warning: {e}")

    # Migration 51: PF5-MS2-SESSION-B — Create reviews table
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'reviews'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 51: Creating reviews table...")
            execute_query("""
                CREATE TABLE reviews (
                    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
                    handoff_id UNIQUEIDENTIFIER NOT NULL,
                    prompt_pth NVARCHAR(10) NULL,
                    assessment NVARCHAR(20) NOT NULL
                        CHECK (assessment IN ('pass', 'conditional_pass', 'fail')),
                    focus_areas NVARCHAR(MAX) NULL,
                    risks NVARCHAR(MAX) NULL,
                    regression_zones NVARCHAR(MAX) NULL,
                    lesson_candidates NVARCHAR(MAX) NULL,
                    rework_needed BIT DEFAULT 0,
                    notes NVARCHAR(MAX) NULL,
                    created_at DATETIME2 DEFAULT GETDATE(),
                    FOREIGN KEY (handoff_id) REFERENCES mcp_handoffs(id)
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_reviews_handoff ON reviews(handoff_id)", fetch="none")
            execute_query("CREATE INDEX idx_reviews_pth ON reviews(prompt_pth)", fetch="none")
            logger.info("  Migration 51: reviews table created.")
        else:
            logger.info("  Migration 51: reviews table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 51 warning: {e}")

    # Migration 52: MM09 — Create governance table (replaces governance_state.json)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'governance'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 52: Creating governance table...")
            execute_query("""
                CREATE TABLE governance (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    checkpoint NVARCHAR(50) NOT NULL,
                    bootstrap_version NVARCHAR(20) NOT NULL,
                    updated_at NVARCHAR(20) NOT NULL,
                    source NVARCHAR(200) NULL
                )
            """, fetch="none")
            execute_query("""
                INSERT INTO governance (checkpoint, bootstrap_version, updated_at, source)
                VALUES ('BOOT-1.5.18-BA07', '1.5.18', '2026-03-21',
                        'project-methodology/templates/CC_Bootstrap_v1.md')
            """, fetch="none")
            logger.info("  Migration 52: governance table created and seeded with BOOT-1.5.18-BA07.")
        else:
            logger.info("  Migration 52: governance table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 52 warning: {e}")

    # Migration 53: AP03 — Create session_logs table (Amendment A) + governance_kv table (Amendment E)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'session_logs'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 53a: Creating session_logs table...")
            execute_query("""
                CREATE TABLE session_logs (
                    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
                    pth NVARCHAR(20),
                    sprint_id NVARCHAR(100),
                    model NVARCHAR(50),
                    exit_status NVARCHAR(20),
                    full_response NVARCHAR(MAX),
                    response_length INT,
                    timestamp DATETIME2,
                    source NVARCHAR(50),
                    created_at DATETIME2 DEFAULT GETUTCDATE()
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_session_logs_pth ON session_logs(pth)", fetch="none")
            execute_query("CREATE INDEX idx_session_logs_exit ON session_logs(exit_status)", fetch="none")
            logger.info("  Migration 53a: session_logs table created.")
        else:
            logger.info("  Migration 53a: session_logs table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 53a warning: {e}")

    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'governance_kv'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 53b: Creating governance_kv table...")
            execute_query("""
                CREATE TABLE governance_kv (
                    key_name NVARCHAR(100) PRIMARY KEY,
                    value_json NVARCHAR(MAX) NOT NULL,
                    updated_at DATETIME2 DEFAULT GETUTCDATE()
                )
            """, fetch="none")
            logger.info("  Migration 53b: governance_kv table created.")
        else:
            logger.info("  Migration 53b: governance_kv table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 53b warning: {e}")

    # Migration 54: AP09 — Add archive_reason column to uat_pages
    # (keep existing)
    try:
        col_check = execute_query(
            "SELECT COUNT(*) as cnt FROM sys.columns WHERE object_id = OBJECT_ID('uat_pages') AND name = 'archive_reason'",
            fetch="one"
        )
        if not col_check or col_check["cnt"] == 0:
            execute_query("ALTER TABLE uat_pages ADD archive_reason NVARCHAR(200) NULL", fetch="none")
            logger.info("  Migration 54: archive_reason column added to uat_pages.")
        else:
            logger.info("  Migration 54: archive_reason column already exists.")
    except Exception as e:
        logger.warning(f"  Migration 54 warning: {e}")

    # Migration 55b: MM10B — Drop and recreate cc_prompts status CHECK to add 'cancelled'
    try:
        # Use same pattern as Migration 50 — find any status CHECK, drop it, recreate with 'cancelled'
        execute_query("""
            DECLARE @ck NVARCHAR(200)
            SELECT @ck = name FROM sys.check_constraints
            WHERE parent_object_id = OBJECT_ID('cc_prompts') AND definition LIKE '%status%'
              AND definition NOT LIKE '%cancelled%'
            IF @ck IS NOT NULL
                EXEC('ALTER TABLE cc_prompts DROP CONSTRAINT [' + @ck + ']')
        """, fetch="none")
        # Add new constraint with 'cancelled' — skip if already exists
        try:
            execute_query("""
                ALTER TABLE cc_prompts ADD CONSTRAINT CK_cc_prompts_status
                CHECK (status IN ('draft','prompt_ready','approved','sent','completed',
                                  'executing','complete','closed','rejected','cancelled'))
            """, fetch="none")
            logger.info("  Migration 55b: cc_prompts status constraint updated to include 'cancelled'.")
        except Exception as ck_add_err:
            if 'already exists' in str(ck_add_err).lower() or 'duplicate' in str(ck_add_err).lower():
                logger.info("  Migration 55b: CK_cc_prompts_status already includes 'cancelled'.")
            else:
                raise
    except Exception as e:
        logger.warning(f"  Migration 55b warning: {e}")

    # Migration 55: MM10B — Create job_executions table for PTH-aware Jobs panel
    try:
        tbl_check = execute_query(
            "SELECT COUNT(*) as cnt FROM sys.tables WHERE name = 'job_executions'",
            fetch="one"
        )
        if not tbl_check or tbl_check["cnt"] == 0:
            execute_query("""
                CREATE TABLE job_executions (
                    id           NVARCHAR(200) PRIMARY KEY,
                    pth          NVARCHAR(20)  NULL,
                    job_type     NVARCHAR(20)  NOT NULL DEFAULT 'loop1',
                    handoff_id   NVARCHAR(36)  NULL,
                    started_at   DATETIME2     NOT NULL DEFAULT GETUTCDATE(),
                    status       NVARCHAR(20)  NOT NULL DEFAULT 'running'
                )
            """, fetch="none")
            execute_query(
                "CREATE INDEX ix_job_executions_started ON job_executions(started_at DESC)",
                fetch="none"
            )
            logger.info("  Migration 55: job_executions table created.")
        else:
            logger.info("  Migration 55: job_executions table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 55 warning: {e}")

    # Migration 56: MC01 — Create compliance_docs table (stores Bootstrap, PKs, CAI standards)
    try:
        tbl_check = execute_query("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'compliance_docs'
        """, fetch="one")
        if not tbl_check or tbl_check["cnt"] == 0:
            logger.info("  Migration 56: Creating compliance_docs table...")
            execute_query("""
                CREATE TABLE compliance_docs (
                    id           NVARCHAR(50)   NOT NULL PRIMARY KEY,
                    doc_type     NVARCHAR(20)   NOT NULL,
                    project_code NVARCHAR(20)   NULL,
                    content_md   NVARCHAR(MAX)  NOT NULL,
                    version      NVARCHAR(50)   NOT NULL,
                    [checkpoint] NVARCHAR(20)   NOT NULL,
                    updated_at   DATETIME2      NOT NULL DEFAULT GETUTCDATE(),
                    updated_by   NVARCHAR(50)   NOT NULL DEFAULT 'system'
                )
            """, fetch="none")
            execute_query(
                "CREATE INDEX idx_compliance_docs_type ON compliance_docs(doc_type)",
                fetch="none"
            )
            logger.info("  Migration 56: compliance_docs table created.")
        else:
            logger.info("  Migration 56: compliance_docs table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 56 warning: {e}")

    # Migration 57: MF002 — Drop FK on reviews.handoff_id (allow refs to handoff_shells)
    try:
        fk_check = execute_query("""
            SELECT name FROM sys.foreign_keys
            WHERE parent_object_id = OBJECT_ID('reviews')
            AND name LIKE '%handoff%'
        """, fetch="one")
        if fk_check:
            fk_name = fk_check["name"]
            logger.info(f"  Migration 57: Dropping FK {fk_name} on reviews...")
            execute_query(f"ALTER TABLE reviews DROP CONSTRAINT [{fk_name}]", fetch="none")
            logger.info(f"  Migration 57: FK {fk_name} dropped.")
        else:
            logger.info("  Migration 57: No handoff FK on reviews — already dropped or absent.")
    except Exception as e:
        logger.warning(f"  Migration 57 warning: {e}")

    # Migration 58: MF002 — Extend PTH columns to NVARCHAR(20) across all tables
    try:
        pth_alters = [
            ("uat_pages", "pth"),
            ("roadmap_requirements", "pth"),
            ("pth_registry", "pth"),
            ("mcp_handoffs", "pth"),
            ("cc_prompts", "pth"),
            ("reviews", "prompt_pth"),
        ]
        for table, col in pth_alters:
            try:
                col_check = execute_query(f"""
                    SELECT character_maximum_length as max_len
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = '{table}' AND COLUMN_NAME = '{col}'
                """, fetch="one")
                if col_check and col_check["max_len"] and col_check["max_len"] < 20:
                    execute_query(f"ALTER TABLE [{table}] ALTER COLUMN [{col}] NVARCHAR(20) NULL", fetch="none")
                    logger.info(f"  Migration 58: {table}.{col} extended to NVARCHAR(20).")
                else:
                    logger.info(f"  Migration 58: {table}.{col} already >= 20 or not found.")
            except Exception as inner_e:
                logger.warning(f"  Migration 58: {table}.{col} — {inner_e}")
    except Exception as e:
        logger.warning(f"  Migration 58 warning: {e}")

    # Migration 59: MF002 — Ensure handoff_shells table exists (BA17 prerequisite)
    try:
        tbl_check = execute_query("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'handoff_shells'
        """, fetch="one")
        if not tbl_check or tbl_check["cnt"] == 0:
            logger.info("  Migration 59: Creating handoff_shells table...")
            execute_query("""
                CREATE TABLE handoff_shells (
                    id             UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
                    pth            NVARCHAR(20) NOT NULL,
                    sprint_id      NVARCHAR(100) NULL,
                    project_code   NVARCHAR(20) NULL,
                    uat_spec_id    UNIQUEIDENTIFIER NULL,
                    status         NVARCHAR(20) NOT NULL DEFAULT 'shell_created',
                    version_from   NVARCHAR(50) NULL,
                    version_to     NVARCHAR(50) NULL,
                    commit_hash    NVARCHAR(50) NULL,
                    deploy_url     NVARCHAR(500) NULL,
                    machine_tests  NVARCHAR(MAX) NULL,
                    deviations     NVARCHAR(MAX) NULL,
                    notes          NVARCHAR(MAX) NULL,
                    created_at     DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
                    updated_at     DATETIME2 NOT NULL DEFAULT GETUTCDATE()
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_handoff_shells_pth ON handoff_shells(pth)", fetch="none")
            logger.info("  Migration 59: handoff_shells table created.")
        else:
            # Ensure missing columns exist (table may have been created manually without these)
            missing_cols = {
                "status": "NVARCHAR(20) NOT NULL DEFAULT 'shell_created'",
                "notes": "NVARCHAR(MAX) NULL",
                "updated_at": "DATETIME2 NOT NULL DEFAULT GETUTCDATE()",
            }
            for col_name, col_def in missing_cols.items():
                col_check = execute_query(f"""
                    SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = 'handoff_shells' AND COLUMN_NAME = '{col_name}'
                """, fetch="one")
                if not col_check or col_check["cnt"] == 0:
                    try:
                        execute_query(f"ALTER TABLE handoff_shells ADD [{col_name}] {col_def}", fetch="none")
                        logger.info(f"  Migration 59: Added {col_name} to handoff_shells.")
                    except Exception as col_e:
                        logger.warning(f"  Migration 59: Failed to add {col_name}: {col_e}")
                else:
                    logger.info(f"  Migration 59: handoff_shells.{col_name} already exists.")
    except Exception as e:
        logger.warning(f"  Migration 59 warning: {e}")

    # Migration 60: Create challenge_tokens table (MPCH1 — Tier 2 anti-fabrication)
    try:
        result = execute_query("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'challenge_tokens'
        """, fetch="one")
        if result and result['cnt'] == 0:
            logger.info("  Migration 60: Creating challenge_tokens table...")
            execute_query("""
                CREATE TABLE challenge_tokens (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    pth NVARCHAR(20) NOT NULL,
                    token NVARCHAR(64) NOT NULL,
                    used BIT DEFAULT 0,
                    created_at DATETIME DEFAULT GETDATE(),
                    used_at DATETIME NULL
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_challenge_tokens_pth ON challenge_tokens(pth)", fetch="none")
            logger.info("  Migration 60: challenge_tokens table created.")
        else:
            logger.info("  Migration 60: challenge_tokens table already exists.")
    except Exception as e:
        logger.warning(f"  Migration 60 warning: {e}")

    # Migration 61: MP10 — Add session signal columns to cc_prompts
    try:
        session_cols = {
            "session_started_at": "DATETIME NULL",
            "session_ended_at": "DATETIME NULL",
            "session_outcome": "NVARCHAR(50) NULL",
            "session_stop_reason": "NVARCHAR(500) NULL",
        }
        for col_name, col_def in session_cols.items():
            col_check = execute_query(f"""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'cc_prompts' AND COLUMN_NAME = '{col_name}'
            """, fetch="one")
            if not col_check or col_check["cnt"] == 0:
                execute_query(f"ALTER TABLE cc_prompts ADD [{col_name}] {col_def}", fetch="none")
                logger.info(f"  Migration 61: Added {col_name} to cc_prompts.")
            else:
                logger.info(f"  Migration 61: cc_prompts.{col_name} already exists.")
    except Exception as e:
        logger.warning(f"  Migration 61 warning: {e}")

    # Migration 61b: MP10 — Add 'stopped' to cc_prompts status constraint
    try:
        execute_query("""
            DECLARE @ck NVARCHAR(200)
            SELECT @ck = name FROM sys.check_constraints
            WHERE parent_object_id = OBJECT_ID('cc_prompts') AND definition LIKE '%status%'
              AND definition NOT LIKE '%stopped%'
            IF @ck IS NOT NULL
                EXEC('ALTER TABLE cc_prompts DROP CONSTRAINT [' + @ck + ']')
        """, fetch="none")
        try:
            execute_query("""
                ALTER TABLE cc_prompts ADD CONSTRAINT CK_cc_prompts_status
                CHECK (status IN ('draft','prompt_ready','approved','sent','completed',
                                  'executing','complete','closed','rejected','cancelled','stopped'))
            """, fetch="none")
            logger.info("  Migration 61b: cc_prompts status constraint updated to include 'stopped'.")
        except Exception as ck_err:
            if 'already exists' in str(ck_err).lower():
                logger.info("  Migration 61b: CK_cc_prompts_status already includes 'stopped'.")
            else:
                raise
    except Exception as e:
        logger.warning(f"  Migration 61b warning: {e}")

    # Migration 62: MP12B — prompt_history table (Layer 1: application-level audit trail)
    try:
        exists = execute_query(
            "SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'prompt_history'",
            fetch="one"
        )
        if not exists or exists["cnt"] == 0:
            execute_query("""
                CREATE TABLE prompt_history (
                    id INT IDENTITY PRIMARY KEY,
                    prompt_id INT NOT NULL,
                    pth NVARCHAR(50) NOT NULL,
                    from_status NVARCHAR(50) NULL,
                    to_status NVARCHAR(50) NOT NULL,
                    changed_at DATETIME NOT NULL DEFAULT GETUTCDATE(),
                    changed_by NVARCHAR(50) NOT NULL,
                    [trigger] NVARCHAR(100) NULL,
                    success BIT NOT NULL DEFAULT 1,
                    blocked_reason NVARCHAR(500) NULL
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_ph_pth ON prompt_history(pth)", fetch="none")
            execute_query("CREATE INDEX idx_ph_prompt_id ON prompt_history(prompt_id)", fetch="none")
            execute_query("CREATE INDEX idx_ph_changed_at ON prompt_history(changed_at)", fetch="none")
            logger.info("  Migration 62: Created prompt_history table with indexes.")
        else:
            logger.info("  Migration 62: prompt_history already exists.")
    except Exception as e:
        logger.warning(f"  Migration 62 warning: {e}")

    # Migration 62b: MP12B — Add success/blocked_reason to requirement_history
    try:
        for col_name, col_def in [("success", "BIT NOT NULL DEFAULT 1"), ("blocked_reason", "NVARCHAR(500) NULL")]:
            col_check = execute_query(f"""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'requirement_history' AND COLUMN_NAME = '{col_name}'
            """, fetch="one")
            if not col_check or col_check["cnt"] == 0:
                execute_query(f"ALTER TABLE requirement_history ADD [{col_name}] {col_def}", fetch="none")
                logger.info(f"  Migration 62b: Added {col_name} to requirement_history.")
            else:
                logger.info(f"  Migration 62b: requirement_history.{col_name} already exists.")
    except Exception as e:
        logger.warning(f"  Migration 62b warning: {e}")

    # Migration 62c: MP12B — failure_events table
    try:
        exists = execute_query(
            "SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'failure_events'",
            fetch="one"
        )
        if not exists or exists["cnt"] == 0:
            execute_query("""
                CREATE TABLE failure_events (
                    id INT IDENTITY PRIMARY KEY,
                    event_type NVARCHAR(50) NOT NULL,
                    pth NVARCHAR(50) NULL,
                    [trigger] NVARCHAR(100) NOT NULL,
                    fired_at DATETIME NOT NULL DEFAULT GETUTCDATE(),
                    details NVARCHAR(1000) NULL
                )
            """, fetch="none")
            execute_query("CREATE INDEX idx_fe_pth ON failure_events(pth)", fetch="none")
            execute_query("CREATE INDEX idx_fe_fired_at ON failure_events(fired_at)", fetch="none")
            logger.info("  Migration 62c: Created failure_events table.")
        else:
            logger.info("  Migration 62c: failure_events already exists.")
    except Exception as e:
        logger.warning(f"  Migration 62c warning: {e}")

    # Migration 62d: MP12B — DB triggers on cc_prompts and roadmap_requirements (Layer 2)
    try:
        # Trigger on cc_prompts status changes
        trigger_exists = execute_query(
            "SELECT COUNT(*) as cnt FROM sys.triggers WHERE name = 'trg_cc_prompts_status_audit'",
            fetch="one"
        )
        if not trigger_exists or trigger_exists["cnt"] == 0:
            execute_query("""
                CREATE TRIGGER trg_cc_prompts_status_audit
                ON cc_prompts
                AFTER UPDATE
                AS
                BEGIN
                    SET NOCOUNT ON;
                    IF NOT UPDATE(status) RETURN;

                    DECLARE @prompt_id INT, @pth NVARCHAR(50), @old_status NVARCHAR(50), @new_status NVARCHAR(50);

                    SELECT @prompt_id = i.id, @pth = i.pth, @old_status = d.status, @new_status = i.status
                    FROM inserted i
                    JOIN deleted d ON i.id = d.id
                    WHERE i.status <> d.status;

                    IF @prompt_id IS NULL RETURN;

                    IF NOT EXISTS (
                        SELECT 1 FROM prompt_history
                        WHERE prompt_id = @prompt_id
                        AND to_status = @new_status
                        AND changed_at > DATEADD(second, -2, GETUTCDATE())
                    )
                    BEGIN
                        INSERT INTO prompt_history (prompt_id, pth, from_status, to_status, changed_by, [trigger], success)
                        VALUES (@prompt_id, @pth, @old_status, @new_status, 'db_trigger', 'db_trigger_catchall', 1);
                    END
                END;
            """, fetch="none")
            logger.info("  Migration 62d: Created trg_cc_prompts_status_audit trigger.")
        else:
            logger.info("  Migration 62d: trg_cc_prompts_status_audit already exists.")

        # Trigger on roadmap_requirements status changes
        rr_trigger_exists = execute_query(
            "SELECT COUNT(*) as cnt FROM sys.triggers WHERE name = 'trg_roadmap_req_status_audit'",
            fetch="none"  # existing trigger from migration 25 — check if our NEW one exists
        )
        # The existing migration-25 trigger already covers requirement_history. Our trigger is supplemental
        # for defense-in-depth when success/blocked_reason columns are present. Skip if existing trigger covers it.
        logger.info("  Migration 62d: roadmap_requirements trigger already handled by migration 25.")
    except Exception as e:
        logger.warning(f"  Migration 62d warning: {e}")

    # Migration 62e: MP12B — Update cc_prompts status constraint to include 'blocked'
    try:
        execute_query("""
            DECLARE @ck NVARCHAR(200)
            SELECT @ck = name FROM sys.check_constraints
            WHERE parent_object_id = OBJECT_ID('cc_prompts') AND definition LIKE '%status%'
              AND definition NOT LIKE '%blocked%'
            IF @ck IS NOT NULL
                EXEC('ALTER TABLE cc_prompts DROP CONSTRAINT [' + @ck + ']')
        """, fetch="none")
        try:
            execute_query("""
                ALTER TABLE cc_prompts ADD CONSTRAINT CK_cc_prompts_status_v2
                CHECK (status IN ('draft','prompt_ready','approved','sent','completed',
                                  'executing','complete','closed','rejected','cancelled','stopped','blocked'))
            """, fetch="none")
            logger.info("  Migration 62e: cc_prompts status constraint updated to include 'blocked'.")
        except Exception as ck_err:
            if 'already exists' in str(ck_err).lower():
                logger.info("  Migration 62e: status constraint already includes 'blocked'.")
            else:
                raise
    except Exception as e:
        logger.warning(f"  Migration 62e warning: {e}")

    # Migration 62f: MP12B — Backfill prompt_history for existing prompts
    try:
        backfill_count = execute_query("""
            INSERT INTO prompt_history (prompt_id, pth, from_status, to_status, changed_by, [trigger], success)
            SELECT p.id, p.pth, NULL, p.status, 'migration_backfill', 'initial_state_backfill', 1
            FROM cc_prompts p
            LEFT JOIN prompt_history ph ON p.id = ph.prompt_id
            WHERE ph.id IS NULL AND p.pth IS NOT NULL
        """, fetch="none")
        # Count backfilled
        bf_count = execute_query("""
            SELECT COUNT(*) as cnt FROM prompt_history WHERE changed_by = 'migration_backfill'
        """, fetch="one")
        logger.info(f"  Migration 62f: Backfilled prompt_history ({bf_count['cnt'] if bf_count else 0} total backfill rows).")
    except Exception as e:
        logger.warning(f"  Migration 62f warning: {e}")

    # Migration 62g: MP12B — Backfill requirement_history for requirements with no history
    try:
        execute_query("""
            INSERT INTO requirement_history (requirement_id, field_name, old_value, new_value, changed_by, notes)
            SELECT r.id, 'status', NULL, r.status, 'migration_backfill', 'initial_state_backfill'
            FROM roadmap_requirements r
            LEFT JOIN requirement_history rh ON r.id = rh.requirement_id
            WHERE rh.id IS NULL
        """, fetch="none")
        bf_count = execute_query("""
            SELECT COUNT(*) as cnt FROM requirement_history WHERE changed_by = 'migration_backfill'
        """, fetch="one")
        logger.info(f"  Migration 62g: Backfilled requirement_history ({bf_count['cnt'] if bf_count else 0} total backfill rows).")
    except Exception as e:
        logger.warning(f"  Migration 62g warning: {e}")

    logger.info("Migrations complete.")
