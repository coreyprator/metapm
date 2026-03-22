"""
UAT Page Generator — MP-UAT-GEN
Generates UAT HTML pages from handoff data and requirements.
"""
import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional
from html import escape

logger = logging.getLogger(__name__)

# EG06: Project display name lookup — prevents None crash and shows correct display names
PROJECT_DISPLAY_NAMES = {
    'proj-mp': 'MetaPM',
    'proj-sf': 'Super Flashcards',
    'proj-hl': 'HarmonyLab',
    'proj-af': 'ArtForge',
    'proj-em': 'Etymython',
    'proj-efg': 'Etymology Graph',
    'proj-pr': 'Portfolio RAG',
    'proj-pa': 'Personal Assistant',
    'proj-pm': 'project-methodology',
    'MetaPM': 'MetaPM',
    'HarmonyLab': 'HarmonyLab',
    'Super Flashcards': 'Super Flashcards',
    'Super-Flashcards': 'Super Flashcards',
    'Etymology Graph': 'Etymology Graph',
    'Etymology Graph Service': 'Etymology Graph',
}


def resolve_project_name(raw: str | None) -> str:
    """Safely resolve any project identifier to a display name. Never crashes."""
    if not raw:
        return 'Unknown Project'
    return PROJECT_DISPLAY_NAMES.get(raw, raw.replace('proj-', '').replace('-', ' ').title())


# Project emoji mapping
PROJECT_EMOJIS = {
    "metapm": "\U0001f534",       # red circle
    "etymython": "\U0001f7e3",    # purple circle
    "super-flashcards": "\U0001f7e1",  # yellow circle
    "artforge": "\U0001f7e0",     # orange circle
    "harmonylab": "\U0001f535",   # blue circle
    "pie-network-graph": "\U0001f537",  # blue diamond
    "portfolio-rag": "\u26aa",    # white circle
    "project-methodology": "\U0001f7e2",  # green circle
}

# Project accent colors
PROJECT_COLORS = {
    "metapm": "#ef4444",
    "etymython": "#a855f7",
    "super-flashcards": "#eab308",
    "artforge": "#f97316",
    "harmonylab": "#3b82f6",
    "pie-network-graph": "#06b6d4",
    "portfolio-rag": "#6b7280",
    "project-methodology": "#22c55e",
}

# Category badge colors
CATEGORY_COLORS = {
    "acceptance": "#3b82f6",      # blue
    "bug_fix": "#ef4444",         # red
    "risk_check": "#f97316",      # orange
    "regression": "#eab308",      # yellow
    "smoke": "#6b7280",           # gray
    "deploy_verify": "#22c55e",   # green
    "cai_focus": "#a855f7",       # purple
}

CATEGORY_LABELS = {
    "deploy_verify": "Deploy Verification",
    "smoke": "Smoke Tests",
    "acceptance": "Acceptance Criteria",
    "bug_fix": "Bug Fix Verification",
    "cai_focus": "CAI Focus Areas",
    "risk_check": "Risk Checks",
    "regression": "Regression Tests",
}


def parse_acceptance_criteria(description: Optional[str]) -> List[str]:
    """Extract acceptance criteria from requirement description text."""
    if not description:
        return []

    criteria = []
    lines = description.split('\n')
    for line in lines:
        line = line.strip()
        # Match checklist items: "- [ ] ...", "- [x] ..."
        m = re.match(r'^-\s*\[[ x]\]\s*(.+)', line, re.IGNORECASE)
        if m:
            criteria.append(m.group(1).strip())
            continue
        # Match numbered items: "1. ...", "2) ..."
        m = re.match(r'^\d+[.)]\s+(.+)', line)
        if m:
            criteria.append(m.group(1).strip())
            continue
        # Match "AC:" prefix lines
        m = re.match(r'^AC\s*:\s*(.+)', line, re.IGNORECASE)
        if m:
            criteria.append(m.group(1).strip())
            continue
        # Match bullet items with meaningful content (not headers/blank)
        m = re.match(r'^[-*]\s+(.{10,})', line)
        if m and not line.startswith('- **'):
            criteria.append(m.group(1).strip())
            continue

    return criteria


def generate_test_cases(
    work_items: List[Dict],
    project: str,
    version: str,
    cai_review: Optional[Dict] = None,
    deploy_url: Optional[str] = None
) -> List[Dict]:
    """Generate test cases from requirements and CAI review data."""
    cases = []

    # MP-UAT-PROJTYPE-001: skip deploy/smoke tests for GitHub repo URLs
    is_github_repo = "github.com" in (deploy_url or "").lower()

    if is_github_repo:
        cases.append({
            "id": "DV-01",
            "category": "deploy_verify",
            "title": f"Health endpoint returns version {version}",
            "expected": f"GET /health returns version: {version}",
            "req_code": None,
            "status": "skipped",
            "notes": "Non-app project (GitHub repo URL detected) — deploy verification not applicable."
        })
        cases.append({
            "id": "SM-01",
            "category": "smoke",
            "title": "Application loads without console errors",
            "expected": "No JS errors in browser console on main page load",
            "req_code": None,
            "status": "skipped",
            "notes": "Non-app project (GitHub repo URL detected) — smoke test not applicable."
        })
    else:
        # ALWAYS: deploy verify
        cases.append({
            "id": "DV-01",
            "category": "deploy_verify",
            "title": f"Health endpoint returns version {version}",
            "expected": f"GET /health returns version: {version}",
            "req_code": None
        })

        # ALWAYS: smoke
        cases.append({
            "id": "SM-01",
            "category": "smoke",
            "title": "Application loads without console errors",
            "expected": "No JS errors in browser console on main page load",
            "req_code": None
        })

    # For each requirement work item
    for i, item in enumerate(work_items):
        req_code = item.get("code", f"REQ-{i+1:02d}")
        title = item.get("title", "")
        description = item.get("description", "")
        item_type = item.get("type", "feature")

        # Parse acceptance criteria from description
        criteria = parse_acceptance_criteria(description)

        if criteria:
            for j, criterion in enumerate(criteria):
                cases.append({
                    "id": f"AC-{i+1:02d}-{j+1:02d}",
                    "category": "acceptance",
                    "title": criterion[:200],
                    "expected": f"Acceptance criterion for {req_code} is met",
                    "req_code": req_code
                })
        else:
            # No parseable criteria - add generic test from title
            cases.append({
                "id": f"AC-{i+1:02d}-01",
                "category": "acceptance",
                "title": f"Verify: {title[:180]}",
                "expected": f"Requirement {req_code} is satisfied",
                "req_code": req_code
            })

        # Bug reqs get regression test
        if item_type == "bug":
            cases.append({
                "id": f"BF-{i+1:02d}",
                "category": "bug_fix",
                "title": f"Verify fix: {title[:150]}",
                "expected": "Bug is resolved. No regression in related functionality.",
                "req_code": req_code
            })

    # CAI review contributions
    if cai_review:
        for j, area in enumerate(cai_review.get("focus_areas", [])):
            cases.append({
                "id": f"CF-{j+1:02d}",
                "category": "cai_focus",
                "title": str(area)[:200],
                "expected": "Focus area verified as working correctly",
                "req_code": None
            })
        for j, risk in enumerate(cai_review.get("risks", [])):
            cases.append({
                "id": f"RC-{j+1:02d}",
                "category": "risk_check",
                "title": f"Risk check: {str(risk)[:180]}",
                "expected": "Risk scenario tested, no issues found",
                "req_code": None
            })
        for j, zone in enumerate(cai_review.get("regression_zones", [])):
            cases.append({
                "id": f"RG-{j+1:02d}",
                "category": "regression",
                "title": f"Regression: {str(zone)[:180]} still works correctly",
                "expected": "Existing functionality unaffected",
                "req_code": None
            })

    return cases


def render_uat_html(
    uat_id: str,
    project: str,
    sprint_code: Optional[str],
    pth: Optional[str],
    version: Optional[str],
    deploy_url: Optional[str],
    handoff_id: str,
    test_cases: List[Dict],
    linked_requirements: List[str],
    feature_title: Optional[str] = None
) -> str:
    """Render a complete UAT HTML page matching UAT_Template_v3 visual pattern."""
    emoji = PROJECT_EMOJIS.get(project, "")
    color = PROJECT_COLORS.get(project, "#6366f1")
    project_display = resolve_project_name(project)
    if feature_title:
        title = f"{emoji} {feature_title}"
    else:
        title = f"{emoji} {project_display} v{version or '?'}"
        if sprint_code:
            title += f" - UAT: {sprint_code}"
    subtitle_parts = []
    if sprint_code:
        subtitle_parts.append(f"Sprint: {sprint_code}")
    if pth:
        subtitle_parts.append(f"PTH: {pth}")
    subtitle = " | ".join(subtitle_parts) if subtitle_parts else "UAT Checklist"

    health_url = ""
    if deploy_url:
        base = deploy_url.rstrip("/")
        health_url = f"{base}/health"

    handoff_url = f"https://metapm.rentyourcio.com/mcp/handoffs/{handoff_id}/content"

    # Group test cases by category
    category_order = ["deploy_verify", "smoke", "acceptance", "bug_fix",
                      "cai_focus", "risk_check", "regression"]
    grouped = {}
    for tc in test_cases:
        cat = tc.get("category", "acceptance")
        grouped.setdefault(cat, []).append(tc)

    # Build sections HTML
    sections_html = ""
    section_num = 0
    for cat in category_order:
        if cat not in grouped:
            continue
        section_num += 1
        items = grouped[cat]
        cat_label = CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())
        cat_color = CATEGORY_COLORS.get(cat, "#6366f1")

        items_html = ""
        for tc in items:
            tc_id = escape(tc["id"])
            tc_title = escape(tc["title"])
            tc_expected = escape(tc.get("expected", ""))
            req_tag = ""
            if tc.get("req_code"):
                req_tag = f'<span class="req-tag">{escape(tc["req_code"])}</span>'

            items_html += f'''
        <div class="test-item" data-test="{tc_id}" data-reqs="{escape(tc.get('req_code','') or '')}">
            <div class="test-row">
                <div class="test-content">
                    <span class="test-label">{tc_title}{req_tag}</span>
                    <span class="expected">-> {tc_expected}</span>
                </div>
                <div class="test-buttons">
                    <button class="btn btn-pass" onclick="setResult(this,'pass')">Pass</button>
                    <button class="btn btn-fail" onclick="setResult(this,'fail')">Fail</button>
                    <button class="btn btn-skip" onclick="setResult(this,'skip')">Skip</button>
                </div>
            </div>
            <div class="notes-container">
                <div class="notes-label">Notes</div>
                <textarea class="notes-input" placeholder=""></textarea>
            </div>
            <div class="media-row">
                <div class="paste-zone" contenteditable="true" data-paste-target="true">Ctrl+V screenshot</div>
            </div>
        </div>'''

        sections_html += f'''
    <section>
        <h2 style="border-color:{cat_color}"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{cat_color};margin-right:8px"></span>{section_num}. {cat_label} ({len(items)})</h2>
        {items_html}
    </section>'''

    linked_reqs_json = json.dumps(linked_requirements)
    uat_page_url = f"https://metapm.rentyourcio.com/uat/{uat_id}"

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(title)}</title>
    <style>
        :root {{
            --bg-primary: #1a1a2e;
            --bg-secondary: #252538;
            --accent: {color};
            --accent-success: #22c55e;
            --accent-danger: #ef4444;
            --accent-skip: #6b7280;
            --text-primary: #e5e5e5;
            --text-muted: #9ca3af;
            --border-color: #3a3a52;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }}
        header {{
            background: linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent), black 15%));
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 24px;
        }}
        header h1 {{ font-size: 1.4rem; margin-bottom: 8px; }}
        header p {{ opacity: 0.9; font-size: 0.9rem; }}
        .meta {{ display: flex; gap: 16px; flex-wrap: wrap; margin-top: 12px; font-size: 0.85rem; }}
        .meta span {{ background: rgba(255,255,255,0.15); padding: 4px 10px; border-radius: 4px; }}
        .url-link {{ display: block; background: #0f172a; padding: 10px 14px; border-radius: 6px; margin: 10px 0 20px 0; font-family: monospace; font-size: 0.85rem; }}
        .url-link a {{ color: color-mix(in srgb, var(--accent), white 40%); text-decoration: none; }}
        .url-link a:hover {{ text-decoration: underline; }}
        section {{ background: var(--bg-secondary); border-radius: 8px; padding: 20px; margin-bottom: 16px; }}
        section h2 {{ color: color-mix(in srgb, var(--accent), white 40%); font-size: 1.1rem; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid var(--accent); }}
        .test-item {{ padding: 16px 0; border-bottom: 1px solid var(--border-color); }}
        .test-item:last-child {{ border-bottom: none; }}
        .test-row {{ display: flex; align-items: flex-start; gap: 12px; }}
        .test-content {{ flex: 1; }}
        .test-label {{ font-weight: 500; display: block; margin-bottom: 4px; }}
        .expected {{ color: #a78bfa; font-size: 0.85rem; font-style: italic; }}
        .req-tag {{ display: inline-block; font-size: 0.7rem; background: rgba(239,68,68,0.25); color: #fca5a5; padding: 1px 6px; border-radius: 3px; margin-left: 6px; vertical-align: middle; }}
        .test-buttons {{ display: flex; gap: 6px; flex-shrink: 0; }}
        .btn {{ padding: 6px 14px; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; font-size: 0.85rem; transition: all 0.15s; }}
        .btn-pass {{ background: #166534; color: #bbf7d0; }}
        .btn-pass:hover, .btn-pass.selected {{ background: var(--accent-success); color: white; }}
        .btn-fail {{ background: #991b1b; color: #fecaca; }}
        .btn-fail:hover, .btn-fail.selected {{ background: var(--accent-danger); color: white; }}
        .btn-skip {{ background: #374151; color: #d1d5db; }}
        .btn-skip:hover, .btn-skip.selected {{ background: var(--accent-skip); color: white; }}
        .test-item.passed .test-label {{ color: #4ade80; }}
        .test-item.passed .test-label::before {{ content: "\\2713 "; }}
        .test-item.failed .test-label {{ color: #f87171; }}
        .test-item.failed .test-label::before {{ content: "\\2717 "; }}
        .test-item.skipped .test-label {{ color: #9ca3af; }}
        .test-item.skipped .test-label::before {{ content: "\\25CB "; }}
        .notes-container {{ margin-top: 10px; }}
        .notes-label {{ font-size: 0.8rem; color: var(--text-muted); margin-bottom: 4px; }}
        .notes-input {{ width: 100%; padding: 8px 10px; background: #1e1e32; border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary); font-family: inherit; font-size: 0.9rem; resize: vertical; min-height: 40px; }}
        .notes-input:focus {{ outline: none; border-color: var(--accent); }}
        .media-row {{ display: flex; gap: 8px; align-items: center; margin-top: 8px; flex-wrap: wrap; }}
        .paste-zone {{ padding: 6px 10px; background: #1e1e32; border: 1px dashed var(--border-color); border-radius: 4px; font-size: 0.75rem; color: var(--text-muted); cursor: text; min-width: 140px; }}
        .paste-zone:focus {{ outline: none; border-color: var(--accent); }}
        .paste-zone.has-image {{ border-color: var(--accent-success); border-style: solid; }}
        .media-thumb {{ max-width: 120px; max-height: 80px; border-radius: 4px; margin-top: 4px; cursor: pointer; }}
        .general-notes {{ background: #1e2a3f; border: 2px solid #8b5cf6; border-radius: 8px; padding: 20px; margin-top: 24px; }}
        .general-notes h3 {{ color: #a78bfa; margin-bottom: 12px; }}
        .general-notes-input {{ width: 100%; min-height: 80px; padding: 12px; background: #1e1e32; border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary); font-size: 0.9rem; resize: vertical; }}
        .summary {{ background: #1e1e32; border: 2px solid var(--accent); border-radius: 8px; padding: 20px; margin-top: 24px; }}
        .summary h3 {{ margin-bottom: 16px; }}
        .summary-stats {{ display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }}
        .stat {{ padding: 12px 20px; border-radius: 6px; font-weight: bold; text-align: center; }}
        .stat.total {{ background: var(--accent); }}
        .stat.passed {{ background: var(--accent-success); }}
        .stat.failed {{ background: #991b1b; }}
        .stat.skipped {{ background: var(--accent-skip); }}
        .overall-result {{ padding: 16px; border-radius: 8px; text-align: center; margin-top: 16px; }}
        .overall-result.pending {{ background: #374151; border: 2px dashed #6b7280; }}
        .overall-result.pass {{ background: #166534; border: 2px solid var(--accent-success); }}
        .overall-result.fail {{ background: #991b1b; border: 2px solid #ef4444; }}
        .overall-buttons {{ display: flex; gap: 12px; justify-content: center; margin-top: 12px; }}
        .overall-btn {{ padding: 10px 24px; border: none; border-radius: 6px; font-size: 1rem; font-weight: 600; cursor: pointer; }}
        .overall-btn.approve {{ background: var(--accent-success); color: white; }}
        .overall-btn.reject {{ background: #991b1b; color: white; }}
        .export-bar {{ text-align: center; margin-top: 24px; display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }}
        .export-btn {{ padding: 12px 32px; border: none; border-radius: 8px; font-size: 15px; cursor: pointer; font-weight: 600; }}
        .copy-btn {{ background: var(--accent); color: white; }}
        .submit-btn {{ background: var(--accent-success); color: white; }}
        .gen-badge {{ display: inline-block; font-size: 0.7rem; background: rgba(99,102,241,0.3); color: #a5b4fc; padding: 2px 8px; border-radius: 3px; margin-top: 8px; }}
    </style>
</head>
<body>
    <header>
        <h1>{escape(title)}</h1>
        <p>{escape(subtitle)}</p>
        <div class="meta">
            <span>Version: {escape(version or '?')}</span>
            <span id="test-date"></span>
            <span><a href="{escape(handoff_url)}" style="color:white;text-decoration:none">View Handoff</a></span>
        </div>
        <div class="gen-badge">Auto-generated by MetaPM UAT Engine</div>
    </header>

    <div class="url-link">
        <strong>Production:</strong> <a href="{escape(deploy_url or '')}" target="_blank">{escape(deploy_url or 'N/A')}</a><br>
        <strong>Health:</strong> <a href="{escape(health_url)}" target="_blank">{escape(health_url or 'N/A')}</a>
    </div>

    {sections_html}

    <div class="general-notes">
        <h3>General Notes</h3>
        <textarea id="general-notes" class="general-notes-input" placeholder="Any observations, issues found, suggestions..."></textarea>
    </div>

    <div class="summary">
        <h3>Results Summary</h3>
        <div class="summary-stats">
            <div class="stat total">Total: <span id="total-count">0</span></div>
            <div class="stat passed">Pass: <span id="pass-count">0</span></div>
            <div class="stat failed">Fail: <span id="fail-count">0</span></div>
            <div class="stat skipped">Skip: <span id="skip-count">0</span></div>
        </div>
        <div class="overall-result pending" id="overall-result">
            <h4>Overall Result</h4>
            <p style="margin-bottom:12px;opacity:0.8;">{escape(title)} approved?</p>
            <div class="overall-buttons">
                <button class="overall-btn approve" onclick="setOverall('pass')">APPROVED</button>
                <button class="overall-btn reject" onclick="setOverall('fail')">NEEDS FIXES</button>
            </div>
        </div>
    </div>

    <div class="export-bar">
        <button class="export-btn copy-btn" onclick="copyResults()">Copy Results</button>
        <button class="export-btn submit-btn" id="submit-btn" onclick="submitToMetaPM()">Submit to MetaPM</button>
    </div>

    <script>
        const UAT_CONFIG = {{
            project: {json.dumps(project_display)},
            version: {json.dumps(version or '?')},
            feature: {json.dumps(sprint_code or 'UAT')},
            linked_requirements: {linked_reqs_json},
            handoff_id: {json.dumps(handoff_id)},
            uat_id: {json.dumps(uat_id)}
        }};

        const results = {{}};

        document.getElementById('test-date').textContent = new Date().toLocaleDateString();
        document.getElementById('total-count').textContent =
            document.querySelectorAll('.test-item').length;

        function setResult(btn, result) {{
            const item = btn.closest('.test-item');
            const id = item.dataset.test;
            item.querySelectorAll('.btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            item.classList.remove('passed', 'failed', 'skipped');
            if (result === 'pass') item.classList.add('passed');
            else if (result === 'fail') item.classList.add('failed');
            else item.classList.add('skipped');
            results[id] = result;
            updateCounts();
        }}

        function updateCounts() {{
            const p = Object.values(results).filter(r => r === 'pass').length;
            const f = Object.values(results).filter(r => r === 'fail').length;
            const s = Object.values(results).filter(r => r === 'skip').length;
            document.getElementById('pass-count').textContent = p;
            document.getElementById('fail-count').textContent = f;
            document.getElementById('skip-count').textContent = s;
        }}

        function setOverall(result) {{
            const c = document.getElementById('overall-result');
            c.classList.remove('pending', 'pass', 'fail');
            c.classList.add(result);
            c.innerHTML = result === 'pass'
                ? '<h4 style="color:#4ade80;">v' + UAT_CONFIG.version + ' APPROVED</h4><p>All checks verified!</p>'
                : '<h4 style="color:#f87171;">NEEDS FIXES</h4><p>See notes above.</p>';
        }}

        function buildResultsText() {{
            const total = document.querySelectorAll('.test-item').length;
            const passed = Object.values(results).filter(r => r === 'pass').length;
            const failed = Object.values(results).filter(r => r === 'fail').length;
            const skipped = total - passed - failed;
            const sep = '='.repeat(60);
            const subsep = '-'.repeat(50);

            let out = '[' + UAT_CONFIG.project + '] ';
            const overall = document.getElementById('overall-result');
            if (overall.classList.contains('fail') || failed > 0) out += 'FAIL ';
            else if (overall.classList.contains('pass')) out += 'PASS ';
            out += 'v' + UAT_CONFIG.version + ' -- UAT: ' + UAT_CONFIG.feature + '\\n' + sep + '\\n';
            out += 'Date: ' + new Date().toLocaleString() + '\\n';
            out += 'Version: ' + UAT_CONFIG.version + '\\n';
            if (UAT_CONFIG.linked_requirements.length)
                out += 'Requirements: ' + UAT_CONFIG.linked_requirements.join(', ') + '\\n';
            out += 'Summary: ' + passed + ' passed, ' + failed + ' failed, ' + skipped + ' skipped\\n' + sep + '\\n';

            document.querySelectorAll('section').forEach(sec => {{
                const h = sec.querySelector('h2');
                if (!h) return;
                out += '\\n' + h.textContent + '\\n' + subsep + '\\n';
                sec.querySelectorAll('.test-item').forEach(item => {{
                    const id = item.dataset.test;
                    const label = item.querySelector('.test-label');
                    const title = label ? label.textContent.replace(/[A-Z]+-\\d+/g, '').trim() : '';
                    const notes = item.querySelector('.notes-input')?.value || '';
                    const status = results[id] || 'pending';
                    const tags = {{ pass: 'PASS', fail: 'FAIL', skip: 'SKIP', pending: 'PENDING' }};
                    out += '  [' + id + '] ' + tags[status] + ': ' + title + '\\n';
                    if (notes.trim()) out += '         Notes: ' + notes + '\\n';
                }});
            }});

            const gn = document.getElementById('general-notes').value.trim();
            if (gn) out += '\\nGeneral Notes\\n' + subsep + '\\n' + gn + '\\n';

            if (overall.classList.contains('pass')) out += '\\nOVERALL: APPROVED\\n';
            else if (overall.classList.contains('fail')) out += '\\nOVERALL: NEEDS FIXES\\n';
            else out += '\\nOVERALL: PENDING\\n';

            return out;
        }}

        function copyResults() {{
            const text = buildResultsText();
            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(text).then(() => alert('Copied!'));
            }} else {{
                const ta = document.createElement('textarea');
                ta.value = text;
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                alert('Copied!');
            }}
        }}

        document.addEventListener('paste', function(e) {{
            const zone = e.target.closest('[data-paste-target]');
            if (!zone) return;
            const item = zone.closest('.test-item');
            if (!item) return;
            const files = e.clipboardData?.files;
            if (!files || !files.length) return;
            const file = files[0];
            if (!file.type.startsWith('image/')) return;
            e.preventDefault();
            const reader = new FileReader();
            reader.onload = function(ev) {{
                const img = new Image();
                img.onload = function() {{
                    const maxW = 800;
                    let w = img.width, h = img.height;
                    if (w > maxW) {{ h = Math.round(h * maxW / w); w = maxW; }}
                    const canvas = document.createElement('canvas');
                    canvas.width = w; canvas.height = h;
                    canvas.getContext('2d').drawImage(img, 0, 0, w, h);
                    zone.innerHTML = '';
                    zone.classList.add('has-image');
                    const thumb = document.createElement('img');
                    thumb.src = canvas.toDataURL('image/png');
                    thumb.className = 'media-thumb';
                    zone.appendChild(thumb);
                }};
                img.src = ev.target.result;
            }};
            reader.readAsDataURL(file);
        }});

        async function submitToMetaPM() {{
            const submitBtn = document.getElementById('submit-btn');
            const total = document.querySelectorAll('.test-item').length;
            const passed = Object.values(results).filter(r => r === 'pass').length;
            const failed = Object.values(results).filter(r => r === 'fail').length;
            const skipped = total - passed - failed;

            if ((passed + failed) === 0) {{
                alert('Complete at least one test as Pass or Fail before submitting.');
                return;
            }}

            const detailed = [];
            document.querySelectorAll('.test-item').forEach(t => {{
                const id = t.dataset.test;
                const reqs = t.dataset.reqs || '';
                const label = t.querySelector('.test-label');
                const title = label ? label.textContent.replace(/[A-Z]+-\\d+/g, '').trim() : '';
                const status = results[id] || 'skip';
                const note = t.querySelector('.notes-input')?.value || '';
                detailed.push({{
                    id, title, status, note,
                    linked_requirements: reqs ? reqs.split(',').map(s => s.trim()) : []
                }});
            }});

            const overall = document.getElementById('overall-result');
            let overallStatus = 'pending';
            if (overall.classList.contains('pass')) overallStatus = 'passed';
            else if (overall.classList.contains('fail')) overallStatus = 'failed';
            else overallStatus = failed > 0 ? 'failed' : 'passed';

            submitBtn.disabled = true;
            submitBtn.textContent = 'Submitting...';

            try {{
                const response = await fetch(
                    'https://metapm.rentyourcio.com/api/uat/submit',
                    {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            project: UAT_CONFIG.project,
                            version: UAT_CONFIG.version,
                            feature: UAT_CONFIG.feature,
                            status: overallStatus,
                            total_tests: total,
                            passed, failed, skipped,
                            notes_count: detailed.filter(d => (d.note || '').trim().length > 0).length,
                            results_text: buildResultsText(),
                            results: detailed,
                            linked_requirements: UAT_CONFIG.linked_requirements,
                            url: window.location.href,
                            tested_by: 'PL'
                        }})
                    }}
                );
                const data = await response.json();
                if (response.ok) {{
                    submitBtn.textContent = 'Submitted!';
                    submitBtn.style.background = '#166534';
                    if (data.handoff_url) {{
                        const link = document.createElement('a');
                        link.href = data.handoff_url;
                        link.target = '_blank';
                        link.textContent = 'View in MetaPM';
                        link.style.cssText = 'display:block;text-align:center;margin-top:12px;color:#60a5fa;font-weight:600';
                        submitBtn.parentElement.appendChild(link);
                    }}
                }} else {{
                    submitBtn.textContent = 'Error: ' + (data.detail || response.status);
                    submitBtn.style.background = '#991b1b';
                    submitBtn.disabled = false;
                }}
            }} catch(err) {{
                submitBtn.textContent = 'Network error';
                submitBtn.style.background = '#991b1b';
                submitBtn.disabled = false;
                console.error('Submit error:', err);
            }}
        }}
    </script>
</body>
</html>'''

    return html
