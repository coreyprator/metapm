# [MetaPM] 🔴 Phase 3 MCP API — Comprehensive Testing Request

> **From**: Claude.ai (Architect)
> **To**: Claude Code (Command Center)
> **Project**: 🔴 MetaPM
> **Task**: phase3-api-comprehensive-testing
> **Timestamp**: 2026-02-07T19:45:00Z
> **Priority**: HIGH

---

## Context

Phase 3 MCP API is deployed (v1.7.0). Initial testing shows:
- ✅ Health endpoint works
- ✅ List handoffs works (1 existing handoff found)
- ❓ Create/Update/Delete operations need verification
- ❓ Task CRUD needs verification
- ❓ Public content endpoint needs verification (CRITICAL for Claude.ai)

---

## API Key

```
zCU2rHIcNPVLQ42RBQnafcwKL44jjApQImhH_rhZYJc
```

---

## Test Suite

Run ALL tests and report results.

### 1. Health & Auth Tests

```bash
# 1.1 Health (no auth)
curl https://metapm.rentyourcio.com/mcp/health
# Expected: {"status":"healthy","service":"mcp","version":"1.7.0","api_key_configured":true}

# 1.2 Auth rejection (no key)
curl https://metapm.rentyourcio.com/mcp/handoffs
# Expected: 401 {"detail":"API key required"}

# 1.3 Auth rejection (bad key)
curl -H "X-API-Key: bad-key" https://metapm.rentyourcio.com/mcp/handoffs
# Expected: 403 {"detail":"Invalid API key"}

# 1.4 Auth success (good key)
curl -H "X-API-Key: zCU2rHIcNPVLQ42RBQnafcwKL44jjApQImhH_rhZYJc" https://metapm.rentyourcio.com/mcp/handoffs
# Expected: 200 with handoffs list
```

### 2. Handoff CRUD Tests

```bash
# 2.1 Create handoff (cc_to_ai direction)
curl -X POST https://metapm.rentyourcio.com/mcp/handoffs \
  -H "X-API-Key: zCU2rHIcNPVLQ42RBQnafcwKL44jjApQImhH_rhZYJc" \
  -H "Content-Type: application/json" \
  -d '{
    "project": "MetaPM",
    "task": "cc-comprehensive-test",
    "direction": "cc_to_ai",
    "content": "# CC Comprehensive Test\n\nThis handoff tests the full API.\n\n## Sections\n- Auth\n- CRUD\n- Public access",
    "metadata": {"test_run": "comprehensive", "timestamp": "2026-02-07"}
  }'
# Expected: 201 with id, public_url
# SAVE THE ID for subsequent tests

# 2.2 Get handoff by ID (authenticated)
curl -H "X-API-Key: zCU2rHIcNPVLQ42RBQnafcwKL44jjApQImhH_rhZYJc" \
  https://metapm.rentyourcio.com/mcp/handoffs/{ID}
# Expected: Full handoff object with content

# 2.3 PUBLIC content endpoint (NO auth) - CRITICAL TEST
curl https://metapm.rentyourcio.com/mcp/handoffs/{ID}/content
# Expected: Raw markdown content, NO auth required
# This is what Claude.ai will use to read handoffs!

# 2.4 Update handoff status
curl -X PATCH https://metapm.rentyourcio.com/mcp/handoffs/{ID} \
  -H "X-API-Key: zCU2rHIcNPVLQ42RBQnafcwKL44jjApQImhH_rhZYJc" \
  -H "Content-Type: application/json" \
  -d '{"status": "read"}'
# Expected: 200 with updated status

# 2.5 List with filters
curl -H "X-API-Key: zCU2rHIcNPVLQ42RBQnafcwKL44jjApQImhH_rhZYJc" \
  "https://metapm.rentyourcio.com/mcp/handoffs?project=MetaPM&status=pending"
# Expected: Filtered list
```

### 3. Task CRUD Tests

```bash
# 3.1 Create task
curl -X POST https://metapm.rentyourcio.com/mcp/tasks \
  -H "X-API-Key: zCU2rHIcNPVLQ42RBQnafcwKL44jjApQImhH_rhZYJc" \
  -H "Content-Type: application/json" \
  -d '{
    "project": "MetaPM",
    "title": "Test Phase 3 API comprehensively",
    "description": "Run full test suite and report results",
    "priority": "high",
    "assigned_to": "cc",
    "tags": ["testing", "phase3", "api"]
  }'
# Expected: 201 with task id
# SAVE THE ID

# 3.2 Get task by ID
curl -H "X-API-Key: zCU2rHIcNPVLQ42RBQnafcwKL44jjApQImhH_rhZYJc" \
  https://metapm.rentyourcio.com/mcp/tasks/{TASK_ID}
# Expected: Full task object

# 3.3 List tasks with filters
curl -H "X-API-Key: zCU2rHIcNPVLQ42RBQnafcwKL44jjApQImhH_rhZYJc" \
  "https://metapm.rentyourcio.com/mcp/tasks?project=MetaPM&assigned_to=cc"
# Expected: Filtered list

# 3.4 Update task
curl -X PATCH https://metapm.rentyourcio.com/mcp/tasks/{TASK_ID} \
  -H "X-API-Key: zCU2rHIcNPVLQ42RBQnafcwKL44jjApQImhH_rhZYJc" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress", "notes": "Running comprehensive tests"}'
# Expected: 200 with updated task

# 3.5 Complete task
curl -X PATCH https://metapm.rentyourcio.com/mcp/tasks/{TASK_ID} \
  -H "X-API-Key: zCU2rHIcNPVLQ42RBQnafcwKL44jjApQImhH_rhZYJc" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
# Expected: 200 with status=done, completed_at set

# 3.6 Delete task (cleanup)
curl -X DELETE https://metapm.rentyourcio.com/mcp/tasks/{TASK_ID} \
  -H "X-API-Key: zCU2rHIcNPVLQ42RBQnafcwKL44jjApQImhH_rhZYJc"
# Expected: 204 No Content
```

### 4. Activity Log Test

```bash
# 4.1 Get activity log
curl -H "X-API-Key: zCU2rHIcNPVLQ42RBQnafcwKL44jjApQImhH_rhZYJc" \
  https://metapm.rentyourcio.com/mcp/log
# Expected: List of recent handoff and task activities

# 4.2 Filtered log
curl -H "X-API-Key: zCU2rHIcNPVLQ42RBQnafcwKL44jjApQImhH_rhZYJc" \
  "https://metapm.rentyourcio.com/mcp/log?project=MetaPM&limit=5"
# Expected: Filtered list
```

### 5. Edge Case Tests

```bash
# 5.1 Invalid handoff ID
curl -H "X-API-Key: zCU2rHIcNPVLQ42RBQnafcwKL44jjApQImhH_rhZYJc" \
  https://metapm.rentyourcio.com/mcp/handoffs/00000000-0000-0000-0000-000000000000
# Expected: 404 Not Found

# 5.2 Invalid direction value
curl -X POST https://metapm.rentyourcio.com/mcp/handoffs \
  -H "X-API-Key: zCU2rHIcNPVLQ42RBQnafcwKL44jjApQImhH_rhZYJc" \
  -H "Content-Type: application/json" \
  -d '{"project": "Test", "task": "test", "direction": "invalid", "content": "test"}'
# Expected: 422 Validation error

# 5.3 Missing required field
curl -X POST https://metapm.rentyourcio.com/mcp/handoffs \
  -H "X-API-Key: zCU2rHIcNPVLQ42RBQnafcwKL44jjApQImhH_rhZYJc" \
  -H "Content-Type: application/json" \
  -d '{"project": "Test"}'
# Expected: 422 Validation error
```

---

## Report Format

Create a handoff with results in this format:

```markdown
# Phase 3 MCP API Test Results

## Summary
- Total Tests: X
- Passed: X
- Failed: X

## Results by Section

### 1. Health & Auth
| Test | Expected | Actual | Pass/Fail |
|------|----------|--------|-----------|
| 1.1 Health | 200 + version | ... | ✅/❌ |
...

### 2. Handoff CRUD
...

### 3. Task CRUD
...

### 4. Activity Log
...

### 5. Edge Cases
...

## Critical Findings
- Public content endpoint: PASS/FAIL
- Any issues discovered

## Handoff IDs Created
- Test handoff: {ID}
- Public URL: {URL}
```

---

## Definition of Done

- [ ] All 20+ tests executed
- [ ] Results documented in table format
- [ ] Public content endpoint verified (CRITICAL)
- [ ] Any failures explained with error messages
- [ ] Handoff sent via handoff bridge

---

*Testing request from Claude.ai (Architect)*
*Machine-to-machine verification of Phase 3 MCP API*
