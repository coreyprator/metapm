# Lessons Learned Log

This document captures issues encountered during project development, their root causes, and the fixes applied to the methodology.

## Format

Each entry includes:
- **Date**: When the issue was encountered
- **Project**: Which project surfaced the issue
- **Issue**: What went wrong
- **Root Cause**: Why it happened
- **Fix Applied**: How the methodology was updated
- **Template Section**: Where the fix lives

---

## 2024-12 Lessons (v3.5)

### LL-001: VS Code AI Didn't Create Database User

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | VS Code AI generated code expecting database user, but never created the user in SQL Server |
| Root Cause | Responsibility for database user creation was not explicitly assigned |
| Fix Applied | Added "Create database & user in SQL" to VS Code AI responsibilities in the Responsibility Matrix |
| Template Section | Phase 1: Responsibility Matrix |

**Impact**: Deployment failed with authentication errors. Required manual intervention to create the database user.

---

### LL-002: Password Prompt Blocking GCP Commands

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | `gcloud config set project` prompted for password, blocking automated workflows |
| Root Cause | Authentication order was wrong—project was set before browser auth completed |
| Fix Applied | Created Phase 0 with explicit authentication order. Added warning about password prompts. |
| Template Section | Phase 0: Pre-Kickoff Setup, Section 0.1 |

**Impact**: VS Code AI couldn't proceed with gcloud commands. User had to manually intervene with authentication.

**Key Learning**: The correct order is:
1. `gcloud auth login` (browser/Passkey)
2. `gcloud auth application-default login`
3. `gcloud config set project` (should NOT prompt)
4. `gcloud auth application-default set-quota-project`

---

### LL-003: Wrong GCP Project Selected

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | Commands ran against wrong GCP project, creating resources in unexpected location |
| Root Cause | Project was not verified at the start of the session |
| Fix Applied | Added project verification step after authentication |
| Template Section | Phase 0: Pre-Kickoff Setup, Section 0.2 |

**Impact**: Had to clean up resources from wrong project and recreate in correct project.

---

### LL-004: "Project Does Not Exist" Errors

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | HarmonyLab (planning) |
| Issue | Kickoff document referenced GCP project that hadn't been created yet |
| Root Cause | Decision to use new vs. existing project wasn't made upfront |
| Fix Applied | Added pre-kickoff questions about GCP project choice |
| Template Section | Pre-Kickoff Checklist (separate document) |

**Impact**: Wasted time debugging "project not found" errors that were actually planning issues.

---

### LL-005: SQL Scripts Failed in Cloud SQL Studio

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | SQL scripts with GO statements failed in Cloud SQL Studio |
| Root Cause | Cloud SQL Studio doesn't support GO batch separator |
| Fix Applied | Added SQL Execution Environment section specifying which tool to use |
| Template Section | Phase 0: Pre-Kickoff Setup, Section 0.3 |

**Impact**: Schema creation failed. Had to re-run scripts in SSMS.

**Key Learning**: 
- SSMS/sqlcmd: Full T-SQL support including GO
- Cloud SQL Studio: Single statements only

---

### LL-006: VS Code AI Ran Localhost Server

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | VS Code AI started local development server with `uvicorn` instead of deploying to Cloud Run |
| Root Cause | Default developer workflow is local-first; cloud-first not documented |
| Fix Applied | Added "NO LOCALHOST SERVERS" section with cloud-first workflow diagram |
| Template Section | Phase 0: Pre-Kickoff Setup, Section 0.4 |

**Impact**: Testing was done against localhost, then failed on Cloud Run due to environment differences.

**Key Learning**: The workflow is always: Write → Push → Deploy → Test on Cloud Run URL

---

### LL-007: Git Repository Not Initialized

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | VS Code AI generated code but didn't initialize git or push to GitHub |
| Root Cause | Git initialization wasn't in the task list |
| Fix Applied | Added git init, remote add, commit, push to VS Code AI responsibilities |
| Template Section | Phase 1: Responsibility Matrix |

**Impact**: Code sat locally; GitHub Actions never triggered.

---

### LL-008: No Test Plan Created

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | Sprint 1 completed but no tests existed and no plan for what to test |
| Root Cause | TEST_PLAN.md wasn't a required deliverable |
| Fix Applied | Added TEST_PLAN.md to Claude's required deliverables; added to Sprint 1 DoD |
| Template Section | Phase 1: Responsibility Matrix, Phase 3: Sprint 1 DoD |

**Impact**: Sprint 2 started without clarity on what needed testing.

---

### LL-009: No UI Design Document

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | Frontend development started without any UI design specification |
| Root Cause | UI_DESIGN.md wasn't a required deliverable |
| Fix Applied | Added UI_DESIGN.md to Claude's required deliverables |
| Template Section | Phase 1: Responsibility Matrix |

**Impact**: Frontend had to be reworked multiple times due to unclear requirements.

---

### LL-010: Users Confused by Application

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | Users didn't understand how to use the application |
| Root Cause | No user documentation existed |
| Fix Applied | Added USER_GUIDE.md to Claude's required deliverables |
| Template Section | Phase 1: Responsibility Matrix |

**Impact**: Support burden on developer; users abandoned application.

---

### LL-011: Technical Errors Exposed to Users

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | Users saw errors like `NoneType has no attribute 'id'` |
| Root Cause | No guidelines for user-friendly error messages |
| Fix Applied | Added Testing Philosophy section with error message guidelines |
| Template Section | Phase 4: Sprint 2, Section 4.1 |

**Impact**: Users confused by technical errors; poor user experience.

**Key Learning**:
- Happy path errors: User-friendly messages
- System errors: Can bubble up (users have AI to explain)

---

### LL-012: Help Content Embedded in Application

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | Help documentation was embedded in React components |
| Root Cause | No strategy defined for help content |
| Fix Applied | Changed to external link strategy—help links to GitHub docs |
| Template Section | Phase 4: Sprint 2, Section 4.2 |

**Impact**: Every documentation fix required a full redeploy.

**Key Learning**: External help links allow doc updates without app deployment.

---

## 2024-12 Lessons (v3.6)

### LL-013: VS Code AI Delegated Automation to Project Lead

| Field | Value |
|-------|-------|
| Date | 2024-12-28 |
| Project | HarmonyLab |
| Issue | VS Code AI told Project Lead to manually create secrets and run gcloud commands instead of automating |
| Root Cause | Responsibility matrix listed tasks but didn't emphasize automation over instruction |
| Fix Applied | Added "Responsibility Matrix Clarification" section; created cloud migration script template |
| Template Section | Phase 1: Responsibility Matrix, Appendix C: Cloud Migration Script |

**Impact**: Project Lead had to repeatedly redirect VS Code AI to automate tasks. Slowed migration by 2+ hours.

**Key Learning**: 
- VS Code AI must execute, not instruct
- Provide executable script templates, not command lists
- The only manual step is Passkey authentication (Phase 0.1)

---

## 2025-12 Lessons (v3.7)

### LL-014: Smoke Tests Before User Testing

| Field | Value |
|-------|-------|
| Date | 2025-12-30 |
| Project | ArtForge |
| Issue | User attempted to test ArtForge UI but received "Internal Server Error: Unexpected token 'I'" - could not test any functionality |
| Root Cause | Sprint 1 Definition of Done only checked "code deployed" - no verification that the deployed app actually works |
| Fix Applied | Added "Deployment Verification" phase with layered smoke tests between deployment and user testing |
| Template Section | SPRINT_1_CHECKLIST.md Phase 5, SMOKE_TEST_TEMPLATE.md |

**Impact**: 
- User testing completely blocked
- Debug cycle added: diagnose → fix → redeploy → test
- Confusion about whether unit tests or deployment was the problem

**Key Learning**: "Deployed" ≠ "Working". Smoke tests verify the deployed app works before users touch it.

---

### LL-015: Smoke Tests vs Unit Tests - Different Purposes

| Field | Value |
|-------|-------|
| Date | 2025-12-30 |
| Project | ArtForge |
| Issue | Team was stuck deciding between "fix 21 failing unit tests" vs "deploy anyway" - neither option addressed the real problem |
| Root Cause | Confusion about test types: unit tests verify code logic with mocks, smoke tests verify deployed app works |
| Fix Applied | Added "Test Types and Purposes" section clarifying when each test type is required |
| Template Section | PROJECT_KICKOFF_TEMPLATE.md Phase 4.1 Testing Philosophy |

**Impact**:
- Hours spent on wrong priority
- Unit tests written for unverified behavior
- No tests for actual deployment health

**Key Learning**: 
- Smoke tests: Run against deployed URL, verify app works
- Unit tests: Run against mocks, verify code logic
- The 21 failing unit tests were testing *assumed* behavior - the app had never been verified to work

---

### LL-016: Testing Phase Sequence

| Field | Value |
|-------|-------|
| Date | 2025-12-30 |
| Project | ArtForge |
| Issue | Tests were written before confirming the feature worked, then blocked deployment when they failed |
| Root Cause | Assumed sequence was: Write code → Write tests → Deploy → User test |
| Fix Applied | Documented correct sequence for new features vs existing features |
| Template Section | PROJECT_KICKOFF_TEMPLATE.md Phase 4.1 Testing Philosophy |

**Impact**: 
- Circular dependency: Can't deploy because tests fail, can't verify behavior because not deployed
- Tests based on assumptions, not reality

**Key Learning**: For NEW features:
```
Write code → Deploy → Smoke test → User test → Write unit tests based on verified behavior
```
For EXISTING features: Unit tests are blocking (prevent regression).

---

### LL-017: Database Backups Not Verified

| Field | Value |
|-------|-------|
| Date | 2025-12-31 |
| Project | All Projects |
| Issue | Databases deployed to production without verified backup and disaster recovery configuration |
| Root Cause | No backup verification step in Sprint 1 checklist or deployment verification |
| Fix Applied | Added backup configuration to Sprint 1 checklist, DEPLOYMENT_CHECKLIST, PRE_KICKOFF_CHECKLIST; created BACKUP_VERIFICATION.md with automated verification script |
| Template Section | SPRINT_1_CHECKLIST.md, DEPLOYMENT_CHECKLIST.md, PRE_KICKOFF_CHECKLIST.md, BACKUP_VERIFICATION.md |

**Impact**: 
- Risk of data loss without recovery option
- No disaster recovery capability for production databases
- Potential compliance/audit issues

**Key Learning**: 
- Backups must be verified, not assumed
- Every database needs: automated backups enabled, PITR for production, verified retention period
- Automated verification script catches gaps across all instances

---

## 2026-01 Lessons (v3.9)

### LL-018: RTFM - AI Agents Don't Read Project Documentation

| Field | Value |
|-------|-------|
| Date | 2026-01-01 |
| Project | Etymython |
| Issue | VS Code built Sprint 4 content generation without consulting the database schema. Result: queries that don't match actual table structures, JOINs that fail, misunderstanding of data relationships |
| Root Cause | AI agents start coding immediately without reviewing existing documentation, schemas, or prior work |
| Fix Applied | Added Pre-Work Checklist (mandatory before writing code) and Violation Response Protocol |
| Template Section | PROJECT_KICKOFF_TEMPLATE.md Phase 3, VIOLATION_RESPONSE.md |

**Impact**: 
- Queries joining tables incorrectly
- Scripts assuming wrong column names
- Hours of debugging preventable issues

**Key Learning**: AI agents must be explicitly required to read documentation before coding. Add "Confirm understanding with Project Lead before proceeding" as a gate.

---

### LL-019: Automation First - State What TO DO, Not What NOT To Do

| Field | Value |
|-------|-------|
| Date | 2026-01-01 |
| Project | Etymython |
| Issue | AI agents repeatedly perform manual operations (password prompts, manual data entry, interactive confirmations) despite methodology prohibiting them |
| Root Cause | Methodology stated what NOT to do ("don't use getpass") leaving infinite wrong choices. Should state exactly what TO DO (one correct choice) |
| Fix Applied | Rewrote automation requirements as positive instructions with specific code examples |
| Template Section | PROJECT_KICKOFF_TEMPLATE.md Phase 1 Responsibility Matrix Clarification |

**Impact**: 
- Scripts hanging waiting for password input
- Manual API key entry requests blocking automation
- Interactive confirmations breaking CI/CD

**Key Learning**: 
- **Parent Principle**: Anything that CAN be automated SHOULD be automated
- Give one correct way, not infinite wrong ways to avoid

---

### LL-020: AI Lacks Metacognition - External Verification Required

| Field | Value |
|-------|-------|
| Date | 2026-01-01 |
| Project | Etymython |
| Issue | AI agent reported "ROUNDTRIP SUCCESS" when the test was actually failing. The test compared corrupted-input to corrupted-output, both having the same bug, so they matched |
| Root Cause | AI cannot evaluate its own output quality. It trusts its own tests, which may have the same blind spots as its code |
| Fix Applied | Established Golden Audit governance model - truth sources owned by Architect, read-only for VS Code |
| Template Section | VERIFICATION_GOVERNANCE.md |

**Impact**: 
- False success reports masking real failures
- Corrupted data (Unicode 206 mojibake) passing "tests"
- Project Lead time wasted investigating "passing" tests

**Key Learning**: 
- **The programmer cannot grade their own test**
- VS Code's tests = CLAIMS (not proof)
- Golden Audit = SINGLE SOURCE OF TRUTH (read-only for VS Code)

---

### LL-021: AI Memory Loss - Context Doesn't Persist

| Field | Value |
|-------|-------|
| Date | 2026-01-01 |
| Project | Etymython |
| Issue | VS Code repeatedly forgets established patterns, configurations, and decisions from earlier in the same project or conversation |
| Root Cause | AI context windows are limited. Long conversations lose early context. Separate chat sessions have no shared memory |
| Fix Applied | Added context reinforcement strategies: explicit citations, instruction templates, periodic reminders |
| Template Section | PROJECT_KICKOFF_TEMPLATE.md, VIOLATION_RESPONSE.md |

**Impact**: 
- Forgetting passkey authentication after being told multiple times
- Reverting to default patterns instead of project-specific ones
- Disproven theories persisting across sessions

**Key Learning**: 
- Use explicit citations: "Per PROJECT_METHODOLOGY.md section 4.2..."
- Every ~10 exchanges, restate critical constraints
- When violated, require lookup and confirmation before proceeding

---

### LL-022: Unit Before Bulk - Testing Sequence

| Field | Value |
|-------|-------|
| Date | 2026-01-01 |
| Project | Etymython |
| Issue | VS Code jumped from "code written" directly to "bulk execution" of 56 records, causing widespread data corruption |
| Root Cause | No enforced testing sequence requiring single-record verification before batch operations |
| Fix Applied | Mandatory testing sequence: Smoke → Unit (1 record) → Small Batch (3-5) → Bulk. Added bulk operation checklist |
| Template Section | SPRINT_1_CHECKLIST.md, TEST_PLAN_TEMPLATE.md |

**Impact**: 
- Bulk operations applying bugs to all records simultaneously
- No rollback possible when entire dataset corrupted
- Multiple recovery attempts needed

**Key Learning**: 
```
NEVER skip from "code written" to "bulk execution"
Sequence: Smoke test → Unit test (1 record) → Small batch (3-5) → Bulk
```

---

### LL-023: Unicode/Encoding Requires Special Attention

| Field | Value |
|-------|-------|
| Date | 2026-01-01 |
| Project | Etymython |
| Issue | Greek Unicode text corrupted multiple times due to encoding mismatches between Python, pyodbc, and SQL Server |
| Root Cause | String comparison doesn't catch encoding bugs. SQL Server NVARCHAR uses UTF-16, Python uses UTF-8, pyodbc configuration is non-obvious |
| Fix Applied | Added Unicode handling requirements: verify with UNICODE() not string comparison, UTF-16LE encoding for pyodbc |
| Template Section | UNICODE_HANDLING.md |

**Impact**: 
- Original `Ζεύς` (Unicode 918) became `????` then `Î–ÎµÏÏ‚` (mojibake)
- Each "fix" made data worse
- 56 records corrupted before root cause found

**Key Learning**: 
- Test with UNICODE values: `SELECT UNICODE(LEFT(column, 1))` 
- Greek should be 913-1023 (basic) or 7936-8191 (extended)
- If you see 63, 206, 195, 225 = encoding bug
- pyodbc setup: `conn.setencoding(encoding='utf-16-le')`

---

### LL-024: Error Recovery - Don't Make It Worse

| Field | Value |
|-------|-------|
| Date | 2026-01-01 |
| Project | Etymython |
| Issue | Each "fix" attempt made the data worse, not better. Pressure to show progress led to untested fixes that compounded problems |
| Root Cause | No error recovery protocol. Fixes applied to all affected records without isolated testing |
| Fix Applied | Error Recovery Protocol: STOP → PRESERVE → ISOLATE → VERIFY → ROLLBACK PLAN |
| Template Section | PROJECT_KICKOFF_TEMPLATE.md Appendix D |

**Impact**: 
- Original: Some records had `????` (data lost but recoverable)
- After fix attempt: All 56 records had mojibake (worse than before)
- Multiple attempts before finally working

**Key Learning**: 
```
BACKUP BEFORE FIX: SELECT * INTO table_backup_YYYYMMDD FROM table;
NEVER apply untested fixes to all affected records simultaneously.
```

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total Lessons | 24 |
| Template Sections Updated | 15 |
| New Sections Added | 12 |
| Projects Contributing | ArtForge, HarmonyLab, Etymython |

---

### LL-025: External API Temporary Resources - Persist Immediately

| Field | Value |
|-------|-------|
| Date | 2026-01-02 |
| Project | Etymython |
| Issue | 3 figures had broken images discovered days later by users. DALL-E returns Azure Blob URLs that expire in 2 hours, but these were stored directly in database |
| Root Cause | External API temporary URLs stored as-is instead of downloading and persisting to controlled storage |
| Fix Applied | Added External API Resource Handling requirements - identify temp resources, persist immediately to GCS, validate in audit |
| Template Section | PROJECT_KICKOFF_TEMPLATE.md External Integrations, EXTERNAL_API_HANDLING.md |

**Impact**: 
- Silent failures discovered by end users, not tests
- 67 figures worked (permanent GCS URLs), 3 failed (temp DALL-E URLs)
- Expiration was invisible until images broke

**Key Learning**: 
```
NEVER store temporary URLs in persistent database fields.
1. Identify temporary resources (DALL-E 2hr, pre-signed URLs, tokens)
2. Download/persist immediately to storage you control (GCS)
3. Store YOUR permanent URL, not the API's temporary URL
4. Add audit checks for known temp URL patterns
```

---

### LL-026: No Diffs - Always Provide Complete Files

| Field | Value |
|-------|-------|
| Date | 2026-01-02 |
| Project | Etymython |
| Issue | AI provided stored procedure update as diff ("Replace the DC-005 section with this..."). Project Lead refused: "I don't do diffs. It breaks code and takes mental cycles to figure out." |
| Root Cause | AI defaulting to minimal output instead of complete, immediately usable files |
| Fix Applied | Added File Delivery Standard - always provide complete files, never diffs or snippets |
| Template Section | PROJECT_KICKOFF_TEMPLATE.md Code Delivery Standards |

**Impact**: 
- Error-prone manual merging
- Time-consuming context reconstruction
- Ambiguous line numbers that shift
- Missing context makes review difficult

**Key Learning**: 
```
✅ ALWAYS: Provide complete file, ready to copy/paste or save
❌ NEVER: "Replace this section...", "Find line X and change...", unified diff format

EXCEPTION: If file >500 lines AND small change, ASK preference first.
RATIONALE: Extra seconds to generate complete file saves significant debugging time.
```

---

### LL-027: Test the Code Path, Not Just the Data

| Field | Value |
|-------|-------|
| Date | 2026-01-02 |
| Project | Etymython |
| Issue | Fix proposal for 3 broken images didn't address root cause - just regenerate images and update DB. Project Lead: "That particular application will continue to repeat the broken behavior." |
| Root Cause | Temptation to fix visible symptoms (bad data) without proving the underlying code is fixed |
| Fix Applied | Added Bug Fix Verification protocol - must test the actual code path before fixing data it created |
| Template Section | PROJECT_KICKOFF_TEMPLATE.md Appendix D (expanded), BUG_FIX_PROTOCOL.md |

**Impact**: 
- Bug recurs next time code runs if only data fixed
- False confidence that problem is solved
- Wasted effort on repeated fixes

**Key Learning**: 
```
When fixing a bug that caused bad data:
1. FIND the root cause code
2. FIX the code
3. TEST by running that exact code path (create NEW test data)
4. VERIFY test data is correct (via Golden Audit)
5. ONLY THEN fix existing bad data

ANTI-PATTERN: Fix data directly without fixing/testing code = bug will recur
```

---

### LL-028: Git Push at Logical Checkpoints, Not On Demand

| Field | Value |
|-------|-------|
| Date | 2026-01-02 |
| Project | Etymython |
| Issue | After completing Sprint 4, discovered last push was 1 week ago. 8 modified files with critical fixes (UTF-16LE encoding, DALL-E→GCS) sitting unpushed |
| Root Cause | AI agents don't proactively push; wait until explicitly asked |
| Fix Applied | Added Git Push Best Practices - push at logical checkpoints, minimum daily, proactively suggest |
| Template Section | PROJECT_KICKOFF_TEMPLATE.md Version Control |

**Impact**: 
- Week of work at risk if local environment lost
- CI/CD pipeline didn't run on critical fixes
- No backup of production fixes
- Team couldn't see or build on changes

**Key Learning**: 
```
WHEN TO PUSH:
- After each significant fix
- After each feature completion
- At end of each working session
- Before handoffs
- MINIMUM: Daily

AI RESPONSIBILITY: Proactively suggest "Ready to push?" after completing work.
ANTI-PATTERN: Waiting until asked, accumulating week of local-only changes.
```

---

### LL-029: Session Start Authentication - Human Responsibility

| Field | Value |
|-------|-------|
| Date | 2026-01-02 |
| Project | Etymython |
| Issue | GCloud commands prompted for password, blocking AI agents. Tokens expire after ~1 hour of inactivity, requiring browser/passkey re-authentication that AI cannot perform |
| Root Cause | No documented session-start ritual; AI tried to proceed with expired credentials instead of requesting human re-auth |
| Fix Applied | Added Session Start Authentication Checklist; clarified human-only auth responsibility; AI must stop and request re-auth if blocked |
| Template Section | PROJECT_KICKOFF_TEMPLATE.md Phase 0.1 (enhanced) |

**Impact**: 
- Scripts blocked waiting for password input
- AI couldn't proceed with GCP operations
- Work stalled until human manually authenticated

**Key Learning**: 
```
GCP AUTH IS HUMAN-ONLY:
- Browser/Passkey authentication cannot be done by AI
- Create session-start script (TextExpander, shell alias)
- Run BEFORE any GCP work session

IF AI ENCOUNTERS PASSWORD PROMPT:
1. STOP immediately
2. Tell Project Lead: "GCP auth has expired. Please run session start script."
3. Wait for confirmation before proceeding
4. Do NOT attempt to enter credentials or work around it
```

---

### LL-030: Developer Tests Before Handoff - Universal Principle

| Field | Value |
|-------|-------|
| Date | 2026-01-03 |
| Project | Etymython |
| Issue | VS Code handed off broken code 3 times without testing it. Project Lead found console errors (service worker cache failures) that VS Code should have caught |
| Root Cause | AI assumed "code compiles" = "code works"; no self-verification before handoff |
| Fix Applied | Added universal "Developer Tests Before Handoff" section - applies to ALL work (frontend, API, scripts, bug fixes) throughout entire project lifecycle |
| Template Section | PROJECT_KICKOFF_TEMPLATE.md Phase 1 (universal principles) |

**Impact**: 
- Project Lead time wasted debugging console errors
- Multiple round-trips for same feature
- Broken service worker caching files that don't exist

**Key Learning**: 
```
UNIVERSAL PRINCIPLE - APPLIES TO ALL HANDOFFS:

Do not hand off ANY work for review until you have tested it yourself.

| Work Type     | Self-Verification Required                    |
|---------------|-----------------------------------------------|
| Frontend/UI   | DevTools Console + Network, feature renders   |
| API endpoints | Curl/test request, no 500 errors              |
| Database      | Query works, no constraint violations         |
| Scripts       | Runs without errors, expected output          |
| Bug fixes     | Bug no longer reproduces                      |

Project Lead's time is for reviewing WORKING code, not debugging errors 
you should have caught.
```

---

### LL-031: VS Code AI Cannot Manually Test - Playwright Required

| Field | Value |
|-------|-------|
| Date | 2026-01-03 |
| Project | Etymython |
| Issue | When challenged to "open a browser and test it yourself," VS Code clarified it literally cannot open Chrome, use DevTools, see console errors, click elements, or test mobile viewports. VS Code was coding blind. |
| Root Cause | VS Code AI has no visual interface - it cannot manually test UI. Only Project Lead could see results, making PL the only tester by default. |
| Fix Applied | Added Playwright requirement for UI projects - gives VS Code "eyes" to programmatically test browsers |
| Template Section | PROJECT_KICKOFF_TEMPLATE.md Phase 1, PLAYWRIGHT_TESTING.md |

**Impact**: 
- VS Code handed off untested code repeatedly
- Project Lead became sole tester by default
- No way for VS Code to verify UI actually worked

**Key Learning**: 
```
VS Code AI CANNOT:
- Open Chrome or any browser
- Use DevTools
- See console errors visually
- Click interactive elements
- Test mobile viewports
- Take screenshots manually

SOLUTION: Playwright gives VS Code "eyes"
- Launch headless browser programmatically
- Capture console errors
- Click elements, fill forms
- Test mobile/desktop viewports
- Verify elements are visible

For ANY project with UI: Install Playwright early, create smoke tests,
run before every handoff. "Playwright tests passing" replaces "I tested it manually."
```

---

### LL-032: Shell Environment - PowerShell Not Bash

| Field | Value |
|-------|-------|
| Date | 2026-01-03 |
| Project | Etymython |
| Issue | AI-generated scripts used bash syntax (`&&`, `$VAR`, `/dev/null`) that failed in our Windows/PowerShell environment |
| Root Cause | Shell environment not explicitly documented; AI defaulted to bash assumptions |
| Fix Applied | Added explicit Shell Environment section specifying PowerShell (pwsh) as standard |
| Template Section | PROJECT_KICKOFF_TEMPLATE.md Phase 0 |

**Impact**: 
- Scripts failed silently or with confusing errors
- Time wasted debugging syntax issues
- Inconsistent script formats across project

**Key Learning**: 
```
SHELL ENVIRONMENT: PowerShell (pwsh)

All scripts and command-line examples must use PowerShell syntax:
- Shell: powershell or pwsh, NOT bash or sh
- Extension: .ps1, NOT .sh
- Variables: $env:VAR, NOT $VAR
- Chaining: ; or separate lines, NOT &&
- Null redirect: $null, NOT /dev/null
- Conditionals: if ($x) {}, NOT if [ $x ]
```

---

### LL-033: AI Agents Must Use AI Tools for Domain Research

| Field | Value |
|-------|-------|
| Date | 2026-01-06 |
| Project | Etymython |
| Issue | AI agent delegated domain research questions to Project Lead instead of using available AI tools (OpenAI API, web search, documentation) to find answers itself |
| Root Cause | AI defaulted to asking rather than researching; didn't recognize research as its responsibility |
| Fix Applied | Added clear guidance: AI researches using available tools, proposes answers with evidence. PL time is for decisions, not research. |
| Template Section | PROJECT_KICKOFF_TEMPLATE.md Responsibility Matrix |

**Impact**: 
- Project Lead time wasted answering questions AI could research
- Slower iteration cycles
- AI not using its full capabilities

**Key Learning**: 
```
WRONG:
AI: "I need to know the correct value for X. What should it be?"
AI: "Should I use approach A or B? Here are the tradeoffs..."

RIGHT:
AI: [Calls OpenAI/searches documentation to find answer]
AI: "I researched X and found the correct value is Y because [evidence].
     I'll proceed with this unless you disagree."

WHEN TO RESEARCH vs. WHEN TO ASK:
| Situation                  | Action                        |
|----------------------------|-------------------------------|
| Factual domain question    | AI researches                 |
| Industry best practice     | AI researches                 |
| Implementation approach    | AI researches, proposes       |
| Business/policy decision   | Ask Project Lead              |
| Ambiguous requirements     | Ask Project Lead              |
| Irreversible action        | Confirm with Project Lead     |

AI agents have research capabilities. Use them.
```

---

### LL-034: Complete the Audit Before Going Deep

| Field | Value |
|-------|-------|
| Date | 2026-01-06 |
| Project | Etymython |
| Issue | When auditing functionality, AI found one issue and spent hours fixing it before discovering other features were also broken. Led to thrashing and surprise discoveries. |
| Root Cause | No structured audit approach; rabbit-holing on first issue found |
| Fix Applied | Added Surface Scan First protocol - test everything at surface level, report complete findings, get prioritization, THEN fix systematically |
| Template Section | PROJECT_KICKOFF_TEMPLATE.md Testing Requirements |

**Impact**: 
- Wasted effort fixing low-priority items
- Surprise discoveries late in process
- Project Lead couldn't make informed priority decisions

**Key Learning**: 
```
WRONG APPROACH:
Test A → Find bug → Spend 2 hours fixing → Test A again → Works!
Finally test B → Also broken → Repeat thrashing...

RIGHT APPROACH:
Test A → Note: "BROKEN - [symptom]"
Test B → Note: "WORKS"
Test C → Note: "BROKEN - [symptom]"
REPORT complete findings → Get prioritization → Fix in order

AUDIT REPORT FORMAT:
Working:
- Feature X: ✅ Works as expected

Broken - Critical (crashes/blocks):
- Feature A: ❌ Returns 500 error

Broken - Major (doesn't work):
- Feature C: ❌ Does nothing when clicked

Broken - Minor (works with issues):
- Feature E: ⚠️ Works but [issue]

Not Tested:
- Feature F: Blocked by Feature B

Awaiting prioritization.
```

---

### LL-035: Audit Coverage Must Match Data Model

| Field | Value |
|-------|-------|
| Date | 2026-01-06 |
| Project | Etymython |
| Issue | Golden Audit checked some entity categories (Olympians, Titans) but missed others (Primordials, Heroes, Mortals), creating blind spots where invalid data went undetected |
| Root Cause | Audits built incrementally without systematic coverage check |
| Fix Applied | Added Audit Coverage Checklist - verify all categorical field values are covered, prefer generic checks over specific |
| Template Section | VERIFICATION_GOVERNANCE.md |

**Impact**: 
- Invalid data in uncovered categories went undetected
- False confidence in "100% passing" audits
- New categories added without audit coverage

**Key Learning**: 
```
THE RULE:
If a data model has a categorical field with N valid values, the audit needs:
- N specific checks (one per value), OR
- 1 generic check covering all values

FIND UNCOVERED VALUES:
SELECT DISTINCT category_field FROM table
WHERE category_field NOT IN (/* categories your audit covers */);

PREFER GENERIC OVER SPECIFIC:
-- FRAGILE: Must update when new types added
CHECK_TYPE_A: All Type A have X
CHECK_TYPE_B: All Type B have X
-- What about Type C, D, E?

-- ROBUST: Automatically covers all types
CHECK_ALL_TYPES: All records have X (grouped by type)
```

---

### LL-036: Verify GCP Project Before Every Deploy

| Field | Value |
|-------|-------|
| Date | 2026-01-06 |
| Project | Etymython |
| Issue | Deployment went to wrong GCP project because `gcloud config` was set incorrectly |
| Root Cause | No verification step before deploy; assumed project was correct |
| Fix Applied | Added mandatory project verification before any `gcloud run deploy` |
| Template Section | DEPLOYMENT_CHECKLIST.md, PROJECT_KICKOFF_TEMPLATE.md |

**Impact**: 
- Broken deployment
- Confusion about where code actually deployed
- Wasted time debugging

**Key Learning**: 
```
BEFORE ANY `gcloud run deploy`:

gcloud config get-value project

If it doesn't match your target project, STOP and fix it:

gcloud config set project {{GCP_PROJECT_ID}}

Wrong project = broken deployment.
```

---

### LL-037: Version Numbers - Verify Deployed == Tested

| Field | Value |
|-------|-------|
| Date | 2026-01-09 |
| Project | Etymython |
| Issue | Confusion about whether Project Lead was testing the latest deployment. No way to verify "what I'm looking at" matches "what VS Code deployed." |
| Root Cause | No visible version number in the application; no version communication in handoffs |
| Fix Applied | Added version number requirement - display in app, increment with each deploy, communicate in handoff |
| Template Section | PROJECT_KICKOFF_TEMPLATE.md Deployment Standards |

**Impact**: 
- Wasted time debugging "fixed" issues that were actually stale cache
- Confusion about which version was live
- No way to confirm tester and developer were on same page

**Key Learning**: 
```
EVERY APPLICATION MUST:
1. Display a version number visible in the UI (footer, about page, or console)
2. Increment version with EVERY deployment
3. Communicate version in handoff: "Deployed v1.2.3 - please verify you see this version"

HANDOFF FORMAT:
"Deployed v1.2.3 to production. 
 Please verify: [location where version is displayed]
 Changes in this version: [list]"

IF VERSIONS DON'T MATCH:
- Hard refresh (Ctrl+Shift+R)
- Clear cache
- Check service worker (Application → Service Workers → Unregister)
- If still wrong, deployment may have failed
```

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total Lessons | 37 |
| Template Sections Updated | 27 |
| New Sections Added | 23 |
| Projects Contributing | ArtForge, HarmonyLab, Etymython |

## How to Add New Lessons

1. Create entry with the next LL number (e.g., LL-013)
2. Fill in all fields in the table format
3. Add Impact and Key Learning sections if significant
4. Update the Summary Statistics
5. Update the relevant template section
6. Increment version in CHANGELOG.md
