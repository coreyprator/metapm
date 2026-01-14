# MetaPM Methodology Violation AI Assistant - Requirements & Design

**Version:** 1.0  
**Author:** Claude (Architect)  
**Date:** January 13, 2026  
**Status:** NEW REQUIREMENT - Pending Sprint Assignment  
**Estimated Effort:** 3-5 days

---

## 1. Executive Summary

Create an AI-powered methodology compliance assistant that helps the Project Lead:
1. Log methodology violations efficiently
2. Automatically identify which rules were violated
3. Generate corrective prompts to send back to VS Code (or other AI agents)
4. Track violation patterns over time

**Primary Use Case:** When VS Code deploys to wrong project, PL copies the VS chat, pastes into MetaPM, and gets back a formatted response to paste into VS Code to get it back in compliance.

---

## 2. User Story

> As a Project Lead managing AI agents, I want to quickly log methodology violations and get AI-generated corrective prompts so that I can efficiently enforce compliance without manually writing detailed responses each time.

**Acceptance Criteria:**
- [ ] Can paste raw VS Code chat text into a form
- [ ] AI identifies which methodology rules were violated
- [ ] AI generates a corrective prompt citing specific rules
- [ ] Response is formatted for copy/paste into VS Code
- [ ] Violation is logged with full context for audit trail

---

## 3. Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    VIOLATION LOGGING WORKFLOW                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. PL discovers violation (e.g., wrong project deployment)         │
│                          │                                           │
│                          ▼                                           │
│  2. PL opens Methodology tab → Violations → "Log Violation"         │
│                          │                                           │
│                          ▼                                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              VIOLATION INTAKE FORM                            │   │
│  │  ┌─────────────────────────────────────────────────────────┐ │   │
│  │  │ Project: [META ▼]                                       │ │   │
│  │  ├─────────────────────────────────────────────────────────┤ │   │
│  │  │ Paste VS Code Chat / Incident Context:                  │ │   │
│  │  │ ┌─────────────────────────────────────────────────────┐ │ │   │
│  │  │ │ VS Code said: "I've deployed to project X..."       │ │ │   │
│  │  │ │ But it should have been project Y...                │ │ │   │
│  │  │ │ [Large text area for pasting chat]                  │ │ │   │
│  │  │ └─────────────────────────────────────────────────────┘ │ │   │
│  │  ├─────────────────────────────────────────────────────────┤ │   │
│  │  │ Your Comments/Notes (optional):                         │ │   │
│  │  │ ┌─────────────────────────────────────────────────────┐ │ │   │
│  │  │ │ "This is the 3rd time this week..."                 │ │ │   │
│  │  │ └─────────────────────────────────────────────────────┘ │ │   │
│  │  ├─────────────────────────────────────────────────────────┤ │   │
│  │  │ [🤖 Analyze & Generate Response]  [Save Without AI]    │ │   │
│  │  └─────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                          │                                           │
│                          ▼                                           │
│  3. AI analyzes incident against methodology rules                  │
│                          │                                           │
│                          ▼                                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              AI ANALYSIS RESULTS                              │   │
│  │  ┌─────────────────────────────────────────────────────────┐ │   │
│  │  │ VIOLATIONS IDENTIFIED:                                  │ │   │
│  │  │ • LL-003: Verify GCP Project (CRITICAL)                │ │   │
│  │  │ • LL-036: Verify GCP Project Before Deploy (CRITICAL)  │ │   │
│  │  │ • LL-030: Developer Tests Before Handoff (CRITICAL)    │ │   │
│  │  ├─────────────────────────────────────────────────────────┤ │   │
│  │  │ GENERATED CORRECTIVE PROMPT:                           │ │   │
│  │  │ ┌─────────────────────────────────────────────────────┐ │ │   │
│  │  │ │ ## METHODOLOGY VIOLATION                            │ │ │   │
│  │  │ │                                                     │ │ │   │
│  │  │ │ You have violated the following rules:              │ │ │   │
│  │  │ │                                                     │ │ │   │
│  │  │ │ **LL-003: Verify GCP Project**                     │ │ │   │
│  │  │ │ Always verify the GCP project before running...    │ │ │   │
│  │  │ │                                                     │ │ │   │
│  │  │ │ **LL-036: Verify GCP Project Before Deploy**       │ │ │   │
│  │  │ │ Before any gcloud run deploy...                    │ │ │   │
│  │  │ │                                                     │ │ │   │
│  │  │ │ ## REQUIRED CORRECTIVE ACTION:                     │ │ │   │
│  │  │ │ 1. Run: gcloud config get-value project            │ │ │   │
│  │  │ │ 2. Verify it matches: [PROJECT_ID]                 │ │ │   │
│  │  │ │ 3. Redeploy to correct project                     │ │ │   │
│  │  │ │ 4. Confirm deployment with version number          │ │ │   │
│  │  │ └─────────────────────────────────────────────────────┘ │ │   │
│  │  │                                                         │ │   │
│  │  │ [📋 Copy to Clipboard]  [✏️ Edit]  [💾 Save Violation] │ │   │
│  │  └─────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                          │                                           │
│                          ▼                                           │
│  4. PL copies prompt → pastes into VS Code chat                     │
│                          │                                           │
│                          ▼                                           │
│  5. VS Code acknowledges and corrects behavior                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. API Design

### 4.1 New Endpoint: Analyze Violation

```
POST /api/methodology/violations/analyze
```

**Request:**
```json
{
    "projectCode": "META",
    "incidentContext": "VS Code said: I've deployed to project super-flashcards...\n[full chat paste]",
    "plComments": "This is the 3rd time this week. Need to reinforce the deployment checklist.",
    "generateResponse": true
}
```

**Response:**
```json
{
    "success": true,
    "analysis": {
        "identifiedRules": [
            {
                "ruleCode": "LL-003",
                "ruleName": "Verify GCP Project",
                "severity": "CRITICAL",
                "confidence": 0.95,
                "matchReason": "Incident mentions deploying to wrong project"
            },
            {
                "ruleCode": "LL-036",
                "ruleName": "Verify GCP Project Before Deploy",
                "severity": "CRITICAL",
                "confidence": 0.92,
                "matchReason": "Deployment occurred without project verification"
            }
        ],
        "suggestedCategory": "DEPLOYMENT",
        "severityAssessment": "CRITICAL"
    },
    "generatedPrompt": "## METHODOLOGY VIOLATION\n\nYou have violated...",
    "violationId": null  // Not saved yet
}
```

### 4.2 New Endpoint: Save Violation with AI Response

```
POST /api/methodology/violations
```

**Request (Enhanced):**
```json
{
    "projectCode": "META",
    "ruleIds": [6, 21],  // LL-003, LL-036
    "context": "VS Code deployed to wrong project...",
    "plComments": "3rd time this week",
    "aiAnalysis": { ... },  // Full analysis from /analyze
    "generatedPrompt": "## METHODOLOGY VIOLATION...",
    "copilotSessionRef": "https://github.com/copilot/session/123"
}
```

### 4.3 AI Prompt for Analysis

```python
VIOLATION_ANALYSIS_PROMPT = """
You are a methodology compliance analyzer for software development projects.

METHODOLOGY RULES:
{rules_json}

INCIDENT REPORT:
Project: {project_code}
Context/Chat Log:
{incident_context}

Project Lead Comments:
{pl_comments}

TASK:
1. Identify which methodology rules were likely violated
2. For each violated rule, explain why (cite specific text from incident)
3. Assess overall severity (CRITICAL, HIGH, MEDIUM, LOW)
4. Generate a corrective prompt that:
   - Lists violated rules with descriptions
   - Cites the specific methodology document sections
   - Provides clear corrective actions
   - Is formatted for copy/paste into VS Code chat

OUTPUT FORMAT (JSON):
{
    "identifiedRules": [
        {
            "ruleCode": "LL-XXX",
            "ruleName": "...",
            "severity": "...",
            "confidence": 0.0-1.0,
            "matchReason": "..."
        }
    ],
    "suggestedCategory": "DEPLOYMENT|TESTING|DOCUMENTATION|...",
    "severityAssessment": "CRITICAL|HIGH|MEDIUM|LOW",
    "generatedPrompt": "## METHODOLOGY VIOLATION\\n\\n..."
}
"""
```

---

## 5. Database Changes

### 5.1 Enhanced MethodologyViolations Table

```sql
-- Add columns if not present
ALTER TABLE MethodologyViolations ADD 
    PLComments NVARCHAR(MAX),
    AIAnalysisJSON NVARCHAR(MAX),      -- Store full AI analysis
    GeneratedPrompt NVARCHAR(MAX),      -- Store generated corrective prompt
    PromptCopied BIT DEFAULT 0,         -- Track if PL used the prompt
    PromptCopiedAt DATETIME2;
```

### 5.2 New Table: ViolationRuleLinks (Many-to-Many)

```sql
-- A single violation can break multiple rules
CREATE TABLE ViolationRuleLinks (
    LinkID INT IDENTITY(1,1) PRIMARY KEY,
    ViolationID INT NOT NULL FOREIGN KEY REFERENCES MethodologyViolations(ViolationID),
    RuleID INT NOT NULL FOREIGN KEY REFERENCES MethodologyRules(RuleID),
    Confidence DECIMAL(3,2),  -- AI confidence score
    MatchReason NVARCHAR(500),
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    CONSTRAINT UQ_ViolationRule UNIQUE (ViolationID, RuleID)
);
```

---

## 6. UI Components

### 6.1 Violation Intake Form

```html
<!-- Enhanced Log Violation Modal -->
<div id="violationModal" class="modal-overlay hidden">
    <div class="modal-content" style="max-width: 800px;">
        <h2>Log Methodology Violation</h2>
        
        <form id="violationForm">
            <!-- Project Selection -->
            <div class="form-group">
                <label>Project</label>
                <select id="violationProject" required>
                    <option value="">Select project...</option>
                    <!-- Populated from API -->
                </select>
            </div>
            
            <!-- Incident Context (Main Input) -->
            <div class="form-group">
                <label>Paste VS Code Chat / Incident Context</label>
                <textarea id="violationContext" rows="10" 
                    placeholder="Paste the VS Code chat or describe the incident..."
                    required></textarea>
                <small>Tip: Copy the entire VS Code chat for best AI analysis</small>
            </div>
            
            <!-- PL Comments -->
            <div class="form-group">
                <label>Your Comments/Notes (optional)</label>
                <textarea id="violationComments" rows="3"
                    placeholder="Add your observations, patterns noticed, questions..."></textarea>
            </div>
            
            <!-- Copilot Session Reference -->
            <div class="form-group">
                <label>VS Code Session URL (optional)</label>
                <input type="url" id="violationSessionRef" 
                    placeholder="https://github.com/copilot/...">
            </div>
            
            <!-- Action Buttons -->
            <div class="form-actions">
                <button type="button" id="analyzeViolationBtn" class="btn btn-primary">
                    🤖 Analyze & Generate Response
                </button>
                <button type="button" id="saveWithoutAIBtn" class="btn btn-secondary">
                    Save Without AI
                </button>
                <button type="button" class="btn btn-ghost" onclick="closeViolationModal()">
                    Cancel
                </button>
            </div>
        </form>
        
        <!-- AI Analysis Results (Initially Hidden) -->
        <div id="aiAnalysisResults" class="hidden">
            <hr>
            <h3>🤖 AI Analysis Results</h3>
            
            <!-- Identified Violations -->
            <div id="identifiedViolations" class="violation-list">
                <!-- Populated by JS -->
            </div>
            
            <!-- Generated Prompt -->
            <div class="form-group">
                <label>Generated Corrective Prompt</label>
                <textarea id="generatedPrompt" rows="12" readonly></textarea>
                <div class="prompt-actions">
                    <button type="button" id="copyPromptBtn" class="btn btn-success">
                        📋 Copy to Clipboard
                    </button>
                    <button type="button" id="editPromptBtn" class="btn btn-secondary">
                        ✏️ Edit
                    </button>
                </div>
            </div>
            
            <!-- Final Save -->
            <div class="form-actions">
                <button type="button" id="saveViolationBtn" class="btn btn-primary">
                    💾 Save Violation & Log
                </button>
            </div>
        </div>
    </div>
</div>
```

### 6.2 JavaScript Handler

```javascript
async function analyzeViolation() {
    const projectCode = document.getElementById('violationProject').value;
    const context = document.getElementById('violationContext').value;
    const comments = document.getElementById('violationComments').value;
    
    if (!projectCode || !context) {
        showToast('Please select project and enter incident context', 'error');
        return;
    }
    
    // Show loading
    document.getElementById('analyzeViolationBtn').disabled = true;
    document.getElementById('analyzeViolationBtn').textContent = '🔄 Analyzing...';
    
    try {
        const res = await fetch(`${API}/api/methodology/violations/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                projectCode,
                incidentContext: context,
                plComments: comments,
                generateResponse: true
            })
        });
        
        const data = await res.json();
        
        if (data.success) {
            displayAnalysisResults(data);
        } else {
            showToast('Analysis failed: ' + data.error, 'error');
        }
    } catch (err) {
        showToast('Error: ' + err.message, 'error');
    } finally {
        document.getElementById('analyzeViolationBtn').disabled = false;
        document.getElementById('analyzeViolationBtn').textContent = '🤖 Analyze & Generate Response';
    }
}

function displayAnalysisResults(data) {
    // Show results section
    document.getElementById('aiAnalysisResults').classList.remove('hidden');
    
    // Display identified rules
    const violationsList = document.getElementById('identifiedViolations');
    violationsList.innerHTML = data.analysis.identifiedRules.map(rule => `
        <div class="violation-item severity-${rule.severity.toLowerCase()}">
            <strong>${rule.ruleCode}: ${rule.ruleName}</strong>
            <span class="badge badge-${rule.severity.toLowerCase()}">${rule.severity}</span>
            <p class="match-reason">${rule.matchReason}</p>
            <small>Confidence: ${Math.round(rule.confidence * 100)}%</small>
        </div>
    `).join('');
    
    // Display generated prompt
    document.getElementById('generatedPrompt').value = data.generatedPrompt;
    
    // Store for save
    window.currentViolationAnalysis = data;
}

async function copyPromptToClipboard() {
    const prompt = document.getElementById('generatedPrompt').value;
    await navigator.clipboard.writeText(prompt);
    showToast('Copied to clipboard!');
    
    // Track that prompt was copied
    window.promptCopied = true;
}

async function saveViolation() {
    const data = window.currentViolationAnalysis;
    if (!data) {
        showToast('No analysis to save', 'error');
        return;
    }
    
    const payload = {
        projectCode: document.getElementById('violationProject').value,
        ruleIds: data.analysis.identifiedRules.map(r => r.ruleId),
        context: document.getElementById('violationContext').value,
        plComments: document.getElementById('violationComments').value,
        aiAnalysis: data.analysis,
        generatedPrompt: document.getElementById('generatedPrompt').value,
        promptCopied: window.promptCopied || false,
        copilotSessionRef: document.getElementById('violationSessionRef').value
    };
    
    try {
        const res = await fetch(`${API}/api/methodology/violations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (res.ok) {
            showToast('Violation logged successfully');
            closeViolationModal();
            loadViolations();  // Refresh list
        } else {
            showToast('Failed to save violation', 'error');
        }
    } catch (err) {
        showToast('Error: ' + err.message, 'error');
    }
}
```

---

## 7. Backend Implementation

### 7.1 New API Endpoint: analyze_violation

```python
# app/api/methodology.py

@router.post("/violations/analyze")
async def analyze_violation(request: ViolationAnalyzeRequest):
    """Use AI to analyze incident and identify violated rules."""
    
    # Get all active methodology rules
    rules = execute_query("""
        SELECT RuleID, RuleCode, RuleName, Description, Category, Severity
        FROM MethodologyRules WHERE IsActive = 1
    """)
    
    # Build prompt for Claude
    rules_json = json.dumps(rules, default=str)
    
    prompt = VIOLATION_ANALYSIS_PROMPT.format(
        rules_json=rules_json,
        project_code=request.projectCode,
        incident_context=request.incidentContext,
        pl_comments=request.plComments or "None provided"
    )
    
    # Call Claude API
    try:
        response = await call_claude_api(
            system="You are a methodology compliance analyzer. Always respond with valid JSON.",
            user_message=prompt,
            max_tokens=2000
        )
        
        # Parse response
        analysis = json.loads(response)
        
        # Map rule codes to IDs
        rule_map = {r['RuleCode']: r['RuleID'] for r in rules}
        for identified in analysis.get('identifiedRules', []):
            identified['ruleId'] = rule_map.get(identified['ruleCode'])
        
        return {
            "success": True,
            "analysis": analysis,
            "generatedPrompt": analysis.get('generatedPrompt', '')
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def call_claude_api(system: str, user_message: str, max_tokens: int = 1000):
    """Call Anthropic Claude API."""
    import anthropic
    
    client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}]
    )
    
    return message.content[0].text
```

---

## 8. Testing Requirements

### 8.1 Unit Tests

```python
def test_violation_analysis_identifies_rules():
    """AI should identify correct rules from incident context."""
    response = client.post("/api/methodology/violations/analyze", json={
        "projectCode": "META",
        "incidentContext": "VS Code deployed to wrong GCP project without verifying first",
        "plComments": "Need to enforce deployment checklist",
        "generateResponse": True
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert len(data["analysis"]["identifiedRules"]) > 0
    
    # Should identify deployment-related rules
    rule_codes = [r["ruleCode"] for r in data["analysis"]["identifiedRules"]]
    assert "LL-003" in rule_codes or "LL-036" in rule_codes

def test_generated_prompt_includes_rules():
    """Generated prompt should cite the violated rules."""
    # ... test implementation
```

### 8.2 Playwright Tests

```python
def test_violation_form_workflow(page):
    """Test full violation logging workflow."""
    page.goto(f"{BASE_URL}/static/dashboard.html")
    page.click('.tab-btn[data-tab="methodology"]')
    page.click('.method-tab[data-subtab="violations"]')
    page.click('#logViolationBtn')
    
    # Fill form
    page.select_option('#violationProject', 'META')
    page.fill('#violationContext', 'VS Code deployed to wrong project')
    page.fill('#violationComments', 'Test violation')
    
    # Analyze
    page.click('#analyzeViolationBtn')
    page.wait_for_selector('#aiAnalysisResults:not(.hidden)')
    
    # Verify analysis appeared
    expect(page.locator('#identifiedViolations')).to_contain_text('LL-')
    expect(page.locator('#generatedPrompt')).not_to_be_empty()
    
    # Copy prompt
    page.click('#copyPromptBtn')
    
    # Save
    page.click('#saveViolationBtn')
    page.wait_for_selector('.toast')
```

---

## 9. Implementation Phases

| Phase | Days | Deliverable |
|-------|------|-------------|
| 1 | 1 | Database schema updates, ViolationRuleLinks table |
| 2 | 1-2 | Backend `/violations/analyze` endpoint with Claude integration |
| 3 | 1 | Enhanced violation intake form UI |
| 4 | 0.5 | Copy to clipboard, edit prompt functionality |
| 5 | 0.5 | Save violation with full analysis data |
| 6 | 1 | Testing and deployment |
| **Total** | **3-5** | Full AI-assisted violation tracking |

---

## 10. Dependencies

- [ ] Fix current `/api/methodology/violations` 500 error first
- [ ] Anthropic API key already configured (used by capture feature)
- [ ] Methodology rules populated (42 rules exist)

---

## 11. Success Metrics

- **Time to log violation:** < 2 minutes (vs. 5-10 minutes manually)
- **Prompt quality:** PL accepts generated prompt without editing 80%+ of time
- **Rule identification accuracy:** AI correctly identifies violated rules 90%+ of time

---

## Summary

This feature transforms the Methodology tab from a passive log into an active compliance assistant. The PL can quickly:

1. **Paste** → VS Code chat
2. **Click** → Analyze
3. **Copy** → Generated prompt
4. **Paste** → Into VS Code

Total time: ~1 minute instead of 5-10 minutes writing manual responses.
