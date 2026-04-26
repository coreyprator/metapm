// Direction C — Cluster Map
// Bugs as cards in a 2D space, positioned by inferred similarity (token Jaccard).
// Lasso/click-to-add to a working set, then commit the set as a chain.

const { useState: useStateC, useMemo: useMemoC, useRef: useRefC, useEffect: useEffectC } = React;

// Stable 2D layout via deterministic projection of token sets to (x,y).
// We compute pairwise Jaccard similarity, then run a simple force-directed step
// from a seeded grid layout for repeatable, readable clusters.
function computeLayout(bugs) {
  const N = bugs.length;
  const tokens = bugs.map(b => new Set([...b.tokens, ...b.signals, b.layer, b.prefix]));

  // Seed positions on a circle by hash of code (deterministic).
  const hash = s => { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) | 0; return h; };
  const positions = bugs.map((b, i) => {
    const a = (hash(b.code) % 360) * Math.PI / 180;
    const r = 250 + (i % 5) * 8;
    return { x: 500 + Math.cos(a) * r, y: 320 + Math.sin(a) * r };
  });

  const sim = (i, j) => {
    const a = tokens[i], b = tokens[j];
    let inter = 0;
    a.forEach(t => { if (b.has(t)) inter++; });
    const union = a.size + b.size - inter;
    return union ? inter / union : 0;
  };

  // 80 iterations of relaxation
  for (let it = 0; it < 80; it++) {
    const fx = new Array(N).fill(0), fy = new Array(N).fill(0);
    for (let i = 0; i < N; i++) {
      for (let j = i + 1; j < N; j++) {
        const s = sim(i, j);
        const dx = positions[j].x - positions[i].x, dy = positions[j].y - positions[i].y;
        const d = Math.sqrt(dx*dx + dy*dy) + 0.01;
        // Attraction proportional to similarity, repulsion otherwise
        const attract = s * 0.04;
        const repel = (1 - s) * 250 / (d * d);
        const fxi = (dx / d) * (attract * d - repel);
        const fyi = (dy / d) * (attract * d - repel);
        fx[i] += fxi; fy[i] += fyi; fx[j] -= fxi; fy[j] -= fyi;
      }
    }
    for (let i = 0; i < N; i++) {
      positions[i].x += fx[i] * 0.5;
      positions[i].y += fy[i] * 0.5;
      // Loose box constraint
      positions[i].x = Math.max(60, Math.min(940, positions[i].x));
      positions[i].y = Math.max(60, Math.min(580, positions[i].y));
    }
  }
  return positions;
}

function ClusterDirection() {
  const bugs = window.BUG_DATA;
  const chains = window.CHAIN_DATA;
  const membership = window.MEMBERSHIP;

  const positions = useMemoC(() => computeLayout(bugs), []);

  const [query, setQuery] = useStateC("");
  const [layerHi, setLayerHi] = useStateC(null);
  const [selected, setSelected] = useStateC(new Set());
  const [hover, setHover] = useStateC(null);
  const [chainName, setChainName] = useStateC("BC-NEW-CHAIN");

  const layerColor = {
    frontend: 'oklch(60% 0.13 220)',
    backend:  'oklch(55% 0.13 145)',
    db:       'oklch(55% 0.14 280)',
    infra:    'oklch(60% 0.13 30)',
    algorithm:'oklch(58% 0.14 320)',
  };

  const matches = bugs.map((b, i) => ({
    b, i, pos: positions[i],
    isMatch: query ? window.matchesQuery(b, query) : true,
    isHi: layerHi ? b.layer === layerHi : true
  }));

  const toggle = code => setSelected(s => {
    const n = new Set(s); n.has(code) ? n.delete(code) : n.add(code); return n;
  });

  // Compute proposed Expected Outcome / Missing Signal from the selected set
  const proposed = useMemoC(() => {
    if (selected.size === 0) return null;
    const sel = bugs.filter(b => selected.has(b.code));
    const tokenCounts = {}, signalCounts = {};
    sel.forEach(b => {
      b.tokens.forEach(t => tokenCounts[t] = (tokenCounts[t]||0)+1);
      b.signals.forEach(s => signalCounts[s] = (signalCounts[s]||0)+1);
    });
    const topTokens = Object.entries(tokenCounts).sort((a,b)=>b[1]-a[1]).slice(0,4);
    const topSignals = Object.entries(signalCounts).sort((a,b)=>b[1]-a[1]).slice(0,3);
    return { sel, topTokens, topSignals };
  }, [selected, bugs]);

  return (
    <div style={clStyles.root}>
      <div style={clStyles.topbar}>
        <div style={{display:'flex', alignItems:'center', gap: 10}}>
          <div style={clStyles.brandDot}></div>
          <div>
            <div style={{fontWeight: 600, fontSize: 13}}>MetaPM · Bug Classifier</div>
            <div style={{fontSize: 10.5, color:'var(--ink-3)'}}>Cluster map · similarity by shared tokens</div>
          </div>
        </div>
        <div style={{display:'flex', gap: 8, alignItems:'center'}}>
          <input className="input" placeholder="search…" style={{maxWidth: 220}}
            value={query} onChange={e => setQuery(e.target.value)} />
          <div style={{display:'flex', gap:3}}>
            {Object.keys(layerColor).map(l => (
              <button key={l} className="btn"
                style={layerHi===l ? {background:'var(--ink)', color:'var(--bg-elev)', borderColor:'var(--ink)'}
                                   : {borderLeft: `3px solid ${layerColor[l]}`}}
                onClick={() => setLayerHi(layerHi===l ? null : l)}>{l}</button>
            ))}
          </div>
        </div>
      </div>

      <div style={clStyles.body}>
        <div style={clStyles.canvas}>
          <svg viewBox="0 0 1000 640" style={{width:'100%', height:'100%', display:'block'}}>
            {/* subtle grid */}
            <defs>
              <pattern id="cgrid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="oklch(94% 0.005 80)" strokeWidth="1"/>
              </pattern>
            </defs>
            <rect width="1000" height="640" fill="url(#cgrid)" />

            {/* Lines from each selected bug to centroid */}
            {selected.size > 1 && (() => {
              const sel = matches.filter(m => selected.has(m.b.code));
              const cx = sel.reduce((a,m)=>a+m.pos.x,0)/sel.length;
              const cy = sel.reduce((a,m)=>a+m.pos.y,0)/sel.length;
              return (<g>
                {sel.map(m => (
                  <line key={m.b.code} x1={cx} y1={cy} x2={m.pos.x} y2={m.pos.y}
                    stroke="oklch(55% 0.13 30)" strokeWidth="1" strokeDasharray="2 3" opacity="0.6"/>
                ))}
                <circle cx={cx} cy={cy} r={6} fill="oklch(55% 0.13 30)" opacity="0.8"/>
                <circle cx={cx} cy={cy} r={14} fill="none" stroke="oklch(55% 0.13 30)" strokeWidth="1" opacity="0.4"/>
              </g>);
            })()}

            {/* Dots */}
            {matches.map(m => {
              const isSel = selected.has(m.b.code);
              const isMember = !!membership[m.b.code];
              const dim = !m.isMatch || !m.isHi;
              return (
                <g key={m.b.code} transform={`translate(${m.pos.x}, ${m.pos.y})`}
                   style={{cursor:'pointer'}}
                   onClick={() => toggle(m.b.code)}
                   onMouseEnter={() => setHover(m.b.code)}
                   onMouseLeave={() => setHover(null)}>
                  <circle r={isSel ? 10 : (isMember ? 7 : 6)}
                    fill={isMember ? 'oklch(96% 0.005 80)' : layerColor[m.b.layer]}
                    stroke={isSel ? 'oklch(35% 0.13 30)' : layerColor[m.b.layer]}
                    strokeWidth={isSel ? 3 : (isMember ? 2 : 0)}
                    opacity={dim ? 0.15 : 1} />
                  {hover === m.b.code && (
                    <g pointerEvents="none">
                      <rect x="12" y="-30" width="280" height="56" rx="4"
                        fill="oklch(20% 0.01 60)" opacity="0.96" />
                      <text x="20" y="-14" fill="oklch(85% 0.005 80)" fontSize="10" fontFamily="var(--mono)">{m.b.code} · {m.b.priority} · {m.b.layer}</text>
                      <text x="20" y="2" fill="oklch(96% 0.005 80)" fontSize="11.5" fontFamily="var(--sans)">
                        {m.b.title.length > 48 ? m.b.title.slice(0,48)+'…' : m.b.title}
                      </text>
                      <text x="20" y="18" fill="oklch(70% 0.005 80)" fontSize="10" fontFamily="var(--mono)">
                        tokens: {m.b.tokens.slice(0,4).join(', ')}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}
          </svg>

          <div style={clStyles.legend}>
            <div style={{fontSize:10.5, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom: 6, fontWeight:600}}>Legend</div>
            {Object.entries(layerColor).map(([l, c]) => (
              <div key={l} style={{display:'flex', alignItems:'center', gap: 6, fontSize: 11, marginBottom: 3}}>
                <span style={{width: 10, height: 10, borderRadius:'50%', background: c, display:'inline-block'}}></span>
                <span>{l}</span>
              </div>
            ))}
            <div className="divider" style={{margin:'8px 0'}}></div>
            <div style={{display:'flex', alignItems:'center', gap: 6, fontSize: 11, marginBottom: 3}}>
              <span style={{width: 10, height: 10, borderRadius:'50%', background:'oklch(96% 0.005 80)', border:'2px solid var(--ink-2)', display:'inline-block'}}></span>
              <span>in a chain</span>
            </div>
            <div style={{display:'flex', alignItems:'center', gap: 6, fontSize: 11}}>
              <span style={{width: 10, height: 10, borderRadius:'50%', background:'var(--ink-3)', border:'3px solid var(--accent)', display:'inline-block'}}></span>
              <span>selected</span>
            </div>
          </div>
        </div>

        <div style={clStyles.sidebar}>
          <div style={clStyles.sidebarHeader}>
            <div style={clStyles.paneTitle}>Working set</div>
            <span className="mono" style={{fontSize: 11, color:'var(--ink-3)'}}>{selected.size}</span>
          </div>

          {selected.size === 0 ? (
            <div style={{padding: '14px 14px', color:'var(--ink-3)', fontSize: 12.5, lineHeight: 1.5}}>
              Click bugs to build a working set.
              <br/><br/>
              Bugs nearer each other share more tokens. Look for tight clusters far from chained (white-filled) bugs — those are unclassified patterns.
            </div>
          ) : (
            <div style={{display:'flex', flexDirection:'column', flex:1, minHeight: 0}}>
              <div className="scroll" style={{flex:1, overflowY:'auto'}}>
                {Array.from(selected).map(code => {
                  const b = bugs.find(x => x.code === code);
                  return (
                    <div key={code} style={clStyles.workRow}>
                      <span className="mono" style={{fontSize: 10.5, color:'var(--ink-3)', minWidth: 70}}>{code}</span>
                      <span style={{flex:1, fontSize: 11.5, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis'}}>{b?.title}</span>
                      <button className="btn ghost" style={{padding:'2px 6px', fontSize: 11}}
                        onClick={() => toggle(code)}>×</button>
                    </div>
                  );
                })}
              </div>
              {proposed && (
                <div style={{padding: '10px 14px', borderTop: '1px solid var(--rule)', background:'var(--bg-sunk)'}}>
                  <div style={{fontSize: 10.5, textTransform:'uppercase', letterSpacing:'0.06em', color:'var(--ink-3)', marginBottom: 6, fontWeight: 600}}>
                    Suggested chain
                  </div>
                  <input className="input" value={chainName} onChange={e => setChainName(e.target.value)} style={{marginBottom: 8, fontSize:11.5}}/>
                  <div style={{fontSize: 11, color:'var(--ink-2)', marginBottom: 6}}>
                    <span style={{color:'var(--ink-3)'}}>Top tokens:</span>{' '}
                    {proposed.topTokens.map(([t, n]) => (
                      <code key={t} style={{fontFamily:'var(--mono)', fontSize: 10.5, padding:'1px 5px', background:'var(--bg-elev)', borderRadius: 3, marginRight: 3, border:'1px solid var(--rule)'}}>
                        {t}<span style={{color:'var(--ink-3)'}}>·{n}</span>
                      </code>
                    ))}
                  </div>
                  <div style={{fontSize: 11, color:'var(--ink-2)', marginBottom: 8}}>
                    <span style={{color:'var(--ink-3)'}}>Top signals:</span>{' '}
                    {proposed.topSignals.map(([t, n]) => (
                      <code key={t} style={{fontFamily:'var(--mono)', fontSize: 10.5, padding:'1px 5px', background:'oklch(95% 0.04 220)', borderRadius: 3, marginRight: 3}}>
                        {t}<span style={{color:'var(--ink-3)'}}>·{n}</span>
                      </code>
                    ))}
                  </div>
                  <div style={{fontSize: 10.5, color:'var(--ink-3)', marginBottom: 4}}>Inferred match rule</div>
                  <code style={{display:'block', fontFamily:'var(--mono)', fontSize: 11, padding:'5px 6px', background:'var(--bg-elev)', borderRadius: 3, border:'1px solid var(--rule)', marginBottom: 8, lineHeight: 1.5}}>
                    {proposed.topTokens.slice(0,2).map(([t]) => `tokens has '${t}'`).join(' AND ')}
                  </code>
                  <div style={{display:'flex', gap: 6}}>
                    <button className="btn primary" style={{flex:1}}>Commit chain</button>
                    <button className="btn" onClick={() => setSelected(new Set())}>Clear</button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const clStyles = {
  root: { width:'100%', height:'100%', display:'flex', flexDirection:'column', background:'var(--bg)', fontFamily:'var(--sans)', overflow:'hidden' },
  topbar: { display:'flex', justifyContent:'space-between', alignItems:'center', padding:'8px 14px',
    borderBottom:'1px solid var(--rule)', background:'var(--bg-elev)' },
  brandDot: { width: 22, height: 22, borderRadius: 5, background:'linear-gradient(135deg, oklch(58% 0.14 320), oklch(55% 0.13 145))' },
  body: { flex: 1, display: 'grid', gridTemplateColumns: '1fr 340px', minHeight: 0 },
  canvas: { position:'relative', background:'var(--bg-elev)' },
  legend: { position:'absolute', top: 12, right: 12, padding: 10, background:'oklch(99% 0.005 80)', border:'1px solid var(--rule)', borderRadius: 6, minWidth: 130 },
  sidebar: { borderLeft:'1px solid var(--rule)', background:'var(--bg-elev)', display:'flex', flexDirection:'column', minHeight: 0 },
  sidebarHeader: { display:'flex', justifyContent:'space-between', alignItems:'center', padding:'8px 14px', borderBottom:'1px solid var(--rule)' },
  paneTitle: { fontSize: 12, fontWeight: 600, textTransform:'uppercase', letterSpacing:'0.06em', color:'var(--ink-2)' },
  workRow: { display:'flex', alignItems:'center', gap: 8, padding:'6px 14px', borderBottom:'1px solid var(--rule)' },
};

window.ClusterDirection = ClusterDirection;
