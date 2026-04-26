// Inspector v2 — single-direction, schema-aligned, with tabbed right pane and CRUD panels.

const { useState, useMemo, useEffect, useRef, useCallback } = React;

const ALL_LAYERS = ["frontend","backend","db","infra","algorithm","process"];
const ALL_PRIORITIES = ["P1","P2","P3"];

function highlight(text, query) {
  if (!query || !text) return text;
  try {
    const re = new RegExp("(" + query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig");
    const parts = String(text).split(re);
    return parts.map((p, i) => re.test(p) ? <mark key={i}>{p}</mark> : <span key={i}>{p}</span>);
  } catch { return text; }
}

function matchQ(b, q) {
  if (!q) return true;
  const hay = (b.code+" "+b.title+" "+b.description+" "+(b.tokens||[]).join(" ")+" "+(b.signals||[]).join(" ")).toLowerCase();
  return hay.includes(q.toLowerCase());
}

function fmtDate(s) {
  if (!s) return "—";
  const d = new Date(s);
  return d.toISOString().slice(0,10) + " " + d.toISOString().slice(11,16);
}

function SchemaFlag({ note }) {
  return <span className="schema-flag" title={note}>?schema</span>;
}

const STORAGE_KEY = "metapm-bug-classifier-v2";

// === API-backed persistence (replaces localStorage) ===
async function loadFromAPI() {
  try {
    const res = await fetch("/api/classifier/bootstrap");
    if (!res.ok) throw new Error(`Bootstrap failed: ${res.status}`);
    const data = await res.json();
    return {
      bugs: data.bugs || [],
      classifications: data.classifications || [],
      chains: data.chains || [],
    };
  } catch (e) {
    console.error("[API] Bootstrap failed, using seed fallback", e);
    return {
      bugs: window.BUGS || [],
      classifications: window.CLASSIFICATIONS || [],
      chains: window.BUG_CHAINS || [],
    };
  }
}

async function persistBugUpdate(code, classifications, bug_chain_ids) {
  try {
    const res = await fetch(`/api/bugs/${code}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ classifications, bug_chain_ids }),
    });
    if (!res.ok) throw new Error(`PATCH /api/bugs/${code} failed: ${res.status}`);
    console.log(`[API] Updated bug ${code}`);
  } catch (e) {
    console.error("[API] Bug update failed", e);
  }
}

async function persistClassification(cls, isUpdate = false) {
  try {
    const method = isUpdate ? "PATCH" : "POST";
    const url = isUpdate ? `/api/classifications/${cls.code}` : "/api/classifications";
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cls),
    });
    if (!res.ok) throw new Error(`${method} ${url} failed: ${res.status}`);
    console.log(`[API] ${isUpdate ? "Updated" : "Created"} classification ${cls.code || cls.name}`);
  } catch (e) {
    console.error("[API] Classification persist failed", e);
  }
}

async function deleteClassification(code) {
  try {
    const res = await fetch(`/api/classifications/${code}`, { method: "DELETE" });
    if (!res.ok) throw new Error(`DELETE /api/classifications/${code} failed: ${res.status}`);
    console.log(`[API] Deleted classification ${code}`);
  } catch (e) {
    console.error("[API] Classification delete failed", e);
  }
}

async function persistChain(chain, isUpdate = false) {
  try {
    const method = isUpdate ? "PATCH" : "POST";
    const url = isUpdate ? `/api/chains/${chain.id}` : "/api/chains";
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(chain),
    });
    if (!res.ok) throw new Error(`${method} ${url} failed: ${res.status}`);
    console.log(`[API] ${isUpdate ? "Updated" : "Created"} chain ${chain.id}`);
  } catch (e) {
    console.error("[API] Chain persist failed", e);
  }
}

async function deleteChain(id) {
  try {
    const res = await fetch(`/api/chains/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error(`DELETE /api/chains/${id} failed: ${res.status}`);
    console.log(`[API] Deleted chain ${id}`);
  } catch (e) {
    console.error("[API] Chain delete failed", e);
  }
}

async function addChainMember(chain_id, bug_code) {
  try {
    const res = await fetch(`/api/chains/${chain_id}/members`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: bug_code }),
    });
    if (!res.ok) throw new Error(`POST /api/chains/${chain_id}/members failed: ${res.status}`);
    console.log(`[API] Added ${bug_code} to chain ${chain_id}`);
  } catch (e) {
    console.error("[API] Chain member add failed", e);
  }
}

async function removeChainMember(chain_id, bug_code) {
  try {
    const res = await fetch(`/api/chains/${chain_id}/members/${bug_code}`, { method: "DELETE" });
    if (!res.ok) throw new Error(`DELETE /api/chains/${chain_id}/members/${bug_code} failed: ${res.status}`);
    console.log(`[API] Removed ${bug_code} from chain ${chain_id}`);
  } catch (e) {
    console.error("[API] Chain member remove failed", e);
  }
}

async function mergeChains(source_id, target_id) {
  try {
    const res = await fetch(`/api/chains/${source_id}/merge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target: target_id }),
    });
    if (!res.ok) throw new Error(`POST /api/chains/${source_id}/merge failed: ${res.status}`);
    console.log(`[API] Merged chain ${source_id} into ${target_id}`);
  } catch (e) {
    console.error("[API] Chain merge failed", e);
  }
}


function App() {
  const [bugs, setBugs] = useState([]);
  const [classifications, setClassifications] = useState([]);
  const [chains, setChains] = useState([]);
  const [loading, setLoading] = useState(true);

  // Load data from API on mount
  useEffect(() => {
    loadFromAPI().then(data => {
      setBugs(data.bugs);
      setClassifications(data.classifications);
      setChains(data.chains);
      setLoading(false);
    });
  }, []);

  const resetAll = () => {
    if (!confirm("Reload data from server?")) return;
    setLoading(true);
    loadFromAPI().then(data => {
      setBugs(data.bugs);
      setClassifications(data.classifications);
      setChains(data.chains);
      setLoading(false);
    });
  };

  const [query, setQuery] = useState("");

  const [layerF, setLayerF] = useState(new Set());
  const [priorityF, setPriorityF] = useState(new Set());
  const [showAssigned, setShowAssigned] = useState(true);
  const [showStatus, setShowStatus] = useState("open"); // "all" | "open" | "closed"
  const [noClsOnly, setNoClsOnly] = useState(false);

  const [selectedCode, setSelectedCode] = useState("BUG-085");
  const [tab, setTab] = useState("description"); // description | uat | sprints | reviews | state | chain
  const [crudOpen, setCrudOpen] = useState(null); // null | "classifications" | "chains"
  const [popover, setPopover] = useState(null); // { kind, x, y } for quick-edit

  const filtered = useMemo(() => bugs.filter(b => {
    if (showStatus !== "all" && b.status !== showStatus) return false;
    if (!showAssigned && b.bug_chain_id) return false;
    if (layerF.size && !layerF.has(b.layer)) return false;
    if (priorityF.size && !priorityF.has(b.priority)) return false;
    if (noClsOnly && (b.classifications && b.classifications.length > 0)) return false;
    if (!matchQ(b, query)) return false;
    return true;
  }), [bugs, query, layerF, priorityF, showAssigned, showStatus, noClsOnly]);

  const sel = bugs.find(b => b.code === selectedCode) || filtered[0];

  // Update bug helper - updates local state and syncs to API
  const updateBug = (code, patch) => {
    setBugs(bs => bs.map(b => b.code === code ? { ...b, ...patch, updated_at: new Date().toISOString() } : b));

    // If classifications or bug_chain_ids changed, persist to API
    if ("classifications" in patch || "bug_chain_ids" in patch) {
      const bug = bugs.find(b => b.code === code);
      if (bug) {
        const classifications = patch.classifications !== undefined ? patch.classifications : bug.classifications;
        const bug_chain_ids = patch.bug_chain_ids !== undefined ? patch.bug_chain_ids : bug.bug_chain_ids;
        persistBugUpdate(code, classifications, bug_chain_ids);
      }
    }
  };

  // Keyboard shortcuts
  useEffect(() => {
    const onKey = (e) => {
      if (e.target && (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA")) return;
      if (e.key === "j") setSelectedCode(c => {
        const i = filtered.findIndex(b => b.code === c);
        return filtered[Math.min(filtered.length-1, i+1)]?.code || c;
      });
      if (e.key === "k") setSelectedCode(c => {
        const i = filtered.findIndex(b => b.code === c);
        return filtered[Math.max(0, i-1)]?.code || c;
      });
      if (e.key === "c") setPopover({ kind: "classification" });
      if (e.key === "h") setPopover({ kind: "chain" });
      if (e.key === "1") setTab("description");
      if (e.key === "2") setTab("uat");
      if (e.key === "3") setTab("sprints");
      if (e.key === "4") setTab("reviews");
      if (e.key === "5") setTab("state");
      if (e.key === "6") setTab("chain");
      if (e.key === "Escape") { setPopover(null); setCrudOpen(null); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [filtered]);

  const toggleSet = (set, v, setter) => { const n = new Set(set); n.has(v) ? n.delete(v) : n.add(v); setter(n); };

  // Sibling search by token overlap
  const siblings = useMemo(() => {
    if (!sel) return [];
    return bugs.filter(b => b.code !== sel.code)
      .map(b => ({ b, overlap: (b.tokens||[]).filter(t => (sel.tokens||[]).includes(t)).length }))
      .filter(x => x.overlap >= 2)
      .sort((a,b) => b.overlap - a.overlap)
      .slice(0, 8);
  }, [sel, bugs]);

  return (
    <div style={S.root}>
      {/* === Topbar === */}
      <div style={S.topbar}>
        <div style={{display:'flex', alignItems:'center', gap: 10}}>
          <div style={S.brandDot}></div>
          <div>
            <div style={{fontWeight: 600, fontSize: 13}}>MetaPM · Bug Classifier</div>
            <div style={{fontSize: 10.5, color: 'var(--ink-3)'}}>Inspector v2 · schema-aligned</div>
          </div>
        </div>
        <div style={{display:'flex', alignItems:'center', gap: 8}}>
          <button className="btn" onClick={() => setCrudOpen("classifications")}>
            Classifications <span className="mono" style={{color:'var(--ink-3)'}}>{classifications.filter(c=>c.active).length}</span>
          </button>
          <button className="btn" onClick={() => setCrudOpen("chains")}>
            Bug chains <span className="mono" style={{color:'var(--ink-3)'}}>{chains.length}</span>
          </button>
          <button className="btn" onClick={() => {
            const payload = { _exportedAt: new Date().toISOString(), bugs, classifications, chains };
            const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });

            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = `metapm-classifier-export-${new Date().toISOString().slice(0,10)}.json`;
            a.click();
            URL.revokeObjectURL(a.href);
          }} title="Export current state as JSON for prod migration">
            ⬇ export
          </button>
          <span style={{width: 1, height: 20, background:'var(--rule)'}}></span>
          <span className="mono" style={{fontSize: 11, color:'var(--ink-3)'}}>
            {filtered.length}/{bugs.length} bugs
          </span>
          <span style={{width: 1, height: 20, background:'var(--rule)'}}></span>
          <span title={loading ? "loading..." : "connected to MetaPM"}
            style={{display:'inline-flex', alignItems:'center', gap: 4, fontSize: 10.5, color: loading ? 'var(--ink-3)' : 'oklch(45% 0.10 145)'}}>
            <span style={{width: 6, height: 6, borderRadius:'50%', background: loading ? 'var(--ink-4)' : 'oklch(60% 0.12 145)'}}></span>
            {loading ? 'loading...' : 'live'}
          </span>
          <button className="btn ghost" style={{fontSize: 11, color:'var(--ink-3)'}} onClick={resetAll}>reload</button>
        </div>
      </div>

      {/* === Body 3-pane === */}
      <div style={S.body}>
        {/* Pane 1: queue */}
        <div style={S.pane}>
          <div style={S.paneHead}>
            <div style={S.paneTitle}>Queue</div>
            <div style={{display:'flex', gap: 4}}>
              <span className="kbd">j</span><span className="kbd">k</span>
              <span style={{fontSize:10.5, color:'var(--ink-3)'}}>nav</span>
            </div>
          </div>
          <div style={{padding:'8px 10px', borderBottom:'1px solid var(--rule)'}}>
            <input className="input" placeholder="search title/description/code/token…"
              value={query} onChange={e=>setQuery(e.target.value)} />
            <div style={{display:'flex', flexWrap:'wrap', gap: 4, marginTop: 7}}>
              {ALL_PRIORITIES.map(p => (
                <button key={p} className="btn sm" onClick={()=>toggleSet(priorityF,p,setPriorityF)}
                  style={priorityF.has(p) ? S.btnActive : {}}>
                  <span className={`pill ${p.toLowerCase()}`} style={{padding:'0 5px'}}>{p}</span>
                </button>
              ))}
              {ALL_LAYERS.map(l => (
                <button key={l} className="btn sm" onClick={()=>toggleSet(layerF,l,setLayerF)}
                  style={layerF.has(l) ? S.btnActive : {}}>
                  <span style={{fontSize: 10.5}}>{l}</span>
                </button>
              ))}
              <button className="btn sm" onClick={()=>setShowAssigned(s=>!s)}
                style={!showAssigned ? S.btnActive : {}}>
                <span style={{fontSize: 10.5}}>{showAssigned ? "all" : "unassigned"}</span>
              </button>
              <button className="btn sm" onClick={()=>setNoClsOnly(s=>!s)}
                style={noClsOnly ? S.btnActive : {}} title="Show only bugs with no classification assigned">
                <span style={{fontSize: 10.5}}>no cls</span>
              </button>
              <select className="input" style={{width:'auto', fontSize:11, padding:'2px 6px'}}
                value={showStatus} onChange={e=>setShowStatus(e.target.value)}>
                <option value="open">open</option>
                <option value="all">all status</option>
                <option value="closed">closed</option>
              </select>
            </div>
          </div>
          <div className="scroll" style={S.queueList}>
            {filtered.map(b => {
              const isSel = b.code === sel?.code;
              const ch = b.bug_chain_id && chains.find(c => c.id === b.bug_chain_id);
              return (
                <div key={b.code} onClick={()=>setSelectedCode(b.code)}
                  style={{...S.queueRow,
                    background: isSel ? 'var(--bg-sunk)' : 'transparent',
                    borderLeft: isSel ? '2px solid var(--ink)' : '2px solid transparent'}}>
                  <div style={{display:'flex', justifyContent:'space-between', alignItems:'baseline', gap:6}}>
                    <span className="mono" style={{fontSize: 10.5, color:'var(--ink-3)'}}>{b.code}</span>
                    <div style={{display:'flex', gap:3}}>
                      <span className={`pill ${b.priority.toLowerCase()}`}>{b.priority}</span>
                      <span className={`pill layer-${b.layer}`}>{b.layer}</span>
                    </div>
                  </div>
                  <div style={{fontSize: 12.5, lineHeight: 1.35, marginTop: 3, color:'var(--ink)', textWrap:'pretty'}}>
                    {highlight(b.title, query)}
                  </div>
                  <div style={{marginTop: 5, display:'flex', gap: 4, flexWrap:'wrap', alignItems:'center'}}>
                    {b.classifications?.length ? b.classifications.map(c => (
                      <span key={c} className="pill" style={{background:'oklch(96% 0.04 280)', color:'oklch(38% 0.10 280)', fontSize: 10.5, padding:'1px 6px'}}>{c}</span>
                    )) : (
                      <span style={{fontSize: 10.5, color:'oklch(58% 0.14 30)', fontWeight: 500, letterSpacing: '0.02em'}}>⚠ no cls</span>
                    )}
                  </div>
                  {ch && (
                    <div style={{marginTop: 3, fontSize: 10.5}}>
                      <span className="mono" style={{color:'var(--accent)', fontWeight: 600}}>● {ch.pattern_label}</span>
                      <span className="mono" style={{color:'var(--ink-4)', marginLeft: 4}}>×{ch.total_occurrences}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Pane 2: detail header + tab content */}
        <div style={S.pane}>
          <div style={S.detailHeader}>
            <div style={{display:'flex', alignItems:'center', gap: 8, flexWrap:'wrap'}}>
              <span className="mono" style={{fontSize: 12, color:'var(--ink-2)', fontWeight:600}}>{sel?.code}</span>
              <span className={`pill ${sel?.priority.toLowerCase()}`}>{sel?.priority}</span>
              <span className={`pill layer-${sel?.layer}`}>{sel?.layer}</span>
              <span className="pill">{sel?.status}</span>
              <span className="pill">age {sel?.age}d</span>
              {sel?.pth && <span className="mono pill">{sel.pth}</span>}
              {sel?.sprint_id && <span className="mono pill">{sel.sprint_id}</span>}
            </div>
            <h2 style={S.detailTitle}>{highlight(sel?.title, query)}</h2>
            {/* Quick-edit chips row */}
            <div style={{display:'flex', gap: 6, flexWrap:'wrap', marginTop: 6, alignItems:'center'}}>
              <QuickEdit label="cls" multi values={sel?.classifications || []} hotkey="c"
                options={classifications.filter(c=>c.active).map(c=>({value: c.name, description: c.description}))}
                onSet={vs => updateBug(sel.code, { classifications: vs })} />
              <QuickEdit label="chain" value={sel?.bug_chain_id} hotkey="h"
                options={chains.map(c=>({value: c.id, description: `${c.pattern_label}\n\n${c.expected_outcome || ''}`}))}
                onSet={v => {
                  updateBug(sel.code, { bug_chain_id: v });
                  if (v) setChains(cs => cs.map(c => c.id===v && !c.member_requirement_codes.includes(sel.code)
                    ? {...c, member_requirement_codes: [...c.member_requirement_codes, sel.code], total_occurrences: c.total_occurrences+1}
                    : c));
                }} />
              <a className="btn ghost" style={{fontSize: 11, color:'var(--ink-3)'}}
                href={`https://metapm.rentyourcio.com/bug/${sel?.code}`} target="_blank">
                ↗ open in MetaPM
              </a>
            </div>
          </div>

          <div className="tabs">
            {[
              ["description", "Description", null],
              ["uat", "UAT history", sel?.uat_walks?.length || 0],
              ["sprints", "Sprints", sel?.sprints?.length || 0],
              ["reviews", "Reviews", sel?.reviews?.length || 0],
              ["state", "State", sel?.history?.length || 0],
              ["chain", "Chain", null],
            ].map(([id, label, count]) => (
              <div key={id} className={`tab ${tab===id?'active':''}`} onClick={()=>setTab(id)}>
                {label}{count!=null && <span className="count">{count}</span>}
              </div>
            ))}
          </div>

          <div className="scroll" style={{flex: 1, overflowY:'auto'}}>
            {tab === "description" && <DescriptionTab bug={sel} query={query} siblings={siblings} onSelect={setSelectedCode} />}
            {tab === "uat" && <UATTab bug={sel} />}
            {tab === "sprints" && <SprintsTab bug={sel} />}
            {tab === "reviews" && <ReviewsTab bug={sel} />}
            {tab === "state" && <StateTab bug={sel} />}
            {tab === "chain" && <ChainTab bug={sel} chains={chains} setChains={setChains} bugs={bugs} updateBug={updateBug} />}
          </div>
        </div>

        {/* Pane 3: outline / shortcuts */}
        <div style={S.pane}>
          <div style={S.paneHead}>
            <div style={S.paneTitle}>Outline</div>
          </div>
          <div className="scroll" style={{padding: 12, overflowY:'auto'}}>
            <OutlineSummary bug={sel} chains={chains} />
            <div className="divider"></div>
            <div style={{fontSize: 10.5, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.06em', fontWeight: 600, marginBottom: 6}}>Shortcuts</div>
            {[
              ["j / k", "next / prev bug"],
              ["1 – 6", "switch tab"],
              ["c", "set classification"],
              ["h", "set chain"],
              ["esc", "close popover"],
            ].map(([k, d]) => (
              <div key={k} style={{display:'flex', alignItems:'center', gap: 8, fontSize: 11, marginBottom: 3, color:'var(--ink-2)'}}>
                <span className="kbd" style={{minWidth: 50, textAlign:'center'}}>{k}</span>
                <span>{d}</span>
              </div>
            ))}
            <div className="divider"></div>
            <div style={{fontSize: 10.5, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.06em', fontWeight: 600, marginBottom: 6}}>Schema source</div>
            <div style={{fontSize: 11, lineHeight: 1.5, color:'var(--ink-2)'}}>
              All field names mirror tables at <span className="mono">/erd</span>. Three fields are flagged <span className="schema-flag">?schema</span> pending confirmation:
              <ul style={{paddingLeft: 16, margin: '6px 0', fontSize: 10.5}}>
                <li><span className="mono">uat_results.classifications</span> (multi)</li>
                <li><span className="mono">bug_chains.missing_signal</span></li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Popover quick-edit */}
      {popover && (
        <PopoverEdit kind={popover.kind} bug={sel}
          classifications={classifications} chains={chains}
          onClose={() => setPopover(null)}
          onSet={(field, value) => { updateBug(sel.code, { [field]: value }); if (field !== 'classifications') setPopover(null); }}
        />
      )}

      {/* CRUD modals */}
      {crudOpen === "classifications" && <CrudModal title="Classifications" subtitle={<>Promote PL's free-text <span className="mono">uat_results.classification</span> to a typed lookup. <SchemaFlag note="Brief says classification is currently free-text on uat_results; ERD doesn't show this column. Confirm before production wiring." /></>}
        items={classifications} setItems={setClassifications}
        fields={[{key:'name', label:'Name', width:200}, {key:'description', label:'Description', width:'1fr'}]}
        onClose={() => setCrudOpen(null)} hasOrder hasActive />}
      {crudOpen === "chains" && <ChainsModal chains={chains} setChains={setChains} bugs={bugs} setBugs={setBugs} onClose={() => setCrudOpen(null)} />}
    </div>
  );
}

function QuickEdit({ label, value, values, multi, hotkey, options, onSet }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return;
    const onClick = (e) => { if (!ref.current?.contains(e.target)) setOpen(false); };
    setTimeout(() => document.addEventListener("click", onClick), 10);
    return () => document.removeEventListener("click", onClick);
  }, [open]);

  const display = multi
    ? (values?.length ? (values.length === 1 ? values[0] : `${values[0]} +${values.length-1}`) : "—")
    : (value || "—");
  const isSet = multi ? (values?.length > 0) : !!value;

  const toggle = (v) => {
    if (multi) {
      const next = (values || []).includes(v) ? values.filter(x => x !== v) : [...(values || []), v];
      onSet(next);
    } else {
      onSet(v);
      setOpen(false);
    }
  };
  const isActive = (v) => multi ? (values || []).includes(v) : value === v;
  const clear = () => { multi ? onSet([]) : onSet(null); if (!multi) setOpen(false); };

  return (
    <div style={{position: 'relative'}} ref={ref}>
      <button className="btn sm" onClick={() => setOpen(o => !o)}
        style={isSet ? {} : {borderStyle:'dashed', color:'var(--ink-3)'}}>
        <span style={{color:'var(--ink-3)', fontSize: 10.5}}>{label}</span>
        <span style={{fontSize: 11.5, fontWeight: 500}}>{display}</span>
        <span className="kbd" style={{marginLeft: 4}}>{hotkey}</span>
      </button>
      {open && (
        <div className="popover" style={{top: 'calc(100% + 4px)', left: 0, padding: '4px 0', minWidth: 320, maxWidth: 420}}>
          {multi && (
            <div style={{padding:'6px 10px 4px', display:'flex', justifyContent:'space-between', alignItems:'center', borderBottom:'1px solid var(--rule)'}}>
              <span style={{fontSize: 10.5, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.06em', fontWeight: 600}}>Select all that apply</span>
              <button className="btn ghost sm" onClick={clear} style={{fontSize: 10.5, padding:'1px 6px'}}>clear</button>
            </div>
          )}
          {!multi && (
            <div className="popover-row" onClick={clear}
              style={{color:'var(--ink-3)', fontStyle:'italic'}}>— clear —</div>
          )}
          {options.map(o => {
            const v = typeof o === 'string' ? o : o.value;
            const desc = typeof o === 'string' ? null : o.description;
            const active = isActive(v);
            return (
              <div key={v} className={`popover-row ${active?'active':''}`}
                onClick={() => toggle(v)}
                style={{flexDirection: 'row', alignItems: 'flex-start', gap: 8, padding: '7px 10px'}}>
                {multi && (
                  <span style={{flexShrink: 0, marginTop: 2, width: 14, height: 14, borderRadius: 3, border: '1.5px solid '+(active?'var(--ink)':'var(--rule-strong)'), background: active?'var(--ink)':'var(--bg-elev)', display:'flex', alignItems:'center', justifyContent:'center'}}>
                    {active && <span style={{color:'var(--bg-elev)', fontSize: 10, lineHeight: 1}}>✓</span>}
                  </span>
                )}
                <div style={{display:'flex', flexDirection:'column', gap: 2, minWidth: 0, flex: 1}}>
                  <span className="mono" style={{fontSize: 11.5, fontWeight: 500}}>{v}</span>
                  {desc && <span style={{fontSize: 10.5, color:'var(--ink-3)', lineHeight: 1.4, fontFamily:'var(--sans)', textWrap:'pretty', whiteSpace:'pre-wrap'}}>{desc}</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function PopoverEdit({ kind, bug, classifications, chains, onClose, onSet }) {
  const opts = kind === "classification" ? classifications.filter(c=>c.active).map(c=>({value: c.name, description: c.description}))
             : chains.map(c=>({value: c.id, description: `${c.pattern_label}\n\n${c.expected_outcome || ''}`}));
  const isMulti = kind === "classification";
  const field = kind === "chain" ? "bug_chain_id" : isMulti ? "classifications" : kind;
  const cur = bug?.[field];

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" style={{minWidth: 360, maxWidth: 460}} onClick={e=>e.stopPropagation()}>
        <div style={{padding: '12px 14px', borderBottom: '1px solid var(--rule)'}}>
          <div style={{fontSize: 10.5, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.06em', fontWeight: 600}}>
            Set {kind.replace("_"," ")}
          </div>
          <div style={{fontSize: 13, marginTop: 2}}>{bug?.code} · <span style={{color:'var(--ink-3)'}}>{bug?.title.slice(0, 60)}…</span></div>
        </div>
        <div style={{maxHeight: 360, overflowY: 'auto'}}>
          {isMulti ? (
            <div style={{padding:'8px 12px', display:'flex', justifyContent:'space-between', alignItems:'center', borderBottom:'1px solid var(--rule)'}}>
              <span style={{fontSize: 11, color:'var(--ink-3)'}}>Select all that apply · multiple classes welcome</span>
              <button className="btn sm" onClick={() => onSet(field, [])}>clear</button>
            </div>
          ) : (
            <div className="popover-row" onClick={() => onSet(field, null)}
              style={{color:'var(--ink-3)', fontStyle:'italic'}}>— clear —</div>
          )}
          {opts.map(o => {
            const active = isMulti ? (cur || []).includes(o.value) : cur === o.value;
            return (
              <div key={o.value} className={`popover-row ${active?'active':''}`}
                onClick={() => {
                  if (isMulti) {
                    const next = active ? cur.filter(x => x !== o.value) : [...(cur || []), o.value];
                    onSet(field, next);
                  } else {
                    onSet(field, o.value);
                  }
                }}
                style={{flexDirection: 'row', alignItems: 'flex-start', gap: 10, padding: '8px 12px'}}>
                {isMulti && (
                  <span style={{flexShrink: 0, marginTop: 2, width: 16, height: 16, borderRadius: 3, border: '1.5px solid '+(active?'var(--ink)':'var(--rule-strong)'), background: active?'var(--ink)':'var(--bg-elev)', display:'flex', alignItems:'center', justifyContent:'center'}}>
                    {active && <span style={{color:'var(--bg-elev)', fontSize: 11, lineHeight: 1}}>✓</span>}
                  </span>
                )}
                <div style={{display:'flex', flexDirection:'column', gap: 2, flex: 1, minWidth: 0}}>
                  <span className="mono" style={{fontSize: 12, fontWeight: 500}}>{o.value}</span>
                  {o.description && <span style={{fontSize: 11, color:'var(--ink-3)', lineHeight: 1.45, fontFamily:'var(--sans)', textWrap:'pretty', whiteSpace:'pre-wrap'}}>{o.description}</span>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

window.App = App;
window.fmtDate = fmtDate;
window.SchemaFlag = SchemaFlag;
window.highlight = highlight;

const S = {
  root: {width:'100%', height:'100%', display:'flex', flexDirection:'column', background:'var(--bg)', overflow:'hidden', position:'relative'},
  topbar: {display:'flex', justifyContent:'space-between', alignItems:'center', padding:'8px 14px', borderBottom:'1px solid var(--rule)', background:'var(--bg-elev)', flexShrink: 0},
  brandDot: {width: 22, height: 22, borderRadius: 5, background:'linear-gradient(135deg, oklch(55% 0.13 30), oklch(45% 0.10 280))'},
  body: {flex:1, display:'grid', gridTemplateColumns:'320px 1fr 280px', minHeight: 0},
  pane: {display:'flex', flexDirection:'column', borderRight:'1px solid var(--rule)', minHeight:0, background:'var(--bg-elev)'},
  paneHead: {display:'flex', justifyContent:'space-between', alignItems:'center', padding:'8px 12px', borderBottom:'1px solid var(--rule)'},
  paneTitle: {fontSize: 12, fontWeight: 600, textTransform:'uppercase', letterSpacing:'0.06em', color:'var(--ink-2)'},
  queueList: {overflowY:'auto', flex:1},
  queueRow: {padding:'8px 10px', borderBottom:'1px solid var(--rule)', cursor:'pointer'},
  detailHeader: {padding:'12px 16px 10px', borderBottom:'1px solid var(--rule)'},
  detailTitle: {fontSize: 17, lineHeight: 1.3, margin: '8px 0 0', fontWeight: 500, textWrap:'pretty'},
  btnActive: {background:'var(--ink)', color:'var(--bg-elev)', borderColor:'var(--ink)'},
};
window.S = S;
