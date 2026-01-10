# Project Methodology & Best Practices

A battle-tested methodology for building AI-powered applications on Google Cloud Platform, developed through real-world experience with projects like ArtForge, HarmonyLab, Etymython, and Super-Flashcards.

## Why This Exists

When working with VS Code AI assistants on new projects, the same issues kept appearing:
- AI assumed local development (localhost, .env files) instead of cloud-first
- Responsibilities between human and AI unclear
- Authentication order wrong (password prompts blocking progress)
- No testing, UI design, or documentation planned
- "Done" meant code written, not actually deployed and usable

This methodology captures lessons learned and provides a repeatable framework for successful project delivery.

## Quick Start

### Starting a New Project

1. **Review the Pre-Kickoff Checklist** → `checklists/PRE_KICKOFF_CHECKLIST.md`
2. **Generate a Project Kickoff** using the template → `PROJECT_KICKOFF_TEMPLATE.md`
3. **Follow Sprint 1** (Infrastructure & API) → `checklists/SPRINT_1_CHECKLIST.md`
4. **Follow Sprint 2** (Testing & UI) → `checklists/SPRINT_2_CHECKLIST.md`
5. **Verify Deployment** → `checklists/DEPLOYMENT_CHECKLIST.md`

### Key Principles

| Principle | What It Means |
|-----------|---------------|
| **Cloud-First** | No localhost servers. Write → Push → Deploy → Test on Cloud Run URL |
| **Secrets in Secret Manager** | Never .env files. All secrets in Google Secret Manager |
| **Clear Responsibilities** | Explicit matrix of who does what (Human / Claude / VS Code AI) |
| **Two-Sprint Model** | Sprint 1 = Working backend. Sprint 2 = Tested, polished, documented |
| **Smoke Tests Before Users** | "Deployed" ≠ "Working". Verify app works before user testing |
| **Backups Verified** | Every database has automated backups enabled and verified |
| **RTFM First** | AI must read documentation before writing code |
| **Positive Instructions** | State what TO DO, not just what NOT to do |
| **External Verification** | The programmer cannot grade their own test |
| **Unit Before Bulk** | Never skip from "code written" to "bulk execution" |
| **Persist Immediately** | Never store temporary API URLs; download and persist to your storage |
| **No Diffs** | Always provide complete files, never diffs or snippets |
| **Test the Code Path** | When fixing bugs, test the broken code before fixing the data |
| **Push at Checkpoints** | Git push after fixes, features, sessions—minimum daily |
| **Session Auth is Human** | GCP auth requires browser/passkey; AI must stop and request re-auth |
| **Developer Tests First** | Test your own work before ANY handoff; PL reviews working code, not bugs |
| **Playwright for UI** | VS Code can't open browsers; Playwright gives it "eyes" for UI testing |
| **PowerShell Not Bash** | All scripts use PowerShell syntax (.ps1, $env:VAR, ;) not bash |
| **AI Researches First** | AI uses available tools for research; PL time is for decisions |
| **Surface Scan First** | Audit everything at surface level before rabbit-holing into fixes |
| **Verify GCP Project** | Check `gcloud config get-value project` before every deploy |
| **Version Numbers** | Every deploy has visible version; verify deployed == tested |
| **Definition of Done** | Not done until deployed, tested, documented, and usable |

## Repository Structure

```
project-methodology/
├── README.md                     # This file
├── PROJECT_KICKOFF_TEMPLATE.md   # Master template for new projects
├── LESSONS_LEARNED.md            # Detailed log of issues and fixes
├── CHANGELOG.md                  # Version history
├── PRE_KICKOFF_CHECKLIST.md      # Questions before starting
├── SPRINT_1_CHECKLIST.md         # Infrastructure, API & Smoke tests
├── SPRINT_2_CHECKLIST.md         # Testing & UI tasks
├── DEPLOYMENT_CHECKLIST.md       # GCP setup verification
├── TEST_PLAN_TEMPLATE.md         # Testing documentation template
├── UI_DESIGN_TEMPLATE.md         # UI/UX design template
├── USER_GUIDE_TEMPLATE.md        # End-user documentation template
├── SMOKE_TEST_TEMPLATE.md        # Deployment verification tests
├── BACKUP_VERIFICATION.md        # Database backup verification
├── VIOLATION_RESPONSE.md         # Handling methodology violations
├── VERIFICATION_GOVERNANCE.md    # Golden Audit governance model
├── UNICODE_HANDLING.md           # Non-ASCII encoding requirements
├── EXTERNAL_API_HANDLING.md      # Temporary resource persistence
├── VS_CODE_TESTING_REQUIREMENTS.md # Automated testing requirements for VS Code
└── ARTFORGE_KICKOFF.md           # Real example for reference
```

## Technology Stack

This methodology is optimized for:

- **Cloud**: Google Cloud Platform (Cloud Run, Cloud SQL, Secret Manager, GCS)
- **Backend**: Python 3.12.10 + FastAPI (NOT 3.13 due to ODBC compatibility)
- **Database**: MS SQL Server on Cloud SQL
- **CI/CD**: GitHub Actions
- **Development**: VS Code with AI assistants (Copilot, Cursor)
- **Authentication**: GitHub Passkey, Google OAuth

## How to Reference This Methodology

In each project's README, add:

```markdown
## Development Methodology
This project follows [coreyprator/project-methodology](https://github.com/coreyprator/project-methodology) v3.12.1
```

## Version

Current: **v3.12.1** (January 2026)

See `CHANGELOG.md` for version history.

## Contributing

This is a personal methodology repository. Lessons learned from each project are captured and incorporated into future versions.

To add a lesson learned:
1. Document the issue, root cause, and fix
2. Update `LESSONS_LEARNED.md`
3. Update relevant template sections
4. Increment version in `CHANGELOG.md`

## Author

**Corey Prator** - Software Developer & Project Lead
- 20+ years development experience
- Specializing in AI-powered applications on GCP
