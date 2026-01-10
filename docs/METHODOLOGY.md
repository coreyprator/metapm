# MetaPM Development Methodology

This project follows [coreyprator/project-methodology](https://github.com/coreyprator/project-methodology) v3.12.1

## Quick Reference: Top 10 Rules

| # | Rule | Summary |
|---|------|---------|
| 1 | **Cloud-First** | No localhost. Write → Push → Deploy → Test on Cloud Run |
| 2 | **Secrets in Secret Manager** | Never .env with secrets. Use Google Secret Manager |
| 3 | **Test Before Handoff** | Run automated tests. Show output. Never "I think it works" |
| 4 | **Playwright for UI** | VS Code can't see browsers. Use Playwright to verify UI |
| 5 | **RTFM First** | Read documentation before coding. State what you learned |
| 6 | **Unit Before Bulk** | Test 1 record → 5 records → bulk. Never skip steps |
| 7 | **Verify GCP Project** | Run `gcloud config get-value project` before deploy |
| 8 | **PowerShell Not Bash** | Use .ps1, $env:VAR, semicolons |
| 9 | **Version Numbers** | Display version in app. Increment every deploy |
| 10 | **Push at Checkpoints** | git push after fixes, features, sessions. Minimum daily |

## Methodology Rule Codes

These rules are stored in the MetaPM database and can be retrieved via:
- API: `GET /api/methodology/rules/{code}`
- This returns the rule description and a pre-written violation prompt

### Critical Rules (Stop work until resolved)

| Code | Name | Use When |
|------|------|----------|
| LL-019 | Automation First | AI used getpass() or manual password entry |
| LL-022 | Unit Before Bulk | AI attempted bulk operation without testing |
| LL-024 | Backup Before Bulk | AI ran UPDATE/DELETE without backup |
| LL-030 | Developer Tests Before Handoff | AI handed off untested code |
| LL-031 | Playwright Required | UI work without Playwright tests |
| TEST-HUMAN-VISIBLE | Verify Human-Visible | Test doesn't verify user experience |
| LL-020 | External Verification | AI modified truth sources |

### High Priority Rules

| Code | Name | Use When |
|------|------|----------|
| LL-002 | Authentication Order | GCP commands before auth |
| LL-003 | Verify GCP Project | Deploy without project verification |
| LL-006 | No Localhost Servers | AI started local dev server |
| LL-018 | RTFM | Coding without reading docs |
| LL-027 | Test Code Path | Fixed data without testing code |
| LL-034 | Surface Scan First | Rabbit-holed before full audit |
| LL-037 | Version Numbers | No visible version in app |
| SPRINT-SEQUENCE | Sprint Task Sequence | Didn't proceed to next task |

### Medium Priority Rules

| Code | Name | Use When |
|------|------|----------|
| LL-007 | Git Push at Checkpoints | Work not pushed to GitHub |
| LL-021 | Context Loss Prevention | AI forgot established patterns |
| LL-023 | Unicode Handling | String comparison for Unicode |
| LL-026 | No Diffs | Provided snippet instead of file |
| LL-032 | PowerShell Not Bash | Used bash syntax |
| LL-033 | AI Researches First | Delegated research to PL |

## How to Use Violation Prompts

When VS Code AI violates a rule:

```powershell
# 1. Fetch the rule from MetaPM API
Invoke-RestMethod -Uri "https://metapm.rentyourcio.com/api/methodology/rules/LL-030"

# 2. Copy the violation_prompt field
# 3. Paste into VS Code Copilot Chat
# 4. Wait for AI to acknowledge and correct

# 5. Optionally log the violation
$body = @{
    ruleCode = "LL-030"
    projectCode = "EM"  # or AF, HL, SF, META
    description = "Handed off untested feature X"
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
    -Uri "https://metapm.rentyourcio.com/api/methodology/violations" `
    -Body $body `
    -ContentType "application/json"
```

## Standard Violation Response Template

Copy this when needed:

```
METHODOLOGY VIOLATION DETECTED

VS Code, you have violated our established methodology:

VIOLATION: [describe what they did wrong]
EXAMPLE: "[specific action they took]"

BEFORE WE CONTINUE:

1. LOOKUP: Review the following documentation:
   - LESSONS_LEARNED.md: [LL-XXX]
   - [specific file if applicable]

2. REPORT BACK:
   - What is our policy on [topic]?
   - What is the CORRECT way to handle this?
   - How will you fix your current approach?

3. CONFIRM: State your understanding and proposed fix.

DO NOT proceed with any other work until you have completed steps 1-3.
```

## Handoff Report Template

VS Code MUST provide this with every handoff:

```markdown
## Handoff: [Feature/Fix Name]

**Version**: v[X.Y.Z] (verify at [location])
**Deployed to**: [CLOUD_RUN_URL]

### What was implemented
[Description]

### Automated Tests Run
```
pytest tests/test_*.py -v
# Output:
# test_xxx PASSED
# test_yyy PASSED
# 5 passed in 3.42s
```

### Self-Verification Completed
- [x] All smoke tests pass
- [x] No console errors (verified by Playwright)
- [x] No network failures (verified by Playwright)
- [x] Feature works on mobile viewport
- [x] No TODO/FIXME in code

### Ready for Review
Yes - all automated tests pass.
```

## What VS Code Cannot Say

| ❌ Unacceptable | Why |
|-----------------|-----|
| "I think it works" | No automated verification |
| "It should work" | No automated verification |
| "Please test and let me know" | Shifts testing burden to PL |
| "I can't test the UI" | Must use Playwright |
| "The code looks correct" | Code review ≠ testing |

## What VS Code Must Say

| ✅ Acceptable | Why |
|---------------|-----|
| "All 7 Playwright tests pass" | Automated verification |
| "pytest output shows 0 failures" | Automated verification |
| "Health endpoint returns 200" | Verified with actual request |

## Context Reminder

For long conversations, every ~10 exchanges paste:

```
CONTEXT REMINDER:

This project uses:
- Google Secret Manager for ALL credentials (no prompts)
- MS SQL Server via pyodbc with parameterized queries
- Cloud-first workflow: Write → Push → Deploy → Test
- PowerShell syntax for all scripts
- Mandatory testing before handoff

Continue with these constraints in mind.
```

---

**Methodology Version**: 3.12.1  
**MetaPM Version**: 0.1.0  
**Last Updated**: January 2026
