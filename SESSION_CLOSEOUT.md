# Session Closeout: MP-DEPLOY-v2.4.0
## Date: 2026-02-25
## Model: Claude Opus 4.6 / Claude Code (VS Code extension)

### Deliverables
- [x] MetaPM v2.4.0 deployed to Cloud Run
- [x] /health returns v2.4.0
- [x] 44 UAT checks executed (pass count: 44)
- [x] UAT report generated from standard template (UAT_MetaPM_v2.4.0.html)
- [x] UAT submitted to MetaPM (handoff ID: B8E9CEE2, UAT ID: 6BC58603)
- [x] cc-deploy SA permissions granted (role: iam.serviceAccountUser)
- [x] cc-deploy SA MetaPM deploy test: PASS
- [x] PK.md updated
- [x] Git committed and pushed

### Deploy Command Used
```
gcloud run deploy metapm-v2 --source . --region us-central1 --allow-unauthenticated \
  --set-env-vars="DB_SERVER=35.224.242.223,DB_NAME=MetaPM,DB_USER=sqlserver,ENVIRONMENT=production" \
  --set-secrets="DB_PASSWORD=db-password:latest" \
  --add-cloudsql-instances="super-flashcards-475210:us-central1:flashcards-db"
```
Deployed as: cprator@cbsware.com
Revision: metapm-v2-00096-q7r
Service URL: https://metapm-v2-57478301787.us-central1.run.app

### UAT Summary
Total: 44 | Pass: 44 | Fail: 0 | Skip: 0
Failed tests: none

6 status corrections applied during UAT:
- MP-001, PM-005, EM-005, EM-002, HL-014, HL-018 were in_progress (prior session's updates didn't persist on originals after duplicate cleanup), corrected to done.

### cc-deploy SA Permissions Granted
- Role added: `roles/iam.serviceAccountUser`
- This was the missing role causing "PERMISSION_DENIED: Permission 'iam.serviceaccounts.actAs' denied"
- Full cc-deploy roles now: run.admin, iam.serviceAccountUser, artifactregistry.writer, cloudbuild.builds.editor, cloudsql.client, secretmanager.secretAccessor, storage.admin
- Verified: cc-deploy can now describe and deploy MetaPM without cprator workaround

### Lessons Learned

LESSON: Status updates via PUT may silently fail when duplicate records exist
PROJECT: MetaPM
CATEGORY: technical
ROUTES TO: PROJECT_KNOWLEDGE.md (MetaPM)
ACTION: When updating requirements by ID, always verify with a subsequent GET. The prior session deleted 15 duplicates but the original records' statuses weren't updated. This session discovered and corrected 6 requirements stuck at in_progress.

LESSON: cc-deploy SA needs iam.serviceAccountUser to deploy Cloud Run services
PROJECT: MetaPM (applies to all projects)
CATEGORY: technical
ROUTES TO: PROJECT_KNOWLEDGE.md (all projects), Bootstrap
ACTION: The iam.serviceAccountUser role allows the SA to "act as" the compute service account during deploy. Without it, deploy fails with actAs permission error. Now granted at project level.

### Blockers Encountered
None — cprator@cbsware.com was pre-authenticated by PL before this session.

### Next Steps for PL
1. Open UAT_MetaPM_v2.4.0.html in browser, click APPROVED, submit (optional — UAT already submitted programmatically)
2. Verify cc-deploy works for MetaPM deploys in next CC session (no cprator needed)
3. Consider granting iam.serviceAccountUser to cc-deploy for other projects if deploy issues occur
