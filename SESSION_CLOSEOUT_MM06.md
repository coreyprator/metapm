# Session Closeout — MM06 MCP Tools + Email + Prompt Viewer
Date: 2026-03-20
Version: 2.37.4 → 2.37.5
Commits: 0fd0a69 (MM06), 7f0978e (fix C1 lookup)
Handoff ID: 7CCFAB5C-26CF-4275-8FB1-A99F1EB4C25C
UAT URL: https://metapm.rentyourcio.com/uat/CCE000D9-DDFB-47AB-958E-8FB8E6125BC0

## Sprint
PTH: MM06 | MP-MEGA-012

## Items Delivered

### Item 1 — GET /api/prompts/{pth}/handoff (MP-GET-HO-BY-PTH)
- New endpoint returns handoff_id, uat_url, uat_spec_id, sprint, version, project for any PTH
- Primary lookup: JOIN mcp_handoffs via cc_prompts.handoff_id (set on handoff create)
- Fallback: pth column or metadata LIKE search
- create_handoff: now also writes UPDATE mcp_handoffs SET pth=? for future direct lookups
- C1 PASS: GET /api/prompts/MM05/handoff → 36-char UUID + uat_url

### Item 2 — PA notification email completeness (MP-EMAIL-COMPLETE)
- send_handoff_email: plain-text block at top: PTH, Handoff ID, UAT URL, View link
- Handoff ID row added to HTML table
- notify_pa in prompts.py: forwards handoff_id in payload
- create_handoff in mcp.py: passes handoff_id to notify_pa call
- check-handoffs in PA main.py: passes str(hf['id']) as handoff_id + uses public_url
- PA deployed: personal-assistant-00051-skv (v1.4.1)

### Item 3 — CAI outbound gate on POST /api/prompts (MP-CAI-OUTBOUND-GATE)
- _has_uat_spec() checks for ```json block with test_cases array in content_md
- PromptCreate: enforcement_bypass: Optional[str] field ("data_only_sprint" bypasses)
- Returns 400 {"error":"prompt_missing_uat_spec",...} when no UAT spec found
- C2 PASS: POST without spec → 400
- C3 PASS: POST with spec → 201

### Item 4 — Prompt viewer collapsible UI (MP-PROMPT-UI-001)
- buildCollapsibleContent(): parses content_md into H2 sections
- BOILERPLATE_SECTIONS collapsed by default: Bootstrap, Phase 0, Git Gate, Deploy, Canaries, etc.
- EXPAND_KEYWORDS expanded: Item, Requirement, Objective, Fix, Deliverable, Scope, etc.
- Expand all / Collapse all buttons
- Chevron indicators (▶/▼)
- Section hints for known boilerplate (e.g. "standard preamble")
- C4: browser-only — pending PL UAT

## Files Changed
### MetaPM
- app/api/prompts.py — GET /{pth}/handoff endpoint, CAI outbound gate, notify_pa handoff_id
- app/api/mcp.py — store pth on handoff, pass handoff_id to notify_pa
- app/core/config.py — VERSION 2.37.5
- static/prompt-viewer.html — collapsible section rendering

### Personal Assistant
- sources/gmail_source.py — plain-text block + Handoff ID in email
- main.py — handoff_id in check-handoffs send_handoff_email call, VERSION 1.4.1

## Canaries
- C1: GET /api/prompts/MM05/handoff → handoff_id: 9C169530-4C5C-4A48-B3E6-0D1DC1551445 ✅
- C2: POST /api/prompts without UAT spec → 400 ✅
- C3: POST /api/prompts with UAT spec → 201 ✅
- C4: browser — prompt viewer collapsible (pending PL)
- C5: PA email (pending next handoff trigger)
- C6: MetaPM health → 2.37.5 ✅
- C7: PA health → 1.4.1 ✅
- C8: UAT spec test_count: 5 ✅

## Requirement Transitions
- MP-GET-HO-BY-PTH: cc_executing → cc_complete (193B) → uat_ready
- MP-EMAIL-COMPLETE: cc_executing → cc_complete (B738) → uat_ready
- MP-CAI-OUTBOUND-GATE: cc_executing → cc_complete (E691) → uat_ready
- MP-PROMPT-UI-001: cc_executing → cc_complete (B0FE) → uat_ready
