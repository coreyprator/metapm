"""
MetaPM UAT Renderer — BV card HTML generation.
Extracted from uat_spec.py (MP44 REQ-080).
"""
from html import escape as esc


def filter_pl_visual(test_cases: list) -> list:
    """Return only test cases where type is pl_visual (or absent/None)."""
    return [tc for tc in test_cases if tc.get("type", "pl_visual") != "cc_machine"]


def filter_cc_machine(test_cases: list) -> list:
    """Return only cc_machine test cases."""
    return [tc for tc in test_cases if tc.get("type") == "cc_machine"]


def render_machine_card(tc: dict, result_by_id: dict) -> str:
    """Render a single cc_machine BV card (read-only, pre-verified by CC)."""
    tid = esc(tc["id"])
    title = esc(tc["title"])
    current = result_by_id.get(tc["id"], {})
    cur_status = current.get("cc_result", current.get("status", "pending"))
    cc_evidence = esc(current.get("cc_evidence", ""))
    cur_notes = esc(current.get("notes", ""))
    result_label = "PASS" if cur_status == "pass" else ("FAIL" if cur_status == "fail" else cur_status.upper())
    result_color = "var(--pass)" if cur_status == "pass" else ("var(--fail)" if cur_status == "fail" else "var(--pending)")
    evidence_html = ""
    if cc_evidence:
        evidence_html = f"""
        <details style="margin-top:6px">
          <summary style="font-size:0.8rem;color:var(--muted);cursor:pointer">Machine evidence</summary>
          <pre style="font-size:0.75rem;color:var(--muted);background:#0d1117;padding:8px;border-radius:4px;margin-top:4px;overflow-x:auto;white-space:pre-wrap;word-break:break-word">{cc_evidence}</pre>
        </details>"""
    return f"""
    <div class="test-card result-{cur_status} submitted" data-id="{tid}" data-type="cc_machine">
      <div class="test-header">
        <span class="test-id">{tid}</span>
        <span class="test-name">{title}</span>
        <span style="margin-left:auto;font-weight:700;font-size:0.85rem;color:{result_color}">{result_label}</span>
      </div>
      {f'<div style="font-size:0.85rem;color:var(--muted);margin-top:4px">{cur_notes}</div>' if cur_notes else ''}
      {evidence_html}
    </div>"""


def render_pl_card(tc: dict, result_by_id: dict,
                   submitted_cls: str, is_submitted: bool) -> str:
    """Render a single pl_visual BV card with radio buttons, notes, and attachments."""
    tid = esc(tc["id"])
    title = esc(tc["title"])
    url = tc.get("url", "")
    steps = tc.get("steps", [])
    expected = esc(tc.get("expected", ""))
    current = result_by_id.get(tc["id"], {})
    cur_status = current.get("status", "pending")
    cur_notes = esc(current.get("notes", ""))
    cur_class = current.get("classification", "")
    cur_ft = current.get("failure_type", "")
    steps_html = "".join(f"<li>{esc(s)}</li>" for s in steps)
    url_html = f'<a href="{esc(url)}" target="_blank" class="bv-url">{esc(url)}</a>' if url else ""

    def checked(val):
        return " checked" if cur_status == val else ""

    def cls_selected(val):
        return " selected" if cur_class == val else ""

    ft_display = "block" if cur_status == "fail" else "none"
    return f"""
    <div class="test-card result-{cur_status} {submitted_cls}" data-id="{tid}">
      <div class="test-header">
        <span class="test-id">{tid}</span>
        <span class="test-name">{title}</span>
      </div>
      {url_html}
      <ol class="test-steps">{steps_html}</ol>
      <div class="expected">Expected: {expected}</div>
      <div class="radio-group">
        <label class="radio-label{' checked-pass' if cur_status=='pass' else ''}">
          <input type="radio" name="{tid}" value="pass"{checked('pass')}> ✓ Pass</label>
        <label class="radio-label{' checked-fail' if cur_status=='fail' else ''}">
          <input type="radio" name="{tid}" value="fail"{checked('fail')}> ✗ Fail</label>
        <label class="radio-label{' checked-skip' if cur_status=='skip' else ''}">
          <input type="radio" name="{tid}" value="skip"{checked('skip')}> ○ Skip</label>
        <label class="radio-label{' checked-pending' if cur_status=='pending' else ''}">
          <input type="radio" name="{tid}" value="pending"{checked('pending')}> ? Pending</label>
      </div>
      <div class="cascade-classification" data-id="{tid}"
        style="display:{'none' if cur_status == 'pass' else 'block'};margin-top:10px">
        <div class="notes-label">Classification</div>
        <select class="classification-select" data-id="{tid}"
          style="width:100%;padding:7px 10px;background:#0d1117;border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:0.85rem;margin-bottom:8px">
          <option value="">— Select classification —</option>
          <option value="New requirement"{cls_selected("New requirement")}>New requirement</option>
          <option value="Bug"{cls_selected("Bug")}>Bug</option>
          <option value="Finding"{cls_selected("Finding")}>Finding</option>
          <option value="No-action"{'selected' if cur_status == 'pass' else cls_selected("No-action")}>No-action</option>
          <option value="Out of scope"{cls_selected("Out of scope")}>Out of scope</option>
        </select>
        <div class="failure-type-section" data-id="{tid}" style="display:{'block' if (cur_class == 'Bug' and cur_ft) else 'none'}">
          <div class="notes-label">Failure type</div>
          <select class="failure-type-select" data-id="{tid}" data-saved-value="{cur_ft}"
            style="width:100%;padding:7px 10px;background:#0d1117;border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:0.85rem">
            <option value="">— Select failure type —</option>
          </select>
        </div>
      </div>
      <div class="notes-label">Notes</div>
      <textarea id="notes-{tid}" class="notes-input" placeholder="Add notes here..." rows="3">{cur_notes}</textarea>
      {'' if is_submitted else f'<div class="paste-zone" id="paste-{tid}" data-id="{tid}" tabindex="0" contenteditable="false">📷 Paste screenshot here (Ctrl+V)</div>'}
      <div class="attach-row">
        <label class="attach-btn">📎 Attach file<input type="file" class="attach-input" accept="image/*,.pdf" data-id="{tid}" {'disabled' if is_submitted else ''}></label>
        <span class="attach-name" id="aname-{tid}"></span>
      </div>
      <div class="attach-thumb" id="athumb-{tid}">{''.join(f'<img src="data:{a.get("mime","image/png")};base64,{a["data"]}" title="{esc(a.get("filename","attachment"))}">' for a in (current.get("attachments") or []) if a.get("data"))}</div>
    </div>"""


def render_bv_cards_section(real_test_cases: list, result_by_id: dict,
                            submitted_cls: str, is_submitted: bool) -> str:
    """Render the full BV cards section — machine tests + PL-visual cards."""
    cc_machine_tcs = filter_cc_machine(real_test_cases)
    pl_visual_tcs = filter_pl_visual(real_test_cases)

    # Machine tests in collapsed details (MP19 REQ-050)
    machine_section = ""
    if cc_machine_tcs:
        machine_pass = sum(
            1 for tc in cc_machine_tcs
            if result_by_id.get(tc["id"], {}).get("cc_result") == "pass"
            or result_by_id.get(tc["id"], {}).get("status") == "pass"
        )
        machine_cards = "".join(render_machine_card(tc, result_by_id) for tc in cc_machine_tcs)
        machine_section = f"""
        <details style="margin-bottom:20px;opacity:0.75">
          <summary style="font-size:0.95rem;color:var(--pass);cursor:pointer;padding:10px 0">
            Machine tests — pre-verified by CC ({machine_pass}/{len(cc_machine_tcs)} passed)
          </summary>
          <p style="font-size:0.85rem;color:var(--muted);margin:8px 0 12px">These were verified programmatically by CC before handoff. No action required from PL.</p>
          {machine_cards}
        </details>"""

    pl_section = ""
    if pl_visual_tcs:
        pl_cards = "".join(render_pl_card(tc, result_by_id, submitted_cls, is_submitted) for tc in pl_visual_tcs)
        pl_section = f"""
        <div class="uat-section-pl">
          <h3 style="font-size:1rem;color:var(--accent);margin-bottom:12px">Your input required — {len(pl_visual_tcs)} items</h3>
          {pl_cards}
        </div>"""
    elif cc_machine_tcs:
        pl_section = f"""
        <div class="uat-section-pl" style="text-align:center;padding:20px">
          <p style="color:var(--muted);margin-bottom:12px">All BVs were machine-verified. No action required.</p>
          <button class="btn btn-submit" onclick="submitAcknowledge()">Acknowledge &amp; Close</button>
        </div>"""

    return machine_section + pl_section
