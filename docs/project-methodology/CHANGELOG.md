# Changelog

All notable changes to this methodology are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.12.1] - 2026-01-09

### Added
- **LL-037**: Version Numbers - Verify Deployed == Tested
- **VS_CODE_TESTING_REQUIREMENTS.md**: Comprehensive automated testing requirements for VS Code AI
- **Application Version Numbers** (PROJECT_KICKOFF_TEMPLATE.md): Requirements for visible versioning
- **Version Implementation Examples**: Frontend (HTML, console) and backend (API, health check)
- **Deployment Handoff Format**: Template including version verification

### Key Insight

**LL-037: Version Numbers**
> Every deployment must have a visible version number. Communicate in handoff so tester can verify: "Please confirm you see v1.2.3 before testing."

**VS_CODE_TESTING_REQUIREMENTS.md**
> VS Code cannot manually test. It must use Playwright for UI, pytest for API, and provide test output in every handoff. "No test output = no handoff."

---

## [3.12.0] - 2026-01-06

### Added
- **LL-033**: AI Agents Must Use AI Tools for Domain Research (not delegate to Project Lead)
- **LL-034**: Complete the Audit Before Going Deep (surface scan first)
- **LL-035**: Audit Coverage Must Match Data Model (cover all categorical values)
- **LL-036**: Verify GCP Project Before Every Deploy
- **Pre-Deploy Code Review Checklist** (PROJECT_KICKOFF_TEMPLATE.md): Check for TODOs, empty functions, initialization order
- **AI Research Responsibility** (PROJECT_KICKOFF_TEMPLATE.md): When to research vs. when to ask
- **Audit Coverage Section** (VERIFICATION_GOVERNANCE.md): Ensure all categorical values covered
- **Complete the Audit Before Going Deep** (VERIFICATION_GOVERNANCE.md): Surface scan protocol
- **GCP Project Verification** (DEPLOYMENT_CHECKLIST.md): Prominent warning before deploys

### Changed
- Enhanced DEPLOYMENT_CHECKLIST.md with critical project verification warning

### Key Insights

**LL-033: AI Research Responsibility**
> AI agents have research capabilities. Use them. Project Lead's time is for decisions, not research.

**LL-034: Surface Scan First**
> Test everything at surface level, report complete findings, get prioritization, THEN fix systematically.

**LL-035: Audit Coverage**
> If a data model has N categorical values, the audit must cover all N values.

**LL-036: Verify GCP Project**
> Before ANY `gcloud run deploy`: `gcloud config get-value project`. Wrong project = broken deployment.

---

## [3.11.0] - 2026-01-03

### Added
- **LL-031**: VS Code AI Cannot Manually Test - Playwright Required
- **LL-032**: Shell Environment - PowerShell Not Bash
- **Shell Environment: PowerShell** (PROJECT_KICKOFF_TEMPLATE.md Phase 0.4): Explicit standard with conversion table
- **Playwright for UI Testing** (PROJECT_KICKOFF_TEMPLATE.md Phase 1): VS Code's "eyes" for UI projects
- **Minimum Smoke Test Template**: Ready-to-use Playwright test for console errors, visibility, mobile viewport

### Changed
- Renumbered Phase 0.4 Development Workflow to Phase 0.5

### Key Insights

**LL-031: Playwright Required for UI**
> VS Code AI literally cannot open a browser, use DevTools, or see console errors. Playwright gives VS Code "eyes" to programmatically test. "Playwright tests passing" replaces "I tested it manually."

**LL-032: PowerShell Not Bash**
> All scripts use PowerShell (pwsh), not bash. Use `.ps1` not `.sh`, `$env:VAR` not `$VAR`, `;` not `&&`, `$null` not `/dev/null`.

---

## [3.10.2] - 2026-01-03

### Added
- **LL-030**: Developer Tests Before Handoff - Universal Principle (applies to ALL work, not just Sprint 1)
- **Developer Tests Before Handoff** (PROJECT_KICKOFF_TEMPLATE.md): Universal section covering frontend, API, database, scripts, bug fixes
- **Self-Verification Requirements**: Matrix of what to verify for each work type
- **Handoff Report Template**: Required format when requesting Project Lead review

### Changed
- Moved handoff testing requirements from Sprint 1 to universal Phase 1 section
- Updated VIOLATION_RESPONSE.md quick reference with 5 new violation types (LL-025 through LL-030)

### Key Insight

**LL-030: Developer Tests Before Handoff**
> Do not hand off ANY work for review until you have tested it yourself. This applies to frontend, API, database, scripts, bug fixes—everything. Project Lead's time is for reviewing WORKING code, not debugging errors you should have caught.

---

## [3.10.1] - 2026-01-02

### Added
- **LL-029**: Session Start Authentication - Human Responsibility
- **Session Start Script** (PROJECT_KICKOFF_TEMPLATE.md Phase 0.1): Reusable PowerShell script for GCP auth
- **AI Behavior When Blocked** (PROJECT_KICKOFF_TEMPLATE.md Phase 0.1): Clear protocol for password prompt encounters
- **Re-Authentication Triggers**: Documented when tokens expire and re-auth is needed

### Key Insight

**LL-029: Session Start Authentication**
> GCP auth is human-only. Browser/Passkey authentication cannot be done by AI. If AI encounters password prompt: STOP, request re-auth, wait for confirmation.

---

## [3.10.0] - 2026-01-02

### Added
- **EXTERNAL_API_HANDLING.md**: New guide for persisting temporary API resources immediately
- **Code Delivery Standards** (PROJECT_KICKOFF_TEMPLATE.md): Always provide complete files, never diffs
- **Version Control Best Practices** (PROJECT_KICKOFF_TEMPLATE.md): Push at logical checkpoints
- **Bug Fix Verification: Test the Code Path** (PROJECT_KICKOFF_TEMPLATE.md Appendix D): Must test the broken code, not just fix data
- **LL-025**: External API temporary resources must be persisted immediately (DALL-E URLs expire in 2hrs)
- **LL-026**: Always provide complete files, never diffs or snippets
- **LL-027**: Test the code path that caused a bug before fixing the data it created
- **LL-028**: Git push at logical checkpoints, not only when asked

### Changed
- **Appendix D Error Recovery**: Expanded with "Test the Code Path" section
- **Appendix E**: Added EXTERNAL_API_HANDLING.md reference

### Key Insights

**LL-025: Persist Immediately**
> NEVER store temporary URLs in persistent database fields. Download and persist to YOUR storage immediately.

**LL-026: No Diffs**
> Extra seconds to generate complete file saves significant debugging time. AI token costs are trivial compared to human merge-error debugging.

**LL-027: Test the Code Path**
> If you don't exercise the exact code path that was broken, you don't actually know if your fix works.

**LL-028: Push at Checkpoints**
> Unpushed code is unprotected code. Push after fixes, features, sessions—minimum daily.

---

## [3.9.0] - 2026-01-01

### Added
- **VIOLATION_RESPONSE.md**: New template for handling methodology violations with standard response protocol
- **VERIFICATION_GOVERNANCE.md**: Golden Audit governance model - truth sources owned by Architect, read-only for VS Code
- **UNICODE_HANDLING.md**: Encoding requirements for non-ASCII data (Python + SQL Server)
- **Pre-Work Checklist** (PROJECT_KICKOFF_TEMPLATE.md): Mandatory documentation review before coding
- **Automation Requirements** (PROJECT_KICKOFF_TEMPLATE.md): Positive instructions (what TO DO) instead of just prohibitions
- **Appendix D: Error Recovery Protocol** (PROJECT_KICKOFF_TEMPLATE.md): STOP → PRESERVE → ISOLATE → VERIFY → APPLY
- **Phase 5.5: Mandatory Testing Sequence** (SPRINT_1_CHECKLIST.md): Smoke → Unit → Small Batch → Bulk
- **Bulk Operation Checklist** (SPRINT_1_CHECKLIST.md): Required verification before bulk operations
- **LL-018 through LL-024**: Seven lessons from Etymython Sprint 3-4

### Changed
- **Responsibility Matrix Clarification**: Now includes pre-work checklist and positive automation instructions
- **Sprint 1 Checklist**: Added testing sequence and bulk operation requirements

### Key Insights

**LL-018: RTFM**
> AI agents must be explicitly required to read documentation before coding.

**LL-019: Automation First**
> State what TO DO (one correct choice), not what NOT to do (infinite wrong choices).

**LL-020: External Verification**
> The programmer cannot grade their own test. Golden Audit = single source of truth.

**LL-022: Unit Before Bulk**
> NEVER skip from "code written" to "bulk execution".

**LL-023: Unicode Handling**
> String comparison doesn't catch encoding bugs. Always verify with UNICODE() values.

**LL-024: Error Recovery**
> Each "fix" attempt can make data worse. Stop and plan before acting.

---

## [3.8.0] - 2025-12-31

### Added
- **BACKUP_VERIFICATION.md**: New template with automated PowerShell script to verify all Cloud SQL backups
- **Database Backup & DR section** (SPRINT_1_CHECKLIST.md): Required backup configuration before user testing
- **Backup Configuration section** (DEPLOYMENT_CHECKLIST.md): Verification that backups are enabled and successful
- **Backup questions** (PRE_KICKOFF_CHECKLIST.md): Retention period, PITR, and backup window decisions
- **LL-017**: Database backups must be verified, not assumed

### Changed
- **Sprint 1 Definition of Done**: Now requires "Database backups enabled and verified"
- **README.md**: Added "Backups Verified" principle

### Key Insight
> **Backups must be verified, not assumed.**
> 
> Every database needs: automated backups enabled, PITR for production, retention period set, and at least one successful backup completed.

---

## [3.7.0] - 2025-12-30

### Added
- **Smoke Test Template** (SMOKE_TEST_TEMPLATE.md): Layered smoke tests to verify deployment works before user testing
- **Phase 6: Smoke Testing** (SPRINT_1_CHECKLIST.md): Required verification phase between deployment and user testing
- **Test Types and Purposes** (PROJECT_KICKOFF_TEMPLATE.md): Clarifies smoke vs unit vs integration tests
- **Testing Sequence for New Features**: Write code → Deploy → Smoke test → User test → Unit tests
- **LL-014**: Smoke tests required before user testing (ArtForge "Internal Server Error" incident)
- **LL-015**: Smoke tests vs unit tests serve different purposes
- **LL-016**: Testing phase sequence for new vs existing features

### Changed
- **Sprint 1 Definition of Done**: Now requires smoke tests pass, no 500 errors, user can load app
- **Testing Philosophy**: Added test type matrix and sequence guidance

### Fixed
- "Deployed" being confused with "Working"
- Unit tests blocking deployment when behavior was never verified
- Users discovering 500 errors instead of automated tests catching them

### Key Insight
> **"Deployed" ≠ "Working"**
> 
> Smoke tests fill the gap between deployment and user testing by verifying the deployed app actually works.

---

## [3.6.0] - 2024-12-28

### Added
- **Passkey Authentication Script** (Phase 0.1): Explicit success/failure indicators for each authentication step
- **Responsibility Matrix Clarification** (Phase 1): Emphasizes VS Code AI must execute, not instruct
- **Cloud Migration Script Template** (Appendix C): Executable PowerShell script for automating cloud migration
- **LL-013**: Documents delegation anti-pattern from HarmonyLab migration

### Changed
- **Authentication Flow**: Now includes "AFTER THIS POINT" marker clarifying VS Code AI runs all subsequent gcloud commands
- **Responsibility Matrix**: Added comparison table showing wrong vs. correct VS Code AI behavior

### Fixed
- Ambiguity about who runs gcloud commands after authentication
- VS Code AI interpreting responsibility matrix as "instruct user" rather than "execute directly"

---

## [3.5.0] - 2024-12-27

### Added
- **Meta-project structure**: Organized methodology into dedicated repository
- **Pre-Kickoff Checklist**: Standalone document for questions before kickoff
- **Sprint Checklists**: Separate checklists for Sprint 1 and Sprint 2
- **Deployment Checklist**: GCP verification steps
- **Document Templates**: TEST_PLAN, UI_DESIGN, USER_GUIDE templates
- **ArtForge Example**: Real-world kickoff document for reference

### Changed
- **Repository structure**: From single document to organized folder structure
- **Lessons learned**: Moved to dedicated LESSONS_LEARNED.md with detailed context

---

## [3.4.0] - 2024-12-27

### Added
- **Help Content Strategy** (Section 0.12): External link approach vs embedded docs
- **Definition of Done** (Section 0.16): Explicit completion criteria for both sprints

### Changed
- **Testing Philosophy**: Added distinction between happy path errors and system errors

---

## [3.3.0] - 2024-12-27

### Added
- **Testing Philosophy** (Section 0.11): Guidelines for what to test and error messages
- **Required Documentation** (Section 0.10): TEST_PLAN.md, UI_DESIGN.md, USER_GUIDE.md
- **Document Templates** (Sections 0.13-0.15): Starter templates for required docs

### Changed
- **Responsibility Matrix**: Added TEST_PLAN.md, UI_DESIGN.md, USER_GUIDE.md to Claude deliverables

---

## [3.2.0] - 2024-12-27

### Added
- **Sprint Planning Requirements** (Section 0.9): Two-sprint model defined
  - Sprint 1: Infrastructure & API
  - Sprint 2: Testing, UI/UX, Documentation

### Changed
- **Responsibility Matrix**: Clarified that VS Code AI implements tests in Sprint 2

---

## [3.1.0] - 2024-12-27

### Added
- **GitHub & Deployment Workflow** (Section 0.7): Git init, push, Cloud Run URL retrieval
- **Responsibility Matrix** (Section 0.8): Explicit task assignments

### Fixed
- **LL-007**: Git initialization now in VS Code AI responsibilities
- **LL-001**: Database user creation now in VS Code AI responsibilities

---

## [3.0.0] - 2024-12-27

### Added
- **Development & Testing Environment** (Section 0.5): NO LOCALHOST rule
- **Kickoff Document Variables** (Section 0.6): Standardized placeholders

### Changed
- **Major restructure**: Moved from implicit assumptions to explicit documentation
- **Workflow**: Established cloud-first development pattern

### Fixed
- **LL-006**: Added "No localhost servers" section

---

## [2.0.0] - 2024-12-27

### Added
- **Authentication Flow** (Section 0.3): Exact command order to avoid password prompts
- **SQL Execution Environment** (Section 0.4): Tool selection for GO statements
- **GCP Project Guidance** (Section 0.2): When to use shared vs dedicated projects

### Fixed
- **LL-002**: Authentication order documented
- **LL-003**: Project verification added
- **LL-005**: SQL tool selection documented

---

## [1.0.0] - 2024-12-27

### Added
- **Pre-Kickoff Questions** (Section 0.1): Questions Claude asks before generating kickoff
- **Initial Lessons Learned Log**: First entries from ArtForge development

### Notes
- First formal version of the methodology
- Based on accumulated experience from ArtForge, HarmonyLab planning, Etymython, Super-Flashcards

---

## Version Numbering

- **Major** (X.0.0): Significant restructuring or new phases
- **Minor** (0.X.0): New sections or features added
- **Patch** (0.0.X): Clarifications, typo fixes, minor updates

## Contributing

When adding changes:
1. Add entry under `[Unreleased]` section
2. When releasing, move to versioned section with date
3. Reference Lessons Learned entries (LL-XXX) where applicable
