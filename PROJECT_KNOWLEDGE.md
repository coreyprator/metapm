# MetaPM -- Project Knowledge Document
Generated: 2026-02-15 by CC Session
Updated: 2026-02-20 — Sprint "MP-023 Roadmap API + Dashboard Fixes" (v2.3.1 in progress)
Purpose: Canonical reference for all AI sessions working on this project.

---

## 1. PROJECT IDENTITY

**Name**: MetaPM (Meta Project Manager)
**Description**: Cross-project task management system and meta-dashboard for tracking health and status across all of Corey Prator's 2026 personal projects. It is the "command center" that manages 21+ projects spanning software, travel, music, art, and language learning.
**Repository**: github.com/coreyprator/metapm
**Custom Domain**: https://metapm.rentyourcio.com
**Cloud Run URL**: https://metapm-67661554310.us-central1.run.app (legacy; use custom domain)
**Current Version**: v2.3.1 (per `app/core/config.py` line 15)
**Latest Known Revision**: metapm-v2-00080-22r _(Source: SESSION_CLOSEOUT_2026-02-19_MP022.md — deployed 2026-02-19)_
**Owner**: Corey Prator

### Tech Stack
| Component | Technology | Source |
|-----------|------------|--------|
| Language | Python 3.11 | `Dockerfile` line 5 |
| Web Framework | FastAPI 0.109.2 | `requirements.txt` line 4 |
| ASGI Server | Uvicorn 0.27.1 + Gunicorn 21.2.0 | `requirements.txt` lines 5, 25 |
| Database | MS SQL Server (GCP Cloud SQL) via pyodbc 5.0.1 | `requirements.txt` line 10 |
| ORM/Query | Raw SQL via pyodbc (no ORM) | `app/core/database.py` |
| Validation | Pydantic 2.6.1 + pydantic-settings 2.1.0 | `requirements.txt` lines 6-7 |
| Deployment | GCP Cloud Run | `CLAUDE.md` line 66 |
| CI/CD | Cloud Build (cloudbuild.yaml, currently tests disabled) | `cloudbuild.yaml` |
| GCS Integration | google-cloud-storage 2.10.0 | `requirements.txt` line 14 |
| HTTP Client | httpx 0.25.2 (for Whisper/Claude API calls) | `requirements.txt` line 15 |
| Frontend | Vanilla HTML/JS/CSS (static files, no framework) | `static/` directory |

Sources: `requirements.txt`, `Dockerfile`, `README.md`, `app/core/config.py`

---

## 2. ARCHITECTURE

### High-Level Architecture

MetaPM is a monolithic FastAPI application serving both a REST API and static HTML pages. There is no separate frontend build process -- the dashboard is a single large HTML file (`static/dashboard.html` at ~185KB) with inline JavaScript.

```
Browser (dashboard.html, capture.html, handoffs.html, roadmap.html)
    |
    v
Cloud Run (metapm-v2 service, us-central1)
    |-- FastAPI app (app/main.py)
    |   |-- /api/tasks, /api/projects, /api/categories    (CRUD)
    |   |-- /api/methodology (rules + violations)
    |   |-- /api/capture (voice + text, uses Whisper + Claude)
    |   |-- /api/calendar (Google Calendar integration)
    |   |-- /api/themes, /api/backlog (CRUD)
    |   |-- /api/transactions (AI conversation history)
    |   |-- /mcp/* (MCP handoff bridge API, API-key protected)
    |   |-- /api/projects, /api/sprints, /api/requirements, /api/roadmap (Roadmap)
    |   |-- /api/handoffs, /api/handoffs/{id}/status, /api/handoffs/{id}/complete (Handoff Lifecycle)
    |   |-- /api/conductor/* (Conductor prototype -- in-memory state)
    |   |-- /static/* (StaticFiles mount)
    |   |-- /health, /api/version, /debug/routes
    |
    v
Cloud SQL (flashcards-db instance, SQL Server)
    |-- Database: MetaPM
    |
GCS Bucket: corey-handoff-bridge
    |-- {project}/outbox/*.md (handoff files synced to DB)
```

Source: `app/main.py` lines 74-87, `CLAUDE.md` lines 63-71

### Application Entry Point

`app/main.py` creates the FastAPI app, runs migrations at startup, mounts static files, and includes all routers. Root `/` redirects to `/static/dashboard.html`.

Source: `app/main.py`

### Key Directories

| Directory | Purpose | Source |
|-----------|---------|--------|
| `app/api/` | API route handlers (12 modules) | `app/api/` |
| `app/core/` | Config, database, migrations | `app/core/` |
| `app/models/` | Pydantic models (project, task, methodology, transaction) | `app/models/` |
| `app/schemas/` | Pydantic schemas for MCP and Roadmap | `app/schemas/` |
| `app/services/` | Business logic (handoff_service) | `app/services/` |
| `app/jobs/` | Background jobs (GCS handoff sync) | `app/jobs/` |
| `static/` | Frontend HTML pages + JS + favicons | `static/` |
| `scripts/` | Schema SQL, migrations, utilities | `scripts/` |
| `tests/` | Unit tests (conftest, test_api, test_mcp_api) + E2E (Playwright) | `tests/` |
| `handoffs/` | Handoff bridge files (inbox, outbox, archive, log) | `handoffs/` |
| `docs/` | Architecture docs, API docs, decisions | `docs/` |

### Database Connection

Uses raw pyodbc with context-managed connections. UTF-16LE encoding is set explicitly for NVARCHAR Unicode support. Connection strings are built from environment variables. There is NO ORM.

Source: `app/core/database.py`

### Migrations

Idempotent startup migrations (13 total) run at application boot via `app/core/migrations.py`. They check `INFORMATION_SCHEMA` before applying changes. Migrations include:
1. TaskType column on Tasks
2. mcp_handoffs table
3. mcp_tasks table
4. Dashboard columns on mcp_handoffs (source, gcs_path, from_entity, to_entity)
5. Final dashboard columns (content_hash, summary, title, version, priority, type, git tracking, compliance)
6. uat_results table + handoff status constraint update
7. UAT columns on mcp_handoffs (uat_status, uat_passed, uat_failed, uat_date)
8. roadmap_projects table
9. roadmap_sprints table
10. roadmap_requirements table
11. uat_results status constraint update (allow 'pending')
12. Handoff lifecycle tables (handoff_requests, handoff_completions, roadmap_handoffs)
13. roadmap_sprints.project_id column + FK_roadmap_sprints_project FK constraint

Source: `app/core/migrations.py`

---

## 3. DATABASE SCHEMA

**Database**: MetaPM
**Instance**: flashcards-db (Cloud SQL, SQL Server)
**IP**: 35.224.242.223
**Connection Name**: super-flashcards-475210:us-central1:flashcards-db

### Core Tables (from `scripts/schema.sql`)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `Categories` | Task classification (TASK_TYPE, DOMAIN) | CategoryID, CategoryCode, CategoryName, CategoryType |
| `Projects` | Registry of all 21+ projects | ProjectID, ProjectCode, ProjectName, Theme, Status, Priority |
| `Tasks` | Central task registry | TaskID, Title, Description, Priority, Status, TaskType, DueDate |
| `TaskProjectLinks` | Many-to-many Tasks<->Projects | TaskID, ProjectID, IsPrimary |
| `TaskCategoryLinks` | Many-to-many Tasks<->Categories | TaskID, CategoryID |
| `MethodologyRules` | PM methodology rules | RuleID, RuleCode, RuleName, ViolationPrompt, Severity |
| `MethodologyViolations` | Violation tracking | ViolationID, RuleID, ProjectID, Resolution |
| `CrossProjectLinks` | Explicit project relationships | SourceProjectID, TargetProjectID, LinkType |

### MCP Tables (from `app/core/migrations.py`)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `mcp_handoffs` | Handoff bridge records | id (GUID), project, task, direction, status, content, gcs_path, uat_status |
| `mcp_tasks` | MCP-managed tasks | id (GUID), project, title, priority, status, assigned_to |
| `uat_results` | UAT test results | id (GUID), handoff_id, status, total_tests, passed, failed, results_text |

### Roadmap Tables (from `app/core/migrations.py`)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `roadmap_projects` | Project registry for roadmap | id, code, name, emoji, color, current_version, status |
| `roadmap_sprints` | Sprint definitions | id, name, project_id (FK → roadmap_projects.id), status, start_date, end_date |
| `roadmap_requirements` | Requirements linked to projects/sprints | id, project_id, code, title, type, priority, status |

### Handoff Lifecycle Tables (from `app/core/migrations.py`)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `handoff_requests` | Full lifecycle tracking per handoff | id (HO-XXXX), project, request_type, title, status |
| `handoff_completions` | CC completion responses | handoff_id, status (COMPLETE/PARTIAL/BLOCKED), commit_hash |
| `roadmap_handoffs` | Junction table roadmap<->handoffs | roadmap_id, handoff_id, relationship |

### Backlog Tables (from `scripts/backlog_schema.sql`)

| Table | Purpose |
|-------|---------|
| `Bugs` | Bug tracking per project (BugID, ProjectID, Code, Title, Status, Priority) |
| `Requirements` | Feature requests per project (RequirementID, ProjectID, Code, Title, Status, Priority) |

### Views (from `scripts/schema.sql`)

`vw_OverdueTasks`, `vw_IncompleteTasksByPriority`, `vw_TasksWithoutDueDates`, `vw_TasksByProject`, `vw_CrossProjectTasks`, `vw_BlockedProjects`, `vw_MethodologyViolationSummary`

### Stored Procedures (from `scripts/schema.sql`)

`sp_AddTask`, `sp_QuickCapture`, `sp_GetNextSprintTask`, `sp_LogMethodologyViolation`, `sp_StartConversation`, `sp_RecordTransaction`

Sources: `scripts/schema.sql`, `scripts/backlog_schema.sql`, `app/core/migrations.py`

---

## 4. API SURFACE

### Router Registration (from `app/main.py` lines 75-87)

| Prefix | Module | Tags | Auth |
|--------|--------|------|------|
| `/api/tasks` | `app/api/tasks.py` | Tasks | None |
| `/api/projects` | `app/api/projects.py` | Projects | None |
| `/api/categories` | `app/api/categories.py` | Categories | None |
| `/api/methodology` | `app/api/methodology.py` | Methodology | None |
| `/api/capture` | `app/api/capture.py` | Quick Capture | None |
| `/api/transactions` | `transactions.py` | Transactions & Analytics | None |
| `/api/calendar` | `app/api/calendar.py` | Calendar | None |
| `/api/themes` | `app/api/themes.py` | Themes | None |
| `/api/backlog` | `app/api/backlog.py` | Backlog | None |
| `/mcp` | `app/api/mcp.py` | MCP | API Key (X-API-Key or Bearer) |
| `/api` | `app/api/roadmap.py` | Roadmap | None |
| `/api` | `app/api/handoff_lifecycle.py` | Handoff Lifecycle | None |
| `/api/conductor` | `app/api/conductor.py` | Conductor | None |

### Key Endpoints

**Tasks** (`/api/tasks`): GET (list/filter/paginate), GET/{id}, POST, PUT/{id}, DELETE/{id}, POST/{id}/complete, POST/{id}/reopen
**Projects** (`/api/projects`): GET (list), GET/{code}, GET/{code}/tasks, POST, PUT/{code}, DELETE/{code}
**MCP Handoffs** (`/mcp/handoffs`): POST (create), GET (list), GET/dashboard (public), GET/stats (public), POST/sync, GET/export/log, GET/{id} (auth), GET/{id}/content (public), PATCH/{id}
**MCP Tasks** (`/mcp/tasks`): POST, GET (list), GET/{id}, PATCH/{id}, DELETE/{id}
**UAT** (`/mcp/handoffs/{id}/uat`, `/mcp/uat/submit`, `/mcp/uat/direct-submit`, `/mcp/uat/latest`, `/mcp/uat/list`, `/mcp/uat/results`, `/mcp/uat/results/{id}`, `/mcp/uat/{id}`)
**Roadmap** (`/api/projects`, `/api/sprints`, `/api/requirements`, `/api/roadmap`, `/api/roadmap/seed`)
**Roadmap (New 2026-02-18)**: GET /api/roadmap/projects, GET /api/roadmap/requirements, GET /api/requirements?limit=N, POST /api/requirements, PATCH /api/requirements/:id, PUT /api/requirements/:id
**Roadmap Export (New 2026-02-20)**: GET /api/roadmap/export (public JSON snapshot with projects, nested requirements, sprints, and aggregate stats)
**UAT Submit (New 2026-02-18)**: POST /api/uat/submit (project derived from linked_requirements, 201 Created confirmed)
**Handoff Lifecycle** (`/api/handoffs`, `/api/handoffs/{id}`, `/api/handoffs/{id}/status`, `/api/handoffs/{id}/complete`, `/api/roadmap/{id}/handoffs`)
**Conductor** (`/api/conductor/update`, `/api/conductor/dispatch`, `/api/conductor/status`, `/api/conductor/inbox`)
**Methodology**: `/api/methodology/rules`, `/api/methodology/violations`, `/api/methodology/analytics`
**Backlog**: `/api/backlog/bugs`, `/api/backlog/requirements`, `/api/backlog/grouped`, `/api/backlog/next-code/{project_id}/{item_type}`
**Calendar**: `/api/calendar/status`, `/api/calendar/today`, `/api/calendar/week`, `/api/calendar/events`, `/api/calendar/from-voice`, `/api/calendar/calendars`
**Capture**: `/api/capture/text`, `/api/capture/voice`
**System**: `/health`, `/api/version`, `/debug/routes`, `/docs`, `/redoc`

### Authentication

MCP endpoints require an API key via `X-API-Key` header or `Authorization: Bearer` header. The key is validated against `settings.MCP_API_KEY` or `settings.API_KEY`. Dashboard/public endpoints (stats, dashboard, UAT direct-submit, handoff content) are unauthenticated.

Source: `app/api/mcp.py` lines 32-63

---

## 5. FRONTEND

### Static HTML Pages

| File | URL | Purpose | Source |
|------|-----|---------|--------|
| `static/dashboard.html` | `/static/dashboard.html` (root redirects here) | Main dashboard with tabs: Tasks, Projects, Methodology, Backlog, Capture | `static/dashboard.html` (~185KB) |
| `static/capture.html` | `/capture.html` | Voice/text quick capture PWA page | `static/capture.html` |
| `static/handoffs.html` | `/handoffs.html` | Handoff Bridge dashboard | `static/handoffs.html` |
| `static/roadmap.html` | `/roadmap.html` | Redirect to dashboard.html (13-line redirect, MP-009 sprint) | `static/roadmap.html` |
| `static/compare.html` | `/compare/{handoff_id}` | Handoff comparison page | `static/compare.html` |

### Frontend Features
- **PWA Support**: Service worker (`static/sw.js`), manifest (`static/manifest.json`), offline support via IndexedDB
- **Dark/Light/Auto Theme Toggle**: Stored in localStorage
- **Tab Persistence**: Last-viewed tab stored in `localStorage['metapm-activeTab']`
- **Bulk Task Actions**: Checkboxes with selection counter, bulk status changes
- **Mobile Responsive**: Designed for mobile-first usage
- **Favicons**: Full set (16x16, 32x32, 48x48, apple-touch-icon, 192, 512)

### Offline Sync
- `static/js/offline-data.js` (20KB): IndexedDB sync queue implementation
- Service worker caches pages for offline access

Source: `static/` directory listing, `static/manifest.json`, `static/sw.js`

---

## 6. FEATURES -- WHAT EXISTS TODAY

### Core Features (Production)
- **Hierarchical Single-Page Dashboard (MP-009 — Deployed 2026-02-18)**: Single scrollable page replacing old 3 separate pages (roadmap, backlog, dashboard)
  - 31 total projects (6 portfolio + 25 personal legacy projects, all visible in dashboard)
  - Filter bar: Project, Priority, Status dropdowns + Sort + Group By
  - Triangle expand/collapse per project section
  - **Expand/Collapse All button (MP-019 — Done 2026-02-19)**: ▼/▲ toggle in control bar expands or collapses all project sections at once
  - Row click → detail panel slides in with description, status, priority, inline editing
  - [+ Add ▼] button — **FIXED (MP-020 v2 — 2026-02-19)**. Root cause was makeId() generating 40-41 char IDs into NVARCHAR(36) PKs. Fix: bare UUID always 36 chars. All Add operations (project, sprint, requirement, bug, task) confirmed working with HTTP 201.
  - Requirement drawer: **Title field now editable** (v2.2.2). Title included in PUT payload.
  - Dashboard header shows **version number** fetched from /health (v2.2.2).
  - **Full CRUD for all entity types (MP-022 — v2.3.0)**:
    - ✏️ Edit icon on project header opens edit modal (name, emoji, version, status, repo_url)
    - ✏️ Edit icon on sprint bucket opens edit modal (name, project, status)
    - 🗑 Delete button in requirement drawer (with confirm dialog)
    - 🗑 Delete buttons in edit modals for projects and sprints
    - DELETE /api/roadmap/projects/{id} — backend endpoint added (409 if has requirements)
    - DELETE /api/roadmap/sprints/{id} — backend endpoint added
  - **Client-side search (MP-022d — v2.3.0)**: Search box in controls bar filters requirements and projects by code, title, type, priority, status, project name. Instant, no backend call.
  - **Requirement code badge (MP-022c — v2.3.0)**: `data-searchable` on all rows. Code already shown as `<strong>` badge (v2.2.2).
  - /roadmap.html is now a redirect to dashboard.html
- **CORS Fix (2026-02-19)**: `app/main.py` now allows `GET, POST, PUT, PATCH, DELETE, OPTIONS` — was missing PUT, PATCH, DELETE which blocked edit/delete from cross-origin contexts
- **MP-023 API + Dashboard Fixes (2026-02-20, v2.3.1)**:
  - Public roadmap export endpoint: `GET /api/roadmap/export` (all projects + nested requirements + sprints + stats)
  - Roadmap delete endpoints: `DELETE /api/roadmap/projects/{id}` (409 guard if requirements exist), `DELETE /api/roadmap/sprints/{id}` (unassigns linked requirements first)
  - Sprint create ID fix in dashboard (`crypto.randomUUID()` UUID-only IDs)
  - Requirement drawer save/close lifecycle fixed (no stale reopen behavior)
  - Dashboard UX updates: sticky header/footer, independent content scroll, Enter-to-research behavior, and `Not Done` status preset
  - Status cleanup applied: MP-018/019/020/021 set to `done`
- **Requirements — 80 seeded (MP-002 — Complete)**: 79 from Portfolio Vision Framework v3 + MP-018 added by CAI
  - All 80 have descriptions in PL's voice (loaded from canonical seed file `metapm_descriptions_seed.json`)
  - Roadmap requirements for MetaPM project (proj-mp): 21 total (MP-001 through MP-021)
- **UAT Submit Pipeline**: POST /api/uat/submit endpoint — 201 Created confirmed
  - Project derivation from linked_requirements (no explicit project field needed)
  - Cross-portfolio fallback when requirements span multiple projects
  - First successful submission ID: 5A471083-51C4-4042-8A0C-8ABE92361CE6
  - **Gap:** Submitted handoffs not yet visible in dashboard UI (MP-021)
- **Full CRUD APIs**: Tasks, Projects, Categories, Themes, Methodology Rules/Violations, Bugs, Requirements
- **Cross-Project Task Linking**: Tasks can belong to multiple projects
- **Task Type System**: task, bug, requirement (auto-prefixed BUG-xxx, REQ-xxx)
- **Voice/Text Capture**: Whisper transcription + Claude intent extraction + auto task creation
- **Google Calendar Integration**: Today/week events, create events, voice-to-calendar
- **Methodology Enforcement**: Rules with pre-written violation prompts, violation tracking, analytics
- **MCP Handoff Bridge**: Full handoff CRUD, GCS bucket sync, dashboard view, content serving
- **UAT Results Tracking**: Submit UAT from HTML checklists (direct-submit), results history, latest/list views
- **Roadmap System**: Projects, sprints, requirements with aggregated dashboard view, seed data endpoint
- **Handoff Lifecycle Tracking**: Request -> Completion -> UAT flow with roadmap linking
- **Conductor API**: Prototype for CC/CAI status routing (in-memory only)
- **PWA with Offline Sync**: Service worker, IndexedDB queue, background sync
- **Dark/Light Theme Toggle**: Appearance theming with localStorage persistence

Sources: `app/main.py`, `app/api/*.py`, `PROJECT_STATUS.md`, `SPRINT3_IMPLEMENTATION_SUMMARY.md`

### Sprint History
- **Sprint 1-2**: Core scaffold, CRUD APIs, Cloud Run deployment
- **Sprint 3**: Color themes, favicon, task sort, dark/light toggle, offline sync, expand/collapse
- **Sprint 4**: Theme management UI (completed), Violation AI (CANCELED -- Command Center model replaces it)
- **Sprint 5 Phase 3**: MCP API (handoffs, tasks, log), API key auth
- **Post-Sprint**: Dashboard (v1.9.0), UAT tracking (v1.9.2), Roadmap (v2.0.0), Handoff lifecycle (v2.0.5), Bug sprint (v2.1.x)
- **Sprint "Etymython Integration + MetaPM Dashboard Rework" (2026-02-18)**:
  - MP-009: Hierarchical single-page dashboard deployed
  - 80 requirements seeded (79 from Vision Framework + MP-018)
  - 79 canonical descriptions loaded from seed file in PL's voice
  - UAT Submit pipeline: POST /api/uat/submit working (201 confirmed)
  - 24 personal projects recovered to roadmap_projects table
  - MP-021 filed: Handoff CRUD visibility needed
  - Deployed revision: metapm-v2-00077-dzt
- **Sprint "MP-020 Fix Sprint Start" (2026-02-18/19)**:
  - MP-020: Fixed [+ Add] button 500 error. Root cause: FK constraint when project_id invalid/empty in POST /api/roadmap/requirements. aType field was free-text input (invalid enum risk); changed to `<select>`. render() was filtering projects with no requirements (`if (!pReqs.length) continue`) hiding 24+ personal projects — removed.
  - MP-019: Expand/collapse all button added to dashboard.html control bar. Uses `state.expanded` Set and calls `render()`.
  - CORS: `allow_methods` updated to include PUT, PATCH, DELETE.
  - roadmap.html replaced with 13-line redirect to dashboard.html (from MP-009 sprint, committed this sprint).
  - roadmap_sprints.project_id FK added (Migration 13, from MP-009 sprint, committed this sprint).
  - MP-019, MP-020, MP-021 seeded as roadmap_requirements for proj-mp (21 total now).
  - Deployed revision: metapm-v2-00078-vsc
- **Sprint "MP-020 Fix v2" (2026-02-19)**:
  - MP-020 root cause corrected: makeId() prepended prefix to UUID generating 40-41 char IDs into NVARCHAR(36) columns, causing every Add operation to return 500.
  - Fix: makeId() now returns bare crypto.randomUUID() (36 chars always).
  - Title field added to requirement drawer (was not editable).
  - PUT /api/roadmap/requirements payload now includes title field.
  - Version number displayed in dashboard header via /health fetch on load.
  - UAT Template v3 committed to project-methodology/templates/.
  - MP-020 status updated to done.
  - Deployed revision: metapm-v2-00079-szg
- **Sprint "MP-022 Full CRUD + Search" (2026-02-19)**:
  - MP-022a: Edit modal for projects (name, emoji, version, status, repo_url) and sprints (name, project, status). ✏️ icon in project-head and sprint bucket-title. Re-uses addModal with state.editMode toggle.
  - MP-022b: DELETE /api/roadmap/projects/{id} (with FK check: 409 if has requirements) and DELETE /api/roadmap/sprints/{id} added to roadmap.py. Delete buttons in edit modal with confirm() dialog. 🗑 button in requirement drawer.
  - MP-022c: data-searchable attribute on all requirement rows (code + title + type + priority + status + project name).
  - MP-022d: Search bar added to controls (client-side, instant filter). Hides non-matching req rows and collapses empty project sections.
  - Also: showToast() for delete confirmations, escHtml() XSS guard in openEdit().
  - All test data cleaned up from DB (no residual test records).
  - Deployed revision: metapm-v2-00080-22r

Sources: `PROJECT_STATUS.md`, `SPRINT_4_CANCELED.md`, `handoffs/log/HANDOFF_LOG.md`

---

## 7. FEATURES -- PLANNED/IN PROGRESS

### What's Next (per Roadmap, as of 2026-02-19)

| ID | Requirement | Priority | Notes |
|----|------------|----------|-------|
| MP-021 | Handoff/UAT CRUD visibility | P2 | PL: "clicking on handoff ID should open MetaPM to show and CRUD" |
| MP-018 | Full-text search across all entities | P2 | No way to find anything except scrolling |
| — | Add button full CRUD for all entity types | P2 | PL: "full CRUD capability all objects (Project, Items, UATs etc.)" |
| — | Dashboard hierarchy incomplete | P2 | Only Projects → Requirements; needs Tasks + UATs |
| MP-012 | Task entity as child of requirement | P2 | New table needed |
| MP-013 | Test Plan / UAT entity hierarchy | P2 | New table needed |
| MP-011 | Sprint entity + assignment | P2 | Sprint project_id FK now exists |
| MP-005 | Roadmap CRUD | P2 | |

### MetaPM Vision — Full Entity Hierarchy Needed
```
Project → Sprint → Requirement/Bug → Task → Test Case → Result
Full-text search, expand/collapse all, handoff/UAT visibility, cross-project links
```

---

## 8. CONFIGURATION & SECRETS

### Environment Variables (from `app/core/config.py`)

| Variable | Purpose | Default | Source |
|----------|---------|---------|--------|
| `VERSION` | App version | "2.3.0" | config.py line 15 |
| `DB_SERVER` | SQL Server host | "localhost" | config.py line 19 |
| `DB_NAME` | Database name | "MetaPM" | config.py line 20 |
| `DB_USER` | Database user | "sqlserver" | config.py line 21 |
| `DB_PASSWORD` | Database password | "" | config.py line 22 (from Secret Manager) |
| `DB_DRIVER` | ODBC driver | "ODBC Driver 18 for SQL Server" | config.py line 23 |
| `GCP_PROJECT_ID` | GCP project | "" | config.py line 26 |
| `CLOUD_SQL_INSTANCE` | Cloud SQL connection name | "" | config.py line 27 |
| `GCS_MEDIA_BUCKET` | Media bucket | "metapm-media" | config.py line 28 |
| `GCS_HANDOFF_BUCKET` | Handoff bridge bucket | "corey-handoff-bridge" | config.py line 39 |
| `OPENAI_API_KEY` | For Whisper transcription | "" | config.py line 31 |
| `ANTHROPIC_API_KEY` | For Claude AI processing | "" | config.py line 32 |
| `API_KEY` | General API key | "" | config.py line 35 |
| `MCP_API_KEY` | MCP endpoint API key | "" | config.py line 36 |
| `ENVIRONMENT` | development/production | "development" | config.py line 42 |
| `LOG_LEVEL` | Logging level | "INFO" | config.py line 43 |

### Secrets in Google Secret Manager (from `CLAUDE.md`)

| Secret Name | Purpose | Source |
|-------------|---------|--------|
| `db-password` | SQL Server password | CLAUDE.md line 209 |
| `openai-api-key` | OpenAI API key | CLAUDE.md line 210 |
| `anthropic-api-key` | Anthropic API key | CLAUDE.md line 211 |

### CRITICAL: No .env files in production
All secrets are managed via GCP Secret Manager and injected via `--set-secrets` at deploy time. `.env` files are `.gitignore`d and must NEVER be committed.

Source: `app/core/config.py`, `CLAUDE.md` lines 204-214, `.env.example`

---

## 9. DEPLOYMENT

### Infrastructure

| Resource | Value | Source |
|----------|-------|--------|
| **GCP Project** | `super-flashcards-475210` | CLAUDE.md line 67 |
| **Cloud Run Service** | `metapm-v2` (NOT `metapm`) | CLAUDE.md line 68 |
| **Cloud Run Region** | `us-central1` | CLAUDE.md line 69 |
| **Custom Domain** | `https://metapm.rentyourcio.com` | CLAUDE.md line 70 |
| **Cloud SQL Instance** | `flashcards-db` | CLAUDE.md line 71 |
| **Cloud SQL Connection** | `super-flashcards-475210:us-central1:flashcards-db` | CLAUDE.md line 72 |
| **Database Name** | `MetaPM` | CLAUDE.md line 73 |
| **Database IP** | `35.224.242.223` | CLAUDE.md line 74 |
| **GCS Handoff Bucket** | `corey-handoff-bridge` | config.py line 39 |

### DEPRECATED (DO NOT USE)
- Service `metapm` (old, broken)
- Project `metapm` (wrong for this database)
- Instance `coreyscloud` (doesn't exist)

Source: `CLAUDE.md` lines 93-97

### Deploy Command (EXACT)

```powershell
gcloud run deploy metapm-v2 `
  --source . `
  --region us-central1 `
  --allow-unauthenticated `
  --set-env-vars="DB_SERVER=35.224.242.223,DB_NAME=MetaPM,DB_USER=sqlserver,ENVIRONMENT=production" `
  --set-secrets="DB_PASSWORD=db-password:latest" `
  --add-cloudsql-instances="super-flashcards-475210:us-central1:flashcards-db"
```

Source: `CLAUDE.md` lines 83-91

### Docker Configuration

- Base image: `python:3.11`
- Installs ODBC Driver 18 for SQL Server (Microsoft Debian 11 packages)
- Non-root user `appuser` for security
- Health check: `curl -f http://localhost:8080/health`
- Entrypoint: `gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8080 --timeout 120`
- Port: 8080

Source: `Dockerfile`

### Cloud Build (`cloudbuild.yaml`)

- Tests: DISABLED (ODBC drivers not available in test container)
- Builds Docker image tagged with `$COMMIT_SHA` and `latest`
- Pushes to GCR
- Deploys to Cloud Run with Cloud SQL instance, env vars, secrets
- Resources: 512Mi memory, 1 CPU, 0-3 instances
- Timeout: 1200s (20 minutes)

Source: `cloudbuild.yaml`

### `.gcloudignore`

Excludes: `.git`, `__pycache__`, `.env`, `.vscode`, `*.md`, `tests/`, `scripts/`, `.venv/`, `venv/`, `incoming_zip/`, `project-methodology/`

### UAT Template

Canonical UAT checklist template: `project-methodology/templates/UAT_Template_v3.html`
GitHub: https://github.com/coreyprator/project-methodology/blob/main/templates/UAT_Template_v3.html
Do not recreate from scratch. Copy and replace `UAT_` placeholders.

Source: `.gcloudignore`

### Health Check

```bash
curl https://metapm.rentyourcio.com/health
```
Returns: `{"status": "healthy", "version": "2.3.0", "build": "..."}`

Source: `app/main.py` lines 95-104

---

## 10. TESTING

### Test Framework

- **Unit tests**: pytest with FastAPI TestClient
- **E2E tests**: Playwright (runs against live deployment)
- **Test files location**: `tests/`

### Test Files

| File | Type | What It Tests | Source |
|------|------|---------------|--------|
| `tests/conftest.py` | Fixture | TestClient, sample_task, sample_quick_capture | `tests/conftest.py` |
| `tests/test_api.py` | Unit | Basic API endpoints | `tests/test_api.py` |
| `tests/test_dashboard.py` | Unit | Dashboard functionality | `tests/test_dashboard.py` |
| `tests/test_dashboard_functional.py` | Unit | Dashboard functional tests | `tests/test_dashboard_functional.py` |
| `tests/test_mcp_api.py` | Unit | MCP API: UAT results alias, handoffs list, direct submit (with monkeypatching) | `tests/test_mcp_api.py` |
| `tests/test_sprint3_features.py` | Unit | Sprint 3 features | `tests/test_sprint3_features.py` |
| `tests/test_theme_management.py` | Unit | Theme CRUD | `tests/test_theme_management.py` |
| `tests/e2e/test_bulk_status.py` | E2E/Playwright | Bulk status selection counter (HO-MP01) | `tests/e2e/test_bulk_status.py` |
| `tests/e2e/test_tab_persistence.py` | E2E/Playwright | Tab persistence via localStorage (HO-MP02) | `tests/e2e/test_tab_persistence.py` |

### Testing Approach

MCP API tests use `monkeypatch` to mock `execute_query`, avoiding the need for a real database connection. E2E tests run against the live `https://metapm.rentyourcio.com` deployment.

### Running Tests

```bash
# Unit tests
pytest tests/ -v

# E2E tests (requires Playwright installed)
pytest tests/e2e/ -v

# UI smoke test (required before every handoff per CLAUDE.md)
pytest tests/test_ui_smoke.py -v
```

Source: `tests/`, `CLAUDE.md` lines 117-119

---

## 11. INTEGRATIONS WITH OTHER PROJECTS

### Projects Tracked in MetaPM

MetaPM manages 21+ projects across 4 themes (from `scripts/schema.sql` seed data):

| Theme | Projects |
|-------|----------|
| A: Creation | ArtForge, Cubist, 6 Video projects, Art-System |
| B: Learning | Etymython, HarmonyLab, Super-Flashcards, French, Greek, Jazz Piano |
| C: Adventure | Route 89, Colorado River, Grand Canyon, Alcan |
| D: Relationships | DIPsters |
| Cross-Cutting | MetaPM itself |

### GCS Handoff Bridge

MetaPM syncs handoffs from `gs://corey-handoff-bridge/{project}/outbox/*.md` for these projects:
- ArtForge, HarmonyLab (as "harmonylab"), Super-Flashcards, MetaPM (as "metapm"), Etymython, project-methodology

Source: `app/jobs/sync_gcs_handoffs.py` lines 19-26

### AI Integration

- **Whisper**: Voice transcription via OpenAI API (`app/api/capture.py`)
- **Claude (Anthropic)**: Intent extraction from captures, voice-to-calendar parsing (`app/api/capture.py`, `app/api/calendar.py`)
- Model used: `claude-sonnet-4-20250514`

### Google Calendar

Read/write integration with Google Calendar via OAuth. Requires refresh token, client ID, and client secret. Used for event viewing and voice-to-calendar creation.

Source: `app/api/calendar.py`

### Handoff Bridge Protocol

MetaPM serves as the central hub for the Handoff Bridge protocol between Claude Code (CC) and Claude.ai (CAI). Handoffs are markdown files exchanged via GCS bucket, with MetaPM providing:
- SQL storage of all handoffs
- Dashboard for viewing/filtering
- UAT results tracking
- Content serving at public URLs for `web_fetch`
- Handoff lifecycle tracking (SPEC -> PENDING -> DELIVERED -> UAT -> PASSED/FAILED)

Source: `app/api/mcp.py`, `app/api/handoff_lifecycle.py`, `app/services/handoff_service.py`

---

## 12. KNOWN ISSUES & TECHNICAL DEBT

### Open Bugs (Current — as of 2026-02-19)
| ID | Issue | Severity | Impact |
|----|-------|----------|--------|
| MP-021 | Handoff/UAT data not visible in dashboard | P2 | Submit works but no UI to see/click/edit handoffs |
| — | Dashboard hierarchy incomplete | P2 | Only Projects → Requirements (no Tasks, UATs, Sprints) |
| — | roadmap_handoffs type mismatch | P3 | Junction table has varchar/UUID type inconsistency |
| — | backlog.py ReferenceURL column | P3 | Column referenced in INSERT/SELECT but missing from Requirements table schema; affects /api/backlog/requirements (NOT roadmap endpoints) |

### Resolved Bugs (Recent)
| ID | Issue | Fixed | How |
|----|-------|-------|-----|
| MP-022a | No edit UI for projects or sprints | 2026-02-19 | ✏️ edit icon in project/sprint headers; addModal re-used with editMode state |
| MP-022b | No delete UI; no DELETE endpoints for projects/sprints | 2026-02-19 | DELETE endpoints added to roadmap.py; 🗑 buttons in edit modal + requirement drawer |
| MP-022c | Requirement code not visible as searchable badge | 2026-02-19 | data-searchable attribute on req rows; code already shown as <strong> badge |
| MP-022d | No search functionality | 2026-02-19 | Client-side search bar in controls; instant filter, no backend call |
| MP-020 | makeId() generated 40-41 char IDs for NVARCHAR(36) PK columns — all Add ops returned 500 | 2026-02-19 | makeId() now returns bare crypto.randomUUID() (36 chars). Patched by CAI. |
| MP-019 | No expand/collapse all button | 2026-02-19 | ▼/▲ Expand All button added to dashboard.html control bar |
| CORS | PUT/DELETE blocked cross-origin | 2026-02-19 | allow_methods now includes PUT, PATCH, DELETE |

### Pre-existing Technical Debt

1. **Cloud Build tests disabled**: ODBC drivers not available in the Cloud Build test container, so CI tests are commented out (`cloudbuild.yaml` lines 5-13).

2. **SQL injection risk**: Several API endpoints use f-string interpolation for SQL queries instead of parameterized queries (e.g., `app/api/projects.py` lines 78-79, `app/api/tasks.py` lines 191-200, `app/api/methodology.py` lines 76-78). This is mitigated by the app being single-user but should be fixed.

3. **Conductor API is prototype only**: Uses in-memory dict, not persisted to database (`app/api/conductor.py` line 19).

4. **CLAUDE.md has duplicate/conflicting sections**: The file contains two versions of instructions -- the top half (updated 2026-02-10) has correct infrastructure values, while the bottom half (older) has incorrect GCP project name "metapm" instead of "super-flashcards-475210" (`CLAUDE.md` lines 258-390).

5. **Root-level file clutter**: Many specification, UAT, and handoff `.md` and `.html` files are in the project root instead of organized in subdirectories.

6. **transactions.py lives in project root**: The transactions router module is at `transactions.py` (root) rather than in `app/api/` like all other routers (`app/main.py` line 16).

7. **`client_secret_*.json` committed**: A Google OAuth client secret JSON file is present in the repo root, though it's in `.gitignore` pattern (`client_secret_*.json`).

### Technical Debt

- No type hints on many database return values
- No connection pooling (new connection per query)
- Dashboard HTML is a single 185KB file -- should be modularized
- No automated test for database migrations
- Backlog tables (`Bugs`, `Requirements`) overlap somewhat with `roadmap_requirements`
- Multiple overlapping project tables: `Projects` (core) and `roadmap_projects` (roadmap feature)

Sources: Code review of `app/api/*.py`, `app/core/database.py`, `CLAUDE.md`, project structure

---

## 13. LESSONS LEARNED (PROJECT-SPECIFIC)

| ID | Title | Summary | Source |
|----|-------|---------|--------|
| LL-039 | No Import-Time Database Calls | Never execute DB queries at module import time -- blocks Cloud Run cold starts. All DB calls must be inside function bodies. | `LL-039-NO-IMPORT-TIME-DB-CALLS.md` |
| LL-045 | AI Must Read Existing Docs First | AI sessions must read existing documentation before starting work. | `PROJECT_STATUS.md` |
| LL-046 | No Import-Time Database Calls | Same as LL-039, re-documented. | `PROJECT_STATUS.md` |
| LL-047 | Sprint Documentation Checklist | Sprint docs must follow a checklist format. | `PROJECT_STATUS.md` |
| LL-048 | Claude Also Reads Docs First | Claude.ai must read docs first, just like CC. | `PROJECT_STATUS.md` |
| LL-049 | "Complete" Requires Test Proof | Cannot say "complete" without deployed revision + test output. | `PROJECT_STATUS.md` |
| LL-050 | Audit Must Verify Connectivity | Audit scripts must verify actual connectivity, not just resource existence. | `PROJECT_STATUS.md` |

### Key Decision: Sprint 4 Canceled

The Violation AI feature (Sprint 4) was canceled on 2026-01-31. The Command Center model (Claude Code + CLAUDE.md enforcement) replaces the need for in-app violation detection. Compliance is enforced proactively at the source rather than detected after the fact.

Source: `SPRINT_4_CANCELED.md`

### Key Decision: Service Rename

Service renamed from `metapm` to `metapm-v2` in January 2026 due to Docker cache issues with the old service. The old `metapm` service was deleted on Jan 30, 2026.

Source: `PROJECT_STATUS.md`

### Key Decision: DB_SERVER changed to TCP IP

Changed from Unix socket path to TCP IP (`35.224.242.223`) on Jan 31, 2026 because Unix socket path broke pyodbc.

Source: `PROJECT_STATUS.md`

### Key Decision: UAT Results Alias

On 2026-02-14, added `GET /mcp/uat/results/{id}` as an alias for `GET /mcp/uat/{id}` to preserve backward compatibility with existing UAT templates.

Source: `docs/decisions/2026-02-14-uat-results-alias.md`

---

## 14. DIRECTIVES FOR AI SESSIONS

### From CLAUDE.md (MANDATORY)

1. **Cloud-First**: There is NO localhost. Workflow: Write -> Push -> Deploy -> Test on Cloud Run URL. Never say "local edits." Database is ALWAYS Cloud SQL.

2. **You Own Deployment**: Run `gcloud run deploy` without asking permission. Deploy, verify, and report results.

3. **You Must Test Before Handoff**: Use Playwright. Run `pytest tests/test_ui_smoke.py -v` before every handoff. Include test output in report.

4. **Version Numbers**: Every deploy must update `app/core/config.py` VERSION. Report: "Deployed v1.X.Y"

5. **Definition of Done**: Code changes complete, tests pass, git committed + pushed, deployed, health check passes, version matches, UAT checklist created (for features), handoff created + uploaded.

6. **Handoff Format**: Must include version, revision, deployed URL, git status, test output, "All tests pass: Yes", "Ready for review: Yes".

7. **Vocabulary Lockdown**: Cannot say "Complete"/"Done"/"Finished" without proof (deployed revision + test output). Must say deployed revision, test output, version number.

8. **Security**: NEVER hardcode secrets. Use GCP Secret Manager. Mask secrets in logs.

9. **Before Starting Work**: Verify GCP project (`gcloud config get-value project` must return `super-flashcards-475210`), read CLAUDE.md completely, read spec files, check recent test results.

10. **Handoff Bridge**: ALL responses to Claude.ai/Corey MUST use the handoff bridge. Create file -> Run handoff_send.py -> Provide URL.

11. **Git Commit Format**: Include handoff ID: `feat: [description] (HO-XXXX)` or `fix: [description] (HO-XXXX)`

12. **Database**: Always check `scripts/schema.sql` for actual column names before writing SQL. Do NOT guess column names.

### From .claude/settings.json

**Allowed**: Read, Edit, Bash(git/python/pip/npm/gcloud/cd/ls/cat/mkdir/cp/mv)
**Denied**: Bash(rm -rf), Bash(sudo), Read(.env*)

Source: `CLAUDE.md`, `.claude/settings.json`

---

## 15. OPEN QUESTIONS

1. **Why are there two overlapping project tables?** `Projects` (core, from schema.sql) and `roadmap_projects` (from migration 8). Should they be unified?

2. **What is the current state of the Conductor API?** It's prototype-only (in-memory). Is it still needed, or should it be removed?

3. **Should transactions.py be moved into app/api/?** It currently lives at the project root, unlike all other route modules.

4. **What is the plan for Cloud Build test re-enablement?** Tests are disabled due to ODBC driver unavailability in the build container.

5. **Should the root-level .md and .html files be organized?** There are ~40 specification/UAT/handoff files cluttering the project root.

6. **Is the Google Calendar integration fully operational?** The code references OAuth credentials that may need rotation/reconfiguration.

7. **What happened to the `templates/` directory?** It exists and now contains `UAT_Template_v3.html` (committed 2026-02-19) as well as previous templates. Use this location for all UAT template versions.

8. **Are the Backlog tables (`Bugs`, `Requirements`) still in use alongside `roadmap_requirements`?** There appears to be functional overlap.

---

## DOCUMENTATION SOURCES INVENTORY

### Found and Read

| File | Status | Notes |
|------|--------|-------|
| `CLAUDE.md` | READ | Primary AI instructions (has duplicate/conflicting sections) |
| `README.md` | READ | Project overview, API docs, directory structure |
| `.claude/settings.json` | READ | Permission configuration |
| `.env.example` | READ | Environment variable template |
| `requirements.txt` | READ | Python dependencies |
| `Dockerfile` | READ | Container configuration |
| `cloudbuild.yaml` | READ | CI/CD pipeline (tests disabled) |
| `.gitignore` | READ | Git exclusions |
| `.gcloudignore` | READ | Cloud Build exclusions |
| `app/core/config.py` | READ | Settings class with all env vars |
| `app/core/database.py` | READ | Database connection management |
| `app/core/migrations.py` | READ | 12 idempotent startup migrations |
| `app/main.py` | READ | FastAPI app entry point |
| `app/api/*.py` (12 files) | READ | All route handlers |
| `app/models/*.py` (4 files) | READ | Pydantic models |
| `app/schemas/*.py` (2 files) | READ | MCP and Roadmap schemas |
| `app/services/handoff_service.py` | READ | Handoff business logic |
| `app/jobs/sync_gcs_handoffs.py` | READ | GCS sync job |
| `scripts/schema.sql` | READ | Database schema v1.0 |
| `scripts/backlog_schema.sql` | EXISTS | Backlog tables (referenced) |
| `scripts/migrations/import_gcs_handoffs.py` | READ | GCS import migration script |
| `tests/conftest.py` | READ | Test fixtures |
| `tests/test_mcp_api.py` | READ | MCP API tests (8 tests) |
| `tests/e2e/test_bulk_status.py` | READ | E2E bulk status tests |
| `tests/e2e/test_tab_persistence.py` | READ | E2E tab persistence tests |
| `PROJECT_STATUS.md` | READ | Sprint status and decisions |
| `SPRINT_4_CANCELED.md` | READ | Sprint 4 cancellation rationale |
| `LL-039-NO-IMPORT-TIME-DB-CALLS.md` | READ | Critical lesson learned |
| `handoffs/log/HANDOFF_LOG.md` | READ | Chronological handoff log |
| `docs/decisions/2026-02-14-uat-results-alias.md` | READ | Architecture decision record |
| `transactions.py` | READ | Root-level transactions router |
| `static/` directory | INVENTORIED | 7 HTML pages, JS, favicons, manifest |

### Found but Not Read (Lower Priority)

| File | Reason |
|------|--------|
| `static/dashboard.html` (~185KB) | Too large; functionality documented from API routes |
| `static/capture.html`, `handoffs.html`, `roadmap.html`, `compare.html` | Frontend HTML; API surface documented |
| `static/js/offline-data.js` | IndexedDB sync implementation |
| `tests/test_api.py`, `test_dashboard.py`, `test_dashboard_functional.py` | Additional test files |
| `tests/test_sprint3_features.py`, `test_theme_management.py` | Additional test files |
| `handoffs/inbox/*.md` (10 files) | Inbox handoff specs |
| `handoffs/outbox/*.md` (23 files) | Outbox completion handoffs |
| `handoffs/archive/HO-A1B2_request.md` | Archived handoff |
| Root `.md` files (MetaPM_*.md, VS_CODE_*.md, etc.) | Historical specs, UAT checklists, reports |
| `docs/METHODOLOGY.md` | Methodology rules documentation |
| Various root `.html` files | UAT checklists (browser-viewable) |
| `scripts/seed_methodology_rules.sql` | Methodology seed data |
| `scripts/seed_backlog.sql` | Backlog seed data |
| `gen_report.py`, `fix_uat_constraint.py` | Utility scripts |

### Expected but Missing

| File | Status |
|------|--------|
| `.claude/settings.local.json` | NOT FOUND |
| `app/core/security.py` | Referenced in README but NOT FOUND |
| `app/services/task_service.py` | Referenced in README but NOT FOUND |
| `app/services/methodology_service.py` | Referenced in README but NOT FOUND |
| `pyproject.toml` | NOT FOUND (uses requirements.txt instead) |
| `package.json` | NOT FOUND (no Node.js frontend) |
| `.github/` | NOT FOUND (uses Cloud Build instead of GitHub Actions) |
| `docs/API.md` | NOT FOUND (docs/api/ has only .gitkeep) |
| `docs/architecture/` | EXISTS but only has .gitkeep |
| `alembic/` | NOT FOUND (uses custom migrations) |
| `specs/`, `roadmaps/` | NOT FOUND as separate directories |

---

*End of Project Knowledge Document*
