# VS Code Prompt: Diagnose and Complete Cloud Run Deployment

Copy this entire prompt to VS Code Copilot.

---

## PROMPT START

### Task: Diagnose Cloud Run Deployment Failure and Retry

**Project**: MetaPM  
**GCP Project ID**: metapm  
**Status**: All infrastructure ready, deployment failed on build

### Step 1: Check Recent Build Logs

```powershell
# List recent Cloud Build jobs
gcloud builds list --limit=5 --project=metapm

# Get details of the most recent (failed) build
$buildId = (gcloud builds list --limit=1 --format="value(id)" --project=metapm)
Write-Host "Most recent build: $buildId"

# View the build log
gcloud builds log $buildId --project=metapm
```

**Report what error you see** before proceeding. Common issues:
- `DEADLINE_EXCEEDED` → Build took too long, retry
- `CANCELLED` → User cancelled or quota hit
- `INTERNAL_ERROR` → GCP infra issue, retry
- Docker build error → Need to fix Dockerfile

### Step 2: Verify APIs Are Enabled

```powershell
# Check required APIs
gcloud services list --enabled --project=metapm | Select-String -Pattern "cloudbuild|run|artifactregistry"

# If artifactregistry is missing, enable it
gcloud services enable artifactregistry.googleapis.com --project=metapm
```

### Step 3: Verify Service Account Permissions

```powershell
# Check Cloud Build service account has needed roles
$projectNumber = gcloud projects describe metapm --format="value(projectNumber)"
Write-Host "Project number: $projectNumber"

# Cloud Build SA needs: Cloud Run Admin, Service Account User
gcloud projects get-iam-policy metapm --format=json | Select-String -Pattern "cloudbuild"
```

### Step 4: Retry Deployment with Verbose Output

```powershell
# Change to project directory
cd "G:\My Drive\Code\Python\metapm"

# Verify we're on correct GCP project
gcloud config get-value project
# Should output: metapm

# Retry deployment with verbose output
gcloud run deploy metapm `
    --source . `
    --region us-central1 `
    --project metapm `
    --service-account=metapm-cloud-run@metapm.iam.gserviceaccount.com `
    --allow-unauthenticated `
    --add-cloudsql-instances super-flashcards-475210:us-central1:coreyscloud `
    --set-secrets "DB_PASSWORD=metapm-db-password:latest,OPENAI_API_KEY=openai-api-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest" `
    --set-env-vars "DB_SERVER=/cloudsql/super-flashcards-475210:us-central1:coreyscloud,DB_NAME=MetaPM,DB_USER=metapm_user,GCP_PROJECT_ID=metapm,GCS_MEDIA_BUCKET=metapm-media" `
    --timeout=600 `
    --memory=512Mi `
    --cpu=1 `
    --verbosity=info
```

### Step 5: If Build Fails Again, Try Pre-Building Image

Sometimes `--source .` has issues. Try building explicitly:

```powershell
# Enable Artifact Registry if not done
gcloud services enable artifactregistry.googleapis.com --project=metapm

# Create a repository for Docker images
gcloud artifacts repositories create metapm-repo `
    --repository-format=docker `
    --location=us-central1 `
    --project=metapm

# Configure Docker auth
gcloud auth configure-docker us-central1-docker.pkg.dev

# Submit build manually
gcloud builds submit `
    --tag us-central1-docker.pkg.dev/metapm/metapm-repo/metapm:latest `
    --project=metapm `
    --timeout=1200

# If build succeeds, deploy from the image
gcloud run deploy metapm `
    --image us-central1-docker.pkg.dev/metapm/metapm-repo/metapm:latest `
    --region us-central1 `
    --project metapm `
    --service-account=metapm-cloud-run@metapm.iam.gserviceaccount.com `
    --allow-unauthenticated `
    --add-cloudsql-instances super-flashcards-475210:us-central1:coreyscloud `
    --set-secrets "DB_PASSWORD=metapm-db-password:latest,OPENAI_API_KEY=openai-api-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest" `
    --set-env-vars "DB_SERVER=/cloudsql/super-flashcards-475210:us-central1:coreyscloud,DB_NAME=MetaPM,DB_USER=metapm_user,GCP_PROJECT_ID=metapm,GCS_MEDIA_BUCKET=metapm-media"
```

### Step 6: Verify Deployment

```powershell
# Get the service URL
$serviceUrl = gcloud run services describe metapm --region=us-central1 --format="value(status.url)" --project=metapm
Write-Host "Service URL: $serviceUrl"

# Test health endpoint
Invoke-RestMethod -Uri "$serviceUrl/health"

# Test docs page
Start-Process "$serviceUrl/docs"
```

### Handoff Report Template

```markdown
## Deployment Complete

**Service URL**: [URL from step 6]
**Build ID**: [from gcloud builds list]

### Verification
- [ ] /health returns {"status": "healthy"}
- [ ] /docs loads Swagger UI
- [ ] /api/tasks returns 200

### If Issues Found
[Describe any errors and what was done to fix them]
```

---

## PROMPT END
