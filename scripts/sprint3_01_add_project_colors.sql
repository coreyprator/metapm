-- Sprint 3 Feature 1: Project Color Themes
-- Add ColorCode column to Projects table for Peacock-style project theming

-- Add ColorCode column
ALTER TABLE Projects ADD ColorCode NVARCHAR(7) NULL;

-- Add description for documentation
EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Hex color code for Peacock-style project theming (e.g., #FF6B6B)',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'TABLE', @level1name = N'Projects',
    @level2type = N'COLUMN', @level2name = N'ColorCode';

-- Optional: Set sample colors for existing projects
UPDATE Projects SET ColorCode = '#42b883' WHERE ProjectCode = 'META';   -- Vue Green
UPDATE Projects SET ColorCode = '#007ACC' WHERE ProjectCode = 'HL';     -- Azure Blue
UPDATE Projects SET ColorCode = '#DD4814' WHERE ProjectCode = 'AF';     -- Ubuntu Orange
UPDATE Projects SET ColorCode = '#CF9FFF' WHERE ProjectCode = 'SF';     -- Lavender
UPDATE Projects SET ColorCode = '#4FC08D' WHERE ProjectCode = 'EM';     -- Mint

-- Verify the changes
SELECT ProjectCode, ProjectName, ColorCode FROM Projects;
