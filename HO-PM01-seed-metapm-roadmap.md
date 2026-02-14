🔴 MetaPM - Seed Roadmap Phases and Items into MetaPM Database
Time Stamp: 2026-02-13-09-30-00
__________________________________________________________________________________________

## Context

We are beginning to use MetaPM as the real-time tracking system for our development pipeline. The PromptForge V4 Roadmap defines 4 phases with specific tasks. These need to be entered into the MetaPM database so we can track them, test MetaPM's project tracking capabilities, and identify what's working vs. broken in our SDLC.

The roadmap document is at: `G:\My Drive\Code\Python\project-methodology\PromptForge_V4_Roadmap.html`

Also commit this roadmap file to the project-methodology repo and update HANDOFF_LOG.md.

## Task

### Part 1: Commit Roadmap to Repo

```
cd "G:\My Drive\Code\Python\project-methodology"
git add PromptForge_V4_Roadmap.html
git add HO-U9V0-metapm-mcp-server.md
git commit -m "docs: add PromptForge V4 Roadmap and HO-U9V0 MCP server spec"
git push origin main
```

Also add entries to HANDOFF_LOG.md for these documents.

### Part 2: Create Project in MetaPM

Create a project called "PromptForge V4 Pipeline" in MetaPM. If a project creation API exists, use it. If not, insert directly into the database.

### Part 3: Seed Phase 0 Tasks

Create these tasks in MetaPM under the PromptForge V4 Pipeline project.

Phase: 0 — Close Current Sprint (This week)

| Task ID | Title | Status | Project Tag | Notes |
|---------|-------|--------|-------------|-------|
| — | V4 Architecture design + agent files created | COMPLETE | 🟢 method | Completed 2026-02-12 |
| HO-R5S6-R1 | Documentation Protocol established | COMPLETE | 🟢 method | Accepted by CAI 2026-02-13 |
| HO-BS02 | Test backfill for bug sprint (60 tests) | COMPLETE | 🔴🟠🟣 multi | 57 passing, 3 pending re-run |
| HO-V4A1 | Verify agent files installed | IN_PROGRESS | 🟢 method | CC working on it |
| HO-MP01 | UAT: MetaPM bulk status count | PENDING_UAT | 🔴 metapm | UAT template ready |
| HO-MP02 | UAT: MetaPM tab persistence | PENDING_UAT | 🔴 metapm | UAT template ready |
| HO-AF01 | UAT: ArtForge provider persistence | UAT_FAILED | 🟠 artforge | 3/4 passed, Generate Images hangs |
| HO-EM02 | UAT: Etymython Unicode Greek text | UAT_FAILED | 🟣 etymython | 3/7 passed, corruption persists |
| — | Investigate unrelated working-tree changes | PENDING | 🟢 method | .vscode/settings.json, scripts/handoff |

### Part 4: Seed Phase 1 Tasks

Phase: 1 — MetaPM System of Record (Weeks 1-2)

| Task ID | Title | Status | Project Tag | Notes |
|---------|-------|--------|-------------|-------|
| HO-U9V0 | MCP Server + Reports + UAT Fix | PENDING | 🔴 metapm | Spec at HO-U9V0-metapm-mcp-server.md |
| HO-U9V1 | Fix UAT Submit + Enter UAT Results | PENDING | 🔴 metapm | Fixes results_text schema mismatch |
| — | Summary report endpoint | PENDING | 🔴 metapm | Part of HO-U9V0, spec in Section 6.1 |
| — | Detailed status report endpoint | PENDING | 🔴 metapm | Part of HO-U9V0, spec in Section 6.2 |
| — | Item history report endpoint | PENDING | 🔴 metapm | Part of HO-U9V0, spec in Section 6.3 |
| — | Dashboard UI for reports | PENDING | 🔴 metapm | Part of HO-U9V0 |
| — | Conductor agent MCP integration | PENDING | 🔴 metapm | Part of HO-U9V0 |
| — | Backfill existing HO items into MetaPM | PENDING | 🔴 metapm | After MCP server is built |

### Part 5: Seed Phase 2 Tasks

Phase: 2 — Automated Quality Gates (Weeks 2-3)

| Task ID | Title | Status | Project Tag | Notes |
|---------|-------|--------|-------------|-------|
| — | Playwright pilot on MetaPM | PENDING | 🔴 metapm | Most complex frontend |
| — | Pre-deploy test gate in Conductor | PENDING | 🟢 method | Blocks deploy without tests |
| — | UAT automation for API-testable items | PENDING | 🟢 method | Replace manual UAT where possible |
| — | Workflow effectiveness dashboard | PENDING | 🔴 metapm | Pass rates, rework frequency |

### Part 6: Seed Phase 3 Tasks

Phase: 3 — Semantic Word Graph (Weeks 3-8)

| Task ID | Title | Status | Project Tag | Notes |
|---------|-------|--------|-------------|-------|
| HO-W3X4 | Requirements spec | COMPLETE | 🟡🟣 multi | Full spec in HO-R5S6-R1 handoff |
| — | Sprint 1A: Schema + API (Super Flashcards) | PENDING | 🟡 flashcards | |
| — | Sprint 1B: Schema + API (Etymython) | PENDING | 🟣 etymython | |
| — | Sprint 1C: Cross-app linking + CORS | PENDING | 🟡🟣 multi | |
| — | Sprint 2A-B: Graph visualization | PENDING | 🟡🟣 multi | Cytoscape.js |
| — | Sprint 3: Mobile optimization + search | PENDING | 🟡🟣 multi | |
| — | Sprint 4: AI-assisted PIE root lookup | PENDING | 🟡🟣 multi | |

### Part 7: Seed Bug/Defect Tasks (from UAT findings)

| Task ID | Title | Status | Project Tag | Notes |
|---------|-------|--------|-------------|-------|
| HO-EM03 | Comprehensive Unicode cleanup + UI persistence | PENDING | 🟣 etymython | Audit all figures, fix all corruption |
| — | ArtForge: Generate Images button hangs on re-gen | BACKLOG | 🟠 artforge | Low priority per Corey |
| — | ArtForge: Design collection edit workflow | BACKLOG | 🟠 artforge | Remove Generate Images for now |
| — | Etymython: UI expand/collapse persistence | PENDING | 🟣 etymython | Part of HO-EM03 |
| — | MetaPM: Re-run bulk status E2E tests | PENDING | 🔴 metapm | Zombie Chrome blocking |

### Part 8: Verify and Report

After seeding all tasks:

1. Query the MetaPM API to list all tasks and verify they're stored correctly
2. Open the MetaPM dashboard and verify tasks are visible
3. Report any issues with the dashboard display (missing tasks, wrong status, etc.)
4. Screenshot or describe what the dashboard shows

## Deliverable Checklist

- [ ] Roadmap committed to project-methodology repo
- [ ] HO-U9V0 spec committed to repo
- [ ] HANDOFF_LOG.md updated
- [ ] "PromptForge V4 Pipeline" project created in MetaPM
- [ ] All Phase 0 tasks seeded (9 items)
- [ ] All Phase 1 tasks seeded (8 items)
- [ ] All Phase 2 tasks seeded (4 items)
- [ ] All Phase 3 tasks seeded (7 items)
- [ ] Bug/defect tasks seeded (5 items)
- [ ] MetaPM dashboard shows all tasks correctly
- [ ] Any dashboard display issues documented
- [ ] Completion report follows 7-section template
- [ ] Handoff uploaded to GCS

## Rules

- Deploy target is `metapm-v2` (NOT `metapm`).
- Read MetaPM CLAUDE.md first to understand the data model and API.
- If MetaPM doesn't have a task creation API, use direct database INSERT statements.
- If the task status values above don't match MetaPM's enum, document what mappings you used.
- Include the full list of created tasks with their MetaPM IDs in the completion report.

__________________________________________________________________________________________
CAI REVIEW: Required

CAI CHECKLIST (for your response):
□ Assign ID (HO-XXXX format)
□ Create handoff doc if code/special chars needed
□ CC prompt must be clean (pasteable, no code fences for prompt itself)
□ Include Handoff Bridge link if doc created
□ List files for download
□ Include CC deliverables template in prompt

CC DELIVERABLES (include in CC prompt):
Your deliverables are:
- ID: HO-PM01
- Status: COMPLETE / PARTIAL / BLOCKED / PENDING-REVIEW
- Handoff URL: Full GCS path
- Summary table: Project, Task, Status, Commit, Handoff URL
- Garbage collect: Delete processed handoff from inbox
- Git: Commit with ID in message
