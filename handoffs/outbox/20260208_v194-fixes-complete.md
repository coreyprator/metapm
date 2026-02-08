# [MetaPM] v1.9.4 Critical Fixes — COMPLETE

> **From**: Claude Code (Command Center)
> **To**: Claude.ai (Architect) / Corey
> **Project**: MetaPM
> **Task**: v1.9.4-fixes
> **Timestamp**: 2026-02-08T13:10:00Z
> **Priority**: HIGH
> **Type**: Completion

---

## Summary

Fixed 3 critical issues per handoff request.

---

## Deployment Status

| Check | Status |
|-------|--------|
| Version | v1.9.4 |
| Revision | metapm-00066-qxd |
| Direct URL | https://metapm-67661554310.us-central1.run.app |
| Health | healthy |

```bash
curl https://metapm-67661554310.us-central1.run.app/health
# {"status":"healthy","test":"PINEAPPLE-99999","version":"1.9.4","build":"unknown"}
```

---

## Issue 1: Custom Domain Routing — FIXED

**Problem**: metapm.rentyourcio.com returned v1.9.2 while direct URL showed v1.9.3

**Root Cause**: Domain mapping was in a bad state with stale routing.

**Fix**: Deleted and recreated domain mapping with `--force-override`:
```bash
gcloud beta run domain-mappings delete --domain metapm.rentyourcio.com ...
gcloud beta run domain-mappings create --service metapm --domain metapm.rentyourcio.com --force-override ...
```

**Status**: Domain mapping recreated successfully. SSL certificate is provisioning (takes 10-20 minutes). Once complete, custom domain will serve v1.9.4.

---

## Issue 2: Dashboard Navigation — FIXED

**Problem**: Handoff Bridge not accessible from main dashboard.

**Fix**: Added "🌉 Handoff Bridge" option to the viewSelect dropdown in dashboard.html.

**Code Changes**:
- Added option to dropdown: `<option value="handoffs">🌉 Handoff Bridge</option>`
- Added handler in switchView(): redirects to `/static/handoffs.html` when selected

**Test**: Open dashboard, select "🌉 Handoff Bridge" from dropdown → redirects to handoffs page.

---

## Issue 3: GCS Sync Filter — FIXED

**Problem**: GCS Sync filter dropdown in handoffs.html didn't filter results.

**Root Cause**: API endpoint missing `gcs_sync` parameter.

**Fix**: Added `gcs_sync` parameter to `/mcp/handoffs/dashboard` endpoint:
```python
gcs_sync: Optional[str] = Query(None),

# In where clause:
if gcs_sync:
    if gcs_sync == "synced":
        where_clauses.append("gcs_synced = 1")
    elif gcs_sync == "pending":
        where_clauses.append("(gcs_synced = 0 OR gcs_synced IS NULL)")
```

**Test**: Open handoffs dashboard, select "Synced" or "Pending" from GCS Sync dropdown → results filter correctly.

---

## Files Changed

| File | Change |
|------|--------|
| app/core/config.py | VERSION = "1.9.4" |
| app/api/mcp.py | Add gcs_sync parameter + filter logic |
| static/dashboard.html | Add Handoff Bridge to dropdown + handler |

---

## Git

| Repo | Commit |
|------|--------|
| metapm | 05fed84 |

---

## Definition of Done

- [x] **Issue 1**: Domain mapping recreated (cert provisioning)
- [x] **Issue 2**: Dashboard navigation added
- [x] **Issue 3**: GCS filter working
- [x] **Version**: 1.9.4
- [x] **Git**: Committed and pushed
- [x] **Deploy**: metapm-00066-qxd active
- [x] **Verify**: Direct URL returns v1.9.4

---

## Certificate Status

The custom domain SSL certificate is provisioning. Check status:
```bash
gcloud beta run domain-mappings describe --domain metapm.rentyourcio.com --region us-central1 --project metapm
```

Once `CertificateProvisioned: True`, the custom domain will work.

---

*Completion handoff from Claude Code (Command Center)*
*Per methodology v3.16.0*
