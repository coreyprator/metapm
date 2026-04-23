# DIAG-005: OAuth Outage on /app/login (P0)

**Date:** 2026-04-23  
**Duration:** Read-only diagnostic (1.5h)  
**Scope:** MetaPM OAuth authentication failure blocking all UAT walking  
**Challenge token:** `689cc47a6193ea928264b0bdcd08a585`

---

## Context

PL reported inability to authenticate to ANY MetaPM UAT page as of 2026-04-23. All requests to `/app/login` return 503 with body:

```
OAuth Not Configured — GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set.
```

This outage blocks:
- MP58 closeout UAT
- MP58B scoping  
- All other sprints awaiting PL UAT verification

The issue regresses BUG-076 and BUG-095 fixes despite no deploy reported since DIAG-003 (2026-04-22 ~16:00 UTC), which had confirmed OAuth secrets were bound correctly. Cross-portfolio impact: SF UAT also affected (9B3C6614).

---

## Evidence Capture

### Step 1: Service State

**Command:**
```bash
gcloud run services describe metapm-v2 --region=us-central1 --format=yaml
```

**Findings:**
- Active revision receiving 100% traffic: **metapm-v2-00425-ljl**
- Latest created revision: metapm-v2-00436-mzd
- Latest ready revision: metapm-v2-00428-6wv
- Traffic configuration: 100% → 00425-ljl (matches DIAG-003 baseline)
- Service account: cc-deploy@super-flashcards-475210.iam.gserviceaccount.com

**H5 Assessment:** Traffic split unchanged from DIAG-003. H5 **ruled out**.

### Step 2: Revision Deploy Config

**Command:**
```bash
gcloud run revisions describe metapm-v2-00425-ljl --region=us-central1 --format=yaml
```

**Findings:**

Revision **metapm-v2-00425-ljl** environment variables:
```yaml
env:
  - name: DB_SERVER
    value: 35.224.242.223
  - name: DB_NAME
    value: MetaPM
  - name: DB_USER
    value: sqlserver
  - name: ENVIRONMENT
    value: production
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        key: latest
        name: db-password
```

**CRITICAL FINDING:** No Google OAuth secrets bound. Expected but missing:
- `GOOGLE_CLIENT_ID` (from secret metapm-google-oauth-client-id)
- `GOOGLE_CLIENT_SECRET` (from secret metapm-google-oauth-client-secret)

Also missing: `MCP_API_KEY` (from secret metapm-api-key)

Revision timestamps:
- Created: 2026-04-22T00:08:23.976437Z
- Active: 2026-04-22T12:46:18.641104Z (traffic switch time)

**Cross-check on newer revision 00428-6wv:**

Environment variables:
```yaml
env:
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        key: latest
        name: db-password
  - name: MCP_API_KEY
    value: gvhGURyMZRa/jHZEKjcv2rljz2uuMnO9ihraVsZNi6I=
```

Still no OAuth secrets bound. Note: MCP_API_KEY is hardcoded as plaintext (security concern but not the current outage cause).

### Step 3: Secret Version Audit

**Command:**
```bash
gcloud secrets versions list metapm-google-oauth-client-secret
```

**Findings:**
```
NAME  STATE    CREATED              DESTROYED
1     enabled  2026-04-21T22:49:37  -
```

Secret exists, single version, **STATE=enabled**, created ~26 hours before outage report.

**H1 Assessment:** Secret not disabled or destroyed. H1 **ruled out**.

**H2 Assessment:** Only one version exists (version 1), so `:latest` pointer cannot have advanced to an inaccessible version. H2 **ruled out**.

### Step 4: Secret IAM Policy

**Command:**
```bash
gcloud secrets get-iam-policy metapm-google-oauth-client-secret
```

**Findings:**
```yaml
bindings:
- members:
  - serviceAccount:cc-deploy@super-flashcards-475210.iam.gserviceaccount.com
  role: roles/secretmanager.secretAccessor
etag: BwZQAD3sZd4=
version: 1
```

Runtime service account (cc-deploy@) has `secretAccessor` role. IAM permissions intact.

### Step 5: SF and EM Secret State Cross-Check

**Commands:**
```bash
gcloud secrets versions list sf-google-oauth-client-secret
gcloud secrets versions list em-google-oauth-client-secret
```

**Findings:**

SF OAuth secret:
```
NAME  STATE    CREATED              DESTROYED
1     enabled  2026-04-21T22:49:42  -
```

EM OAuth secret:
```
NAME  STATE    CREATED              DESTROYED
1     enabled  2026-04-21T22:49:39  -
```

Both enabled, created within 5 seconds of MetaPM's secret. No collision pattern detected.

**H3 Assessment:** SF/EM secret state changes not affecting MetaPM. H3 **ruled out**.

### Step 6: Production Response Capture

**Command:**
```bash
curl -i https://metapm.rentyourcio.com/app/login
```

**Findings:**
```
HTTP/1.1 503 Service Unavailable
content-type: text/html; charset=utf-8
date: Thu, 23 Apr 2026 13:21:07 GMT
server: Google Frontend
Content-Length: 592

<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>OAuth Not Configured</title>
...
<h1 style="color:#d29922">OAuth Not Configured</h1>
<p style="color:#8b949e">GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set.<br>
Contact the system administrator.</p>
...
```

Production response confirms application-level detection of missing environment variables.

### Step 7: Cloud Run Error Logs

**Command:**
```bash
gcloud logging read 'resource.type="cloud_run_revision" resource.labels.service_name="metapm-v2" severity>=ERROR' --limit=50 --format=json --freshness=2h
```

**Findings:**
```
ERROR: (gcloud.logging.read) PERMISSION_DENIED: Permission denied for all log views. 
This command is authenticated as cc-deploy@super-flashcards-475210.iam.gserviceaccount.com
```

cc-deploy@ service account lacks `logging.viewer` or equivalent IAM role. Logs inaccessible for this diagnostic. Per DIAG-003 pattern, this is a known cc-deploy@ limitation and does not block root cause identification.

---

## Verdict

### Root Cause

**Deployment configuration regression**: Google OAuth secrets (`metapm-google-oauth-client-id` and `metapm-google-oauth-client-secret`) exist in Secret Manager with correct IAM bindings but are **not bound to Cloud Run revisions** via `--update-secrets` flags during deployment.

This is distinct from all hypotheses H1-H6:
- **Not H1** (secret version disabled/destroyed): Secret version 1 is `enabled`
- **Not H2** (latest pointer advanced): Only one version exists
- **Not H3** (SF/EM collision): All three service secrets are independent and enabled
- **Not H4** (OAuth client revoked): Would produce different error from Google OAuth flow, not "must be set" from app startup
- **Not H5** (traffic split changed): Traffic remains 100% on 00425-ljl as in DIAG-003
- **Not H6** (legacy secret being read): Application error explicitly states env vars not set, indicating nothing is being read

### Timeline Reconstruction

1. **2026-04-21 22:49:37-42** — All three OAuth secrets (MetaPM, SF, EM) created in Secret Manager within 5-second window
2. **2026-04-22 00:08:23** — Revision metapm-v2-00425-ljl created WITHOUT OAuth secrets bound
3. **2026-04-22 12:46:18** — Traffic switched to revision 00425-ljl (or revision became active)
4. **2026-04-22 ~16:00** — DIAG-003 diagnostic (timestamp approximate from prompt)
5. **2026-04-23 ~13:00** — PL reports OAuth outage; DIAG-005 initiated

### Why DIAG-003 Might Have Missed This

Two scenarios:
1. DIAG-003 was run against a different revision (not 00425-ljl) that *did* have secrets bound
2. DIAG-003 only verified Secret Manager state (secrets exist + IAM correct) but did not inspect Cloud Run revision environment bindings

The prompt states "no deploy since DIAG-003...confirmed those secrets bound correctly" — this suggests DIAG-003 found secrets in Secret Manager but may not have verified revision-level binding.

### Supporting Evidence

- Revision 00425-ljl env spec: Only `DB_PASSWORD` secret bound (Step 2)
- Revision 00428-6wv env spec: Only `DB_PASSWORD` bound; `MCP_API_KEY` as plaintext (Step 2)
- Latest service template (generation 454): Shows `MCP_API_KEY` from secret but no OAuth secrets (Step 1)
- Production error explicitly reports missing env vars (Step 6)

---

## Fix Recipe

### Immediate Action Required (PL execution)

Run the following gcloud command to update the MetaPM Cloud Run service with proper OAuth secret bindings:

```bash
gcloud run services update metapm-v2 \
  --region=us-central1 \
  --update-secrets=GOOGLE_CLIENT_ID=metapm-google-oauth-client-id:latest,GOOGLE_CLIENT_SECRET=metapm-google-oauth-client-secret:latest
```

**Expected outcome:**
- New revision created with GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET bound from Secret Manager
- New revision automatically receives 100% traffic
- `/app/login` returns OAuth redirect (200 or 302) instead of 503
- UAT pages become accessible after OAuth flow completes

**Test verification:**
```bash
curl -i https://metapm.rentyourcio.com/app/login
```
Should return HTTP 302 redirect to Google OAuth consent screen (or 200 if already rendering page), not 503.

### Optional Simultaneous Fix

If `MCP_API_KEY` should also be bound from Secret Manager (instead of hardcoded plaintext in revision 00428):

```bash
gcloud run services update metapm-v2 \
  --region=us-central1 \
  --update-secrets=GOOGLE_CLIENT_ID=metapm-google-oauth-client-id:latest,GOOGLE_CLIENT_SECRET=metapm-google-oauth-client-secret:latest,MCP_API_KEY=metapm-api-key:latest
```

### Why This Requires PL

cc-deploy@ service account can authenticate to gcloud but lacks:
- `run.services.update` permission (potentially — would need testing)
- Visibility into recent deployment history that might explain why secrets were not bound
- Context on whether secrets were intentionally unbind during BUG-076/BUG-095 fixes

Safest path: PL executes fix via Cloud Console or gcloud CLI with full project owner permissions.

### Prevention

For future deployments, ensure `gcloud run deploy` or CI/CD pipelines include:
```bash
--update-secrets=GOOGLE_CLIENT_ID=metapm-google-oauth-client-id:latest,GOOGLE_CLIENT_SECRET=metapm-google-oauth-client-secret:latest,MCP_API_KEY=metapm-api-key:latest
```

Or via Cloud Run YAML deployment manifest:
```yaml
spec:
  template:
    spec:
      containers:
      - env:
        - name: GOOGLE_CLIENT_ID
          valueFrom:
            secretKeyRef:
              name: metapm-google-oauth-client-id
              key: latest
        - name: GOOGLE_CLIENT_SECRET
          valueFrom:
            secretKeyRef:
              name: metapm-google-oauth-client-secret
              key: latest
        - name: MCP_API_KEY
          valueFrom:
            secretKeyRef:
              name: metapm-api-key
              key: latest
```

---

## Parking Lot

### Questions for PL

1. **Deployment history**: What command/process created revision 00425-ljl on 2026-04-22? Was it manual `gcloud run deploy` or CI/CD?
2. **BUG-076/BUG-095 scope**: Did those fixes involve removing and re-adding secrets? Secrets were created 2026-04-21 22:49, suggesting they might have been deleted and recreated.
3. **DIAG-003 scope**: What exactly did DIAG-003 verify? Secret existence only, or revision-level binding?
4. **SF UAT 9B3C6614 affected**: Is SF running a similar revision without OAuth secrets? Should SF receive same fix?

### Additional Findings

- **MCP_API_KEY plaintext exposure**: Revision 00428-6wv has `MCP_API_KEY` hardcoded as plaintext value `gvhGURyMZRa/jHZEKjcv2rljz2uuMnO9ihraVsZNi6I=`. This is a security risk (visible in Cloud Run revision YAML, audit logs, etc.). Should be bound from Secret Manager.
  
- **Multiple revisions without secrets**: At minimum, revisions 00425-ljl and 00428-6wv lack OAuth bindings. Latest template (generation 454) shows MCP_API_KEY from secret but still no OAuth. Suggests multiple recent deploys without proper secret configuration.

### Observations

- Service account `cc-deploy@` has correct Secret Manager IAM but lacks Cloud Logging read permissions (PERMISSION_DENIED on logs). This is expected per DIAG-003 precedent but limits diagnostic visibility.

- All three OAuth secrets (MetaPM, SF, EM) created within 5-second window on 2026-04-21 22:49:37-42. This suggests a bulk secret creation operation, possibly as part of BUG-076/BUG-095 resolution attempt.

---

## Diagnostic Metadata

- **PTH:** DIAG-005
- **Sprint ID:** DIAG-005-OAUTH-OUTAGE-001  
- **Requirement:** TSK-032 (metapm.rentyourcio.com/dashboard#TSK-032)
- **Diagnostic duration:** ~90 minutes
- **Commands executed:** 12 (7 read-only diagnostic steps + 5 setup/verification)
- **Service account:** cc-deploy@super-flashcards-475210.iam.gserviceaccount.com
- **GCP project:** super-flashcards-475210
- **Mutations:** 0 (read-only diagnostic per constraint)
- **Branch:** diag/DIAG-005
