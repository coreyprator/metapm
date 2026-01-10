# MetaPM - Meta Project Manager

**Cross-project task management system with AI integration**

## Overview

MetaPM is a centralized command center for managing Corey Prator's 2026 personal projects. It provides:

- **Unified Task Management** — Single source of truth across 21+ projects
- **Cross-Project Linking** — Tasks can relate to multiple projects (e.g., PIE etymology in both Super-Flashcards and Etymython)
- **Methodology Enforcement** — Pre-written prompts for common VS Code Copilot violations
- **Mobile Voice Capture** — Quick task entry via speech-to-text
- **Sprint Integration** — Track and sequence sprint tasks

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11+ / FastAPI |
| Database | MS SQL Server (GCP Cloud SQL) |
| Deployment | GCP Cloud Run |
| CI/CD | GitHub Actions |
| Auth | API Key (initial), OAuth 2.0 (future) |

## Project Registry

This system manages the following projects:

| Code | Project | Theme | Status |
|------|---------|-------|--------|
| AF | ArtForge | A: Creation | Active |
| EM | Etymython | B: Learning | Active |
| HL | HarmonyLab | B: Learning | Active |
| SF | Super-Flashcards | B: Learning | Active |
| META | Meta Project Manager | Cross-Cutting | Active |
| CUBIST | Cubist Art Software | A: Creation | Active |
| VID-* | Video Projects (6) | A: Creation | Various |
| TRIP-* | Travel Projects (4) | C: Adventure | Various |
| LANG-* | Language Learning (2) | B: Learning | Active |
| MUSIC-JAZZ | Jazz Piano | B: Learning | Active |
| DIPSTERS | DIPster Engagement | D: Relationships | Active |

## Directory Structure

```
metapm/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   ├── tasks.py         # Task CRUD endpoints
│   │   ├── projects.py      # Project endpoints
│   │   ├── categories.py    # Category management
│   │   ├── methodology.py   # Methodology rules & violations
│   │   └── capture.py       # Quick capture endpoint for mobile
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Settings and environment
│   │   ├── database.py      # SQL Server connection
│   │   └── security.py      # API key validation
│   ├── models/
│   │   ├── __init__.py
│   │   ├── task.py          # Task Pydantic models
│   │   ├── project.py       # Project models
│   │   └── methodology.py   # Methodology rule models
│   └── services/
│       ├── __init__.py
│       ├── task_service.py  # Business logic for tasks
│       └── methodology_service.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   ├── test_tasks.py
│   └── test_capture.py
├── scripts/
│   ├── schema.sql           # Database schema
│   └── seed_data.sql        # Initial data
├── docs/
│   ├── METHODOLOGY.md       # Project methodology rules
│   └── API.md               # API documentation
├── .env.example             # Environment template
├── .gitignore
├── Dockerfile
├── requirements.txt
├── cloudbuild.yaml          # GCP Cloud Build config
└── README.md
```

## API Endpoints

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tasks` | List tasks with filters |
| GET | `/api/tasks/{id}` | Get single task |
| POST | `/api/tasks` | Create task |
| PUT | `/api/tasks/{id}` | Update task |
| DELETE | `/api/tasks/{id}` | Delete task |
| POST | `/api/tasks/capture` | Quick capture (mobile) |

### Query Parameters for GET /api/tasks

- `status` — Filter by status (NEW, STARTED, BLOCKED, COMPLETE)
- `priority` — Filter by priority (1-5)
- `project` — Filter by project code (e.g., `EM`, `AF`)
- `category` — Filter by category code (e.g., `BUG`, `ACTION`)
- `overdue` — Boolean, show only overdue tasks
- `no_due_date` — Boolean, show tasks without due dates
- `cross_project` — Boolean, show tasks linked to multiple projects

### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects` | List all projects |
| GET | `/api/projects/{code}` | Get project with tasks |
| GET | `/api/projects/{code}/next` | Get next sprint task |

### Methodology

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/methodology/rules` | List all rules |
| GET | `/api/methodology/rules/{code}` | Get rule with violation prompt |
| POST | `/api/methodology/violations` | Log a violation |
| GET | `/api/methodology/violations/summary` | Violation statistics |

## Quick Capture API

Designed for mobile/voice input with minimal required fields:

```bash
POST /api/tasks/capture
Content-Type: application/json

{
  "title": "Add PIE etymology to flashcard system",
  "project": "SF",        # Optional - project code
  "category": "IDEA"      # Optional - defaults to IDEA
}
```

Returns the created task with ID for confirmation.

## Environment Variables

```bash
# Database
DB_SERVER=<cloud-sql-ip-or-connection>
DB_NAME=MetaPM
DB_USER=sqlserver
DB_PASSWORD=<password>

# GCP
GCP_PROJECT_ID=<project-id>
CLOUD_SQL_INSTANCE=<project:region:instance>

# Security
API_KEY=<generated-api-key>

# Optional
LOG_LEVEL=INFO
ENVIRONMENT=development
```

## Local Development

```bash
# Clone repository
git clone https://github.com/<username>/metapm.git
cd metapm

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your values

# Run locally
uvicorn app.main:app --reload --port 8000
```

## Deployment

### GCP Cloud Run

```bash
# Build and deploy
gcloud builds submit --config cloudbuild.yaml

# Or manual deploy
gcloud run deploy metapm \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances $CLOUD_SQL_INSTANCE \
  --set-env-vars "DB_SERVER=/cloudsql/$CLOUD_SQL_INSTANCE,DB_NAME=MetaPM"
```

## Methodology Rules (Summary)

These rules are stored in the database and can be retrieved via API:

| Code | Name | Severity |
|------|------|----------|
| TEST-HUMAN-VISIBLE | Verify Human-Visible Functionality | CRITICAL |
| NO-UNTESTED-CODE | No Untested Code Handoff | CRITICAL |
| SPRINT-TASK-SEQUENCE | Follow Sprint Task Sequence | HIGH |
| DB-CONNECTION-VERIFY | Verify Database Connections | HIGH |

When VS Code Copilot violates a rule:
1. Call `GET /api/methodology/rules/{code}`
2. Copy the `violation_prompt` field
3. Paste into Copilot Chat
4. Optionally log the violation via `POST /api/methodology/violations`

## Cross-Project Task Example

A task like "Add PIE etymology" benefits both Super-Flashcards and Etymython:

```bash
POST /api/tasks
{
  "title": "Add PIE (Proto-Indo-European) etymology data from Wiktionary",
  "description": "Research and add PIE roots to enhance etymology learning",
  "priority": 2,
  "projects": ["SF", "EM"],  # Links to both projects
  "categories": ["REQUIREMENT", "RESEARCH"]
}
```

## Sprint 1 Goals

1. ✅ Database schema deployed
2. ⬜ FastAPI project scaffold
3. ⬜ Core CRUD endpoints for Tasks
4. ⬜ Quick capture endpoint
5. ⬜ Deploy to Cloud Run
6. ⬜ Basic mobile web UI for capture

---

## For VS Code Copilot

**IMPORTANT:** When working on this project, always:

1. **Test before handoff** — Never provide untested code
2. **Verify human-visible behavior** — Tests must confirm what users actually see
3. **Follow sprint sequence** — After completing a task, check for the next one
4. **Reference methodology** — When uncertain, check `/docs/METHODOLOGY.md`

**Database Connection:** This project uses MS SQL Server via `pyodbc`. Always use parameterized queries to prevent SQL injection.

**Project Pattern:** This follows the same architecture as Etymython and Super-Flashcards. Reference those projects for established patterns.
