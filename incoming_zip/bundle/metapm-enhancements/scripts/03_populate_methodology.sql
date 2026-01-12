-- ============================================
-- MetaPM Methodology Rules Population
-- Extracted from project-methodology v3.12.1
-- and lessons learned across projects
-- Run AFTER schema updates
-- ============================================

-- Clear existing rules if you want a fresh start (OPTIONAL - commented out)
-- DELETE FROM MethodologyViolations;
-- DELETE FROM MethodologyRules;
-- GO

-- ============================================
-- Insert/Update Methodology Rules
-- ============================================

-- Check what rules exist
SELECT RuleID, RuleCode, RuleName, Category, Severity FROM MethodologyRules ORDER BY RuleCode;
GO

-- Use MERGE to insert or update rules
-- ============================================
-- DEVELOPMENT RULES
-- ============================================

MERGE MethodologyRules AS target
USING (SELECT 'LL-001' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'RTFM First',
    Description = 'Read The F***ing Manual before writing code. Always check official documentation, existing skills, and project READMEs before implementing.',
    Rationale = 'Prevents reinventing the wheel and ensures solutions align with established patterns.',
    Category = 'DEVELOPMENT',
    Severity = 'HIGH',
    IsActive = 1
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-001', 'RTFM First', 
        'Read The F***ing Manual before writing code. Always check official documentation, existing skills, and project READMEs before implementing.',
        'Prevents reinventing the wheel and ensures solutions align with established patterns.',
        'DEVELOPMENT', 'HIGH');
GO

MERGE MethodologyRules AS target
USING (SELECT 'LL-002' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'External Verification',
    Description = 'Verify all outputs and assumptions externally. Don''t trust AI-generated code without testing. Check database results in SSMS, API responses in browser.',
    Rationale = 'AI can hallucinate. Manual verification catches errors early.',
    Category = 'TESTING',
    Severity = 'CRITICAL'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-002', 'External Verification', 
        'Verify all outputs and assumptions externally. Don''t trust AI-generated code without testing.',
        'AI can hallucinate. Manual verification catches errors early.',
        'TESTING', 'CRITICAL');
GO

MERGE MethodologyRules AS target
USING (SELECT 'LL-003' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'Data is Cheap, API Calls are Expensive',
    Description = 'Cache AI-generated content. Store transcriptions, responses, and metadata in the database. Avoid regenerating content that can be retrieved.',
    Rationale = 'API costs add up quickly. A $0.05 flashcard x 1000 = $50.',
    Category = 'DEVELOPMENT',
    Severity = 'HIGH'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-003', 'Data is Cheap, API Calls are Expensive', 
        'Cache AI-generated content. Store transcriptions, responses, and metadata in the database. Avoid regenerating content.',
        'API costs add up quickly. A $0.05 flashcard x 1000 = $50.',
        'DEVELOPMENT', 'HIGH');
GO

MERGE MethodologyRules AS target
USING (SELECT 'LL-004' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'Examine Working Projects First',
    Description = 'Before debugging a new issue, check how similar problems were solved in other working projects (Etymython, HarmonyLab, etc.).',
    Rationale = 'The Etymython direct IP pattern revealed the Cloud SQL Proxy issue immediately.',
    Category = 'DEVELOPMENT',
    Severity = 'MEDIUM'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-004', 'Examine Working Projects First', 
        'Before debugging a new issue, check how similar problems were solved in other working projects.',
        'The Etymython direct IP pattern revealed the Cloud SQL Proxy issue immediately.',
        'DEVELOPMENT', 'MEDIUM');
GO

MERGE MethodologyRules AS target
USING (SELECT 'LL-005' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'SET NOCOUNT ON',
    Description = 'Always add SET NOCOUNT ON to SQL Server stored procedures that return data. Without it, pyodbc/SQLAlchemy may grab empty row count messages instead of actual data.',
    Rationale = 'Caused hours of debugging when sp_StartConversation returned None instead of conversation data.',
    Category = 'DEVELOPMENT',
    Severity = 'HIGH'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-005', 'SET NOCOUNT ON', 
        'Always add SET NOCOUNT ON to SQL Server stored procedures that return data.',
        'Caused hours of debugging when sp_StartConversation returned None.',
        'DEVELOPMENT', 'HIGH');
GO

MERGE MethodologyRules AS target
USING (SELECT 'LL-006' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'Direct IP for SQL Server on GCP',
    Description = 'Use direct public IP connection for SQL Server on GCP Cloud SQL, not Cloud SQL Proxy. SQL Server ODBC doesn''t support Unix sockets like PostgreSQL/MySQL.',
    Rationale = 'Cloud SQL Proxy creates TCP listener on 127.0.0.1:1433 but pyodbc connection still failed. Direct IP works reliably.',
    Category = 'DEPLOYMENT',
    Severity = 'HIGH'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-006', 'Direct IP for SQL Server on GCP', 
        'Use direct public IP for SQL Server on GCP Cloud SQL, not Cloud SQL Proxy.',
        'Cloud SQL Proxy TCP connection failed with pyodbc. Direct IP works.',
        'DEPLOYMENT', 'HIGH');
GO

MERGE MethodologyRules AS target
USING (SELECT 'LL-007' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'Named Primary Keys for Full-Text',
    Description = 'SQL Server full-text indexes require explicitly named primary keys or unique indexes. Auto-generated PK names like PK__Table__ID cause errors.',
    Rationale = 'Full-text index creation failed with "not a valid index" until explicit PK_Transactions constraint was created.',
    Category = 'DEVELOPMENT',
    Severity = 'MEDIUM'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-007', 'Named Primary Keys for Full-Text', 
        'SQL Server full-text indexes require explicitly named primary keys or unique indexes.',
        'Full-text index creation failed until explicit PK_Transactions was created.',
        'DEVELOPMENT', 'MEDIUM');
GO

MERGE MethodologyRules AS target
USING (SELECT 'LL-008' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'Transaction Logging for Undo',
    Description = 'Log all AI transactions with full context (prompt, response, model, cost) to enable undo functionality and cost tracking.',
    Rationale = 'Can''t undo what you didn''t record. Transaction history enables audit, replay, and cost analysis.',
    Category = 'DEVELOPMENT',
    Severity = 'MEDIUM'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-008', 'Transaction Logging for Undo', 
        'Log all AI transactions with full context to enable undo functionality and cost tracking.',
        'Can''t undo what you didn''t record. Transaction history enables audit and analysis.',
        'DEVELOPMENT', 'MEDIUM');
GO

-- ============================================
-- TESTING RULES
-- ============================================

MERGE MethodologyRules AS target
USING (SELECT 'LL-009' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'Playwright for UI Verification',
    Description = 'Use Playwright for automated UI testing before deployment. Visual verification catches issues that unit tests miss.',
    Rationale = 'Deployment issues in ArtForge were caught only after manual testing revealed UI failures.',
    Category = 'TESTING',
    Severity = 'MEDIUM'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-009', 'Playwright for UI Verification', 
        'Use Playwright for automated UI testing before deployment.',
        'Deployment issues were caught only after manual testing revealed UI failures.',
        'TESTING', 'MEDIUM');
GO

MERGE MethodologyRules AS target
USING (SELECT 'LL-010' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'Test with Real Data',
    Description = 'Test with production-like data, not just happy path examples. Unicode, special characters, and edge cases break things.',
    Rationale = 'Greek text appeared correctly in preview but failed to save to SQL Server due to encoding issues.',
    Category = 'TESTING',
    Severity = 'HIGH'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-010', 'Test with Real Data', 
        'Test with production-like data including Unicode, special characters, and edge cases.',
        'Greek text appeared correctly in preview but failed to save to SQL Server.',
        'TESTING', 'HIGH');
GO

MERGE MethodologyRules AS target
USING (SELECT 'LL-011' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'Verify Database Writes',
    Description = 'After any INSERT/UPDATE operation, query the database to confirm the data was actually written. Silent failures are the worst failures.',
    Rationale = 'Database writes were failing silently or not executing at all in Etymython Sprint 6.',
    Category = 'TESTING',
    Severity = 'CRITICAL'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-011', 'Verify Database Writes', 
        'After any INSERT/UPDATE, query the database to confirm data was actually written.',
        'Database writes were failing silently in Etymython Sprint 6.',
        'TESTING', 'CRITICAL');
GO

-- ============================================
-- DEPLOYMENT RULES
-- ============================================

MERGE MethodologyRules AS target
USING (SELECT 'LL-012' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'Secrets in Secret Manager',
    Description = 'Never hardcode API keys, passwords, or connection strings. Use GCP Secret Manager and --set-secrets in Cloud Run deployment.',
    Rationale = 'Security best practice. Also enables easy rotation without code changes.',
    Category = 'DEPLOYMENT',
    Severity = 'CRITICAL'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-012', 'Secrets in Secret Manager', 
        'Never hardcode API keys or passwords. Use GCP Secret Manager and --set-secrets.',
        'Security best practice. Enables easy rotation without code changes.',
        'DEPLOYMENT', 'CRITICAL');
GO

MERGE MethodologyRules AS target
USING (SELECT 'LL-013' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'Grant IAM Before Deploying',
    Description = 'Grant service account access to secrets BEFORE deployment. Missing permissions cause silent failures on Cloud Run startup.',
    Rationale = 'Deployment succeeded but endpoints 500''d because service account couldn''t read DB_PASSWORD secret.',
    Category = 'DEPLOYMENT',
    Severity = 'HIGH'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-013', 'Grant IAM Before Deploying', 
        'Grant service account access to secrets BEFORE deployment.',
        'Deployment succeeded but endpoints failed due to missing secret access.',
        'DEPLOYMENT', 'HIGH');
GO

MERGE MethodologyRules AS target
USING (SELECT 'LL-014' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'Custom Domain SSL Delay',
    Description = 'After mapping a custom domain to Cloud Run, SSL provisioning takes 15-30 minutes. Don''t panic if HTTPS doesn''t work immediately.',
    Rationale = 'Thought something was broken when metapm.rentyourcio.com showed certificate error right after mapping.',
    Category = 'DEPLOYMENT',
    Severity = 'LOW'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-014', 'Custom Domain SSL Delay', 
        'SSL provisioning takes 15-30 minutes after domain mapping. Don''t panic.',
        'Certificate error was just timing, not configuration.',
        'DEPLOYMENT', 'LOW');
GO

-- ============================================
-- DOCUMENTATION RULES
-- ============================================

MERGE MethodologyRules AS target
USING (SELECT 'LL-015' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'Document Deployment Commands',
    Description = 'Keep the exact gcloud deploy command in the README or deployment script. One typo in --set-secrets breaks everything.',
    Rationale = 'Had to reconstruct the full deploy command multiple times across sessions.',
    Category = 'DOCUMENTATION',
    Severity = 'MEDIUM'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-015', 'Document Deployment Commands', 
        'Keep exact gcloud deploy command in README. One typo breaks everything.',
        'Had to reconstruct full deploy command multiple times.',
        'DOCUMENTATION', 'MEDIUM');
GO

MERGE MethodologyRules AS target
USING (SELECT 'LL-016' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'Lessons Learned Document',
    Description = 'Maintain a LESSONS_LEARNED.md in each project root. Update it when you solve a hard problem.',
    Rationale = 'Future you will forget. Future AI assistants won''t know. Write it down.',
    Category = 'DOCUMENTATION',
    Severity = 'MEDIUM'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-016', 'Lessons Learned Document', 
        'Maintain LESSONS_LEARNED.md in each project. Update when solving hard problems.',
        'Future you will forget. Future AI assistants won''t know. Write it down.',
        'DOCUMENTATION', 'MEDIUM');
GO

MERGE MethodologyRules AS target
USING (SELECT 'LL-017' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'Store AI Chat Thread URLs',
    Description = 'Save the Claude/ChatGPT conversation URL in the project. These threads contain valuable context and decisions.',
    Rationale = 'Created CurrentAIThreadURL field specifically to track ongoing AI collaborations per project.',
    Category = 'DOCUMENTATION',
    Severity = 'MEDIUM'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-017', 'Store AI Chat Thread URLs', 
        'Save Claude/ChatGPT conversation URLs in project. Contains valuable context.',
        'Created CurrentAIThreadURL field to track AI collaborations.',
        'DOCUMENTATION', 'MEDIUM');
GO

-- ============================================
-- PROCESS RULES
-- ============================================

MERGE MethodologyRules AS target
USING (SELECT 'LL-018' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'Complete Over Incremental',
    Description = 'Prefer complete solutions over incremental builds when working with AI. Partial implementations lead to inconsistent state.',
    Rationale = 'Corey''s preference for comprehensive documentation and complete feature bundles.',
    Category = 'PROCESS',
    Severity = 'MEDIUM'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-018', 'Complete Over Incremental', 
        'Prefer complete solutions over incremental builds with AI.',
        'Partial implementations lead to inconsistent state.',
        'PROCESS', 'MEDIUM');
GO

MERGE MethodologyRules AS target
USING (SELECT 'LL-019' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'VS Code Prompt Handoff',
    Description = 'When delegating to VS Code Copilot, provide a complete, self-contained prompt with all context. Don''t assume shared knowledge.',
    Rationale = 'VS Code Copilot can thrash without clear architectural direction.',
    Category = 'PROCESS',
    Severity = 'MEDIUM'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-019', 'VS Code Prompt Handoff', 
        'Provide complete, self-contained prompts to VS Code Copilot.',
        'Copilot thrashes without clear architectural direction.',
        'PROCESS', 'MEDIUM');
GO

MERGE MethodologyRules AS target
USING (SELECT 'LL-020' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'SQLAlchemy Connection Pooling',
    Description = 'Use SQLAlchemy with connection pooling for database connections instead of raw pyodbc. Prevents connection exhaustion on Cloud Run.',
    Rationale = 'Etymython pattern: pool_size=5, max_overflow=10, pool_recycle=3600.',
    Category = 'DEVELOPMENT',
    Severity = 'MEDIUM'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-020', 'SQLAlchemy Connection Pooling', 
        'Use SQLAlchemy with connection pooling instead of raw pyodbc.',
        'Prevents connection exhaustion. Etymython pattern works.',
        'DEVELOPMENT', 'MEDIUM');
GO

MERGE MethodologyRules AS target
USING (SELECT 'LL-021' AS RuleCode) AS source ON target.RuleCode = source.RuleCode
WHEN MATCHED THEN UPDATE SET 
    RuleName = 'Track Combination Logic',
    Description = 'When parsing MIDI or complex files, verify track/channel combination logic. Multiple tracks may need merging for accurate interpretation.',
    Rationale = 'HarmonyLab MIDI parser produced hallucinations until track combination logic was fixed to detect jazz chord voicings.',
    Category = 'DEVELOPMENT',
    Severity = 'MEDIUM'
WHEN NOT MATCHED THEN INSERT (RuleCode, RuleName, Description, Rationale, Category, Severity)
VALUES ('LL-021', 'Track Combination Logic', 
        'Verify track/channel combination logic when parsing MIDI or complex files.',
        'HarmonyLab MIDI parser hallucinated until track logic was fixed.',
        'DEVELOPMENT', 'MEDIUM');
GO

-- ============================================
-- Verify Results
-- ============================================

SELECT 
    RuleCode,
    RuleName,
    Category,
    Severity,
    LEFT(Description, 60) + '...' AS DescriptionPreview
FROM MethodologyRules
WHERE IsActive = 1
ORDER BY RuleCode;
GO

SELECT 
    Category,
    COUNT(*) AS RuleCount
FROM MethodologyRules
WHERE IsActive = 1
GROUP BY Category
ORDER BY COUNT(*) DESC;
GO

PRINT '';
PRINT '=== METHODOLOGY RULES POPULATION COMPLETE ===';
PRINT 'Total active rules: ' + CAST((SELECT COUNT(*) FROM MethodologyRules WHERE IsActive = 1) AS VARCHAR(10));
GO
