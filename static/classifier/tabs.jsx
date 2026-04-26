// Tab content components for Inspector v2 — schema-aligned.

const { useState: uS } = React;

const lblStyle = {fontSize: 10.5, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.06em', fontWeight: 600};

function DescriptionTab({ bug, query, siblings, onSelect }) {
  if (!bug) return null;
  return (
    <div style={{padding: '14px 16px'}}>
      <div style={{fontSize: 13, lineHeight: 1.6, color:'var(--ink-2)', textWrap:'pretty', whiteSpace:'pre-wrap'}}>
        {window.highlight(bug.description, query)}
      </div>

      {(bug.tokens?.length || bug.signals?.length) ? (
        <div style={{marginTop: 16, display:'grid', gridTemplateColumns:'1fr 1fr', gap: 14}}>
          {bug.tokens?.length ? (
            <div>
              <div style={lblStyle}>Tokens <window.SchemaFlag note="`tokens` not in /erd. Inspector synthesizes from title+description for sibling search." /></div>
              <div style={{display:'flex', flexWrap:'wrap', gap: 4, marginTop: 5}}>
                {bug.tokens.map(t => <span key={t} className="pill mono" style={{fontSize: 10.5}}>{t}</span>)}
              </div>
            </div>
          ) : null}
          {bug.signals?.length ? (
            <div>
              <div style={lblStyle}>Signals <window.SchemaFlag note="`signals` is a synthesized field; in production these come from failure_events.metadata or stack-trace parsing." /></div>
              <div style={{display:'flex', flexWrap:'wrap', gap: 4, marginTop: 5}}>
                {bug.signals.map(s => <span key={s} className="pill mono" style={{fontSize: 10.5, background:'oklch(95% 0.04 30)'}}>{s}</span>)}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      {siblings.length > 0 && (
        <div style={{marginTop: 18}}>
          <div style={lblStyle}>Similar by token overlap</div>
          <div style={{marginTop: 6, display:'flex', flexDirection:'column', gap: 4}}>
            {siblings.map(({b, overlap}) => (
              <div key={b.code} onClick={() => onSelect(b.code)}
                style={{padding:'6px 8px', border:'1px solid var(--rule)', borderRadius: 5, cursor:'pointer', background:'var(--bg-elev)'}}>
                <div style={{display:'flex', justifyContent:'space-between', alignItems:'baseline', gap: 8}}>
                  <span className="mono" style={{fontSize: 10.5, color:'var(--ink-3)'}}>{b.code}</span>
                  <span className="mono" style={{fontSize: 10.5, color:'var(--accent)'}}>{overlap} tokens</span>
                </div>
                <div style={{fontSize: 12, marginTop: 2, color:'var(--ink-2)'}}>{b.title}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function UATTab({ bug }) {
  if (!bug) return null;
  const walks = bug.uat_walks || [];
  if (!walks.length) return <Empty msg="No UAT walks recorded" />;
  return (
    <div style={{padding:'14px 16px'}}>
      {walks.map((w, i) => {
        const failCount = (w.bvs || []).filter(b => b.status === "fail").length;
        const passCount = (w.bvs || []).filter(b => b.status === "pass").length;
        const pendCount = (w.bvs || []).filter(b => b.status === "pending").length;
        return (
          <div key={w.id || i} style={{border:'1px solid var(--rule)', borderRadius: 6, marginBottom: 12, background:'var(--bg-elev)', overflow:'hidden'}}>
            {/* Walk header */}
            <div style={{padding:'8px 10px', borderBottom:'1px solid var(--rule)', background:'var(--bg-sunk)'}}>
              <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', flexWrap:'wrap', gap: 6}}>
                <div style={{display:'flex', gap: 6, alignItems:'center', flexWrap:'wrap'}}>
                  <span className="mono" style={{fontSize: 11, color:'var(--ink-3)'}}>{w.id}</span>
                  <span className={`pill uat-${w.uat_status}`}>{w.uat_status}</span>
                  <span className="mono pill">{w.sprint_id}</span>
                  <span className="mono pill">{w.version}</span>
                </div>
                <div style={{display:'flex', gap: 4, fontSize: 10.5}}>
                  {passCount > 0 && <span className="pill status-pass">✓ {passCount}</span>}
                  {failCount > 0 && <span className="pill status-fail">✕ {failCount}</span>}
                  {pendCount > 0 && <span className="pill status-pending">… {pendCount}</span>}
                </div>
              </div>
              <div style={{fontSize: 10.5, color:'var(--ink-3)', marginTop: 4}}>
                submitted {w.submitted_at ? window.fmtDate(w.submitted_at) : "—"} {w.submitted_by && <>by <span className="mono">{w.submitted_by}</span></>}
              </div>
            </div>

            {/* PL general_notes */}
            {w.general_notes && (
              <div style={{padding: '8px 10px', borderBottom: '1px solid var(--rule)', background:'oklch(98% 0.02 60)'}}>
                <div style={{...lblStyle, fontSize: 9.5, marginBottom: 3}}>PL general notes</div>
                <div style={{fontSize: 12, lineHeight: 1.5, color:'var(--ink-2)', textWrap:'pretty'}}>{w.general_notes}</div>
              </div>
            )}

            {/* CAI review */}
            {w.cai_review_json && (
              <div style={{padding: '8px 10px', borderBottom:'1px solid var(--rule)', background:'oklch(97% 0.02 280)'}}>
                <div style={{display:'flex', alignItems:'center', gap: 6, marginBottom: 4}}>
                  <span style={{...lblStyle, fontSize: 9.5}}>CAI review</span>
                  <span className={`pill ${w.cai_review_json.assessment==='pass'?'status-pass':w.cai_review_json.assessment==='fail'?'status-fail':'status-pending'}`}>{w.cai_review_json.assessment}</span>
                </div>
                {w.cai_review_json.summary && <div style={{fontSize: 12, color:'var(--ink-2)', lineHeight: 1.5, marginBottom: 4}}>{w.cai_review_json.summary}</div>}
                {w.cai_review_json.actionable?.length ? (
                  <ul style={{margin: '4px 0 0', paddingLeft: 18, fontSize: 11.5, color:'var(--ink-2)', lineHeight: 1.5}}>
                    {w.cai_review_json.actionable.map((a, k) => <li key={k}>{a}</li>)}
                  </ul>
                ) : null}
              </div>
            )}

            {/* BV list */}
            <div style={{padding: '4px 0'}}>
              {(w.bvs || []).map((bv, j) => (
                <div key={bv.bv_id || j} style={{padding:'8px 10px', borderBottom: j<w.bvs.length-1 ?'1px dashed var(--rule)':'none'}}>
                  <div style={{display:'flex', gap: 6, alignItems:'center', flexWrap:'wrap', marginBottom: 3}}>
                    <span className={`pill status-${bv.status}`}>{bv.status}</span>
                    <span className={`pill bvtype-${bv.bv_type}`}>{bv.bv_type}</span>
                    <span className="mono" style={{fontSize: 11, color:'var(--ink-2)', fontWeight: 600}}>{bv.bv_id}</span>
                  </div>
                  <div style={{fontSize: 12.5, color:'var(--ink)', textWrap:'pretty', marginBottom: 3}}>{bv.title}</div>
                  <div style={{display:'flex', gap: 4, flexWrap:'wrap', marginBottom: 4}}>
                    {bv.classifications?.map(c => <span key={c} className="pill" style={{background:'oklch(95% 0.04 280)'}}>cls: {c}</span>)}
                  </div>
                  {bv.notes && (
                    <div style={{fontSize: 11.5, color:'var(--ink-2)', lineHeight: 1.5, padding:'5px 8px', background:'oklch(98% 0.02 60)', borderLeft:'2px solid oklch(80% 0.06 60)', borderRadius: 3, marginTop: 3}}>
                      <span style={{color:'var(--ink-3)', fontSize: 10}}>PL · </span>{bv.notes}
                    </div>
                  )}
                  {bv.cc_evidence && (
                    <div style={{fontSize: 11, color:'var(--ink-2)', lineHeight: 1.5, padding:'5px 8px', background:'oklch(97% 0.02 280)', borderLeft:'2px solid oklch(78% 0.08 280)', borderRadius: 3, marginTop: 3, fontFamily:'var(--mono)', whiteSpace:'pre-wrap'}}>
                      <span style={{color:'var(--ink-3)', fontSize: 10, fontFamily:'var(--sans)'}}>CC evidence · </span>{bv.cc_evidence}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SprintsTab({ bug }) {
  if (!bug) return null;
  const sprints = bug.sprints || [];
  const handoffs = bug.handoffs || [];
  if (!sprints.length && !handoffs.length) return <Empty msg="Not assigned to a sprint" />;

  const handoffById = Object.fromEntries(handoffs.map(h => [h.id, h]));

  return (
    <div style={{padding:'14px 16px'}}>
      <div className="tl">
        {sprints.map((s, i) => {
          const ho = s.handoff_id && handoffById[s.handoff_id];
          const cls = s.session_outcome === "pass" ? "pass"
                    : s.session_outcome === "fail" ? "fail"
                    : s.status === "executing" ? "exec" : "";
          return (
            <div key={s.id || i} className={`tl-item ${cls}`}>
              <div style={{display:'flex', gap: 6, alignItems:'center', flexWrap:'wrap', marginBottom: 4}}>
                <span className="mono" style={{fontSize: 12, fontWeight: 600}}>{s.sprint_id}</span>
                <span className="mono pill">{s.pth}</span>
                <span className="pill">{s.status}</span>
                {s.session_outcome && <span className={`pill status-${s.session_outcome}`}>{s.session_outcome}</span>}
                {s.version_before && s.version_after && (
                  <span className="mono" style={{fontSize: 10.5, color:'var(--ink-3)'}}>{s.version_before} → {s.version_after}</span>
                )}
              </div>
              <div style={{fontSize: 10.5, color:'var(--ink-3)', marginBottom: 5}}>
                {s.session_started_at && <>started {window.fmtDate(s.session_started_at)}</>}
                {s.session_ended_at && <> · ended {window.fmtDate(s.session_ended_at)}</>}
              </div>

              {s.content && (
                <div style={{fontSize: 12, color:'var(--ink-2)', lineHeight: 1.5, padding:'6px 8px', background:'var(--bg-sunk)', borderRadius: 4, marginBottom: 5, textWrap:'pretty'}}>
                  {s.content}
                </div>
              )}

              <div style={{display:'flex', flexWrap:'wrap', gap: 4, marginBottom: 5}}>
                {s.also_closes?.length ? (
                  <span className="pill mono" style={{fontSize: 10}}>also_closes: {s.also_closes.join(", ")}</span>
                ) : null}
                {s.approved_by && <span className="pill mono" style={{fontSize: 10}}>approved by {s.approved_by}</span>}
              </div>

              {s.session_stop_reason && (
                <div style={{fontSize: 11.5, color:'oklch(40% 0.15 25)', lineHeight: 1.5, padding:'5px 8px', background:'oklch(96% 0.04 25)', borderLeft:'2px solid oklch(70% 0.13 25)', borderRadius: 3, marginBottom: 5}}>
                  <span style={{fontSize: 10, color:'var(--ink-3)'}}>stop reason · </span>{s.session_stop_reason}
                </div>
              )}

              {ho && (
                <div style={{marginTop: 6, padding:'7px 8px', border:'1px solid var(--rule)', borderRadius: 4, background:'var(--bg-elev)'}}>
                  <div style={{display:'flex', alignItems:'center', gap: 6, marginBottom: 3}}>
                    <span style={{...lblStyle, fontSize: 9.5}}>Handoff</span>
                    <span className="mono pill" style={{fontSize: 10}}>#{ho.id}</span>
                    <span className="pill" style={{fontSize: 10}}>{ho.direction}</span>
                  </div>
                  {ho.description && <div style={{fontSize: 11.5, color:'var(--ink-2)', marginBottom: 5}}>{ho.description}</div>}
                  {ho.evidence_json && <EvidenceBlock ev={ho.evidence_json} />}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function EvidenceBlock({ ev }) {
  return (
    <div style={{fontSize: 11, fontFamily:'var(--mono)', color:'var(--ink-2)', background:'var(--bg-sunk)', borderRadius: 3, padding: 6}}>
      {ev.tests_run?.length ? (
        <div style={{marginBottom: 4}}>
          <span style={{color:'var(--ink-3)'}}>tests_run:</span>
          <ul style={{margin: '2px 0 0', paddingLeft: 18}}>
            {ev.tests_run.map((t, i) => <li key={i} style={{fontSize: 10.5}}>{t}</li>)}
          </ul>
        </div>
      ) : null}
      {ev.tests_passed != null && (
        <div style={{marginBottom: 4}}>
          <span style={{color:'var(--ink-3)'}}>tests_passed/failed:</span> <span style={{color: 'var(--pass)'}}>{ev.tests_passed}</span> / <span style={{color: ev.tests_failed ? 'var(--fail)' : 'var(--ink-3)'}}>{ev.tests_failed ?? 0}</span>
        </div>
      )}
      {ev.dom_scan && (
        <div style={{marginBottom: 4}}>
          <span style={{color:'var(--ink-3)'}}>dom_scan:</span><br />
          <span style={{whiteSpace:'pre-wrap'}}>{ev.dom_scan}</span>
        </div>
      )}
      {ev.gaps_acknowledged?.length ? (
        <div style={{marginBottom: 4}}>
          <span style={{color:'oklch(45% 0.12 60)'}}>gaps_acknowledged:</span>
          <ul style={{margin: '2px 0 0', paddingLeft: 18}}>
            {ev.gaps_acknowledged.map((g, i) => <li key={i} style={{fontSize: 10.5, color:'var(--ink-2)'}}>{g}</li>)}
          </ul>
        </div>
      ) : null}
      {ev.note && (
        <div style={{color:'var(--ink-3)', fontStyle:'italic', fontSize: 10.5, marginTop: 3}}>{ev.note}</div>
      )}
    </div>
  );
}

function ReviewsTab({ bug }) {
  if (!bug) return null;
  const reviews = bug.reviews || [];
  if (!reviews.length) return <Empty msg="No CAI reviews on file" />;
  return (
    <div style={{padding:'14px 16px'}}>
      {reviews.map((r, i) => (
        <div key={r.id || i} style={{border:'1px solid var(--rule)', borderRadius: 6, marginBottom: 12, background:'var(--bg-elev)', overflow:'hidden'}}>
          <div style={{padding:'8px 10px', borderBottom:'1px solid var(--rule)', background:'var(--bg-sunk)'}}>
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', flexWrap:'wrap', gap: 6}}>
              <div style={{display:'flex', gap: 6, alignItems:'center'}}>
                <span style={{fontWeight: 600, fontSize: 12.5}}>{r.created_by || "CAI"}</span>
                <span className={`pill status-${r.assessment === 'pass' ? 'pass' : r.assessment === 'fail' ? 'fail' : r.assessment === 'conditional_pass' ? 'conditional_pass' : 'pending'}`}>{r.assessment}</span>
                <span className="mono pill" style={{fontSize: 10}}>{r.pth}</span>
                {r.handoff_id && <span className="mono pill" style={{fontSize: 10}}>handoff #{r.handoff_id}</span>}
              </div>
              <span className="mono" style={{fontSize: 10.5, color:'var(--ink-3)'}}>{window.fmtDate(r.created_at)}</span>
            </div>
          </div>
          <div style={{padding: '10px'}}>
            {r.notes && <div style={{fontSize: 12, color:'var(--ink-2)', lineHeight: 1.55, textWrap:'pretty', marginBottom: 8}}>{r.notes}</div>}

            {r.lesson_candidates && (
              <div style={{padding:'8px 10px', borderRadius: 4, background:'oklch(97% 0.03 90)', border: '1px dashed oklch(82% 0.08 90)'}}>
                <div style={{display:'flex', alignItems:'center', gap: 6, marginBottom: 4}}>
                  <span style={{...lblStyle, fontSize: 9.5}}>Lesson candidate</span>
                  {r.lesson_candidates.target && <span className="pill mono" style={{fontSize: 10}}>{r.lesson_candidates.target}</span>}
                  {r.lesson_candidates.severity && (
                    <span className={`pill ${r.lesson_candidates.severity==='high'?'p1':r.lesson_candidates.severity==='medium'?'p2':'p3'}`}>
                      {r.lesson_candidates.severity}
                    </span>
                  )}
                </div>
                {r.lesson_candidates.lesson && (
                  <div style={{fontSize: 12, color:'var(--ink-2)', lineHeight: 1.55, textWrap:'pretty', fontStyle:'italic'}}>
                    "{r.lesson_candidates.lesson}"
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function StateTab({ bug }) {
  if (!bug) return null;
  const history = bug.history || [];
  if (!history.length) return <Empty msg="No state transitions recorded" />;
  return (
    <div style={{padding:'14px 16px'}}>
      <div className="tl">
        {history.map((h, i) => {
          const cls = h.new_status === "closed" || h.new_status?.includes("pass") ? "pass"
                    : h.new_status?.includes("fail") || h.new_status?.includes("rejected") ? "fail"
                    : h.new_status?.includes("executing") || h.new_status?.includes("cc_") ? "exec" : "";
          return (
            <div key={h.id || i} className={`tl-item ${cls}`}>
              <div style={{display:'flex', gap: 6, alignItems:'center', flexWrap:'wrap', marginBottom: 3}}>
                <span className="mono" style={{fontSize: 11, color: 'var(--ink-3)'}}>
                  {h.old_status || <span style={{color:'var(--ink-4)'}}>∅</span>}
                </span>
                <span style={{color:'var(--ink-4)'}}>→</span>
                <span className="mono" style={{fontSize: 11.5, fontWeight: 600, color:'var(--ink)'}}>{h.new_status}</span>
                {h.changed_by && <span className="pill mono" style={{fontSize: 10}}>{h.changed_by}</span>}
                <span className="mono" style={{fontSize: 10.5, color:'var(--ink-3)', marginLeft:'auto'}}>{window.fmtDate(h.changed_at)}</span>
              </div>
              {h.note && <div style={{fontSize: 11.5, color:'var(--ink-2)', lineHeight: 1.5, textWrap:'pretty'}}>{h.note}</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ChainTab({ bug, chains, setChains, bugs, updateBug }) {
  if (!bug) return null;
  const ch = bug.bug_chain_id && chains.find(c => c.id === bug.bug_chain_id);
  const [draft, setDraft] = uS(ch ? {...ch} : null);
  React.useEffect(() => { setDraft(ch ? {...ch} : null); }, [ch?.id]);

  if (!ch) {
    return (
      <div style={{padding:'14px 16px'}}>
        <div style={{...lblStyle, marginBottom: 8}}>Not in a chain</div>
        <div style={{fontSize: 12, color:'var(--ink-3)', marginBottom: 12, lineHeight: 1.5}}>
          Use <span className="kbd">h</span> to attach to an existing chain, or create a new chain seeded from this bug.
        </div>
        <button className="btn primary" onClick={() => {
          const id = "BC-" + String(chains.length+1).padStart(3,'0');
          const c = {
            id, pattern_label: bug.title.slice(0, 50),
            expected_outcome: "", missing_signal: "",
            tokens: [...(bug.tokens||[])].slice(0,5),
            member_requirement_codes: [bug.code],
            total_occurrences: 1, status: "open", first_seen: bug.created_at, last_seen: bug.updated_at,
          };
          setChains(cs => [...cs, c]);
          updateBug(bug.code, { bug_chain_id: id });
        }}>+ Seed new chain from this bug</button>
      </div>
    );
  }

  if (!draft) return null;
  const dirty = JSON.stringify(draft) !== JSON.stringify(ch);
  const members = bugs.filter(b => ch.member_requirement_codes.includes(b.code));

  return (
    <div style={{padding:'14px 16px'}}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'baseline', marginBottom: 8}}>
        <div>
          <span className="mono" style={{fontSize: 11, color:'var(--ink-3)'}}>{ch.id}</span>
          <span className="mono" style={{fontSize: 10.5, color:'var(--ink-4)', marginLeft: 8}}>×{ch.total_occurrences} · {ch.status}</span>
        </div>
        {dirty && (
          <div style={{display:'flex', gap: 6}}>
            <button className="btn sm" onClick={() => setDraft({...ch})}>discard</button>
            <button className="btn sm primary" onClick={() => setChains(cs => cs.map(c => c.id===ch.id ? draft : c))}>save</button>
          </div>
        )}
      </div>

      <div style={{...lblStyle, marginTop: 6}}>Pattern label</div>
      <input className="input" value={draft.pattern_label} onChange={e=>setDraft({...draft, pattern_label: e.target.value})} style={{marginTop: 4}} />

      <div style={{...lblStyle, marginTop: 12}}>
        Expected outcome <span style={{color:'var(--ink-4)', textTransform:'none', letterSpacing:0}}>— what should happen</span>
      </div>
      <textarea className="textarea" value={draft.expected_outcome} onChange={e=>setDraft({...draft, expected_outcome: e.target.value})} style={{marginTop: 4}} />

      <div style={{...lblStyle, marginTop: 12}}>
        Missing signal <window.SchemaFlag note="`missing_signal` not in current /erd; brief specifies it as part of bug_chains. Confirm column add." />
      </div>
      <textarea className="textarea" value={draft.missing_signal} onChange={e=>setDraft({...draft, missing_signal: e.target.value})} style={{marginTop: 4}} />

      <div style={{...lblStyle, marginTop: 12}}>Match tokens</div>
      <input className="input mono" value={(draft.tokens||[]).join(", ")}
        onChange={e=>setDraft({...draft, tokens: e.target.value.split(",").map(s=>s.trim()).filter(Boolean)})}
        style={{marginTop: 4}} />

      <div style={{...lblStyle, marginTop: 14}}>Members ({members.length})</div>
      <div style={{marginTop: 4, display:'flex', flexDirection:'column', gap: 3}}>
        {members.map(m => (
          <div key={m.code} style={{padding:'5px 8px', border:'1px solid var(--rule)', borderRadius: 4, fontSize: 11.5, display:'flex', justifyContent:'space-between', gap: 6, background: m.code===bug.code ?'var(--bg-sunk)':'var(--bg-elev)'}}>
            <div style={{display:'flex', gap:6, alignItems:'baseline', minWidth: 0}}>
              <span className="mono" style={{color:'var(--ink-3)', flexShrink: 0}}>{m.code}</span>
              <span style={{overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap', color:'var(--ink-2)'}}>{m.title}</span>
            </div>
            <span className={`pill ${m.priority.toLowerCase()}`}>{m.priority}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function OutlineSummary({ bug, chains }) {
  if (!bug) return null;
  const ch = bug.bug_chain_id && chains.find(c => c.id === bug.bug_chain_id);
  return (
    <div>
      <div style={lblStyle}>Identifiers</div>
      <Row k="code" v={bug.code} />
      <Row k="pth" v={bug.pth || "—"} />
      <Row k="sprint_id" v={bug.sprint_id || "—"} />

      <div style={{...lblStyle, marginTop: 10}}>Classifications</div>
      <Row k="classifications" v={bug.classifications?.length ? bug.classifications.join(", ") : <span style={{color:'var(--ink-4)'}}>—</span>} flag />
      <Row k="bug_chain_id" v={bug.bug_chain_id || <span style={{color:'var(--ink-4)'}}>—</span>} />
      {ch && (
        <div style={{marginTop: 6, padding: 7, background:'var(--bg-sunk)', borderRadius: 4, fontSize: 11, lineHeight: 1.45}}>
          <div className="mono" style={{color:'var(--accent)', fontWeight: 600}}>● {ch.pattern_label}</div>
          <div style={{color:'var(--ink-3)', marginTop: 3}}>{ch.expected_outcome?.slice(0, 80)}{ch.expected_outcome?.length>80?"…":""}</div>
        </div>
      )}

      <div style={{...lblStyle, marginTop: 10}}>Activity</div>
      <Row k="created_at" v={bug.created_at?.slice(0,10)} />
      <Row k="updated_at" v={bug.updated_at?.slice(0,10)} />
      <Row k="age" v={`${bug.age}d`} />
    </div>
  );
}

function Row({ k, v, flag }) {
  return (
    <div style={{display:'flex', justifyContent:'space-between', gap: 6, fontSize: 11, padding:'2px 0'}}>
      <span className="mono" style={{color:'var(--ink-3)'}}>{k}{flag && <span style={{marginLeft: 4}}><window.SchemaFlag note="Schema-flagged field — see Outline footer." /></span>}</span>
      <span className="mono" style={{color:'var(--ink-2)', textAlign:'right', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap', maxWidth: 160}}>{v}</span>
    </div>
  );
}

function Empty({ msg }) {
  return <div style={{padding: 30, textAlign:'center', color:'var(--ink-4)', fontSize: 12}}>{msg}</div>;
}

window.DescriptionTab = DescriptionTab;
window.UATTab = UATTab;
window.SprintsTab = SprintsTab;
window.ReviewsTab = ReviewsTab;
window.StateTab = StateTab;
window.ChainTab = ChainTab;
window.OutlineSummary = OutlineSummary;
