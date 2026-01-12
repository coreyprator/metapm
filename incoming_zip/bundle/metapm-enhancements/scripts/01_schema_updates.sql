-- ============================================
-- MetaPM Schema Updates - Rich Text & Project Enhancements
-- Run this in SSMS against MetaPM database
-- ============================================

-- ============================================
-- 1. Add ContentHTML to Projects for rich text
-- ============================================

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('Projects') AND name = 'ContentHTML')
BEGIN
    ALTER TABLE Projects ADD ContentHTML NVARCHAR(MAX);
    PRINT 'Added ContentHTML to Projects';
END
GO

-- ============================================
-- 2. Add GoalStatement to Projects
-- ============================================

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('Projects') AND name = 'GoalStatement')
BEGIN
    ALTER TABLE Projects ADD GoalStatement NVARCHAR(500);
    PRINT 'Added GoalStatement to Projects';
END
GO

-- ============================================
-- 3. Add PriorityNextSteps to Projects
-- ============================================

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('Projects') AND name = 'PriorityNextSteps')
BEGIN
    ALTER TABLE Projects ADD PriorityNextSteps NVARCHAR(MAX);
    PRINT 'Added PriorityNextSteps to Projects';
END
GO

-- ============================================
-- 4. Add TechStack to Projects
-- ============================================

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('Projects') AND name = 'TechStack')
BEGIN
    ALTER TABLE Projects ADD TechStack NVARCHAR(500);
    PRINT 'Added TechStack to Projects';
END
GO

-- ============================================
-- 5. Add ProductionURL to Projects
-- ============================================

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('Projects') AND name = 'ProductionURL')
BEGIN
    ALTER TABLE Projects ADD ProductionURL NVARCHAR(500);
    PRINT 'Added ProductionURL to Projects';
END
GO

-- ============================================
-- 6. Add VSCodePath and GitHubURL if not present
-- ============================================

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('Projects') AND name = 'VSCodePath')
BEGIN
    ALTER TABLE Projects ADD VSCodePath NVARCHAR(500);
    PRINT 'Added VSCodePath to Projects';
END
GO

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('Projects') AND name = 'GitHubURL')
BEGIN
    ALTER TABLE Projects ADD GitHubURL NVARCHAR(500);
    PRINT 'Added GitHubURL to Projects';
END
GO

-- ============================================
-- Verify Updated Schema
-- ============================================

SELECT 
    c.name AS ColumnName,
    t.name AS DataType,
    c.max_length,
    c.is_nullable
FROM sys.columns c
JOIN sys.types t ON c.user_type_id = t.user_type_id
WHERE c.object_id = OBJECT_ID('Projects')
ORDER BY c.column_id;
GO

PRINT '';
PRINT '=== SCHEMA UPDATES COMPLETE ===';
GO
