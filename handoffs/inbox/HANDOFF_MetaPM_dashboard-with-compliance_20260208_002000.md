# [MetaPM] 🔴 Phase 4 — Handoff Dashboard with Compliance Tracking

> **From**: Claude.ai (Architect)
> **To**: Claude Code (Command Center)
> **Project**: 🔴 MetaPM
> **Task**: handoff-dashboard-with-compliance
> **Timestamp**: 2026-02-08T00:20:00Z
> **Priority**: HIGH
> **Type**: Feature Spec (ENHANCED)

---

## Overview

This is an **ENHANCED** version of the Handoff Dashboard spec. In addition to visibility into all handoffs, the dashboard now includes **compliance tracking** — showing evidence that each handoff followed proper procedures (GCS, GDrive, Git).

**Why**: The git emergency revealed compliance gaps. The dashboard should help verify that all required steps are being followed.

---

## Enhanced Data Model

### Handoff Record (Enhanced)

```python
class Handoff:
    # Core fields (from original spec)
    id: str
    project: str  # ArtForge, HarmonyLab, etc.
    title: str    # Task name
    direction: str  # "to_cc" or "to_claude_ai"
    status: str   # pending, read, done, archived
    created_at: datetime
    content: str  # Markdown content
    
    # NEW: Compliance fields
    gcs_url: str  # gs://corey-handoff-bridge/project/outbox/file.md
    gcs_verified: bool  # File exists in GCS
    gdrive_logged: bool  # Entry in HANDOFF_LOG.md
    git_commit: str  # Commit hash (if applicable)
    git_verified: bool  # Commit exists in repo
    compliance_score: int  # 0-100%
```

---

## Enhanced UI

### Dashboard with Compliance Indicators

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ MetaPM                                              [User] [Settings]        │
├─────────────────────────────────────────────────────────────────────────────┤
│ ◀ Dashboard  │  Handoff Bridge                    Compliance: 87% ⚠️        │
├──────────────┴──────────────────────────────────────────────────────────────┤
│                                                                              │
│  Filters: [All Projects ▼] [All Status ▼] [Compliance ▼] [🔍 Search]        │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────────┐│
│  │ Project      │ Title           │ Status │ Date    │ GCS │ Log │ Git │ ✓ ││
│  ├──────────────┼─────────────────┼────────┼─────────┼─────┼─────┼─────┼───┤│
│  │ 🔵 HarmonyLab│ v1.4.5-progress │ ✅ Done│ 2/7 11pm│ ✓   │ ✓   │ ✓   │ ✓ ││
│  │ 🔵 HarmonyLab│ v1.4.4-oauth    │ ✅ Done│ 2/7 9pm │ ✓   │ ✓   │ ✓   │ ✓ ││
│  │ 🟠 ArtForge  │ v2.2.1-uat-fixes│ ✅ Done│ 2/7 9pm │ ✓   │ ✗   │ ✓   │ ⚠️ ││
│  │ 🟢 proj-meth │ git-commit-policy│ ✅ Done│ 2/7 11pm│ ✓   │ ✓   │ ✓   │ ✓ ││
│  │ 🔴 MetaPM    │ phase3-api-test │ ✅ Done│ 2/7 6pm │ ✓   │ ✗   │ ✓   │ ⚠️ ││
│  └──────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  Legend: GCS = Cloud Storage │ Log = GDrive HANDOFF_LOG │ Git = Committed   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Compliance Column Definitions

| Column | Icon | Meaning |
|--------|------|---------|
| GCS | ✓/✗ | Handoff file exists in GCS bucket |
| Log | ✓/✗ | Entry exists in project's HANDOFF_LOG.md |
| Git | ✓/✗ | Related commit exists (for completion handoffs) |
| ✓ | ✓/⚠️/✗ | Overall compliance (all green = ✓) |

### Compliance Filter Options

- **All** — Show all handoffs
- **Compliant** — Only fully compliant (✓ ✓ ✓)
- **Warnings** — Missing some compliance (⚠️)
- **Non-compliant** — Major gaps (✗)

---

## Compliance Verification Logic

### 1. GCS Verification

```python
async def verify_gcs(handoff: Handoff) -> bool:
    """Check if handoff file exists in GCS bucket."""
    bucket = "corey-handoff-bridge"
    path = f"{handoff.project}/outbox/{handoff.filename}"
    
    blob = storage_client.bucket(bucket).blob(path)
    return blob.exists()
```

### 2. GDrive Log Verification

```python
async def verify_gdrive_log(handoff: Handoff) -> bool:
    """Check if handoff is logged in project's HANDOFF_LOG.md."""
    log_path = f"G:\\My Drive\\Code\\Python\\{handoff.project}\\handoffs\\log\\HANDOFF_LOG.md"
    
    if not os.path.exists(log_path):
        return False
    
    with open(log_path, 'r') as f:
        content = f.read()
        
    # Check if handoff filename or timestamp is in log
    return handoff.filename in content or handoff.task in content
```

### 3. Git Verification

```python
async def verify_git_commit(handoff: Handoff) -> tuple[bool, str]:
    """Check if related git commit exists."""
    repo_path = f"G:\\My Drive\\Code\\Python\\{handoff.project}"
    
    # Look for commits around handoff time with related message
    result = subprocess.run(
        ['git', 'log', '--oneline', '--since', handoff.created_at.isoformat(), '-10'],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    # Check if any commit message relates to handoff task
    for line in result.stdout.split('\n'):
        if handoff.task.lower() in line.lower() or handoff.version in line:
            commit_hash = line.split()[0]
            return True, commit_hash
    
    return False, None
```

### 4. Compliance Score

```python
def calculate_compliance(handoff: Handoff) -> int:
    """Calculate compliance percentage."""
    checks = [
        handoff.gcs_verified,
        handoff.gdrive_logged,
        handoff.git_verified if handoff.direction == "to_claude_ai" else True  # Git only required for completions
    ]
    
    return int(sum(checks) / len(checks) * 100)
```

---

## New API Endpoints

### Dashboard Endpoint (Enhanced)

```python
GET /mcp/handoffs/dashboard
    ?project=HarmonyLab
    &status=done
    &compliance=warning  # NEW: all, compliant, warning, non_compliant
    &sort=created_at
    &order=desc
    &page=1
    &limit=10
```

### Compliance Summary

```python
GET /mcp/handoffs/compliance-summary

Response:
{
    "overall_score": 87,
    "total_handoffs": 24,
    "compliant": 20,
    "warnings": 3,
    "non_compliant": 1,
    "by_project": {
        "ArtForge": { "score": 80, "total": 5, "compliant": 4 },
        "HarmonyLab": { "score": 100, "total": 6, "compliant": 6 },
        ...
    }
}
```

### Verify Single Handoff

```python
POST /mcp/handoffs/{id}/verify

Response:
{
    "gcs_verified": true,
    "gcs_url": "gs://corey-handoff-bridge/...",
    "gdrive_logged": false,
    "gdrive_log_path": "G:\\My Drive\\...",
    "git_verified": true,
    "git_commit": "abc1234",
    "compliance_score": 66,
    "issues": ["Missing HANDOFF_LOG.md entry"]
}
```

### Bulk Verify All

```python
POST /mcp/handoffs/verify-all

# Runs verification on all handoffs, updates compliance fields
```

---

## Detail Panel (Enhanced)

```
┌─────────────────────────────────────────────────────────────┐
│ [HarmonyLab] 🔵 v1.4.5-progress-fix                         │
├─────────────────────────────────────────────────────────────┤
│ From: Claude Code (Command Center)                          │
│ To: Claude.ai (Architect)                                   │
│ Created: 2026-02-07T23:00:00Z                               │
│ Status: Done                                                │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ COMPLIANCE                                    Score: 100%│ │
│ │                                                         │ │
│ │ ✓ GCS: gs://corey-handoff-bridge/harmonylab/outbox/...  │ │
│ │ ✓ Log: HANDOFF_LOG.md entry found                       │ │
│ │ ✓ Git: 7f90d74 - "fix: progress page API (v1.4.5)"      │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Preview:                                                    │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Fixed Progress page API endpoint mismatch. The frontend │ │
│ │ was calling endpoints that didn't exist...              │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ [View Full] [Re-verify] [Mark as Done] [Archive]            │
└─────────────────────────────────────────────────────────────┘
```

---

## Compliance Alert Banner

When compliance drops below threshold, show alert:

```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ COMPLIANCE ALERT: 3 handoffs missing GDrive log entries  │
│ Projects affected: ArtForge (2), MetaPM (1)                 │
│ [View Details] [Remediate Now]                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Background Jobs

### 1. GCS Sync (from original spec)

Scans GCS bucket and imports handoffs to database.

### 2. Compliance Verification Job (NEW)

Runs periodically to verify all handoffs:

```python
async def compliance_verification_job():
    """Run every hour to verify compliance."""
    handoffs = await get_all_handoffs()
    
    for handoff in handoffs:
        handoff.gcs_verified = await verify_gcs(handoff)
        handoff.gdrive_logged = await verify_gdrive_log(handoff)
        handoff.git_verified, handoff.git_commit = await verify_git_commit(handoff)
        handoff.compliance_score = calculate_compliance(handoff)
        
        await save_handoff(handoff)
    
    # Generate compliance summary
    await update_compliance_summary()
```

---

## Database Schema (Enhanced)

```sql
ALTER TABLE mcp_handoffs ADD COLUMN gcs_url NVARCHAR(500);
ALTER TABLE mcp_handoffs ADD COLUMN gcs_verified BIT DEFAULT 0;
ALTER TABLE mcp_handoffs ADD COLUMN gdrive_logged BIT DEFAULT 0;
ALTER TABLE mcp_handoffs ADD COLUMN git_commit NVARCHAR(50);
ALTER TABLE mcp_handoffs ADD COLUMN git_verified BIT DEFAULT 0;
ALTER TABLE mcp_handoffs ADD COLUMN compliance_score INT DEFAULT 0;
ALTER TABLE mcp_handoffs ADD COLUMN last_verified_at DATETIME2;
```

---

## Files to Create/Modify

| File | Description |
|------|-------------|
| `frontend/handoffs.html` | Dashboard with compliance columns |
| `frontend/js/handoffs.js` | Compliance filtering, verification |
| `frontend/css/handoffs.css` | Compliance indicators styling |
| `app/services/compliance_service.py` | NEW - Verification logic |
| `app/jobs/compliance_job.py` | NEW - Background verification |
| `app/routers/mcp.py` | Enhanced endpoints |
| `app/migrations.py` | New compliance columns |

---

## Testing Checklist

| Test | Expected |
|------|----------|
| Dashboard shows compliance columns | GCS, Log, Git, ✓ visible |
| Compliance filter works | Shows filtered results |
| Detail panel shows compliance | Links to GCS, GDrive, Git |
| Non-compliant highlighted | ⚠️ or ✗ icons visible |
| Verify endpoint works | Returns compliance status |
| Compliance summary accurate | Counts match actual state |

---

## Version

Bump to **v1.8.0** after implementation.

---

## Definition of Done

- [ ] Dashboard displays compliance columns
- [ ] Compliance filter works
- [ ] Detail panel shows compliance evidence with links
- [ ] Verification endpoints work
- [ ] Background job runs
- [ ] Compliance summary endpoint works
- [ ] Non-compliant items highlighted
- [ ] Version bumped to 1.8.0
- [ ] All tests pass
- [ ] Git committed (per policy!)
- [ ] Handoff sent

---

*Enhanced spec from Claude.ai (Architect)*
*Dashboard now serves as both visibility AND compliance verification tool*
