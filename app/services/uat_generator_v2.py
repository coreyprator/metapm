"""
UAT Generator V2 — MP-UAT-GEN-001
Renders UAT HTML pages from structured test case data submitted by CC.
Only pl_visual test cases are shown in the HTML. cc_machine cases are stored but hidden.
"""
import json
import logging
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

PROJECT_EMOJIS = {
    "metapm": "\U0001f534",
    "etymython": "\U0001f7e3",
    "super-flashcards": "\U0001f7e1",
    "artforge": "\U0001f7e0",
    "harmonylab": "\U0001f535",
    "pie-network-graph": "\U0001f537",
    "portfolio-rag": "\u26aa",
    "project-methodology": "\U0001f7e2",
}


def render_structured_uat_html(
    project: str,
    version: str,
    feature: str,
    pth: Optional[str],
    cc_summary: Optional[str],
    test_cases: List[Dict],
    handoff_id: str,
    uat_result_id: str,
    uat_page_id: Optional[str] = None,
) -> str:
    """Render a complete interactive UAT HTML page from structured test case data.

    Only test cases where type == 'pl_visual' are rendered.
    cc_machine test cases are stored in the DB but not shown.
    """
    project_key = project.lower().replace(" ", "-") if project else "unknown"
    color = PROJECT_COLORS.get(project_key, "#6366f1")
    emoji = PROJECT_EMOJIS.get(project_key, "")
    project_display = resolve_project_name(project)

    # Filter to PL-visible test cases only
    pl_cases = [tc for tc in test_cases if tc.get("type", "pl_visual") == "pl_visual"]
    total_tests = len(pl_cases)

    # Header line 1: {emoji} {Project} v{version} PTH: {PTH} — {sprint_title}
    # Header line 2: {feature_description} | {N} test cases
    title = f"{emoji} {project_display} v{version}"
    if pth:
        title += f" PTH: {pth}"

    # Split feature into sprint title (before colon) and description (after colon)
    sprint_title = ""
    feature_desc = ""
    if feature:
        if ":" in feature:
            sprint_title = feature.split(":", 1)[0].strip()
            feature_desc = feature.split(":", 1)[1].strip()
        else:
            sprint_title = feature

    if sprint_title:
        title += f" — {sprint_title}"

    subtitle_parts = []
    if feature_desc:
        subtitle_parts.append(feature_desc)
    subtitle_parts.append(f"{total_tests} test cases")
    subtitle = " | ".join(subtitle_parts)

    page_id = uat_page_id or uat_result_id

    # Build CC summary block HTML
    cc_summary_html = ""
    if cc_summary:
        cc_summary_html = f'''
    <div class="cc-summary">
        <h3>CC Summary</h3>
        <pre>{escape(cc_summary)}</pre>
    </div>'''

    # Build test case sections
    test_items_html = ""
    for i, tc in enumerate(pl_cases):
        tc_id = escape(tc["id"])
        tc_title = escape(tc["title"])
        tc_expected = escape(tc.get("expected") or "")

        # Build instruction steps
        instructions = tc.get("instructions", [])
        steps_html = ""
        if instructions:
            steps_items = "".join(
                f"<li>{escape(step)}</li>" for step in instructions
            )
            steps_html = f'<ol class="steps">{steps_items}</ol>'

        test_items_html += f'''
        <div class="test-item" data-test="{tc_id}">
            <div class="test-header">
                <span class="test-id">{tc_id}</span>
                <span class="test-title">{tc_title}</span>
            </div>
            {steps_html}
            <div class="expected-row">Expected: {tc_expected}</div>
            <div class="test-controls">
                <div class="test-buttons">
                    <button class="btn btn-pass" onclick="setResult(this,'pass')">Pass</button>
                    <button class="btn btn-fail" onclick="setResult(this,'fail')">Fail</button>
                    <button class="btn btn-skip" onclick="setResult(this,'skip')">Skip</button>
                </div>
                <select class="failure-type-select" style="display:none;margin-top:8px;padding:6px 8px;background:#1e1e32;color:#e2e8f0;border:1px solid #f8717180;border-radius:4px;font-size:0.85rem">
                    <option value="">Select failure type...</option>
                    <optgroup label="Content failures">
                      <option value="wrong_spec">Wrong spec</option>
                      <option value="regression">Regression</option>
                      <option value="environment">Environment</option>
                      <option value="unclear_bv">Unclear BV</option>
                    </optgroup>
                    <optgroup label="Bug types">
                      <option value="ui_rendering_bug">UI rendering — wrong position, missing element, wrong style</option>
                      <option value="data_mapping_bug">Data mapping — wrong field shown, incorrect join</option>
                      <option value="filter_query_bug">Filter/query — filter doesn't work, empty dropdown</option>
                      <option value="gate_validation_bug">Gate/validation — blocks valid input or allows invalid</option>
                      <option value="navigation_routing_bug">Navigation/routing — wrong page, wrong link destination</option>
                      <option value="api_contract_bug">API contract — wrong response shape, missing fields</option>
                      <option value="state_management_bug">State management — data doesn't persist, stale data</option>
                      <option value="performance_bug">Performance — timeout, slow load, unresponsive UI</option>
                    </optgroup>
                    <optgroup label="Process failures">
                      <option value="machine_test_sent_to_pl">Machine test sent to PL</option>
                      <option value="no_5q_applied">No 5Q applied</option>
                      <option value="incomplete_spec">Incomplete spec</option>
                      <option value="missing_acceptance_criteria">Missing acceptance criteria</option>
                      <option value="incomplete_handoff">Incomplete handoff</option>
                    </optgroup>
                    <option value="other">Other</option>
                </select>
                <div class="notes-container">
                    <textarea class="notes-input" placeholder="Notes..."></textarea>
                </div>
                <div class="media-row">
                    <div class="paste-zone" contenteditable="true" data-paste-target="true">Ctrl+V screenshot</div>
                </div>
            </div>
        </div>'''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UAT: {escape(project_display)} v{escape(version)}</title>
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
            max-width: 900px; margin: 0 auto; padding: 20px;
            background: var(--bg-primary); color: var(--text-primary); line-height: 1.6;
        }}
        header {{
            background: linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent), black 15%));
            padding: 20px; border-radius: 12px; margin-bottom: 24px;
        }}
        header h1 {{ font-size: 1.4rem; margin-bottom: 8px; }}
        header p {{ opacity: 0.9; font-size: 0.9rem; }}
        .meta {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 12px; font-size: 0.85rem; }}
        .meta span {{ background: rgba(255,255,255,0.15); padding: 4px 10px; border-radius: 4px; }}
        .cc-summary {{
            background: #1e2a3f; border: 2px solid #3b82f6; border-radius: 8px;
            padding: 20px; margin-bottom: 24px;
        }}
        .cc-summary h3 {{ color: #60a5fa; margin-bottom: 12px; font-size: 1rem; }}
        .cc-summary pre {{
            background: #0f172a; padding: 16px; border-radius: 6px;
            font-size: 0.8rem; line-height: 1.5; white-space: pre-wrap;
            color: #cbd5e1; overflow-x: auto;
        }}
        .test-section {{ background: var(--bg-secondary); border-radius: 8px; padding: 20px; margin-bottom: 16px; }}
        .test-section h2 {{
            color: color-mix(in srgb, var(--accent), white 40%); font-size: 1.1rem;
            margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid var(--accent);
        }}
        .test-item {{ padding: 16px 0; border-bottom: 1px solid var(--border-color); }}
        .test-item:last-child {{ border-bottom: none; }}
        .test-header {{ display: flex; gap: 10px; align-items: baseline; margin-bottom: 8px; }}
        .test-id {{
            background: var(--accent); color: white; padding: 2px 8px;
            border-radius: 4px; font-weight: 700; font-size: 0.85rem; flex-shrink: 0;
        }}
        .test-title {{ font-weight: 500; font-size: 1rem; }}
        .steps {{ margin: 8px 0 8px 24px; font-size: 0.9rem; color: #d1d5db; }}
        .steps li {{ margin-bottom: 4px; }}
        .expected-row {{
            font-size: 0.85rem; color: #a78bfa; font-style: italic;
            margin-bottom: 10px; padding-left: 4px;
        }}
        .test-controls {{ display: flex; flex-direction: column; gap: 8px; }}
        .test-buttons {{ display: flex; gap: 6px; }}
        .btn {{
            padding: 6px 14px; border: none; border-radius: 4px;
            cursor: pointer; font-weight: 600; font-size: 0.85rem; transition: all 0.15s;
        }}
        .btn-pass {{ background: #166534; color: #bbf7d0; }}
        .btn-pass:hover, .btn-pass.selected {{ background: var(--accent-success); color: white; }}
        .btn-fail {{ background: #991b1b; color: #fecaca; }}
        .btn-fail:hover, .btn-fail.selected {{ background: var(--accent-danger); color: white; }}
        .btn-skip {{ background: #374151; color: #d1d5db; }}
        .btn-skip:hover, .btn-skip.selected {{ background: var(--accent-skip); color: white; }}
        .test-item.passed .test-title {{ color: #4ade80; }}
        .test-item.passed .test-title::before {{ content: "\\2713 "; }}
        .test-item.failed .test-title {{ color: #f87171; }}
        .test-item.failed .test-title::before {{ content: "\\2717 "; }}
        .test-item.skipped .test-title {{ color: #9ca3af; }}
        .test-item.skipped .test-title::before {{ content: "\\25CB "; }}
        .notes-input {{
            width: 100%; padding: 8px 10px; background: #1e1e32;
            border: 1px solid var(--border-color); border-radius: 4px;
            color: var(--text-primary); font-family: inherit; font-size: 0.9rem;
            resize: vertical; min-height: 40px;
        }}
        .notes-input:focus {{ outline: none; border-color: var(--accent); }}
        .media-row {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
        .paste-zone {{
            padding: 6px 10px; background: #1e1e32;
            border: 1px dashed var(--border-color); border-radius: 4px;
            font-size: 0.75rem; color: var(--text-muted); cursor: text; min-width: 140px;
        }}
        .paste-zone:focus {{ outline: none; border-color: var(--accent); }}
        .paste-zone.has-image {{ border-color: var(--accent-success); border-style: solid; }}
        .media-thumb {{ max-width: 120px; max-height: 80px; border-radius: 4px; margin-top: 4px; cursor: pointer; }}
        .status-bar {{
            background: #1e1e32; border: 2px solid var(--accent); border-radius: 8px;
            padding: 20px; margin-top: 24px;
        }}
        .status-bar h3 {{ margin-bottom: 16px; }}
        .summary-stats {{ display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }}
        .stat {{
            padding: 12px 20px; border-radius: 6px; font-weight: bold; text-align: center;
            min-width: 80px;
        }}
        .stat.total {{ background: var(--accent); }}
        .stat.pass {{ background: var(--accent-success); }}
        .stat.fail {{ background: #991b1b; }}
        .stat.skip {{ background: var(--accent-skip); }}
        .stat.pending {{ background: #374151; }}
        .overall-result {{ padding: 16px; border-radius: 8px; text-align: center; margin-top: 16px; }}
        .overall-result.is-pending {{ background: #374151; border: 2px dashed #6b7280; }}
        .overall-result.is-pass {{ background: #166534; border: 2px solid var(--accent-success); }}
        .overall-result.is-fail {{ background: #991b1b; border: 2px solid #ef4444; }}
        .export-bar {{
            text-align: center; margin-top: 24px;
            display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;
        }}
        .export-btn {{
            padding: 12px 32px; border: none; border-radius: 8px;
            font-size: 15px; cursor: pointer; font-weight: 600;
        }}
        .copy-btn {{ background: var(--accent); color: white; }}
        .submit-btn {{ background: var(--accent-success); color: white; }}
        .save-btn {{ background: #3b82f6; color: white; }}
        .general-notes {{ background: #1e2a3f; border: 2px solid #8b5cf6; border-radius: 8px; padding: 20px; margin-top: 24px; }}
        .general-notes h3 {{ color: #a78bfa; margin-bottom: 12px; }}
        .general-notes-input {{
            width: 100%; min-height: 80px; padding: 12px;
            background: #1e1e32; border: 1px solid var(--border-color);
            border-radius: 6px; color: var(--text-primary); font-size: 0.9rem; resize: vertical;
        }}
        /* Floating cheat sheet button */
        .uat-help-fab {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: var(--accent, #e74c3c);
            color: #fff;
            border: none;
            font-size: 20px;
            font-weight: bold;
            box-shadow: 0 4px 15px rgba(0,0,0,0.4);
            cursor: pointer;
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        /* Native Popover API styling */
        #uat-cheat-sheet[popover] {{
            width: min(400px, 90vw);
            max-height: 80vh;
            overflow-y: auto;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid var(--border-color, #26344f);
            background: var(--bg-secondary, #111a2d);
            color: var(--text-primary, #e6edf8);
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            margin: auto;
        }}
        .popover-header h3 {{
            margin: 0 0 12px;
            font-size: 16px;
            color: var(--text-primary, #e6edf8);
        }}
        .popover-header h3 small {{
            font-size: 11px;
            color: var(--text-muted, #9aa8c7);
            margin-left: 6px;
        }}
        .rules-summary {{
            background: rgba(231, 76, 60, 0.1);
            border-left: 4px solid var(--accent, #e74c3c);
            padding: 10px 12px;
            margin: 0 0 16px;
            font-size: 13px;
        }}
        .rules-summary ul {{
            margin: 6px 0 0;
            padding-left: 16px;
        }}
        .type-definitions h4 {{
            color: #4a90d9;
            border-bottom: 1px solid var(--border-color, #26344f);
            padding-bottom: 4px;
            margin: 0 0 8px;
            font-size: 13px;
        }}
        .group-title {{
            font-size: 11px;
            text-transform: uppercase;
            color: var(--text-muted, #9aa8c7);
            margin: 12px 0 4px;
            font-weight: 600;
            letter-spacing: 0.05em;
        }}
        .type-definitions ul {{
            margin: 0;
            padding-left: 16px;
            font-size: 12px;
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <header>
        <h1>{escape(title)}</h1>
        <p>{escape(subtitle)}</p>
        <div class="meta">
            <span>Version: {escape(version)}</span>
            <span id="test-date"></span>
            <span>Status: <strong id="overall-label">PENDING</strong></span>
        </div>
    </header>

    {cc_summary_html}

    <div class="test-section">
        <h2>PL Browser Verification ({total_tests} tests)</h2>
        {test_items_html}
    </div>

    <div class="general-notes">
        <h3>General Notes</h3>
        <div id="notes-list"></div>
        <button type="button" onclick="addNote()" style="margin-top:8px;padding:8px 16px;background:#3b82f6;color:white;border:none;border-radius:6px;cursor:pointer;font-size:0.85rem">+ Add Note</button>
    </div>

    <footer style="background:linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent), black 15%));padding:20px;border-radius:12px;margin-top:24px;">
        <h1 style="font-size:1.4rem;margin-bottom:8px;">{escape(title)}</h1>
        <p style="opacity:0.9;font-size:0.9rem;">{escape(subtitle)}</p>
    </footer>

    <div class="status-bar">
        <h3>Results Summary</h3>
        <div class="summary-stats">
            <div class="stat total">Total: <span id="total-count">{total_tests}</span></div>
            <div class="stat pass">Pass: <span id="pass-count">0</span></div>
            <div class="stat fail">Fail: <span id="fail-count">0</span></div>
            <div class="stat skip">Skip: <span id="skip-count">0</span></div>
            <div class="stat pending">Pending: <span id="pending-count">{total_tests}</span></div>
        </div>
        <div class="overall-result is-pending" id="overall-result">
            <h4>Overall: PENDING</h4>
            <p style="margin-top:8px;opacity:0.8;">Mark all test cases, then submit.</p>
        </div>
    </div>

    <div class="export-bar">
        <button class="export-btn save-btn" onclick="saveResults()">Save Progress</button>
        <button class="export-btn copy-btn" onclick="copyResults()">{'Copy CC Link (' + escape(pth) + ')' if pth else 'Copy CC Link'}</button>
        <button class="export-btn submit-btn" id="submit-btn" onclick="submitResults()">Submit Final</button>
    </div>

    <script>
        const UAT_CONFIG = {{
            project: {json.dumps(project_display)},
            version: {json.dumps(version)},
            feature: {json.dumps(feature or '')},
            pth: {json.dumps(pth or '')},
            handoff_id: {json.dumps(handoff_id)},
            uat_result_id: {json.dumps(uat_result_id)},
            uat_page_id: {json.dumps(page_id)}
        }};

        const results = {{}};
        document.getElementById('test-date').textContent = new Date().toLocaleDateString();

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
            // MP24 REQ-056: Show/hide failure_type dropdown on fail
            const ftSelect = item.querySelector('.failure-type-select');
            if (ftSelect) ftSelect.style.display = result === 'fail' ? 'block' : 'none';
            updateCounts();
        }}

        function updateCounts() {{
            const total = document.querySelectorAll('.test-item').length;
            const p = Object.values(results).filter(r => r === 'pass').length;
            const f = Object.values(results).filter(r => r === 'fail').length;
            const s = Object.values(results).filter(r => r === 'skip').length;
            const pending = total - p - f - s;
            document.getElementById('pass-count').textContent = p;
            document.getElementById('fail-count').textContent = f;
            document.getElementById('skip-count').textContent = s;
            document.getElementById('pending-count').textContent = pending;

            const overall = document.getElementById('overall-result');
            const label = document.getElementById('overall-label');
            if (pending === 0) {{
                if (f > 0) {{
                    overall.className = 'overall-result is-fail';
                    overall.innerHTML = '<h4 style="color:#f87171;">NEEDS FIXES</h4><p>' + f + ' test(s) failed.</p>';
                    label.textContent = 'FAILED';
                    label.style.color = '#f87171';
                }} else {{
                    overall.className = 'overall-result is-pass';
                    overall.innerHTML = '<h4 style="color:#4ade80;">ALL PASSED</h4><p>All ' + p + ' tests passed!</p>';
                    label.textContent = 'PASSED';
                    label.style.color = '#4ade80';
                }}
            }} else {{
                overall.className = 'overall-result is-pending';
                overall.innerHTML = '<h4>Overall: PENDING</h4><p>' + pending + ' test(s) remaining.</p>';
                label.textContent = 'PENDING';
                label.style.color = '';
            }}
        }}

        function gatherTestCases() {{
            const cases = [];
            document.querySelectorAll('.test-item').forEach(item => {{
                const id = item.dataset.test;
                const notes = item.querySelector('.notes-input')?.value || '';
                const ftSelect = item.querySelector('.failure-type-select');
                const failure_type = ftSelect ? ftSelect.value : '';
                cases.push({{
                    id: id,
                    status: results[id] || 'pending',
                    result: results[id] ? (results[id] === 'pass' ? 'Confirmed' : results[id] === 'fail' ? 'Failed' : 'Skipped') : null,
                    notes: notes,
                    failure_type: failure_type || null
                }});
            }});
            return cases;
        }}

        function buildResultsText() {{
            const total = document.querySelectorAll('.test-item').length;
            const p = Object.values(results).filter(r => r === 'pass').length;
            const f = Object.values(results).filter(r => r === 'fail').length;
            const s = Object.values(results).filter(r => r === 'skip').length;
            const sep = '='.repeat(60);

            let out = '[' + UAT_CONFIG.project + '] ';
            out += (f > 0 ? '\\U0001f534' : '\\U0001f7e2') + ' v' + UAT_CONFIG.version;
            out += ' \\u2014 UAT: ' + UAT_CONFIG.feature + '\\n' + sep + '\\n';
            out += 'Date: ' + new Date().toLocaleString() + '\\n';
            out += 'Version: ' + UAT_CONFIG.version + '\\n';
            out += 'Summary: ' + p + ' passed, ' + f + ' failed, ' + s + ' skipped\\n' + sep + '\\n\\n';

            document.querySelectorAll('.test-item').forEach(item => {{
                const id = item.dataset.test;
                const title = item.querySelector('.test-title')?.textContent || '';
                const notes = item.querySelector('.notes-input')?.value || '';
                const status = results[id] || 'pending';
                const icons = {{ pass: '\\u2713 PASS', fail: '\\u2717 FAIL', skip: '? PENDING', pending: '? PENDING' }};
                out += '  [' + id + '] ' + (icons[status] || status) + ': ' + title + '\\n';
                if (notes.trim()) out += '         \\U0001f4dd ' + notes + '\\n';
                out += '\\n';
            }});

            const notes = gatherNotes();
            if (notes.length) {{
                out += 'General Notes\\n' + '-'.repeat(50) + '\\n';
                notes.forEach(n => {{ out += '[' + (n.classification || '') + '] ' + n.text + '\\n'; }});
            }}

            out += '\\nOVERALL: ' + (f > 0 ? 'PENDING' : (Object.keys(results).length === total ? 'APPROVED' : 'PENDING')) + '\\n';
            return out;
        }}

        function copyResults() {{
            const text = buildResultsText();
            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(text).then(() => alert('Copied!'));
            }} else {{
                const ta = document.createElement('textarea');
                ta.value = text; document.body.appendChild(ta);
                ta.select(); document.execCommand('copy');
                document.body.removeChild(ta); alert('Copied!');
            }}
        }}

        async function saveResults() {{
            const cases = gatherTestCases();
            const pending = cases.filter(c => c.status === 'pending').length;
            const failed = cases.filter(c => c.status === 'fail').length;
            let overall = 'pending';
            if (pending === 0) overall = failed > 0 ? 'failed' : 'passed';

            try {{
                const res = await fetch(
                    'https://metapm.rentyourcio.com/api/uat/' + UAT_CONFIG.uat_page_id + '/results',
                    {{
                        method: 'PATCH',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ test_cases: cases, overall_status: overall }})
                    }}
                );
                if (res.ok) {{
                    alert('Progress saved!');
                }} else {{
                    const d = await res.json();
                    alert('Save failed: ' + (d.detail || res.status));
                }}
            }} catch(err) {{
                alert('Network error: ' + err.message);
            }}
        }}

        async function submitResults() {{
            const btn = document.getElementById('submit-btn');
            const cases = gatherTestCases();
            const total = cases.length;
            const p = cases.filter(c => c.status === 'pass').length;
            const f = cases.filter(c => c.status === 'fail').length;
            const s = cases.filter(c => c.status === 'skip').length;
            const pending = total - p - f - s;

            if (pending > 0) {{
                if (!confirm(pending + ' test(s) still pending. Submit anyway?')) return;
            }}

            btn.disabled = true;
            btn.textContent = 'Submitting...';

            try {{
                // Save results first — auto-approve when all pass
                const allPassFinal = (f === 0 && pending === 0 && p === total);
                const saveRes = await fetch(
                    'https://metapm.rentyourcio.com/api/uat/' + UAT_CONFIG.uat_page_id + '/results',
                    {{
                        method: 'PATCH',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            test_cases: cases,
                            overall_status: allPassFinal ? 'approved' : (f > 0 ? 'failed' : (pending > 0 ? 'pending' : 'passed'))
                        }})
                    }}
                );

                // Then submit to UAT results
                const submitRes = await fetch(
                    'https://metapm.rentyourcio.com/api/uat/submit',
                    {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            project: UAT_CONFIG.project,
                            version: UAT_CONFIG.version,
                            feature: UAT_CONFIG.feature,
                            status: f > 0 ? 'failed' : 'passed',
                            total_tests: total,
                            passed: p, failed: f, skipped: s,
                            results_text: buildResultsText(),
                            results: cases.map(c => ({{
                                id: c.id, title: c.id, status: c.status, note: c.notes
                            }})),
                            tested_by: 'PL',
                            pth: UAT_CONFIG.pth
                        }})
                    }}
                );

                if (submitRes.ok) {{
                    const data = await submitRes.json();
                    const allPass = (f === 0 && pending === 0 && p === total);
                    btn.textContent = allPass ? 'UAT approved — all tests passed' : 'Submitted!';
                    btn.style.background = '#166534';
                    if (data.handoff_url) {{
                        const link = document.createElement('a');
                        link.href = data.handoff_url; link.target = '_blank';
                        link.textContent = 'View in MetaPM';
                        link.style.cssText = 'display:block;text-align:center;margin-top:12px;color:#60a5fa;font-weight:600';
                        btn.parentElement.appendChild(link);
                    }}
                }} else {{
                    const d = await submitRes.json();
                    btn.textContent = 'Error: ' + (d.detail || submitRes.status);
                    btn.style.background = '#991b1b';
                    btn.disabled = false;
                }}
            }} catch(err) {{
                btn.textContent = 'Network error';
                btn.style.background = '#991b1b';
                btn.disabled = false;
            }}
        }}

        // MP24 REQ-057: Multi-note management
        let noteCounter = 0;
        function addNote() {{
            noteCounter++;
            const ts = new Date().toISOString().replace('T', ' ').substring(0, 19) + 'Z';
            const container = document.getElementById('notes-list');
            const entry = document.createElement('div');
            entry.className = 'note-entry';
            entry.dataset.noteId = noteCounter;
            entry.style.cssText = 'background:#1e1e32;border:1px solid #334155;border-radius:6px;padding:12px;margin-bottom:8px;position:relative';
            entry.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">` +
                `<span style="color:#8b949e;font-size:0.8rem">${{ts}}</span>` +
                `<div style="display:flex;gap:8px;align-items:center">` +
                `<select class="note-classification" style="padding:4px 6px;background:#0d1117;color:#e2e8f0;border:1px solid #334155;border-radius:4px;font-size:0.8rem">` +
                `<option value="">No classification</option>` +
                `<option value="bug">Bug</option>` +
                `<option value="finding">Finding</option>` +
                `<option value="new_requirement">New Requirement</option>` +
                `<option value="no_action">No-action</option>` +
                `</select>` +
                `<button onclick="this.closest('.note-entry').remove()" style="background:none;border:none;color:#f87171;cursor:pointer;font-size:1.1rem;padding:0 4px">&times;</button>` +
                `</div></div>` +
                `<textarea class="note-text" placeholder="Enter note..." style="width:100%;min-height:60px;padding:8px;background:#0d1117;color:#e2e8f0;border:1px solid #334155;border-radius:4px;resize:vertical;font-size:0.85rem"></textarea>`;
            container.appendChild(entry);
        }}

        function gatherNotes() {{
            const entries = [];
            document.querySelectorAll('.note-entry').forEach(entry => {{
                const text = entry.querySelector('.note-text')?.value || '';
                const classification = entry.querySelector('.note-classification')?.value || null;
                const tsSpan = entry.querySelector('span');
                const timestamp = tsSpan ? tsSpan.textContent.trim() : null;
                if (text.trim()) {{
                    entries.push({{ timestamp, text: text.trim(), classification: classification || null }});
                }}
            }});
            return entries;
        }}

        // Screenshot paste handler
        document.addEventListener('paste', function(e) {{
            const zone = e.target.closest('[data-paste-target]');
            if (!zone) return;
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

        // Pre-populate saved results on page load (MP-UAT-DASHBOARD-FIX-001)
        (async function loadSavedResults() {{
            try {{
                const res = await fetch(
                    'https://metapm.rentyourcio.com/api/uat/' + UAT_CONFIG.uat_page_id + '/results'
                );
                if (!res.ok) return;
                const data = await res.json();
                (data.test_cases || []).forEach(tc => {{
                    if (!tc.status || tc.status === 'pending') return;
                    const item = document.querySelector('.test-item[data-test="' + tc.id + '"]');
                    if (!item) return;
                    // Find and click the matching button
                    const btnClass = tc.status === 'pass' ? 'btn-pass' : tc.status === 'fail' ? 'btn-fail' : 'btn-skip';
                    const btn = item.querySelector('.' + btnClass);
                    if (btn) setResult(btn, tc.status);
                    // Restore notes
                    if (tc.notes) {{
                        const textarea = item.querySelector('.notes-input');
                        if (textarea) textarea.value = tc.notes;
                    }}
                }});
            }} catch(e) {{
                console.log('Could not load saved results:', e);
            }}
        }})();
    </script>

    <!-- Floating cheat sheet trigger -->
    <button popovertarget="uat-cheat-sheet" class="uat-help-fab" title="UAT Rules &amp; Definitions">?</button>

    <!-- Cheat sheet popover — native Popover API, renders in browser top layer -->
    <div id="uat-cheat-sheet" popover>
      <div class="popover-header">
        <h3>UAT Reference Guide <small>v2.82.0</small></h3>
      </div>

      <div class="rules-summary">
        <strong>&#9888;&#65039; Submission Rules:</strong>
        <ul>
          <li><strong>Fail / Conditional Pass:</strong> Requires Failure Type</li>
          <li><strong>Skip / Pending:</strong> Requires Notes explaining why</li>
          <li><strong>Pass:</strong> No additional fields required</li>
        </ul>
      </div>

      <div class="type-definitions">
        <h4>Failure Types</h4>

        <div class="group">
          <div class="group-title">Content Failures</div>
          <ul>
            <li><strong>Wrong spec:</strong> CC built something different from intended</li>
            <li><strong>Regression:</strong> Previously working is now broken</li>
            <li><strong>Environment:</strong> Deploy or infrastructure issue</li>
            <li><strong>Unclear BV:</strong> Test too vague to evaluate fairly</li>
          </ul>
        </div>

        <div class="group">
          <div class="group-title">Bug Types</div>
          <ul>
            <li><strong>UI rendering:</strong> Wrong position, missing element, wrong style</li>
            <li><strong>Data mapping:</strong> Wrong field shown, incorrect join</li>
            <li><strong>Filter/query:</strong> Filter doesn't work, empty dropdown</li>
            <li><strong>Gate/validation:</strong> Blocks valid input or allows invalid</li>
            <li><strong>Navigation/routing:</strong> Wrong page, wrong link destination</li>
            <li><strong>API contract:</strong> Wrong response shape, missing fields</li>
            <li><strong>State management:</strong> Data doesn't persist, stale data</li>
            <li><strong>Performance:</strong> Timeout, slow load, unresponsive UI</li>
          </ul>
        </div>

        <div class="group">
          <div class="group-title">Process Failures</div>
          <ul>
            <li><strong>Machine test sent to PL:</strong> cc_machine BV in PL form (BA32)</li>
            <li><strong>No 5Q applied:</strong> Sprint posted without 5Q (BA31)</li>
            <li><strong>Incomplete spec:</strong> Spec too vague to build from</li>
            <li><strong>Missing acceptance criteria:</strong> BV didn't explain how to test</li>
            <li><strong>Incomplete handoff:</strong> Missing version, commit, deploy URL</li>
          </ul>
        </div>

        <div class="group">
          <div class="group-title">Other</div>
          <ul>
            <li><strong>Other:</strong> Any failure not covered above — explain in notes</li>
          </ul>
        </div>
      </div>
    </div>
</body>
</html>'''

    return html
