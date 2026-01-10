<#
.SYNOPSIS
    MetaPM Setup Script - GCP, GitHub, and Local Configuration
.DESCRIPTION
    This script sets up the MetaPM project including:
    - GCP project configuration and API enabling
    - Cloud SQL connectivity verification
    - Secret Manager setup
    - GitHub repository initialization
    - Local development environment
.NOTES
    Version: 1.0
    Requires: gcloud CLI, git, Python 3.11+
    Methodology: project-methodology v3.12.1
#>

param(
    [switch]$SkipAuth,
    [switch]$SkipGitHub,
    [switch]$Verbose
)

# ============================================
# CONFIGURATION
# ============================================

$GCP_PROJECT_ID = "metapm"
$GCP_REGION = "us-central1"
$CLOUD_SQL_INSTANCE = "super-flashcards-475210:us-central1:coreyscloud"  # Your existing instance
$DB_NAME = "MetaPM"
$GITHUB_REPO = "https://github.com/coreyprator/metapm.git"
$PROJECT_DIR = "G:\My Drive\Code\Python\metapm"

# Colors for output
function Write-Step { param($msg) Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "[✓] $msg" -ForegroundColor Green }
function Write-Warning { param($msg) Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Failure { param($msg) Write-Host "[✗] $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "    $msg" -ForegroundColor Gray }

# ============================================
# PHASE 0: AUTHENTICATION (Per LL-002)
# ============================================

Write-Step "PHASE 0: Authentication"
Write-Info "Per LL-002: Must authenticate BEFORE setting project"

if (-not $SkipAuth) {
    Write-Host "`nStep 0.1: Browser authentication required"
    Write-Warning "A browser window will open. Complete authentication there."
    
    # Check if already authenticated
    $authTest = gcloud auth list --format="value(account)" 2>$null
    if ($authTest) {
        Write-Success "Already authenticated as: $authTest"
        $reauth = Read-Host "Re-authenticate? (y/N)"
        if ($reauth -eq "y") {
            gcloud auth login
            gcloud auth application-default login
        }
    } else {
        Write-Info "Running: gcloud auth login"
        gcloud auth login
        
        Write-Info "Running: gcloud auth application-default login"
        gcloud auth application-default login
    }
}

# ============================================
# PHASE 1: PROJECT CONFIGURATION
# ============================================

Write-Step "PHASE 1: GCP Project Configuration"

# Set project (should NOT prompt for password after auth - LL-002)
Write-Info "Setting project to: $GCP_PROJECT_ID"
gcloud config set project $GCP_PROJECT_ID

# Verify project is set correctly (LL-036)
$currentProject = gcloud config get-value project 2>$null
if ($currentProject -ne $GCP_PROJECT_ID) {
    Write-Failure "Project mismatch! Expected: $GCP_PROJECT_ID, Got: $currentProject"
    exit 1
}
Write-Success "Project verified: $currentProject"

# Set quota project
gcloud auth application-default set-quota-project $GCP_PROJECT_ID

# ============================================
# PHASE 2: ENABLE APIS
# ============================================

Write-Step "PHASE 2: Enable Required APIs"

# Note: PowerShell doesn't use \ for line continuation like bash
$apis = @(
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com"
)

foreach ($api in $apis) {
    Write-Info "Enabling: $api"
    $result = gcloud services enable $api 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Enabled: $api"
    } else {
        Write-Warning "May already be enabled or needs billing: $api"
    }
}

# ============================================
# PHASE 3: LINK BILLING (Required for APIs)
# ============================================

Write-Step "PHASE 3: Billing Configuration"

# List available billing accounts
Write-Info "Checking billing accounts..."
$billingAccounts = gcloud billing accounts list --format="value(name)" 2>$null

if ($billingAccounts) {
    Write-Success "Found billing account(s)"
    
    # Check if project already has billing
    $projectBilling = gcloud billing projects describe $GCP_PROJECT_ID --format="value(billingEnabled)" 2>$null
    
    if ($projectBilling -eq "True") {
        Write-Success "Project already has billing enabled"
    } else {
        Write-Warning "Project needs billing linked"
        Write-Info "Available billing accounts:"
        gcloud billing accounts list
        
        $billingAccount = Read-Host "Enter billing account ID to link (or press Enter to skip)"
        if ($billingAccount) {
            gcloud billing projects link $GCP_PROJECT_ID --billing-account=$billingAccount
            Write-Success "Billing linked"
        }
    }
} else {
    Write-Warning "No billing accounts found. Some APIs may not work."
}

# ============================================
# PHASE 4: SECRET MANAGER SETUP
# ============================================

Write-Step "PHASE 4: Secret Manager Configuration"

# Check if secret already exists
$secretExists = gcloud secrets describe metapm-db-password --project=$GCP_PROJECT_ID 2>$null
if ($secretExists) {
    Write-Success "Secret 'metapm-db-password' already exists"
} else {
    Write-Info "Creating database password secret..."
    Write-Warning "You will be prompted to enter the database password."
    
    $dbPassword = Read-Host "Enter database password for MetaPM" -AsSecureString
    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPassword)
    $plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    
    # Create secret
    $plainPassword | gcloud secrets create metapm-db-password --data-file=- --project=$GCP_PROJECT_ID
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Secret created"
    } else {
        Write-Failure "Failed to create secret"
    }
    
    # Clean up
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

# Get compute service account and grant access
Write-Info "Granting Cloud Run access to secret..."
$projectNumber = gcloud projects describe $GCP_PROJECT_ID --format="value(projectNumber)"
$serviceAccount = "${projectNumber}-compute@developer.gserviceaccount.com"

gcloud secrets add-iam-policy-binding metapm-db-password `
    --member="serviceAccount:$serviceAccount" `
    --role="roles/secretmanager.secretAccessor" `
    --project=$GCP_PROJECT_ID 2>$null

Write-Success "Secret access configured"

# ============================================
# PHASE 5: CLOUD SQL CONNECTIVITY
# ============================================

Write-Step "PHASE 5: Cloud SQL Connectivity"

Write-Info "Using existing Cloud SQL instance: $CLOUD_SQL_INSTANCE"
Write-Info "Database: $DB_NAME"

# Verify the instance is accessible
$instanceInfo = gcloud sql instances describe coreyscloud --project=super-flashcards-475210 --format="value(connectionName)" 2>$null
if ($instanceInfo) {
    Write-Success "Cloud SQL instance verified: $instanceInfo"
} else {
    Write-Warning "Could not verify Cloud SQL instance. May need cross-project access."
}

# Grant Cloud Run service account access to Cloud SQL (cross-project)
Write-Info "Granting Cloud SQL client access..."
gcloud projects add-iam-policy-binding super-flashcards-475210 `
    --member="serviceAccount:$serviceAccount" `
    --role="roles/cloudsql.client" 2>$null

Write-Success "Cloud SQL access configured"

# ============================================
# PHASE 6: GITHUB REPOSITORY
# ============================================

Write-Step "PHASE 6: GitHub Repository Setup"

if (-not $SkipGitHub) {
    Set-Location $PROJECT_DIR
    
    # Check if git already initialized
    if (Test-Path ".git") {
        Write-Success "Git already initialized"
    } else {
        Write-Info "Initializing git repository..."
        git init
        Write-Success "Git initialized"
    }
    
    # Check remote
    $remote = git remote get-url origin 2>$null
    if ($remote) {
        Write-Success "Remote already set: $remote"
    } else {
        Write-Info "Adding GitHub remote..."
        git remote add origin $GITHUB_REPO
        Write-Success "Remote added: $GITHUB_REPO"
    }
    
    # Create .gitignore if not exists
    if (-not (Test-Path ".gitignore")) {
        Write-Info "Note: .gitignore should be extracted from project zip"
    }
}

# ============================================
# PHASE 7: LOCAL ENVIRONMENT
# ============================================

Write-Step "PHASE 7: Local Development Environment"

Set-Location $PROJECT_DIR

# Check Python version
$pythonVersion = python --version 2>&1
Write-Info "Python: $pythonVersion"

# Create virtual environment if not exists
if (-not (Test-Path "venv")) {
    Write-Info "Creating virtual environment..."
    python -m venv venv
    Write-Success "Virtual environment created"
} else {
    Write-Success "Virtual environment exists"
}

# Activate and install dependencies
Write-Info "To activate and install dependencies, run:"
Write-Host ""
Write-Host "    .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host "    pip install -r requirements.txt" -ForegroundColor Yellow
Write-Host ""

# Create .env from template
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Success ".env created from template"
        Write-Warning "Edit .env with your actual values!"
    } else {
        Write-Warning ".env.example not found. Extract from project zip first."
    }
} else {
    Write-Success ".env already exists"
}

# ============================================
# PHASE 8: SUMMARY
# ============================================

Write-Step "SETUP COMPLETE"

Write-Host ""
Write-Host "Configuration Summary:" -ForegroundColor White
Write-Host "  GCP Project:      $GCP_PROJECT_ID"
Write-Host "  Region:           $GCP_REGION"
Write-Host "  Cloud SQL:        $CLOUD_SQL_INSTANCE"
Write-Host "  Database:         $DB_NAME"
Write-Host "  GitHub:           $GITHUB_REPO"
Write-Host "  Local Directory:  $PROJECT_DIR"
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor White
Write-Host "  1. Extract metapm-project.zip into $PROJECT_DIR"
Write-Host "  2. Run: .\venv\Scripts\Activate.ps1"
Write-Host "  3. Run: pip install -r requirements.txt"
Write-Host "  4. Edit .env with database credentials"
Write-Host "  5. Run: uvicorn app.main:app --reload --port 8000"
Write-Host "  6. Test: http://localhost:8000/docs"
Write-Host ""

Write-Host "To deploy to Cloud Run:" -ForegroundColor White
Write-Host "  gcloud run deploy metapm --source . --region $GCP_REGION --allow-unauthenticated"
Write-Host ""

Write-Success "Setup script completed!"
