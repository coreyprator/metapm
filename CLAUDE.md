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
