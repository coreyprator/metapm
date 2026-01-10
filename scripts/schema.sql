-- ============================================
-- META PROJECT MANAGER - SQL Schema v1.0
-- For: Corey Prator's 2026 Project Management
-- Database: MS SQL Server (Cloud SQL)
-- ============================================

-- ============================================
-- CORE TABLES
-- ============================================

-- Categories: User-maintainable classification system
CREATE TABLE Categories (
    CategoryID INT IDENTITY(1,1) PRIMARY KEY,
    CategoryCode VARCHAR(20) NOT NULL UNIQUE,  -- e.g., 'ACTION', 'IDEA', 'BUG'
    CategoryName VARCHAR(100) NOT NULL,
    CategoryType VARCHAR(50) NOT NULL,  -- 'TASK_TYPE' or 'DOMAIN'
    Description VARCHAR(500),
    SortOrder INT DEFAULT 0,
    IsActive BIT DEFAULT 1,
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    UpdatedAt DATETIME2 DEFAULT GETUTCDATE()
);

-- Seed Categories
INSERT INTO Categories (CategoryCode, CategoryName, CategoryType, Description, SortOrder) VALUES
-- Task Types
('ACTION', 'Action Item', 'TASK_TYPE', 'Concrete next step to complete', 1),
('IDEA', 'Idea', 'TASK_TYPE', 'Concept to explore or evaluate', 2),
('BUG', 'Bug', 'TASK_TYPE', 'Defect requiring fix', 3),
('REQUIREMENT', 'Requirement', 'TASK_TYPE', 'Feature or capability needed', 4),
('TEST', 'Test Item', 'TASK_TYPE', 'Verification or validation task', 5),
('RESEARCH', 'Research', 'TASK_TYPE', 'Investigation or learning task', 6),
-- Domains
('SOFTWARE', 'Software Development', 'DOMAIN', 'Code, architecture, deployment', 10),
('TRAVEL', 'Travel & Adventure', 'DOMAIN', 'Trip planning, bookings', 11),
('HOME', 'Home & Admin', 'DOMAIN', 'Household, personal admin', 12),
('MUSIC', 'Music & Piano', 'DOMAIN', 'Jazz practice, composition', 13),
('LANGUAGE', 'Language Learning', 'DOMAIN', 'French, Greek studies', 14),
('ART', 'Art & Video', 'DOMAIN', 'Creative projects', 15),
('SOCIAL', 'Relationships', 'DOMAIN', 'DIPsters, family, networking', 16);

-- Projects: Registry of all projects
CREATE TABLE Projects (
    ProjectID INT IDENTITY(1,1) PRIMARY KEY,
    ProjectCode VARCHAR(20) NOT NULL UNIQUE,  -- e.g., 'AF', 'EM', 'HL', 'SF', 'META'
    ProjectName VARCHAR(200) NOT NULL,
    Theme VARCHAR(50),  -- 'A: Creation', 'B: Learning', 'C: Adventure', 'D: Relationships'
    Description VARCHAR(MAX),  -- Rich text (HTML or MD)
    ProjectURL VARCHAR(500),  -- Production URL if applicable
    GitHubRepo VARCHAR(500),  -- GitHub repository URL
    VSCodeWorkspace VARCHAR(500),  -- Path to .code-workspace file
    Status VARCHAR(20) DEFAULT 'ACTIVE',  -- ACTIVE, PAUSED, COMPLETED, ARCHIVED
    Priority INT DEFAULT 3 CHECK (Priority BETWEEN 1 AND 5),
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    UpdatedAt DATETIME2 DEFAULT GETUTCDATE()
);

-- Seed Projects from 2026 Plan
INSERT INTO Projects (ProjectCode, ProjectName, Theme, ProjectURL, Status, Priority) VALUES
('AF', 'ArtForge', 'A: Creation', 'https://artforge.rentyourcio.com/', 'ACTIVE', 2),
('EM', 'Etymython', 'B: Learning', 'https://etymython.rentyourcio.com/app', 'ACTIVE', 1),
('HL', 'HarmonyLab', 'B: Learning', NULL, 'ACTIVE', 2),
('SF', 'Super-Flashcards', 'B: Learning', NULL, 'ACTIVE', 2),
('META', 'Meta Project Manager', 'CROSS-CUTTING', NULL, 'ACTIVE', 1),
('VID-MAC', 'Video: MacBook Recovery', 'A: Creation', NULL, 'ACTIVE', 3),
('VID-LOIS', 'Video: Lois Story', 'A: Creation', NULL, 'NOT_STARTED', 4),
('VID-PRATOR', 'Video: Prator Family History', 'A: Creation', NULL, 'ACTIVE', 3),
('VID-CHICKS', 'Video: Chicks in Maids Quarters', 'A: Creation', NULL, 'NOT_STARTED', 5),
('VID-3D', 'Video: 2D to 3D Art', 'A: Creation', NULL, 'NOT_STARTED', 5),
('VID-PARA', 'Video: Paraguay Honeymoon', 'A: Creation', NULL, 'BLOCKED', 5),
('TRIP-89', 'Route 89 Road Trip', 'C: Adventure', NULL, 'ACTIVE', 3),
('TRIP-COLORADO', 'Colorado River Documentary', 'C: Adventure', NULL, 'BLOCKED', 4),
('TRIP-CANYON', 'Grand Canyon Raft Trip', 'C: Adventure', NULL, 'BLOCKED', 3),
('TRIP-ALCAN', 'Alcan Highway', 'C: Adventure', NULL, 'BLOCKED', 4),
('LANG-FRENCH', 'French Language Learning', 'B: Learning', NULL, 'ACTIVE', 2),
('LANG-GREEK', 'Greek Language Learning', 'B: Learning', NULL, 'ACTIVE', 2),
('MUSIC-JAZZ', 'Jazz Piano Development', 'B: Learning', NULL, 'ACTIVE', 2),
('ART-SYSTEM', 'Art Creation System', 'A: Creation', NULL, 'ACTIVE', 2),
('DIPSTERS', 'DIPster Engagement', 'D: Relationships', NULL, 'ACTIVE', 2),
('CUBIST', 'Cubist Art Software', 'A: Creation', NULL, 'ACTIVE', 3);

-- Tasks: Central task registry
CREATE TABLE Tasks (
    TaskID INT IDENTITY(1,1) PRIMARY KEY,
    Title VARCHAR(500) NOT NULL,
    Description VARCHAR(MAX),  -- Rich text (HTML or MD supported)
    ReferenceURL VARCHAR(1000),  -- Hyperlink to related resource
    Priority INT DEFAULT 3 CHECK (Priority BETWEEN 1 AND 5),
    Status VARCHAR(20) DEFAULT 'NEW',  -- NEW, STARTED, BLOCKED, COMPLETE, CANCELLED
    BlockedReason VARCHAR(500),  -- If Status = BLOCKED
    Source VARCHAR(50),  -- 'TODOIST', 'MANUAL', 'VOICE', 'COPILOT', 'SPRINT'
    SprintNumber INT,  -- If associated with a sprint
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    DueDate DATE,
    StartedAt DATETIME2,
    CompletedAt DATETIME2,
    UpdatedAt DATETIME2 DEFAULT GETUTCDATE()
);

-- TaskProjectLinks: Many-to-many between Tasks and Projects
CREATE TABLE TaskProjectLinks (
    TaskProjectLinkID INT IDENTITY(1,1) PRIMARY KEY,
    TaskID INT NOT NULL FOREIGN KEY REFERENCES Tasks(TaskID) ON DELETE CASCADE,
    ProjectID INT NOT NULL FOREIGN KEY REFERENCES Projects(ProjectID) ON DELETE CASCADE,
    IsPrimary BIT DEFAULT 0,  -- Is this the primary project for this task?
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    CONSTRAINT UQ_TaskProject UNIQUE (TaskID, ProjectID)
);

-- TaskCategoryLinks: Many-to-many between Tasks and Categories
CREATE TABLE TaskCategoryLinks (
    TaskCategoryLinkID INT IDENTITY(1,1) PRIMARY KEY,
    TaskID INT NOT NULL FOREIGN KEY REFERENCES Tasks(TaskID) ON DELETE CASCADE,
    CategoryID INT NOT NULL FOREIGN KEY REFERENCES Categories(CategoryID) ON DELETE CASCADE,
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    CONSTRAINT UQ_TaskCategory UNIQUE (TaskID, CategoryID)
);

-- ============================================
-- METHODOLOGY SUPPORT TABLES
-- ============================================

-- MethodologyRules: PM rules that can be referenced when VS Code violates them
CREATE TABLE MethodologyRules (
    RuleID INT IDENTITY(1,1) PRIMARY KEY,
    RuleCode VARCHAR(50) NOT NULL UNIQUE,  -- e.g., 'TEST-BEFORE-COMMIT', 'VERIFY-HUMAN-VISIBLE'
    RuleName VARCHAR(200) NOT NULL,
    Category VARCHAR(50),  -- 'TESTING', 'DEPLOYMENT', 'CODE-QUALITY', 'DOCUMENTATION'
    Description VARCHAR(MAX),  -- Full explanation
    ViolationPrompt VARCHAR(MAX),  -- Pre-written prompt to send to VS Code when violated
    Severity VARCHAR(20) DEFAULT 'MEDIUM',  -- LOW, MEDIUM, HIGH, CRITICAL
    IsActive BIT DEFAULT 1,
    CreatedAt DATETIME2 DEFAULT GETUTCDATE()
);

-- Seed some methodology rules based on your experiences
INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('TEST-HUMAN-VISIBLE', 'Verify Human-Visible Functionality', 'TESTING', 
 'Tests must verify actual human-visible functionality, not just technical presence. A passing test should mean a human user would see the expected behavior.',
 'STOP. You have violated the TEST-HUMAN-VISIBLE rule. Before proceeding, you must: 1) Identify what a human user would actually see or experience, 2) Write a test that verifies that specific user experience, 3) Run the test and confirm it passes. Do not mark this task complete until you can describe what a human would observe.',
 'CRITICAL'),
('NO-UNTESTED-CODE', 'No Untested Code Handoff', 'TESTING',
 'Never hand code to Corey that has not been tested. All code must be verified working before handoff.',
 'STOP. You are about to hand off untested code. Per project methodology: 1) Run all relevant tests, 2) Verify the feature works end-to-end, 3) Document what you tested and results. Only then may you hand off.',
 'CRITICAL'),
('SPRINT-TASK-SEQUENCE', 'Follow Sprint Task Sequence', 'WORKFLOW',
 'When completing a sprint task, immediately reference the sprint document and proceed to the next item. Do not wait for user prompt.',
 'You have completed a sprint task. Per methodology: 1) Mark the completed task in the sprint doc, 2) Identify the next task, 3) Begin work on it or report any blockers. What is the next task in the sprint?',
 'HIGH'),
('DB-CONNECTION-VERIFY', 'Verify Database Connections', 'TESTING',
 'Always verify database connections work in the actual deployed environment, not just locally.',
 'Database connection issues detected. Per methodology: 1) Verify connection string is correct for target environment, 2) Check GCP project authentication, 3) Test with a simple query before proceeding.',
 'HIGH');

-- MethodologyViolations: Log of violations for pattern analysis
CREATE TABLE MethodologyViolations (
    ViolationID INT IDENTITY(1,1) PRIMARY KEY,
    RuleID INT FOREIGN KEY REFERENCES MethodologyRules(RuleID),
    ProjectID INT FOREIGN KEY REFERENCES Projects(ProjectID),
    TaskID INT FOREIGN KEY REFERENCES Tasks(TaskID),
    Description VARCHAR(MAX),
    CopilotSessionRef VARCHAR(500),  -- Reference to Copilot chat if applicable
    Resolution VARCHAR(MAX),
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    ResolvedAt DATETIME2
);

-- ============================================
-- CROSS-PROJECT INSIGHTS
-- ============================================

-- CrossProjectLinks: Explicit relationships between projects
CREATE TABLE CrossProjectLinks (
    CrossProjectLinkID INT IDENTITY(1,1) PRIMARY KEY,
    SourceProjectID INT NOT NULL FOREIGN KEY REFERENCES Projects(ProjectID),
    TargetProjectID INT NOT NULL FOREIGN KEY REFERENCES Projects(ProjectID),
    LinkType VARCHAR(50),  -- 'SHARES_CODE', 'SHARES_DATA', 'SHARES_CONCEPT', 'DEPENDS_ON'
    Description VARCHAR(500),
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    CONSTRAINT UQ_CrossProject UNIQUE (SourceProjectID, TargetProjectID, LinkType)
);

-- Seed known cross-project relationships
INSERT INTO CrossProjectLinks (SourceProjectID, TargetProjectID, LinkType, Description)
SELECT s.ProjectID, t.ProjectID, 'SHARES_CONCEPT', 'PIE etymology content useful in both'
FROM Projects s, Projects t WHERE s.ProjectCode = 'SF' AND t.ProjectCode = 'EM';

INSERT INTO CrossProjectLinks (SourceProjectID, TargetProjectID, LinkType, Description)
SELECT s.ProjectID, t.ProjectID, 'SHARES_CONCEPT', 'PIE etymology content useful in both'
FROM Projects s, Projects t WHERE s.ProjectCode = 'EM' AND t.ProjectCode = 'SF';

-- ============================================
-- STANDARD VIEWS
-- ============================================

-- View: Overdue Tasks
CREATE VIEW vw_OverdueTasks AS
SELECT 
    t.TaskID, t.Title, t.Priority, t.Status, t.DueDate,
    DATEDIFF(day, t.DueDate, GETUTCDATE()) AS DaysOverdue,
    p.ProjectCode, p.ProjectName
FROM Tasks t
LEFT JOIN TaskProjectLinks tpl ON t.TaskID = tpl.TaskID AND tpl.IsPrimary = 1
LEFT JOIN Projects p ON tpl.ProjectID = p.ProjectID
WHERE t.Status NOT IN ('COMPLETE', 'CANCELLED')
  AND t.DueDate < CAST(GETUTCDATE() AS DATE);

-- View: Incomplete Tasks by Priority
CREATE VIEW vw_IncompleteTasksByPriority AS
SELECT 
    t.TaskID, t.Title, t.Priority, t.Status, t.DueDate, t.CreatedAt,
    p.ProjectCode, p.ProjectName,
    STRING_AGG(c.CategoryName, ', ') AS Categories
FROM Tasks t
LEFT JOIN TaskProjectLinks tpl ON t.TaskID = tpl.TaskID AND tpl.IsPrimary = 1
LEFT JOIN Projects p ON tpl.ProjectID = p.ProjectID
LEFT JOIN TaskCategoryLinks tcl ON t.TaskID = tcl.TaskID
LEFT JOIN Categories c ON tcl.CategoryID = c.CategoryID
WHERE t.Status NOT IN ('COMPLETE', 'CANCELLED')
GROUP BY t.TaskID, t.Title, t.Priority, t.Status, t.DueDate, t.CreatedAt, p.ProjectCode, p.ProjectName;

-- View: Tasks Without Due Dates
CREATE VIEW vw_TasksWithoutDueDates AS
SELECT 
    t.TaskID, t.Title, t.Priority, t.Status, t.CreatedAt,
    DATEDIFF(day, t.CreatedAt, GETUTCDATE()) AS DaysOpen,
    p.ProjectCode, p.ProjectName
FROM Tasks t
LEFT JOIN TaskProjectLinks tpl ON t.TaskID = tpl.TaskID AND tpl.IsPrimary = 1
LEFT JOIN Projects p ON tpl.ProjectID = p.ProjectID
WHERE t.Status NOT IN ('COMPLETE', 'CANCELLED')
  AND t.DueDate IS NULL;

-- View: Tasks by Project with Categories
CREATE VIEW vw_TasksByProject AS
SELECT 
    p.ProjectCode, p.ProjectName, p.Theme, p.Status AS ProjectStatus,
    t.TaskID, t.Title, t.Priority, t.Status AS TaskStatus, t.DueDate,
    STRING_AGG(c.CategoryCode, ', ') AS CategoryCodes
FROM Projects p
LEFT JOIN TaskProjectLinks tpl ON p.ProjectID = tpl.ProjectID
LEFT JOIN Tasks t ON tpl.TaskID = t.TaskID
LEFT JOIN TaskCategoryLinks tcl ON t.TaskID = tcl.TaskID
LEFT JOIN Categories c ON tcl.CategoryID = c.CategoryID
GROUP BY p.ProjectCode, p.ProjectName, p.Theme, p.Status, 
         t.TaskID, t.Title, t.Priority, t.Status, t.DueDate;

-- View: Cross-Project Tasks (tasks linked to multiple projects)
CREATE VIEW vw_CrossProjectTasks AS
SELECT 
    t.TaskID, t.Title, t.Priority, t.Status,
    COUNT(tpl.ProjectID) AS ProjectCount,
    STRING_AGG(p.ProjectCode, ', ') AS LinkedProjects
FROM Tasks t
JOIN TaskProjectLinks tpl ON t.TaskID = tpl.TaskID
JOIN Projects p ON tpl.ProjectID = p.ProjectID
GROUP BY t.TaskID, t.Title, t.Priority, t.Status
HAVING COUNT(tpl.ProjectID) > 1;

-- View: Blocked Projects Summary
CREATE VIEW vw_BlockedProjects AS
SELECT 
    p.ProjectID, p.ProjectCode, p.ProjectName, p.Theme,
    COUNT(t.TaskID) AS BlockedTaskCount,
    STRING_AGG(t.BlockedReason, '; ') AS BlockedReasons
FROM Projects p
LEFT JOIN TaskProjectLinks tpl ON p.ProjectID = tpl.ProjectID
LEFT JOIN Tasks t ON tpl.TaskID = t.TaskID AND t.Status = 'BLOCKED'
WHERE p.Status = 'BLOCKED' OR t.Status = 'BLOCKED'
GROUP BY p.ProjectID, p.ProjectCode, p.ProjectName, p.Theme;

-- View: Methodology Violation Summary
CREATE VIEW vw_MethodologyViolationSummary AS
SELECT 
    mr.RuleCode, mr.RuleName, mr.Severity,
    COUNT(mv.ViolationID) AS TotalViolations,
    SUM(CASE WHEN mv.ResolvedAt IS NULL THEN 1 ELSE 0 END) AS OpenViolations,
    MAX(mv.CreatedAt) AS LastViolation
FROM MethodologyRules mr
LEFT JOIN MethodologyViolations mv ON mr.RuleID = mv.RuleID
GROUP BY mr.RuleCode, mr.RuleName, mr.Severity;

-- ============================================
-- USEFUL STORED PROCEDURES
-- ============================================

-- Procedure: Add Task with Project and Categories in one call
CREATE PROCEDURE sp_AddTask
    @Title VARCHAR(500),
    @Description VARCHAR(MAX) = NULL,
    @ReferenceURL VARCHAR(1000) = NULL,
    @Priority INT = 3,
    @DueDate DATE = NULL,
    @ProjectCode VARCHAR(20) = NULL,
    @CategoryCodes VARCHAR(500) = NULL,  -- Comma-separated: 'ACTION,SOFTWARE'
    @Source VARCHAR(50) = 'MANUAL'
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @TaskID INT;
    DECLARE @ProjectID INT;
    
    -- Insert the task
    INSERT INTO Tasks (Title, Description, ReferenceURL, Priority, DueDate, Source)
    VALUES (@Title, @Description, @ReferenceURL, @Priority, @DueDate, @Source);
    
    SET @TaskID = SCOPE_IDENTITY();
    
    -- Link to project if provided
    IF @ProjectCode IS NOT NULL
    BEGIN
        SELECT @ProjectID = ProjectID FROM Projects WHERE ProjectCode = @ProjectCode;
        IF @ProjectID IS NOT NULL
        BEGIN
            INSERT INTO TaskProjectLinks (TaskID, ProjectID, IsPrimary)
            VALUES (@TaskID, @ProjectID, 1);
        END
    END
    
    -- Link to categories if provided
    IF @CategoryCodes IS NOT NULL
    BEGIN
        INSERT INTO TaskCategoryLinks (TaskID, CategoryID)
        SELECT @TaskID, c.CategoryID
        FROM Categories c
        WHERE c.CategoryCode IN (SELECT TRIM(value) FROM STRING_SPLIT(@CategoryCodes, ','));
    END
    
    SELECT @TaskID AS NewTaskID;
END;
GO

-- Procedure: Quick capture (minimal fields for voice/mobile input)
CREATE PROCEDURE sp_QuickCapture
    @Title VARCHAR(500),
    @ProjectCode VARCHAR(20) = NULL,
    @CategoryCode VARCHAR(20) = 'IDEA'
AS
BEGIN
    EXEC sp_AddTask 
        @Title = @Title,
        @ProjectCode = @ProjectCode,
        @CategoryCodes = @CategoryCode,
        @Source = 'VOICE';
END;
GO

-- Procedure: Get Next Sprint Task
CREATE PROCEDURE sp_GetNextSprintTask
    @ProjectCode VARCHAR(20)
AS
BEGIN
    SELECT TOP 1 
        t.TaskID, t.Title, t.Description, t.Priority, t.SprintNumber
    FROM Tasks t
    JOIN TaskProjectLinks tpl ON t.TaskID = tpl.TaskID
    JOIN Projects p ON tpl.ProjectID = p.ProjectID
    WHERE p.ProjectCode = @ProjectCode
      AND t.Status = 'NEW'
      AND t.SprintNumber IS NOT NULL
    ORDER BY t.SprintNumber, t.Priority;
END;
GO

-- Procedure: Log Methodology Violation
CREATE PROCEDURE sp_LogMethodologyViolation
    @RuleCode VARCHAR(50),
    @ProjectCode VARCHAR(20),
    @Description VARCHAR(MAX),
    @CopilotSessionRef VARCHAR(500) = NULL
AS
BEGIN
    INSERT INTO MethodologyViolations (RuleID, ProjectID, Description, CopilotSessionRef)
    SELECT mr.RuleID, p.ProjectID, @Description, @CopilotSessionRef
    FROM MethodologyRules mr
    CROSS JOIN Projects p
    WHERE mr.RuleCode = @RuleCode AND p.ProjectCode = @ProjectCode;
END;
GO
