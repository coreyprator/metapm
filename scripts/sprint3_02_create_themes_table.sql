-- Sprint 3 Feature 4: Theme CRUD
-- Create Themes table for managing project themes

-- Create Themes table
CREATE TABLE Themes (
    ThemeID INT IDENTITY(1,1) PRIMARY KEY,
    ThemeName NVARCHAR(100) NOT NULL UNIQUE,
    ThemeCode NVARCHAR(20) NOT NULL UNIQUE,
    Description NVARCHAR(500),
    DisplayOrder INT DEFAULT 0,
    ColorCode NVARCHAR(7),
    IsActive BIT DEFAULT 1,
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    UpdatedAt DATETIME2 DEFAULT GETUTCDATE()
);

-- Add indexes
CREATE INDEX IX_Themes_DisplayOrder ON Themes(DisplayOrder);
CREATE INDEX IX_Themes_IsActive ON Themes(IsActive);

-- Add descriptions
EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Project themes for categorization and organization',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'TABLE', @level1name = N'Themes';

-- Seed initial themes
INSERT INTO Themes (ThemeCode, ThemeName, Description, DisplayOrder, ColorCode) VALUES
('A', 'Creation', 'Building and creating things', 1, '#FF6B6B'),
('B', 'Learning', 'Education and skill development', 2, '#4ECDC4'),
('C', 'Adventure', 'Travel and experiences', 3, '#FFD93D'),
('D', 'Relationships', 'People and connections', 4, '#95E1D3'),
('META', 'Meta', 'Project management and tools', 5, '#A8DADC');

-- Optional: Add ThemeID column to Projects table
ALTER TABLE Projects ADD ThemeID INT NULL;

-- Optional: Add foreign key constraint
-- ALTER TABLE Projects ADD CONSTRAINT FK_Projects_Themes 
--     FOREIGN KEY (ThemeID) REFERENCES Themes(ThemeID);

-- Optional: Migrate existing theme data
UPDATE p SET ThemeID = t.ThemeID
FROM Projects p
INNER JOIN Themes t ON p.Theme = t.ThemeName
WHERE p.Theme IS NOT NULL;

-- Verify the changes
SELECT * FROM Themes ORDER BY DisplayOrder;
SELECT ProjectCode, ProjectName, Theme, ThemeID FROM Projects;
