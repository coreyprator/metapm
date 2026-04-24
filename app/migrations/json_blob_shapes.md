# MetaPM JSON Blob Shapes Documentation
**Sprint**: MP53B Phase C.1  
**Created**: 2026-04-23  
**Purpose**: Document actual JSON structure in blob columns before creating OPENJSON views

## 1. uat_pages.spec_data

**Sample count**: 5 records with valid JSON  
**Structure**: Root object with project/sprint/pth/version + test_cases array

```json
{
  "project": "MP",
  "sprint": "MP53B-DATA-MODEL-CLEANUP-003",
  "pth": "MP53B",
  "version": "v3.2.0 to v3.3.0",
  "test_cases": [
    {
      "id": "M01",
      "type": "cc_machine",
      "title": "BA49 refresh before schema writes",
      "expected": "get_checkpoint('bootstrap') returned BOOT-1.5.63-BA52..."
    },
    {
      "id": "M02",
      "type": "cc_machine",
      "title": "Five new views exist",
      "expected": "SELECT name FROM sys.views..."
    }
  ]
}
```

**Key fields**:
- `project` (string): Project code (MP, SF, HL, etc.)
- `sprint` (string): Full sprint ID
- `pth` (string): Prompt tracking hash
- `version` (string): Version transition
- `test_cases` (array): Array of BV objects with id/type/title/expected

**Usage**: CAI pre-creates UAT specs via post_uat_spec MCP tool. This is the structured form before rendering to uat_bv_items.

---

## 2. uat_pages.cai_review_json

**Sample count**: 3 records with valid JSON  
**Structure**: Root object with focus_areas/risks/regression_zones arrays

```json
{
  "focus_areas": ["UAT tab visible in nav", "PTH searchable"],
  "risks": ["Performance with 50+ UAT records"],
  "regression_zones": ["Existing handoff submit"]
}
```

**Key fields**:
- `focus_areas` (array of strings): What to test carefully
- `risks` (array of strings): Known risk areas
- `regression_zones` (array of strings): Areas prone to breakage

**Usage**: CAI review metadata for PL UAT execution guidance.

---

## 3. uat_pages.general_notes

**Sample count**: 5 records (mixed JSON array and plain text)  
**Structure**: When JSON, it's an array of note objects with timestamp/text/classification

```json
[
  {
    "timestamp": "2026-04-23 17:57:03Z",
    "text": "New Bug: Question content problems with templates...",
    "classification": "bug",
    "failure_type": "regression"
  }
]
```

**Key fields** (when structured):
- `timestamp` (ISO 8601 string): When note was added
- `text` (string): Note content
- `classification` (string, optional): "bug" or other type
- `failure_type` (string, optional): Failure classification

**Usage**: PL free-form notes on UAT execution. **NOT always JSON** — sometimes plain text. View must handle both.

---

## 4. mcp_handoffs.evidence_json

**Sample count**: 2 records with valid JSON  
**Structure**: Array of evidence items with code/status/evidence object

```json
[
  {
    "code": "CANARY-001",
    "status": "complete",
    "evidence": {
      "curl_command": "curl -s https://...",
      "http_status": 200,
      "response_preview": "..."
    }
  }
]
```

**Key fields**:
- `code` (string): Evidence item code
- `status` (string): complete/incomplete/partial
- `evidence` (object, optional): Nested proof data

**Usage**: CC handoff structured machine test evidence (BA17 handoff shell pattern).

---

## 5. reviews.lesson_candidates

**Sample count**: 5 records with valid JSON  
**Structure**: Array of lesson objects with lesson/target/severity

```json
[
  {
    "lesson": "BA12 anti-pattern (function in local scope via onclick) recurred...",
    "target": "bootstrap",
    "severity": "high"
  },
  {
    "lesson": "MuseScore .mscz regression: when replacing an OMR engine...",
    "target": "pk-harmonylab",
    "severity": "medium"
  }
]
```

**Key fields**:
- `lesson` (string): Lesson learned text (governance amendment candidate)
- `target` (string): Target doc (bootstrap, pk-{project}, methodology-*)
- `severity` (string): high/medium/low

**Usage**: CAI review loop 2 output — lessons to route to compliance docs.

---

## 6. cc_prompts.also_closes

**Sample count**: 5 records with valid JSON  
**Structure**: Simple array of requirement codes

```json
["REQ-082", "REQ-084", "REQ-085", "TSK-020"]
```

**Key fields**: None (flat array of strings)

**Usage**: Secondary requirements closed by a sprint (BA44 also_closes gate).

---

## Notes

- **ISJSON() filtering**: All views will use `WHERE ISJSON(column) = 1` to skip malformed JSON.
- **general_notes caveat**: May contain plain text or JSON. View will only extract structured JSON entries.
- **Nullability**: All 6 columns are nullable; views return 0 rows when NULL or invalid JSON.
- **No schema enforcement**: JSON structure is not validated at insert time. Views are read-only analysis tools, not enforcement layers.
