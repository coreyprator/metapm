"""
Insert ArtForge requirements AF-015 through AF-029 into MetaPM.
Data sprint — no features built. Descriptions inserted VERBATIM.
Run from MetaPM repo root. Requires internet access to MetaPM production.
"""
import urllib.request
import urllib.error
import json
import sys

BASE_URL = "https://metapm.rentyourcio.com"

AF015_DESC = """\
## AF-015: Prompt Moderation Pre-Check & Auto-Sanitize

### Problem
External AI providers (Runway, Stability) enforce content moderation on prompts. When a prompt is rejected, the user loses time and API credits, and the error message flashes too fast to diagnose. Currently there is no way to know a prompt will fail moderation until after it's submitted to the provider.

### Solution
Add an AI-powered moderation pre-check layer that evaluates prompts **before** they reach external providers. The system checks whether prompt text would pass provider moderation filters and optionally rewrites flagged content to be moderation-safe while preserving creative intent.

### Integration Points

**1. Scene Prompt Generation (automatic)**
ArtForge has an existing process that takes the voice-over script and generates scene prompts. In this pipeline:
- After scene prompts are generated from the VO script, each prompt is automatically run through the moderation pre-check
- If the "Pre-flight Check" configuration option is enabled (ON by default), flagged prompts are highlighted with specific phrases identified and suggested alternatives provided
- If the "Auto-Sanitize" configuration option is enabled, flagged prompts are automatically rewritten to be moderation-safe. The original and sanitized versions are both shown to the user for comparison
- User can accept the sanitized version or keep the original (at their own risk)

**2. Manual Prompt Editing (dynamic)**
When a user manually edits any scene prompt text:
- If Pre-flight Check preference is enabled, the edit is automatically evaluated on blur/save
- If the edited prompt would fail moderation, inline feedback appears immediately: "This prompt may be flagged by Runway. Suggested revision: [alternative]. Would you like to correct it or leave as-is?"
- If Auto-Sanitize preference is enabled, the correction is applied automatically with an undo option
- This check happens dynamically as part of the editing workflow — no separate button click required

**3. Generate-Time Final Check (safety net)**
When the user clicks any "Generate" button (image, video, SFX):
- If Pre-flight Check is enabled, one final moderation check runs before the API call
- If the prompt fails, a persistent warning is shown (not a flash toast) with the option to: (a) auto-correct and generate, (b) edit manually, or (c) generate anyway (override)
- This is the last safety net before burning API credits

### Configuration
Two checkboxes in ArtForge settings (story-level or global preference):
- **☑ Pre-flight Moderation Check** (default: ON) — Evaluate prompts against provider moderation rules before submission. Shows warnings on flagged content.
- **☑ Auto-Sanitize** (default: OFF) — Automatically rewrite flagged prompts to pass moderation. Shows original vs sanitized for user approval.

Both can be overridden per-action. When Pre-flight is OFF, no checks occur (user accepts full risk of provider rejection). When Auto-Sanitize is ON, Pre-flight is implicitly ON.

### Moderation Check Implementation
- Use OpenAI or Claude API to evaluate prompt text
- System prompt: "Evaluate whether this image/video generation prompt would pass content moderation for [provider]. Flag specific phrases likely to trigger rejection. For each flagged phrase, suggest an alternative that preserves creative intent. Providers are sensitive to: explicit violence, sexual content, real celebrity likenesses, graphic medical content, and weapons."
- Provider-aware: Runway, Stability, and other providers have slightly different moderation rules. The check should be parameterized by target provider.
- Response format: {"passes": true/false, "flags": [{"phrase": "...", "reason": "...", "suggestion": "..."}], "sanitized_prompt": "..."}

### User Experience
- Flagged phrases highlighted in amber/orange in the prompt editor
- Hover/click on a flag shows the reason and suggested alternative
- "Accept all suggestions" button for batch correction
- Persistent feedback (not flash toasts) — moderation warnings stay visible until dismissed
- Clear indicator when a prompt is "clean" (green checkmark or similar)

### Acceptance Criteria
1. Scene prompts generated from VO script are automatically pre-checked when preference is enabled
2. Manual prompt edits trigger dynamic moderation feedback on blur/save when preference is enabled
3. Generate-time final check prevents API calls to providers when prompt would fail (with override option)
4. Configuration checkboxes (Pre-flight Check ON by default, Auto-Sanitize OFF by default) control behavior
5. Flagged phrases are highlighted with specific reasons and suggested alternatives
6. User can accept suggestions individually, batch-accept, or override
7. Auto-Sanitize shows original vs sanitized side-by-side for user approval
8. Moderation check is provider-aware (different rules for Runway vs Stability)
9. Clean prompts show a positive indicator (green check or similar)
10. All moderation warnings are persistent (not flash toasts) until user takes action

### Technical Notes
- Moderation check is an async AI call — add loading indicator while checking
- Cache moderation results per prompt text to avoid redundant API calls on re-edits
- The VO→scene prompt pipeline already exists — this slots in as middleware after prompt generation
- Consider batching: if 8 scene prompts are generated at once, check all 8 in one API call
- Provider moderation rules may change over time — the system prompt should be in a config/constant, not hardcoded deep in business logic"""

REQUIREMENTS = [
    {
        "id": "req-af-015",
        "project_id": "proj-af",
        "code": "AF-015",
        "title": "Prompt Moderation Pre-Check & Auto-Sanitize",
        "description": AF015_DESC,
        "type": "feature",
        "priority": "P2",
        "status": "backlog",
    },
    {
        "id": "req-af-016",
        "project_id": "proj-af",
        "code": "AF-016",
        "title": "Video Persistence",
        "description": "Generated video clips disappear after navigating away from the story and returning. Videos must persist in the database and GCS. When a user returns to a story, all previously generated video clips should be visible and playable. Root cause: either the video URL is not being saved to the database after Runway returns the result, or the frontend is not loading saved video URLs on page load. Investigate and fix.",
        "type": "bug",
        "priority": "P1",
        "status": "backlog",
    },
    {
        "id": "req-af-017",
        "project_id": "proj-af",
        "code": "AF-017",
        "title": "SFX Assignment Persistence",
        "description": "SFX can be generated via AI prompt (works correctly) but the assignment to a scene does not persist. After generating or selecting an SFX and assigning it to a scene, leaving and returning shows no SFX assigned. The SFX audio file and its scene assignment must be saved to the database and reloaded on page load.",
        "type": "bug",
        "priority": "P1",
        "status": "backlog",
    },
    {
        "id": "req-af-018",
        "project_id": "proj-af",
        "code": "AF-018",
        "title": "Music Assignment Persistence",
        "description": "Background music can be selected from the 6-mood dropdown but the selection does not persist. After choosing a mood and assigning music, leaving and returning shows no music assigned. The music selection and scene assignment must be saved to the database and reloaded on page load. Additionally, investigate adding AI-generated music from a text prompt (similar to SFX AI generation). Research available music generation APIs (e.g., Mubert, Soundraw, or similar) and document options in PROJECT_KNOWLEDGE.md.",
        "type": "bug",
        "priority": "P1",
        "status": "backlog",
    },
    {
        "id": "req-af-019",
        "project_id": "proj-af",
        "code": "AF-019",
        "title": "Assembly Fix — Pixabay CDN 403",
        "description": "Assembly fails with \"Client error '403 Forbidden' for url 'https://cdn.pixabay.com/audio/2023/05/01/audio_d3459f14d4.mp3'\". The assembly pipeline tries to fetch music from Pixabay CDN URLs that are either expired or rate-limited. Fix: when music is assigned, download and store the audio file in GCS (like we do for SFX and VO). Assembly should reference GCS URLs, not external CDN URLs that can expire or block.",
        "type": "bug",
        "priority": "P1",
        "status": "backlog",
    },
    {
        "id": "req-af-020",
        "project_id": "proj-af",
        "code": "AF-020",
        "title": "Premiere Export — Local Media Download + Relative Paths",
        "description": "The Premiere XML export currently references GCS URLs for media files. Adobe Premiere cannot resolve these URLs. The export function must: (1) Download all referenced media files (images, video clips, VO audio, SFX audio, music) to a local folder alongside the XML. (2) Use relative paths in the XML (e.g., `./media/scene_1.png`) so that when the user moves the export folder, Premiere finds all media. (3) Package as a ZIP download containing the .xml file and a /media subfolder with all assets. This makes the export self-contained and portable. Adobe Premiere has poor folder navigation UX — the export should minimize the need for the user to manually locate files.",
        "type": "enhancement",
        "priority": "P2",
        "status": "backlog",
    },
    {
        "id": "req-af-021",
        "project_id": "proj-af",
        "code": "AF-021",
        "title": "Provider Default Memory",
        "description": "After generating an image with a provider (e.g., Stability), the provider selector resets to the first option in the list. It should default to the last provider used. Additionally, add a story-level or global preference to set a default provider for image generation and a separate default for video generation, applied across all scenes. This saves repetitive reselection when working through multiple scenes.",
        "type": "enhancement",
        "priority": "P3",
        "status": "backlog",
    },
    {
        "id": "req-af-022",
        "project_id": "proj-af",
        "code": "AF-022",
        "title": "Login / Logout Flow",
        "description": "Two issues: (1) On desktop, logging out does not prompt for a different Google account on re-login — it silently logs back in to the previous account. The logout flow should clear the OAuth session so the login screen offers account selection. (2) On iPhone, the same issue — the app caches the last account and does not offer a chance to switch users. Investigate whether this requires changes to the OAuth consent screen parameters (prompt=select_account) or clearing browser cookies.",
        "type": "bug",
        "priority": "P3",
        "status": "backlog",
    },
    {
        "id": "req-af-023",
        "project_id": "proj-af",
        "code": "AF-023",
        "title": "Seedance Video Provider Setup",
        "description": "The Seedance 2.0 video provider is listed in the UI but returns \"Seedance 2.0 API key not configured. See handoff docs for setup instructions.\" Document: (1) How to provision a Seedance API key. (2) Which GCP Secret Manager secret to create. (3) What env var the code reads. (4) Steps to test after provisioning. Add setup instructions to PROJECT_KNOWLEDGE.md. If the Seedance provider is not worth pursuing (cost, quality, availability), document that decision and remove it from the UI.",
        "type": "task",
        "priority": "P3",
        "status": "backlog",
    },
    {
        "id": "req-af-024",
        "project_id": "proj-af",
        "code": "AF-024",
        "title": "Version String Consistency",
        "description": "The app footer shows \"ArtForge v2.3.0\" while /health returns v2.3.3 (or v2.3.4 after error logging sprint). The footer version is hardcoded in the HTML template and not updated during version bumps. Fix: the footer should read the version from the same source as /health (e.g., an API call or a template variable injected at build time). All version displays (footer, /health, any \"about\" page) must be consistent after every version bump.",
        "type": "bug",
        "priority": "P3",
        "status": "backlog",
    },
    {
        "id": "req-af-025",
        "project_id": "proj-af",
        "code": "AF-025",
        "title": "Scene Splitter UX",
        "description": "The scene splitter needs a loading state indicator and should disable the button during processing. PL clicked twice because there was no visual feedback that processing was happening. Add: (1) Loading spinner or progress indicator while splitting. (2) Disable the split button during processing to prevent double-clicks. (3) Clear completion message when splitting is done.",
        "type": "enhancement",
        "priority": "P3",
        "status": "backlog",
    },
    {
        "id": "req-af-026",
        "project_id": "proj-af",
        "code": "AF-026",
        "title": "Voice-Over UX Improvements",
        "description": "Voice-over functionality works but needs UX improvements: (1) Better placement in the UI flow — currently hard to find. (2) Double-click protection on generate button. (3) Stop/play/pause (VCR) controls for playback. (4) Avatar/voice selection — ability to choose from available 11Labs voices with preview. (5) Character-level voice assignment — different characters in the story should have different voices.",
        "type": "enhancement",
        "priority": "P3",
        "status": "backlog",
    },
    {
        "id": "req-af-027",
        "project_id": "proj-af",
        "code": "AF-027",
        "title": "SFX Auto-Generate from Scene Description",
        "description": "Currently SFX requires manual prompt entry. Add an \"Auto-generate\" option that reads the scene description and automatically generates an appropriate SFX prompt. Example: if the scene description mentions \"café in Rio de Janeiro,\" auto-suggest SFX prompt \"ambient café sounds, Brazilian bossa nova music in background, coffee cups clinking.\"",
        "type": "feature",
        "priority": "P3",
        "status": "backlog",
    },
    {
        "id": "req-af-028",
        "project_id": "proj-af",
        "code": "AF-028",
        "title": "Story-Level Context / Establishing Shot",
        "description": "The AI-generated scene descriptions lack story-level context. Example: a story set in Brazil/Rio de Janeiro generated a scene with \"a cozy, dimly lit tavern with wooden beams\" — appropriate for a British pub, not Brazil. Add story-level settings that persist across all scene generations: (1) Location/setting (e.g., \"Rio de Janeiro, Brazil\"). (2) Era/time period (e.g., \"contemporary,\" \"1960s\"). (3) Mood/atmosphere (e.g., \"tropical, vibrant, warm\"). (4) Visual style notes (e.g., \"bright colors, outdoor settings\"). These settings should be injected into every scene prompt as context, ensuring the AI generates scenes consistent with the story world. Consider an \"establishing shot\" first scene that sets the visual tone.",
        "type": "feature",
        "priority": "P2",
        "status": "backlog",
    },
    {
        "id": "req-af-029",
        "project_id": "proj-af",
        "code": "AF-029",
        "title": "Top Navigation / Breadcrumb",
        "description": "To return to the main story list from a storyboard, the user must click the browser back arrow multiple times. Add proper navigation: (1) Top nav with \"Your Collections\" → \"Storyboard\" breadcrumb trail. (2) One-click return to the story list from any storyboard view. (3) Consistent nav bar across all views.",
        "type": "feature",
        "priority": "P3",
        "status": "backlog",
    },
]


def post_requirement(req: dict) -> dict:
    url = f"{BASE_URL}/api/requirements"
    body = json.dumps(req).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            return {"status": resp.status, "body": json.loads(resp.read())}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        return {"status": e.code, "error": body_text}
    except Exception as e:
        return {"status": 0, "error": str(e)}


def main():
    print(f"Inserting {len(REQUIREMENTS)} ArtForge requirements into MetaPM...")
    print()

    successes = []
    failures = []

    for req in REQUIREMENTS:
        code = req["code"]
        result = post_requirement(req)
        status = result.get("status")

        if status == 201:
            print(f"  OK  {code}: {req['title']}")
            successes.append(code)
        elif status == 400 and "already exists" in result.get("error", ""):
            print(f"  SKIP {code}: already exists")
            successes.append(code)  # Not an error — idempotent
        else:
            print(f"  FAIL {code}: HTTP {status} — {result.get('error', result.get('body', ''))[:200]}")
            failures.append(code)

    print()
    print(f"Results: {len(successes)} inserted/skipped, {len(failures)} failed")
    if failures:
        print(f"FAILURES: {', '.join(failures)}")
        sys.exit(1)
    else:
        print("All requirements inserted successfully.")


if __name__ == "__main__":
    main()
