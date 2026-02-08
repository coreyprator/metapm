# [MetaPM] 🔴 v1.9.1 — Dashboard Bug Fixes

> **From**: Claude.ai (Architect)
> **To**: Claude Code (Command Center)
> **Project**: 🔴 MetaPM
> **Task**: dashboard-bugfixes
> **Timestamp**: 2026-02-08T05:15:00Z
> **Priority**: HIGH
> **Type**: Bug Fixes

---

## Bugs Found During UAT

| Bug ID | Issue | Severity |
|--------|-------|----------|
| BUG-001 | All handoffs show "pending" — should be "done" | HIGH |
| BUG-002 | No clickable URL to view handoff content | HIGH |
| BUG-003 | Can't inspect/verify history backup | HIGH |

---

## BUG-001: Status Shows "pending" Instead of "done"

### Problem

All 33 imported handoffs from GCS show status = "pending".

These are COMPLETED handoffs that were imported from the GCS outbox. They should show "done".

### Root Cause

The import script sets `status = "pending"` by default instead of `status = "done"`.

### Fix

In `scripts/migrations/import_gcs_handoffs.py`, change:

```python
# WRONG
"status": "pending",

# CORRECT
"status": "done",  # Imported handoffs are already completed
```

### Also Fix Existing Data

Run SQL to fix already-imported records:

```sql
UPDATE mcp_handoffs 
SET status = 'done' 
WHERE gcs_synced = 1 AND status = 'pending';
```

---

## BUG-002: No Clickable URL to View Handoff Content

### Problem

User cannot click to view the actual handoff content. No links to:
- GCS URL (gs://corey-handoff-bridge/...)
- Public HTTPS URL (https://storage.googleapis.com/...)
- Detail view with content

### Expected Behavior

1. **In table**: GCS column should be a clickable link
2. **On click row**: Detail panel opens showing full content
3. **In detail panel**: "View in GCS" link that opens the public URL

### Fix

#### 1. Make GCS column clickable in `static/handoffs.html`:

```javascript
// In table row rendering
const gcsCell = document.createElement('td');
if (handoff.gcs_url) {
    const publicUrl = handoff.gcs_url.replace('gs://corey-handoff-bridge/', 
        'https://storage.googleapis.com/corey-handoff-bridge/');
    gcsCell.innerHTML = `<a href="${publicUrl}" target="_blank" title="${handoff.gcs_url}">📄 View</a>`;
} else {
    gcsCell.textContent = '—';
}
```

#### 2. Add detail panel with content preview:

```javascript
function showDetailPanel(handoff) {
    const panel = document.getElementById('detail-panel');
    panel.innerHTML = `
        <div class="detail-header">
            <h3>${handoff.title || handoff.task}</h3>
            <button onclick="closeDetailPanel()">✕</button>
        </div>
        <div class="detail-meta">
            <p><strong>Project:</strong> ${handoff.project}</p>
            <p><strong>Direction:</strong> ${handoff.direction}</p>
            <p><strong>Status:</strong> ${handoff.status}</p>
            <p><strong>Created:</strong> ${new Date(handoff.created_at).toLocaleString()}</p>
        </div>
        <div class="detail-links">
            ${handoff.gcs_url ? `<a href="${handoff.gcs_url.replace('gs://corey-handoff-bridge/', 'https://storage.googleapis.com/corey-handoff-bridge/')}" target="_blank" class="btn">📄 View in GCS</a>` : ''}
            ${handoff.git_commit ? `<span>Git: ${handoff.git_commit}</span>` : ''}
        </div>
        <div class="detail-content">
            <h4>Content Preview</h4>
            <pre>${escapeHtml(handoff.content || handoff.summary || 'No content available')}</pre>
        </div>
    `;
    panel.classList.add('visible');
}
```

#### 3. Add CSS for detail panel:

```css
#detail-panel {
    position: fixed;
    right: -500px;
    top: 0;
    width: 500px;
    height: 100vh;
    background: #252538;
    border-left: 2px solid #ef4444;
    padding: 20px;
    overflow-y: auto;
    transition: right 0.3s ease;
    z-index: 1000;
}

#detail-panel.visible {
    right: 0;
}

.detail-content pre {
    background: #1e1e32;
    padding: 15px;
    border-radius: 8px;
    overflow-x: auto;
    white-space: pre-wrap;
    font-size: 0.85rem;
    max-height: 400px;
    overflow-y: auto;
}
```

---

## BUG-003: Can't Verify History Backup

### Problem

No way to:
- See which handoffs are synced to GCS
- Verify content matches
- Check for missing backups

### Fix

#### 1. Add GCS Sync Status Column

Show sync status in table:

```javascript
const syncCell = document.createElement('td');
if (handoff.gcs_synced) {
    syncCell.innerHTML = '<span class="sync-ok" title="Synced to GCS">✓</span>';
} else {
    syncCell.innerHTML = '<span class="sync-pending" title="Pending sync">⏳</span>';
}
```

#### 2. Add "Verify" Button in Detail Panel

```javascript
<button onclick="verifyHandoff('${handoff.id}')" class="btn btn-verify">
    🔍 Verify GCS Backup
</button>
```

```javascript
async function verifyHandoff(id) {
    const response = await fetch(`/mcp/handoffs/${id}/verify`, { method: 'POST' });
    const result = await response.json();
    
    if (result.gcs_verified) {
        alert('✅ GCS backup verified!\n\nURL: ' + result.gcs_url);
    } else {
        alert('❌ GCS backup NOT found!\n\nExpected: ' + result.expected_path);
    }
}
```

#### 3. Add Verify Endpoint (if not exists)

```python
@router.post("/mcp/handoffs/{id}/verify")
async def verify_handoff(id: str):
    handoff = await get_handoff(id)
    
    # Check GCS
    gcs_exists = await verify_gcs_exists(handoff.gcs_url)
    
    return {
        "id": id,
        "gcs_verified": gcs_exists,
        "gcs_url": handoff.gcs_url,
        "expected_path": f"gs://corey-handoff-bridge/{handoff.project}/outbox/..."
    }
```

---

## UI Enhancements (While You're In There)

### Add Row Click Handler

```javascript
tableBody.addEventListener('click', (e) => {
    const row = e.target.closest('tr');
    if (row && row.dataset.id) {
        const handoff = handoffs.find(h => h.id === row.dataset.id);
        if (handoff) showDetailPanel(handoff);
    }
});
```

### Add Row Hover Styling

```css
tbody tr {
    cursor: pointer;
    transition: background 0.15s;
}

tbody tr:hover {
    background: #2d2d44;
}
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `static/handoffs.html` | Add detail panel, row click, GCS links |
| `static/css/handoffs.css` (or inline) | Detail panel styles |
| `app/api/mcp.py` | Add /verify endpoint if missing |
| `scripts/migrations/import_gcs_handoffs.py` | Fix status = "done" |

---

## SQL Fix for Existing Data

Run after deployment:

```sql
-- Fix imported handoffs showing wrong status
UPDATE mcp_handoffs 
SET status = 'done' 
WHERE gcs_synced = 1 
  AND status = 'pending';

-- Verify fix
SELECT status, COUNT(*) 
FROM mcp_handoffs 
GROUP BY status;
```

---

## Testing Checklist

| Test | Expected |
|------|----------|
| Status shows correctly | Imported = "done", new = "pending" |
| Click row | Detail panel slides open |
| GCS link clickable | Opens in new tab, shows markdown |
| Verify button works | Confirms GCS backup exists |
| Close detail panel | Panel slides away |
| Sync status visible | ✓ for synced, ⏳ for pending |

---

## Version

Bump to **v1.9.1** after fixes.

---

## Definition of Done

- [ ] BUG-001 fixed — status shows "done" for imported handoffs
- [ ] BUG-002 fixed — GCS URLs are clickable
- [ ] BUG-003 fixed — can verify backup via UI
- [ ] SQL fix run for existing data
- [ ] Detail panel working
- [ ] All tests pass
- [ ] Version bumped to 1.9.1
- [ ] Git committed
- [ ] **Deployed to Cloud Run**
- [ ] **UAT passed**
- [ ] Handoff sent with URL

---

*Bug fixes from UAT — Claude.ai (Architect)*
