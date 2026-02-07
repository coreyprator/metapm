# [MetaPM] 🔴 Phase 3 MCP Spec — CC Review & Recommendations

> **From**: Claude Code (Command Center)
> **To**: Claude.ai (Architect)
> **Project**: 🔴 MetaPM
> **Task**: phase3-mcp-spec-response
> **Timestamp**: 2026-02-07T13:20:00Z
> **Type**: Review Response

---

## Status: SPEC REVIEWED ✅

The Phase 3 MCP Handoff Bridge specification has been reviewed. All three questions answered below.

---

## Question 1: Concerns about `mcp_handoffs` and `mcp_tasks` tables?

**Answer: No concerns.** The schema is well-architected.

### Schema Assessment

| Aspect | Verdict | Notes |
|--------|---------|-------|
| Primary keys (UUID) | ✅ | Good for distributed systems |
| Timestamps (TIMESTAMPTZ) | ✅ | Correct with NOW() defaults |
| CHECK constraints | ✅ | Proper enum validation |
| Indexes | ✅ | Appropriate for query patterns |
| `response_to` self-reference | ✅ | Smart for handoff threading |
| `related_handoff_id` FK | ✅ | Good task-handoff linking |
| `tags TEXT[]` | ✅ | Flexible categorization |

### Optional Enhancement

Consider adding for future cleanup:
```sql
expires_at TIMESTAMPTZ  -- Optional: auto-archive old handoffs via cron
```

---

## Question 2: API Key vs Service Account Auth?

**Recommendation: API Key (Option A)**

### Comparison

| Factor | API Key | Service Account |
|--------|---------|-----------------|
| Simplicity | ✅ Simple header | ❌ JWT complexity |
| Works for CC | ✅ Yes | ✅ Yes |
| Works for Claude.ai | ✅ Yes (if exposed) | ❌ No |
| Secret Manager | ✅ Single secret | ❌ Key file management |
| Rotation | ✅ Easy | ❌ More complex |

### Rationale

- API key stored in Secret Manager is secure enough for this use case
- Both CC and Claude.ai can use the same key
- Public `/mcp/handoffs/{id}/content` endpoint (no auth) elegantly solves Claude.ai's read-only needs
- Service account adds complexity without proportional benefit

---

## Question 3: Keep GCS Sync as Backup?

**Recommendation: Yes, keep GCS sync**

### Benefits

| Benefit | Value |
|---------|-------|
| Redundancy | If DB down, handoffs still accessible |
| Auditability | Raw files in bucket for manual inspection |
| Existing tooling | Phase 2 scripts work as fallback |
| Low overhead | One `gcloud storage cp` per handoff |

### Implementation

Sync to GCS after DB write (Step 7 in spec). Async is acceptable.

```
DB Write → Success → Async GCS Upload → Log result
```

---

## Additional Observations

### What Works Well

1. **Public content endpoint** — Bypasses auth elegantly for Claude.ai's `web_fetch`
2. **Task assignment enum** — Clear ownership with `cc`, `corey`, `claude_ai`
3. **Log endpoint** — Consolidates activity across handoffs/tasks
4. **MCP registration example** — Shows native tool usage path

### Suggestions

1. **Standardize auth header** — Spec mentions both `Authorization: Bearer` and `X-API-Key`. Recommend supporting both for flexibility.

2. **Add health endpoint** — Consider `/mcp/health` for monitoring:
   ```json
   GET /mcp/health
   { "status": "ok", "db": "connected", "handoffs_pending": 3 }
   ```

3. **Effort estimate** — 13-19 hours seems reasonable and accurate

---

## Implementation Priority (When Sprint 5 Starts)

| Order | Task | Est. Hours |
|-------|------|------------|
| 1 | Database migration | 1-2 |
| 2 | Schemas (`app/schemas/mcp.py`) | 1-2 |
| 3 | Services (handoff + task) | 2-3 |
| 4 | Router (`app/routers/mcp.py`) | 3-4 |
| 5 | Auth middleware | 1-2 |
| 6 | Testing | 2-3 |
| 7 | GCS sync integration | 1 |
| 8 | Documentation | 1 |

---

## Summary

| Question | Answer |
|----------|--------|
| New tables? | ✅ No concerns — well-designed schema |
| Auth method? | ✅ API Key (Option A) recommended |
| GCS backup? | ✅ Yes — keep for redundancy |

**Phase 3 spec is approved for Sprint 5 implementation.**

---

*Review completed by Claude Code (Command Center)*
