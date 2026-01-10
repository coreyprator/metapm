# Deployment Checklist

Verify GCP resources and deployment status.

---

## Pre-Deployment Verification

> ⚠️ **CRITICAL**: Wrong project = broken deployment. Verify BEFORE every deploy.

### GCP Project Verification

```powershell
# ALWAYS run this first - before any deploy command
gcloud config get-value project
# Must output: [YOUR_PROJECT_ID]

# If wrong, fix it immediately:
gcloud config set project [YOUR_PROJECT_ID]
```

**Do not proceed if project is wrong.**

### GCP Authentication
```powershell
# Verify correct project (again - it's that important)
gcloud config get-value project
# Expected: [YOUR_PROJECT_ID]

# Verify authenticated account
gcloud auth list
# Should show your account with asterisk (active)
```

- [ ] **Correct GCP project selected** (verified with `gcloud config get-value project`)
- [ ] Authenticated with correct account

### Required APIs Enabled
```powershell
# Check enabled APIs
gcloud services list --enabled --filter="NAME:(run OR sql OR secretmanager OR cloudbuild)"
```

- [ ] Cloud Run API enabled
- [ ] Cloud SQL Admin API enabled
- [ ] Secret Manager API enabled
- [ ] Cloud Build API enabled

---

## Database Verification

### Cloud SQL Instance
```powershell
# List instances
gcloud sql instances list

# Get instance details
gcloud sql instances describe [INSTANCE_NAME]
```

- [ ] Cloud SQL instance exists and is running
- [ ] Instance IP address noted

### Database & User
```sql
-- Run in SSMS connected to Cloud SQL
SELECT name FROM sys.databases WHERE name = '[DATABASE_NAME]';
SELECT name FROM sys.server_principals WHERE name = '[USER_NAME]';
```

- [ ] Database exists
- [ ] Database user exists
- [ ] User has correct permissions (db_datareader, db_datawriter)

### Backup Configuration
```powershell
# Verify backup settings
gcloud sql instances describe [INSTANCE_NAME] --format="yaml(settings.backupConfiguration)"

# List recent backups
gcloud sql backups list --instance=[INSTANCE_NAME] --limit=5
```

- [ ] Automated backups enabled (`enabled: true`)
- [ ] Point-in-time recovery enabled (`pointInTimeRecoveryEnabled: true`)
- [ ] Retention period set (minimum 7 days)
- [ ] At least one successful backup exists
- [ ] Most recent backup completed within last 24 hours

> ⚠️ **CRITICAL**: Do not proceed to production without verified backups.

---

## Secret Manager Verification

### Secrets Exist
```powershell
# List project secrets
gcloud secrets list --filter="name:[PROJECT_SLUG]"
```

Expected secrets:
- [ ] `[PROJECT_SLUG]-db-connection` - Database connection string
- [ ] `[PROJECT_SLUG]-*` - Any additional secrets (API keys, OAuth, etc.)

### IAM Bindings
```powershell
# Check IAM policy for each secret
gcloud secrets get-iam-policy [SECRET_NAME]
```

- [ ] Compute service account has `secretmanager.secretAccessor` role
- [ ] Service account format: `[PROJECT_NUMBER]-compute@developer.gserviceaccount.com`

### Secret Content (Optional Verification)
```powershell
# Read secret value (be careful with sensitive output)
gcloud secrets versions access latest --secret=[SECRET_NAME]
```

- [ ] Connection string format is correct
- [ ] Credentials are valid

---

## GitHub Actions Verification

### Repository Secrets
In GitHub repo → Settings → Secrets and variables → Actions:

- [ ] `WIF_PROVIDER` - Workload Identity Federation provider
- [ ] `WIF_SERVICE_ACCOUNT` - GCP service account email

### Workflow File
- [ ] `.github/workflows/deploy.yml` exists
- [ ] Triggers on push to main
- [ ] Uses correct service and region

---

## Cloud Run Verification

### Service Status
```powershell
# List Cloud Run services
gcloud run services list --region=us-central1

# Get service details
gcloud run services describe [SERVICE_NAME] --region=us-central1
```

- [ ] Service exists
- [ ] Service is in us-central1 (or expected region)
- [ ] Latest revision is serving traffic

### Service URL
```powershell
# Get URL
gcloud run services describe [SERVICE_NAME] --region=us-central1 --format="value(status.url)"
```

- [ ] URL is accessible
- [ ] URL format: `https://[SERVICE]-xxxxxxxxxx-uc.a.run.app`

### Health Check
```powershell
$URL = "[CLOUD_RUN_URL]"
curl "$URL/health"
```

- [ ] Returns 200 OK
- [ ] Response indicates healthy status

---

## Application Verification

### API Endpoints
```powershell
# Health check
curl "[URL]/health"

# API endpoint (adjust as needed)
curl "[URL]/api/v1/status"
```

- [ ] Health endpoint responds
- [ ] API endpoints respond correctly
- [ ] Authentication works (if applicable)

### Database Connectivity
```powershell
# Check logs for database connection
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=[SERVICE_NAME] AND textPayload:database" --limit=10
```

- [ ] No database connection errors in logs
- [ ] Queries execute successfully

### Secret Access
```powershell
# Check logs for secret access
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=[SERVICE_NAME] AND textPayload:secret" --limit=10
```

- [ ] No "secret not found" errors
- [ ] No permission denied errors

---

## Logging & Monitoring

### View Recent Logs
```powershell
# All logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=[SERVICE_NAME]" --limit=50

# Errors only
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=[SERVICE_NAME] AND severity>=ERROR" --limit=20
```

- [ ] No unexpected errors
- [ ] Application starts correctly
- [ ] Requests are being processed

### Cloud Console
- [ ] Cloud Run → Service → Metrics showing traffic
- [ ] Cloud Run → Service → Logs accessible
- [ ] Cloud SQL → Instance → Connections showing activity

---

## Post-Deployment Tasks

### OAuth Redirect URIs (if applicable)
After first deployment, update OAuth credentials:

1. Go to Google Cloud Console → APIs & Services → Credentials
2. Edit OAuth 2.0 Client ID
3. Add Cloud Run URL to Authorized redirect URIs

- [ ] OAuth redirect URI updated with Cloud Run URL

### Custom Domain (if applicable)
```powershell
gcloud run domain-mappings create --service=[SERVICE_NAME] --domain=[CUSTOM_DOMAIN] --region=us-central1
```

- [ ] Domain mapping created
- [ ] DNS records configured
- [ ] SSL certificate provisioned

### Monitoring Setup (optional)
- [ ] Uptime check configured in Cloud Monitoring
- [ ] Alert policies for errors/latency
- [ ] Dashboard created for key metrics

---

## Troubleshooting Quick Reference

| Symptom | Check | Common Fix |
|---------|-------|------------|
| 502 Bad Gateway | Container startup | Check Dockerfile, verify dependencies |
| Secret not found | IAM binding | Add secretAccessor role to service account |
| Database timeout | Network/IP | Verify Cloud SQL authorized networks |
| 401 Unauthorized | Auth config | Check OAuth setup, token validation |
| Slow cold start | Container size | Optimize Dockerfile, reduce dependencies |

### Useful Commands
```powershell
# Force new deployment
gcloud run deploy [SERVICE_NAME] --source . --region=us-central1

# View build logs
gcloud builds list --limit=5
gcloud builds log [BUILD_ID]

# Describe latest revision
gcloud run revisions list --service=[SERVICE_NAME] --region=us-central1

# Check service account permissions
gcloud projects get-iam-policy [PROJECT_ID] --flatten="bindings[].members" --filter="bindings.members:[SERVICE_ACCOUNT]"
```

---

## Deployment Complete

All verification checks passed:
- [ ] GCP resources provisioned correctly
- [ ] Secrets accessible
- [ ] Database connected
- [ ] Application responding
- [ ] No errors in logs

**Deployment successful!** ✅
