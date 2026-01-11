# VS Code Prompt: Fix Static Files and Debug 500 Errors

Copy this entire prompt to VS Code Copilot.

---

## PROMPT START

### Task: Debug MetaPM 500 Errors and Missing Static Files

**Issues**:
1. All API endpoints return 500 Internal Server Error
2. /static/capture.html returns 404 Not Found

### Step 1: Check Cloud Run Logs

```powershell
# Get recent logs to see the actual error
gcloud run services logs read metapm --region=us-central1 --project=metapm --limit=100

# Or open in browser
Start-Process "https://console.cloud.google.com/run/detail/us-central1/metapm/logs?project=metapm"
```

**Report the error message** - it will tell us exactly what's wrong.

### Step 2: Check Static Files Exist Locally

```powershell
cd "G:\My Drive\Code\Python\metapm"

# Check if static folder exists
if (Test-Path "static") {
    Get-ChildItem -Path "static" -Recurse
} else {
    Write-Host "ERROR: static folder is MISSING!" -ForegroundColor Red
}
```

### Step 3: Create Static Folder If Missing

If the static folder doesn't exist, create it with the PWA files:

```powershell
# Create static directory
New-Item -ItemType Directory -Path "static" -Force

# Download the static files from the repository or create them
# The files needed are:
# - static/capture.html (PWA voice capture UI)
# - static/manifest.json (PWA manifest)
# - static/sw.js (Service worker)
```

I'll create the minimal files if they don't exist.

### Step 4: Check Database Connection String

The 500 errors are likely database connection issues. Verify the environment variables:

```powershell
# Check what env vars are set on the service
gcloud run services describe metapm --region=us-central1 --project=metapm --format="yaml(spec.template.spec.containers[0].env)"
```

Expected variables:
- `DB_SERVER` = `/cloudsql/super-flashcards-475210:us-central1:coreyscloud`
- `DB_NAME` = `MetaPM`
- `DB_USER` = `metapm_user`
- Secrets: `DB_PASSWORD`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`

### Step 5: Test Database Connection Locally (Optional)

If you have Cloud SQL Proxy installed:

```powershell
# Start Cloud SQL Proxy (in separate terminal)
cloud-sql-proxy super-flashcards-475210:us-central1:coreyscloud

# Test connection with sqlcmd or your preferred tool
```

### Step 6: Check Static Files in Git

```powershell
cd "G:\My Drive\Code\Python\metapm"

# Check what's tracked in git
git ls-files | Select-String "static"

# If static files are NOT in git, add them
git add static/
git status
```

### Step 7: Redeploy After Fixes

```powershell
# Commit any changes
git add .
git commit -m "Add static files for PWA"
git push origin main

# Redeploy
gcloud run deploy metapm `
    --source . `
    --region us-central1 `
    --project metapm `
    --service-account=metapm-cloud-run@metapm.iam.gserviceaccount.com `
    --allow-unauthenticated `
    --add-cloudsql-instances super-flashcards-475210:us-central1:coreyscloud `
    --set-secrets "DB_PASSWORD=metapm-db-password:latest,OPENAI_API_KEY=openai-api-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest" `
    --set-env-vars "DB_SERVER=/cloudsql/super-flashcards-475210:us-central1:coreyscloud,DB_NAME=MetaPM,DB_USER=metapm_user,GCP_PROJECT_ID=metapm,GCS_MEDIA_BUCKET=metapm-media"
```

### Step 8: Verify After Deployment

```powershell
$baseUrl = "https://metapm-67661554310.us-central1.run.app"

# Test health (should work)
Invoke-RestMethod -Uri "$baseUrl/health"

# Test static files
Invoke-WebRequest -Uri "$baseUrl/static/capture.html" -Method Head

# Test API
Invoke-RestMethod -Uri "$baseUrl/api/projects"
```

### Handoff Report

```markdown
## Debug Results

### Cloud Run Logs Error
[Paste the actual error message from logs]

### Static Files Status
- [ ] static/ folder exists
- [ ] capture.html present
- [ ] manifest.json present
- [ ] sw.js present
- [ ] Files committed to git

### Database Connection
- [ ] Env vars correct
- [ ] Cloud SQL instance accessible
- [ ] Secrets mounted

### After Redeployment
- [ ] /health returns 200
- [ ] /static/capture.html loads
- [ ] /api/projects returns data
```

---

## PROMPT END
