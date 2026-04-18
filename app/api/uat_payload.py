"""
MetaPM UAT Payload — Full page assembly (CSS + HTML structure + JS).
Extracted from uat_spec.py (MP44 REQ-080).
"""
import json
from html import escape as esc


_PROJECT_NAMES = {
    'proj-mp': 'MetaPM', 'proj-sf': 'Super Flashcards',
    'proj-hl': 'HarmonyLab', 'proj-af': 'ArtForge',
    'proj-em': 'Etymython', 'proj-efg': 'Etymology Graph',
    'proj-pr': 'Portfolio RAG', 'proj-pa': 'Personal Assistant',
    'proj-pm': 'project-methodology', 'EFG': 'Etymology Graph',
}


def get_page_css() -> str:
    """Return all CSS styles for the UAT page."""
    return """
    :root {
      --bg: #0f1117; --card: #161b22; --border: #30363d;
      --accent: #58a6ff; --pass: #3fb950; --fail: #f85149;
      --skip: #8b949e; --pending: #d29922; --text: #c9d1d9; --muted: #8b949e;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: var(--bg); color: var(--text); padding: 24px 16px;
      max-width: 860px; margin: 0 auto; line-height: 1.6; }
    header { background: var(--card); border: 1px solid var(--border);
      border-left: 4px solid var(--accent); border-radius: 8px;
      padding: 20px; margin-bottom: 20px; }
    header h1 { font-size: 1.3rem; color: #e6edf3; }
    .meta { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
    .chip { background: rgba(88,166,255,0.1); border: 1px solid rgba(88,166,255,0.3);
      color: var(--accent); font-size: 0.8rem; padding: 3px 10px; border-radius: 12px; }
    .reqs { margin-top: 10px; font-size: 0.85rem; color: var(--muted); }
    .pl-info { font-size: 0.8rem; color: var(--muted); margin-top: 8px; }
    .summary-bar { display: flex; gap: 10px; flex-wrap: wrap;
      background: var(--card); border: 1px solid var(--border);
      border-radius: 8px; padding: 14px 18px; margin-bottom: 20px; align-items: center; }
    .summary-bar .label { font-size: 0.8rem; color: var(--muted); }
    .count { padding: 4px 14px; border-radius: 12px; font-weight: 700; font-size: 0.9rem; }
    .ct-total { background: #21262d; color: var(--text); }
    .ct-pass { background: rgba(63,185,80,0.15); color: var(--pass); }
    .ct-fail { background: rgba(248,81,73,0.15); color: var(--fail); }
    .ct-skip { background: rgba(139,148,158,0.15); color: var(--skip); }
    .ct-pend { background: rgba(210,153,34,0.15); color: var(--pending); }
    .test-card { background: var(--card); border: 1px solid var(--border);
      border-radius: 8px; padding: 14px 16px; margin-bottom: 10px;
      transition: border-color 0.2s; }
    .test-card.result-pass { border-left: 3px solid var(--pass); }
    .test-card.result-fail { border-left: 3px solid var(--fail); }
    .test-card.result-skip { border-left: 3px solid var(--skip); }
    .test-card.result-pending { border-left: 3px solid var(--pending); }
    .test-header { display: flex; gap: 10px; align-items: flex-start; flex-wrap: wrap; margin-bottom: 8px; }
    .test-id { font-family: monospace; font-size: 0.85rem; color: var(--muted); flex-shrink: 0; }
    .test-name { flex: 1; font-weight: 500; color: #e6edf3; }
    .bv-url { display: block; font-size: 0.82rem; color: var(--accent);
      margin-bottom: 8px; text-decoration: none; }
    .bv-url:hover { text-decoration: underline; }
    .test-steps { font-size: 0.85rem; color: var(--muted); padding-left: 18px;
      margin-bottom: 8px; }
    .expected { font-size: 0.82rem; color: #6e7681; font-style: italic;
      margin-bottom: 10px; }
    .radio-group { display: flex; gap: 6px; flex-wrap: wrap; margin: 8px 0; }
    .radio-label { display: flex; align-items: center; gap: 5px;
      padding: 5px 12px; border-radius: 6px; border: 1px solid var(--border);
      cursor: pointer; font-size: 0.85rem; user-select: none; transition: all 0.15s; }
    .radio-label:hover { border-color: var(--accent); }
    .radio-label input[type=radio] { display: none; }
    .radio-label.checked-pass { background: rgba(63,185,80,0.2); border-color: var(--pass); color: var(--pass); font-weight: 600; }
    .radio-label.checked-fail { background: rgba(248,81,73,0.2); border-color: var(--fail); color: var(--fail); font-weight: 600; }
    .radio-label.checked-skip { background: rgba(139,148,158,0.2); border-color: var(--skip); color: var(--skip); font-weight: 600; }
    .radio-label.checked-pending { background: rgba(210,153,34,0.2); border-color: var(--pending); color: var(--pending); font-weight: 600; }
    .notes-label { font-size: 0.75rem; color: var(--muted); margin-bottom: 4px; }
    .notes-input { width: 100%; padding: 7px 10px; background: var(--card) !important;
      border: 1px solid var(--border) !important; border-radius: 6px; color: var(--text) !important;
      font-family: inherit; font-size: 0.85rem; resize: vertical; min-height: 36px; }
    .notes-input::placeholder { color: var(--muted); }
    .notes-input:focus { outline: none; border-color: var(--accent); }
    .general-notes { background: var(--card); border: 1px solid var(--border);
      border-radius: 8px; padding: 16px; margin-bottom: 20px; }
    .general-notes textarea { width: 100%; min-height: 80px; padding: 10px 12px;
      background: var(--card); border: 1px solid var(--border); border-radius: 6px;
      color: var(--text); font-family: inherit; font-size: 0.9rem; resize: vertical; }
    .classification-select,
    .failure-type-select {
      background: var(--card) !important;
      color: var(--text) !important;
      border: 1px solid var(--border) !important;
    }
    .general-notes textarea:focus { outline: none; border-color: #bc8cff; }
    .general-notes-title { font-size: 1rem; font-weight: 600; color: #bc8cff;
      border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 12px; }
    .btn-row { display: flex; gap: 12px; justify-content: center; margin-top: 24px; }
    .btn { padding: 11px 28px; border: none; border-radius: 8px;
      font-size: 0.95rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
    .btn:hover { opacity: 0.85; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-submit { background: var(--pass); color: #0d1117; }
    .btn-resubmit { background: #21262d; color: var(--text); border: 1px solid var(--border); }
    .btn-mark-passed { background: #b45309; color: #fff; }
    #submit-result { margin-top: 16px; padding: 14px 18px; border-radius: 8px;
      font-size: 0.9rem; display: none; }
    #submit-result.ok { background: rgba(63,185,80,0.15); border: 1px solid var(--pass); }
    #submit-result.err { background: rgba(248,81,73,0.15); border: 1px solid var(--fail); }
    #submit-result a { color: var(--accent); }
    .read-only-badge { display: inline-block; background: rgba(63,185,80,0.15);
      border: 1px solid var(--pass); color: var(--pass); padding: 4px 12px;
      border-radius: 6px; font-size: 0.8rem; font-weight: 600; margin-left: 12px; }
    .test-card.submitted .radio-label { pointer-events: none; opacity: 0.85; }
    .test-card.submitted .notes-input { background: var(--bg) !important; pointer-events: none; }
    .paste-zone { border: 2px dashed var(--border); border-radius: 6px; padding: 8px 12px;
      margin-top: 8px; font-size: 0.82rem; color: var(--muted); cursor: text;
      transition: border-color 0.2s; user-select: none; }
    .paste-zone:focus, .paste-zone.drag-over { border-color: var(--accent); outline: none; }
    .paste-zone.has-image { border-color: var(--pass); color: var(--pass); }
    .attach-row { display: flex; align-items: center; gap: 8px; margin-top: 6px; }
    .attach-btn { display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px;
      background: var(--card) !important; border: 1px solid var(--border) !important; border-radius: 6px;
      font-size: 0.82rem; cursor: pointer; color: var(--text) !important; }
    .attach-btn:hover { border-color: var(--accent) !important; }
    .attach-btn input[type=file] { display: none; }
    .attach-name { font-size: 0.78rem; color: var(--muted); }
    .attach-thumb { margin-top: 6px; }
    .attach-thumb img { max-width: 160px; max-height: 120px; border-radius: 4px;
      border: 1px solid var(--border); }
    :root { --transition-speed: 0.25s; }
    body { transition: background-color var(--transition-speed), color var(--transition-speed); }
    [data-theme="light"] { --bg: #caced2; --card: #eef2f6; --border: #cbd5e1; --text: #1e293b; --muted: #64748b; }
    #theme-toggle { background: var(--card); border: 1px solid var(--border); color: var(--text); padding: 4px 10px; border-radius: 4px; cursor: pointer; margin-left: auto; transition: transform 0.1s ease, border-color 0.2s; font-size: 16px; }
    #theme-toggle:hover { border-color: var(--accent); }
    #theme-toggle:active { transform: scale(0.92); }
    .item-description { font-size: 13px !important; line-height: 1.5; color: #b0c4de !important; }
    [data-theme="light"] .item-description { color: var(--muted) !important; }
    .uat-help-fab {
      position: fixed; bottom: 24px; right: 24px; width: 48px; height: 48px;
      border-radius: 50%; background: var(--fail, #e74c3c); color: #fff; border: none;
      font-size: 20px; font-weight: bold; box-shadow: 0 4px 15px rgba(0,0,0,0.4);
      cursor: pointer; z-index: 10000; display: flex; align-items: center; justify-content: center;
    }
    #uat-cheat-sheet[popover] {
      width: min(420px, 90vw); max-height: 80vh; overflow-y: auto; padding: 20px;
      border-radius: 12px; border: 1px solid var(--border); background: var(--card);
      color: var(--text); box-shadow: 0 10px 30px rgba(0,0,0,0.5); margin: auto;
    }"""


def get_page_js(spec_id: str, pl_email: str, general_notes_json: str) -> str:
    """Return all JavaScript for the UAT page."""
    return f"""
  <script>
    // REQ-071: Light/dark theme toggle
    (function() {{
      var saved = localStorage.getItem('metapm-theme') || 'dark';
      document.documentElement.setAttribute('data-theme', saved);
      var btn = document.getElementById('theme-toggle');
      if (btn) {{
        btn.textContent = saved === 'dark' ? '\u2600\uFE0F' : '\U0001F319';
        btn.addEventListener('click', function() {{
          var current = document.documentElement.getAttribute('data-theme') || 'dark';
          var next = current === 'dark' ? 'light' : 'dark';
          document.documentElement.setAttribute('data-theme', next);
          btn.textContent = next === 'dark' ? '\u2600\uFE0F' : '\U0001F319';
          localStorage.setItem('metapm-theme', next);
        }});
      }}
    }})();
  </script>
  <script>
    const SPEC_ID = "{spec_id}";

    // MP24 REQ-057: Multi-note management
    let noteCounter = 0;
    function addNote() {{
      noteCounter++;
      const ts = new Date().toISOString().replace('T', ' ').substring(0, 19) + 'Z';
      const container = document.getElementById('notes-list');
      const entry = document.createElement('div');
      entry.className = 'note-entry';
      entry.style.cssText = 'background:#0d1117;border:1px solid #334155;border-radius:6px;padding:10px;margin-bottom:8px;position:relative';
      entry.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">` +
        `<span style="color:#8b949e;font-size:0.78rem">${{ts}}</span>` +
        `<div style="display:flex;gap:6px;align-items:center">` +
        `<select class="note-classification" style="padding:3px 6px;background:#161b22;color:#e2e8f0;border:1px solid #334155;border-radius:4px;font-size:0.78rem">` +
        `<option value="">No classification</option>` +
        `<option value="new_requirement">New requirement</option>` +
        `<option value="bug">Bug</option>` +
        `<option value="finding">Finding</option>` +
        `<option value="no_action">No-action</option>` +
        `<option value="out_of_scope">Out of scope</option>` +
        `</select>` +
        `<button onclick="this.closest('.note-entry').remove()" style="background:none;border:none;color:#f87171;cursor:pointer;font-size:1rem;padding:0 4px">&times;</button>` +
        `</div></div>` +
        `<div class="note-failure-type-row" style="display:none;margin-bottom:6px">` +
        `<label style="font-size:0.75rem;color:#8b949e;margin-bottom:4px;display:block">Failure Type</label>` +
        `<select class="note-failure-type" style="width:100%;padding:7px 10px;background:#0d1117;border:1px solid #334155;border-radius:6px;color:#e2e8f0;font-size:0.85rem">` +
        `<option value="">-- Select --</option>` +
        `<option value="wrong_spec">Wrong spec</option>` +
        `<option value="regression">Regression</option>` +
        `<option value="environment">Environment</option>` +
        `<option value="unclear_bv">Unclear BV</option>` +
        `<option value="machine_test_sent_to_pl">Machine test sent to PL</option>` +
        `<option value="no_5q_applied">No 5Q applied</option>` +
        `<option value="incomplete_spec">Incomplete spec</option>` +
        `<option value="missing_acceptance_criteria">Missing acceptance criteria</option>` +
        `<option value="incomplete_handoff">Incomplete handoff</option>` +
        `<option value="ui_rendering_bug">UI rendering bug</option>` +
        `<option value="data_mapping_bug">Data mapping bug</option>` +
        `<option value="filter_query_bug">Filter/query bug</option>` +
        `<option value="gate_validation_bug">Gate/validation bug</option>` +
        `<option value="navigation_routing_bug">Navigation/routing bug</option>` +
        `<option value="api_contract_bug">API contract bug</option>` +
        `<option value="state_management_bug">State management bug</option>` +
        `<option value="performance_bug">Performance bug</option>` +
        `<option value="other">Other</option>` +
        `</select>` +
        `</div>` +
        `<textarea class="note-text" placeholder="Enter note..." style="width:100%;min-height:50px;padding:6px;background:#161b22;color:#e2e8f0;border:1px solid #334155;border-radius:4px;resize:vertical;font-size:0.82rem"></textarea>`;
      container.appendChild(entry);

      // BUG-075: Wire classification → failure type cascade for General Notes
      const classSelect = entry.querySelector('.note-classification');
      const ftRow = entry.querySelector('.note-failure-type-row');
      classSelect.addEventListener('change', function() {{
        if (this.value === 'bug') {{
          ftRow.style.display = 'block';
        }} else {{
          ftRow.style.display = 'none';
          ftRow.querySelector('select').value = '';
        }}
        if (window.PortfolioDebug) {{
          window.PortfolioDebug.log('GeneralNotes', 'classification changed', {{
            value: classSelect.value,
            failureTypeVisible: classSelect.value === 'bug'
          }});
        }}
      }});
    }}

    function gatherNotes() {{
      const entries = [];
      document.querySelectorAll('.note-entry').forEach(entry => {{
        const text = entry.querySelector('.note-text')?.value || '';
        const classification = entry.querySelector('.note-classification')?.value || null;
        const failureType = entry.querySelector('.note-failure-type')?.value || null;
        const tsSpan = entry.querySelector('span');
        const timestamp = tsSpan ? tsSpan.textContent.trim() : null;
        if (text.trim()) {{
          const note = {{ timestamp, text: text.trim(), classification: classification || null }};
          if (classification === 'bug' && failureType) {{
            note.failure_type = failureType;
          }}
          entries.push(note);
        }}
      }});
      return entries;
    }}

    // Pre-populate existing notes on page load
    (function loadExistingNotes() {{
      const existingNotes = {general_notes_json};
      existingNotes.forEach(n => {{
        addNote();
        const entries = document.querySelectorAll('.note-entry');
        const last = entries[entries.length - 1];
        if (n.text) last.querySelector('.note-text').value = n.text;
        if (n.classification) {{
          last.querySelector('.note-classification').value = n.classification;
          if (n.classification === 'bug') {{
            const ftRow = last.querySelector('.note-failure-type-row');
            if (ftRow) ftRow.style.display = 'block';
          }}
        }}
        if (n.failure_type) {{
          const ftSelect = last.querySelector('.note-failure-type');
          if (ftSelect) ftSelect.value = n.failure_type;
        }}
        if (n.timestamp) last.querySelector('span').textContent = n.timestamp;
      }});
    }})();

    function updateCounts() {{
      const cards = document.querySelectorAll('.test-card:not([data-type="cc_machine"])');
      const machineCards = document.querySelectorAll('.test-card[data-type="cc_machine"]');
      let pass=0,fail=0,skip=0,pend=0;
      cards.forEach(card => {{
        const id = card.dataset.id;
        const checked = card.querySelector(`input[name="${{id}}"]:checked`);
        const val = checked ? checked.value : 'pending';
        card.querySelectorAll('.radio-label').forEach(l => l.className = l.className.replace(/\\bchecked-\\w+/g,''));
        if (checked) checked.closest('.radio-label')?.classList.add(`checked-${{val}}`);
        card.className = card.className.replace(/\\bresult-\\w+/g,'') + ` result-${{val}}`;
        if (val==='pass') pass++; else if(val==='fail') fail++; else if(val==='skip') skip++; else pend++;
      }});
      machineCards.forEach(card => {{ pass++; }});
      document.getElementById('cnt-total').textContent = cards.length + machineCards.length;
      document.getElementById('cnt-pass').textContent = pass;
      document.getElementById('cnt-fail').textContent = fail;
      document.getElementById('cnt-skip').textContent = skip;
      document.getElementById('cnt-pend').textContent = pend;
    }}

    // MP30: Data-driven failure schema — 2-level cascade
    let FAILURE_SCHEMA = {{}};

    async function loadFailureSchema() {{
      try {{
        const resp = await fetch('/api/config/failure-schema');
        FAILURE_SCHEMA = await resp.json();
        document.querySelectorAll('.failure-type-select').forEach(sel => {{
          const savedVal = sel.dataset.savedValue || '';
          sel.innerHTML = '<option value="">\\u2014 Select failure type \\u2014</option>';
          Object.entries(FAILURE_SCHEMA).forEach(([catCode, cat]) => {{
            const group = document.createElement('optgroup');
            group.label = cat.label;
            cat.types.forEach(t => {{
              const opt = new Option(t.text, t.value);
              if (t.value === savedVal) opt.selected = true;
              group.appendChild(opt);
            }});
            sel.appendChild(group);
          }});
        }});
        const container = document.getElementById('cheat-sheet-types');
        if (container) {{
          let html = '<h4>Failure Types</h4>';
          Object.entries(FAILURE_SCHEMA).forEach(([code, cat]) => {{
            html += '<div style="margin-bottom:10px">' +
              '<div style="font-size:11px;text-transform:uppercase;color:var(--muted);font-weight:600;margin:8px 0 4px">' + cat.label + '</div>' +
              '<ul style="margin:0;padding-left:16px;font-size:12px;line-height:1.6">';
            cat.types.forEach(t => {{
              const shortName = t.text.split(' \\u2014 ')[0] || t.text;
              html += '<li><strong>' + shortName + ':</strong> ' + t.help + '</li>';
            }});
            html += '</ul></div>';
          }});
          container.innerHTML = html;
        }}
      }} catch(e) {{
        console.error('Failed to load failure schema:', e);
      }}
    }}

    // MP31 REQ-070: Load classifications from DB
    async function loadClassifications() {{
      try {{
        const resp = await fetch('/api/config/uat-classifications');
        const classifications = await resp.json();
        document.querySelectorAll('.classification-select').forEach(sel => {{
          const savedVal = sel.value || sel.dataset.savedValue || '';
          sel.innerHTML = '<option value="">\\u2014 Select classification \\u2014</option>';
          classifications.forEach(c => {{
            const opt = new Option(c.display_label, c.display_label);
            if (c.display_label === savedVal) opt.selected = true;
            sel.appendChild(opt);
          }});
        }});
        const cheatContainer = document.getElementById('cheat-sheet-types');
        if (cheatContainer) {{
          const classHtml = `
            <h4 style="color:var(--info);border-bottom:1px solid var(--line);
                       padding-bottom:4px;margin:16px 0 8px;font-size:13px">
              Classifications
            </h4>
            <ul style="margin:0;padding-left:16px;font-size:12px;line-height:1.7">
            ${{classifications.map(c =>
              `<li><strong>${{c.display_label}}:</strong> ${{c.help_text}}</li>`
            ).join('')}}
            </ul>`;
          cheatContainer.insertAdjacentHTML('beforeend', classHtml);
        }}
      }} catch(e) {{
        console.error('Failed to load classifications:', e);
      }}
    }}

    function updateCascade(card) {{
      const id = card.dataset.id;
      const status = card.querySelector(`input[name="${{id}}"]:checked`)?.value || 'pending';
      const cascade = card.querySelector('.cascade-classification');
      const classSelect = card.querySelector('.classification-select');
      const ftRow = card.querySelector('.failure-type-section');
      if (!cascade) return;
      if (status === 'pass') {{
        cascade.style.display = 'none';
        if (classSelect) classSelect.value = 'No-action';
      }} else {{
        cascade.style.display = 'block';
      }}
      const classification = classSelect?.value || '';
      if (ftRow) {{
        ftRow.style.display = (classification === 'Bug') ? 'block' : 'none';
      }}
    }}

    // Wire radio buttons + classification selects for cascade
    document.querySelectorAll('.test-card:not([data-type="cc_machine"])').forEach(card => {{
      card.querySelectorAll('input[type="radio"]').forEach(r => {{
        r.addEventListener('change', () => {{
          updateCounts();
          updateCascade(card);
        }});
      }});
      const classSelect = card.querySelector('.classification-select');
      if (classSelect) {{
        classSelect.addEventListener('change', () => updateCascade(card));
      }}
      // BA41: notes textarea focus instrumentation
      const notesInput = card.querySelector('.notes-input');
      if (notesInput) {{
        notesInput.addEventListener('focus', () => {{
          if (window.PortfolioDebug) {{
            window.PortfolioDebug.log('BVCard', 'notes focused', {{bvId: card.dataset.id}});
          }}
        }});
      }}
    }});

    updateCounts();
    loadFailureSchema();
    loadClassifications();

    // ── Attachment support (MP07) ──
    const attachmentsMap = {{}};
    let generalNotesAttachments = [];

    function blobToBase64(blob) {{
      return new Promise(resolve => {{
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.readAsDataURL(blob);
      }});
    }}

    function showThumbInEl(el, mime, b64) {{
      if (el) el.innerHTML = `<img src="data:${{mime}};base64,${{b64}}">`;
    }}

    document.querySelectorAll('.paste-zone').forEach(zone => {{
      zone.addEventListener('paste', async e => {{
        e.preventDefault();
        const items = Array.from(e.clipboardData.items);
        const imgItem = items.find(i => i.type.startsWith('image/'));
        if (!imgItem) return;
        const b64 = await blobToBase64(imgItem.getAsFile());
        const att = [{{type:'image', mime: imgItem.type, data: b64, filename:'screenshot.png'}}];
        const id = zone.dataset.id;
        if (id) {{
          attachmentsMap[id] = att;
          showThumbInEl(document.getElementById(`athumb-${{id}}`), imgItem.type, b64);
        }} else {{
          generalNotesAttachments = att;
          showThumbInEl(document.getElementById('gn-attach-thumb'), imgItem.type, b64);
        }}
        zone.classList.add('has-image');
        zone.innerHTML = '✅ Screenshot captured <button class="remove-attach" onclick="removeAttach(this)" title="Remove screenshot" style="background:#7f1d1d;color:#fca5a5;border:none;border-radius:4px;padding:1px 6px;cursor:pointer;margin-left:8px;font-size:12px">✕</button>';
      }});
    }});

    function removeAttach(btn) {{
      const zone = btn.closest('.paste-zone');
      if (!zone) return;
      const id = zone.dataset.id;
      if (id) {{
        delete attachmentsMap[id];
        const thumb = document.getElementById(`athumb-${{id}}`);
        if (thumb) thumb.innerHTML = '';
      }} else {{
        generalNotesAttachments = [];
        const thumb = document.getElementById('gn-attach-thumb');
        if (thumb) thumb.innerHTML = '';
      }}
      zone.classList.remove('has-image');
      zone.innerHTML = '📷 Paste screenshot here (Ctrl+V)';
    }}

    document.querySelectorAll('.attach-input').forEach(input => {{
      input.addEventListener('change', async e => {{
        const file = e.target.files[0];
        if (!file) return;
        const b64 = await blobToBase64(file);
        const type = file.type.startsWith('image/') ? 'image' : 'file';
        const att = [{{type, mime: file.type, data: b64, filename: file.name}}];
        const id = input.dataset.id;
        attachmentsMap[id] = att;
        const nameEl = document.getElementById(`aname-${{id}}`);
        nameEl.innerHTML = `${{file.name}} (${{Math.round(file.size/1024)}}KB) <button class="remove-attach" onclick="removeFileAttach(this, '${{id}}')" title="Remove file" style="background:#7f1d1d;color:#fca5a5;border:none;border-radius:4px;padding:1px 6px;cursor:pointer;margin-left:6px;font-size:12px">✕</button>`;
        if (type === 'image') showThumbInEl(document.getElementById(`athumb-${{id}}`), file.type, b64);
      }});
    }});

    function removeFileAttach(btn, id) {{
      delete attachmentsMap[id];
      const nameEl = document.getElementById(`aname-${{id}}`);
      if (nameEl) nameEl.textContent = '';
      const thumb = document.getElementById(`athumb-${{id}}`);
      if (thumb) thumb.innerHTML = '';
      const input = document.querySelector(`.attach-input[data-id="${{id}}"]`);
      if (input) input.value = '';
    }}

    const gnInput = document.getElementById('gn-attach-input');
    if (gnInput) {{
      gnInput.addEventListener('change', async e => {{
        const file = e.target.files[0];
        if (!file) return;
        const b64 = await blobToBase64(file);
        const type = file.type.startsWith('image/') ? 'image' : 'file';
        generalNotesAttachments = [{{type, mime: file.type, data: b64, filename: file.name}}];
        document.getElementById('gn-attach-name').textContent = `${{file.name}} (${{Math.round(file.size/1024)}}KB)`;
        if (type === 'image') showThumbInEl(document.getElementById('gn-attach-thumb'), file.type, b64);
      }});
    }}

    async function reopenUAT(specId) {{
      const confirmed = confirm('Reopen this UAT for editing? Current results will be cleared.');
      if (!confirmed) return;
      const btn = document.querySelector('.btn-resubmit');
      if (btn) {{ btn.disabled = true; btn.textContent = '⏳ Reopening...'; }}
      try {{
        const r = await fetch(`/api/uat/${{specId}}/reopen`, {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}}
        }});
        if (r.ok) {{
          window.location.reload();
        }} else {{
          const data = await r.json();
          alert(`Reopen failed: ${{data.detail || JSON.stringify(data)}}`);
          if (btn) {{ btn.disabled = false; btn.textContent = '↩ Reopen & Edit Results'; }}
        }}
      }} catch(e) {{
        alert(`Reopen error: ${{e.message}}`);
        if (btn) {{ btn.disabled = false; btn.textContent = '↩ Reopen & Edit Results'; }}
      }}
    }}

    async function markAsPassed() {{
      const btn = document.querySelector('.btn-mark-passed');
      if (btn) {{ btn.disabled = true; btn.textContent = '⏳ Overriding...'; }}
      try {{
        const resp = await fetch(`/api/uat/${{SPEC_ID}}/override`, {{
          method: 'PATCH',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{ status: 'passed', override_note: 'PL override: conditional_pass → passed' }})
        }});
        const data = await resp.json();
        if (resp.ok) {{
          const div = document.getElementById('submit-result');
          div.style.display = 'block';
          div.className = 'ok';
          div.innerHTML = `Status overridden to <strong>passed</strong>. <a href="/uat/${{SPEC_ID}}">View UAT record &rarr;</a>`;
          if (btn) btn.style.display = 'none';
        }} else {{
          if (btn) {{ btn.disabled = false; btn.textContent = '✅ Mark as Passed'; }}
          alert(`Override failed: ${{data.detail || JSON.stringify(data)}}`);
        }}
      }} catch(e) {{
        if (btn) {{ btn.disabled = false; btn.textContent = '✅ Mark as Passed'; }}
        alert(`Override error: ${{e.message}}`);
      }}
    }}

    async function submitAcknowledge() {{
      if (!confirm('All items were machine-verified. Acknowledge and close?')) return;
      try {{
        const resp = await fetch(`/api/uat/${{SPEC_ID}}/pl-results`, {{
          method: 'PATCH',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{ test_cases: [], general_notes: [{{timestamp: new Date().toISOString(), text: 'All BVs machine-verified. PL acknowledged.', classification: null}}] }})
        }});
        if (resp.ok) {{
          const div = document.getElementById('submit-result');
          div.style.display = 'block';
          div.className = 'ok';
          div.innerHTML = 'Acknowledged. <a href="/uat/' + SPEC_ID + '">View UAT record &rarr;</a>';
        }} else {{
          const data = await resp.json();
          alert('Acknowledge failed: ' + (data.detail || JSON.stringify(data)));
        }}
      }} catch(e) {{ alert('Error: ' + e.message); }}
    }}

    async function submitResults() {{
      const confirmed = confirm(
        'Submit UAT results?\\n\\nThis will record your test results. ' +
        'You can reopen and edit results after submission.'
      );
      if (!confirmed) return;

      const cards = document.querySelectorAll('.test-card:not([data-type="cc_machine"])');
      const test_cases = [];
      let missingClassification = [];
      let hasFails = false;
      cards.forEach(card => {{
        if (card.dataset.type === 'cc_machine') return;
        const id = card.dataset.id;
        const checked = card.querySelector(`input[name="${{id}}"]:checked`);
        const status = checked ? checked.value : 'pending';
        const notes = card.querySelector('.notes-input')?.value || '';
        const attachments = attachmentsMap[id] || [];
        const classSelect = card.querySelector('.classification-select');
        const classification = classSelect ? classSelect.value : '';
        if (!classification && status !== 'pass') missingClassification.push(id);
        const ftSelect = card.querySelector('.failure-type-select');
        const failure_type = (ftSelect && classification === 'Bug') ? ftSelect.value : null;
        if (status === 'fail') hasFails = true;
        test_cases.push({{ id, status, notes, attachments, classification, failure_type }});
      }});
      if (missingClassification.length > 0) {{
        alert('Classification required for all BVs: ' + missingClassification.join(', '));
        return;
      }}
      const general_notes = gatherNotes();

      let sprintFailureType = null;
      const hasSkips = test_cases.some(tc => tc.status === 'skip');
      const allPassOrSkip = test_cases.every(tc => tc.status === 'pass' || tc.status === 'skip');
      if (!hasFails && hasSkips && allPassOrSkip) {{
        sprintFailureType = prompt('This UAT will be a conditional pass.\\nPlease select a failure type:\\n\\n' +
          '1. wrong_spec\\n2. regression\\n3. environment\\n4. unclear_bv\\n' +
          '5. incomplete_spec\\n6. other\\n\\nType the failure type:');
        if (!sprintFailureType) {{
          alert('Conditional pass requires a failure type.');
          return;
        }}
      }}

      const btn = document.getElementById('submit-btn');
      btn.disabled = true;
      btn.textContent = '⏳ Submitting...';

      const payload = {{ test_cases, general_notes, general_notes_attachments: generalNotesAttachments, submitted_by: '{pl_email}' }};
      if (sprintFailureType) payload.failure_type = sprintFailureType;

      try {{
        const resp = await fetch(`/api/uat/${{SPEC_ID}}/pl-results`, {{
          method: 'PATCH',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify(payload)
        }});
        const data = await resp.json();
        const div = document.getElementById('submit-result');
        div.style.display = 'block';
        if (resp.ok) {{
          window.location.replace('/uat/' + SPEC_ID);
          return;
        }} else {{
          btn.disabled = false;
          btn.textContent = '📤 Submit Results';
          div.className = 'err';
          const detail = data.detail;
          const msg = (typeof detail === 'object' && detail.message) ? detail.message : (typeof detail === 'string' ? detail : JSON.stringify(detail));
          div.textContent = `Error: ${{msg}}`;
        }}
      }} catch(e) {{
        btn.disabled = false;
        btn.textContent = '📤 Submit Results';
        const div = document.getElementById('submit-result');
        div.style.display = 'block';
        div.className = 'err';
        div.textContent = `Submit failed: ${{e.message}}`;
      }}
    }}
  </script>"""


def build_page_html(project: str, version: str, sprint: str, pth: str,
                    reqs: str, pl_email: str, spec_id: str,
                    cards_html: str, notes_html: str,
                    is_submitted: bool, spec_status: str,
                    general_notes_json: str) -> str:
    """Assemble the full UAT page from pre-rendered sections."""
    submitted_badge = '<span class="read-only-badge">✓ Submitted</span>' if is_submitted else ""
    resubmit_btn = (f'<button class="btn btn-resubmit" onclick="reopenUAT(\'{spec_id}\')">'
                    '↩ Reopen &amp; Edit Results</button>') if is_submitted else ""
    mark_passed_btn = ('<button class="btn btn-mark-passed" onclick="markAsPassed()">'
                       '✅ Mark as Passed</button>') if spec_status == "conditional_pass" else ""
    loop3_hint = ('  <div style="font-size:11px;color:#94a3b8;margin-top:6px;text-align:center">'
                  '⚡ Submitting fires Loop 3 automatically — requirements will be advanced within 2 minutes.'
                  '</div>') if not is_submitted else ''
    submit_result_attrs = f'class="ok" style="display:block"' if is_submitted else ''
    submit_result_content = (f'Results submitted. <a href="/uat/{spec_id}">View UAT record →</a>'
                             if is_submitted else '')

    css = get_page_css()
    js = get_page_js(spec_id, pl_email, general_notes_json)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{project} v{version} — UAT</title>
  <style>{css}</style>
</head>
<body>
  <header>
    <div style="display:flex;align-items:center;gap:8px">
      <h1 style="flex:1">{project} v{version} — UAT {submitted_badge}</h1>
      <button id="theme-toggle" title="Toggle Light/Dark Mode"></button>
    </div>
    <div class="meta">
      <span class="chip">v{version}</span>
      <span class="chip">PTH: {pth}</span>
      <span class="chip">{sprint}</span>
    </div>
    <div class="reqs"><strong>Requirements:</strong> {esc(reqs)}</div>
    <div class="pl-info">Authenticated as {esc(pl_email)} · <a href="/app/logout" style="color:var(--muted);font-size:0.8rem">Sign out</a></div>
  </header>

  <div class="summary-bar">
    <span class="label">Total</span><span class="count ct-total" id="cnt-total">0</span>
    <span class="label">Pass</span><span class="count ct-pass" id="cnt-pass">0</span>
    <span class="label">Fail</span><span class="count ct-fail" id="cnt-fail">0</span>
    <span class="label">Skip</span><span class="count ct-skip" id="cnt-skip">0</span>
    <span class="label">Pending</span><span class="count ct-pend" id="cnt-pend">0</span>
  </div>

  {cards_html}

  {notes_html}

  <div class="btn-row">
    <button class="btn btn-submit" id="submit-btn" onclick="submitResults()" {'style="display:none"' if is_submitted else ''}>📤 Submit Results</button>
    {resubmit_btn}
    {mark_passed_btn}
  </div>
  {loop3_hint}
  <div id="submit-result" {submit_result_attrs}>{submit_result_content}</div>

  {js}

  <button popovertarget="uat-cheat-sheet" class="uat-help-fab" title="UAT Rules &amp; Definitions">?</button>
  <div id="uat-cheat-sheet" popover>
    <div style="margin:0 0 12px;font-size:16px;font-weight:600">UAT Reference Guide <small style="font-size:11px;color:var(--muted);margin-left:6px">v2.83.0</small></div>
    <div style="background:rgba(248,81,73,0.1);border-left:4px solid var(--fail);padding:10px 12px;margin:0 0 16px;font-size:13px">
      <strong>Submission Rules:</strong>
      <ul style="margin:6px 0 0;padding-left:16px">
        <li><strong>Fail / Conditional Pass:</strong> Requires Classification + Failure Type</li>
        <li><strong>Skip / Pending:</strong> Requires Notes explaining why</li>
        <li><strong>Pass:</strong> No additional fields required</li>
      </ul>
    </div>
    <div id="cheat-sheet-types"><p style="color:var(--muted);font-size:12px">Loading...</p></div>
  </div>
</body>
</html>"""
