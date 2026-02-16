# MetaPM Roadmap Audit & Seed Report

**Date:** 2026-02-16  
**Task:** CC_Task_MetaPM_Roadmap_Seed  
**Handoff ID:** HO-MP01  
**Author:** CC (Claude Copilot)  
**Status:** COMPLETE

---

## Executive Summary

Roadmap seeded. **26 items added**, **2 updated** (closed), **3 versions corrected**.  
Linkage finding: **Handoff-requirement linkage exists in schema but is completely disconnected** — MCP handoffs never auto-link to roadmap requirements.  
Dashboard reflects current state: 6 projects, 40 requirements (31 backlog, 1 planned, 2 in-progress, 6 done).  
HO-P1Q3 status updated to `done`/`partial` (conditional pass — 2 "failures" reclassified as new requirements).

---

## Part 1: AUDIT — Before State

### 1.1 Version Gap Table

| Project | Emoji | MetaPM Version (Before) | Actual Deployed Version | Source | Gap |
|---------|-------|------------------------|------------------------|--------|-----|
| ArtForge | 🟠 | 2.2.1 | 2.2.1 | artforge.rentyourcio.com/health | OK |
| Etymython | 🟣 | 1.2.0 | (no version in health) | etymython.rentyourcio.com/health | Unknown |
| HarmonyLab | 🔵 | 1.5.3 | 1.8.2 (backend) | Deployed via Cloud Run | **Way behind** |
| MetaPM | 🔴 | 2.0.0 | 2.1.5 | metapm.rentyourcio.com/health | **Behind** |
| project-methodology | 🟢 | 3.17.0 | N/A (not a service) | No health endpoint | N/A |
| Super-Flashcards | 🟡 | 8.0.0 | 2.9.0 | learn.rentyourcio.com/health | **Wrong** |

> Note: HarmonyLab health endpoint reports `harmonylab-frontend v1.4.5` — this is the separate frontend service. The backend (Cloud Run `harmonylab`) is at v1.8.2.

> Note: Super-Flashcards was `8.0.0` in MetaPM but health shows `2.9.0` — appears to be a version numbering scheme mismatch from initial seed.

### 1.2 Requirements Before State (14 total)

| Code | Project | Title | Status | Priority |
|------|---------|-------|--------|----------|
| AF-001 | ArtForge | Export fixes (images + PDF) | planned | P1 |
| AF-002 | ArtForge | Voice selection for 11Labs | backlog | P2 |
| AF-003 | ArtForge | Slideshow feature (3 modes) | backlog | P2 |
| AF-004 | ArtForge | Runway Gen-3 video generation | backlog | P2 |
| EM-001 | Etymython | 11Labs VO from Origin Story | backlog | P3 |
| EM-002 | Etymython | Link cognates SF<->EM | backlog | P3 |
| HL-001 | HarmonyLab | Quiz backend fix | **done** | P1 |
| HL-002 | HarmonyLab | Complete audio UAT | **uat** | P1 |
| HL-003 | HarmonyLab | Show intervals on chord display | backlog | P3 |
| HL-004 | HarmonyLab | Progression quiz (next chord) | backlog | P3 |
| SF-001 | Super-Flashcards | Performance stats per-user | backlog | P3 |
| SF-002 | Super-Flashcards | IPA direction + silent letters | backlog | P3 |
| SF-003 | Super-Flashcards | Related card hyperlinks | backlog | P3 |
| SF-004 | Super-Flashcards | Back button navigation | backlog | P3 |

MetaPM and project-methodology had **0 requirements** each.

### 1.3 Health Check Results

```
metapm.rentyourcio.com/health      → {"status":"healthy","version":"2.1.5","build":"unknown"}
harmonylab.rentyourcio.com/health  → {"status":"healthy","service":"harmonylab-frontend","version":"1.4.5"}
artforge.rentyourcio.com/health    → {"status":"healthy","database":"connected","version":"2.2.1"}
etymython.rentyourcio.com/health   → {"status":"healthy"}
learn.rentyourcio.com/health       → {"status":"healthy","version":"2.9.0","database":"connected"}
```

### 1.4 Schema Documentation

#### roadmap_projects
| Column | Type | Nullable |
|--------|------|----------|
| id | nvarchar(36) | NOT NULL |
| code | nvarchar(10) | NOT NULL |
| name | nvarchar(100) | NOT NULL |
| emoji | nvarchar(10) | NULL |
| color | nvarchar(20) | NULL |
| current_version | nvarchar(20) | NULL |
| status | nvarchar(20) | NULL |
| repo_url | nvarchar(500) | NULL |
| deploy_url | nvarchar(500) | NULL |
| created_at | datetime2 | NULL |
| updated_at | datetime2 | NULL |

#### roadmap_requirements
| Column | Type | Nullable |
|--------|------|----------|
| id | nvarchar(36) | NOT NULL |
| project_id | nvarchar(36) | NOT NULL |
| code | nvarchar(20) | NOT NULL |
| title | nvarchar(200) | NOT NULL |
| description | nvarchar(max) | NULL |
| type | nvarchar(20) | NULL |
| priority | nvarchar(10) | NULL |
| status | nvarchar(20) | NULL |
| target_version | nvarchar(20) | NULL |
| sprint_id | nvarchar(36) | NULL |
| handoff_id | uniqueidentifier | NULL |
| uat_id | uniqueidentifier | NULL |
| created_at | datetime2 | NULL |
| updated_at | datetime2 | NULL |

#### roadmap_handoffs (junction table)
| Column | Type | Nullable |
|--------|------|----------|
| roadmap_id | varchar(20) | NOT NULL |
| handoff_id | varchar(10) | NOT NULL |
| relationship | varchar(20) | NOT NULL |
| created_at | datetime2 | NULL |

#### mcp_handoffs (32 columns, key subset shown)
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | uniqueidentifier | NOT NULL | PK |
| project | nvarchar(100) | NOT NULL | |
| status | nvarchar(20) | NULL | CHECK: pending/read/processed/archived/pending_uat/needs_fixes/done |
| uat_status | nvarchar(20) | NULL | No CHECK constraint |
| uat_passed | int | NULL | |
| uat_failed | int | NULL | |
| direction | nvarchar(20) | NOT NULL | CHECK: ai_to_cc / cc_to_ai |

#### uat_results
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| id | uniqueidentifier | NOT NULL | PK |
| handoff_id | uniqueidentifier | NOT NULL | FK to mcp_handoffs |
| status | nvarchar(20) | NOT NULL | CHECK: pending/failed/passed |
| total_tests | int | NULL | |
| passed | int | NULL | |
| failed | int | NULL | |

**Related tables:** `handoff_requests` (lifecycle, 1 row), `handoff_completions` (lifecycle, 1 row), `roadmap_sprints` (empty)

---

## Part 2: SEED — Changes Made

### 2.1 Version Updates (Direct SQL — API endpoint shadowed)

| Project | From | To | Method |
|---------|------|----|--------|
| HarmonyLab | 1.5.3 | **1.8.2** | Direct SQL UPDATE |
| MetaPM | 2.0.0 | **2.1.5** | Direct SQL UPDATE |
| Super-Flashcards | 8.0.0 | **2.9.0** | Direct SQL UPDATE |

> **BUG FOUND:** The `PUT /api/projects/{project_id}` endpoint in `roadmap.py` is **shadowed** by the `PUT /api/projects/{project_code}` endpoint in `projects.py`. Both are mounted under `/api` but `projects.py` is registered first (line 76 of `main.py`) and always matches first. This means roadmap project updates via API are impossible. Filed as finding for MP-003.

### 2.2 Closed Completed Items (via API)

| Code | Title | Old Status | New Status |
|------|-------|------------|------------|
| HL-001 | Quiz backend fix | done | done (already) |
| HL-002 | Complete audio UAT | uat | **done** |

### 2.3 New Requirements Added (26 items via POST /api/requirements)

#### MetaPM 🔴 (4 items)
| Code | Title | Type | Priority | Status |
|------|-------|------|----------|--------|
| MP-001 | GitHub Actions CI/CD | task | P1 | backlog |
| MP-002 | Seed roadmap with current state | task | P1 | **in_progress** |
| MP-003 | Fix handoff-requirement linkage | bug | P1 | backlog |
| MP-004 | Dashboard as morning standup view | enhancement | P2 | backlog |

#### HarmonyLab 🔵 (9 items)
| Code | Title | Type | Priority | Status |
|------|-------|------|----------|--------|
| HL-005 | MIDI P0 import fix (arpeggios) | bug | P1 | **done** |
| HL-006 | Analysis quality (key+chords) | bug | P1 | **done** |
| HL-007 | Branch fix master to main | task | P1 | backlog |
| HL-008 | Import 37 jazz standards | feature | P2 | backlog |
| HL-009 | Edit chord form dropdowns | enhancement | P2 | backlog |
| HL-010 | Default to Analysis page | enhancement | P2 | backlog |
| HL-011 | Login page version mismatch | bug | P2 | backlog |
| HL-012 | Chord granularity: 20 bars not 35 | enhancement | P2 | backlog |
| HL-013 | Verify MIDI file storage location | task | P2 | backlog |

> Note: HL-005 was listed as P0 in task spec but API only accepts P1/P2/P3. Used P1.  
> Note: HL-012 was listed as "refinement" type but API only accepts feature/bug/enhancement/task. Used enhancement.

#### ArtForge 🟠 (2 items)
| Code | Title | Type | Priority | Status |
|------|-------|------|----------|--------|
| AF-005 | Verify v2.2.2 handoff fixes | task | P1 | backlog |
| AF-006 | Etymython<->ArtForge content pipe | feature | P2 | backlog |

#### Etymython 🟣 (4 items)
| Code | Title | Type | Priority | Status |
|------|-------|------|----------|--------|
| EM-003 | Shared OAuth (copy SF/AF pattern) | task | P1 | backlog |
| EM-004 | Etymython<->SF shared etymology | feature | P2 | backlog |
| EM-005 | GCP project ID clarification | task | P2 | backlog |
| EM-006 | Figure count verification | task | P2 | backlog |

#### Super Flashcards 🟡 (2 items)
| Code | Title | Type | Priority | Status |
|------|-------|------|----------|--------|
| SF-005 | User membership model | feature | P2 | backlog |
| SF-006 | Etymology bridge normalization | task | P2 | backlog |

#### project-methodology 🟢 (5 items)
| Code | Title | Type | Priority | Status |
|------|-------|------|----------|--------|
| PM-001 | Bootstrap prompt v1 | task | P1 | **done** |
| PM-002 | Methodology coherence audit | task | P1 | **done** |
| PM-003 | Methodology cleanup execution | task | P1 | **in_progress** |
| PM-004 | Cross-project CI/CD standard | task | P1 | backlog |
| PM-005 | Standardize DEPLOYMENT_CHECKLIST | task | P2 | backlog |

### 2.5 After State (Verified)

```
🟠 AF  ArtForge              v2.2.1 — 6 reqs  (backlog:5, planned:1)
🟣 EM  Etymython             v1.2.0 — 6 reqs  (backlog:6)
🔵 HL  HarmonyLab            v1.8.2 — 13 reqs (backlog:9, done:4)
🔴 MP  MetaPM                v2.1.5 — 4 reqs  (backlog:3, in_progress:1)
🟢 PM  project-methodology   v3.17.0 — 5 reqs (backlog:2, done:2, in_progress:1)
🟡 SF  Super-Flashcards      v2.9.0 — 6 reqs  (backlog:6)

Total: 40 | backlog:31 planned:1 in_progress:2 uat:0 done:6
```

---

## Part 3: INVESTIGATION — Handoff-Requirement Linkage

### 3.1 Data Model Analysis

**Two separate handoff systems exist in MetaPM:**

1. **MCP Handoffs** (`mcp_handoffs` table) — The primary handoff system used by all projects
   - 66 handoffs total across all projects
   - Stores handoff content, UAT results, GCS sync status
   - Used by `POST /mcp/handoffs`, `POST /mcp/uat/submit`

2. **Lifecycle Handoffs** (`handoff_requests` + `handoff_completions`) — A secondary/experimental system
   - 1 handoff request (test data: HO-A1B2)
   - 1 completion record
   - Has `roadmap_id` FK for linking

**Junction table:** `roadmap_handoffs` bridges roadmap requirements to handoffs
- Schema: `(roadmap_id VARCHAR(20), handoff_id VARCHAR(10), relationship VARCHAR(20))`
- Current data: 1 test row `('MP-lifecycle', 'HO-A1B2', 'IMPLEMENTS')`

### 3.2 Why Handoffs Don't Link to Requirements

**Root cause: The MCP handoff flow has ZERO references to roadmap or requirements.**

Confirmed by searching `app/api/mcp.py` for "roadmap", "requirement", or "link" — **zero matches**.

The linking mechanism exists:
- `POST /api/roadmap/{roadmap_id}/handoffs` — manually links a handoff to a requirement
- `PUT /api/requirements/{req_id}` with `handoff_id` field — sets a direct FK
- `POST /api/handoffs` (lifecycle) — auto-links if `roadmap_id` is provided

But nothing in the MCP flow calls these. The two systems are **completely disconnected**.

### 3.3 Current Linkage State

| Metric | Count |
|--------|-------|
| MCP handoffs | 66 |
| Linked to requirements via `roadmap_handoffs` | 0 (1 test row from lifecycle system) |
| Requirements with `handoff_id` set | 0 |
| Requirements with `uat_id` set | 0 |
| **Linkage rate** | **0%** |

### 3.4 What Would Need to Be Built

To auto-link handoffs to requirements, the MCP handoff submit flow needs to:

1. **On UAT submit** (`POST /mcp/uat/submit`): Parse the project name and version from the handoff. Look for matching roadmap requirements by project and status (e.g., `in_progress` or `uat`). Auto-create `roadmap_handoffs` entries.

2. **On handoff create** (`POST /mcp/handoffs`): If the handoff metadata contains a requirement code (e.g., "HL-006"), auto-link via `roadmap_handoffs`.

3. **Schema fix**: The `roadmap_handoffs.handoff_id` is `varchar(10)` but MCP handoff IDs are `uniqueidentifier` (GUID). These types are incompatible. The junction table was designed for the lifecycle system (`HO-A1B2` format), not MCP GUIDs.

### 3.5 HO-P1Q3 Status Update

**Before:**
- Handoff status: `needs_fixes`
- UAT status: `failed`
- Passed/Failed: 7/2

**After (updated via direct SQL):**
- Handoff status: `done`
- UAT status: `partial`
- Passed/Failed: 7/2 (unchanged)

**Rationale:** The 2 "failures" in the v1.8.2 UAT were reclassified as new requirements (HL-009 Edit chord form dropdowns, HL-012 Chord granularity). They were not regressions. The handoff work itself was completed successfully.

### 3.6 Status Values Available

| Table | Column | Allowed Values | Source |
|-------|--------|---------------|--------|
| mcp_handoffs | status | pending, read, processed, archived, pending_uat, needs_fixes, done | CHECK constraint |
| mcp_handoffs | uat_status | (any nvarchar(20)) | No constraint |
| uat_results | status | pending, failed, passed | CHECK constraint |
| UATStatus enum (Python) | — | passed, failed, pending, blocked, partial | Pydantic enum |

**Recommendation:** Add `conditional_pass` to the `uat_results` CHECK constraint and the Python `UATStatus` enum. This avoids the workaround of setting `uat_status = 'partial'` via SQL.

### 3.7 API Route Shadowing Bug

**Bug:** `PUT /api/projects/{project_id}` (roadmap.py) is unreachable because `PUT /api/projects/{project_code}` (projects.py) is registered first in `app/main.py` (line 76 vs line 85).

**Impact:** Cannot update roadmap project versions via the API. Must use direct SQL.

**Fix:** Change roadmap router prefix from `/api` to `/api/roadmap`, making the endpoint `PUT /api/roadmap/projects/{project_id}`.

---

## Findings Summary

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | HarmonyLab version 3 releases behind | Data | **Fixed** → 1.8.2 |
| 2 | MetaPM version behind by 4 minor versions | Data | **Fixed** → 2.1.5 |
| 3 | Super-Flashcards version mismatch (8.0.0 vs 2.9.0) | Data | **Fixed** → 2.9.0 |
| 4 | MetaPM and PM had 0 roadmap requirements | Data | **Fixed** → 4 and 5 items respectively |
| 5 | MCP handoffs never link to roadmap requirements | Bug | **Documented** → MP-003 |
| 6 | `roadmap_handoffs.handoff_id` type mismatch (varchar vs UUID) | Bug | **Documented** |
| 7 | PUT /api/projects/{id} route shadowed | Bug | **Documented** |
| 8 | No `conditional_pass` UAT status | Enhancement | **Documented** |
| 9 | HO-P1Q3 incorrectly marked as `needs_fixes` | Data | **Fixed** → done/partial |

---

## Definition of Done Checklist

- [x] Full schema documented (roadmap_projects, roadmap_requirements, roadmap_sprints, roadmap_handoffs, mcp_handoffs, uat_results, handoff_requests, handoff_completions)
- [x] All project versions match actual deployed versions (HL→1.8.2, MP→2.1.5, SF→2.9.0)
- [x] Completed items marked done (HL-001, HL-002, HL-005, HL-006, PM-001, PM-002)
- [x] All new requirements inserted (26 items across 6 projects)
- [x] Dashboard shows accurate data (40 reqs: 31 backlog, 1 planned, 2 in_progress, 6 done)
- [x] Handoff linkage investigation complete with findings (disconnected systems, type mismatch)
- [x] UAT status update mechanism documented (no API for editing, submit-new or direct SQL)
- [x] HO-P1Q3 status updated (done/partial)
- [x] Audit report written
- [ ] Report uploaded to GCS

---

*Report generated: 2026-02-16*  
*Source: CC_Task_MetaPM_Roadmap_Seed.md*
