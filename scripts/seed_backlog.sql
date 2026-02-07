-- ============================================
-- SEED DATA: Bugs & Requirements
-- MetaPM Sprint 5
-- ============================================
-- Depends on: Projects table already seeded (schema.sql)
-- Run AFTER backlog_schema.sql

-- Super-Flashcards (ProjectCode = 'SF')
INSERT INTO Bugs (ProjectID, Code, Title, Description, Status, Priority)
SELECT ProjectID, 'BUG-006', 'OAuth session expiry on iOS',
    'Google OAuth tokens expire and are not refreshed. Users get logged out after ~1hr. Needs refresh token flow and iOS ITP mitigation.',
    'Deferred', 'P3'
FROM Projects WHERE ProjectCode = 'SF';

INSERT INTO Requirements (ProjectID, Code, Title, Description, Status, Priority)
SELECT ProjectID, 'REQ-001', 'Practice Tab',
    'New tab between Read and Browse that holds all pronunciation UI. Read mode becomes a clean reference view. Implemented in v2.10.0.',
    'Done', 'P1'
FROM Projects WHERE ProjectCode = 'SF';

-- ArtForge (ProjectCode = 'AF')
INSERT INTO Bugs (ProjectID, Code, Title, Description, Status, Priority)
SELECT ProjectID, 'BUG-001', 'OAuth login does not persist',
    'After successful OAuth login, refreshing the page loses authentication state. Session cookie or token storage issue.',
    'Open', 'P1'
FROM Projects WHERE ProjectCode = 'AF';

INSERT INTO Bugs (ProjectID, Code, Title, Description, Status, Priority)
SELECT ProjectID, 'BUG-002', 'AI provider selection not saving',
    'Selecting a different AI provider in settings reverts to default on page reload.',
    'Open', 'P1'
FROM Projects WHERE ProjectCode = 'AF';

INSERT INTO Requirements (ProjectID, Code, Title, Description, Status, Priority)
SELECT ProjectID, 'REQ-001', 'Storyboard generation workflow',
    'Multi-panel storyboard generation from text prompts with consistent character style across panels.',
    'Backlog', 'P2'
FROM Projects WHERE ProjectCode = 'AF';

-- Etymython (ProjectCode = 'EM')
INSERT INTO Bugs (ProjectID, Code, Title, Description, Status, Priority)
SELECT ProjectID, 'BUG-001', 'NULL etymology ID in word detail',
    'Some words have NULL etymology_id causing detail page to crash with unhandled exception.',
    'Open', 'P2'
FROM Projects WHERE ProjectCode = 'EM';

INSERT INTO Bugs (ProjectID, Code, Title, Description, Status, Priority)
SELECT ProjectID, 'BUG-002', 'Unicode corruption in Greek text',
    'Greek characters display as replacement characters in some contexts. Encoding mismatch between DB and frontend.',
    'Open', 'P2'
FROM Projects WHERE ProjectCode = 'EM';

INSERT INTO Requirements (ProjectID, Code, Title, Description, Status, Priority)
SELECT ProjectID, 'REQ-001', 'Story generation from etymology',
    'Generate narrative stories that weave together etymological roots, making word origins memorable through storytelling.',
    'Backlog', 'P3'
FROM Projects WHERE ProjectCode = 'EM';

-- HarmonyLab (ProjectCode = 'HL')
INSERT INTO Requirements (ProjectID, Code, Title, Description, Status, Priority)
SELECT ProjectID, 'REQ-001', 'Quiz interface for chord progressions',
    'Interactive quiz mode where users identify chord progressions by ear. Includes scoring and progress tracking.',
    'Backlog', 'P4'
FROM Projects WHERE ProjectCode = 'HL';
