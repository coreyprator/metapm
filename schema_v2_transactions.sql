-- ============================================
-- META PROJECT MANAGER - Schema v2.0
-- Added: Transaction History, Media Support, Full-Text Search
-- ============================================

-- ============================================
-- TRANSACTION HISTORY TABLES
-- ============================================

-- Conversations: Groups related transactions (like a chat thread)
CREATE TABLE Conversations (
    ConversationID INT IDENTITY(1,1) PRIMARY KEY,
    ConversationGUID UNIQUEIDENTIFIER DEFAULT NEWID() NOT NULL,  -- For API references
    Title NVARCHAR(500),  -- Auto-generated or user-provided
    Source VARCHAR(50) NOT NULL,  -- 'VOICE', 'WEB', 'API', 'MOBILE', 'VSCODE'
    ProjectID INT FOREIGN KEY REFERENCES Projects(ProjectID),  -- Optional project context
    Status VARCHAR(20) DEFAULT 'ACTIVE',  -- ACTIVE, ARCHIVED, DELETED
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    UpdatedAt DATETIME2 DEFAULT GETUTCDATE(),
    ArchivedAt DATETIME2,
    
    -- Metadata for context
    DeviceInfo NVARCHAR(500),  -- User agent, device type
    Location NVARCHAR(200),  -- Optional: "Houston, TX" for context
    Tags NVARCHAR(500)  -- Comma-separated tags for categorization
);

CREATE INDEX IX_Conversations_CreatedAt ON Conversations(CreatedAt DESC);
CREATE INDEX IX_Conversations_ProjectID ON Conversations(ProjectID);
CREATE INDEX IX_Conversations_Source ON Conversations(Source);

-- Transactions: Individual prompt/response pairs
CREATE TABLE Transactions (
    TransactionID INT IDENTITY(1,1) PRIMARY KEY,
    TransactionGUID UNIQUEIDENTIFIER DEFAULT NEWID() NOT NULL,
    ConversationID INT NOT NULL FOREIGN KEY REFERENCES Conversations(ConversationID),
    
    -- The prompt (input)
    PromptText NVARCHAR(MAX),  -- Text of the prompt (or transcription if voice)
    PromptType VARCHAR(20) NOT NULL,  -- 'TEXT', 'VOICE', 'IMAGE', 'DOCUMENT'
    PromptTokens INT,  -- Token count for cost tracking
    
    -- The response (output)
    ResponseText NVARCHAR(MAX),  -- AI response
    ResponseTokens INT,  -- Token count
    ResponseModel VARCHAR(100),  -- 'claude-3-5-sonnet', 'whisper-1', etc.
    
    -- Processing metadata
    ProcessingTimeMs INT,  -- How long the AI took
    AIProvider VARCHAR(50),  -- 'ANTHROPIC', 'OPENAI', 'GOOGLE'
    CostUSD DECIMAL(10,6),  -- Actual cost of this transaction
    
    -- Voice-specific fields
    AudioDurationSeconds DECIMAL(10,2),  -- If voice input
    TranscriptionConfidence DECIMAL(5,4),  -- Whisper confidence score
    
    -- Extracted data (what Claude understood)
    ExtractedIntent VARCHAR(100),  -- 'CREATE_TASK', 'QUERY', 'UPDATE', 'SEARCH'
    ExtractedProjectCode VARCHAR(20),  -- If Claude identified a project
    ExtractedCategories NVARCHAR(200),  -- Categories Claude identified
    ExtractedTaskID INT FOREIGN KEY REFERENCES Tasks(TaskID),  -- If a task was created/updated
    
    -- Status
    Status VARCHAR(20) DEFAULT 'COMPLETE',  -- PENDING, COMPLETE, FAILED, RETRY
    ErrorMessage NVARCHAR(MAX),  -- If processing failed
    
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    
    -- For full-text search
    SearchableContent AS (COALESCE(PromptText, N'') + N' ' + COALESCE(ResponseText, N'')) PERSISTED
);

CREATE INDEX IX_Transactions_ConversationID ON Transactions(ConversationID);
CREATE INDEX IX_Transactions_CreatedAt ON Transactions(CreatedAt DESC);
CREATE INDEX IX_Transactions_ExtractedIntent ON Transactions(ExtractedIntent);
CREATE INDEX IX_Transactions_ExtractedProjectCode ON Transactions(ExtractedProjectCode);

-- ============================================
-- MEDIA ATTACHMENTS
-- ============================================

-- MediaFiles: Stores references to files in GCS
CREATE TABLE MediaFiles (
    MediaID INT IDENTITY(1,1) PRIMARY KEY,
    MediaGUID UNIQUEIDENTIFIER DEFAULT NEWID() NOT NULL,
    
    -- File information
    FileName NVARCHAR(500) NOT NULL,
    FileType VARCHAR(50) NOT NULL,  -- 'AUDIO', 'IMAGE', 'DOCUMENT', 'VIDEO'
    MimeType VARCHAR(100) NOT NULL,  -- 'audio/webm', 'image/png', etc.
    FileSizeBytes BIGINT,
    
    -- Storage location (GCS)
    GCSBucket VARCHAR(200) NOT NULL,
    GCSPath NVARCHAR(500) NOT NULL,  -- Full path in bucket
    GCSUrl NVARCHAR(1000),  -- Signed URL (regenerated on access)
    
    -- Processing status
    ProcessingStatus VARCHAR(20) DEFAULT 'UPLOADED',  -- UPLOADED, PROCESSING, PROCESSED, FAILED
    ProcessedAt DATETIME2,
    
    -- For audio files
    AudioDurationSeconds DECIMAL(10,2),
    TranscriptionText NVARCHAR(MAX),  -- Whisper transcription stored here too
    
    -- For images
    ImageWidth INT,
    ImageHeight INT,
    OCRText NVARCHAR(MAX),  -- If we run OCR on screenshots
    ImageDescription NVARCHAR(MAX),  -- Claude's description of the image
    
    -- Metadata
    OriginalFileName NVARCHAR(500),  -- What user uploaded
    UploadSource VARCHAR(50),  -- 'MOBILE', 'WEB', 'API'
    
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    ExpiresAt DATETIME2  -- For temp files
);

CREATE INDEX IX_MediaFiles_FileType ON MediaFiles(FileType);
CREATE INDEX IX_MediaFiles_CreatedAt ON MediaFiles(CreatedAt DESC);

-- TransactionMedia: Links media to transactions (many-to-many)
CREATE TABLE TransactionMedia (
    TransactionMediaID INT IDENTITY(1,1) PRIMARY KEY,
    TransactionID INT NOT NULL FOREIGN KEY REFERENCES Transactions(TransactionID) ON DELETE CASCADE,
    MediaID INT NOT NULL FOREIGN KEY REFERENCES MediaFiles(MediaID),
    MediaRole VARCHAR(20) NOT NULL,  -- 'INPUT' (user sent), 'OUTPUT' (AI generated)
    DisplayOrder INT DEFAULT 0,
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    
    CONSTRAINT UQ_TransactionMedia UNIQUE (TransactionID, MediaID)
);

-- ============================================
-- FULL-TEXT SEARCH SETUP
-- ============================================

-- Create full-text catalog
IF NOT EXISTS (SELECT * FROM sys.fulltext_catalogs WHERE name = 'MetaPM_FTCatalog')
BEGIN
    CREATE FULLTEXT CATALOG MetaPM_FTCatalog AS DEFAULT;
END
GO

-- Full-text index on Transactions
IF NOT EXISTS (SELECT * FROM sys.fulltext_indexes WHERE object_id = OBJECT_ID('Transactions'))
BEGIN
    CREATE FULLTEXT INDEX ON Transactions(SearchableContent)
    KEY INDEX PK__Transact__55433A6B___ ON MetaPM_FTCatalog  -- Replace with actual PK name
    WITH CHANGE_TRACKING AUTO;
END
GO

-- Full-text index on MediaFiles (transcriptions and OCR)
IF NOT EXISTS (SELECT * FROM sys.fulltext_indexes WHERE object_id = OBJECT_ID('MediaFiles'))
BEGIN
    CREATE FULLTEXT INDEX ON MediaFiles(TranscriptionText, OCRText, ImageDescription)
    KEY INDEX PK__MediaFil____ ON MetaPM_FTCatalog
    WITH CHANGE_TRACKING AUTO;
END
GO

-- ============================================
-- USEFUL VIEWS
-- ============================================

-- View: Full transaction history with media counts
CREATE OR ALTER VIEW vw_TransactionHistory AS
SELECT 
    t.TransactionID,
    t.TransactionGUID,
    c.ConversationID,
    c.Title AS ConversationTitle,
    c.Source AS ConversationSource,
    p.ProjectCode,
    p.ProjectName,
    t.PromptText,
    t.PromptType,
    t.ResponseText,
    t.ResponseModel,
    t.AIProvider,
    t.ExtractedIntent,
    t.CostUSD,
    t.AudioDurationSeconds,
    t.CreatedAt,
    (SELECT COUNT(*) FROM TransactionMedia tm WHERE tm.TransactionID = t.TransactionID AND tm.MediaRole = 'INPUT') AS InputMediaCount,
    (SELECT COUNT(*) FROM TransactionMedia tm WHERE tm.TransactionID = t.TransactionID AND tm.MediaRole = 'OUTPUT') AS OutputMediaCount
FROM Transactions t
JOIN Conversations c ON t.ConversationID = c.ConversationID
LEFT JOIN Projects p ON c.ProjectID = p.ProjectID;
GO

-- View: Search across all content (prompts, responses, transcriptions)
CREATE OR ALTER VIEW vw_SearchableContent AS
SELECT 
    'TRANSACTION' AS ContentType,
    t.TransactionID AS ContentID,
    t.TransactionGUID AS ContentGUID,
    c.Title AS Context,
    t.PromptText AS PrimaryText,
    t.ResponseText AS SecondaryText,
    t.CreatedAt,
    p.ProjectCode
FROM Transactions t
JOIN Conversations c ON t.ConversationID = c.ConversationID
LEFT JOIN Projects p ON c.ProjectID = p.ProjectID

UNION ALL

SELECT 
    'MEDIA' AS ContentType,
    m.MediaID AS ContentID,
    m.MediaGUID AS ContentGUID,
    m.FileName AS Context,
    m.TranscriptionText AS PrimaryText,
    COALESCE(m.OCRText, m.ImageDescription) AS SecondaryText,
    m.CreatedAt,
    NULL AS ProjectCode
FROM MediaFiles m
WHERE m.TranscriptionText IS NOT NULL 
   OR m.OCRText IS NOT NULL 
   OR m.ImageDescription IS NOT NULL;
GO

-- View: Cost analysis by project and model
CREATE OR ALTER VIEW vw_CostAnalysis AS
SELECT 
    COALESCE(p.ProjectCode, 'UNASSIGNED') AS ProjectCode,
    t.AIProvider,
    t.ResponseModel,
    COUNT(*) AS TransactionCount,
    SUM(t.CostUSD) AS TotalCostUSD,
    SUM(t.PromptTokens) AS TotalPromptTokens,
    SUM(t.ResponseTokens) AS TotalResponseTokens,
    SUM(t.AudioDurationSeconds) AS TotalAudioSeconds,
    AVG(t.ProcessingTimeMs) AS AvgProcessingTimeMs,
    MIN(t.CreatedAt) AS FirstTransaction,
    MAX(t.CreatedAt) AS LastTransaction
FROM Transactions t
JOIN Conversations c ON t.ConversationID = c.ConversationID
LEFT JOIN Projects p ON c.ProjectID = p.ProjectID
GROUP BY p.ProjectCode, t.AIProvider, t.ResponseModel;
GO

-- ============================================
-- STORED PROCEDURES
-- ============================================

-- Procedure: Start a new conversation
CREATE OR ALTER PROCEDURE sp_StartConversation
    @Source VARCHAR(50),
    @ProjectCode VARCHAR(20) = NULL,
    @Title NVARCHAR(500) = NULL,
    @DeviceInfo NVARCHAR(500) = NULL,
    @Location NVARCHAR(200) = NULL
AS
BEGIN
    DECLARE @ProjectID INT = NULL;
    DECLARE @ConversationID INT;
    
    IF @ProjectCode IS NOT NULL
    BEGIN
        SELECT @ProjectID = ProjectID FROM Projects WHERE ProjectCode = @ProjectCode;
    END
    
    INSERT INTO Conversations (Source, ProjectID, Title, DeviceInfo, Location)
    VALUES (@Source, @ProjectID, @Title, @DeviceInfo, @Location);
    
    SET @ConversationID = SCOPE_IDENTITY();
    
    SELECT 
        ConversationID,
        ConversationGUID,
        Title,
        Source,
        CreatedAt
    FROM Conversations 
    WHERE ConversationID = @ConversationID;
END;
GO

-- Procedure: Record a transaction (prompt + response)
CREATE OR ALTER PROCEDURE sp_RecordTransaction
    @ConversationGUID UNIQUEIDENTIFIER,
    @PromptText NVARCHAR(MAX),
    @PromptType VARCHAR(20) = 'TEXT',
    @ResponseText NVARCHAR(MAX) = NULL,
    @ResponseModel VARCHAR(100) = NULL,
    @AIProvider VARCHAR(50) = NULL,
    @PromptTokens INT = NULL,
    @ResponseTokens INT = NULL,
    @ProcessingTimeMs INT = NULL,
    @CostUSD DECIMAL(10,6) = NULL,
    @AudioDurationSeconds DECIMAL(10,2) = NULL,
    @TranscriptionConfidence DECIMAL(5,4) = NULL,
    @ExtractedIntent VARCHAR(100) = NULL,
    @ExtractedProjectCode VARCHAR(20) = NULL,
    @ExtractedCategories NVARCHAR(200) = NULL
AS
BEGIN
    DECLARE @ConversationID INT;
    DECLARE @TransactionID INT;
    
    SELECT @ConversationID = ConversationID 
    FROM Conversations 
    WHERE ConversationGUID = @ConversationGUID;
    
    IF @ConversationID IS NULL
    BEGIN
        RAISERROR('Conversation not found', 16, 1);
        RETURN;
    END
    
    INSERT INTO Transactions (
        ConversationID, PromptText, PromptType, ResponseText, ResponseModel,
        AIProvider, PromptTokens, ResponseTokens, ProcessingTimeMs, CostUSD,
        AudioDurationSeconds, TranscriptionConfidence, ExtractedIntent,
        ExtractedProjectCode, ExtractedCategories
    )
    VALUES (
        @ConversationID, @PromptText, @PromptType, @ResponseText, @ResponseModel,
        @AIProvider, @PromptTokens, @ResponseTokens, @ProcessingTimeMs, @CostUSD,
        @AudioDurationSeconds, @TranscriptionConfidence, @ExtractedIntent,
        @ExtractedProjectCode, @ExtractedCategories
    );
    
    SET @TransactionID = SCOPE_IDENTITY();
    
    -- Update conversation timestamp
    UPDATE Conversations SET UpdatedAt = GETUTCDATE() WHERE ConversationID = @ConversationID;
    
    SELECT 
        TransactionID,
        TransactionGUID,
        PromptText,
        ResponseText,
        CreatedAt
    FROM Transactions 
    WHERE TransactionID = @TransactionID;
END;
GO

-- Procedure: Full-text search across all content
CREATE OR ALTER PROCEDURE sp_SearchContent
    @SearchTerms NVARCHAR(500),
    @ProjectCode VARCHAR(20) = NULL,
    @ContentType VARCHAR(20) = NULL,  -- 'TRANSACTION', 'MEDIA', or NULL for all
    @StartDate DATETIME2 = NULL,
    @EndDate DATETIME2 = NULL,
    @MaxResults INT = 50
AS
BEGIN
    -- Build the search query
    SELECT TOP (@MaxResults)
        ContentType,
        ContentID,
        ContentGUID,
        Context,
        PrimaryText,
        SecondaryText,
        CreatedAt,
        ProjectCode
    FROM vw_SearchableContent
    WHERE 
        (CONTAINS((PrimaryText, SecondaryText), @SearchTerms) OR 
         PrimaryText LIKE '%' + @SearchTerms + '%' OR 
         SecondaryText LIKE '%' + @SearchTerms + '%')
        AND (@ProjectCode IS NULL OR ProjectCode = @ProjectCode)
        AND (@ContentType IS NULL OR ContentType = @ContentType)
        AND (@StartDate IS NULL OR CreatedAt >= @StartDate)
        AND (@EndDate IS NULL OR CreatedAt <= @EndDate)
    ORDER BY CreatedAt DESC;
END;
GO

-- Procedure: Get conversation with all transactions and media
CREATE OR ALTER PROCEDURE sp_GetConversationFull
    @ConversationGUID UNIQUEIDENTIFIER
AS
BEGIN
    -- Get conversation details
    SELECT 
        c.ConversationID,
        c.ConversationGUID,
        c.Title,
        c.Source,
        c.Status,
        c.CreatedAt,
        c.UpdatedAt,
        p.ProjectCode,
        p.ProjectName
    FROM Conversations c
    LEFT JOIN Projects p ON c.ProjectID = p.ProjectID
    WHERE c.ConversationGUID = @ConversationGUID;
    
    -- Get all transactions
    SELECT 
        t.TransactionID,
        t.TransactionGUID,
        t.PromptText,
        t.PromptType,
        t.ResponseText,
        t.ResponseModel,
        t.AIProvider,
        t.ExtractedIntent,
        t.ExtractedProjectCode,
        t.CostUSD,
        t.AudioDurationSeconds,
        t.CreatedAt
    FROM Transactions t
    JOIN Conversations c ON t.ConversationID = c.ConversationID
    WHERE c.ConversationGUID = @ConversationGUID
    ORDER BY t.CreatedAt;
    
    -- Get all media for this conversation
    SELECT 
        m.MediaID,
        m.MediaGUID,
        m.FileName,
        m.FileType,
        m.MimeType,
        m.GCSUrl,
        m.TranscriptionText,
        m.ImageDescription,
        tm.TransactionID,
        tm.MediaRole,
        m.CreatedAt
    FROM MediaFiles m
    JOIN TransactionMedia tm ON m.MediaID = tm.MediaID
    JOIN Transactions t ON tm.TransactionID = t.TransactionID
    JOIN Conversations c ON t.ConversationID = c.ConversationID
    WHERE c.ConversationGUID = @ConversationGUID
    ORDER BY t.CreatedAt, tm.DisplayOrder;
END;
GO

-- ============================================
-- ANALYTICS PROCEDURES
-- ============================================

-- Procedure: Get usage patterns (for identifying common tasks, issues)
CREATE OR ALTER PROCEDURE sp_GetUsagePatterns
    @DaysBack INT = 30,
    @ProjectCode VARCHAR(20) = NULL
AS
BEGIN
    -- Intent distribution
    SELECT 
        ExtractedIntent,
        COUNT(*) AS TransactionCount,
        AVG(ProcessingTimeMs) AS AvgProcessingMs
    FROM Transactions t
    JOIN Conversations c ON t.ConversationID = c.ConversationID
    LEFT JOIN Projects p ON c.ProjectID = p.ProjectID
    WHERE t.CreatedAt >= DATEADD(DAY, -@DaysBack, GETUTCDATE())
        AND (@ProjectCode IS NULL OR p.ProjectCode = @ProjectCode)
        AND t.ExtractedIntent IS NOT NULL
    GROUP BY ExtractedIntent
    ORDER BY TransactionCount DESC;
    
    -- Source distribution
    SELECT 
        c.Source,
        COUNT(*) AS ConversationCount,
        COUNT(DISTINCT CAST(c.CreatedAt AS DATE)) AS ActiveDays
    FROM Conversations c
    WHERE c.CreatedAt >= DATEADD(DAY, -@DaysBack, GETUTCDATE())
    GROUP BY c.Source
    ORDER BY ConversationCount DESC;
    
    -- Daily volume
    SELECT 
        CAST(t.CreatedAt AS DATE) AS TransactionDate,
        COUNT(*) AS TransactionCount,
        SUM(t.CostUSD) AS DailyCostUSD
    FROM Transactions t
    WHERE t.CreatedAt >= DATEADD(DAY, -@DaysBack, GETUTCDATE())
    GROUP BY CAST(t.CreatedAt AS DATE)
    ORDER BY TransactionDate;
END;
GO
