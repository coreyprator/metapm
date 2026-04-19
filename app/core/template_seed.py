"""
MP47 REQ-082: Seed data for the `templates` table.

Each template has its own numbered question set. Content preserved verbatim
from the legacy static templates.html JS object.
"""

TEMPLATE_SEED = [
    {
        "id": "1",
        "name": "Bug Fix",
        "version": "1.0",
        "display_order": 1,
        "questions": [
            {"number": 1, "text": "What is broken? (URL, user action, wrong behavior)"},
            {"number": 2, "text": "What should happen instead?"},
            {"number": 3, "text": "What are the exact steps to reproduce?"},
            {"number": 4, "text": "What error evidence exists? (logs, console output, screenshots)"},
            {"number": 5, "text": "What environment is affected? (URL, browser, last working version)"},
            {"number": 6, "text": "What is the suspected root cause, if known?"},
            {"number": 7, "text": "What constraints must be preserved? (adjacent features, data, rollback path)"},
        ],
        "content_md": """## BUG FIX

**Project:** [project name + emoji]
**PTH:** [PTH code]
**Bug Code:** BUG-[NNN]
**Reported:** [date]
**Severity:** [P1 Critical / P2 High / P3 Normal]

---

### Problem Statement
[What is broken? Be specific — include the URL, the user action, and the wrong behavior.]

### Expected Behavior
[What should happen instead?]

### Steps to Reproduce
1. [Navigate to ...]
2. [Click / submit / trigger ...]
3. [Observe ...]

### Error Evidence
```
[Paste error message, console output, or screenshot description]
```

### Environment
- Production URL: [https://...]
- Browser / client: [if relevant]
- Last known working version: [vX.X.X]

### Suspected Root Cause
[If known — otherwise state "Unknown, needs diagnosis"]

### Constraints
- [ ] Must not break [adjacent feature]
- [ ] Must preserve [data / behavior]
- [ ] Rollback path: [describe or "standard revert"]

---

### DELIVERABLE
- [ ] Bug is fixed and verified on production URL
- [ ] No regressions in adjacent features
- [ ] Version bump: vX.X.X -> vX.X.X
- [ ] Handoff posted to MetaPM with evidence""",
    },
    {
        "id": "2",
        "name": "Diagnosing an Unknown Problem",
        "version": "1.0",
        "display_order": 2,
        "questions": [
            {"number": 1, "text": "What symptom is the user experiencing?"},
            {"number": 2, "text": "When did it start? (date / version / deploy)"},
            {"number": 3, "text": "What has been tried already?"},
            {"number": 4, "text": "What is the affected scope? (URLs, features, user conditions)"},
            {"number": 5, "text": "What evidence is available? (logs, errors, screenshots)"},
            {"number": 6, "text": "What is the hypothesis space? (possible causes A/B/C)"},
            {"number": 7, "text": "What diagnostic steps are requested?"},
        ],
        "content_md": """## DIAGNOSING AN UNKNOWN PROBLEM

**Project:** [project name + emoji]
**PTH:** [PTH code]
**Reported:** [date]

---

### Symptom
[What is the user experiencing? Describe the observable behavior without assuming a cause.]

### When Did It Start?
[Date / version / deploy if known — otherwise "Unknown"]

### What Has Been Tried?
- [ ] [First thing checked]
- [ ] [Second thing checked]
- [ ] [Nothing yet — fresh diagnosis needed]

### Affected Scope
- URL(s): [https://...]
- Feature(s): [which features are impacted]
- Users affected: [all / specific conditions]

### Available Evidence
```
[Logs, error messages, screenshots, or "none available"]
```

### Hypothesis Space
1. [Possible cause A]
2. [Possible cause B]
3. [Possible cause C]

### Diagnostic Steps Requested
- [ ] Check logs for [specific pattern]
- [ ] Query database for [specific state]
- [ ] Test endpoint [specific URL] with [specific input]
- [ ] Compare behavior between [version A] and [version B]

---

### DELIVERABLE
- [ ] Root cause identified and documented
- [ ] Fix implemented OR escalation with evidence
- [ ] Verification that the symptom is resolved""",
    },
    {
        "id": "3",
        "name": "New Feature Request",
        "version": "1.0",
        "display_order": 3,
        "questions": [
            {"number": 1, "text": "What is the feature and why does PL want it?"},
            {"number": 2, "text": "What is the user story? (As a [role], I want to [action] so that [benefit])"},
            {"number": 3, "text": "What are the acceptance criteria? (specific, testable)"},
            {"number": 4, "text": "What are the UI / UX details? (layout, interactions, style reference)"},
            {"number": 5, "text": "What are the technical notes? (endpoints, schema changes, dependencies)"},
            {"number": 6, "text": "What is explicitly out of scope?"},
            {"number": 7, "text": "What edge cases must be handled? (empty input, no data, mobile)"},
        ],
        "content_md": """## NEW FEATURE REQUEST

**Project:** [project name + emoji]
**PTH:** [PTH code]
**Requirement Code:** REQ-[NNN]
**Priority:** [P1 / P2 / P3]

---

### Feature Summary
[One paragraph: what is the feature and why does PL want it?]

### User Story
As a [role], I want to [action] so that [benefit].

### Acceptance Criteria
- [ ] [Criterion 1 — specific, testable]
- [ ] [Criterion 2 — specific, testable]
- [ ] [Criterion 3 — specific, testable]

### UI / UX Details
[Describe the visual behavior, layout, interactions. Reference existing pages for style matching.]

### Technical Notes
- Endpoint(s): [GET/POST /api/...]
- Database changes: [new table / new column / none]
- Dependencies: [other services, APIs, secrets]

### Out of Scope
- [What this sprint does NOT include]
- [Adjacent features to resist building]

### Edge Cases
- [What happens if input is empty?]
- [What happens if the user has no data?]
- [What happens on mobile?]

---

### DELIVERABLE
- [ ] Feature implemented and deployed to production
- [ ] All acceptance criteria verified
- [ ] Version bump: vX.X.X -> vX.X.X
- [ ] Handoff posted to MetaPM""",
    },
    {
        "id": "4",
        "name": "Sprint Scope Definition",
        "version": "1.0",
        "display_order": 4,
        "questions": [
            {"number": 1, "text": "What is the sprint goal? (one sentence outcome)"},
            {"number": 2, "text": "What requirements are in scope? (code, title, priority, type)"},
            {"number": 3, "text": "What is the implementation order and why?"},
            {"number": 4, "text": "What is explicitly out of scope?"},
            {"number": 5, "text": "What dependencies exist? (secrets, migrations, upstream deploys)"},
            {"number": 6, "text": "What are the highest risks and mitigations?"},
            {"number": 7, "text": "What machine BVs and PL-visual BVs will verify the work?"},
        ],
        "content_md": """## SPRINT SCOPE DEFINITION

**Project:** [project name + emoji]
**PTH:** [PTH code]
**Sprint ID:** [SPRINT-CODE]
**Version:** [vX.X.X -> vX.X.X]
**Estimated Hours:** [N]

---

### Sprint Goal
[One sentence: what is the outcome of this sprint?]

### Requirements In Scope

| # | Code | Title | Priority | Type |
|---|------|-------|----------|------|
| 1 | REQ-NNN | [title] | P1 | feature |
| 2 | BUG-NNN | [title] | P2 | bugfix |
| 3 | REQ-NNN | [title] | P3 | enhancement |

### Implementation Order
1. [First — because ...]
2. [Second — because ...]
3. [Third — because ...]

### Out of Scope
- [Explicitly excluded item 1]
- [Explicitly excluded item 2]

### Dependencies
- [ ] [Secret / env var needed]
- [ ] [Database migration needed]
- [ ] [Other service must be deployed first]

### Risk Assessment
- **Highest risk:** [what could go wrong]
- **Mitigation:** [how to prevent or recover]
- **Rollback plan:** [revert strategy]

### Machine BVs (Test Plan)
| BV# | Title | Type | Command / Steps |
|-----|-------|------|-----------------|
| M01 | [title] | cc_machine | curl ... |
| M02 | [title] | cc_machine | curl ... |
| V01 | [title] | pl_visual | Navigate to ... |

---

### DELIVERABLE
- [ ] All requirements implemented
- [ ] All BVs pass
- [ ] Deployed to production
- [ ] Handoff + UAT spec posted to MetaPM""",
    },
    {
        "id": "5",
        "name": "Spec Readiness Check (5Q)",
        "version": "1.0",
        "display_order": 5,
        "questions": [
            {"number": 1, "text": "Q1 Action — Is every deliverable explicitly named with a clear success state?"},
            {"number": 2, "text": "Q2 Assertion — For every deliverable, is the assertion specific enough that CC can determine pass/fail without judgment?"},
            {"number": 3, "text": "Q3 Inputs/Outputs — What is the confirmed pre-state, what changes, and what is the verified post-state?"},
            {"number": 4, "text": "Q4 Misinterpretation — What will CC, CAI, or PL get wrong? (naming collisions, scope creep, edge cases, ambiguity)"},
            {"number": 5, "text": "Q5 Failure Mode — What is the single most dangerous failure, and what prevents it?"},
        ],
        "content_md": """## SPEC READINESS CHECK (5Q)

**Requirement Code:** [REQ-NNN / BUG-NNN]
**Project:** [project name + emoji]
**PTH:** [PTH code]

---

### Q1 — Action
**Is every deliverable explicitly named with a clear success state?**

- Deliverables:
  1. [Deliverable name] — success state: [specific]
  2. [Deliverable name] — success state: [specific]
- Out of scope: [what is excluded]
- Version bump: [vX.X.X -> vX.X.X] — justified because [reason]
- Phase dependencies: [Phase 1 must complete before Phase 2 because ...]

### Q2 — Assertion
**For every deliverable, is the assertion specific enough for pass/fail?**

| BV# | Type | Exact Command | Expected Output | Failure Signal |
|-----|------|---------------|-----------------|----------------|
| M01 | cc_machine | curl -s URL | {"status": "ok"} | non-200 or missing field |
| V01 | pl_visual | Navigate to /page, click X | See Y | Y is missing or wrong |

- Test data seeding needed? [yes — strategy / no]
- End-to-end parity check: [describe]

### Q3 — Inputs / Outputs / Changes
**Pre-state -> Changes -> Post-state**

- Pre-state (confirmed live):
  - [Table X has N rows]
  - [Endpoint /api/Y returns Z]
  - [Version: vX.X.X]
- Changes:
  - [File: app/foo.py — add function bar()]
  - [Table: new column baz on table X]
  - [Endpoint: new GET /api/new]
- Post-state:
  - [Table X has N+1 columns]
  - [GET /api/new returns 200]
- Side effects: [none / affects project Y because ...]
- Rollback: [revert commit + drop column]

### Q4 — Misinterpretation
**What will CC, CAI, or PL get wrong?**

- Q4A Naming collisions: [spec says "status" but table has "req_status"]
- Q4B Scope creep temptation: [CC may try to also refactor ...]
- Q4C Undefined edge cases: [what if input is empty? Decision: ...]
- Q4D Ambiguous terms: ["template" means X in this context, not Y]

### Q5 — Failure Mode
**What is the single most dangerous failure?**

- Most dangerous failure: [describe]
- Stop condition: [if X happens, CC must stop and report]
- Recovery path: [rollback steps]
- Silent failure mode: [counter that never increments / detector that always returns zero]
- Verification step: [how to confirm it's not silently failing]

---

### READINESS VERDICT
- [ ] All 5 questions answered substantively
- [ ] No gaps requiring PL input
- [ ] Ready to post_prompt""",
    },
    {
        "id": "6",
        "name": "Architecture / Design Decision",
        "version": "1.0",
        "display_order": 6,
        "questions": [
            {"number": 1, "text": "What is the context? (situation requiring a decision)"},
            {"number": 2, "text": "What are the decision drivers? (performance, compliance, UX)"},
            {"number": 3, "text": "What options were considered? (A, B, C with pros/cons/effort)"},
            {"number": 4, "text": "Which option was chosen and why?"},
            {"number": 5, "text": "What are the consequences? (changes, constraints, enabled/blocked work)"},
            {"number": 6, "text": "What systems are affected? (services, tables, endpoints, other projects)"},
        ],
        "content_md": """## ARCHITECTURE / DESIGN DECISION

**Project:** [project name + emoji]
**Decision ID:** [ADR-NNN or REQ-NNN]
**Date:** [date]
**Status:** [proposed / accepted / superseded]

---

### Context
[What is the situation that requires a decision? What problem are we solving?]

### Decision Drivers
- [Driver 1 — e.g., performance, compliance, user experience]
- [Driver 2]
- [Driver 3]

### Options Considered

#### Option A: [Name]
- Description: [how it works]
- Pros: [advantages]
- Cons: [disadvantages]
- Effort: [low / medium / high]

#### Option B: [Name]
- Description: [how it works]
- Pros: [advantages]
- Cons: [disadvantages]
- Effort: [low / medium / high]

#### Option C: [Name]
- Description: [how it works]
- Pros: [advantages]
- Cons: [disadvantages]
- Effort: [low / medium / high]

### Decision
[Which option was chosen and why]

### Consequences
- [What changes as a result]
- [What new constraints are introduced]
- [What future work is enabled or blocked]

### Affected Systems
- [Service / table / endpoint affected]
- [Other projects impacted]

---

### RECORD
- [ ] Decision documented
- [ ] Stakeholders notified
- [ ] Implementation plan created (if applicable)""",
    },
    {
        "id": "7",
        "name": "Governance Amendment",
        "version": "1.0",
        "display_order": 7,
        "questions": [
            {"number": 1, "text": "What is the current rule? (quote verbatim with section/BA code)"},
            {"number": 2, "text": "What problem exposed the gap or flaw? (reference the sprint/PTH)"},
            {"number": 3, "text": "What is the proposed change? (exact diff — removed vs added)"},
            {"number": 4, "text": "What is the rationale? (specific incidents or patterns)"},
            {"number": 5, "text": "What is the impact? (affected docs, workflows, backward compatibility)"},
            {"number": 6, "text": "What are the implementation steps?"},
            {"number": 7, "text": "What is the rollback path if the amendment causes problems?"},
        ],
        "content_md": """## GOVERNANCE AMENDMENT

**Amendment ID:** [BA-NN or BOOT-X.X.X-BANN]
**Date:** [date]
**Proposed by:** [PL / CAI]
**Status:** [proposed / approved / enacted]

---

### Current Rule
[Quote the existing governance rule verbatim, including its section number or BA code]

### Problem with Current Rule
[What situation exposed the gap or flaw? Be specific — include the sprint/PTH where it surfaced.]

### Proposed Change
[Exact new wording for the rule. Show the diff — what is removed, what is added.]

### Rationale
[Why this change improves governance. Reference specific incidents or patterns.]

### Impact Analysis
- **Affected documents:** [Bootstrap, CAI Outbound, 5Q Framework, etc.]
- **Affected workflows:** [prompt construction, handoff, UAT, etc.]
- **Backward compatibility:** [does this break existing sprints in flight?]

### Implementation Steps
1. [ ] Update compliance_docs table via update_compliance_doc()
2. [ ] Update version / checkpoint
3. [ ] Notify CC sessions of new checkpoint
4. [ ] Update CLAUDE.md if applicable

### Rollback
[How to revert if the amendment causes problems]

---

### APPROVAL
- [ ] PL reviewed and approved
- [ ] Compliance doc updated
- [ ] New checkpoint: BOOT-X.X.X-BANN""",
    },
    {
        "id": "8",
        "name": "Cross-Session Handoff / Context Refresh",
        "version": "1.0",
        "display_order": 8,
        "questions": [
            {"number": 1, "text": "What was done in the prior session? (handoff ID, version, deploy URL, UAT URL)"},
            {"number": 2, "text": "What remains to be done?"},
            {"number": 3, "text": "Why is a new session needed? (timeout, blocker, scope expansion)"},
            {"number": 4, "text": "What context does the new session need? (version, modified files, DB state, branches)"},
            {"number": 5, "text": "What blockers or dependencies exist?"},
            {"number": 6, "text": "What exact instructions should the new session follow?"},
        ],
        "content_md": """## CROSS-SESSION HANDOFF / CONTEXT REFRESH

**Project:** [project name + emoji]
**PTH:** [PTH code from prior session]
**Date:** [date]
**Prior Session Outcome:** [completed / stopped / blocked]

---

### What Was Done
[Summary of the prior session's accomplishments. Reference the handoff ID.]

- Handoff ID: [UUID]
- Version shipped: [vX.X.X]
- Deploy URL: [https://...]
- UAT URL: [https://metapm.rentyourcio.com/uat/UUID]

### What Remains
- [ ] [Unfinished item 1]
- [ ] [Unfinished item 2]
- [ ] [Known issue discovered during prior session]

### Why a New Session Is Needed
[Explain why this couldn't be completed in the prior session — timeout, blocked dependency, scope expansion, etc.]

### Context the New Session Needs
- Current version: [vX.X.X]
- Key files modified in prior session: [list]
- Database state: [any migrations applied, data seeded, etc.]
- Open branches: [branch name if not merged]

### Blockers / Dependencies
- [ ] [Blocker from prior session — resolved? Y/N]
- [ ] [New dependency identified]

### Instructions for New Session
[Specific instructions for what CC should do. Be precise — the new session has no memory of the prior one.]

1. [Step 1]
2. [Step 2]
3. [Step 3]

---

### DELIVERABLE
- [ ] Remaining items completed
- [ ] New handoff posted with updated version
- [ ] Prior session's UAT items re-verified if affected""",
    },
]
