"""Backfill wave 2: Lessons extracted from SESSION_CLOSEOUT files."""
import requests, json, time

BASE = "https://metapm.rentyourcio.com"

LESSONS = [
    {
        "project": "metapm",
        "category": "technical",
        "lesson": "SQL Server ORDER BY in a subquery without TOP or OFFSET is illegal. Move TOP inline to the base SELECT or add OFFSET 0 ROWS to satisfy the requirement.",
        "source_sprint": "HO-MP11",
        "target": "pk.md",
        "target_file": "metapm/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "HO-MP11"
    },
    {
        "project": "metapm",
        "category": "technical",
        "lesson": "SQL CHECK constraints must be dropped BEFORE running UPDATE statements that introduce new values. The constraint rejects the new values during UPDATE even if you plan to recreate it afterward.",
        "source_sprint": "MP-MS3",
        "target": "pk.md",
        "target_file": "metapm/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "MP-MS3"
    },
    {
        "project": "project-methodology",
        "category": "technical",
        "lesson": "Secret Manager values often contain trailing whitespace. Always call .strip() on tokens retrieved from Secret Manager before using them for authentication.",
        "source_sprint": "MP-MS3",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "MP-MS3"
    },
    {
        "project": "metapm",
        "category": "technical",
        "lesson": "conftest.py that imports app.main triggers run_migrations() at module load, hanging without DB credentials. Use --noconftest for smoke tests that hit production endpoints directly.",
        "source_sprint": "HO-MP11",
        "target": "pk.md",
        "target_file": "metapm/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "HO-MP11"
    },
    {
        "project": "metapm",
        "category": "technical",
        "lesson": "MetaPM NVARCHAR(36) ID columns require all FK columns to match NVARCHAR(36) exactly. Using INT or VARCHAR(255) for FKs referencing MetaPM IDs will fail.",
        "source_sprint": "MP-MS3",
        "target": "pk.md",
        "target_file": "metapm/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "MP-MS3"
    },
    {
        "project": "metapm",
        "category": "architecture",
        "lesson": "When storing innerHTML truncated to N chars, clicking to expand cannot restore the original. Store full text in a data attribute (data-full) and truncated version in data-short, then swap innerHTML on click.",
        "source_sprint": "MP-VB-FIX-001",
        "target": "pk.md",
        "target_file": "metapm/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "MP-VB-FIX-001"
    },
    {
        "project": "project-methodology",
        "category": "process",
        "lesson": "Default API pagination (limit=50) can hide records when total exceeds the limit. Always pass an explicit high limit (limit=100+) when auditing record counts or verifying insertions.",
        "source_sprint": "AF-DATA",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "AF-DATA"
    },
    {
        "project": "project-methodology",
        "category": "process",
        "lesson": "Check highest existing requirement code before assigning new codes in specs. Code collisions (e.g., AF-015 already occupied) cause insertion failures and require renumbering.",
        "source_sprint": "AF-DATA",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "AF-DATA"
    },
    {
        "project": "project-methodology",
        "category": "quality",
        "lesson": "UAT submit APIs should use field aliases to accept common synonyms (project_name->project, test_results_detail->results_text). Strict field naming causes silent rejections when callers use reasonable alternative names.",
        "source_sprint": "UAT-SUBMIT-FIX",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "UAT-SUBMIT-FIX"
    },
    {
        "project": "project-methodology",
        "category": "quality",
        "lesson": "Infer total_tests from payload content (count [XX-NN] patterns or PASS/FAIL lines) rather than requiring callers to manually count. Reduces validation failures from missing metadata.",
        "source_sprint": "UAT-SUBMIT-FIX",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "UAT-SUBMIT-FIX"
    },
    {
        "project": "project-methodology",
        "category": "process",
        "lesson": "Audit sprints that verify cross-project requirements need codebase access + auth for each project. Remote API probing from MetaPM alone cannot verify in_progress status for apps behind auth.",
        "source_sprint": "AUDIT-CLEANUP",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "AUDIT-CLEANUP"
    },
    {
        "project": "project-methodology",
        "category": "quality",
        "lesson": "Remove dead UI elements (unused textareas, phantom fields) during audit sprints. A field that is never saved to the DB misleads users into entering data that gets silently discarded.",
        "source_sprint": "AUDIT-CLEANUP",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "AUDIT-CLEANUP"
    },
    {
        "project": "project-methodology",
        "category": "process",
        "lesson": "When correcting status lies (items marked done that were never built), always verify via production API calls rather than trusting the roadmap status. Use endpoint probing (GET returns 404 = not built).",
        "source_sprint": "AUDIT-CLEANUP",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "AUDIT-CLEANUP"
    },
    {
        "project": "metapm",
        "category": "architecture",
        "lesson": "Legacy table names (Tasks, Categories) may conflict with new feature tables. Prefix new tables with a namespace (roadmap_tasks, roadmap_categories) and use namespaced API routes (/api/roadmap/tasks not /api/tasks).",
        "source_sprint": "MP-MS1",
        "target": "pk.md",
        "target_file": "metapm/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "MP-MS1"
    },
    {
        "project": "metapm",
        "category": "technical",
        "lesson": "MetaPM dashboard.html is a ~185KB single-file SPA with inline JS. Edits require careful exact-string matching due to size. Avoid broad regex replacements.",
        "source_sprint": "MP-MS1",
        "target": "pk.md",
        "target_file": "metapm/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "MP-MS1"
    },
    {
        "project": "project-methodology",
        "category": "process",
        "lesson": "Migration numbering gaps (e.g., 14-16 missing, jumping from 13 to 17) should be documented as intentional in comments. Otherwise the next developer will assume data corruption.",
        "source_sprint": "MP-MS1",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "MP-MS1"
    },
    {
        "project": "project-methodology",
        "category": "technical",
        "lesson": "Google Drive creates .~AUTO_MERGE.lock files during sync. Add these to .gitignore. They cause git warnings but do not affect commits.",
        "source_sprint": "MP-MS1",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "MP-MS1"
    },
    {
        "project": "project-methodology",
        "category": "quality",
        "lesson": "Auto-close logic should only close requirements linked via explicit UAT linked_requirements arrays, never from free-text content scanning. Content-parsed links should be informational only.",
        "source_sprint": "MP-MS1-FIX",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "MP-MS1-FIX"
    },
    {
        "project": "project-methodology",
        "category": "process",
        "lesson": "When local files revert to a pre-commit state (e.g., Google Drive sync conflict), run git checkout -- <files> to restore the committed versions before making new changes.",
        "source_sprint": "PF5-MS1",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "PF5-MS1"
    },
    {
        "project": "project-methodology",
        "category": "architecture",
        "lesson": "When removing legacy enum values from a Pydantic model, existing DB rows with old values will fail validation on read. Either migrate all data first, or add a fallback/default for unrecognized values.",
        "source_sprint": "PF5-MS1",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "PF5-MS1"
    },
    {
        "project": "project-methodology",
        "category": "quality",
        "lesson": "Error toasts should persist at least 10 seconds with a close button. Success toasts at 3-4 seconds. Short error toasts disappear before the user can read the message.",
        "source_sprint": "ERROR-LOGGING",
        "target": "standards",
        "target_file": "",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "ERROR-LOGGING"
    },
    {
        "project": "project-methodology",
        "category": "quality",
        "lesson": "Every frontend fetch/API call should log method, URL, HTTP status, AND full response body to console.error on failure. Use response.clone() when the body must also be consumed downstream.",
        "source_sprint": "ERROR-LOGGING",
        "target": "standards",
        "target_file": "",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "ERROR-LOGGING"
    },
    {
        "project": "project-methodology",
        "category": "architecture",
        "lesson": "All FastAPI apps should have a global exception handler that logs the full traceback and returns structured JSON (error, detail, path) with status 500. Without it, unhandled exceptions return opaque HTML error pages.",
        "source_sprint": "ERROR-LOGGING",
        "target": "standards",
        "target_file": "",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "ERROR-LOGGING"
    },
    {
        "project": "metapm",
        "category": "technical",
        "lesson": "The cprator@cbsware.com gcloud token expires frequently. Use cc-deploy SA for deploys. When cprator is needed, run gcloud auth login in the terminal first and verify with gcloud auth list.",
        "source_sprint": "PF5-MS1",
        "target": "pk.md",
        "target_file": "metapm/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "PF5-MS1"
    },
    {
        "project": "project-methodology",
        "category": "architecture",
        "lesson": "Use GCS as the stable source for shared assets (architecture diagrams, docs). App routes should 302-redirect to GCS URLs. Updates only require GCS upload, no app redeploy.",
        "source_sprint": "MP028",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "MP028"
    },
    {
        "project": "project-methodology",
        "category": "process",
        "lesson": "Use a stable filename without version number (e.g., Development_System_Architecture.html) as the latest pointer, and keep versioned copies (_v4.html) as archives. Consumers always link to the stable name.",
        "source_sprint": "MP028",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "MP028"
    },
    {
        "project": "metapm",
        "category": "technical",
        "lesson": "Windows console emoji decode errors can mask HTTP 201 success responses. When a POST appears to fail on Windows, check for duplicate-key errors on retry to confirm the first attempt actually succeeded.",
        "source_sprint": "AF030-MOD",
        "target": "pk.md",
        "target_file": "metapm/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "AF030-MOD"
    },
    {
        "project": "metapm",
        "category": "technical",
        "lesson": "MetaPM deploy requires --set-secrets and --add-cloudsql-instances flags per CLAUDE.md. The short form (gcloud run deploy --source .) may work because Cloud Run remembers config, but is not guaranteed after config changes.",
        "source_sprint": "MP028",
        "target": "pk.md",
        "target_file": "metapm/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "MP028"
    },
    {
        "project": "project-methodology",
        "category": "process",
        "lesson": "GitHub PAT tokens stored in Secret Manager can hit rate limits under automated workloads. Monitor PAT usage and consider per-repo fine-grained tokens rather than a single broad-scope token.",
        "source_sprint": "MP-MS3-FIX",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "MP-MS3-FIX"
    },
    {
        "project": "project-methodology",
        "category": "process",
        "lesson": "Data-only sprints (inserting requirements, correcting statuses) should not deploy code changes. Bump version only when code is modified. This avoids unnecessary revision churn and deploy risk.",
        "source_sprint": "AF-DATA",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "AF-DATA"
    },
    {
        "project": "metapm",
        "category": "architecture",
        "lesson": "Task hierarchy can be changed in the UI (sibling vs nested display) without modifying the DB schema. Keep the FK relationship intact and adjust rendering only. Schema changes for display preferences are unnecessary.",
        "source_sprint": "MP-MS1-FIX",
        "target": "pk.md",
        "target_file": "metapm/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "MP-MS1-FIX"
    },
    {
        "project": "metapm",
        "category": "architecture",
        "lesson": "Legacy status values in the DB (backlog/executing/closed) should allow unrestricted transitions (None in VALID_TRANSITIONS map) since they predate the lifecycle state machine. Only new lifecycle states need enforced transition rules.",
        "source_sprint": "PF5-MS1",
        "target": "pk.md",
        "target_file": "metapm/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "PF5-MS1"
    },
]

print(f"Backfilling wave 2: {len(LESSONS)} lessons...")
for i, lesson in enumerate(LESSONS):
    resp = requests.post(f"{BASE}/api/lessons", json=lesson)
    if resp.status_code in (200, 201):
        data = resp.json()
        print(f"  {data['id']}: {lesson['project']} / {lesson['category']} / {lesson['lesson'][:60]}...")
    else:
        print(f"  ERROR [{resp.status_code}]: {resp.text[:100]}")
    time.sleep(0.3)

# Verify
stats = requests.get(f"{BASE}/api/lessons/stats").json()
print(f"\nFinal stats: {json.dumps(stats, indent=2)}")
