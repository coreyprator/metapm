# MetaPM Enhancements Bundle
## Project CRUD, Rich Text Content, and Methodology Rules

This bundle adds three major enhancements:

1. **Full Project CRUD** - Create, read, update, delete projects
2. **Rich Text Content** - HTML content field for detailed project documentation
3. **Methodology Rules** - 21 lessons learned pre-populated

---

## Contents

```
metapm-enhancements/
├── scripts/
│   ├── 01_schema_updates.sql      # Add new columns to Projects table
│   ├── 02_populate_projects.sql   # Populate projects from 2026 Plan
│   └── 03_populate_methodology.sql # Insert 21 methodology rules
├── app/
│   └── api/
│       └── projects.py            # Enhanced Projects API with CRUD
└── static/
    └── project-modal.html         # Project edit modal component
```

---

## Installation

### Step 1: Run Schema Updates (SSMS) - IN ORDER

```sql
-- Run each script in SSMS, in order:
-- 1. 01_schema_updates.sql
-- 2. 02_populate_projects.sql  
-- 3. 03_populate_methodology.sql
```

### Step 2: Update API

Replace `app/api/projects.py` with the enhanced version from this bundle.

### Step 3: Integrate Project Modal

The project-modal.html contains the modal HTML and JavaScript. You can either:

**Option A: Merge into dashboard.html**
- Copy the modal HTML into dashboard.html (after other modals)
- Copy the script section into the existing script block
- Add CSS to existing style block

**Option B: Keep separate and include**
```html
<!-- At end of dashboard.html body, before closing </body> -->
<script>
// Load project modal component
fetch('/static/project-modal.html')
    .then(r => r.text())
    .then(html => {
        document.body.insertAdjacentHTML('beforeend', html);
    });
</script>
```

### Step 4: Add Project Create Button

In the Projects tab section of dashboard.html, add:

```html
<button onclick="openProjectModal()" class="w-full glass-card rounded-xl p-3 text-left flex items-center gap-3 hover:bg-white/10 transition">
    <svg class="w-5 h-5 text-pink-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
    </svg>
    <span class="text-gray-400">Add new project...</span>
</button>
```

### Step 5: Update Project Card Click Handler

Change the project card onclick from toggle to open modal:

```javascript
// Change this:
onclick="toggleProjectTasks('${p.projectCode}')"

// To this:
onclick="openProjectModal('${p.projectCode}')"
```

---

## What Gets Populated

### Projects (from 2026 Personal Projects Plan)

| Code | Name | Theme |
|------|------|-------|
| AF | ArtForge - Art Creation System | Creation |
| VIDEO | Video Portfolio 2026 | Creation |
| SF | Super-Flashcards | Learning |
| EM | Etymython | Learning |
| HL | HarmonyLab | Learning |
| ADVENTURE-US | Western US Adventures | Adventure |
| ADVENTURE-INTL | International Travel | Adventure |
| DIPSTER | DIPster Engagement | Relationships |
| META | MetaPM | Meta |
| PROMPTFORGE | PromptForge | Meta |
| CUBIST | Cubist Art Generator | Creation |

### Methodology Rules (21 Rules)

| Category | Count |
|----------|-------|
| DEVELOPMENT | 8 |
| TESTING | 3 |
| DEPLOYMENT | 3 |
| DOCUMENTATION | 3 |
| PROCESS | 4 |

**Key Rules:**
- LL-001: RTFM First
- LL-002: External Verification (CRITICAL)
- LL-003: Data is Cheap, API Calls are Expensive
- LL-005: SET NOCOUNT ON
- LL-006: Direct IP for SQL Server on GCP
- LL-012: Secrets in Secret Manager (CRITICAL)

---

## New API Endpoints

### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/projects | List all projects |
| GET | /api/projects/{code} | Get project with full details |
| GET | /api/projects/{code}/tasks | Get tasks for project |
| POST | /api/projects | Create new project |
| PUT | /api/projects/{code} | Update project |
| PUT | /api/projects/{code}/content | Update HTML content only |
| PUT | /api/projects/{code}/ai-thread | Update AI thread URL only |
| DELETE | /api/projects/{code} | Soft delete project |

### Project Fields

```json
{
  "projectCode": "META",
  "projectName": "MetaPM",
  "description": "Centralized task manager...",
  "theme": "Meta",
  "status": "ACTIVE",
  "goalStatement": "Single place to find and track...",
  "techStack": "Python/FastAPI, SQL Server, GCP",
  "productionURL": "https://metapm.rentyourcio.com/",
  "vsCodePath": "G:\\My Drive\\Code\\Python\\metapm",
  "gitHubURL": "https://github.com/coreyprator/metapm",
  "currentAIThreadURL": "https://claude.ai/chat/...",
  "priorityNextSteps": "1. Complete...\n2. Implement...",
  "contentHTML": "<div>Rich HTML content...</div>"
}
```

---

## Rich Text Content Format

The `contentHTML` field supports standard HTML:

```html
<div class="project-content">
  <h2>Section Title</h2>
  <p>Paragraph text with <strong>bold</strong> and <em>italic</em>.</p>
  
  <h3>Subsection</h3>
  <ul>
    <li>Bullet point 1</li>
    <li>Bullet point 2</li>
  </ul>
  
  <table>
    <tr><th>Column 1</th><th>Column 2</th></tr>
    <tr><td>Data 1</td><td>Data 2</td></tr>
  </table>
</div>
```

The dashboard includes CSS for rendering this content with proper dark theme styling.

---

## Testing

After running the SQL scripts:

```sql
-- Verify projects
SELECT ProjectCode, ProjectName, Theme, 
       CASE WHEN ContentHTML IS NOT NULL THEN 'Yes' ELSE 'No' END AS HasContent
FROM Projects WHERE Status != 'DELETED';

-- Verify methodology rules
SELECT RuleCode, RuleName, Category, Severity
FROM MethodologyRules WHERE IsActive = 1
ORDER BY RuleCode;

-- Count by category
SELECT Category, COUNT(*) as RuleCount
FROM MethodologyRules WHERE IsActive = 1
GROUP BY Category;
```

---

## Notes

- **ContentHTML is NVARCHAR(MAX)** - Can store very large HTML documents
- **Soft delete** - Projects aren't physically deleted, just marked as DELETED
- **Theme dropdown** - Currently hardcoded: Creation, Learning, Adventure, Relationships, Meta
- **AI Thread URL** - Quick access to ongoing Claude/ChatGPT conversations about the project
