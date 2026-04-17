"""
MetaPM UAT Notes — General notes section HTML generation.
Extracted from uat_spec.py (MP44 REQ-080).
"""
from html import escape as esc


def render_general_notes(gn_stored_attachments: list,
                         is_submitted: bool) -> str:
    """Render the General Notes section HTML."""
    attachments_html = ''.join(
        f'<img src="data:{a.get("mime","image/png")};base64,{a["data"]}" title="{esc(a.get("filename","attachment"))}">'
        for a in gn_stored_attachments if a.get("data")
    )

    return f"""
  <div class="general-notes">
    <div class="general-notes-title">General Notes</div>
    <div id="notes-list"></div>
    {'' if is_submitted else '<button type="button" onclick="addNote()" style="margin-top:8px;padding:6px 14px;background:#3b82f6;color:white;border:none;border-radius:6px;cursor:pointer;font-size:0.82rem">+ Add Note</button>'}
    {'' if is_submitted else '<div class="paste-zone" id="gn-paste-zone" tabindex="0" contenteditable="false">📷 Paste screenshot here (Ctrl+V)</div>'}
    <div class="attach-row">
      <label class="attach-btn">📎 Attach file<input type="file" id="gn-attach-input" accept="image/*,.pdf" {'disabled' if is_submitted else ''}></label>
      <span class="attach-name" id="gn-attach-name"></span>
    </div>
    <div class="attach-thumb" id="gn-attach-thumb">{attachments_html}</div>
  </div>"""
