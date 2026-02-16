"""
MetaPM Roadmap Seed Script
CC_Task_MetaPM_Roadmap_Seed — Part 2: Seed the Roadmap
Uses MetaPM API endpoints (no direct SQL needed)
"""
import requests
import json
import sys
from datetime import datetime

BASE_URL = "https://metapm.rentyourcio.com"

def api_put(path, data):
    """PUT request to MetaPM API"""
    url = f"{BASE_URL}{path}"
    r = requests.put(url, json=data, timeout=30)
    return r.status_code, r.json() if r.text else {}

def api_post(path, data):
    """POST request to MetaPM API"""
    url = f"{BASE_URL}{path}"
    r = requests.post(url, json=data, timeout=30)
    return r.status_code, r.json() if r.text else {}

def api_get(path):
    """GET request to MetaPM API"""
    url = f"{BASE_URL}{path}"
    r = requests.get(url, timeout=30)
    return r.status_code, r.json() if r.text else {}

# ============================================================
# STEP 2.1: Update project versions to match health checks
# ============================================================
# Health check results:
#   MetaPM:     2.1.5 (roadmap says 2.0.0)
#   HarmonyLab: 1.8.2 backend (roadmap says 1.5.3)
#   ArtForge:   2.2.1 (roadmap says 2.2.1 — already correct)
#   Etymython:  no version in health (roadmap says 1.2.0 — leave as-is)
#   Super-Flashcards: 2.9.0 (roadmap says 8.0.0)
#   project-methodology: no service (roadmap says 3.17.0 — leave as-is)

version_updates = [
    ("proj-mp", "2.1.5", "MetaPM"),
    ("proj-hl", "1.8.2", "HarmonyLab"),
    # ArtForge already correct at 2.2.1
    # Etymython - no version from health, leave as 1.2.0
    ("proj-sf", "2.9.0", "Super-Flashcards"),
    # project-methodology - not a service, leave as 3.17.0
]

print("=" * 60)
print("STEP 2.1: Update project versions")
print("=" * 60)
for proj_id, version, name in version_updates:
    code, resp = api_put(f"/api/projects/{proj_id}", {"current_version": version})
    status = "OK" if code in (200, 201) else f"FAIL ({code})"
    print(f"  {name}: -> {version} [{status}]")
    if code not in (200, 201):
        print(f"    Response: {json.dumps(resp, indent=2)[:200]}")

# ============================================================
# STEP 2.2: Close completed items
# ============================================================
print("\n" + "=" * 60)
print("STEP 2.2: Close completed items")
print("=" * 60)

completed_items = [
    ("req-hl-001", "HL-001 Quiz backend fix"),
    ("req-hl-002", "HL-002 Complete audio UAT"),
]

for req_id, label in completed_items:
    code, resp = api_put(f"/api/requirements/{req_id}", {"status": "done"})
    status = "OK" if code in (200, 201) else f"FAIL ({code})"
    print(f"  {label}: -> done [{status}]")
    if code not in (200, 201):
        print(f"    Response: {json.dumps(resp, indent=2)[:200]}")

# ============================================================
# STEP 2.4: Add new requirements
# ============================================================
print("\n" + "=" * 60)
print("STEP 2.4: Add new requirements")
print("=" * 60)

new_requirements = [
    # MetaPM (proj-mp)
    {"id": "req-mp-001", "project_id": "proj-mp", "code": "MP-001", "title": "GitHub Actions CI/CD", "type": "task", "priority": "P1", "status": "backlog"},
    {"id": "req-mp-002", "project_id": "proj-mp", "code": "MP-002", "title": "Seed roadmap with current state", "type": "task", "priority": "P1", "status": "in_progress"},
    {"id": "req-mp-003", "project_id": "proj-mp", "code": "MP-003", "title": "Fix handoff-requirement linkage", "type": "bug", "priority": "P1", "status": "backlog"},
    {"id": "req-mp-004", "project_id": "proj-mp", "code": "MP-004", "title": "Dashboard as morning standup view", "type": "enhancement", "priority": "P2", "status": "backlog"},

    # HarmonyLab (proj-hl)
    {"id": "req-hl-005", "project_id": "proj-hl", "code": "HL-005", "title": "MIDI P0 import fix (arpeggios)", "type": "bug", "priority": "P1", "status": "done"},
    {"id": "req-hl-006", "project_id": "proj-hl", "code": "HL-006", "title": "Analysis quality (key+chords)", "type": "bug", "priority": "P1", "status": "done"},
    {"id": "req-hl-007", "project_id": "proj-hl", "code": "HL-007", "title": "Branch fix master to main", "type": "task", "priority": "P1", "status": "backlog"},
    {"id": "req-hl-008", "project_id": "proj-hl", "code": "HL-008", "title": "Import 37 jazz standards", "type": "feature", "priority": "P2", "status": "backlog"},
    {"id": "req-hl-009", "project_id": "proj-hl", "code": "HL-009", "title": "Edit chord form dropdowns", "type": "enhancement", "priority": "P2", "status": "backlog"},
    {"id": "req-hl-010", "project_id": "proj-hl", "code": "HL-010", "title": "Default to Analysis page", "type": "enhancement", "priority": "P2", "status": "backlog"},
    {"id": "req-hl-011", "project_id": "proj-hl", "code": "HL-011", "title": "Login page version mismatch", "type": "bug", "priority": "P2", "status": "backlog"},
    {"id": "req-hl-012", "project_id": "proj-hl", "code": "HL-012", "title": "Chord granularity: 20 bars not 35", "type": "enhancement", "priority": "P2", "status": "backlog"},
    {"id": "req-hl-013", "project_id": "proj-hl", "code": "HL-013", "title": "Verify MIDI file storage location", "type": "task", "priority": "P2", "status": "backlog"},

    # ArtForge (proj-af)
    {"id": "req-af-005", "project_id": "proj-af", "code": "AF-005", "title": "Verify v2.2.2 handoff fixes", "type": "task", "priority": "P1", "status": "backlog"},
    {"id": "req-af-006", "project_id": "proj-af", "code": "AF-006", "title": "Etymython<->ArtForge content pipe", "type": "feature", "priority": "P2", "status": "backlog"},

    # Etymython (proj-em)
    {"id": "req-em-003", "project_id": "proj-em", "code": "EM-003", "title": "Shared OAuth (copy SF/AF pattern)", "type": "task", "priority": "P1", "status": "backlog"},
    {"id": "req-em-004", "project_id": "proj-em", "code": "EM-004", "title": "Etymython<->SF shared etymology", "type": "feature", "priority": "P2", "status": "backlog"},
    {"id": "req-em-005", "project_id": "proj-em", "code": "EM-005", "title": "GCP project ID clarification", "type": "task", "priority": "P2", "status": "backlog"},
    {"id": "req-em-006", "project_id": "proj-em", "code": "EM-006", "title": "Figure count verification", "type": "task", "priority": "P2", "status": "backlog"},

    # Super Flashcards (proj-sf)
    {"id": "req-sf-005", "project_id": "proj-sf", "code": "SF-005", "title": "User membership model", "type": "feature", "priority": "P2", "status": "backlog"},
    {"id": "req-sf-006", "project_id": "proj-sf", "code": "SF-006", "title": "Etymology bridge normalization", "type": "task", "priority": "P2", "status": "backlog"},

    # project-methodology (proj-pm)
    {"id": "req-pm-001", "project_id": "proj-pm", "code": "PM-001", "title": "Bootstrap prompt v1", "type": "task", "priority": "P1", "status": "done"},
    {"id": "req-pm-002", "project_id": "proj-pm", "code": "PM-002", "title": "Methodology coherence audit", "type": "task", "priority": "P1", "status": "done"},
    {"id": "req-pm-003", "project_id": "proj-pm", "code": "PM-003", "title": "Methodology cleanup execution", "type": "task", "priority": "P1", "status": "in_progress"},
    {"id": "req-pm-004", "project_id": "proj-pm", "code": "PM-004", "title": "Cross-project CI/CD standard", "type": "task", "priority": "P1", "status": "backlog"},
    {"id": "req-pm-005", "project_id": "proj-pm", "code": "PM-005", "title": "Standardize DEPLOYMENT_CHECKLIST", "type": "task", "priority": "P2", "status": "backlog"},
]

added = 0
failed = 0
for req in new_requirements:
    code, resp = api_post("/api/requirements", req)
    if code in (200, 201):
        added += 1
        print(f"  + {req['code']} {req['title']} [{req['status']}]")
    elif code == 409 or "already exists" in str(resp).lower() or "duplicate" in str(resp).lower():
        # Item already exists, try to update instead
        update_data = {k: v for k, v in req.items() if k not in ("id", "project_id", "code")}
        ucode, uresp = api_put(f"/api/requirements/{req['id']}", update_data)
        if ucode in (200, 201):
            added += 1
            print(f"  ~ {req['code']} {req['title']} [updated]")
        else:
            failed += 1
            print(f"  ! {req['code']} FAIL create ({code}) + update ({ucode}): {str(uresp)[:150]}")
    else:
        failed += 1
        print(f"  ! {req['code']} FAIL ({code}): {str(resp)[:200]}")

print(f"\n  Summary: {added} added/updated, {failed} failed")

# ============================================================
# STEP 2.5: Verify seeded data
# ============================================================
print("\n" + "=" * 60)
print("STEP 2.5: Verification")
print("=" * 60)

code, roadmap = api_get("/api/roadmap")
if code == 200:
    for proj in roadmap.get("projects", []):
        req_count = len(proj.get("requirements", []))
        status_counts = {}
        for r in proj.get("requirements", []):
            s = r.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1
        status_str = ", ".join(f"{k}:{v}" for k, v in sorted(status_counts.items()))
        print(f"  {proj.get('project_emoji', '')} {proj.get('project_name', '?')} v{proj.get('current_version', '?')} — {req_count} reqs ({status_str})")
    stats = roadmap.get("stats", {})
    print(f"\n  Total: {stats.get('total', '?')} | backlog:{stats.get('backlog', 0)} planned:{stats.get('planned', 0)} in_progress:{stats.get('in_progress', 0)} uat:{stats.get('uat', 0)} done:{stats.get('done', 0)}")
else:
    print(f"  FAIL to verify: {code}")

print("\n" + "=" * 60)
print("Done!")
print("=" * 60)
