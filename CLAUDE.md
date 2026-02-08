# CLAUDE.md - Project Instructions for Claude Code

---

## ⚠️ Handoff Bridge — MANDATORY

ALL responses to Claude.ai/Corey MUST use the handoff bridge.
Create file → Run handoff_send.py → Provide URL.
NO EXCEPTIONS. See project-methodology/CLAUDE.md for details.

---

> **Last Updated**: 2026-01-30
> **Current Service**: metapm-v2 (NOT "metapm")
> **Current Project**: super-flashcards-475210 (NOT "metapm")

---

## ⚠️ INFRASTRUCTURE - READ FIRST

**These values are EXACT. Do not guess or invent alternatives.**

| Resource | Value |
|----------|-------|
| **GCP Project** | `super-flashcards-475210` |
| **Cloud Run Service** | `metapm-v2` |
| **Cloud Run Region** | `us-central1` |
| **Custom Domain** | `https://metapm.rentyourcio.com` |
| **Cloud SQL Instance** | `flashcards-db` |
| **Cloud SQL Connection** | `super-flashcards-475210:us-central1:flashcards-db` |
| **Database Name** | `MetaPM` |
| **Database IP** | `35.224.242.223` |

### Before ANY Deploy Command
```powershell
gcloud config get-value project
# MUST return: super-flashcards-475210
# If wrong: gcloud config set project super-flashcards-475210
```

### Deploy Command (EXACT)
```powershell
gcloud run deploy metapm-v2 `
  --source . `
  --region us-central1 `
  --allow-unauthenticated `
  --set-env-vars="DB_SERVER=35.224.242.223,DB_NAME=MetaPM,DB_USER=sqlserver,ENVIRONMENT=production" `
  --set-secrets="DB_PASSWORD=db-password:latest" `
  --add-cloudsql-instances="super-flashcards-475210:us-central1:flashcards-db"
```

### ❌ DEPRECATED - DO NOT USE
- Service `metapm` (old, broken)
- Project `metapm` (doesn't exist for this database)
- Instance `coreyscloud` (doesn't exist)

---

## CRITICAL RULES

### 1. Cloud-First - No "Local"
There is NO localhost. There is NO "local only."  
Workflow: Write → Push → Deploy → Test on Cloud Run URL.  
Never say "local edits" - that state doesn't exist.

**Database is ALWAYS Cloud SQL. There is NO local database.**

### 2. You Own Deployment
YOU run `gcloud run deploy`. Don't ask permission. Don't ask "want me to deploy?"  
Just deploy, verify, and report results.

### 3. You Must Test Before Handoff
You CANNOT manually test UI. Use Playwright.

Before EVERY handoff:
```powershell
pytest tests/test_ui_smoke.py -v
```

ALL tests must pass. Include test output in your report.

### 4. Version Numbers
Every deploy must update the version in `app/core/config.py`.
Report: "Deployed v1.4.5"

### 5. Definition of Done (MANDATORY for ALL Tasks)

Before sending a completion handoff, ALL items must be checked:

**Code**:
- [ ] Code changes complete
- [ ] Tests pass (if applicable)

**Git (MANDATORY)**:
- [ ] All changes staged: `git add [files]`
- [ ] Committed: `git commit -m "type: description (vX.X.X)"`
- [ ] Pushed: `git push origin main`

**Deployment (MANDATORY)**:
- [ ] Deployed: `gcloud run deploy metapm-v2 --source . --region us-central1`
- [ ] Health check passes: `curl https://metapm.rentyourcio.com/health`
- [ ] Version matches: Response shows new version

**UAT (MANDATORY for features)**:
- [ ] Claude.ai creates UAT checklist
- [ ] Corey executes UAT
- [ ] UAT results submitted to Claude.ai
- [ ] UAT PASSED (all critical tests green)
- [ ] UAT results stored in MetaPM (`POST /mcp/handoffs/{id}/uat`)

**Handoff (MANDATORY)**:
- [ ] Handoff created with deployment verification
- [ ] Uploaded to GCS
- [ ] URL provided

⚠️ "Next steps: Deploy" is NOT acceptable. Deploy first, then send handoff.
⚠️ A feature is NOT complete until UAT passes.

### 6. Handoff Format (REQUIRED)
```markdown
## Handoff: [Feature]

**Version**: v1.4.5
**Revision**: metapm-v2-00012-xyz
**Deployed to**: https://metapm.rentyourcio.com
**Git Status**: Committed and pushed ✓

**Tests Run**:
pytest tests/ -v
# [paste actual output - REQUIRED]

**All tests pass**: Yes

**Ready for review**: Yes
```

---

## VOCABULARY LOCKDOWN

### Words You CANNOT Say (without proof)
| Forbidden | Why |
|-----------|-----|
| "Complete" / "Done" / "Finished" | Requires deployed revision + test output |
| "Ready for review" | Requires test output |
| "I think it works" | Not verification |
| "Please test and let me know" | YOU must test |
| ✅ emoji next to features | Requires proof |

### Words You MUST Say
| Required | Example |
|----------|---------|
| Deployed revision | "Deployed metapm-v2-00012-xyz" |
| Test output | "pytest: 7 passed in 3.2s" |
| Version number | "v1.4.5" |

### If Not Yet Tested
Say: "Code written. Pending deployment and testing."  
NOT: "Feature complete!"

---

## Secret Manager

All secrets are in Google Secret Manager. **NEVER use .env files.**

| Secret Name | Purpose |
|-------------|---------|
| `db-password` | SQL Server password |
| `openai-api-key` | OpenAI API (if used) |
| `anthropic-api-key` | Anthropic API (if used) |

Access in Cloud Run via `--set-secrets` flag.

---

## Database Schema

Schema is in `scripts/schema.sql`.

**Before writing ANY SQL:**
1. Check actual column names in schema.sql
2. Or query INFORMATION_SCHEMA.COLUMNS
3. Do NOT guess column names

---

## Before Starting Work

1. ✅ Run `gcloud config get-value project` - verify `super-flashcards-475210`
2. ✅ Read this CLAUDE.md completely
3. ✅ Read any KICKOFF.md or spec files in docs/
4. ✅ Check VS_CODE_TEST_RESULTS_*.md for recent issues
5. ✅ Understand what's being asked before coding

---

## Common Issues

| Issue | Prevention |
|-------|------------|
| Wrong GCP project | Always verify with `gcloud config get-value project` |
| Wrong service name | Service is `metapm-v2`, NOT `metapm` |
| Wrong DB instance | Instance is `flashcards-db`, NOT `coreyscloud` |
| SQL column mismatch | Check scripts/schema.sql before writing queries |
| Localhost connection | NO local DB - always Cloud SQL |
| "Complete" without tests | Include pytest output or say "pending testing" |

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-30 | Fixed GCP project, service name, DB instance name |
| 2026-01-14 | Initial version (had incorrect values) |
# CLAUDE.md - Project Instructions for Claude Code

## CRITICAL RULES - READ FIRST

### 1. Cloud-First - No "Local"
There is NO localhost. There is NO "local only." 
Workflow: Write → Push → Deploy → Test on Cloud Run URL.
Never say "local edits" - that state doesn't exist.

### 2. You Own Deployment
YOU run `gcloud run deploy`. Don't ask permission. Don't ask "want me to deploy?"
Just deploy, verify, and report results.

Before ANY deploy:
```powershell
gcloud config get-value project
# Must be: metapm
```

### 3. You Must Test Before Handoff
You CANNOT manually test UI. Use Playwright.

Before EVERY handoff:
```powershell
pytest tests/test_ui_smoke.py -v
```

ALL tests must pass. Include test output in your report.

### 4. Version Numbers
Every deploy must update the version. Report: "Deployed v1.2.3"

### 5. Handoff Format
```
## Handoff: [Feature]

**Version**: v1.2.3
**Deployed to**: https://metapm.rentyourcio.com

**Tests Run**:
pytest tests/ -v
# [paste actual output]

**All tests pass**: Yes

**Ready for review**: Yes
```

## What You Cannot Say
- "Local edits only" ❌
- "Let me know if you want me to deploy" ❌
- "Please test and let me know" ❌
- "I think it works" ❌

## What You Must Say
- "Deployed v1.2.3, all 5 tests pass" ✅
- "pytest output: 7 passed in 3.2s" ✅

## Project Details
- **GCP Project**: metapm
- **Cloud Run Service**: metapm
- **Cloud Run Region**: us-central1
- **Cloud Run URL**: https://metapm-67661554310.us-central1.run.app
- **Custom Domain**: https://metapm.rentyourcio.com
- **Container Registry**: us-central1-docker.pkg.dev/metapm/cloud-run-source-deploy/metapm

## Deploy Command
```powershell
cd "g:\My Drive\Code\Python\metapm"
gcloud run deploy metapm --source . --region us-central1 --project metapm --quiet
```

## Database
- **Type**: SQL Server (Azure SQL or GCP SQL Server)
- **Connection**: Via environment variable (configured in Cloud Run)
- **Schema**: scripts/schema.sql

## Before Starting Work
1. Run `gcloud config get-value project` - verify it returns "metapm"
2. Read any KICKOFF.md or spec files in docs/
3. Check VS_CODE_TEST_RESULTS_*.md for recent issues
4. Understand what's being asked before coding

## Common Issues
- **SQL Column Mismatches**: Always check scripts/schema.sql for actual table structure
- **Build Cancellations**: Builds take 5-10 minutes - don't interrupt
- **CRLF Warnings**: Ignore Git CRLF warnings on .md files

---

## 🔒 Security Requirements

### API Keys & Secrets

**NEVER**:
- Hardcode API keys, passwords, or secrets in code
- Include secrets in handoff documents
- Log secrets to console or files
- Commit secrets to git (even in .gitignore'd files)
- Share secrets in chat responses

**ALWAYS**:
- Use GCP Secret Manager for all secrets
- Reference secrets by name, not value: `gcloud secrets versions access latest --secret="secret-name"`
- Use environment variables injected at runtime
- Mask secrets in logs: `key=***REDACTED***`

### If a Secret is Accidentally Exposed

1. **Rotate immediately** — Generate new secret, update in Secret Manager
2. **Notify Corey** — Security incident
3. **Audit** — Check git history, handoff docs, logs for exposure
4. **Document** — Add to lessons learned

### Pre-Commit Checks

Before any commit, verify:
- [ ] No API keys in code
- [ ] No secrets in comments
- [ ] No credentials in test files
- [ ] No keys in handoff documents

---

## Communication Protocol

All responses to Claude.ai or Corey **MUST** use the Handoff Bridge.
See `project-methodology/CLAUDE.md` for full policy.

---

**Last Updated**: 2026-02-07
