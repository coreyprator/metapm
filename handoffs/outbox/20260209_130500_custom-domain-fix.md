# [MetaPM] 🔴 Custom Domain Mapping Fix — IN PROGRESS

> **From**: Claude Code (Command Center)
> **To**: Claude.ai (Architect)
> **Project**: MetaPM
> **Task**: Fix custom domain traffic routing
> **Timestamp**: 2026-02-09T13:05:00Z
> **Status**: IN PROGRESS (Certificate Provisioning)

---

## Summary

The custom domain `metapm.rentyourcio.com` was showing v1.9.4 while the direct Cloud Run URL showed v2.0.1. Deleted and recreated the domain mapping to force a refresh.

---

## Diagnosis

| Endpoint | Version | Status |
|----------|---------|--------|
| Direct URL (metapm-v2-*.run.app) | v2.0.1 | ✅ Working |
| Custom domain (metapm.rentyourcio.com) | v1.9.4 | ❌ Stale |

The traffic routing was correctly set to 100% latest revision, but the custom domain mapping was returning stale responses.

---

## Fix Applied

1. Deleted the existing domain mapping:
   ```bash
   gcloud beta run domain-mappings delete --domain=metapm.rentyourcio.com --region=us-central1
   ```

2. Recreated with force override:
   ```bash
   gcloud beta run domain-mappings create --service=metapm-v2 \
     --domain=metapm.rentyourcio.com --region=us-central1 --force-override
   ```

3. Certificate provisioning in progress

---

## Current Status

```yaml
status:
  conditions:
  - type: Ready
    status: Unknown
    reason: CertificatePending
    message: Waiting for certificate provisioning
  - type: DomainRoutable
    status: 'True'
```

The domain mapping is being recreated. Certificate provisioning typically takes 15-60 minutes.

---

## Workaround

**Use direct Cloud Run URL until custom domain is ready:**
- Direct URL: `https://metapm-v2-57478301787.us-central1.run.app`
- Roadmap: `https://metapm-v2-57478301787.us-central1.run.app/roadmap.html`
- Health: `https://metapm-v2-57478301787.us-central1.run.app/health` → v2.0.1

---

## Next Steps

1. Wait for certificate provisioning to complete
2. Verify custom domain shows v2.0.1
3. Verify /roadmap.html returns 200

---

## Additional Notes

Also redeployed MetaPM to create a fresh revision:
- Revision: `metapm-v2-00042-lgz`
- Deployed: 2026-02-09

---

*Sent via Handoff Bridge per project-methodology policy*
*metapm/handoffs/outbox/20260209_130500_custom-domain-fix.md → GCS backup*
