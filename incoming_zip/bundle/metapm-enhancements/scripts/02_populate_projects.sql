-- ============================================
-- MetaPM Project Content Population
-- Extracted from 2026 Personal Projects Plan
-- Run AFTER 01_schema_updates.sql
-- ============================================

-- ============================================
-- MERGE Projects (Insert or Update)
-- This handles both new projects and updating existing ones
-- ============================================

-- First, let's see what projects already exist
SELECT ProjectID, ProjectCode, ProjectName, Theme, Status FROM Projects;
GO

-- ============================================
-- Theme A: Creation & Expression
-- ============================================

-- A1: Art Creation System (updates ArtForge)
MERGE Projects AS target
USING (SELECT 'AF' AS ProjectCode) AS source
ON target.ProjectCode = source.ProjectCode
WHEN MATCHED THEN
    UPDATE SET 
        ProjectName = 'ArtForge - Art Creation System',
        Description = 'An RLHF-driven art discovery engine that generates images across 53 artistic styles from text prompts or reference images.',
        Theme = 'Creation',
        Status = 'ACTIVE',
        GoalStatement = 'Create better art by developing new methods: AI tools, video/3D, repeatable processes',
        TechStack = 'Python/FastAPI, DALL-E 3, SQL Server, GCP Cloud Run',
        ProductionURL = 'https://artforge.rentyourcio.com/',
        VSCodePath = 'G:\My Drive\Code\Python\artforge',
        GitHubURL = 'https://github.com/coreyprator/artforge',
        PriorityNextSteps = '1. Deploy ArtForge to production and test RLHF ranking system
2. Document 3 new AI art style recipes in the methods guide
3. Schedule one major museum trip (Prado or Vatican)',
        ContentHTML = N'<div class="project-content">
<h2>Project Description</h2>
<ul>
<li>In 2024, I created 100 art pieces using AI image generation tools to enhance reference images from my camera and iPhone.</li>
<li>In 2025, I focused on quality over quantity, using AI and Cubist Software to expand my toolset.</li>
<li>In 2026, I will create better art by:
  <ul>
    <li>Exploring new dimensions (time, video, 3D, gallery of styles, SFX, medium)</li>
    <li>Using AI more effectively</li>
    <li>Building repeatable processes</li>
    <li>Using reference art to go from still to video with 3D perspective (Van Gogh Museum inspiration)</li>
    <li>Seeking more inspiration through travel, exhibitions, museums</li>
  </ul>
</li>
</ul>

<h2>Methods to Become More Creative</h2>
<ul>
<li><strong>Observe:</strong> Be on the lookout for new dimensions. Intentional Awareness.</li>
<li><strong>Share with others:</strong> By explaining to family and friends, and teaching others, push my own creative boundaries.</li>
</ul>

<h2>Key Features</h2>
<ul>
<li>1-5 star rating system for human feedback</li>
<li>Leaderboard showing top/bottom rated styles</li>
<li>Shareable collections</li>
<li>53 artistic style categories spanning Art Historical, Traditional Medium, Cultural Tradition, Photorealistic, Sculptural, and Digital/Contemporary</li>
</ul>

<h2>Museum Visits To Schedule</h2>
<ul>
<li>National Gallery of Art (Washington, D.C.)</li>
<li>Museum of Fine Arts Houston</li>
<li>The British Museum (London) — Rosetta Stone, Elgin Marbles</li>
<li>The Vatican Museums — Sistine Chapel, Raphael Rooms</li>
<li>The Prado Museum (Madrid) — Velázquez, Goya, El Greco</li>
<li>Uffizi Gallery (Florence) — Botticelli, Michelangelo, da Vinci</li>
</ul>
</div>',
        UpdatedAt = GETUTCDATE()
WHEN NOT MATCHED THEN
    INSERT (ProjectCode, ProjectName, Description, Theme, Status, GoalStatement, TechStack, ProductionURL, VSCodePath, GitHubURL, PriorityNextSteps, ContentHTML)
    VALUES ('AF', 'ArtForge - Art Creation System', 
            'An RLHF-driven art discovery engine that generates images across 53 artistic styles.',
            'Creation', 'ACTIVE',
            'Create better art by developing new methods: AI tools, video/3D, repeatable processes',
            'Python/FastAPI, DALL-E 3, SQL Server, GCP Cloud Run',
            'https://artforge.rentyourcio.com/',
            'G:\My Drive\Code\Python\artforge',
            'https://github.com/coreyprator/artforge',
            '1. Deploy ArtForge to production and test RLHF ranking system',
            N'<div class="project-content"><p>Art creation system content...</p></div>');
GO

-- A2: Video Portfolio 2026
MERGE Projects AS target
USING (SELECT 'VIDEO' AS ProjectCode) AS source
ON target.ProjectCode = source.ProjectCode
WHEN MATCHED THEN
    UPDATE SET 
        ProjectName = 'Video Portfolio 2026',
        Description = 'Develop storytelling skills through 5-minute narrative videos. Shared workflow: Script → Voiceover → Scene creation → Adobe Premiere edit.',
        Theme = 'Creation',
        Status = 'ACTIVE',
        GoalStatement = 'Develop storytelling skills through 5-minute narrative videos',
        TechStack = 'Adobe Premiere, GoPro Max 360, AI scene generation',
        PriorityNextSteps = '1. Complete MacBook Air video script with multi-perspective interviews
2. Extract and transcribe Lois GoPro 360 footage
3. Complete AI summarization of Prator family materials',
        ContentHTML = N'<div class="project-content">
<h2>Video Projects</h2>

<h3>Video 1: Recovering Gladys'' MacBook Air</h3>
<p><strong>Status:</strong> In Progress</p>
<p>Story about how Gladys''s laptop was stolen in Paraguay and recovered days later. The story was sent to 400 family members and friends; over 100 replied praising its storytelling.</p>
<p><strong>Goal:</strong> Create a short (5 minute) real-life video story about the recovery.</p>

<h3>Video 2: Lois''s Story</h3>
<p><strong>Status:</strong> Not Started</p>
<p>Family history project from Mother''s Day 2022. Watched old family videos with Lois (mom) and recorded her stories using GoPro Max 360 camera.</p>
<p><strong>Goal:</strong> A highlight reel about 5 minutes long summarizing key moments.</p>

<h3>Video 3: Prator Family Life Story (40+ years)</h3>
<p><strong>Status:</strong> In Progress — 50% complete as of Dec 2024</p>
<p>Since 1980, I''ve written letters, created websites, and recorded videos for family and friends. Using AI (ChatGPT) to collect and summarize these materials.</p>

<h3>Video 4: Chicks in the Maid''s Quarters</h3>
<p><strong>Status:</strong> Not Started</p>
<p>Humorous story about Gladys buying chicks at Ipanema market and dressing them in doll clothes for photos.</p>

<h3>Video 5: 2D to 3D Perspective Abstract Art</h3>
<p><strong>Status:</strong> Not Started</p>
<p>How-to video explaining steps and lessons learned. Use reference art to go from still to video with 3D depth.</p>

<h3>Video 6: Honeymoon in Paraguay — An Extortion Story</h3>
<p><strong>Status:</strong> Blocked — Gladys uncertain about making public</p>
<p>Important for family history. Create as family-only piece first.</p>
</div>',
        UpdatedAt = GETUTCDATE()
WHEN NOT MATCHED THEN
    INSERT (ProjectCode, ProjectName, Description, Theme, Status, GoalStatement, TechStack, PriorityNextSteps, ContentHTML)
    VALUES ('VIDEO', 'Video Portfolio 2026', 
            'Develop storytelling skills through 5-minute narrative videos.',
            'Creation', 'ACTIVE',
            'Develop storytelling skills through 5-minute narrative videos',
            'Adobe Premiere, GoPro Max 360, AI scene generation',
            '1. Complete MacBook Air video script',
            N'<div class="project-content"><p>Video portfolio content...</p></div>');
GO

-- ============================================
-- Theme B: Learning & Growth
-- ============================================

-- B1a: French Language Learning (Super-Flashcards)
MERGE Projects AS target
USING (SELECT 'SF' AS ProjectCode) AS source
ON target.ProjectCode = source.ProjectCode
WHEN MATCHED THEN
    UPDATE SET 
        ProjectName = 'Super-Flashcards',
        Description = 'AI-powered vocabulary learning with GPT-4 generated content and DALL-E 3 images for French language learning.',
        Theme = 'Learning',
        Status = 'ACTIVE',
        GoalStatement = 'Master French vocabulary through AI-enhanced flashcard learning',
        TechStack = 'Python/FastAPI, GPT-4, DALL-E 3, SQL Server, GCP Cloud Run',
        VSCodePath = 'G:\My Drive\Code\Python\super-flashcards',
        GitHubURL = 'https://github.com/coreyprator/super-flashcards',
        PriorityNextSteps = '1. Complete batch processing for new French vocabulary
2. Plan extended stay in France (April–September window)
3. Book Paris extended-stay visa appointment',
        ContentHTML = N'<div class="project-content">
<h2>French Language Learning</h2>
<p>Successfully batch-processed 253 French words with 100% success rate.</p>

<h3>Action Items</h3>
<ul>
<li>Continue daily practice with Super-Flashcards app</li>
<li>Plan extended stay in France (April–September window)</li>
<li>Book Paris extended-stay visa appointment</li>
</ul>

<h2>Technical Achievement</h2>
<p>AI-powered vocabulary learning with GPT-4 generated content and DALL-E 3 images. Costs approximately $0.05 per flashcard.</p>
</div>',
        UpdatedAt = GETUTCDATE()
WHEN NOT MATCHED THEN
    INSERT (ProjectCode, ProjectName, Description, Theme, Status, GoalStatement, TechStack, VSCodePath, GitHubURL, PriorityNextSteps, ContentHTML)
    VALUES ('SF', 'Super-Flashcards', 
            'AI-powered vocabulary learning with GPT-4 generated content.',
            'Learning', 'ACTIVE',
            'Master French vocabulary through AI-enhanced flashcard learning',
            'Python/FastAPI, GPT-4, DALL-E 3, SQL Server, GCP Cloud Run',
            'G:\My Drive\Code\Python\super-flashcards',
            'https://github.com/coreyprator/super-flashcards',
            '1. Complete batch processing for new French vocabulary',
            N'<div class="project-content"><p>Super-Flashcards content...</p></div>');
GO

-- B1b: Greek Language Learning (Etymython)
MERGE Projects AS target
USING (SELECT 'EM' AS ProjectCode) AS source
ON target.ProjectCode = source.ProjectCode
WHEN MATCHED THEN
    UPDATE SET 
        ProjectName = 'Etymython',
        Description = 'An interactive knowledge exploration system tracing modern English vocabulary back to Greek mythology. Transforms Wikipedia-style walls of text into explorable visual graphs.',
        Theme = 'Learning',
        Status = 'ACTIVE',
        GoalStatement = 'Focus on etymology and important words to strengthen English and Romance languages. Learn basic Greek expressions.',
        TechStack = 'Python/FastAPI, SQL Server, GCP Cloud Run, DALL-E 3, Google TTS',
        ProductionURL = 'https://etymython.rentyourcio.com/app',
        VSCodePath = 'G:\My Drive\Code\Python\etymython',
        GitHubURL = 'https://github.com/coreyprator/etymython',
        PriorityNextSteps = '1. Fill remaining 37 etymology gaps in Etymython
2. Fix Tyche fun facts (currently 0)
3. Add AI Content Editor with approval workflow',
        ContentHTML = N'<div class="project-content">
<h2>Current State</h2>
<p>56 mythological figures with Renaissance-style AI images, Greek pronunciation audio, origin stories, and fun facts.</p>

<h2>Sprint 6 Focus</h2>
<ul>
<li>Fill 37 etymology gaps (Zeus, Apollo, Athena, Poseidon, Hades, Hera, Ares, Artemis, Hephaestus, Dionysus, Demeter, Hestia, Persephone, Cronus, Rhea, and more)</li>
<li>Fix Tyche fun facts (currently 0)</li>
<li>Add AI Content Editor: natural language commands, backend endpoint, approval workflow, frontend admin panel</li>
</ul>

<h2>Greek Learning with Theodoros</h2>
<p>Continue 3X per week class. 2026 Topics:</p>
<ul>
<li>Practical expressions</li>
<li>Geography with ancient Greek text</li>
<li>Jazz Modes (Ionian, Dorian, Phrygian, Lydian, Mixolydian, Aeolian, Locrian)</li>
<li>History, Alexander the Great, Homer, Tragic Poets, Sappho</li>
</ul>
</div>',
        UpdatedAt = GETUTCDATE()
WHEN NOT MATCHED THEN
    INSERT (ProjectCode, ProjectName, Description, Theme, Status, GoalStatement, TechStack, ProductionURL, VSCodePath, GitHubURL, PriorityNextSteps, ContentHTML)
    VALUES ('EM', 'Etymython', 
            'Interactive knowledge exploration system for Greek mythology and etymology.',
            'Learning', 'ACTIVE',
            'Focus on etymology and important words to strengthen English and Romance languages.',
            'Python/FastAPI, SQL Server, GCP Cloud Run, DALL-E 3, Google TTS',
            'https://etymython.rentyourcio.com/app',
            'G:\My Drive\Code\Python\etymython',
            'https://github.com/coreyprator/etymython',
            '1. Fill remaining 37 etymology gaps',
            N'<div class="project-content"><p>Etymython content...</p></div>');
GO

-- B2: Jazz Piano Development (HarmonyLab)
MERGE Projects AS target
USING (SELECT 'HL' AS ProjectCode) AS source
ON target.ProjectCode = source.ProjectCode
WHEN MATCHED THEN
    UPDATE SET 
        ProjectName = 'HarmonyLab',
        Description = 'A harmonic progression training system for jazz standards. Transforms memorizing 30+ songs'' chord progressions into quiz-based learning.',
        Theme = 'Learning',
        Status = 'ACTIVE',
        GoalStatement = 'Play jazz standards from memory without lead sheets',
        TechStack = 'Python/FastAPI, SQL Server, Tone.js, GCP Cloud Run',
        VSCodePath = 'G:\My Drive\Code\Python\harmonylab',
        GitHubURL = 'https://github.com/coreyprator/harmonylab',
        PriorityNextSteps = '1. Complete HarmonyLab Sprint 1 and import first 5 songs
2. Continue weekly sessions with Darren Kramer
3. Practice ii-V-I progressions in all 12 keys',
        ContentHTML = N'<div class="project-content">
<h2>Vision</h2>
<p>Started journey in 2007 (17+ years ago). Committed to continue for rest of life. Even small improvements add up.</p>

<h2>2026 Goals</h2>
<ul>
<li>Strengthen improv skills — play riffs and licks on pieces I know well</li>
<li>Play by ear better</li>
<li>Remember tunes by heart — depend less on lead sheets for favorite tunes</li>
<li>Read both treble and bass clef at tempo</li>
<li>Develop interval ear training to hear chords and build them at tempo</li>
<li>Compose more complex pieces using MuseScore and Ableton</li>
<li>Create richer sound beyond ii-V-I Standard Voicing (Alt chords, 4th voicing, open voicing)</li>
</ul>

<h2>Key Features (Planned)</h2>
<ul>
<li>Hierarchical data model: Song → Section → Measure → Chord</li>
<li>Quiz modes: Fill-in-Blank and Sequential</li>
<li>Tone.js audio playback with visual sync</li>
<li>MIDI/MusicXML import from MuseScore</li>
<li>Progress tracking by song and mastery level</li>
</ul>

<h2>Measurement</h2>
<p>Perform in public.</p>
</div>',
        UpdatedAt = GETUTCDATE()
WHEN NOT MATCHED THEN
    INSERT (ProjectCode, ProjectName, Description, Theme, Status, GoalStatement, TechStack, VSCodePath, GitHubURL, PriorityNextSteps, ContentHTML)
    VALUES ('HL', 'HarmonyLab', 
            'Harmonic progression training system for jazz standards.',
            'Learning', 'ACTIVE',
            'Play jazz standards from memory without lead sheets',
            'Python/FastAPI, SQL Server, Tone.js, GCP Cloud Run',
            'G:\My Drive\Code\Python\harmonylab',
            'https://github.com/coreyprator/harmonylab',
            '1. Complete HarmonyLab Sprint 1',
            N'<div class="project-content"><p>HarmonyLab content...</p></div>');
GO

-- ============================================
-- Theme C: Adventure & Exploration
-- ============================================

-- C1: Western US Adventures
MERGE Projects AS target
USING (SELECT 'ADVENTURE-US' AS ProjectCode) AS source
ON target.ProjectCode = source.ProjectCode
WHEN MATCHED THEN
    UPDATE SET 
        UpdatedAt = GETUTCDATE()
WHEN NOT MATCHED THEN
    INSERT (ProjectCode, ProjectName, Description, Theme, Status, GoalStatement, PriorityNextSteps, ContentHTML)
    VALUES ('ADVENTURE-US', 'Western US Adventures', 
            'Travel adventures including Route 89 Road Trip, Colorado River documentary, Grand Canyon Raft Trip, and Alcan Highway.',
            'Adventure', 'ACTIVE',
            'Document iconic American landscapes through video and photography',
            '1. Coordinate Route 89 Spokane leg with Manish
2. Find DIPster travel partner for remaining segments
3. Book Grand Canyon raft trip by June 2026',
            N'<div class="project-content">
<h2>Route 89 Road Trip</h2>
<p><strong>Status:</strong> In Progress</p>
<p>Follow Route 89 from Canada to Mexico. Passes through Sedona, Flagstaff, Grand Canyon.</p>
<p><strong>Goal:</strong> 1-hour 4K video of the entire route.</p>

<h2>Colorado River</h2>
<p><strong>Status:</strong> Blocked — No travel partner</p>
<p>Document Colorado River from source (Rocky Mountain National Park) to Sea of Cortez in Mexico.</p>

<h2>Grand Canyon Raft Trip</h2>
<p><strong>Status:</strong> Blocked — Kids'' scheduling</p>
<p>Want to do it with kids. Fallback: If not booked by June 2026, go with DIPsters instead.</p>

<h2>Alcan Highway Trip</h2>
<p><strong>Status:</strong> Blocked — No travel partner</p>
<p>Drive from US-Canadian border to Anchorage, Alaska. At least 40 hours of driving.</p>
</div>');
GO

-- C2: International Travel
MERGE Projects AS target
USING (SELECT 'ADVENTURE-INTL' AS ProjectCode) AS source
ON target.ProjectCode = source.ProjectCode
WHEN MATCHED THEN
    UPDATE SET 
        UpdatedAt = GETUTCDATE()
WHEN NOT MATCHED THEN
    INSERT (ProjectCode, ProjectName, Description, Theme, Status, GoalStatement, ContentHTML)
    VALUES ('ADVENTURE-INTL', 'International Travel', 
            'International adventures including African Safari, Patagonia Flyfishing, Greek Isles, and Alaska Inner Passage.',
            'Adventure', 'PLANNED',
            'Experience transformative international adventures',
            N'<div class="project-content">
<h2>Planned Trips</h2>
<table>
<tr><th>Trip</th><th>Description</th><th>Status</th></tr>
<tr><td>African Safari</td><td>Wildlife photography expedition</td><td>Not Started</td></tr>
<tr><td>Patagonia Flyfishing</td><td>Argentina — remote fishing adventure</td><td>Not Started</td></tr>
<tr><td>Greek Isles</td><td>Synergizes with Greek language learning</td><td>Not Started</td></tr>
<tr><td>Alaska Inner Passage</td><td>Vancouver to Alaska cruise/expedition</td><td>Not Started</td></tr>
</table>

<h2>Extended European Living</h2>
<p><strong>Goal:</strong> Extended stays (3-6 months) in Paris, Vienna, or Greece</p>
<ul>
<li>Research extended-stay visa requirements for France</li>
<li>Reach out to Paris Hiking Club contacts</li>
<li>Block April-September 2026 on calendar</li>
</ul>
</div>');
GO

-- ============================================
-- Theme D: Relationships & Community
-- ============================================

-- D1: DIPster Engagement
MERGE Projects AS target
USING (SELECT 'DIPSTER' AS ProjectCode) AS source
ON target.ProjectCode = source.ProjectCode
WHEN MATCHED THEN
    UPDATE SET 
        UpdatedAt = GETUTCDATE()
WHEN NOT MATCHED THEN
    INSERT (ProjectCode, ProjectName, Description, Theme, Status, GoalStatement, PriorityNextSteps, ContentHTML)
    VALUES ('DIPSTER', 'DIPster Engagement', 
            'Maintain personal relationships — reach out to friends and DIPsters throughout the year.',
            'Relationships', 'ACTIVE',
            'Maintain close relationships through active outreach (1 contact/week)',
            '1. Contact 1 DIPster per week from master list
2. Research Houston-area clubs/activities for Q1
3. Plan one small dinner event in Q1',
            N'<div class="project-content">
<h2>What is a DIPster?</h2>
<p>A DIPster (Damn Interesting Person) is someone admired for their ability to ''squeeze the juice out of life'' through lifestyle, interests, hobbies, and experiences. Typically adventuresome, social, curious, and engaging.</p>

<h2>2025 Learning</h2>
<p>Virtual salons had limited success. Best DIPster concentration found in shared activities (e.g., scuba diving).</p>

<h2>2026 Strategy</h2>
<ul>
<li>Maintain close relationships through active outreach (1 contact/week)</li>
<li>Find activity-based groups for new DIPster discovery</li>
<li>Small dinner parties (4-6 people) over large events</li>
</ul>

<h2>Action Items</h2>
<ul>
<li>Contact at least 1 old DIPster friend per week from DIPsters 2.0 list</li>
<li>Find a new organization, club, or activity that Gladys and I can participate in</li>
<li>Plan small (4-6 people) dinner events</li>
</ul>
</div>');
GO

-- ============================================
-- Meta: Cross-Cutting Tools
-- ============================================

-- MetaPM (this project!)
MERGE Projects AS target
USING (SELECT 'META' AS ProjectCode) AS source
ON target.ProjectCode = source.ProjectCode
WHEN MATCHED THEN
    UPDATE SET 
        ProjectName = 'MetaPM',
        Description = 'Centralized task manager for 21+ personal projects with voice capture, AI processing, and methodology tracking.',
        Theme = 'Meta',
        Status = 'ACTIVE',
        GoalStatement = 'Single place to find and track all personal projects, prioritize them, and serve as a tickler for next steps',
        TechStack = 'Python/FastAPI, MS SQL Server, GCP Cloud Run, OpenAI Whisper, Claude',
        ProductionURL = 'https://metapm.rentyourcio.com/',
        VSCodePath = 'G:\My Drive\Code\Python\metapm',
        GitHubURL = 'https://github.com/coreyprator/metapm',
        PriorityNextSteps = '1. Complete rich text content for all projects
2. Implement project CRUD in dashboard
3. Load methodology rules from lessons learned',
        ContentHTML = N'<div class="project-content">
<h2>Purpose</h2>
<p>This is the master project management system — the tool that manages all other projects.</p>
<p>From the 2026 Personal Projects Plan: "Consider refactoring this into a tool that navigates among: This Document, VS Code, AI chat links, Status/Task Management tool"</p>

<h2>Key Features</h2>
<ul>
<li>Voice capture with Whisper transcription and Claude understanding</li>
<li>Task CRUD with project and category linking</li>
<li>Methodology rules and violation tracking</li>
<li>Transaction history with AI cost analytics</li>
<li>Dashboard with VS Code, GitHub, and AI Chat quick links</li>
</ul>

<h2>Project Methodology v3.12.1</h2>
<p>Incorporates lessons learned including "RTFM First", "External Verification", "Data is cheap, API calls are expensive".</p>
</div>',
        UpdatedAt = GETUTCDATE()
WHEN NOT MATCHED THEN
    INSERT (ProjectCode, ProjectName, Description, Theme, Status, GoalStatement, TechStack, ProductionURL, VSCodePath, GitHubURL, ContentHTML)
    VALUES ('META', 'MetaPM', 
            'Centralized task manager for 21+ personal projects.',
            'Meta', 'ACTIVE',
            'Single place to find and track all personal projects',
            'Python/FastAPI, MS SQL Server, GCP Cloud Run, OpenAI Whisper, Claude',
            'https://metapm.rentyourcio.com/',
            'G:\My Drive\Code\Python\metapm',
            'https://github.com/coreyprator/metapm',
            N'<div class="project-content"><p>MetaPM content...</p></div>');
GO

-- PromptForge
MERGE Projects AS target
USING (SELECT 'PROMPTFORGE' AS ProjectCode) AS source
ON target.ProjectCode = source.ProjectCode
WHEN MATCHED THEN
    UPDATE SET 
        Theme = 'Meta',
        Status = 'ACTIVE',
        TechStack = 'Python/FastAPI, SQL Server, GCP Cloud Run',
        VSCodePath = 'G:\My Drive\Code\Python\promptforge',
        GitHubURL = 'https://github.com/coreyprator/promptforge',
        UpdatedAt = GETUTCDATE()
WHEN NOT MATCHED THEN
    INSERT (ProjectCode, ProjectName, Description, Theme, Status, TechStack, VSCodePath, GitHubURL)
    VALUES ('PROMPTFORGE', 'PromptForge', 
            'AI prompt development and management system with integrated bridge architecture.',
            'Meta', 'ACTIVE',
            'Python/FastAPI, SQL Server, GCP Cloud Run',
            'G:\My Drive\Code\Python\promptforge',
            'https://github.com/coreyprator/promptforge');
GO

-- Cubist
MERGE Projects AS target
USING (SELECT 'CUBIST' AS ProjectCode) AS source
ON target.ProjectCode = source.ProjectCode
WHEN MATCHED THEN
    UPDATE SET 
        Theme = 'Creation',
        Description = 'SVG artwork generation from input images using geometric algorithms like Delaunay triangulation, Voronoi diagrams, and Poisson disk sampling.',
        TechStack = 'Python, SVG, Geometric algorithms',
        VSCodePath = 'G:\My Drive\Code\Python\cubist',
        GitHubURL = 'https://github.com/coreyprator/cubist',
        UpdatedAt = GETUTCDATE()
WHEN NOT MATCHED THEN
    INSERT (ProjectCode, ProjectName, Description, Theme, Status, TechStack, VSCodePath, GitHubURL)
    VALUES ('CUBIST', 'Cubist Art Generator', 
            'SVG artwork generation using geometric algorithms.',
            'Creation', 'ACTIVE',
            'Python, SVG, Geometric algorithms',
            'G:\My Drive\Code\Python\cubist',
            'https://github.com/coreyprator/cubist');
GO

-- ============================================
-- Verify Results
-- ============================================

SELECT 
    ProjectCode,
    ProjectName,
    Theme,
    Status,
    CASE WHEN ContentHTML IS NOT NULL THEN 'Yes' ELSE 'No' END AS HasContent,
    CASE WHEN ProductionURL IS NOT NULL THEN ProductionURL ELSE '-' END AS URL
FROM Projects
ORDER BY Theme, ProjectCode;
GO

PRINT '';
PRINT '=== PROJECT CONTENT POPULATION COMPLETE ===';
GO
