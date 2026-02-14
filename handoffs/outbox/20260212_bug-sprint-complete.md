| Field | Value |
|-------|-------|
| ID | HO-BS01 |
| Project | 🔴 MetaPM (multi-project sprint report) |
| Task | Bug Sprint — 5 bugs across 4 projects |
| Status | COMPLETE |
| Date | 2025-02-12 |
| Sprint Scope | MetaPM, ArtForge, Etymython |

---

## Bug Sprint Summary

All 5 bugs from the prioritized backlog have been resolved, committed, pushed, and deployed.

### Results

| HO ID | Bug ID | Project | Description | Priority | Commit | Deploy | Status |
|-------|--------|---------|-------------|----------|--------|--------|--------|
| HO-MP01 | META BUG-012 | 🔴 MetaPM | Selected count doesn't decrement after bulk status change | P1 | `0b67fd8` | `metapm-v2-00052-szt` | ✅ COMPLETE |
| HO-MP02 | META BUG-011 | 🔴 MetaPM | Dashboard doesn't persist last-viewed tab | P2 | `0b67fd8` | `metapm-v2-00052-szt` | ✅ COMPLETE |
| HO-AF01 | AF BUG-002 | 🟠 ArtForge | AI provider selection not saved to collection | P1 | `3fd894d` | `artforge-00077-vx4` | ✅ COMPLETE |
| HO-EM01 | EM BUG-001 | 🟣 Etymython | NULL etymology ID for some figures | P2 | N/A | N/A | ✅ Already fixed (audit: 0 missing) |
| HO-EM02 | EM BUG-002 | 🟣 Etymython | Unicode corruption in Greek text (VARCHAR) | P1 | `9b6e3b6` | `etymython-00172-ws4` | ✅ COMPLETE |

---

### Fix Details

#### HO-MP01 — META BUG-012: Selected count doesn't hit 0
- **Root Cause**: `bulkUpdateStatus()` called `selectedTaskIds.clear()` then `loadTasks()` but never invoked `updateSelectionUI()` to refresh the counter display.
- **Fix**: Added `updateSelectionUI()` call after `selectedTaskIds.clear()` in `bulkUpdateStatus()` (~line 1754 of `static/dashboard.html`).
- **Files Changed**: `static/dashboard.html`

#### HO-MP02 — META BUG-011: Persist last-viewed tab
- **Root Cause**: `setDefaultTab()` hardcoded `'tasks'` view on every page load.
- **Fix**: (1) Added `localStorage.setItem('metapm-activeTab', view)` at end of `switchView()` to persist tab choice. (2) Rewrote `setDefaultTab()` to restore from localStorage, falling back to `'tasks'`.
- **Files Changed**: `static/dashboard.html`

#### HO-AF01 — AF BUG-002: AI provider not saved
- **Root Cause**: Frontend schema accepted `providers` but the `Collection` DB model had no column for it — data was silently dropped on every save.
- **Fix**: 
  1. Added `providers = Column(NVARCHAR(500), nullable=True, default='["dalle3"]')` to `Collection` model (`app/models.py`)
  2. Persisted `providers` as JSON in collection creation route (`app/routers/collections.py`)
  3. Added `providers` to response schema (`app/schemas.py`)
  4. Updated `gallery.html` to hydrate localStorage from API response on collection load
  5. Ran DB migration: `ALTER TABLE collections ADD providers NVARCHAR(500) NULL`
- **Files Changed**: `app/models.py`, `app/routers/collections.py`, `app/schemas.py`, `frontend/gallery.html`
- **DB Migration**: `ALTER TABLE collections ADD providers NVARCHAR(500) NULL` — confirmed 11 columns including `providers`

#### HO-EM01 — EM BUG-001: NULL etymology IDs
- **Finding**: Audit endpoint reports `missing_etymologies_count: 0` — all 70 figures have etymologies. Bug was already resolved in a prior session.
- **No action required.**

#### HO-EM02 — EM BUG-002: Unicode Greek corruption
- **Root Cause**: All text columns were `VARCHAR` (single-byte encoding) which maps Greek characters to `?`. Needed `NVARCHAR` (UTF-16) for Greek text storage.
- **Fix (3 parts)**:
  1. **Model fix**: Changed all `String()`→`Unicode()` and `Text`→`UnicodeText` in `app/models.py` (20 lines, 17 columns across 4 tables)
  2. **DB migration**: Ran `ALTER TABLE ... ALTER COLUMN ... NVARCHAR(...)` for all 17 columns — confirmed via `INFORMATION_SCHEMA.COLUMNS`
  3. **Data regeneration**: 8 figures had corrupted `fun_facts.content` with `?????` where Greek should be. Used `POST /api/v1/content/admin/figures/{id}/regenerate-fun-facts?dry_run=false` to delete 116 corrupted records and regenerate 32 clean ones.
- **Files Changed**: `app/models.py`, `migrate_nvarchar.sql`
- **Figures Regenerated**: Ouranos, Titan, Dionysus, Odysseus, Rhea, Hyperion, Theia, Coeus
- **Post-fix Audit**: 0 corruption remaining (46 flagged items are false positives — valid Greek within English text)

---

### Deployment Verification

| Project | Service | Revision | Health |
|---------|---------|----------|--------|
| MetaPM | `metapm-v2` | `metapm-v2-00052-szt` | Serving 100% |
| ArtForge | `artforge` | `artforge-00077-vx4` | Serving 100% |
| Etymython | `etymython` | `etymython-00172-ws4` | Serving 100% |

---

### Remaining Backlog (Not in this sprint)

**Features deferred to future sprints:**
- ArtForge: 5 features (REQ-004 Character Sheets, Video Gen, SDXL, Pricing, Gallery Sort)
- Etymython: 3 features (Cognate Links, Semantic Word Graph, Mobile UX)
- MetaPM: 4 features (Handoff Bridge Tab, Voice Memo, AI Assistant, Methodology Review)
- Super-Flashcards: 3 features (Cognate Links cross-project, Landing Page, Mobile)
- project-methodology: 2 features (Methodology Review, Git Commit Process Update)

**ArtForge Status UAT** for STARTED items (Character Sheets, Video Gen) — still pending, to be created.

---

*Generated by Conductor agent — Bug Sprint session 2025-02-12*
*Handoff Bridge: MetaPM outbox → GCS backup*
