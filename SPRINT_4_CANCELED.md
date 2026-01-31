---
## CANCELED: 2026-01-31

**Reason**: Command Center model makes Violation AI redundant.
- Claude Code now reads methodology docs and enforces compliance proactively
- Enhanced audit script provides compliance verification
- Violations are prevented at source, not detected after the fact

**Replacement**:
- Compliance enforcement → Claude Code + CLAUDE.md
- Audit dashboard → Audit-ProjectCompliance.ps1 + JSON export

See LL-050 in project-methodology for context.
---

# Sprint 4: Violation AI Compliance Assistant

**Sprint**: 4
**Started**: 2026-01-31
**Service**: metapm-v2
**Database**: MetaPM

---

## Features

### Feature 1: Violation Detection API (3 points)
**Endpoint**: POST /api/violations/analyze

Accepts text, returns detected methodology violations.

**Input**:
```json
{
  "text": "The feature is complete and ready for review.",
  "project_id": 1
}
```

**Output**:
```json
{
  "violations": [
    {
      "type": "VOCABULARY_VIOLATION",
      "lesson": "LL-049",
      "trigger": "complete",
      "message": "'Complete' requires proof: deployed revision + test output"
    }
  ],
  "violation_count": 1,
  "compliance_status": "NON-COMPLIANT"
}
```

**Detection Rules**:
| Pattern | Type | Lesson |
|---------|------|--------|
| "complete", "done", "finished", "ready", "✅" (no proof) | VOCABULARY_VIOLATION | LL-049 |
| "test locally", "local environment", "localhost" | NO_LOCAL_VIOLATION | LL-004 |
| "want me to deploy?", "let me know if", "steps for you" | OWNERSHIP_VIOLATION | LL-030 |
| "I think", "should work", "probably" (no test output) | UNVERIFIED_CLAIM | LL-030 |

### Feature 2: Violations Table (2 points)
```sql
CREATE TABLE Violations (
    ViolationID INT IDENTITY(1,1) PRIMARY KEY,
    ProjectID INT NULL FOREIGN KEY REFERENCES Projects(ProjectID),
    ViolationType NVARCHAR(50) NOT NULL,
    Lesson NVARCHAR(20),
    TriggerText NVARCHAR(500),
    FullText NVARCHAR(MAX),
    DetectedAt DATETIME DEFAULT GETDATE(),
    Resolved BIT DEFAULT 0
);
```

### Feature 3: Compliance Dashboard Endpoint (2 points)
**Endpoint**: GET /api/compliance/dashboard

Returns compliance status for all projects.

### Feature 4: Import Audit Results (1 point)
**Endpoint**: POST /api/compliance/import-audit

Imports JSON from Audit-ProjectCompliance.ps1

---

## Acceptance Criteria
- [ ] POST /api/violations/analyze detects 4+ violation types
- [ ] Violations table created
- [ ] GET /api/compliance/dashboard returns all projects
- [ ] Playwright tests pass
- [ ] Deployed to metapm-v2

## Role Assignments
| Task | Owner |
|------|-------|
| Implementation, testing, deployment | Claude Code |
| Architecture, rules design, review | Claude.ai |
| UAT, approval | PL (Corey) |
