// CRUD modal components.

const { useState: cuS } = React;

function CrudModal({ title, subtitle, items, setItems, fields, onClose, hasOrder, hasActive }) {
  const [draft, setDraft] = cuS(items.map(i => ({...i})));
  const dirty = JSON.stringify(draft) !== JSON.stringify(items);

  const update = (id, patch) => setDraft(d => d.map(x => x.id === id ? {...x, ...patch} : x));
  const remove = (id) => setDraft(d => d.filter(x => x.id !== id));
  const add = () => {
    const id = "new-" + Date.now();
    const blank = { id, active: true };
    fields.forEach(f => blank[f.key] = "");
    setDraft(d => [...d, blank]);
  };
  const move = (id, dir) => setDraft(d => {
    const i = d.findIndex(x => x.id === id);
    const j = i + dir;
    if (j < 0 || j >= d.length) return d;
    const next = [...d];
    [next[i], next[j]] = [next[j], next[i]];
    return next;
  });

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" style={{minWidth: 720, maxWidth: 880}} onClick={e=>e.stopPropagation()}>
        <div style={{padding: '14px 16px', borderBottom: '1px solid var(--rule)'}}>
          <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
            <div style={{fontWeight: 600, fontSize: 14}}>{title}</div>
            <button className="btn ghost" onClick={onClose}>✕</button>
          </div>
          {subtitle && <div style={{fontSize: 11.5, color:'var(--ink-3)', marginTop: 4, lineHeight: 1.5}}>{subtitle}</div>}
        </div>

        <div className="scroll" style={{flex: 1, overflowY:'auto', padding: '10px 16px'}}>
          <div style={{
            display:'grid',
            gridTemplateColumns: `${hasOrder?'40px ':''}${fields.map(f => typeof f.width==='number'?f.width+'px':f.width).join(' ')} ${hasActive?'80px ':''}50px`,
            gap: 6, alignItems:'center',
            fontSize: 10.5, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.06em', fontWeight: 600,
            padding:'6px 0', borderBottom:'1px solid var(--rule)'
          }}>
            {hasOrder && <span></span>}
            {fields.map(f => <span key={f.key}>{f.label}</span>)}
            {hasActive && <span>active</span>}
            <span></span>
          </div>
          {draft.map((item, i) => (
            <div key={item.id} style={{
              display:'grid',
              gridTemplateColumns: `${hasOrder?'40px ':''}${fields.map(f => typeof f.width==='number'?f.width+'px':f.width).join(' ')} ${hasActive?'80px ':''}50px`,
              gap: 6, alignItems:'center', padding:'6px 0', borderBottom:'1px solid var(--rule)'
            }}>
              {hasOrder && (
                <div style={{display:'flex', gap: 2}}>
                  <button className="btn ghost sm" disabled={i===0} onClick={()=>move(item.id, -1)} style={{padding:'1px 4px'}}>↑</button>
                  <button className="btn ghost sm" disabled={i===draft.length-1} onClick={()=>move(item.id, 1)} style={{padding:'1px 4px'}}>↓</button>
                </div>
              )}
              {fields.map(f => (
                <input key={f.key} className="input" value={item[f.key] || ""}
                  onChange={e => update(item.id, {[f.key]: e.target.value})} />
              ))}
              {hasActive && (
                <label style={{display:'flex', alignItems:'center', gap: 4, fontSize: 11}}>
                  <input type="checkbox" checked={item.active !== false}
                    onChange={e => update(item.id, {active: e.target.checked})} />
                  <span>{item.active !== false ? 'on':'off'}</span>
                </label>
              )}
              <button className="btn ghost sm danger" onClick={()=>remove(item.id)}>🗑</button>
            </div>
          ))}
          <button className="btn sm" onClick={add} style={{marginTop: 10}}>+ Add row</button>
        </div>

        <div style={{padding:'10px 16px', borderTop:'1px solid var(--rule)', display:'flex', justifyContent:'space-between', alignItems:'center'}}>
          <div style={{fontSize: 11, color:'var(--ink-3)'}}>{dirty ? <span style={{color:'oklch(50% 0.12 60)'}}>● unsaved changes</span> : 'no changes'}</div>
          <div style={{display:'flex', gap: 6}}>
            <button className="btn" onClick={onClose}>cancel</button>
            <button className="btn primary" disabled={!dirty} onClick={() => { setItems(draft); onClose(); }}>save</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ChainsModal({ chains, setChains, bugs, setBugs, onClose }) {
  const [draft, setDraft] = cuS(chains.map(c => ({...c, member_requirement_codes: [...(c.member_requirement_codes||[])]})));
  const [draftBugs, setDraftBugs] = cuS(bugs.map(b => ({...b}))); // local mirror so member changes can be cancelled
  const [editing, setEditing] = cuS(null);
  const [memberQuery, setMemberQuery] = cuS("");
  const [chainQuery, setChainQuery] = cuS("");
  const [mergeTarget, setMergeTarget] = cuS(null);
  const dirty = JSON.stringify(draft) !== JSON.stringify(chains) || JSON.stringify(draftBugs) !== JSON.stringify(bugs);
  const cur = draft.find(c => c.id === editing);

  // Mutate a chain's members AND keep bug.bug_chain_id in sync.
  const addMember = (chainId, code) => {
    setDraft(d => d.map(c => c.id === chainId
      ? { ...c, member_requirement_codes: c.member_requirement_codes.includes(code) ? c.member_requirement_codes : [...c.member_requirement_codes, code], total_occurrences: (c.member_requirement_codes.includes(code) ? c.total_occurrences : (c.total_occurrences||0)+1) }
      : { ...c, member_requirement_codes: c.member_requirement_codes.filter(x => x !== code) })); // remove from any other chain (1:N)
    setDraftBugs(bs => bs.map(b => b.code === code ? { ...b, bug_chain_id: chainId } : b));
  };
  const removeMember = (chainId, code) => {
    setDraft(d => d.map(c => c.id === chainId
      ? { ...c, member_requirement_codes: c.member_requirement_codes.filter(x => x !== code), total_occurrences: Math.max(0,(c.total_occurrences||1)-1) }
      : c));
    setDraftBugs(bs => bs.map(b => (b.code === code && b.bug_chain_id === chainId) ? { ...b, bug_chain_id: null } : b));
  };
  const deleteChain = (chainId) => {
    if (!confirm(`Delete ${chainId}? Members will be unlinked (set to no chain).`)) return;
    setDraft(d => d.filter(c => c.id !== chainId));
    setDraftBugs(bs => bs.map(b => b.bug_chain_id === chainId ? { ...b, bug_chain_id: null } : b));
    setEditing(null);
  };
  const mergeInto = (sourceId, targetId) => {
    if (sourceId === targetId) return;
    if (!confirm(`Merge ${sourceId} into ${targetId}? Members move; ${sourceId} is deleted.`)) return;
    setDraft(d => {
      const src = d.find(c => c.id === sourceId);
      const tgt = d.find(c => c.id === targetId);
      if (!src || !tgt) return d;
      const mergedMembers = Array.from(new Set([...tgt.member_requirement_codes, ...src.member_requirement_codes]));
      return d.filter(c => c.id !== sourceId).map(c => c.id === targetId
        ? { ...c, member_requirement_codes: mergedMembers, total_occurrences: mergedMembers.length }
        : c);
    });
    setDraftBugs(bs => bs.map(b => b.bug_chain_id === sourceId ? { ...b, bug_chain_id: targetId } : b));
    setEditing(targetId);
    setMergeTarget(null);
  };

  // Member candidates: any bug not already in this chain, filtered by query
  const candidates = !cur ? [] : draftBugs
    .filter(b => !cur.member_requirement_codes.includes(b.code))
    .filter(b => {
      if (!memberQuery) return true;
      const q = memberQuery.toLowerCase();
      return b.code.toLowerCase().includes(q) || b.title.toLowerCase().includes(q) || (b.description||"").toLowerCase().includes(q);
    })
    .slice(0, 30);

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" style={{minWidth: 980, width: 980, height: 640}} onClick={e=>e.stopPropagation()}>
        <div style={{padding: '14px 16px', borderBottom: '1px solid var(--rule)', display:'flex', justifyContent:'space-between', alignItems:'center'}}>
          <div>
            <div style={{fontWeight: 600, fontSize: 14}}>Bug chains</div>
            <div style={{fontSize: 11.5, color:'var(--ink-3)', marginTop: 2}}>
              <span className="mono">bug_chains</span> table per /erd. Members joined via <span className="mono">requirements.bug_chain_id</span>.
            </div>
          </div>
          <button className="btn ghost" onClick={onClose}>✕</button>
        </div>

        <div style={{flex: 1, display:'grid', gridTemplateColumns:'300px 1fr', minHeight: 0}}>
          {/* Left: chain list */}
          <div className="scroll" style={{borderRight: '1px solid var(--rule)', overflowY:'auto', display:'flex', flexDirection:'column'}}>
            <div style={{padding: 10, borderBottom:'1px solid var(--rule)', display:'flex', flexDirection:'column', gap: 6}}>
              <input className="input" placeholder="🔍 search chains by id, label, token, member…"
                value={chainQuery} onChange={e=>setChainQuery(e.target.value)} style={{fontSize: 11.5}} />
              <button className="btn primary sm" style={{width: '100%'}} onClick={() => {
                const n = draft.length + 1;
                let id = "BC-NEW-" + String(n).padStart(3,'0');
                while (draft.some(c => c.id === id)) { id = "BC-NEW-" + Math.floor(Math.random()*9999); }
                setDraft(d => [...d, { id, pattern_label: "New pattern", expected_outcome: "", missing_signal: "", tokens: [], member_requirement_codes: [], total_occurrences: 0, status: "open", failure_class_hash: "h_" + Math.random().toString(36).slice(2,8) }]);
                setEditing(id);
              }}>+ New chain</button>
            </div>
            <div style={{flex: 1, overflowY:'auto'}}>
              {(() => {
                const q = chainQuery.toLowerCase();
                const list = q ? draft.filter(c =>
                  c.id.toLowerCase().includes(q) ||
                  (c.pattern_label||"").toLowerCase().includes(q) ||
                  (c.expected_outcome||"").toLowerCase().includes(q) ||
                  (c.tokens||[]).some(t => t.toLowerCase().includes(q)) ||
                  c.member_requirement_codes.some(m => m.toLowerCase().includes(q))
                ) : draft;
                if (list.length === 0) return <div style={{padding: 20, fontSize: 11, color:'var(--ink-4)', textAlign:'center'}}>no chains match “{chainQuery}”</div>;
                return list.map(c => (
                  <div key={c.id} onClick={()=>{setEditing(c.id); setMemberQuery(""); setMergeTarget(null);}}
                    style={{padding:'9px 12px', borderBottom:'1px solid var(--rule)', cursor:'pointer', background: editing===c.id ?'var(--bg-sunk)':'transparent', borderLeft: editing===c.id?'2px solid var(--ink)':'2px solid transparent'}}>
                    <div style={{display:'flex', justifyContent:'space-between', alignItems:'baseline'}}>
                      <span className="mono" style={{fontSize: 10.5, color:'var(--ink-3)'}}>{c.id}</span>
                      <span style={{fontSize: 10.5, color: c.member_requirement_codes.length<2?'oklch(58% 0.14 30)':'var(--ink-4)', fontWeight: c.member_requirement_codes.length<2?600:400}}>
                        {c.member_requirement_codes.length} {c.member_requirement_codes.length<2 && '⚠'}
                      </span>
                    </div>
                    <div style={{fontSize: 12, marginTop: 2, color:'var(--ink)', textWrap:'pretty', lineHeight: 1.3}}>{c.pattern_label}</div>
                  </div>
                ));
              })()}
            </div>
          </div>

          {/* Right: editor */}
          <div className="scroll" style={{padding: 16, overflowY:'auto'}}>
            {!cur ? (
              <div style={{color:'var(--ink-4)', fontSize: 12, textAlign:'center', marginTop: 60}}>Select a chain to edit, or click <span style={{color:'var(--ink-2)'}}>+ New chain</span>.</div>
            ) : (
              <div>
                {/* Action bar */}
                <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom: 14}}>
                  <div>
                    <div style={lblStyleCrud}>chain id</div>
                    <input className="input mono" value={cur.id} onChange={e=>{
                      const newId = e.target.value;
                      const oldId = cur.id;
                      setDraft(d => d.map(c => c.id === oldId ? {...c, id: newId} : c));
                      setDraftBugs(bs => bs.map(b => b.bug_chain_id === oldId ? {...b, bug_chain_id: newId} : b));
                      setEditing(newId);
                    }} style={{marginTop: 4, width: 240}} />
                  </div>
                  <div style={{display:'flex', gap: 6}}>
                    <button className="btn sm" onClick={()=>setMergeTarget(mergeTarget ? null : "_pick")}>
                      ⇢ merge into…
                    </button>
                    <button className="btn sm danger" onClick={()=>deleteChain(cur.id)}>🗑 delete</button>
                  </div>
                </div>

                {/* Merge target picker */}
                {mergeTarget !== null && (
                  <div style={{padding: 10, marginBottom: 14, background:'oklch(96% 0.04 60)', border:'1px solid oklch(85% 0.10 60)', borderRadius: 4}}>
                    <div style={{fontSize: 11, color:'oklch(35% 0.10 60)', marginBottom: 6}}>Pick a chain to merge <span className="mono">{cur.id}</span> into. All members move; this chain deletes.</div>
                    <div style={{display:'flex', gap: 6, flexWrap:'wrap'}}>
                      {draft.filter(c => c.id !== cur.id).map(c => (
                        <button key={c.id} className="btn sm" onClick={()=>mergeInto(cur.id, c.id)}>
                          <span className="mono" style={{fontSize: 10.5}}>{c.id}</span> · <span style={{fontSize: 11}}>{c.pattern_label.slice(0, 32)}</span>
                        </button>
                      ))}
                      <button className="btn ghost sm" onClick={()=>setMergeTarget(null)}>cancel</button>
                    </div>
                  </div>
                )}

                <div style={lblStyleCrud}>pattern_label</div>
                <input className="input" value={cur.pattern_label} onChange={e=>setDraft(d=>d.map(c=>c.id===cur.id?{...c, pattern_label: e.target.value}:c))} style={{marginTop: 4}} />

                <div style={{...lblStyleCrud, marginTop: 12}}>expected_outcome</div>
                <textarea className="textarea" value={cur.expected_outcome||""} onChange={e=>setDraft(d=>d.map(c=>c.id===cur.id?{...c, expected_outcome: e.target.value}:c))} style={{marginTop: 4}} />

                <div style={{...lblStyleCrud, marginTop: 12}}>missing_signal <window.SchemaFlag note="Brief specifies this column on bug_chains; not in current /erd." /></div>
                <textarea className="textarea" value={cur.missing_signal||""} onChange={e=>setDraft(d=>d.map(c=>c.id===cur.id?{...c, missing_signal: e.target.value}:c))} style={{marginTop: 4}} />

                <div style={{display:'grid', gridTemplateColumns:'1fr 200px', gap: 12, marginTop: 12}}>
                  <div>
                    <div style={lblStyleCrud}>tokens (comma-sep)</div>
                    <input className="input mono" value={(cur.tokens||[]).join(", ")} onChange={e=>setDraft(d=>d.map(c=>c.id===cur.id?{...c, tokens: e.target.value.split(",").map(s=>s.trim()).filter(Boolean)}:c))} style={{marginTop: 4}} />
                  </div>
                  <div>
                    <div style={lblStyleCrud}>status</div>
                    <select className="input" value={cur.status||"open"} onChange={e=>setDraft(d=>d.map(c=>c.id===cur.id?{...c, status: e.target.value}:c))} style={{marginTop: 4}}>
                      <option value="open">open</option>
                      <option value="resolved">resolved</option>
                      <option value="watching">watching</option>
                    </select>
                  </div>
                </div>

                {/* Members */}
                <div style={{...lblStyleCrud, marginTop: 18}}>members ({cur.member_requirement_codes.length})</div>
                <div style={{marginTop: 6, padding: 10, background:'var(--bg-sunk)', borderRadius: 4, minHeight: 50}}>
                  {cur.member_requirement_codes.length === 0 ? (
                    <div style={{fontSize: 11, color:'oklch(58% 0.14 30)', fontStyle:'italic'}}>⚠ A chain needs at least 2 members to be a real pattern. Add bugs below.</div>
                  ) : (
                    <div style={{display:'flex', flexWrap:'wrap', gap: 5}}>
                      {cur.member_requirement_codes.map(code => {
                        const m = draftBugs.find(b => b.code === code);
                        return (
                          <div key={code} style={{display:'flex', alignItems:'center', gap: 4, padding:'3px 4px 3px 8px', background:'var(--bg-elev)', border:'1px solid var(--rule)', borderRadius: 3}}>
                            <span className="mono" style={{fontSize: 10.5, color:'var(--ink-2)', fontWeight: 500}}>{code}</span>
                            {m && <span style={{fontSize: 10.5, color:'var(--ink-3)', maxWidth: 180, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{m.title}</span>}
                            <button className="btn ghost sm" onClick={()=>removeMember(cur.id, code)} style={{padding:'0 4px', fontSize: 11, color:'var(--ink-3)'}}>✕</button>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Add member */}
                <div style={{...lblStyleCrud, marginTop: 14}}>add bug to chain</div>
                <input className="input" placeholder="search by code, title, or description…"
                  value={memberQuery} onChange={e=>setMemberQuery(e.target.value)} style={{marginTop: 4}} />
                {(memberQuery || candidates.length > 0) && (
                  <div style={{marginTop: 6, maxHeight: 200, overflowY:'auto', border:'1px solid var(--rule)', borderRadius: 4}}>
                    {candidates.length === 0 ? (
                      <div style={{padding: 10, fontSize: 11, color:'var(--ink-4)', textAlign:'center'}}>no matches</div>
                    ) : candidates.map(b => (
                      <div key={b.code} onClick={()=>addMember(cur.id, b.code)}
                        style={{padding:'6px 10px', borderBottom:'1px solid var(--rule)', cursor:'pointer', display:'flex', gap: 8, alignItems:'baseline'}}
                        onMouseEnter={e=>e.currentTarget.style.background='var(--bg-sunk)'}
                        onMouseLeave={e=>e.currentTarget.style.background='transparent'}>
                        <span className="mono" style={{fontSize: 10.5, color:'var(--ink-3)', flexShrink: 0}}>{b.code}</span>
                        <span style={{fontSize: 11.5, color:'var(--ink-2)', flex: 1, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{b.title}</span>
                        {b.bug_chain_id && <span className="mono" style={{fontSize: 10, color:'oklch(55% 0.14 60)'}}>in {b.bug_chain_id}</span>}
                        <span className="btn ghost sm" style={{fontSize: 10.5, color:'var(--accent)'}}>+ add</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <div style={{padding:'10px 16px', borderTop:'1px solid var(--rule)', display:'flex', justifyContent:'space-between', alignItems:'center', background: dirty?'oklch(98% 0.02 60)':'transparent'}}>
          <div style={{fontSize: 11.5, color: dirty?'oklch(40% 0.14 60)':'var(--ink-3)', fontWeight: dirty?500:400}}>
            {dirty ? '⚠ unsaved changes — click save to apply' : 'no changes'}
          </div>
          <div style={{display:'flex', gap: 6}}>
            <button className="btn" onClick={onClose}>{dirty?'discard':'close'}</button>
            <button className="btn primary" disabled={!dirty} onClick={() => { setChains(draft); setBugs(draftBugs); onClose(); }}>save changes</button>
          </div>
        </div>
      </div>
    </div>
  );
}

const lblStyleCrud = {fontSize: 10.5, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.06em', fontWeight: 600};

window.CrudModal = CrudModal;
window.ChainsModal = ChainsModal;
