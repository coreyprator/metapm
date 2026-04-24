# Outcome Verification Readiness (MP53B Phase F.6)
**Purpose**: Artifact for MP55 spec-lint implementation  
**Created**: 2026-04-23

This section documents expected_outcome + missing_signal + recommended spec-lint assertions for each seeded bug chain. MP55 will read this to build mechanical BV requirement gates.

---

## BC-UAT-DROPDOWN

**Chain label**: BC-UAT-DROPDOWN  
**Members**: BUG-018, BUG-039, BUG-051, BUG-061, BUG-067, BUG-078, BUG-080, BUG-091 (8 total)  
**Failure class**: broken_interaction_bug:app/api/uat_spec.py:classification_dropdown_missing

**Expected outcome**: Dropdown renders with classification options populated from uat_classifications table on UAT page load.

**Missing signal**: Dropdown DOM element contains zero options after page load; no network request to classifications endpoint fired.

**MP55 assertion shape**: Any sprint touching `app/api/uat_spec.py` or UAT form rendering must include:
- (a) cc_machine BV asserting GET /api/uat/classifications returns 200 with array of classification objects (six-field HTTP capture)
- (b) cc_machine BV asserting UAT page HTML contains `<select>` or equivalent with `option` children populated from classifications
- (c) pl_visual BV requiring PL to verify dropdown opens and shows classification options on page load

---

## BC-CSV-EXPORT

**Chain label**: BC-CSV-EXPORT  
**Members**: BUG-029, BUG-030, BUG-031, BUG-062, BUG-063 (5 total, plus TSK-033/DIAG-006 if typed as bug-class)  
**Failure class**: missing_feature:static/dashboard.html:csv_export_gone

**Expected outcome**: Click on Export CSV button triggers download of text/csv file with current dashboard filters applied.

**Missing signal**: exportCsvBtn DOM element absent from dashboard.html, OR GET /api/roadmap/export/csv returns 404, OR click handler not bound.

**MP55 assertion shape**: Any sprint touching `static/dashboard.html` or `app/api/roadmap.py` (export endpoints) must include:
- (a) cc_machine BV asserting exportCsvBtn DOM element exists in dashboard.html (grep or HTML parse)
- (b) cc_machine BV asserting exportCsvBtn has bound click handler in dashboard JavaScript (grep for `exportCsvBtn.addEventListener` or `onclick` attribute)
- (c) cc_machine BV asserting GET /api/roadmap/export/csv returns 200 with Content-Type: text/csv and non-empty body (six-field HTTP capture)
- (d) pl_visual BV requiring PL to click Export CSV and verify file downloads with correct data

---

## Usage Notes for MP55

1. **Mechanical enforcement**: MP55 reads this section and generates BV templates. If a sprint's file manifest matches a chain's affected_module, the corresponding BV assertions are auto-injected into the UAT spec.

2. **Six-field HTTP BVs**: All network assertions must capture method/url/req-headers/req-body/resp-status/resp-headers/resp-body (BA52 R4).

3. **DOM assertions**: Use grep, HTML parse, or DevTools MCP to verify element existence and event binding. No "it should work" inference.

4. **PL-visual separation**: pl_visual BVs are end-to-end user actions. cc_machine BVs are structural proofs that the feature's building blocks exist. Both required.

5. **Recurrence penalty**: If a bug recurs in the same chain after MP55 gates are live, the recurrence is a spec-lint failure (MP56 enforcement).

---

## Extension Pattern

When new chains are seeded (MP53C+), add entries here with the same structure:
- Chain label
- Members (codes)
- Failure class hash
- Expected outcome (observable success signal)
- Missing signal (what's absent or wrong when broken)
- MP55 assertion shape (what BVs to require)

Chains without clear expected_outcome may indicate the chain grouping is incoherent and should be split.
