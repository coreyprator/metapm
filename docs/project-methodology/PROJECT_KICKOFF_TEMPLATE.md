# Project Kickoff Template v3.12

## Document Variables

Replace these placeholders throughout this document:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{PROJECT_NAME}}` | Human-readable project name | ArtForge |
| `{{PROJECT_SLUG}}` | Lowercase, hyphenated | artforge |
| `{{GCP_PROJECT_ID}}` | GCP project identifier | super-flashcards-475210 |
| `{{GITHUB_REPO}}` | Repository URL | coreyprator/artforge |
| `{{SQL_INSTANCE}}` | Cloud SQL instance name | flashcards-db |
| `{{SQL_INSTANCE_IP}}` | Instance IP address | 34.xxx.xxx.xxx |
| `{{DATABASE_NAME}}` | Database name | artforge |
| `{{GCS_BUCKET}}` | Storage bucket name | artforge-images |
| `{{CUSTOM_DOMAIN}}` | Optional custom domain | artforge.example.com |

---

## Phase 0: Pre-Kickoff Setup

### 0.1 Authentication Flow (MUST follow this order)

```powershell
# ============================================
# PASSKEY AUTHENTICATION SEQUENCE
# Project Lead runs this ONCE at session start
# ============================================

# Step 1: Browser authentication (opens browser, use Passkey)
gcloud auth login
# ✓ SUCCESS: Browser shows "You are now authenticated"
# ✗ FAILURE: Password prompt in terminal = wrong flow

# Step 2: Application default credentials (opens browser again)
gcloud auth application-default login
# ✓ SUCCESS: "Credentials saved to file"

# Step 3: Set project (should NOT prompt for anything)
gcloud config set project {{GCP_PROJECT_ID}}
# ✓ SUCCESS: "Updated property [core/project]"
# ✗ FAILURE: Password prompt = Step 1 failed, restart

# Step 4: Set quota project
gcloud auth application-default set-quota-project {{GCP_PROJECT_ID}}
# ✓ SUCCESS: "Credentials saved to file"

# Step 5: VERIFY before proceeding
gcloud config get-value project
# Must output: {{GCP_PROJECT_ID}}

gcloud auth list
# Must show your account with asterisk (ACTIVE)

# ============================================
# AFTER THIS POINT: VS Code AI runs all gcloud commands
# Project Lead does NOT run gcloud commands manually
# ============================================
```

> ⚠️ **CRITICAL**: If you see a password prompt at Step 3, STOP. Run `gcloud auth login` again. The Passkey flow should complete in browser without password entry.

### Session Start Script (Recommended)

GCloud tokens expire after ~1 hour of inactivity. Create a reusable script:

```powershell
# start-gcp-session.ps1 - Run at start of each work session
Write-Host "=== GCP SESSION START ===" -ForegroundColor Cyan
gcloud auth login
gcloud auth application-default login  
gcloud config set project {{GCP_PROJECT_ID}}
gcloud auth application-default set-quota-project {{GCP_PROJECT_ID}}
Write-Host "=== READY ===" -ForegroundColor Green
gcloud config get-value project
```

**Recommendation**: Save as TextExpander snippet or shell alias for quick access.

### When Re-Authentication is Needed

- Any gcloud command prompts for password
- Error: "Your credentials are invalid" or "Token has been expired or revoked"
- First command after ~1 hour idle
- After system restart

### AI Behavior When Blocked

If VS Code AI encounters a password prompt:
1. **STOP** immediately - do not attempt to enter credentials
2. **Tell Project Lead**: "GCP auth has expired. Please run session start script."
3. **Wait** for confirmation before proceeding
4. **Do NOT** work around it or attempt alternative authentication

| Task | Owner | AI Can Do? |
|------|-------|------------|
| Browser/Passkey auth | Human | ❌ NO |
| Run auth script | Human | ❌ NO |
| Detect auth needed | AI | ✅ YES (see password prompt) |
| Request re-auth | AI | ✅ YES (ask human) |

### 0.2 Verify Project Configuration

```powershell
# Confirm correct project
gcloud config get-value project
# Should output: {{GCP_PROJECT_ID}}

# Verify authentication
gcloud auth list
# Should show your account as active
```

### 0.3 SQL Execution Environment

| Tool | Use For | GO Statement Support |
|------|---------|---------------------|
| SSMS | Schema creation, complex scripts | ✅ Yes |
| sqlcmd | Batch execution from command line | ✅ Yes |
| Cloud SQL Studio | Quick queries, single statements | ❌ No |

> **Rule**: If your SQL script contains `GO` statements, use SSMS or sqlcmd, NOT Cloud SQL Studio.

### 0.4 Shell Environment: PowerShell

> **All command-line examples and scripts use PowerShell (pwsh), not bash.**

| Aspect | PowerShell (✅ Use This) | Bash (❌ Don't Use) |
|--------|--------------------------|---------------------|
| Shell | `powershell` or `pwsh` | `bash` or `sh` |
| File extension | `.ps1` | `.sh` |
| Variables | `$env:VAR` or `$VAR` | `$VAR` |
| Command chaining | `;` or separate lines | `&&` |
| Null redirect | `$null` or `Out-Null` | `/dev/null` |
| Conditionals | `if ($x) { }` | `if [ $x ]; then` |
| String interpolation | `"Hello $name"` | `"Hello $name"` (same) |
| Command substitution | `$(command)` | `$(command)` (same) |

**Common Conversions**:

```powershell
# Bash: command1 && command2
# PowerShell:
command1; if ($LASTEXITCODE -eq 0) { command2 }
# Or simply run on separate lines

# Bash: export VAR=value
# PowerShell:
$env:VAR = "value"

# Bash: command > /dev/null 2>&1
# PowerShell:
command *> $null

# Bash: [ -f file.txt ] && echo "exists"
# PowerShell:
if (Test-Path file.txt) { Write-Host "exists" }
```

When providing scripts, **always provide PowerShell versions**.

### 0.5 Development Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    NO LOCALHOST SERVERS                         │
├─────────────────────────────────────────────────────────────────┤
│  Write Code → Push to GitHub → GitHub Actions → Cloud Run      │
│                                                    ↓            │
│                                          Test on Cloud Run URL  │
└─────────────────────────────────────────────────────────────────┘
```

**Testing URL Format**: `https://{{PROJECT_SLUG}}-xxxxxxxxxx-uc.a.run.app`

Get your Cloud Run URL:
```powershell
gcloud run services describe {{PROJECT_SLUG}} --region=us-central1 --format="value(status.url)"
```

---

## Phase 1: Responsibility Matrix

| Task | Project Lead | Claude | VS Code AI |
|------|:------------:|:------:|:----------:|
| Create GitHub repository | ✅ | | |
| Create GCP project (if new) | ✅ | | |
| Create OAuth credentials | ✅ | | |
| Provide API keys | ✅ | | |
| Design system architecture | | ✅ | |
| Create database schema | | ✅ | |
| Design API endpoints | | ✅ | |
| Generate code files | | ✅ | |
| Create TEST_PLAN.md | | ✅ | |
| Create UI_DESIGN.md | | ✅ | |
| Create USER_GUIDE.md | | ✅ | |
| Create database & user in SQL | | | ✅ |
| Store secrets in Secret Manager | | | ✅ |
| Run gcloud commands | | | ✅ |
| Initialize git repository | | | ✅ |
| Create GitHub Actions workflow | | | ✅ |
| Push to GitHub | | | ✅ |
| Debug deployment issues | | | ✅ |
| Implement tests (pytest) | | | ✅ |
| Build frontend | | | ✅ |

### Responsibility Matrix Clarification

**VS Code AI Automation Principle**: When a task is assigned to VS Code AI (✅ in the VS Code AI column), the AI must:

1. **Execute commands directly** — Do not tell Project Lead to run gcloud commands
2. **Create automation scripts** — Wrap multi-step processes in .ps1 scripts
3. **Verify before reporting success** — Check command exit codes and state
4. **Handle errors** — If a command fails, debug and retry before escalating

**The ONLY exception**: If `gcloud config get-value project` returns wrong project, VS Code AI instructs Project Lead to run the Passkey authentication sequence (Phase 0.1).

| ❌ Wrong Behavior | ✅ Correct Behavior |
|-------------------|---------------------|
| "Please run: `gcloud secrets create...`" | Run the command directly in terminal |
| "Paste this value into Secret Manager" | `echo -n "value" \| gcloud secrets create...` |
| "Help debug deployment errors" | Own debugging: check logs, fix issues, retry |
| "You need to set up WIF" | Run WIF setup commands, report completion |

### Pre-Work Checklist (Mandatory)

> **VS Code AI must complete this BEFORE writing any code.**

```
BEFORE WRITING ANY CODE:

[ ] Read relevant SKILL.md files (if applicable)
[ ] Review database schema/data model documentation
[ ] Review API documentation if applicable
[ ] Review project-specific methodology constraints

VS Code must state:
"I have reviewed [specific documents] and understand that [key constraints].
My approach will be [description] which complies with [methodology sections]."

Project Lead confirms understanding before VS Code proceeds.
```

### Automation Requirements (Positive Instructions)

**Parent Principle**: Anything that CAN be automated SHOULD be automated.

```
1. AUTHENTICATION:
   ✅ DO: Retrieve all credentials from Google Secret Manager
   ✅ DO: Use service accounts for GCP operations
   ✅ DO: Use connection strings with embedded credentials from secrets
   
   Example (correct):
   ```python
   from google.cloud import secretmanager
   
   def get_secret(secret_id):
       client = secretmanager.SecretManagerServiceClient()
       name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
       response = client.access_secret_version(request={"name": name})
       return response.payload.data.decode("UTF-8")
   
   db_password = get_secret("{{PROJECT_SLUG}}-db-password")
   ```

2. DATABASE CONNECTIONS:
   ✅ DO: Build connection strings programmatically from secrets
   ✅ DO: Use parameterized queries
   
3. API KEYS:
   ✅ DO: Retrieve from Secret Manager or environment variables
   ✅ DO: Never hardcode, never prompt
   
4. SCRIPTS:
   ✅ DO: Run completely non-interactively
   ✅ DO: Accept all inputs via arguments, env vars, or config files
```

### Automation Violations Quick Reference

| Violation | Correct Approach |
|-----------|------------------|
| `getpass("Enter password:")` | `get_secret("db-password")` |
| `input("Enter API key:")` | `os.getenv("OPENAI_API_KEY")` or Secret Manager |
| `input("Continue? y/n")` | `--force` flag or `--dry-run` default |
| Manual SQL execution in SSMS | Scripted migration with verification |

### Code Delivery Standards

> **Always provide COMPLETE files. Never diffs or snippets.**

When providing code, scripts, stored procedures, or configuration files:

| ✅ ALWAYS DO | ❌ NEVER DO |
|--------------|-------------|
| Provide complete file contents | "Replace this section with..." |
| Ready to copy/paste or save | "Find line X and change to..." |
| Include file header with version | Unified diff format (+/- lines) |
| Immediately usable | "Add this after line 47..." |

**Exception**: If file is >500 lines AND only small section changes, ASK Project Lead preference first.

**Rationale**: Extra seconds to generate complete file saves significant debugging time. AI token costs are trivial compared to human merge-error debugging.

### Version Control Best Practices

> **Push at logical checkpoints, not only when asked.**

| When to Push | Examples |
|--------------|----------|
| After each significant fix | Bug fix, security fix, data integrity fix |
| After each feature completion | User story complete, feature ready for testing |
| End of each working session | Before ending conversation, switching projects |
| Before handoffs | Before deployment, review meetings, another dev needs code |
| **MINIMUM** | At least once per day |

**AI Agent Responsibility**:
- Proactively suggest "Ready to push?" after completing significant work
- Include push status in task completion reports
- Warn if unpushed changes accumulating
- Never let >1 day pass without pushing completed work

**Commit Message Format**:
```
✅ Good: "Fix UTF-16LE encoding for Greek text in SQL Server"
✅ Good: "Store DALL-E images to GCS instead of temp URLs"
❌ Bad: "Fixed stuff"
❌ Bad: "WIP"
```

### Developer Tests Before Handoff

> ⚠️ **Universal Principle**: Do not hand off ANY work for review until you have tested it yourself.
> 
> Project Lead's time is for reviewing WORKING features, not debugging errors you should have caught.

This applies to ALL handoffs throughout the project—Sprint 1, Sprint 2, bug fixes, features, everything.

#### Self-Verification Requirements

**Before requesting Project Lead review, VS Code AI must verify**:

| Work Type | Self-Verification Required |
|-----------|---------------------------|
| **Frontend/UI** | Browser DevTools: Console (zero errors), Network (no failed requests), feature renders |
| **API endpoints** | Curl/Postman: endpoints respond correctly, no 500 errors |
| **Database changes** | Query returns expected results, no constraint violations |
| **Scripts/automation** | Script runs without errors, produces expected output |
| **Bug fixes** | Original bug no longer reproduces, no new errors introduced |

#### Browser DevTools Checklist (Frontend Work)

```
Before handing off ANY frontend work:

1. [ ] Open browser DevTools (F12)
2. [ ] Console tab: ZERO red errors
3. [ ] Network tab: No failed requests (red entries)
4. [ ] Feature actually renders on screen
5. [ ] Basic interactions work (click, submit, navigate)
```

#### Common Issues to Catch Yourself

| Location | What to Check | You Should Fix |
|----------|---------------|----------------|
| Console | `TypeError`, `ReferenceError` | JS bugs |
| Console | `Failed to fetch` | API endpoint URLs |
| Console | Service worker errors | Cache file paths |
| Network (red) | 404 errors | File paths, routing |
| Network (red) | CORS errors | API headers |
| API response | 500 errors | Backend bugs |
| Database | Constraint violations | Data integrity |

#### Handoff Report Template

When requesting Project Lead review, include:

```
## Handoff: [Feature/Fix Name]

**What was implemented**: [description]

**Self-verification completed**:
- [ ] Tested [browser/API/script/database] myself
- [ ] Zero errors in [Console/logs/output]
- [ ] Feature works as expected
- [ ] [For fixes] Original issue no longer reproduces

**Known limitations**: [any caveats]

**Ready for review**: Yes
```

#### Violation Response

If VS Code hands off broken/untested code:

```
METHODOLOGY VIOLATION: You handed off untested code.

Before asking me to test or review:
1. YOU test it yourself first
2. YOU verify zero errors (console, logs, output)
3. YOU confirm it actually works
4. ONLY THEN ask me to review

Fix the errors, verify yourself, then report back with:
- What the bug was
- How you fixed it  
- Confirmation you tested it yourself

My time is for reviewing WORKING code, not finding bugs you should have caught.
```

### Playwright for UI Testing - VS Code's Eyes

> ⚠️ **VS Code AI cannot manually open a browser.** It cannot use DevTools, see console errors, or click elements. For UI projects, Playwright is required.

**Why Playwright is Required**:

VS Code AI literally **cannot**:
- Open Chrome or any browser
- Use DevTools
- See console errors visually
- Click interactive elements
- Test mobile viewports
- Take screenshots manually

Playwright gives VS Code "eyes" - it can programmatically:
- Launch a headless browser
- Capture console errors
- Click elements, fill forms
- Test mobile and desktop viewports
- Verify elements are visible
- Take screenshots

**Setup (Early in Project)**:

```powershell
# Install Playwright
pip install playwright pytest-playwright --break-system-packages
playwright install chromium
```

**Minimum Smoke Test** (`tests/test_ui_smoke.py`):

```python
import pytest
from playwright.sync_api import Page, expect

@pytest.fixture(scope="session")
def browser_context_args():
    return {"viewport": {"width": 1920, "height": 1080}}

def test_page_loads_without_console_errors(page: Page):
    """Page loads without JavaScript errors."""
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    
    page.goto("{{CLOUD_RUN_URL}}")
    page.wait_for_load_state("networkidle")
    
    assert len(errors) == 0, f"Console errors: {errors}"

def test_key_elements_visible(page: Page):
    """Key UI elements are visible."""
    page.goto("{{CLOUD_RUN_URL}}")
    
    # Adjust selectors for your app
    expect(page.locator("header")).to_be_visible()
    expect(page.locator("main")).to_be_visible()

def test_mobile_viewport(page: Page):
    """Page works on mobile (375x667)."""
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("{{CLOUD_RUN_URL}}")
    
    # Verify mobile layout works
    expect(page.locator("body")).to_be_visible()

def test_interactive_elements_clickable(page: Page):
    """Interactive elements respond to clicks."""
    page.goto("{{CLOUD_RUN_URL}}")
    
    # Example: button click doesn't error
    # button = page.locator("button#submit")
    # button.click()
```

**Run Before Every Handoff**:

```powershell
pytest tests/test_ui_smoke.py -v
```

**Handoff Criteria**: "Playwright smoke tests passing" replaces "I tested it manually."

Without Playwright (or equivalent), VS Code is blind to UI behavior and the Project Lead becomes the only tester.

### Pre-Deploy Code Review Checklist

> Playwright catches runtime errors. Code review catches "I shipped placeholder code."

Before deploying, VS Code must verify:

#### No Incomplete Code
```powershell
# Find TODOs in code
Select-String -Path "frontend/*.html","frontend/*.js" -Pattern "TODO|FIXME|stub|not implemented"

# Find empty functions (rough check)
Select-String -Path "frontend/*.js" -Pattern "function.*\{\s*\}"
```

- [ ] Search for `TODO` - none in production code paths
- [ ] Search for `FIXME` - none in production code paths
- [ ] Search for empty function bodies: `function xxx() { }` or `// stub`
- [ ] Search for `console.log("not implemented")` or similar

#### Initialization Order
- [ ] Event listeners that use objects are added AFTER those objects are initialized
- [ ] DOM event handlers are added after DOM elements exist
- [ ] Async dependencies are awaited before use

#### All Code Paths Exist
- [ ] Every `onclick` handler calls a function that exists
- [ ] Every function called actually does something (not a stub)
- [ ] Every imported module is actually used

**The Rule**: If you wrote `// TODO` or an empty function, it's not ready to deploy.

### Verify GCP Project Before Deploy

> Wrong project = broken deployment.

Before ANY `gcloud run deploy`:

```powershell
# ALWAYS verify first
gcloud config get-value project
# Must output: {{GCP_PROJECT_ID}}

# If wrong, fix it:
gcloud config set project {{GCP_PROJECT_ID}}
```

Add this to your deploy script or run manually every time.

### Application Version Numbers

> Every deployment must have a visible version number. Verify deployed == tested.

#### Requirements

1. **Display version in the UI** - Footer, header, about page, or browser console
2. **Increment with EVERY deployment** - Even small fixes get a new version
3. **Communicate version in handoff** - So tester can verify they see the right version

#### Implementation Examples

**Frontend (HTML footer)**:
```html
<footer>
  <span class="version">v1.2.3</span>
</footer>
```

**Frontend (JavaScript console)**:
```javascript
console.log('App Version: 1.2.3');
```

**Backend (API endpoint)**:
```python
@app.get("/version")
def get_version():
    return {"version": "1.2.3"}
```

**Backend (health check)**:
```python
@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.2.3"}
```

#### Version Format

Use semantic versioning: `MAJOR.MINOR.PATCH`
- **MAJOR**: Breaking changes
- **MINOR**: New features
- **PATCH**: Bug fixes, small changes

For rapid iteration, even just incrementing PATCH with each deploy is fine: `1.0.1` → `1.0.2` → `1.0.3`

#### Handoff Format

```
## Deployment Handoff

**Version**: v1.2.3
**Deployed to**: {{CLOUD_RUN_URL}}
**Verify version at**: [footer / /health endpoint / browser console]

**Changes in this version**:
- Fixed service worker caching
- Added mobile viewport support

Please confirm you see v1.2.3 before testing.
```

#### If Versions Don't Match

If tester sees old version:
1. Hard refresh: `Ctrl+Shift+R` (Windows) / `Cmd+Shift+R` (Mac)
2. Clear cache: DevTools → Application → Clear Storage
3. Unregister service worker: DevTools → Application → Service Workers → Unregister
4. If still wrong: deployment may have failed - check GitHub Actions

### AI Research Responsibility

> AI agents have research capabilities. Use them.

When AI needs domain knowledge to complete a task:

| Situation | Action |
|-----------|--------|
| Factual domain question | AI researches using available tools |
| Industry best practice | AI researches using available tools |
| Implementation approach | AI researches, proposes solution |
| Business/policy decision | Ask Project Lead |
| Ambiguous requirements | Ask Project Lead |
| Irreversible action | Confirm with Project Lead |

**Wrong**:
```
AI: "I need to know the correct value for X. What should it be?"
AI: "Should I use approach A or B?"
```

**Right**:
```
AI: [Calls OpenAI/searches documentation]
AI: "I researched X and found the correct value is Y because [evidence].
     I'll proceed with this unless you disagree."
```

Project Lead's time is for decisions, not research the AI can do itself.

---

## Phase 2: Architecture Design

### 2.1 System Overview

```
[Describe the application purpose and main components]
```

### 2.2 Database Schema

```sql
-- {{DATABASE_NAME}} Database Schema
-- Execute in SSMS (contains GO statements)

USE master;
GO

-- Create database if not exists
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{{DATABASE_NAME}}')
BEGIN
    CREATE DATABASE {{DATABASE_NAME}};
END
GO

USE {{DATABASE_NAME}};
GO

-- Tables go here
```

### 2.3 API Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | /health | Health check | No |
| GET | /api/v1/... | ... | Yes |

### 2.4 External Integrations

| Service | Purpose | Credentials Location |
|---------|---------|---------------------|
| Example API | ... | Secret Manager: `{{PROJECT_SLUG}}-api-key` |

### 2.5 GCP Resources Required

| Resource | Name | Notes |
|----------|------|-------|
| Cloud Run Service | {{PROJECT_SLUG}} | us-central1 |
| Cloud SQL Database | {{DATABASE_NAME}} | On {{SQL_INSTANCE}} |
| Secret Manager | {{PROJECT_SLUG}}-* | All project secrets |
| GCS Bucket | {{GCS_BUCKET}} | If needed |

---

## Phase 3: Sprint 1 - Infrastructure & API

### 3.1 VS Code AI Tasks

#### Database Setup
```sql
-- Create database user (run in SSMS)
USE master;
GO

CREATE LOGIN {{PROJECT_SLUG}}_user WITH PASSWORD = '[GENERATE_SECURE_PASSWORD]';
GO

USE {{DATABASE_NAME}};
GO

CREATE USER {{PROJECT_SLUG}}_user FOR LOGIN {{PROJECT_SLUG}}_user;
ALTER ROLE db_datareader ADD MEMBER {{PROJECT_SLUG}}_user;
ALTER ROLE db_datawriter ADD MEMBER {{PROJECT_SLUG}}_user;
GO
```

#### Backup Configuration
```powershell
# Verify backup configuration on instance
gcloud sql instances describe {{SQL_INSTANCE}} --format="yaml(settings.backupConfiguration)"

# If backups not enabled, enable them:
gcloud sql instances patch {{SQL_INSTANCE}} \
    --backup-start-time=03:00 \
    --enable-point-in-time-recovery \
    --retained-backups-count=7

# Verify first backup completed
gcloud sql backups list --instance={{SQL_INSTANCE}} --limit=1
```

> ⚠️ **CRITICAL**: Do not proceed to user testing without verified backups.

#### Secret Manager Setup
```powershell
# Database connection string
echo -n "DRIVER={ODBC Driver 18 for SQL Server};SERVER={{SQL_INSTANCE_IP}};DATABASE={{DATABASE_NAME}};UID={{PROJECT_SLUG}}_user;PWD=[PASSWORD];TrustServerCertificate=yes" | `
gcloud secrets create {{PROJECT_SLUG}}-db-connection --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding {{PROJECT_SLUG}}-db-connection `
    --member="serviceAccount:{{GCP_PROJECT_NUMBER}}-compute@developer.gserviceaccount.com" `
    --role="roles/secretmanager.secretAccessor"
```

#### Project Structure
```
{{PROJECT_SLUG}}/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings from Secret Manager
│   ├── database.py          # Database connection
│   ├── models.py            # Pydantic models
│   └── routers/
│       └── api.py           # API routes
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   └── test_api.py          # API tests
├── .github/
│   └── workflows/
│       └── deploy.yml       # GitHub Actions
├── Dockerfile
├── requirements.txt
├── .gitignore
└── README.md
```

#### GitHub Actions Workflow
```yaml
# .github/workflows/deploy.yml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    
    steps:
      - uses: actions/checkout@v4
      
      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2
      
      - name: Build and Deploy
        run: |
          gcloud run deploy {{PROJECT_SLUG}} \
            --source . \
            --region us-central1 \
            --allow-unauthenticated \
            --set-secrets="DB_CONNECTION={{PROJECT_SLUG}}-db-connection:latest"
```

### 3.2 Sprint 1 Definition of Done

- [ ] Database created with tables and user
- [ ] **Database backups enabled and verified**
- [ ] All secrets stored in Secret Manager
- [ ] API endpoints accessible on Cloud Run URL
- [ ] Authentication working (if applicable)
- [ ] Database CRUD operations succeed
- [ ] GitHub Actions deploys successfully on push
- [ ] TEST_PLAN.md created
- [ ] UI_DESIGN.md created
- [ ] USER_GUIDE.md created
- [ ] **Smoke tests pass against deployed URL**
- [ ] **No 500 errors on any endpoint**
- [ ] **User can load app without error**

---

## Phase 4: Sprint 2 - Testing, UI & Documentation

### 4.1 Testing Philosophy

> **If it's in the requirements or user documentation, it MUST be tested.**

#### Test Types and Purposes

| Test Type | Runs Against | Purpose | When Required |
|-----------|--------------|---------|---------------|
| **Smoke Tests** | Deployed URL | Verify deployment works | Before user testing (BLOCKING) |
| **Unit Tests** | Mocks/Local | Verify code logic | After behavior confirmed |
| **Integration Tests** | Real services | Verify integrations | Before release |

#### Testing Sequence for New Features

```
Write code → Deploy → Smoke test → User test → Write unit tests based on verified behavior
```

1. **Smoke tests**: BLOCKING — must pass before user testing
2. **Unit tests**: NON-BLOCKING during initial development
3. After user validation, unit tests become BLOCKING

#### Testing Sequence for Existing Features

- Unit tests: BLOCKING (prevent regression)
- Smoke tests: BLOCKING (verify deployment)

| Category | What to Test |
|----------|--------------|
| Happy Path | Every documented feature works as described |
| Obvious Exceptions | User-friendly error messages for common mistakes |

#### Error Message Guidelines

```python
# ❌ BAD - Exposes internal implementation
raise HTTPException(status_code=500, detail="NoneType has no attribute 'id'")

# ✅ GOOD - User-friendly, actionable
raise HTTPException(status_code=404, detail="Collection not found. It may have been deleted.")
```

System/infrastructure errors (database down, API timeout) can bubble up as-is—users have AI assistants to help interpret technical errors.

#### Coverage Requirements

```yaml
# In GitHub Actions
- name: Run tests
  run: |
    pytest --cov=app --cov-report=xml --cov-fail-under=70
```

### 4.2 Help Content Strategy

| Approach | Implementation |
|----------|----------------|
| Main Help | Link to GitHub docs: `https://github.com/{{GITHUB_REPO}}/blob/main/docs/USER_GUIDE.md` |
| Tooltips | Inline hints for complex fields |
| Welcome | First-time user message explaining core workflow |

**Why external links?** Documentation can be updated without redeploying the application.

### 4.3 Sprint 2 Definition of Done

- [ ] pytest test suite implemented
- [ ] All tests pass in CI
- [ ] Coverage ≥ 70%
- [ ] Frontend matches UI_DESIGN.md
- [ ] User can complete core workflow end-to-end
- [ ] Help link accessible and working
- [ ] Error messages are user-friendly
- [ ] Welcome/onboarding message displays for new users

---

## Phase 5: Deployment Verification

### 5.1 Post-Deployment Checklist

```powershell
# Get Cloud Run URL
$URL = gcloud run services describe {{PROJECT_SLUG}} --region=us-central1 --format="value(status.url)"

# Health check
curl "$URL/health"

# API check (adjust endpoint as needed)
curl "$URL/api/v1/status"
```

### 5.2 Verify Secrets Access

```powershell
# List secrets
gcloud secrets list --filter="name:{{PROJECT_SLUG}}"

# Verify IAM binding
gcloud secrets get-iam-policy {{PROJECT_SLUG}}-db-connection
```

### 5.3 Verify Database Connectivity

From Cloud Run logs:
```powershell
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name={{PROJECT_SLUG}}" --limit=50
```

---

## Appendix A: Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Password prompt during `gcloud config set project` | Auth not completed | Run `gcloud auth login` first |
| SQL script fails in Cloud SQL Studio | GO statements not supported | Use SSMS or sqlcmd |
| "Secret not found" error | IAM binding missing | Add secretAccessor role to compute service account |
| Cloud Run deployment fails | Dockerfile error | Check build logs with `gcloud builds list` |
| Database connection timeout | IP not authorized | Verify Cloud SQL authorized networks |

---

## Appendix B: Reference Commands

### GCP Authentication
```powershell
gcloud auth login
gcloud auth application-default login
gcloud config set project {{GCP_PROJECT_ID}}
gcloud auth application-default set-quota-project {{GCP_PROJECT_ID}}
```

### Cloud Run
```powershell
# Deploy
gcloud run deploy {{PROJECT_SLUG}} --source . --region us-central1

# Get URL
gcloud run services describe {{PROJECT_SLUG}} --region=us-central1 --format="value(status.url)"

# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name={{PROJECT_SLUG}}" --limit=50
```

### Secret Manager
```powershell
# Create secret
echo -n "secret-value" | gcloud secrets create {{PROJECT_SLUG}}-secret-name --data-file=-

# Grant access
gcloud secrets add-iam-policy-binding {{PROJECT_SLUG}}-secret-name \
    --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Read secret (for verification)
gcloud secrets versions access latest --secret={{PROJECT_SLUG}}-secret-name
```

### Git/GitHub
```powershell
git init
git remote add origin https://github.com/{{GITHUB_REPO}}.git
git add .
git commit -m "Initial commit"
git push -u origin main
```

---

## Appendix C: Cloud Migration Script Template

Use this script template for migrating localhost projects to cloud-first deployment. VS Code AI should customize and execute this script directly.

```powershell
# {{PROJECT_SLUG}}-Cloud-Migration.ps1
# VS Code AI: Run this script to complete cloud migration
# Per project-methodology v3.6

param(
    [string]$ProjectId = "{{GCP_PROJECT_ID}}",
    [string]$ProjectSlug = "{{PROJECT_SLUG}}",
    [string]$Region = "us-central1",
    [string]$SqlInstanceIp = "{{SQL_INSTANCE_IP}}",
    [string]$DatabaseName = "{{DATABASE_NAME}}",
    [string]$DatabaseUser = "{{PROJECT_SLUG}}_user",
    [string]$DatabasePassword = "{{SECURE_PASSWORD}}"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  $ProjectSlug Cloud Migration Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# ========================================
# Step 1: Verify Authentication
# ========================================
Write-Host "`nStep 1: Verifying GCP authentication..." -ForegroundColor Yellow

$currentProject = gcloud config get-value project 2>$null
if ($currentProject -ne $ProjectId) {
    Write-Host "  ✗ Wrong project: $currentProject" -ForegroundColor Red
    Write-Host "  Project Lead must run Passkey authentication sequence first." -ForegroundColor Red
    Write-Host "  See: PROJECT_KICKOFF_TEMPLATE.md Phase 0.1" -ForegroundColor Gray
    exit 1
}
Write-Host "  ✓ Authenticated to project: $currentProject" -ForegroundColor Green

# ========================================
# Step 2: Create/Update Secrets
# ========================================
Write-Host "`nStep 2: Configuring Secret Manager..." -ForegroundColor Yellow

$secrets = @{
    "$ProjectSlug-db-server" = $SqlInstanceIp
    "$ProjectSlug-db-name" = $DatabaseName
    "$ProjectSlug-db-user" = $DatabaseUser
    "$ProjectSlug-db-password" = $DatabasePassword
}

foreach ($secretName in $secrets.Keys) {
    $secretValue = $secrets[$secretName]
    $exists = gcloud secrets describe $secretName --project=$ProjectId 2>$null
    
    if ($exists) {
        Write-Host "  Updating secret '$secretName'..." -ForegroundColor Cyan
        $secretValue | gcloud secrets versions add $secretName --data-file=- --project=$ProjectId 2>$null
    } else {
        Write-Host "  Creating secret '$secretName'..." -ForegroundColor Cyan
        $secretValue | gcloud secrets create $secretName --data-file=- --project=$ProjectId 2>$null
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✓ $secretName" -ForegroundColor Green
    } else {
        Write-Host "    ✗ Failed: $secretName" -ForegroundColor Red
    }
}

# ========================================
# Step 3: Grant IAM Access
# ========================================
Write-Host "`nStep 3: Granting IAM access..." -ForegroundColor Yellow

$PROJECT_NUMBER = (gcloud projects describe $ProjectId --format="value(projectNumber)")
$SA = "$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

foreach ($secretName in $secrets.Keys) {
    gcloud secrets add-iam-policy-binding $secretName `
        --member="serviceAccount:$SA" `
        --role="roles/secretmanager.secretAccessor" `
        --project=$ProjectId 2>$null | Out-Null
    Write-Host "  ✓ IAM binding: $secretName" -ForegroundColor Green
}

# ========================================
# Step 4: Verify Infrastructure Files
# ========================================
Write-Host "`nStep 4: Checking infrastructure files..." -ForegroundColor Yellow

$requiredFiles = @(
    @{ Path = "Dockerfile"; Description = "Container definition" },
    @{ Path = ".github/workflows/deploy.yml"; Description = "CI/CD pipeline" },
    @{ Path = "requirements.txt"; Description = "Python dependencies" }
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file.Path) {
        Write-Host "  ✓ $($file.Path)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ MISSING: $($file.Path) - $($file.Description)" -ForegroundColor Red
    }
}

# ========================================
# Step 5: Summary
# ========================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Migration Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "  1. git add . && git commit -m 'Cloud migration' && git push" -ForegroundColor White
Write-Host "  2. Monitor: https://github.com/{{GITHUB_REPO}}/actions" -ForegroundColor White
Write-Host "  3. Test: gcloud run services describe $ProjectSlug --region=$Region --format='value(status.url)'" -ForegroundColor White
```

---

## Appendix D: Error Recovery Protocol

When fixing bugs or data issues, follow this protocol to avoid making things worse.

> **Key Principle**: Each "fix" attempt can make data worse, not better. Stop and plan before acting.

### Error Recovery Steps

```
1. STOP: Don't attempt fixes until root cause is understood
   - What exactly is wrong?
   - Why did it happen?
   - How many records are affected?

2. PRESERVE: Back up current state before any fix attempt
   - SQL: SELECT * INTO table_backup_YYYYMMDD FROM table;
   - Files: Copy to backup folder with date
   - Document the current state

3. ISOLATE: Test fix on copy/single record, not production data
   - Create test record or use non-critical record
   - Apply fix to ONE record only
   - Verify fix works (via Golden Audit, not self-test)

4. VERIFY: Confirm fix works before applying broadly
   - Golden Audit passes for test record
   - Project Lead confirms fix is correct
   - Small batch (3-5 records) test passes

5. APPLY: Only after steps 1-4 pass
   - Apply to all affected records
   - Include progress logging
   - Verify sample after completion

6. ROLLBACK PLAN: Know how to undo if fix fails
   - Document rollback steps before starting
   - Keep backup until fix is verified
```

### Backup Before Fix Template

```sql
-- Always create backup before any fix
SELECT * INTO {{TABLE_NAME}}_backup_YYYYMMDD FROM {{TABLE_NAME}};

-- Verify backup
SELECT COUNT(*) FROM {{TABLE_NAME}}_backup_YYYYMMDD;

-- After fix is verified, backup can be dropped (optional)
-- DROP TABLE {{TABLE_NAME}}_backup_YYYYMMDD;
```

### Fix Testing Sequence

```
1. UNIT TEST: Fix ONE record
   - Apply fix to single record
   - Verify with Golden Audit (not self-test)
   - Project Lead confirms

2. SMALL BATCH: Fix 3-5 records
   - Apply fix to small batch
   - Verify each individually
   - Check for patterns (all fail same way = systemic bug)

3. BULK FIX: Only after steps 1-2 pass
   - Include progress logging
   - Include error handling (stop on first failure)
   - Verify sample after completion
```

### Bug Fix Verification: Test the Code Path

> **When fixing a bug that caused bad data, you must test THE CODE THAT WAS BROKEN, not just fix the data.**

```
1. FIND THE ROOT CAUSE
   - Locate the code that created the bad data
   - Understand WHY it produced incorrect results
   - Document the file, function, and line numbers
   
2. FIX THE CODE
   - Modify the code to produce correct results
   - Follow "No Diffs" rule - provide complete updated file
   
3. TEST THE CODE PATH (Critical!)
   Before fixing existing data, prove the fix works:
   - Run the ACTUAL code that was broken
   - Create NEW test data through that code path
   - Verify the new data is correct
   
   Example: If "add figure" stored temp URLs:
   - Use "add figure" to create a TEST figure
   - Check: does the test figure have a permanent URL?
   - If yes: code is fixed
   - If no: debug further before proceeding
   
4. VERIFY WITH AUDIT
   - Run Golden Audit
   - Test data should NOT appear in violations
   - Original bad data SHOULD still appear (not fixed yet)
   
5. FIX EXISTING DATA
   Only after step 3 passes:
   - Use the now-verified code to regenerate bad data
   - Or run a data migration script
   
6. FINAL VERIFICATION
   - Run Golden Audit again
   - All violations should be resolved
```

**Anti-Pattern**:
- Fix data directly without fixing code → Bug will recur
- Fix code and assume it works without testing → No proof it's fixed
- Test with different code than what caused the bug → Wrong code tested

### What NOT To Do

| ❌ Wrong | ✅ Correct |
|----------|-----------|
| Apply fix to all records immediately | Test on single record first |
| Skip backup because "it's a simple fix" | Always backup before any change |
| Trust your own test that fix worked | Verify with Golden Audit |
| Keep trying different fixes rapidly | Stop, understand root cause, then fix |
| Delete backup immediately after fix | Keep backup until fix verified in production |
| Fix data without fixing/testing code | Test the code path that was broken first |

---

## Appendix E: Additional Documentation

For detailed guidance, see these companion documents:

| Document | Purpose |
|----------|---------|
| VS_CODE_TESTING_REQUIREMENTS.md | **Automated testing requirements for VS Code AI** |
| VIOLATION_RESPONSE.md | How to handle methodology violations |
| VERIFICATION_GOVERNANCE.md | Golden Audit ownership and access control |
| UNICODE_HANDLING.md | Non-ASCII text encoding requirements |
| BACKUP_VERIFICATION.md | Database backup verification |
| SMOKE_TEST_TEMPLATE.md | Deployment verification tests |
| EXTERNAL_API_HANDLING.md | Temporary resource persistence |

---

**Template Version**: 3.12.1  
**Last Updated**: January 2026  
**Methodology**: [coreyprator/project-methodology](https://github.com/coreyprator/project-methodology)
