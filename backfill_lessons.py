"""Backfill 16 seed lessons from the sprint spec."""
import requests, json, time

BASE = "https://metapm.rentyourcio.com"

LESSONS = [
    {
        "project": "project-methodology",
        "category": "technical",
        "lesson": "Cloud Run GFE returns 411 for POST requests without Content-Length header. All Cloud Scheduler jobs and HTTP clients posting to Cloud Run must include a non-empty message body.",
        "source_sprint": "PR-MS4-MS1",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "PR-MS4-MS1"
    },
    {
        "project": "project-methodology",
        "category": "technical",
        "lesson": "gcloud run deploy in GitHub Actions CI without explicit --set-env-vars wipes all environment variables on Cloud Run. Every CI deploy.yml must include the full --set-env-vars and --set-secrets flags.",
        "source_sprint": "AF-057",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "AF-057"
    },
    {
        "project": "project-methodology",
        "category": "technical",
        "lesson": "MetaPM API endpoint is /api/roadmap/requirements. The /api/v1/requirements path returns 404. All CC prompts must use /api/roadmap/requirements.",
        "source_sprint": "METAPM-SEED-001",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cai",
        "applied_in_sprint": "METAPM-SEED-FIXUP-001"
    },
    {
        "project": "project-methodology",
        "category": "technical",
        "lesson": "Em dashes in MetaPM API POST body fields cause JSON parse errors. Use hyphens only. Never use em dashes in any MetaPM API call body.",
        "source_sprint": "METAPM-SEED-FIXUP-001",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cai",
        "applied_in_sprint": "METAPM-SEED-FIXUP-001"
    },
    {
        "project": "project-methodology",
        "category": "process",
        "lesson": "MetaPM lifecycle requires full sequential state walk: req_created > req_approved > cai_designing > cc_prompt_ready > cc_executing > cc_complete > uat_ready > uat_pass > done. Backend returns 400 on any skipped transition. No shortcuts.",
        "source_sprint": "EFG-MS4",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "EFG-MS4"
    },
    {
        "project": "project-methodology",
        "category": "process",
        "lesson": "UAT_Template_v3.html must be copied, never recreated. CAI must produce a UAT HTML file as a named deliverable output during zccin. No file = zccin is structurally incomplete.",
        "source_sprint": "HL-REIMPORT",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "pl",
        "applied_in_sprint": "HL-REIMPORT"
    },
    {
        "project": "project-methodology",
        "category": "process",
        "lesson": "Documenting a compliance rule does not ensure compliance for stateless agents. Structural gates (required named deliverables that block completion if absent) are more reliable than behavioral instructions.",
        "source_sprint": "HL-REIMPORT",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "pl",
        "applied_in_sprint": "MP-LL-APPLY-001"
    },
    {
        "project": "harmonylab",
        "category": "technical",
        "lesson": "HarmonyLab imported 35 songs with zero individual note data. The parser captured chord symbols only. The HL-REIMPORT sprint added note-level storage via custom .mscx XML parser. Original source files were not in GCS and must be re-uploaded by PL.",
        "source_sprint": "HL-REIMPORT",
        "target": "pk.md",
        "target_file": "harmonylab/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cai",
        "applied_in_sprint": "HL-REIMPORT"
    },
    {
        "project": "harmonylab",
        "category": "technical",
        "lesson": ".mscz files are ZIP archives containing .mscx XML. Parse directly with a custom XML parser. No MuseScore CLI needed. MuseScore CLI adds 500MB to Docker image.",
        "source_sprint": "HL-REIMPORT",
        "target": "pk.md",
        "target_file": "harmonylab/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "HL-REIMPORT"
    },
    {
        "project": "artforge",
        "category": "technical",
        "lesson": "ArtForge story artifact persistence requires explicit save_to_db() call after each generation. The frontend generate button must trigger both the provider API call and the database write. Missing the DB write is the root cause of all AF persistence failures.",
        "source_sprint": "AF-MS2-FIX",
        "target": "pk.md",
        "target_file": "artforge/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cai",
        "applied_in_sprint": "AF-MS2-FIX"
    },
    {
        "project": "artforge",
        "category": "technical",
        "lesson": "No ArtForge client existed in Etymython. AF-057 created app/services/artforge_client.py from scratch using Google Cloud service-to-service ID tokens (fetch_id_token + verify_oauth2_token).",
        "source_sprint": "AF-057",
        "target": "pk.md",
        "target_file": "artforge/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "AF-057"
    },
    {
        "project": "super-flashcards",
        "category": "technical",
        "lesson": "Cross-DB queries from Super Flashcards to Etymython require explicit db_datareader grant on the Etymython DB for flashcards_user. Grant before any cross-DB sprint.",
        "source_sprint": "SF-MS2",
        "target": "pk.md",
        "target_file": "super-flashcards/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "SF-MS2"
    },
    {
        "project": "super-flashcards",
        "category": "technical",
        "lesson": "Use ElevenLabs Aria + multilingual v2 for Greek TTS in Super Flashcards. Rudy voice is English-only and is reserved for ArtForge CHICKS! narration only.",
        "source_sprint": "SF-MS2",
        "target": "pk.md",
        "target_file": "super-flashcards/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "SF-MS2"
    },
    {
        "project": "portfolio-rag",
        "category": "architecture",
        "lesson": "The deployed Portfolio RAG MCP server was filesystem + Brave Search only, not the approved ChromaDB vector RAG. PR-MS3 full rewrite was required. Never assume a deployed service matches its spec without health check verification.",
        "source_sprint": "PR-MS3",
        "target": "pk.md",
        "target_file": "portfolio-rag/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cai",
        "applied_in_sprint": "PR-MS3"
    },
    {
        "project": "pie-network-graph",
        "category": "technical",
        "lesson": "PIE Network Graph has no database. All data is in-memory. Uses Cytoscape.js not D3. Default branch is master not main. DCC CSV URL is dcc.dickinson.edu/greek-core-list.csv.",
        "source_sprint": "EFG-MS4",
        "target": "pk.md",
        "target_file": "pie-network-graph/PROJECT_KNOWLEDGE.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "EFG-MS4"
    },
    {
        "project": "project-methodology",
        "category": "technical",
        "lesson": "allow_origins=['*'] + allow_credentials=True is INVALID. Browsers reject wildcard when credentials enabled. FastAPI/Starlette silently accepts this config but all cross-origin requests fail. Always use explicit origins.",
        "source_sprint": "AF-OPS-001",
        "target": "bootstrap",
        "target_file": "project-methodology/templates/CC_Bootstrap_v1.md",
        "status": "applied",
        "proposed_by": "cc",
        "applied_in_sprint": "AF-OPS-001"
    },
]

print(f"Backfilling {len(LESSONS)} lessons...")
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
