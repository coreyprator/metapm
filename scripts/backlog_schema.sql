-- ============================================
-- BACKLOG TABLES - Bugs & Requirements
-- MetaPM Sprint 5: Jira-like Tracking
-- ============================================

-- Bugs: Tracked defects per project
CREATE TABLE Bugs (
    BugID INT IDENTITY(1,1) PRIMARY KEY,
    ProjectID INT NOT NULL FOREIGN KEY REFERENCES Projects(ProjectID),
    Code NVARCHAR(20) NOT NULL,              -- e.g. 'BUG-006'
    Title NVARCHAR(200) NOT NULL,
    Description NVARCHAR(MAX),
    Status NVARCHAR(20) DEFAULT 'Open',      -- Open, In Progress, Fixed, Deferred, Closed
    Priority NVARCHAR(5) DEFAULT 'P3',       -- P1, P2, P3, P4, P5
    ReportedDate DATETIME2 DEFAULT GETUTCDATE(),
    ResolvedDate DATETIME2 NULL,
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    UpdatedAt DATETIME2 DEFAULT GETUTCDATE(),
    CONSTRAINT UQ_Bug_ProjectCode UNIQUE (ProjectID, Code)
);

-- Requirements: Feature/capability requests per project
CREATE TABLE Requirements (
    RequirementID INT IDENTITY(1,1) PRIMARY KEY,
    ProjectID INT NOT NULL FOREIGN KEY REFERENCES Projects(ProjectID),
    Code NVARCHAR(20) NOT NULL,              -- e.g. 'REQ-001'
    Title NVARCHAR(200) NOT NULL,
    Description NVARCHAR(MAX),
    Status NVARCHAR(20) DEFAULT 'Backlog',   -- Backlog, In Progress, Done, Deferred
    Priority NVARCHAR(5) DEFAULT 'P3',       -- P1, P2, P3, P4, P5
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    UpdatedAt DATETIME2 DEFAULT GETUTCDATE(),
    CONSTRAINT UQ_Req_ProjectCode UNIQUE (ProjectID, Code)
);
