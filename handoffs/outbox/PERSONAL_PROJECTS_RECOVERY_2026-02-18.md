## Personal Projects Recovery

Root cause: **Scenario A (filtering/data-model split)**. Personal projects were not deleted; they remained in legacy `Projects` and `/api/projects` (30 records), while the new dashboard consumed only `roadmap_projects` via `/api/roadmap/projects` (6 portfolio records), which hid personal projects from the new UI.

### What was lost
No underlying personal project records were lost from legacy storage. Visibility was lost in the new dashboard layer because `roadmap_projects` had only the 6 seeded portfolio projects.

### Recovery action taken
- Performed non-destructive recovery by inserting missing legacy personal projects into `roadmap_projects` via live API.
- Verification after recovery:
  - `/api/projects?limit=500` → `30`
  - `/api/roadmap/projects?limit=500` → `30`
  - Non-portfolio projects visible in roadmap layer → `24`
- Sample recovered projects now visible in roadmap API: `African Safari`, `Alaska inner passage`, `Cubist Art Software`, `Fly fishing Patagonia`, `Jazz Piano Development`.

### Safeguards added
- Added script `scripts/recover_personal_projects_to_roadmap.py` for repeatable, non-destructive legacy→roadmap recovery (`--dry-run` / `--apply`).
- Hardened `scripts/seed_vision_requirements.py` with additive-only safeguards:
  - explicit portfolio project presence check
  - preservation message for non-portfolio roadmap projects
  - no mutation/deletion of existing roadmap projects

### Recovery evidence
- Legacy count before/after: `30`
- Roadmap count before: `6`
- Roadmap count after: `30`
- Backup availability confirmed (successful pre-sprint backups exist, including `2026-02-16`).
