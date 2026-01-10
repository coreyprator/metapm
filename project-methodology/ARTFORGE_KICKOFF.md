# ArtForge Project Kickoff

**Project**: ArtForge  
**Generated**: December 2024  
**Methodology Version**: 3.5

---

## Project Overview

ArtForge is an RLHF-driven art discovery engine that generates images across 53 artistic styles and uses human feedback to optimize the generation parameters over time.

### Key Features
- Generate images in 53 distinct art styles
- Rate and compare generated images
- Algorithm learns from user preferences (RLHF)
- Collection management for saved images
- Style exploration and discovery

---

## Document Variables

| Variable | Value |
|----------|-------|
| `PROJECT_NAME` | ArtForge |
| `PROJECT_SLUG` | artforge |
| `GCP_PROJECT_ID` | super-flashcards-475210 |
| `GITHUB_REPO` | coreyprator/artforge |
| `SQL_INSTANCE` | flashcards-db |
| `SQL_INSTANCE_IP` | [Instance IP] |
| `DATABASE_NAME` | artforge |
| `GCS_BUCKET` | artforge-images |

---

## Phase 0: Pre-Kickoff Setup

### 0.1 Authentication Flow

```powershell
# Step 1: Browser authentication with Passkey
gcloud auth login

# Step 2: Application default credentials
gcloud auth application-default login

# Step 3: Set project
gcloud config set project super-flashcards-475210

# Step 4: Set quota project
gcloud auth application-default set-quota-project super-flashcards-475210

# Verify
gcloud config get-value project
# Expected: super-flashcards-475210
```

### 0.2 Pre-Kickoff Checklist

- [x] GitHub repo: https://github.com/coreyprator/artforge
- [x] GCP project: super-flashcards-475210 (shared)
- [x] Database: artforge on flashcards-db instance
- [x] External APIs: OpenAI (DALL-E 3) - key available
- [x] Storage: artforge-images bucket
- [x] Domain: Cloud Run URL (no custom domain)

---

## Phase 1: Architecture

### 1.1 System Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Frontend      │────▶│   FastAPI       │────▶│   Cloud SQL     │
│   (React)       │     │   Backend       │     │   (SQL Server)  │
│                 │     │                 │     │                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │                 │     │                 │
                        │   OpenAI API    │     │   GCS Bucket    │
                        │   (DALL-E 3)    │     │   (Images)      │
                        │                 │     │                 │
                        └─────────────────┘     └─────────────────┘
```

### 1.2 Database Schema

```sql
-- ArtForge Database Schema
-- Execute in SSMS (contains GO statements)

USE master;
GO

IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'artforge')
BEGIN
    CREATE DATABASE artforge;
END
GO

USE artforge;
GO

-- Art Styles (53 predefined styles)
CREATE TABLE art_styles (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    description NVARCHAR(500),
    prompt_modifier NVARCHAR(1000) NOT NULL,
    category NVARCHAR(50),
    created_at DATETIME2 DEFAULT GETUTCDATE()
);
GO

-- Generated Images
CREATE TABLE images (
    id INT IDENTITY(1,1) PRIMARY KEY,
    style_id INT NOT NULL FOREIGN KEY REFERENCES art_styles(id),
    prompt NVARCHAR(2000) NOT NULL,
    gcs_path NVARCHAR(500) NOT NULL,
    generation_params NVARCHAR(MAX), -- JSON
    created_at DATETIME2 DEFAULT GETUTCDATE()
);
GO

-- User Ratings (RLHF data)
CREATE TABLE ratings (
    id INT IDENTITY(1,1) PRIMARY KEY,
    image_id INT NOT NULL FOREIGN KEY REFERENCES images(id),
    rating INT CHECK (rating BETWEEN 1 AND 5),
    comparison_winner_id INT FOREIGN KEY REFERENCES images(id),
    feedback_type NVARCHAR(20) NOT NULL, -- 'rating' or 'comparison'
    created_at DATETIME2 DEFAULT GETUTCDATE()
);
GO

-- Collections
CREATE TABLE collections (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    description NVARCHAR(500),
    created_at DATETIME2 DEFAULT GETUTCDATE()
);
GO

-- Collection Items
CREATE TABLE collection_items (
    id INT IDENTITY(1,1) PRIMARY KEY,
    collection_id INT NOT NULL FOREIGN KEY REFERENCES collections(id),
    image_id INT NOT NULL FOREIGN KEY REFERENCES images(id),
    added_at DATETIME2 DEFAULT GETUTCDATE(),
    UNIQUE(collection_id, image_id)
);
GO

-- RLHF Model Parameters
CREATE TABLE rlhf_parameters (
    id INT IDENTITY(1,1) PRIMARY KEY,
    style_id INT NOT NULL FOREIGN KEY REFERENCES art_styles(id),
    parameter_name NVARCHAR(100) NOT NULL,
    parameter_value FLOAT NOT NULL,
    confidence FLOAT,
    updated_at DATETIME2 DEFAULT GETUTCDATE()
);
GO
```

### 1.3 API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | /health | Health check | No |
| GET | /api/v1/styles | List all art styles | No |
| GET | /api/v1/styles/{id} | Get style details | No |
| POST | /api/v1/generate | Generate image | No |
| GET | /api/v1/images | List generated images | No |
| GET | /api/v1/images/{id} | Get image details | No |
| POST | /api/v1/ratings | Submit rating | No |
| POST | /api/v1/comparisons | Submit comparison | No |
| GET | /api/v1/collections | List collections | No |
| POST | /api/v1/collections | Create collection | No |
| POST | /api/v1/collections/{id}/images | Add image to collection | No |
| DELETE | /api/v1/collections/{id}/images/{image_id} | Remove from collection | No |

### 1.4 External Integrations

| Service | Purpose | Secret Name |
|---------|---------|-------------|
| OpenAI API | DALL-E 3 image generation | artforge-openai-key |
| GCS | Image storage | (uses default credentials) |

### 1.5 GCP Resources

| Resource | Name | Notes |
|----------|------|-------|
| Cloud Run | artforge | us-central1 |
| Cloud SQL | artforge | On flashcards-db instance |
| Secret Manager | artforge-* | All project secrets |
| GCS Bucket | artforge-images | Public read for images |

---

## Phase 2: Sprint 1 Tasks

### 2.1 Database Setup

```sql
-- Create database user (run in SSMS)
USE master;
GO

CREATE LOGIN artforge_user WITH PASSWORD = '[SECURE_PASSWORD]';
GO

USE artforge;
GO

CREATE USER artforge_user FOR LOGIN artforge_user;
ALTER ROLE db_datareader ADD MEMBER artforge_user;
ALTER ROLE db_datawriter ADD MEMBER artforge_user;
GO
```

### 2.2 Secret Manager Setup

```powershell
# Database connection string
echo -n "DRIVER={ODBC Driver 18 for SQL Server};SERVER=[INSTANCE_IP];DATABASE=artforge;UID=artforge_user;PWD=[PASSWORD];TrustServerCertificate=yes" | `
gcloud secrets create artforge-db-connection --data-file=-

# OpenAI API key
echo -n "[OPENAI_API_KEY]" | `
gcloud secrets create artforge-openai-key --data-file=-

# Grant Cloud Run access
$PROJECT_NUMBER = (gcloud projects describe super-flashcards-475210 --format="value(projectNumber)")

gcloud secrets add-iam-policy-binding artforge-db-connection `
    --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" `
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding artforge-openai-key `
    --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" `
    --role="roles/secretmanager.secretAccessor"
```

### 2.3 GCS Bucket Setup

```powershell
# Create bucket
gcloud storage buckets create gs://artforge-images --location=us-central1

# Make objects publicly readable
gcloud storage buckets add-iam-policy-binding gs://artforge-images `
    --member="allUsers" `
    --role="roles/storage.objectViewer"
```

### 2.4 Project Structure

```
artforge/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── styles.py
│   │   ├── images.py
│   │   ├── ratings.py
│   │   └── collections.py
│   └── services/
│       ├── __init__.py
│       ├── openai_service.py
│       ├── storage_service.py
│       └── rlhf_service.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_styles.py
│   ├── test_images.py
│   ├── test_ratings.py
│   └── test_collections.py
├── static/
│   └── (React build output)
├── .github/
│   └── workflows/
│       └── deploy.yml
├── Dockerfile
├── requirements.txt
├── .gitignore
└── README.md
```

### 2.5 GitHub Actions Workflow

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
          gcloud run deploy artforge \
            --source . \
            --region us-central1 \
            --allow-unauthenticated \
            --set-secrets="DB_CONNECTION=artforge-db-connection:latest,OPENAI_API_KEY=artforge-openai-key:latest"
```

---

## Phase 3: Sprint 1 Definition of Done

- [ ] Database `artforge` created with all tables
- [ ] Database user `artforge_user` created with permissions
- [ ] Secrets stored: `artforge-db-connection`, `artforge-openai-key`
- [ ] GCS bucket `artforge-images` created with public read
- [ ] All API endpoints accessible on Cloud Run URL
- [ ] Image generation working via OpenAI API
- [ ] Images stored successfully in GCS
- [ ] Database CRUD operations succeed
- [ ] GitHub Actions deploys successfully
- [ ] TEST_PLAN.md created
- [ ] UI_DESIGN.md created
- [ ] USER_GUIDE.md created

---

## Phase 4: Sprint 2 Overview

Sprint 2 will focus on:

1. **Testing**: Implement pytest suite per TEST_PLAN.md
2. **Frontend**: Build React UI per UI_DESIGN.md
3. **RLHF Algorithm**: Implement learning from ratings
4. **Documentation**: Finalize USER_GUIDE.md
5. **Polish**: Error messages, loading states, empty states

---

## Appendix: Art Style Categories

| Category | Count | Examples |
|----------|-------|----------|
| Classical | 8 | Renaissance, Baroque, Impressionism |
| Modern | 10 | Cubism, Surrealism, Abstract Expressionism |
| Digital | 12 | Pixel Art, Vaporwave, Cyberpunk |
| Traditional | 8 | Watercolor, Oil Painting, Charcoal |
| Cultural | 10 | Japanese Ukiyo-e, Art Nouveau, Art Deco |
| Experimental | 5 | Glitch Art, Generative, Fractal |

**Total**: 53 styles

---

## Reference Commands

```powershell
# Get Cloud Run URL
gcloud run services describe artforge --region=us-central1 --format="value(status.url)"

# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=artforge" --limit=50

# Test health endpoint
$URL = (gcloud run services describe artforge --region=us-central1 --format="value(status.url)")
curl "$URL/health"
```

---

**Methodology**: [coreyprator/project-methodology](https://github.com/coreyprator/project-methodology) v3.5
