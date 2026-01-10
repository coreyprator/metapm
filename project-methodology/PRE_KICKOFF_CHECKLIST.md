# Pre-Kickoff Checklist

Complete this checklist before generating a project kickoff document.

---

## Project Lead Inputs Required

Before Claude can generate a kickoff document, the Project Lead must provide answers to these questions:

### 1. Project Identity

| Question | Your Answer |
|----------|-------------|
| Project name (human-readable)? | |
| Project slug (lowercase, hyphenated)? | |
| Brief description (1-2 sentences)? | |

### 2. GitHub Repository

| Question | Your Answer |
|----------|-------------|
| GitHub repo URL? | `https://github.com/coreyprator/` |
| Has the repo been created? | ☐ Yes ☐ No (I'll create it) |

### 3. GCP Project

| Question | Your Answer |
|----------|-------------|
| Use existing `super-flashcards-475210`? | ☐ Yes ☐ No (new project) |
| If new, what's the project ID? | |

**Guidance on GCP Project Selection:**

| Scenario | Recommendation |
|----------|----------------|
| Small/experimental project | Use shared `super-flashcards-475210` |
| Production application | Create dedicated project |
| Needs isolated billing | Create dedicated project |
| Shares database with other apps | Use shared project |

### 4. Database

| Question | Your Answer |
|----------|-------------|
| Use existing `flashcards-db` Cloud SQL instance? | ☐ Yes ☐ No (new instance) |
| Database name? | |
| Any special SQL Server features needed? | |

**Backup & Disaster Recovery** (Required for all databases):

| Question | Your Answer |
|----------|-------------|
| Backup retention period? | ☐ 7 days ☐ 14 days ☐ 30 days (recommended) |
| Backup window (UTC)? | Default: 03:00-04:00 UTC |
| Point-in-time recovery needed? | ☐ Yes (recommended) ☐ No |

> ⚠️ **Non-negotiable**: All production databases MUST have automated backups enabled before user testing.

### 5. External Services

| Question | Your Answer |
|----------|-------------|
| External APIs required? | |
| API keys available? | ☐ Yes ☐ Will obtain |
| OAuth needed (Google, GitHub, etc.)? | ☐ Yes ☐ No |
| OAuth credentials created? | ☐ Yes ☐ Will create |

### 6. Storage

| Question | Your Answer |
|----------|-------------|
| GCS bucket needed? | ☐ Yes ☐ No |
| Bucket name? | |
| Public or private access? | |

### 7. Domain

| Question | Your Answer |
|----------|-------------|
| Custom domain needed? | ☐ Yes ☐ No (use Cloud Run URL) |
| Domain name? | |
| SSL certificate source? | |

---

## Pre-Kickoff Verification

Before starting, verify these are complete:

### Authentication (Project Lead does this)

- [ ] Logged into Google Cloud Console in browser
- [ ] GitHub authenticated with Passkey
- [ ] VS Code signed into GitHub

### GCP Authentication (Run in terminal)

```powershell
# Run these commands in order:
gcloud auth login
gcloud auth application-default login
gcloud config set project [YOUR_PROJECT_ID]
gcloud auth application-default set-quota-project [YOUR_PROJECT_ID]

# Verify:
gcloud config get-value project
```

> ⚠️ If `gcloud config set project` prompts for a password, STOP and run `gcloud auth login` again.

### Repository (if creating new)

- [ ] GitHub repo created at github.com
- [ ] Repo is empty (no README, no .gitignore)
- [ ] Visibility set (public/private)

### OAuth (if needed)

- [ ] Google Cloud Console → APIs & Services → Credentials
- [ ] OAuth 2.0 Client ID created
- [ ] Authorized redirect URIs will include Cloud Run URL (add after first deploy)

---

## Ready for Kickoff

Once all questions are answered and verifications complete:

**Command to Claude:**
> "Generate kickoff for [PROJECT_NAME] with these inputs:
> - GitHub: [URL]
> - GCP Project: [ID]
> - Database: [name] on [instance]
> - External APIs: [list]
> - Storage: [bucket or none]
> - Domain: [custom or Cloud Run]"

Claude will then generate:
1. Customized PROJECT_KICKOFF document
2. TEST_PLAN.md
3. UI_DESIGN.md  
4. USER_GUIDE.md

---

## Quick Reference: Common Configurations

### Configuration A: Simple API (shared infrastructure)
```
GCP Project: super-flashcards-475210
SQL Instance: flashcards-db
Database: [project-name]
Storage: None
Domain: Cloud Run URL
```

### Configuration B: Full Application (dedicated)
```
GCP Project: [project-name]-prod
SQL Instance: [project-name]-db
Database: [project-name]
Storage: [project-name]-assets
Domain: [project-name].example.com
```

### Configuration C: AI/ML Application (shared + storage)
```
GCP Project: super-flashcards-475210
SQL Instance: flashcards-db
Database: [project-name]
Storage: [project-name]-generated
Domain: Cloud Run URL
```
