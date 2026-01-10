-- ============================================
-- META PROJECT MANAGER - Methodology Rules Seed Data
-- Based on project-methodology v3.12.1 LESSONS_LEARNED.md
-- ============================================

-- Clear existing rules (if re-running)
-- DELETE FROM MethodologyViolations;
-- DELETE FROM MethodologyRules;

-- ============================================
-- METHODOLOGY RULES FROM LESSONS LEARNED
-- ============================================

-- Authentication & GCP
INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-002', 'Authentication Order', 'AUTHENTICATION',
'Authentication must happen BEFORE setting GCP project. Order: gcloud auth login → gcloud auth application-default login → gcloud config set project',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-002: Authentication Order.

VIOLATION: You attempted GCP commands before completing browser authentication.

BEFORE WE CONTINUE:
1. LOOKUP: Review LESSONS_LEARNED.md: LL-002
2. REPORT BACK: What is the correct authentication order?
3. CONFIRM: Run the auth commands in correct order.

DO NOT proceed until authentication is complete.',
'CRITICAL');

INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-003', 'Verify GCP Project', 'DEPLOYMENT',
'Always verify the GCP project before running any commands. Run: gcloud config get-value project',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-003/LL-036: Verify GCP Project.

VIOLATION: You ran GCP commands without verifying the active project.

BEFORE WE CONTINUE:
1. Run: gcloud config get-value project
2. Confirm this matches the intended project
3. If wrong, run: gcloud config set project [correct-project]

DO NOT proceed until project is verified.',
'HIGH');

-- Development Workflow
INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-006', 'No Localhost Servers', 'WORKFLOW',
'Never run localhost development servers. Workflow is always: Write → Push → Deploy → Test on Cloud Run URL',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-006: No Localhost Servers.

VIOLATION: You started a local development server (uvicorn, flask, etc.)

CLOUD-FIRST WORKFLOW:
1. Write code
2. git commit & push
3. gcloud run deploy
4. Test on Cloud Run URL

DO NOT use localhost. Deploy and test in the cloud.',
'HIGH');

INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-007', 'Git Push at Checkpoints', 'WORKFLOW',
'Push to GitHub after fixes, features, and sessions. Minimum daily push.',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-007/LL-028: Git Push at Checkpoints.

VIOLATION: Work completed but not pushed to GitHub.

BEFORE WE CONTINUE:
1. git add .
2. git commit -m "[meaningful message]"
3. git push origin main

Never leave code only on local machine.',
'MEDIUM');

-- Automation & Credentials
INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-019', 'Automation First - No Password Prompts', 'AUTOMATION',
'Never use getpass() or manual credential entry. All secrets must come from Google Secret Manager.',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-019: Automation First.

VIOLATION: You used getpass() or prompted for manual password entry.

CORRECT APPROACH:
```python
from google.cloud import secretmanager

def get_secret(secret_id, project_id):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")
```

Remove all password prompts. Use Secret Manager.',
'CRITICAL');

-- Documentation & Research
INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-018', 'RTFM - Read Documentation First', 'DOCUMENTATION',
'AI must read documentation before writing code. State: "I have reviewed [docs] and understand [constraints]"',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-018: RTFM.

VIOLATION: You wrote code without reviewing relevant documentation.

BEFORE WE CONTINUE:
1. LOOKUP: Read the relevant documentation files
2. REPORT BACK: State what you learned and key constraints
3. CONFIRM: How will your code comply with the documentation?

"I have reviewed [specific documents] and understand that [key constraints]. 
My approach will be [description] which complies with [methodology sections]."

DO NOT proceed until you confirm documentation review.',
'HIGH');

INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-033', 'AI Researches First', 'WORKFLOW',
'AI must use available tools (OpenAI, web search, docs) to research questions. PL time is for decisions, not research.',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-033: AI Researches First.

VIOLATION: You delegated a research question to the Project Lead.

WRONG: "What should the value of X be?"
RIGHT: "I researched X and found it should be Y because [evidence]. Proceeding unless you disagree."

Use your AI tools to research:
- Factual domain questions
- Industry best practices
- Implementation approaches

Only ask PL for:
- Business/policy decisions
- Ambiguous requirements
- Irreversible actions',
'MEDIUM');

-- Testing
INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-022', 'Unit Before Bulk', 'TESTING',
'Never skip from "code written" to "bulk execution". Test single record first, then small batch, then bulk.',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-022: Unit Before Bulk.

VIOLATION: You attempted bulk operation without single-record testing.

REQUIRED SEQUENCE:
1. Test with 1 record
2. Verify output manually
3. Test with 5 records
4. Verify all outputs
5. ONLY THEN run bulk operation

Also: Create backup table BEFORE any UPDATE/DELETE bulk operation.

Show me your single-record test results.',
'CRITICAL');

INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-030', 'Developer Tests Before Handoff', 'TESTING',
'Test your own work before ANY handoff. PL reviews working code, not bugs.',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-030: Developer Tests Before Handoff.

VIOLATION: You handed off untested code.

BEFORE HANDOFF, YOU MUST:
1. Run the code yourself
2. Verify it works (API returns expected data, UI renders correctly)
3. Check for console errors
4. Test edge cases

Unacceptable: "I think it works", "Please test", "Ready for testing"
Acceptable: "All 7 tests pass", "API returns 200 with expected data"

Run your tests and show me the output.',
'CRITICAL');

INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-031', 'Playwright Required for UI', 'TESTING',
'VS Code cannot see browsers. Use Playwright for all UI testing.',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-031: Playwright Required for UI.

VIOLATION: You claimed UI work is complete without Playwright tests.

VS Code cannot:
- Open a browser
- See UI render
- Click buttons
- Check DevTools

REQUIRED:
1. pip install playwright pytest-playwright --break-system-packages
2. playwright install chromium
3. Write Playwright tests for your feature
4. pytest tests/test_ui_*.py -v
5. ALL tests must pass before handoff

Show me passing Playwright test output.',
'CRITICAL');

INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-034', 'Surface Scan First', 'TESTING',
'When auditing, test everything at surface level first. Report complete findings. Get prioritization. THEN fix.',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-034: Surface Scan First.

VIOLATION: You rabbit-holed on fixing the first issue before completing the audit.

WRONG: Test A → Find bug → Spend 2 hours fixing → Finally test B → Also broken
RIGHT: Test A → Note "BROKEN" → Test B → Note "WORKS" → Test C → REPORT → Get priorities → Fix

AUDIT REPORT FORMAT:
Working:
- Feature X: ✅ Works

Broken - Critical:
- Feature A: ❌ Returns 500

Broken - Major:
- Feature C: ❌ Does nothing

Awaiting prioritization.

Complete the audit before fixing anything.',
'HIGH');

-- Code Quality
INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-020', 'External Verification - No Modifying Truth Sources', 'DATA-INTEGRITY',
'The programmer cannot grade their own test. VS Code has read-only access to Golden Audit and truth sources.',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-020: External Verification.

VIOLATION: You modified a truth source (Golden Audit, stored procedure, reference data).

VS Code has READ-ONLY access to:
- Golden Audit procedures
- Reference data tables
- Stored procedures that define truth

If the audit fails, fix the DATA, not the AUDIT.

Revert your changes to the truth source.',
'CRITICAL');

INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-026', 'No Diffs - Complete Files Only', 'CODE-QUALITY',
'Always provide complete files, never diffs or snippets.',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-026: No Diffs.

VIOLATION: You provided a diff or code snippet instead of the complete file.

Diffs cause:
- Merge conflicts
- Missing context
- Manual integration errors

Provide the COMPLETE FILE content.
Do not use "// ... rest of file unchanged"',
'MEDIUM');

INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-027', 'Test Code Path Before Fixing Data', 'DEBUGGING',
'When fixing bugs, test the broken code before fixing the data. Ensure the code path is actually exercised.',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-027: Test Code Path.

VIOLATION: You fixed data without verifying the code path was being exercised.

BEFORE fixing data:
1. Add logging to confirm the code path executes
2. Verify the function is actually called
3. Confirm parameters are passed correctly
4. THEN fix the data if needed

The bug might be in the code calling the function, not the data.',
'HIGH');

-- Environment & Syntax
INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-032', 'PowerShell Not Bash', 'ENVIRONMENT',
'All scripts use PowerShell syntax. Extension: .ps1, Variables: $env:VAR, Chaining: ; not &&',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-032: PowerShell Not Bash.

VIOLATION: You used bash syntax instead of PowerShell.

POWERSHELL REQUIREMENTS:
- Shell: powershell or pwsh, NOT bash or sh
- Extension: .ps1, NOT .sh
- Variables: $env:VAR, NOT $VAR
- Chaining: ; or separate lines, NOT &&
- Null redirect: $null, NOT /dev/null
- Conditionals: if ($x) {}, NOT if [ $x ]

Rewrite using PowerShell syntax.',
'MEDIUM');

-- Version & Deployment
INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-037', 'Version Numbers Required', 'DEPLOYMENT',
'Every application must display a visible version number. Increment with every deploy. Communicate in handoff.',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-037: Version Numbers.

VIOLATION: No visible version number in the application.

REQUIREMENTS:
1. Display version in UI (footer, about page, or console)
2. Increment version with EVERY deployment
3. Handoff format: "Deployed v1.2.3 - please verify at [location]"

Add a version constant and display it in the UI.',
'HIGH');

-- Persistence & Data Handling
INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-025', 'Persist Immediately', 'DATA-INTEGRITY',
'Never store temporary API URLs (DALL-E, etc). Download and persist to your storage immediately.',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-025: Persist Immediately.

VIOLATION: You stored a temporary API URL instead of persisting the content.

Temporary URLs (like DALL-E image URLs) expire!

CORRECT APPROACH:
1. Receive URL from API
2. IMMEDIATELY download content
3. Upload to GCS or permanent storage
4. Store permanent URL in database

Never store: temporary URLs, signed URLs with expiration, blob: URLs',
'HIGH');

INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-023', 'Unicode Handling', 'DATA-INTEGRITY',
'Use database functions (UNICODE(), NCHAR()) for Unicode verification, not string comparison.',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-023: Unicode Handling.

VIOLATION: You used string comparison for Unicode verification.

CORRECT APPROACH:
-- Compare by codepoint, not string
SELECT 
    greek_text,
    UNICODE(greek_text) as codepoint
FROM table
WHERE UNICODE(greek_text) BETWEEN 0x0370 AND 0x03FF

Do not use: text = N''expected'' for Unicode verification.',
'MEDIUM');

-- Backup & Recovery
INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-024', 'Backup Before Bulk Operations', 'DATA-INTEGRITY',
'Create backup table before any bulk UPDATE or DELETE operation.',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated LL-024: Backup Before Bulk Operations.

VIOLATION: You attempted bulk UPDATE/DELETE without creating a backup.

REQUIRED BEFORE BULK OPERATIONS:
```sql
-- Create backup
SELECT * INTO table_backup_YYYYMMDD FROM table;

-- Verify backup
SELECT COUNT(*) FROM table_backup_YYYYMMDD;

-- THEN proceed with bulk operation
```

Create a backup table first.',
'CRITICAL');

-- Sprint Management
INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('SPRINT-SEQUENCE', 'Follow Sprint Task Sequence', 'WORKFLOW',
'When completing a sprint task, immediately proceed to the next item. Do not wait for user prompt.',
'You have completed a sprint task. 

Per methodology: 
1. Mark the completed task in the sprint doc
2. Identify the next task
3. Begin work on it or report any blockers

What is the next task in the sprint?',
'HIGH');

-- Human-Visible Verification
INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('TEST-HUMAN-VISIBLE', 'Verify Human-Visible Functionality', 'TESTING', 
'Tests must verify actual human-visible functionality, not just technical presence. A passing test should mean a human user would see the expected behavior.',
'STOP. You have violated the TEST-HUMAN-VISIBLE rule. 

Before proceeding, you must: 
1. Identify what a human user would actually see or experience
2. Write a test that verifies that specific user experience
3. Run the test and confirm it passes

Do not mark this task complete until you can describe what a human would observe.',
'CRITICAL');

-- Context & Documentation
INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity) VALUES
('LL-021', 'Context Loss Prevention', 'DOCUMENTATION',
'When AI forgets established patterns, cite methodology and require lookup.',
'METHODOLOGY VIOLATION DETECTED

VS Code, you have violated a previously established pattern.

We have already established the correct approach for this.

BEFORE WE CONTINUE:
1. Review the project methodology and previous decisions
2. Confirm what pattern we established
3. Explain how you will apply it now

Do not reinvent patterns we have already solved.',
'MEDIUM');

GO

-- ============================================
-- VERIFY INSERTION
-- ============================================
SELECT 
    RuleCode,
    RuleName,
    Severity,
    Category
FROM MethodologyRules
ORDER BY 
    CASE Severity 
        WHEN 'CRITICAL' THEN 1 
        WHEN 'HIGH' THEN 2 
        WHEN 'MEDIUM' THEN 3 
        WHEN 'LOW' THEN 4 
    END,
    RuleCode;
GO
