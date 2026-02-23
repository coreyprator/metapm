# POST UAT Results to MetaPM — Run from PowerShell
# All 3 UATs: Super Flashcards, ArtForge, HarmonyLab

# ============================================================
# 1. SUPER FLASHCARDS v3.0.1
# ============================================================
$sfBody = @{
    project_name = "Super Flashcards"
    version = "3.0.1"
    results_text = @"
[Super Flashcards] v3.0.1 UAT: Sprint 9 Rework
Date: 2/22/2026 | Rev: super-flashcards-00299-6cs
Reqs: SF-005, SF-007, SF-008, SF-013
Summary: 7 passed, 1 failed, 5 pending

[SM-01] PASS: Version v3.0.1 confirmed, no mismatch. Console: IMG resource load error on error-tracker.js.
[SM-02] PASS: Cards visible, pronunciation works.
[SR-01] PASS: Study mode accessible. 474 cards due.
[SR-02] FAIL: No SRS sorting found. SF-005 set back to backlog. Needs membership model.
[SR-03] PENDING: No rating buttons on cards. PL questions whether req exists.
[PD-01] PASS: Progress page exists. Needs membership to be useful. 1586 cards, 0 mastered.
[PD-02] PASS: Stats present: total, due, mastered, streak, by-language table.
[DIF-01] PASS: Difficulty dropdown visible. All cards unrated.
[PIE-01] PASS: PIE root visible with amber highlight. Example: *ghai- to rejoice.
[PIE-02] PENDING: Spot check not done. New req: PIE pronunciation play button.
[REG-01] PENDING: New req: language reassignment in edit modal. Found Greek word in English.

New Requirements:
- SF-005 back to backlog (SRS needs membership model)
- New: PIE root pronunciation play button
- New: Language reassignment (move card between languages)
- Bug: error-tracker.js IMG resource load failure
"@
    linked_requirements = "SF-005, SF-007, SF-008, SF-013"
    notes = "PL UAT 2/22/2026. SF-005 SRS reverted to backlog. Three new reqs captured."
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "https://metapm.rentyourcio.com/api/uat/submit" -Method POST -ContentType "application/json" -Body $sfBody
Write-Host "`n--- Super Flashcards posted ---`n"

# ============================================================
# 2. ARTFORGE v2.3.3
# ============================================================
$afBody = @{
    project_name = "ArtForge"
    version = "2.3.3"
    results_text = @"
[ArtForge] v2.3.3 UAT: Runway Hotfix + Full Pipeline
Date: 2/22/2026 | Rev: artforge-00104-dq4
Reqs: AF-007, AF-009, AF-010, AF-011, AF-013
Summary: 11 passed, 5 failed, 1 skipped, 1 pending

[SM-01] SKIP: Health should be machine test. Footer shows v2.3.0, inconsistent with release.
[SM-02] FAIL: Desktop works. Logout doesn't prompt for userid. iPhone caches last account.
[IMG-01] PASS: Image generation works. New req: default to last provider used.
[IMG-02] PASS: Radio buttons confirmed.
[VID-01] PASS: Generate Video button visible.
[VID-02] PASS: Runway selectable, duration dropdown works.
[VID-03] PASS: Runway video generated successfully (Scene 2).
[VID-04] FAIL: Video disappeared after leaving and returning to story.
[VO-01] PASS: Voice-over works.
[SFX-01] PASS: SFX panel visible, dropdown populated.
[SFX-02] FAIL: SFX assignment doesn't persist. AI Generate works but doesn't save.
[MUS-01] FAIL: Music dropdown exists but doesn't persist. New req: AI generate music from prompt.
[ASM-01] PASS: Assemble button visible.
[ASM-02] FAIL: Assembly failed: 403 Forbidden on Pixabay CDN music URL.
[PRE-01] PASS: Export button visible.
[PRE-02] PENDING: XML exported but Premiere couldn't import. Files use GCS URLs not local paths.
[REG-01] PASS: Story creation and scene splitter work.
[REG-02] PASS: Existing stories load, CRUD works. New req: better top nav (Collections/Storyboard).

New Requirements:
- Default provider memory (last used provider per image/video)
- Seedance provider setup instructions
- Video persistence (clips disappear after leaving story)
- SFX persistence fix
- Music persistence fix + AI music generation from prompt
- Premiere export: download media locally, use local paths
- Scene splitter: loading state + disable during processing
- Voice-over: UI placement, double-click protection, avatar selection, VCR controls
- SFX: auto-generate prompt from scene description
- Establishing shot / story-level setting (location, mood, era)
- Scene context: AI generated dark pub for Brazil story
- Top navigation: Collections / Storyboard breadcrumb
- Login: prompt for userid on logout/re-login
"@
    linked_requirements = "AF-007, AF-009, AF-010, AF-011, AF-013"
    notes = "PL UAT 2/22/2026. Runway confirmed working (Scene 2). 5 fails mostly persistence issues. 13 new reqs captured."
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "https://metapm.rentyourcio.com/api/uat/submit" -Method POST -ContentType "application/json" -Body $afBody
Write-Host "`n--- ArtForge posted ---`n"

# ============================================================
# 3. HARMONYLAB v1.8.4
# ============================================================
$hlBody = @{
    project_name = "HarmonyLab"
    version = "1.8.4"
    results_text = @"
[HarmonyLab] v1.8.4 UAT: Rework Sprint
Date: 2/22/2026 | BE Rev: harmonylab-00087-fw9 | FE Rev: harmonylab-frontend-00059-ctf
Reqs: HL-008, HL-009, HL-014, HL-018
Summary: 10 passed, 2 failed, 4 skipped, 2 pending

[SM-01] PENDING: Shows v1.8.5 (error logging sprint bumped). Health is a machine test.
[SM-02] PASS: App loads, login works, song list visible. No membership prompt.
[IMP-01] PASS: MIDI import works, no crash/logout.
[IMP-02] PASS: MIDI import creates song with chords.
[IMP-03] FAIL: .mscz files consistently show 'No chord symbols detected'. Reads header (key, time sig, tempo) but derives 0 chords. Import problem specific to MuseScore format.
[IMP-04] PASS: Bad file (.pdf) shows clear error message.
[CHD-01] FAIL: Chord edit modal still has FREE TEXT input, NOT dropdowns. Root/Quality/Extension/Bass dropdowns were NOT implemented.
[CHD-02] SKIP: Blocked by CHD-01.
[CHD-03] SKIP: Blocked by CHD-01.
[CHD-04] SKIP: Blocked by CHD-01.
[CHD-05] PENDING: Blocked by CHD-01.
[DIAG-01] PASS: Import diagnostics present. A Whiter Shade of Pale shows key detection, ii-V-I patterns, confidence.
[DIAG-02] SKIP: Blocked by IMP-03 (.mscz parsing issue).
[ERR-01] PASS: Error toasts working, not alert() dialogs.
[STD-01] PASS: Jazz standards visible. All songs default to Jazz genre.
[BAT-01] PASS: Batch import works, handles duplicates.
[REG-01] PASS: Existing songs work in analysis + quiz.
[REG-02] PASS: Analysis is default view.

Critical Issues:
- CHD-01: Chord dropdowns NOT implemented. CC claimed done but modal still has free text.
- IMP-03: .mscz harmonic analysis returns 0 chords. Works for .mid and .musicxml.

New Requirements:
- Genre variety (not just Jazz default)
- Status bar with song count totals
"@
    linked_requirements = "HL-008, HL-009, HL-014, HL-018"
    notes = "PL UAT 2/22/2026. CHD-01 CRITICAL: chord dropdowns not implemented despite CC claiming done. .mscz parser returns 0 chords. 10 pass, 2 fail, 4 skip."
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "https://metapm.rentyourcio.com/api/uat/submit" -Method POST -ContentType "application/json" -Body $hlBody
Write-Host "`n--- HarmonyLab posted ---`n"

Write-Host "============================================================"
Write-Host "All 3 UATs posted. Verify at https://metapm.rentyourcio.com"
Write-Host "============================================================"
