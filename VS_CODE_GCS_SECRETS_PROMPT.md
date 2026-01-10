# VS Code Prompt: GCS Bucket and Secret Manager Setup

Copy this entire prompt to VS Code Copilot.

---

## PROMPT START

### Task: Set up GCS Media Bucket and API Key Secrets for MetaPM

**Project**: MetaPM  
**GCP Project ID**: metapm  
**Methodology**: All secrets in Google Secret Manager, NOT .env files

### Prerequisites Verified

- [x] GCP project 'metapm' exists
- [x] User is authenticated (`gcloud auth login` completed)
- [x] Project is set (`gcloud config get-value project` returns 'metapm')
- [x] APIs enabled (secretmanager.googleapis.com, storage.googleapis.com)

### Task 1: Create GCS Bucket for Media Storage

Create a bucket to store audio recordings and images.

```powershell
# Create the media bucket
gcloud storage buckets create gs://metapm-media --location=us-central1 --project=metapm

# Verify bucket was created
gcloud storage buckets list --project=metapm
```

Grant Cloud Run service account access to the bucket:

```powershell
# Get the project number
$projectNumber = gcloud projects describe metapm --format="value(projectNumber)"
Write-Host "Project number: $projectNumber"

# Grant storage access to Cloud Run service account
gcloud storage buckets add-iam-policy-binding gs://metapm-media `
    --member="serviceAccount:${projectNumber}-compute@developer.gserviceaccount.com" `
    --role="roles/storage.objectAdmin"

# Verify the IAM binding
gcloud storage buckets get-iam-policy gs://metapm-media
```

### Task 2: Add OpenAI API Key to Secret Manager

The user will provide the OpenAI API key. Store it in Secret Manager.

```powershell
# Prompt user for the key (they will paste it)
$openaiKey = Read-Host "Enter your OpenAI API key (starts with sk-)"

# Create the secret
$openaiKey | gcloud secrets create openai-api-key --data-file=- --project=metapm

# Verify secret was created
gcloud secrets describe openai-api-key --project=metapm

# Grant Cloud Run access to the secret
$projectNumber = gcloud projects describe metapm --format="value(projectNumber)"
gcloud secrets add-iam-policy-binding openai-api-key `
    --member="serviceAccount:${projectNumber}-compute@developer.gserviceaccount.com" `
    --role="roles/secretmanager.secretAccessor" `
    --project=metapm
```

### Task 3: Add Anthropic API Key to Secret Manager

The user will provide the Anthropic API key.

```powershell
# Prompt user for the key (they will paste it)
$anthropicKey = Read-Host "Enter your Anthropic API key (starts with sk-ant-)"

# Create the secret
$anthropicKey | gcloud secrets create anthropic-api-key --data-file=- --project=metapm

# Verify secret was created
gcloud secrets describe anthropic-api-key --project=metapm

# Grant Cloud Run access to the secret
$projectNumber = gcloud projects describe metapm --format="value(projectNumber)"
gcloud secrets add-iam-policy-binding anthropic-api-key `
    --member="serviceAccount:${projectNumber}-compute@developer.gserviceaccount.com" `
    --role="roles/secretmanager.secretAccessor" `
    --project=metapm
```

### Task 4: Verify All Secrets Exist

```powershell
# List all secrets in the project
gcloud secrets list --project=metapm

# Expected output should show:
# - metapm-db-password
# - openai-api-key
# - anthropic-api-key
```

### Task 5: Update Cloud Run Deployment to Use Secrets

When deploying, secrets should be mounted as environment variables:

```powershell
gcloud run deploy metapm `
    --source . `
    --region us-central1 `
    --project metapm `
    --allow-unauthenticated `
    --add-cloudsql-instances super-flashcards-475210:us-central1:coreyscloud `
    --set-secrets "DB_PASSWORD=metapm-db-password:latest,OPENAI_API_KEY=openai-api-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest" `
    --set-env-vars "DB_SERVER=/cloudsql/super-flashcards-475210:us-central1:coreyscloud,DB_NAME=MetaPM,DB_USER=metapm_user,GCP_PROJECT_ID=metapm,GCS_MEDIA_BUCKET=metapm-media"
```

### Verification Checklist

After completing all tasks, verify:

- [ ] `gcloud storage buckets list` shows `gs://metapm-media`
- [ ] `gcloud secrets list` shows all 3 secrets
- [ ] Each secret has IAM binding for compute service account

### Handoff Report

Provide this report when complete:

```markdown
## GCS and Secret Manager Setup Complete

### GCS Bucket
- Bucket: gs://metapm-media
- Location: us-central1
- IAM: [service-account] has roles/storage.objectAdmin

### Secrets Created
| Secret Name | Status | IAM Configured |
|-------------|--------|----------------|
| metapm-db-password | ✅ Exists | ✅ Yes |
| openai-api-key | ✅ Created | ✅ Yes |
| anthropic-api-key | ✅ Created | ✅ Yes |

### Ready for Deployment
Cloud Run can now access all secrets via --set-secrets flag.
```

---

## PROMPT END
