# CC Hotfix: MetaPM — Fix UAT Submit API + Repost Failed Results

## 🚨 BOOTSTRAP GATE
**Read Bootstrap v1.1 FIRST** — located at:
`G:\My Drive\Code\Python\project-methodology\templates\CC_Bootstrap_v1.md`

Complete ALL pre-work gates before writing any code:
1. Read `PROJECT_KNOWLEDGE.md`
2. Read `CLAUDE.md`
3. Activate service account
4. State project identity
5. `git pull origin main`
6. Read previous `SESSION_CLOSEOUT.md`

---

## 🔐 Auth Check

```powershell
# Verify service account is active
gcloud auth list
# Expected: cc-deploy@super-flashcards-475210.iam.gserviceaccount.com (active)

# If not active:
gcloud auth activate-service-account cc-deploy@super-flashcards-475210.iam.gserviceaccount.com --key-file=C:\venvs\cc-deploy-key.json

# DEPLOY WORKAROUND: cc-deploy SA cannot deploy. Switch for deploy only:
# gcloud config set account cprator@cbsware.com
# (switch back after deploy)
```

---

## 📋 Context

**Project**: MetaPM
**Current Version**: v2.3.8 (labeled v2.3.7 due to prior version string miss — fix the label in this sprint)
**Production URL**: https://metapm.rentyourcio.com

### What Happened
PL ran UATs across Super Flashcards, ArtForge, and HarmonyLab. Three issues with posting results to MetaPM:

1. **UAT HTML template submit buttons use wrong field names.** Templates send `test_results_detail` and `test_results_summary` but the API expects `results_text`. Submit buttons fail silently or return: `"Either 'results_text' or 'results' array is required (type=missing_results)"`

2. **PowerShell script POST partially failed.** `POST_UAT_Results_to_MetaPM.ps1` posted 3 UATs successfully but 3 submissions failed with: `"total_tests must be greater than 0"`. The script doesn't send `total_tests`.

3. **No standard UAT template.** PL noted: "CAI should be using standard template." Each UAT was hand-crafted with slightly different submit logic. We need a canonical UAT template that matches the MetaPM API schema exactly.

### Root Problems
- The MetaPM `/api/uat/submit` endpoint schema is not documented in a way that UAT templates can reliably match
- UAT templates were hand-crafted per sprint with no shared submit function
- Field name mismatches between what templates send and what the API expects

---

## 🔧 Requirements

### P0: Audit the UAT Submit API Schema

1. Read the MetaPM codebase — find the `/api/uat/submit` endpoint definition
2. Document the EXACT schema: required fields, optional fields, field names, types, validation rules
3. Output the schema as a reference:
   ```
   POST /api/uat/submit
   Content-Type: application/json
   
   Required fields:
   - project_name: string
   - version: string
   - results_text: string (OR results: array)
   - total_tests: integer (> 0)
   - ...
   
   Optional fields:
   - linked_requirements: string
   - notes: string
   - ...
   ```
4. Check: Is `total_tests` required? If so, can the API infer it from `results_text` content (count test IDs)? If inference is reasonable, implement it as a fallback so callers don't have to send it explicitly.

### P1: Make the API More Resilient

Without breaking existing callers:
- Accept BOTH `results_text` AND `test_results_detail` as aliases (map legacy field names)
- Accept BOTH `test_results_summary` AND `results_text` 
- If `total_tests` is missing but `results_text` is provided, infer count from content (count lines matching patterns like `[XX-NN]` or `PASS/FAIL/SKIP`)
- If inference fails, default to 1 (not 0) so the validation doesn't reject the submission
- Return a clear, helpful error message when required fields are missing — include the field name AND the expected type

### P2: Create Canonical UAT Template

Create a standard UAT HTML template at:
`G:\My Drive\Code\Python\project-methodology\templates\UAT_Template_v4.html`

This replaces UAT_Template_v3. The template must:

**Structure:**
- Dark theme (matches existing templates: bg #0f1117, cards #161b22, border #30363d)
- Header with project name, version, revision, date, requirements list
- Summary bar with auto-tallying pass/fail/skip/pending counters
- Sections with section titles
- Per-test cards with: test ID, test name, badge (FIX/NEW/REG/HOT), radio group (pass/fail/skip), notes textarea
- General notes field at the bottom (PL requested this — was missing from prior templates)
- Button row: Copy Results + Submit to MetaPM

**Submit Logic — MUST match MetaPM API exactly:**
```javascript
function submitToMetaPM() {
  // Gather results
  const results = gatherResults(); // existing function
  
  // Count tests
  let pass = 0, fail = 0, skip = 0;
  document.querySelectorAll('input[type=radio]:checked').forEach(r => {
    if (r.value === 'pass') pass++;
    else if (r.value === 'fail') fail++;
    else skip++;
  });
  const total = document.querySelectorAll('.test').length;
  
  // POST with correct field names
  fetch('https://metapm.rentyourcio.com/api/uat/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_name: PROJECT_NAME,      // Set per template
      version: VERSION,                 // Set per template
      results_text: results,            // Full text results
      total_tests: total,               // REQUIRED by API
      passed: pass,
      failed: fail,
      skipped: skip,
      linked_requirements: REQUIREMENTS, // Set per template
      notes: document.getElementById('general-notes')?.value || ''
    })
  })
  .then(r => r.json())
  .then(data => {
    // Show result persistently (not flash)
    showResult(data);
  })
  .catch(err => {
    showResult({ error: err.message });
  });
}
```

**Template variables** (CAI fills these per sprint):
```html
<script>
  const PROJECT_NAME = "{{PROJECT_NAME}}";
  const VERSION = "{{VERSION}}";
  const REQUIREMENTS = "{{REQUIREMENTS}}";
</script>
```

**General notes field:**
```html
<div class="section">
  <div class="section-title">General Notes</div>
  <textarea id="general-notes" class="notes-input" style="min-height:80px" 
    placeholder="Overall observations, new requirements, UX feedback..."></textarea>
</div>
```

**Acceptance Criteria:**
- Template submit button successfully POSTs to MetaPM API with zero field name mismatches
- Submit result is shown persistently (not flash) with the MetaPM response
- General notes field is included
- Template is self-contained (single HTML file, no external dependencies)
- Copy Results button works
- Template renders correctly on desktop and mobile

### P3: Repost the 3 Failed UAT Results

Using the corrected API (after P1 deploys), repost these three UAT results. Use curl or a script — whichever is faster.

**Super Flashcards v3.0.1 UAT:**
```
Summary: 7 passed, 1 failed, 5 pending out of 13 tests
[SM-01] PASS: Version v3.0.1 confirmed. Console: IMG resource load error on error-tracker.js.
[SM-02] PASS: Cards visible, pronunciation works.
[SR-01] PASS: Study mode accessible. 474 cards due.
[SR-02] FAIL: No SRS sorting. SF-005 set back to backlog. Needs membership model.
[SR-03] PENDING: No rating buttons on cards.
[PD-01] PASS: Progress page exists. 1586 cards, 0 mastered.
[PD-02] PASS: Stats present: total, due, mastered, streak, by-language table.
[DIF-01] PASS: Difficulty dropdown visible. All cards unrated.
[PIE-01] PASS: PIE root visible with amber highlight.
[PIE-02] PENDING: New req: PIE pronunciation play button.
[REG-01] PENDING: New req: language reassignment in edit modal.
New Reqs: PIE pronunciation, language reassignment, error-tracker.js fix.
```

**ArtForge v2.3.3 UAT:**
```
Summary: 11 passed, 5 failed, 1 skipped, 1 pending out of 18 tests
[SM-01] SKIP: Health is machine test. Footer shows v2.3.0.
[SM-02] FAIL: Logout doesn't prompt for userid. iPhone caches account.
[IMG-01] PASS: Image generation works.
[IMG-02] PASS: Radio buttons confirmed.
[VID-01] PASS: Generate Video visible.
[VID-02] PASS: Runway selectable.
[VID-03] PASS: Runway video generated (Scene 2).
[VID-04] FAIL: Video disappeared after leaving story.
[VO-01] PASS: Voice-over works.
[SFX-01] PASS: SFX panel visible, dropdown populated.
[SFX-02] FAIL: SFX assignment doesn't persist.
[MUS-01] FAIL: Music dropdown exists but doesn't persist.
[ASM-01] PASS: Assemble button visible.
[ASM-02] FAIL: Assembly 403 on Pixabay CDN music URL.
[PRE-01] PASS: Export button visible.
[PRE-02] PENDING: XML exported but Premiere couldn't import.
[REG-01] PASS: Story creation works.
[REG-02] PASS: Existing stories load.
New Reqs: provider default memory, video persistence, SFX persistence, music persistence + AI gen, Premiere local export, scene splitter UX, VO controls, establishing shot, nav breadcrumb, login flow.
```

**HarmonyLab v1.8.4 UAT:**
```
Summary: 10 passed, 2 failed, 4 skipped, 2 pending out of 18 tests
[SM-01] PENDING: Shows v1.8.5. Health is machine test.
[SM-02] PASS: App loads, login works.
[IMP-01] PASS: MIDI import works, no crash.
[IMP-02] PASS: MIDI import creates song.
[IMP-03] FAIL: .mscz consistently returns 0 chords.
[IMP-04] PASS: Bad file shows clear error.
[CHD-01] FAIL: Chord edit modal still FREE TEXT, not dropdowns. CC claimed done.
[CHD-02] SKIP: Blocked by CHD-01.
[CHD-03] SKIP: Blocked by CHD-01.
[CHD-04] SKIP: Blocked by CHD-01.
[CHD-05] PENDING: Blocked by CHD-01.
[DIAG-01] PASS: Import diagnostics present.
[DIAG-02] SKIP: Blocked by IMP-03.
[ERR-01] PASS: Error toasts working.
[STD-01] PASS: Jazz standards visible.
[BAT-01] PASS: Batch import works.
[REG-01] PASS: Analysis + quiz work.
[REG-02] PASS: Analysis is default.
Critical: CHD-01 chord dropdowns NOT implemented. IMP-03 .mscz parser returns 0 chords.
```

### P4: Fix Version String

Fix the version label from `2.3.7` to `2.3.9` (2.3.8 was the error logging sprint, 2.3.9 is this sprint).

### P5: Document the UAT API Schema in PROJECT_KNOWLEDGE.md

Add a section to PK.md documenting the UAT submit endpoint schema so future CC sessions and CAI know the exact field names.

---

## ✅ Test Commands

```bash
# 1. Health check
curl -s https://metapm.rentyourcio.com/health | python -m json.tool
# Expected: {"status":"healthy","version":"2.3.9"}

# 2. Test UAT submit with all fields
curl -s -X POST "https://metapm.rentyourcio.com/api/uat/submit" \
  -H "Content-Type: application/json" \
  -d '{"project_name":"Test","version":"0.0.0","results_text":"[T-01] PASS: test","total_tests":1,"passed":1,"failed":0,"skipped":0,"notes":"validation test"}' | python -m json.tool
# Expected: 200 OK with UAT ID

# 3. Test legacy field names still work (backward compat)
curl -s -X POST "https://metapm.rentyourcio.com/api/uat/submit" \
  -H "Content-Type: application/json" \
  -d '{"project_name":"Test","version":"0.0.0","test_results_detail":"[T-01] PASS: test","total_tests":1}' | python -m json.tool
# Expected: 200 OK (test_results_detail mapped to results_text)

# 4. Test total_tests inference
curl -s -X POST "https://metapm.rentyourcio.com/api/uat/submit" \
  -H "Content-Type: application/json" \
  -d '{"project_name":"Test","version":"0.0.0","results_text":"[T-01] PASS: test\n[T-02] FAIL: test2"}' | python -m json.tool
# Expected: 200 OK with total_tests inferred as 2

# 5. Verify all 3 UATs posted
curl -s "https://metapm.rentyourcio.com/api/uat?project=Super Flashcards" | python -m json.tool
curl -s "https://metapm.rentyourcio.com/api/uat?project=ArtForge" | python -m json.tool
curl -s "https://metapm.rentyourcio.com/api/uat?project=HarmonyLab" | python -m json.tool

# 6. Open UAT_Template_v4.html in browser, fill in a test, click Submit — verify it works
```

---

## 📮 Handoff Instructions

```bash
curl -X POST https://metapm.rentyourcio.com/api/uat/submit \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "MetaPM",
    "version": "2.3.9",
    "results_text": "<include test command results>",
    "total_tests": 6,
    "linked_requirements": "CROSS-PORTFOLIO",
    "notes": "Fixed UAT submit API field name aliases, total_tests inference, created canonical UAT_Template_v4.html, reposted 3 failed PL UATs, fixed version string 2.3.7→2.3.9."
  }'
```

---

## 🔒 Session Close-Out

1. Create `SESSION_CLOSEOUT.md`
2. Update `PROJECT_KNOWLEDGE.md`:
   - UAT submit API schema documented (all field names, types, required vs optional)
   - Field name aliases (test_results_detail → results_text, etc.)
   - total_tests inference logic
   - UAT_Template_v4.html location and usage
   - Current version: v2.3.9
3. `git add -A && git commit -m "fix: UAT submit API aliases + total_tests inference + canonical template v4 [v2.3.9]"`
4. `git push origin main`
5. Verify deploy via `/health`

---

## ⚠️ Rules
- **Deploy to Cloud Run and test against production.** Do NOT run local.
- **Backward compatibility is mandatory.** Existing UAT templates and scripts must still work after API changes. Add aliases, don't rename fields.
- **The 3 UAT results in P3 must be posted EXACTLY as written.** Do not paraphrase or summarize. These are PL's test results.
- **UAT_Template_v4.html goes in project-methodology repo** at templates/UAT_Template_v4.html. Commit to that repo separately.
- **Test the template submit button yourself** before declaring done. Open the HTML, fill in one test, click Submit, verify MetaPM receives it.
- **Delete the test UAT records** you created during validation (project_name="Test"). Don't leave test data in production.
