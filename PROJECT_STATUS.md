# MetaPM Project Status

**Last Updated**: January 31, 2026
**Updated By**: Claude (Architect) + Project Lead
**Sprint**: 4 (Canceled — replaced by Command Center model)

---

## Executive Summary

MetaPM is a cross-project task management system for Corey's 21+ personal projects. Sprint 4 (Violation AI) was canceled — the Command Center model with Claude Code + enhanced audit script replaces the need for in-app violation detection.

---

## Current State

### Production Environment

| Resource | Value |
|----------|-------|
| **Service** | `metapm-v2` |
| **URL** | https://metapm.rentyourcio.com |
| **GCP Project** | `super-flashcards-475210` |
| **Region** | `us-central1` |
| **Database** | `MetaPM` on `flashcards-db` instance |
| **Current Revision** | `metapm-v2-00013-662` |
| **Version** | v1.4.3 |

### Sprint 4 Status: CANCELED

| Feature | Status | Notes |
|---------|--------|-------|
| 1. Playwright Test Coverage | ⚠️ Unclear | No formal handoff received |
| 2. Theme Management UI | ✅ Complete | metapm-v2-00012-gtf, 4 tests pass |
| 3. Violation AI Assistant | ❌ Canceled | Command Center model replaces this |

See `SPRINT_4_CANCELED.md` for details.

---

## What's Working (Deployed & Tested)

### Sprint 3 Features (All Complete)
- ✅ **Project Color Themes** - Peacock-style color picker per project
- ✅ **Favicon** - All sizes deployed
- ✅ **Task Sort by Modified** - Multiple sort options
- ✅ **Dark/Light/Auto Toggle** - UI appearance theming with localStorage
- ✅ **Offline Sync (PWA)** - IndexedDB, sync queue, service worker
- ✅ **Expand/Collapse Tasks** - On Projects tab

### Sprint 4 Features (Complete)
- ✅ **Theme Management UI** - CRUD for project categorization themes

### Core Functionality (Previous Sprints)
- ✅ 4-tab dashboard (Tasks, Projects, Methodology, Capture)
- ✅ Full CRUD APIs for tasks, projects, categories
- ✅ Voice/text task capture
- ✅ Methodology rules and violations tracking
- ✅ Cross-project task linking
- ✅ Mobile-responsive PWA

---

## Key Decisions Made

| Decision | Date | Rationale |
|----------|------|-----------|
| Service renamed `metapm` → `metapm-v2` | Jan 2026 | Old service had Docker cache issues |
| Old `metapm` service deleted | Jan 30, 2026 | Avoid confusion |
| DB_SERVER changed to TCP IP | Jan 31, 2026 | Unix socket path broke pyodbc (LL-050) |
| Sprint 4 Violation AI canceled | Jan 31, 2026 | Command Center model replaces it |

---

## Lessons Learned (From This Project)

| LL | Title |
|----|-------|
| LL-045 | AI Must Read Existing Docs First |
| LL-046 | No Import-Time Database Calls |
| LL-047 | Sprint Documentation Checklist |
| LL-048 | Claude Also Reads Docs First |
| LL-049 | "Complete" Requires Test Proof |
| LL-050 | Audit Must Verify Connectivity, Not Just Existence |

---

## Deployment Commands

### Standard Deploy
```powershell
gcloud run deploy metapm-v2 `
  --source . `
  --region us-central1 `
  --allow-unauthenticated `
  --set-env-vars="DB_SERVER=35.224.242.223,DB_NAME=MetaPM,DB_USER=sqlserver,ENVIRONMENT=production" `
  --set-secrets="DB_PASSWORD=db-password:latest" `
  --add-cloudsql-instances="super-flashcards-475210:us-central1:flashcards-db"
```

### Health Check
```powershell
curl https://metapm.rentyourcio.com/health
```

---

**Status**: Sprint 4 canceled. Next work TBD.
