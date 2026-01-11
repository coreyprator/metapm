-- Fix MetaPM Database Schema Issues
-- Run this in SSMS against the MetaPM database

-- ============================================
-- FIX 1: Increase Title column length
-- ============================================
-- Tasks.Title is too short (currently 100 or 200)
-- Increase to 500 to handle longer titles

ALTER TABLE Tasks
ALTER COLUMN Title NVARCHAR(500) NOT NULL;

PRINT '✓ Tasks.Title column increased to 500 characters';

-- ============================================
-- FIX 2: Verify table structure
-- ============================================
-- Check current column lengths
SELECT 
    t.name AS TableName,
    c.name AS ColumnName,
    ty.name AS DataType,
    c.max_length AS MaxLength,
    c.max_length / 2 AS ActualCharLength
FROM sys.tables t
JOIN sys.columns c ON t.object_id = c.object_id
JOIN sys.types ty ON c.user_type_id = ty.user_type_id
WHERE t.name IN ('Tasks', 'Projects')
    AND c.name IN ('Title', 'ProjectName', 'Description')
ORDER BY t.name, c.name;

PRINT '';
PRINT '=== SCHEMA FIX COMPLETE ===';
PRINT 'You can now add tasks with titles up to 500 characters.';
