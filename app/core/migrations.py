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

    logger.info("Migrations complete.")
