# MetaPM V2 Architecture Prompt for VS Code

Copy this entire prompt to VS Code Copilot when starting work on MetaPM.

---

## PROMPT START

You are working on MetaPM, a cross-project task management system with AI integration.

### Project Overview

MetaPM is a FastAPI application that:
1. Manages tasks across 21+ projects (ArtForge, Etymython, HarmonyLab, Super-Flashcards, etc.)
2. Provides voice capture via OpenAI Whisper transcription + Claude understanding
3. Stores complete AI conversation history for searchable memory
4. Tracks methodology violations from project-methodology v3.12.1

### Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11+ / FastAPI |
| Database | MS SQL Server on GCP Cloud SQL |
| Deployment | GCP Cloud Run |
| Secrets | Google Secret Manager (NOT .env files) |
| Storage | Google Cloud Storage (for audio/media) |
| AI - Transcription | OpenAI Whisper API |
| AI - Understanding | Anthropic Claude API |

### Key Architecture Decisions

1. **Cloud-First**: No localhost servers. Write → Push → Deploy → Test on Cloud Run
2. **Secret Manager**: All API keys and passwords come from Google Secret Manager
3. **Transaction History**: Every AI interaction is logged with full prompt/response for searchable memory
4. **Media Storage**: Audio files and screenshots stored in GCS, references in SQL

### Directory Structure

```
metapm/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── api/
│   │   ├── tasks.py         # Task CRUD
│   │   ├── projects.py      # Project registry
│   │   ├── categories.py    # Category management
│   │   ├── methodology.py   # Methodology rules & violations
│   │   ├── capture.py       # Quick text capture
│   │   ├── voice.py         # Voice capture (Whisper + Claude)
│   │   └── transactions.py  # History, search, analytics
│   ├── core/
│   │   ├── config.py        # Settings (loads from Secret Manager)
│   │   ├── database.py      # SQL Server connection
│   │   └── secrets.py       # Google Secret Manager client
│   └── models/
│       ├── task.py          # Task Pydantic models
│       ├── project.py       # Project models
│       ├── methodology.py   # Methodology models
│       └── transaction.py   # Transaction/conversation models
├── tests/
│   ├── test_api_smoke.py    # Basic endpoint tests
│   ├── test_api_integration.py  # CRUD flow tests
│   └── test_ui_smoke.py     # Playwright tests
├── scripts/
│   ├── schema.sql           # V1 database schema
│   ├── schema_v2_transactions.sql  # V2 additions
│   ├── seed_methodology_rules.sql  # Methodology rules
│   └── setup-gcp.ps1        # GCP setup script
└── docs/
    ├── METHODOLOGY.md       # Quick reference
    └── TEST_PLAN.md         # Testing requirements
```

### Database Tables

**Core Tables:**
- Projects - Registry of all 21 projects
- Tasks - Central task list with priority, status, dates
- Categories - User-maintainable (ACTION, IDEA, BUG, etc.)
- TaskProjectLinks - Many-to-many task↔project
- TaskCategoryLinks - Many-to-many task↔category

**Methodology Tables:**
- MethodologyRules - Rules from LESSONS_LEARNED.md
- MethodologyViolations - Violation log

**Transaction History Tables (V2):**
- Conversations - Groups related exchanges
- Transactions - Every prompt/response pair
- MediaFiles - Audio, images in GCS
- TransactionMedia - Links media to transactions

### API Endpoints

| Prefix | Purpose |
|--------|---------|
| /api/tasks | Task CRUD |
| /api/projects | Project registry |
| /api/categories | Category management |
| /api/methodology | Rules and violations |
| /api/capture | Quick text capture |
| /api/voice | Voice capture (audio upload) |
| /api/history | Transaction history, search, analytics |

### Voice Capture Flow

```
1. Mobile app records audio
2. POST /api/voice/voice with audio file
3. Audio uploaded to GCS
4. OpenAI Whisper transcribes audio
5. Claude extracts intent, project, categories
6. Task created if intent = CREATE_TASK
7. Transaction logged with full history
8. Response returned to user
```

### Secrets Required (in Google Secret Manager)

- `metapm-db-password` - Database password
- `openai-api-key` - For Whisper transcription
- `anthropic-api-key` - For Claude understanding

### Critical Methodology Rules

1. **No .env for secrets** - Use Secret Manager
2. **Test before handoff** - Run Playwright tests
3. **PowerShell not bash** - Use .ps1, $env:VAR syntax
4. **Cloud-first** - No localhost servers
5. **Verify GCP project** - Check before every deploy

### Current Sprint Focus

[To be filled in by Project Lead]

---

## PROMPT END

When working on this project:
1. Read relevant documentation before coding
2. Use Google Secret Manager for all credentials
3. Run tests before handoff
4. Follow project-methodology v3.12.1
