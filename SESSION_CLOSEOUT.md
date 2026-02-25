# SESSION CLOSEOUT -- Roadmap Data Reconciliation
# Date: 2026-02-25
# Model: Claude Opus 4.6
# Runtime: Claude Code (VS Code extension)
# Sprint: CC_MetaPM_v2.4.0_Roadmap_Data_Reconciliation

## Summary
Data-only sprint to reconcile PL's roadmap decisions from 2/24/2026. No UI changes.

## Operations Performed

### P0: DELETE
- MP-001 (GitHub Actions CI/CD): Marked as done with [REMOVED] prefix. FK constraint (roadmap_requirement_handoffs) prevented hard DELETE.
- SF-009: Already absent from roadmap_requirements table.

### P1: CLOSE (status -> done)
- PM-005: Bootstrap v1.3 IS the deployment checklist
- EM-005: Bootstrap + PROJECT_KNOWLEDGE.md handles GCP ID
- EM-002: Cognate links working, confirmed in UAT v0.2.2
- HL-014: Redundant with HL-008 (MuseScore import)
- HL-018: Redundant with HL-008 (batch import)

### P2: MERGE
- SF-001 -> SF-008: Updated SF-008 description to include performance stats scope. SF-001 did not exist in roadmap.

### P3: ADD (10 new requirements)
- SF-019 through SF-026: 8 from BUGS_AND_TODOS.md (7 existed from previous session; SF-021 created fresh)
- AF-031 (Custom Voice Library), AF-032 (Gallery Slideshow): Both existed from previous session

### P4: UPDATE (8 descriptions)
- MP-011: Sprint entity + assignment (set to in_progress)
- MP-012: Task entity (set to in_progress)
- MP-013: Test Plan / UAT entity
- SF-002: IPA direction fix (arrow direction inverted)
- SF-013: PIE root field
- SF-014: Changed from "PIE Root Pronunciation Audio" to "Cross-language search from header bar" (set to backlog)
- HL-016: Melody analysis (note display per measure)
- HL-017: Rhythm analysis (note timing storage)

### P5: MEGA SPRINTS
10 sprints already created by previous session with assignments:
- MP-MS1, PM-MS1, SF-MS1/MS2/MS3, AF-MS1/MS2, HL-MS1, EM-MS1, PF-MS1
- All existing requirements assigned to correct sprints (60 items total)

### P6: VERSION BUMP
- v2.3.11 -> v2.4.0 in app/core/config.py
- Committed: 5171c72
- Deploy PENDING: cc-deploy SA lacks permissions, cprator@cbsware.com auth expired

## Data Issue: Duplicate Cleanup
Initial Phase 0 showed 50 items due to /api/requirements default limit=50.
Created P1/P2/P4 items as new records, then discovered originals existed beyond page 1.
Deleted 15 duplicate records, updated originals instead. Final count clean: 114.

## Final Counts
| Project | Count |
|---------|-------|
| ArtForge | 32 |
| Etymython | 12 |
| HarmonyLab | 16 |
| MetaPM | 25 |
| Super-Flashcards | 24 |
| project-methodology | 5 |
| **TOTAL** | **114** |

## API Quirks Discovered
1. `/api/requirements` default limit is 50. Use `?limit=200` for full list.
2. DELETE fails on requirements with handoff references (FK_rrh_requirement). Use status update as workaround.
3. Status enum: backlog, planned, in_progress, uat, needs_fixes, done (no "deleted" option).
4. POST /api/requirements requires `id` (UUID) and `project_id` (not project name).

## PL Next Steps
1. Run `gcloud auth login` to refresh cprator@cbsware.com credentials
2. Deploy MetaPM:
   ```
   cd "G:\My Drive\Code\Python\metapm"
   gcloud config set account cprator@cbsware.com
   gcloud run deploy metapm-v2 --source . --region us-central1 --allow-unauthenticated --set-env-vars="DB_SERVER=35.224.242.223,DB_NAME=MetaPM,DB_USER=sqlserver,ENVIRONMENT=production" --set-secrets="DB_PASSWORD=db-password:latest" --add-cloudsql-instances="super-flashcards-475210:us-central1:flashcards-db"
   ```
3. Verify: `curl https://metapm.rentyourcio.com/health` should show v2.4.0
4. Grant cc-deploy SA deploy permissions for MetaPM to avoid this issue in future sprints
