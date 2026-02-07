# CLAUDE.md - Project Instructions for Claude Code

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
  --set-env-vars="DB_SERVER=/cloudsql/super-flashcards-475210:us-central1:flashcards-db,DB_NAME=MetaPM,DB_USER=sqlserver,ENVIRONMENT=production" `
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

### 5. Handoff Format (REQUIRED)
```markdown
## Handoff: [Feature]

**Version**: v1.4.5
**Revision**: metapm-v2-00012-xyz
**Deployed to**: https://metapm.rentyourcio.com

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
