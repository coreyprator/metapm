# [MetaPM] 🔴 v1.9.3 — UAT Checklist Direct Submission

> **From**: Claude.ai (Architect)
> **To**: Claude Code (Command Center)
> **Project**: 🔴 MetaPM
> **Task**: uat-checklist-submit
> **Timestamp**: 2026-02-08T06:45:00Z
> **Priority**: MEDIUM
> **Type**: Feature Enhancement

---

## Problem Statement

Current UAT workflow has too many steps:
1. Corey runs UAT checklist (HTML)
2. Clicks "Copy Results" 
3. Pastes text to Claude.ai
4. Claude.ai or CC submits to MetaPM API
5. Gets handoff URL to share

**Proposed**: Checklist submits directly to MetaPM, returns handoff URL.

---

## Solution: "Submit to MetaPM" Button

Add a button to UAT checklists that:
1. Collects all test results from the page
2. POSTs directly to MetaPM API
3. Creates/updates handoff record with UAT results
4. Returns a clickable handoff URL
5. User pastes URL to Claude.ai

---

## New Workflow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Run UAT Tests  │────►│ Submit to MetaPM│────►│ Paste URL to    │
│  (HTML checklist)│     │  (one click)    │     │ Claude.ai       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │ MetaPM creates: │
                        │ • UAT record    │
                        │ • Handoff link  │
                        │ • GCS sync      │
                        └─────────────────┘
```

---

## UAT Checklist Changes

### Add "Submit to MetaPM" Button

```html
<div class="submit-section">
    <button class="submit-btn" onclick="submitToMetaPM()">
        📤 Submit to MetaPM
    </button>
    <div id="submit-result" class="hidden">
        <p>✅ Submitted! Handoff URL:</p>
        <input type="text" id="handoff-url" readonly />
        <button onclick="copyHandoffUrl()">📋 Copy URL</button>
    </div>
</div>
```

### JavaScript Function

```javascript
async function submitToMetaPM() {
    const btn = document.querySelector('.submit-btn');
    btn.disabled = true;
    btn.textContent = '⏳ Submitting...';
    
    // Collect test data from page
    const passed = document.querySelectorAll('.test-item.passed').length;
    const failed = document.querySelectorAll('.test-item.failed').length;
    const total = passed + failed;
    const notesCount = Array.from(document.querySelectorAll('.notes-input'))
        .filter(input => input.value.trim().length > 0).length;
    
    // Get project info from page metadata
    const projectMatch = document.title.match(/\[(.*?)\]/);
    const project = projectMatch ? projectMatch[1] : 'Unknown';
    
    const versionMatch = document.title.match(/v(\d+\.\d+\.\d+)/);
    const version = versionMatch ? versionMatch[0] : 'Unknown';
    
    // Build results text (same as copy function)
    const resultsText = buildResultsText();
    
    // Determine status
    const overallResult = document.getElementById('overall-result');
    const status = overallResult.classList.contains('pass') ? 'passed' : 
                   overallResult.classList.contains('fail') ? 'failed' : 'pending';
    
    // Get handoff ID if known (could be in URL param or page data)
    const urlParams = new URLSearchParams(window.location.search);
    const handoffId = urlParams.get('handoff_id') || null;
    
    try {
        const response = await fetch('https://metapm.rentyourcio.com/mcp/uat/submit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                // UAT data
                status: status,
                total_tests: total,
                passed: passed,
                failed: failed,
                notes_count: notesCount,
                results_text: resultsText,
                
                // Context
                project: project,
                version: version,
                handoff_id: handoffId,  // Link to existing handoff if known
                checklist_url: window.location.href,
                tested_by: 'Corey'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Show success with URL
            document.getElementById('submit-result').classList.remove('hidden');
            document.getElementById('handoff-url').value = result.handoff_url;
            btn.textContent = '✅ Submitted!';
            btn.classList.add('success');
        } else {
            throw new Error(result.error || 'Unknown error');
        }
    } catch (error) {
        btn.textContent = '❌ Error: ' + error.message;
        btn.disabled = false;
        setTimeout(() => {
            btn.textContent = '📤 Submit to MetaPM';
        }, 3000);
    }
}

function copyHandoffUrl() {
    const url = document.getElementById('handoff-url').value;
    navigator.clipboard.writeText(url).then(() => {
        alert('URL copied! Paste this to Claude.ai');
    });
}
```

---

## New API Endpoint

### POST /mcp/uat/submit

Public endpoint (no API key required) for UAT checklist submissions.

```python
@router.post("/mcp/uat/submit")
async def submit_uat_from_checklist(data: UATSubmission):
    """
    Accept UAT results directly from HTML checklists.
    Creates handoff record and returns URL.
    """
    
    # 1. Find or create handoff
    if data.handoff_id:
        handoff = await get_handoff(data.handoff_id)
    else:
        # Create new UAT handoff
        handoff = await create_handoff(
            project=data.project,
            task=f"uat-{data.version}",
            direction="to_claude_ai",
            title=f"UAT Results: {data.project} {data.version}",
            content=data.results_text,
            status="pending"  # Claude.ai will review
        )
    
    # 2. Save UAT results
    uat_result = await save_uat_result(
        handoff_id=handoff.id,
        status=data.status,
        total_tests=data.total_tests,
        passed=data.passed,
        failed=data.failed,
        notes_count=data.notes_count,
        results_text=data.results_text,
        checklist_path=data.checklist_url,
        tested_by=data.tested_by
    )
    
    # 3. Update handoff status based on UAT
    if data.status == 'passed':
        handoff.status = 'done'
    elif data.status == 'failed':
        handoff.status = 'needs_fixes'
    
    await save_handoff(handoff)
    
    # 4. Sync to GCS
    gcs_url = await sync_to_gcs(handoff)
    
    # 5. Return URL
    return {
        "success": True,
        "handoff_id": handoff.id,
        "uat_id": uat_result.id,
        "handoff_url": gcs_url,
        "dashboard_url": f"https://metapm.rentyourcio.com/static/handoffs.html?id={handoff.id}"
    }
```

### Request Schema

```python
class UATSubmission(BaseModel):
    # UAT Results
    status: str  # passed, failed, pending
    total_tests: int
    passed: int
    failed: int
    notes_count: int = 0
    results_text: str
    
    # Context
    project: str
    version: str
    handoff_id: Optional[str] = None  # Link to existing handoff
    checklist_url: Optional[str] = None
    tested_by: str = "Corey"
```

### Response Schema

```python
{
    "success": true,
    "handoff_id": "abc-123",
    "uat_id": "uat-456", 
    "handoff_url": "https://storage.googleapis.com/corey-handoff-bridge/metapm/outbox/20260208_uat-results.md",
    "dashboard_url": "https://metapm.rentyourcio.com/static/handoffs.html?id=abc-123"
}
```

---

## UAT Template Update

Update `templates/UAT_Template_v2.html` to include:

1. Submit to MetaPM button
2. JavaScript for API call
3. Handoff URL display
4. Project/version metadata in page

### Add Metadata to Template

```html
<head>
    <meta name="project" content="{{PROJECT}}">
    <meta name="version" content="{{VERSION}}">
    <meta name="handoff-id" content="{{HANDOFF_ID}}">
</head>
```

When Claude.ai creates UAT checklists, fill in these values.

---

## CORS Configuration

Since checklists run from local file:// or project directory, add CORS:

```python
# In main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow local file:// and any origin
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)
```

Or more restrictive:
```python
allow_origins=[
    "file://",
    "https://storage.googleapis.com",
    "https://metapm.rentyourcio.com"
]
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `app/api/mcp.py` | Add `/mcp/uat/submit` endpoint |
| `app/schemas/mcp.py` | Add UATSubmission schema |
| `main.py` | Add CORS for local files |
| `project-methodology/templates/UAT_Template_v2.html` | Add submit button + JS |

---

## Testing Checklist

| Test | Expected |
|------|----------|
| Submit button visible | Shows "📤 Submit to MetaPM" |
| Click submit | Shows loading state |
| Successful submit | Shows handoff URL |
| Copy URL button | Copies to clipboard |
| URL works | Opens GCS or dashboard |
| Claude.ai can fetch | web_fetch returns UAT results |
| Dashboard shows UAT | Badge updates |

---

## Definition of Done

- [ ] `/mcp/uat/submit` endpoint created
- [ ] CORS configured for local files
- [ ] UAT_Template_v2.html updated with submit button
- [ ] Submit creates handoff + UAT record
- [ ] Returns GCS URL
- [ ] Version bumped to 1.9.3
- [ ] Git committed
- [ ] Deployed
- [ ] UAT passed
- [ ] Handoff sent

---

*Feature enhancement from Corey's suggestion*
*Streamline UAT workflow: checklist → MetaPM → URL → Claude.ai*
