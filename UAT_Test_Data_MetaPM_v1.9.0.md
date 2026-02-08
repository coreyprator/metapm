# UAT Results — Test Data for New Tracking Feature

## API Call to Submit Results

Once v1.9.1 is deployed with UAT tracking, submit this:

### Endpoint
```
POST https://metapm.rentyourcio.com/mcp/handoffs/{handoff_id}/uat
```

### Find the handoff_id first
```
GET https://metapm.rentyourcio.com/mcp/handoffs/dashboard?search=dashboard-v190
```

### Request Body
```json
{
    "status": "failed",
    "total_tests": 14,
    "passed": 13,
    "failed": 1,
    "notes_count": 1,
    "checklist_path": "templates/MetaPM_v1.9.0_Dashboard_UAT.html",
    "results_text": "[MetaPM] 🔴 v1.9.0 Dashboard UAT Results\n==================================================\nDate: 2/7/2026, 11:01:37 PM\nVersion: 1.9.0\nURL: https://metapm.rentyourcio.com/static/handoffs.html\nSummary: 13 passed, 1 failed, 1 with notes\n==================================================\nKNOWN BUGS:\n- BUG-001: All handoffs show \"pending\" instead of \"done\"\n- BUG-002: No clickable URL to view handoff content\n- BUG-003: Can't inspect/verify history backup\n\n1. Dashboard Loads\n----------------------------------------\n  ✓ Dashboard page loads without error\n  ✓ Handoffs table populated\n\n2. Status Display\n----------------------------------------\n  ✓ Imported handoffs show correct status\n  ✗ Status filter works\n      📝 \"Done\" doesn't exist as a status. Should be \"Processed\".  Produces: Error loading handoffs\n\n3. View Handoff Content\n----------------------------------------\n  ✓ Click row → Detail panel shows\n  ✓ Detail panel shows full content\n  ✓ GCS URL is clickable\n\n4. Sorting & Filtering\n----------------------------------------\n  ✓ Default sort is Date Descending\n  ✓ Can sort by clicking column headers\n  ✓ Filter by Project works\n  ✓ Search by content works\n\n5. History Verification\n----------------------------------------\n  ✓ Can verify a handoff exists in GCS\n  ✓ All 6 projects have handoffs\n  ✓ Today's handoffs are present\n\n6. Stats & Analytics\n----------------------------------------\n  ○ Stats summary visible\n\nOVERALL: ✗ NEEDS FIXES"
}
```

---

## Test Script (Python)

```python
#!/usr/bin/env python3
"""Test UAT tracking feature with real data."""

import requests
import os

API_BASE = "https://metapm.rentyourcio.com"
API_KEY = os.environ.get("METAPM_API_KEY")

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Step 1: Find the dashboard-v190 handoff
response = requests.get(
    f"{API_BASE}/mcp/handoffs/dashboard",
    params={"search": "dashboard-v190"},
    headers=headers
)
handoffs = response.json().get("items", [])

if not handoffs:
    print("❌ Could not find dashboard-v190 handoff")
    exit(1)

handoff_id = handoffs[0]["id"]
print(f"✅ Found handoff: {handoff_id}")

# Step 2: Submit UAT results
uat_data = {
    "status": "failed",
    "total_tests": 14,
    "passed": 13,
    "failed": 1,
    "notes_count": 1,
    "checklist_path": "templates/MetaPM_v1.9.0_Dashboard_UAT.html",
    "results_text": """[MetaPM] 🔴 v1.9.0 Dashboard UAT Results
==================================================
Date: 2/7/2026, 11:01:37 PM
Version: 1.9.0
Summary: 13 passed, 1 failed, 1 with notes
==================================================

BUG FOUND:
- Status filter uses "Done" but data uses "Processed" - causes error

OVERALL: ✗ NEEDS FIXES (1 bug)"""
}

response = requests.post(
    f"{API_BASE}/mcp/handoffs/{handoff_id}/uat",
    json=uat_data,
    headers=headers
)

if response.status_code == 200:
    result = response.json()
    print(f"✅ UAT results submitted: {result}")
else:
    print(f"❌ Failed: {response.status_code} - {response.text}")

# Step 3: Verify UAT was recorded
response = requests.get(
    f"{API_BASE}/mcp/handoffs/{handoff_id}/uat",
    headers=headers
)

if response.status_code == 200:
    history = response.json()
    print(f"✅ UAT history: {history}")
else:
    print(f"❌ Could not retrieve UAT history")
```

---

## Manual Test via curl

```bash
# 1. Find handoff ID (replace with actual search)
curl -H "X-API-Key: $METAPM_API_KEY" \
  "https://metapm.rentyourcio.com/mcp/handoffs/dashboard?search=dashboard-v190"

# 2. Submit UAT (replace HANDOFF_ID)
curl -X POST \
  -H "X-API-Key: $METAPM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"status":"failed","total_tests":14,"passed":13,"failed":1,"notes_count":1,"results_text":"13 passed, 1 failed. Bug: Status filter mismatch."}' \
  "https://metapm.rentyourcio.com/mcp/handoffs/HANDOFF_ID/uat"

# 3. Get UAT history
curl -H "X-API-Key: $METAPM_API_KEY" \
  "https://metapm.rentyourcio.com/mcp/handoffs/HANDOFF_ID/uat"
```

---

## Expected Dashboard View After Submission

```
│ Project   │ Task           │ Status      │ UAT     │ Date        │
├───────────┼────────────────┼─────────────┼─────────┼─────────────┤
│ 🔴 MetaPM │ dashboard-v190 │ needs_fixes │ ✗ 13/14 │ 2/8 6:00am  │
```

---

## UAT Results to Submit Later (for v1.9.1)

After v1.9.1 fixes the status filter bug, run UAT again and submit:

```json
{
    "status": "passed",
    "total_tests": 14,
    "passed": 14,
    "failed": 0,
    "notes_count": 0,
    "results_text": "[MetaPM] 🔴 v1.9.1 Dashboard UAT Results\n...\nOVERALL: ✓ APPROVED"
}
```

Dashboard should then show:
```
│ 🔴 MetaPM │ dashboard-v191 │ done │ ✓ 14/14 │
```
