# Methodology Violation Response Protocol

**Purpose**: Standardized response when VS Code AI violates established methodology.

> **Key Principle**: AI agents are productive but not self-aware. They need structured escalation when they violate policies.

---

## When to Use This Protocol

Use this protocol when VS Code AI:
- Prompts for manual password/credential entry
- Skips documentation review before coding
- Jumps to bulk operations without unit testing
- Modifies truth sources (Golden Audit, stored procedures)
- Uses string comparison for Unicode verification
- Applies fixes without backup
- Forgets previously established patterns

---

## Standard Violation Response Template

Copy and use this template when a violation occurs:

```
METHODOLOGY VIOLATION DETECTED

VS Code, you have violated our established methodology:

VIOLATION: [describe what they did wrong]
EXAMPLE: "You prompted for manual password entry"

BEFORE WE CONTINUE:

1. LOOKUP: Review the following documentation:
   - PROJECT_METHODOLOGY.md section: [relevant section]
   - Project docs: [specific file if applicable]

2. REPORT BACK:
   - What is our policy on [topic]?
   - What is the CORRECT way to handle this?
   - How will you fix your current approach?

3. CONFIRM: State your understanding and proposed fix.

DO NOT proceed with any other work until you have completed steps 1-3.
```

---

## Quick Reference - Common Violations

| Violation | Methodology Section | Correct Approach |
|-----------|---------------------|------------------|
| Password prompt | LL-019: Automation First | Google Secret Manager |
| Skipped documentation | LL-018: RTFM | Review docs, confirm understanding first |
| Skipped unit test | LL-022: Unit Before Bulk | Single record test first |
| Modified truth source | LL-020: External Verification | Read-only access for VS Code |
| String comparison for Unicode | LL-023: Unicode Handling | Use UNICODE() function |
| Bulk without backup | LL-024: Error Recovery | Backup table first |
| Forgot established pattern | LL-021: Context Loss | Cite methodology, require lookup |
| Stored temp API URL | LL-025: Persist Immediately | Download to GCS immediately |
| Provided diff not complete file | LL-026: No Diffs | Always provide complete file |
| Fixed data without testing code | LL-027: Test Code Path | Test the broken code first |
| Didn't push completed work | LL-028: Push at Checkpoints | Push after fixes, features, sessions |
| Handed off untested code | LL-030: Developer Tests Before Handoff | Test it yourself first (DevTools, API, script output) |
| No Playwright for UI project | LL-031: Playwright Required | Install Playwright, run tests before handoff |
| Used bash syntax | LL-032: PowerShell Not Bash | Use .ps1, $env:VAR, ;, $null |
| Delegated research to PL | LL-033: AI Researches First | Use AI tools to research, propose solution |
| Rabbit-holed before full audit | LL-034: Surface Scan First | Test everything first, report, then fix |
| Audit missed categories | LL-035: Audit Coverage | Cover all categorical values |
| Deployed to wrong project | LL-036: Verify GCP Project | Check `gcloud config get-value project` first |
| No version number in app | LL-037: Version Numbers | Add visible version, communicate in handoff |

---

## Violation Response Examples

### Example 1: Password Prompt Violation

```
METHODOLOGY VIOLATION DETECTED

VS Code, you have violated our established methodology:

VIOLATION: You used getpass() to prompt for manual password entry
EXAMPLE: `password = getpass.getpass("Enter database password:")`

BEFORE WE CONTINUE:

1. LOOKUP: Review the following documentation:
   - PROJECT_METHODOLOGY.md: Automation Requirements
   - LESSONS_LEARNED.md: LL-019

2. REPORT BACK:
   - What is our policy on credential handling?
   - What is the CORRECT way to retrieve database passwords?
   - How will you fix your current script?

3. CONFIRM: State your understanding and proposed fix.

DO NOT proceed with any other work until you have completed steps 1-3.
```

**Expected VS Code Response**:
```
I understand the violation. Per LL-019 Automation First:

POLICY: All credentials must be retrieved from Google Secret Manager.
CORRECT APPROACH:
```python
from google.cloud import secretmanager

def get_secret(secret_id):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

password = get_secret("etymython-db-password")
```

FIX: I will replace the getpass() call with get_secret() and remove any interactive prompts.
```

---

### Example 2: Skipped Documentation Violation

```
METHODOLOGY VIOLATION DETECTED

VS Code, you have violated our established methodology:

VIOLATION: You wrote database queries without reviewing the schema documentation
EXAMPLE: Your JOIN on figure_etymologies uses incorrect column relationships

BEFORE WE CONTINUE:

1. LOOKUP: Review the following documentation:
   - docs/DATABASE_SCHEMA.md
   - PROJECT_METHODOLOGY.md: Pre-Work Checklist

2. REPORT BACK:
   - What tables are involved in this query?
   - What are the correct JOIN relationships?
   - How will you fix your query?

3. CONFIRM: State your understanding with the correct schema relationships.

DO NOT proceed with any other work until you have completed steps 1-3.
```

---

### Example 3: Bulk Operation Without Testing

```
METHODOLOGY VIOLATION DETECTED

VS Code, you have violated our established methodology:

VIOLATION: You attempted to run UPDATE on 56 records without single-record testing
EXAMPLE: `UPDATE etymologies SET greek_root = @value WHERE ...`

BEFORE WE CONTINUE:

1. LOOKUP: Review the following documentation:
   - LESSONS_LEARNED.md: LL-022 Unit Before Bulk
   - TEST_PLAN_TEMPLATE.md: Mandatory Testing Sequence

2. REPORT BACK:
   - What is the required testing sequence before bulk operations?
   - Have you created a backup table?
   - Show me your single-record test and its results

3. CONFIRM: Demonstrate that unit test passes before bulk execution.

DO NOT proceed with bulk operation until steps 1-3 are complete.
```

---

## Pre-Work Checklist (Mandatory)

Before VS Code writes ANY code, require confirmation of:

```
BEFORE WRITING ANY CODE:

[ ] Read relevant SKILL.md files
[ ] Review database schema/data model documentation
[ ] Review API documentation if applicable
[ ] Confirm understanding with Project Lead before proceeding

VS Code must state:
"I have reviewed [specific documents] and understand that [key constraints].
My approach will be [description] which complies with [methodology sections]."
```

---

## Escalation Path

If VS Code repeatedly violates the same policy:

1. **First Violation**: Standard response template
2. **Second Violation**: Require full methodology section quote + explanation
3. **Third Violation**: Escalate to Claude Architect for intervention
4. **Pattern of Violations**: Add to project-specific "watch list" in kickoff doc

---

## Context Reinforcement

For long conversations, every ~10 exchanges restate critical constraints:

```
CONTEXT REMINDER:

This project uses:
- Google Secret Manager for ALL credentials (no prompts)
- UTF-16LE encoding for SQL Server NVARCHAR columns
- Golden Audit (usp_GoldenAudit) as single source of truth
- Mandatory testing sequence: Unit → Small Batch → Bulk

Continue with these constraints in mind.
```

---

## Asking Claude for Help

When you need methodology guidance:

```
@Claude: VS Code just [describe violation]. 

Please:
1. Identify which methodology section applies
2. Provide the relevant policy text
3. Generate an RTFM response requiring VS Code to look up and confirm understanding
```

---

**Template Version**: 3.9  
**Last Updated**: January 2026  
**Methodology**: [coreyprator/project-methodology](https://github.com/coreyprator/project-methodology)
