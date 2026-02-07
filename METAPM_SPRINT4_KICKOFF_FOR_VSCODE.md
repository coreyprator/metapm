# MetaPM Sprint 4 - VS Code Kickoff

**Date**: January 30, 2026  
**Sprint Duration**: 6.5-8.5 days estimated  
**Current Production**: metapm-v2 on Cloud Run

---

## STEP 1: READ DOCS FIRST (Required)

Before writing ANY code, you MUST:

1. **Read CLAUDE.md** in project root - contains infrastructure details
2. **Read this kickoff document** completely
3. **Confirm understanding** by stating the key values below

### Confirm These Values (From CLAUDE.md)
After reading, state:
```
I have read CLAUDE.md and this kickoff. Key infrastructure:
- GCP Project: super-flashcards-475210
- Cloud Run Service: metapm-v2
- Cloud SQL Instance: flashcards-db
- Region: us-central1
- Database: MetaPM
```

**Do NOT proceed until you have confirmed these values.**

---

## INFRASTRUCTURE REFERENCE

| Resource | EXACT Value |
|----------|-------------|
| GCP Project | `super-flashcards-475210` |
| Cloud Run Service | `metapm-v2` |
| Region | `us-central1` |
| Cloud SQL Instance | `flashcards-db` |
| Cloud SQL Connection | `super-flashcards-475210:us-central1:flashcards-db` |
| Database | `MetaPM` |
| Custom Domain | `https://metapm.rentyourcio.com` |

### Deploy Command (Copy-Paste Ready)
```powershell
gcloud run deploy metapm-v2 `
  --source . `
  --region us-central1 `
  --allow-unauthenticated `
  --set-env-vars="DB_SERVER=/cloudsql/super-flashcards-475210:us-central1:flashcards-db,DB_NAME=MetaPM,DB_USER=sqlserver,ENVIRONMENT=production" `
  --set-secrets="DB_PASSWORD=db-password:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest" `
  --add-cloudsql-instances="super-flashcards-475210:us-central1:flashcards-db"
```

### ❌ NEVER USE (Deprecated/Wrong)
- `metapm` (old service - deleted)
- `coreyscloud` (doesn't exist)
- Project `metapm` (wrong project)

---

## VOCABULARY LOCKDOWN

**You may NOT use these words without proof:**

| Forbidden Word | Unlock Requirement |
|----------------|-------------------|
| "Complete" | Deployed revision name + test output |
| "Done" | Deployed revision name + test output |
| "Finished" | Deployed revision name + test output |
| "Ready for review" | Deployed revision name + test output |
| ✅ emoji | Deployed revision name + test output |

### Correct Handoff Format
```markdown
## Handoff: [Feature Name]

**Deployed**: metapm-v2-00015-xyz
**Version**: v1.5.0

**Tests Run**:
```
pytest tests/test_sprint4_feature1.py -v
test_color_picker_opens PASSED
test_color_syncs PASSED
test_color_persists PASSED
3 passed in 2.1s
```

**Ready for review**: Yes (all tests pass)
```

### If Not Yet Tested
Say: "Code written. Pending deployment and testing."  
**NOT**: "Feature complete!" or "✅ Done"

---

## SPRINT 4 FEATURES

### Feature 1: Playwright Test Coverage (2 days)
Create automated tests for Sprint 3 features.

**File**: `tests/test_sprint3_features.py`

**Required Tests**:
| ID | Test | What to Verify |
|----|------|----------------|
| PW-001 | test_page_loads_no_console_errors | No JS errors on load |
| PW-002 | test_project_color_picker_opens | Color modal appears |
| PW-003 | test_color_syncs_to_hex | Picker and input match |
| PW-004 | test_color_persists_after_save | Reload shows same color |
| PW-005 | test_task_sort_changes_order | List reorders on sort |
| PW-006 | test_sort_direction_toggles | Asc/desc switch works |
| PW-007 | test_theme_toggle_works | Dark/light switches |
| PW-008 | test_mobile_viewport | Page works at 375x667 |

**Definition of Done**:
- [ ] 8+ tests in test file
- [ ] All tests pass against https://metapm.rentyourcio.com
- [ ] Test output provided in handoff

---

### Feature 2: Theme Management UI (1.5 days)
Admin CRUD for Project Themes (Creation, Learning, Adventure, Relationships, Meta).

**Note**: This is NOT the dark/light mode toggle (that's done). This is for managing the categorization themes that projects belong to.

**Current Themes in Database**:
| ThemeID | ThemeName | ThemeCode |
|---------|-----------|-----------|
| 1 | Creation | A |
| 2 | Learning | B |
| 3 | Adventure | C |
| 4 | Relationships | D |
| 5 | Meta | META |

**UI Requirements**:
- Add "Manage Themes" button (Projects tab or Methodology tab)
- Modal with theme list showing name, code, color
- Create new theme form
- Edit existing theme
- Delete theme (blocked if projects use it)

**API Endpoints (Already Exist)**:
```
GET    /api/themes        - List all
POST   /api/themes        - Create
PUT    /api/themes/{id}   - Update
DELETE /api/themes/{id}   - Delete
```

**Test Cases**:
| ID | Test | Expected |
|----|------|----------|
| TH-001 | test_theme_list_loads | Shows 5 themes |
| TH-002 | test_create_theme | New theme appears |
| TH-003 | test_edit_theme | Changes persist |
| TH-004 | test_delete_unused_theme | Theme removed |
| TH-005 | test_delete_blocked_if_in_use | Error shown |

**Definition of Done**:
- [ ] Theme management UI accessible
- [ ] CRUD operations work
- [ ] Playwright tests pass
- [ ] No console errors

---

### Feature 3: Violation AI Assistant (3-5 days)
AI-powered analysis of methodology violations.

**Workflow**:
1. PL encounters VS Code violation
2. Opens Methodology → Violations → "Log Violation"
3. Describes incident or pastes VS Code chat
4. Clicks "Analyze"
5. AI identifies violated rules with confidence
6. AI generates corrective prompt
7. PL copies prompt to clipboard
8. Violation saved to database

**New API Endpoint**:
```python
POST /api/methodology/violations/analyze

Request:
{
    "incident": "VS Code said 'complete' without running tests",
    "projectCode": "META"  # optional
}

Response:
{
    "identifiedRules": [
        {"code": "LL-030", "name": "Developer Tests Before Handoff", "confidence": 0.95},
        {"code": "LL-049", "name": "Complete Requires Test Proof", "confidence": 0.90}
    ],
    "suggestedCategory": "TESTING",
    "generatedPrompt": "METHODOLOGY VIOLATION DETECTED\n\nVS Code, you violated..."
}
```

**Database Changes**:
```sql
ALTER TABLE MethodologyViolations ADD
    PLComments NVARCHAR(MAX),
    AIAnalysisJSON NVARCHAR(MAX),
    GeneratedPrompt NVARCHAR(MAX);
```

**Secret Access**:
The `anthropic-api-key` is available via:
```python
import os
api_key = os.environ.get("ANTHROPIC_API_KEY")
```

**Test Cases**:
| ID | Test | Expected |
|----|------|----------|
| VA-001 | test_analyze_endpoint_responds | 200 OK |
| VA-002 | test_identifies_testing_violation | LL-030 in results |
| VA-003 | test_generates_prompt | Non-empty prompt |
| VA-004 | test_save_violation | Record in DB |
| VA-005 | test_copy_button | Clipboard works |

**Definition of Done**:
- [ ] /api/methodology/violations/analyze works
- [ ] UI shows identified rules
- [ ] Copy-to-clipboard works
- [ ] Playwright tests pass

---

## TASK SEQUENCE

Complete features in order:

```
Feature 1: Playwright Tests
    ↓ (must pass before Feature 2)
Feature 2: Theme Management UI  
    ↓ (must pass before Feature 3)
Feature 3: Violation AI Assistant
    ↓
Sprint 4 Complete
```

---

## BEFORE STARTING

Run these verification commands:

```powershell
# Verify GCP project
gcloud config get-value project
# Must return: super-flashcards-475210

# Verify service exists
gcloud run services describe metapm-v2 --region us-central1 --format="value(status.url)"
# Must return the Cloud Run URL

# Verify health
curl https://metapm.rentyourcio.com/health
```

---

## START NOW

1. Confirm you read CLAUDE.md and this kickoff
2. State the infrastructure values
3. Begin Feature 1: Create `tests/test_sprint3_features.py`
4. Run tests against production URL
5. Provide handoff with test output

**Go!**
