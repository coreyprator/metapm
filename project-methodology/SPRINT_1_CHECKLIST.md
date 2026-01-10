# Sprint 1 Checklist: Infrastructure & API

**Goal**: Working backend deployed to Cloud Run with database connectivity and core API endpoints.

---

## Phase 1: Setup & Configuration

### GCP Authentication
- [ ] `gcloud auth login` completed (browser/Passkey)
- [ ] `gcloud auth application-default login` completed
- [ ] `gcloud config set project [PROJECT_ID]` completed (no password prompt)
- [ ] `gcloud auth application-default set-quota-project [PROJECT_ID]` completed
- [ ] Verified with `gcloud config get-value project`

### Database Setup
- [ ] Database created on Cloud SQL instance
- [ ] Database user created with secure password
- [ ] User granted db_datareader and db_datawriter roles
- [ ] Schema (tables, indexes, constraints) created
- [ ] Test data inserted (if applicable)

**SQL Execution Note**: If scripts contain GO statements, use SSMS or sqlcmd, NOT Cloud SQL Studio.

### Database Backup & Disaster Recovery
- [ ] Automated backups enabled on Cloud SQL instance
- [ ] Point-in-time recovery (PITR) enabled
- [ ] Backup retention period set (minimum 7 days, recommend 30)
- [ ] Backup window configured (off-peak hours)
- [ ] First backup completed successfully

```powershell
# Verify backup configuration
gcloud sql instances describe [INSTANCE_NAME] --format="yaml(settings.backupConfiguration)"

# Expected output should show:
#   enabled: true
#   pointInTimeRecoveryEnabled: true
#   backupRetentionSettings:
#     retainedBackups: 7 (or more)

# List recent backups
gcloud sql backups list --instance=[INSTANCE_NAME] --limit=5

# If backups not enabled, enable them:
gcloud sql instances patch [INSTANCE_NAME] \
    --backup-start-time=03:00 \
    --enable-point-in-time-recovery \
    --retained-backups-count=7
```

> ⚠️ **CRITICAL**: No database should go to production without verified backups. This is non-negotiable.

### Secret Manager
- [ ] Database connection string stored as secret
- [ ] API keys stored as secrets (if applicable)
- [ ] OAuth client secret stored (if applicable)
- [ ] IAM bindings added for Cloud Run service account

```powershell
# Verify secrets exist
gcloud secrets list --filter="name:[PROJECT_SLUG]"

# Verify IAM binding
gcloud secrets get-iam-policy [SECRET_NAME]
```

---

## Phase 2: Code Generation

### Project Structure
- [ ] `app/` directory with FastAPI application
- [ ] `app/main.py` - Application entry point
- [ ] `app/config.py` - Settings from Secret Manager
- [ ] `app/database.py` - Database connection
- [ ] `app/models.py` - Pydantic models
- [ ] `app/routers/` - API route modules
- [ ] `tests/` directory structure
- [ ] `Dockerfile` configured
- [ ] `requirements.txt` with dependencies
- [ ] `.gitignore` (Python + secrets)
- [ ] `README.md` with project overview

### API Endpoints
- [ ] `GET /health` - Health check (no auth)
- [ ] Core CRUD endpoints implemented
- [ ] Authentication middleware (if applicable)
- [ ] Error handling with appropriate status codes
- [ ] Request validation with Pydantic

### External Integrations
- [ ] API clients configured
- [ ] Credentials loaded from Secret Manager
- [ ] Error handling for API failures
- [ ] Rate limiting considered

---

## Phase 3: CI/CD Pipeline

### GitHub Actions
- [ ] `.github/workflows/deploy.yml` created
- [ ] Workload Identity Federation configured
- [ ] Triggers on push to main branch
- [ ] Builds and deploys to Cloud Run

### Initial Deployment
- [ ] Git repository initialized
- [ ] Remote added: `git remote add origin [GITHUB_URL]`
- [ ] Initial commit created
- [ ] Pushed to GitHub: `git push -u origin main`
- [ ] GitHub Actions workflow triggered
- [ ] Deployment completed successfully

```powershell
# Get Cloud Run URL
gcloud run services describe [SERVICE_NAME] --region=us-central1 --format="value(status.url)"
```

---

## Phase 4: Verification

### Health Check
```powershell
$URL = "[CLOUD_RUN_URL]"
curl "$URL/health"
# Expected: {"status": "healthy"} or similar
```

### API Endpoints
- [ ] Each endpoint returns expected response
- [ ] Authentication works (if applicable)
- [ ] Database queries execute successfully
- [ ] Error cases return appropriate status codes

### Logs Check
```powershell
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=[SERVICE_NAME]" --limit=20
```
- [ ] No unexpected errors in logs
- [ ] Database connections successful
- [ ] Secret Manager access working

---

## Phase 5: Documentation (Claude Deliverables)

These documents are created by Claude during Sprint 1:

- [ ] **TEST_PLAN.md** - What to test and how
- [ ] **UI_DESIGN.md** - Frontend specifications
- [ ] **USER_GUIDE.md** - End-user documentation

---

## Phase 5.5: Mandatory Testing Sequence

> **NEVER skip from "code written" to "bulk execution"**

### Testing Sequence (Required Order)

```
1. SMOKE TEST (before handoff to Project Lead):
   - All code must be smoke tested by VS Code
   - Cannot hand off untested code
   - Must document what was tested and results

2. UNIT TEST: Prove ONE record works correctly
   - Use hardcoded test data (not generated)
   - Verify against external truth (Golden Audit, not self-comparison)
   - Project Lead confirms pass before proceeding

3. SMALL BATCH: Test 3-5 records
   - Verify each individually
   - Check for patterns (all fail same way = systemic bug)

4. BULK OPERATION: Only after steps 1-3 pass
   - Include progress logging
   - Include rollback capability if possible
   - Verify sample after completion
```

### Bulk Operation Checklist

Before running any bulk operation:

- [ ] Single record test passed (verified by Project Lead)
- [ ] Small batch (3-5) test passed
- [ ] Backup created: `SELECT * INTO table_backup_YYYYMMDD FROM table`
- [ ] Rollback plan documented
- [ ] Progress logging enabled
- [ ] Error handling stops on first failure (not silent continue)

### Unicode Data Operations

For any operation involving non-ASCII text (Greek, Chinese, etc.):

- [ ] pyodbc connection has UTF-16LE encoding configured
- [ ] Database columns are NVARCHAR (not VARCHAR)
- [ ] Verification uses `UNICODE()` function, not string comparison
- [ ] See UNICODE_HANDLING.md for full requirements

---

## Phase 6: Smoke Testing (Required Before User Testing)

> ⚠️ **No user testing until ALL smoke tests pass.**
> 
> "Deployed" ≠ "Working". This phase verifies the app actually works.

### Layer 1: App Running
- [ ] Health endpoint returns 200: `curl $URL/health`
- [ ] Homepage loads without 500 error
- [ ] API docs accessible: `curl $URL/docs`

### Layer 2: Database Connected
- [ ] Data endpoints return data (not empty arrays)
- [ ] Seeded/test data is present and retrievable

### Layer 3: Auth Configured (if applicable)
- [ ] Auth endpoints respond (200 or 401, not 500)
- [ ] OAuth redirect works (doesn't 500)

### Layer 4: Protected Endpoints (if applicable)
- [ ] Return 401 without auth token (not 500)
- [ ] Return expected data with valid auth

### Layer 5: Error Handling
- [ ] Invalid resource IDs return 404 (not 500)
- [ ] Malformed requests return 400/422 (not 500)

### Smoke Test Execution

```bash
# Run smoke tests against deployed URL
export BASE_URL=$(gcloud run services describe [SERVICE_NAME] --region=us-central1 --format="value(status.url)")

# Option 1: Automated smoke test suite
pytest tests/test_smoke.py -v

# Option 2: Quick manual verification
curl $BASE_URL/health
curl $BASE_URL/docs
curl $BASE_URL/api/v1/[your-endpoint]
```

### Smoke Test Results

| Layer | Status | Notes |
|-------|--------|-------|
| App Running | ☐ Pass / ☐ Fail | |
| Database Connected | ☐ Pass / ☐ Fail | |
| Auth Configured | ☐ Pass / ☐ Fail / ☐ N/A | |
| Protected Endpoints | ☐ Pass / ☐ Fail / ☐ N/A | |
| Error Handling | ☐ Pass / ☐ Fail | |

**All layers must pass before proceeding to user testing.**

> 📋 **Before any handoff**: See "Developer Tests Before Handoff" in PROJECT_KICKOFF_TEMPLATE.md - applies to ALL work, not just Sprint 1.

---

## Sprint 1 Definition of Done

All items must be checked for Sprint 1 to be complete:

- [ ] Database created with tables and user
- [ ] **Database backups enabled and verified**
- [ ] All secrets stored in Secret Manager with proper IAM
- [ ] API endpoints accessible on Cloud Run URL
- [ ] Authentication working (if applicable)
- [ ] Database CRUD operations succeed via API
- [ ] GitHub Actions deploys successfully on push to main
- [ ] TEST_PLAN.md created and reviewed
- [ ] UI_DESIGN.md created and reviewed
- [ ] USER_GUIDE.md created and reviewed
- [ ] **Smoke tests pass against deployed URL**
- [ ] **No 500 errors on any endpoint**
- [ ] **User can load app without error**

---

## Common Issues & Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| "Secret not found" | Check secret name, verify IAM binding |
| "Connection refused" to database | Verify Cloud SQL instance IP, check authorized networks |
| GitHub Actions fails | Check WIF_PROVIDER and WIF_SERVICE_ACCOUNT secrets |
| "Module not found" | Verify requirements.txt, rebuild container |
| CORS errors | Add CORS middleware to FastAPI |

---

## Handoff to Sprint 2

Sprint 1 is complete when:
1. All checklist items above are verified
2. **All smoke tests pass** (no 500 errors)
3. Project Lead has tested core API functionality
4. TEST_PLAN.md, UI_DESIGN.md, USER_GUIDE.md are approved

Sprint 2 begins with:
- Implementing unit tests per TEST_PLAN.md (now based on verified behavior)
- Building frontend per UI_DESIGN.md
- Finalizing documentation per USER_GUIDE.md
