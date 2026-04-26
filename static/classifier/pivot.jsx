// Direction B — Pivot Board
// Group bugs by a chosen dimension; aggregate counts; drill down into the bugs in any cell.

const { useState: useStateB, useMemo: useMemoB } = React;

function PivotDirection() {
  const bugs = window.BUG_DATA;
  const chains = window.CHAIN_DATA;
  const membership = window.MEMBERSHIP;

  const [rowDim, setRowDim] = useStateB("layer");
  const [colDim, setColDim] = useStateB("priority");
  const [query, setQuery] = useStateB("");
  const [drill, setDrill] = useStateB(null); // {row, col}

  const dims = {
    layer: { label: "Layer", get: b => b.layer },
    priority: { label: "Priority", get: b => b.priority },
    prefix: { label: "Code prefix", get: b => b.prefix },
    chain: { label: "Chain", get: b => membership[b.code] ? chains.find(c=>c.id===membership[b.code])?.label : "— unassigned —" },
    signal: { label: "Top signal", get: b => b.signals[0] || "—" },
  };

  const filtered = useMemoB(() => bugs.filter(b => window.matchesQuery(b, query)), [query, bugs]);

  const { rowVals, colVals, grid, rowTotals, colTotals } = useMemoB(() => {
    const rowSet = new Set(), colSet = new Set();
    filtered.forEach(b => { rowSet.add(dims[rowDim].get(b)); colSet.add(dims[colDim].get(b)); });
    const rowVals = Array.from(rowSet).sort();
    const colVals = Array.from(colSet).sort();
    const grid = {};
    const rowTotals = {}; const colTotals = {};
    rowVals.forEach(r => { grid[r] = {}; rowTotals[r] = 0; colVals.forEach(c => grid[r][c] = []); });
    colVals.forEach(c => colTotals[c] = 0);
    filtered.forEach(b => {
      const r = dims[rowDim].get(b), c = dims[colDim].get(b);
      grid[r][c].push(b); rowTotals[r]++; colTotals[c]++;
    });
    return { rowVals, colVals, grid, rowTotals, colTotals };
  }, [filtered, rowDim, colDim]);

  const max = useMemoB(() => Math.max(1, ...rowVals.flatMap(r => colVals.map(c => grid[r][c].length))), [grid, rowVals, colVals]);

  const drillBugs = drill ? grid[drill.row]?.[drill.col] || [] : null;

  return (
    <div style={pvStyles.root}>
      <div style={pvStyles.topbar}>
        <div style={{display:'flex', alignItems:'center', gap: 10}}>
          <div style={pvStyles.brandDot}></div>
          <div>
            <div style={{fontWeight: 600, fontSize: 13}}>MetaPM · Bug Classifier</div>
            <div style={{fontSize: 10.5, color: 'var(--ink-3)'}}>Pivot board · root-cause aggregation</div>
          </div>
        </div>
        <input className="input" placeholder="filter pivot scope…" style={{maxWidth: 280}}
          value={query} onChange={e => setQuery(e.target.value)} />
      </div>

      <div style={pvStyles.controls}>
        <div style={pvStyles.controlGroup}>
          <span style={pvStyles.controlLabel}>Rows</span>
          {Object.keys(dims).map(k => (
            <button key={k} className="btn"
              style={k===rowDim ? {background:'var(--ink)', color:'var(--bg-elev)', borderColor:'var(--ink)'} : {}}
              onClick={() => setRowDim(k)}>{dims[k].label}</button>
          ))}
        </div>
        <div style={pvStyles.controlGroup}>
          <span style={pvStyles.controlLabel}>Columns</span>
          {Object.keys(dims).map(k => (
            <button key={k} className="btn"
              style={k===colDim ? {background:'var(--ink)', color:'var(--bg-elev)', borderColor:'var(--ink)'} : {}}
              onClick={() => setColDim(k)} disabled={k===rowDim}>{dims[k].label}</button>
          ))}
        </div>
      </div>

      <div style={pvStyles.body}>
        <div className="scroll" style={pvStyles.gridWrap}>
          <table style={pvStyles.table}>
            <thead>
              <tr>
                <th style={{...pvStyles.th, position:'sticky', left: 0, background:'var(--bg-elev)'}}>
                  <span style={{fontSize: 10.5, color:'var(--ink-3)'}}>{dims[rowDim].label} ↓ / {dims[colDim].label} →</span>
                </th>
                {colVals.map(c => (
                  <th key={c} style={pvStyles.th}>
                    <div style={{fontSize: 11, fontWeight: 600}}>{c}</div>
                    <div className="mono" style={{fontSize: 10, color: 'var(--ink-3)'}}>{colTotals[c]}</div>
                  </th>
                ))}
                <th style={pvStyles.th}>
                  <div style={{fontSize: 10.5, color: 'var(--ink-3)'}}>total</div>
                </th>
              </tr>
            </thead>
            <tbody>
              {rowVals.map(r => (
                <tr key={r}>
                  <td style={{...pvStyles.rowHead, position:'sticky', left:0, background:'var(--bg-elev)'}}>
                    <div style={{fontSize: 12, fontWeight: 600}}>{r}</div>
                    <div className="mono" style={{fontSize: 10, color: 'var(--ink-3)'}}>{rowTotals[r]}</div>
                  </td>
                  {colVals.map(c => {
                    const n = grid[r][c].length;
                    const heat = n / max;
                    return (
                      <td key={c}
                        style={{...pvStyles.cell,
                          background: n > 0 ? `oklch(${96 - heat*22}% ${0.02 + heat*0.10} 30)` : 'var(--bg-elev)',
                          color: heat > 0.6 ? 'var(--bg-elev)' : 'var(--ink)',
                          cursor: n > 0 ? 'pointer' : 'default',
                          opacity: n === 0 ? 0.3 : 1
                        }}
                        onClick={() => n > 0 && setDrill({row: r, col: c})}>
                        <span className="mono" style={{fontSize: 14, fontWeight: 500}}>{n || '·'}</span>
                      </td>
                    );
                  })}
                  <td style={pvStyles.totalCell}>
                    <span className="mono" style={{fontSize: 13, fontWeight: 600}}>{rowTotals[r]}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={pvStyles.drillPane}>
          {drill ? (
            <>
              <div style={pvStyles.drillHeader}>
                <div>
                  <div style={{fontSize: 10.5, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'0.06em'}}>Drill-down</div>
                  <div style={{fontSize: 14, marginTop: 2}}>
                    <span style={{fontWeight: 600}}>{drill.row}</span>
                    <span style={{margin:'0 6px', color:'var(--ink-3)'}}>×</span>
                    <span style={{fontWeight: 600}}>{drill.col}</span>
                  </div>
                  <div className="mono" style={{fontSize: 10.5, color:'var(--ink-3)', marginTop: 2}}>{drillBugs.length} bugs</div>
                </div>
                <button className="btn ghost" onClick={() => setDrill(null)}>×</button>
              </div>
              <div className="scroll" style={{flex: 1, overflowY: 'auto'}}>
                {drillBugs.map(b => (
                  <div key={b.code} style={pvStyles.drillRow}>
                    <div style={{display:'flex', justifyContent:'space-between', alignItems:'baseline'}}>
                      <span className="mono" style={{fontSize: 10.5, color:'var(--ink-3)'}}>{b.code}</span>
                      <div style={{display:'flex', gap:3}}>
                        <span className={`pill ${b.priority.toLowerCase()}`}>{b.priority}</span>
                        <span className={`pill layer-${b.layer}`}>{b.layer}</span>
                      </div>
                    </div>
                    <div style={{fontSize: 12.5, lineHeight: 1.4, marginTop: 4, textWrap: 'pretty'}}>{b.title}</div>
                    <div style={{fontSize: 11.5, lineHeight: 1.5, marginTop: 6, color: 'var(--ink-2)', textWrap: 'pretty'}}>
                      {b.description}
                    </div>
                    <div style={{display:'flex', gap: 4, marginTop: 6, flexWrap:'wrap'}}>
                      {b.tokens.slice(0,5).map(t => (
                        <code key={t} style={{fontFamily:'var(--mono)', fontSize: 10, padding:'1px 5px',
                          background:'var(--bg-sunk)', borderRadius: 3, color:'var(--ink-2)'}}>{t}</code>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div style={{padding: 24, color: 'var(--ink-3)', fontSize: 12.5, lineHeight: 1.6}}>
              <div style={{fontSize: 11, textTransform:'uppercase', letterSpacing:'0.06em', marginBottom: 8, fontWeight: 600}}>Drill-down</div>
              Click any cell in the pivot to inspect the bugs aggregated there.
              <div style={{marginTop: 14}}>
                <div style={{fontSize: 11, textTransform:'uppercase', letterSpacing:'0.06em', marginBottom: 6, fontWeight: 600, color:'var(--ink-3)'}}>Try</div>
                <ul style={{paddingLeft: 16, margin: 0}}>
                  <li style={{marginBottom: 4}}>Layer × Priority — where do P1s concentrate?</li>
                  <li style={{marginBottom: 4}}>Top signal × Chain — which signals lack a chain?</li>
                  <li style={{marginBottom: 4}}>Code prefix × Layer — which sub-product owns frontend pain?</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const pvStyles = {
  root: { width: '100%', height: '100%', display:'flex', flexDirection:'column', background:'var(--bg)', fontFamily:'var(--sans)', overflow:'hidden' },
  topbar: { display:'flex', justifyContent:'space-between', alignItems:'center', padding:'8px 14px',
    borderBottom:'1px solid var(--rule)', background:'var(--bg-elev)' },
  brandDot: { width: 22, height: 22, borderRadius: 5, background:'linear-gradient(135deg, oklch(60% 0.10 220), oklch(50% 0.13 280))' },
  controls: { display:'flex', gap: 16, padding: '8px 14px', borderBottom: '1px solid var(--rule)', background:'var(--bg-elev)', alignItems:'center' },
  controlGroup: { display:'flex', alignItems:'center', gap: 4 },
  controlLabel: { fontSize: 10.5, textTransform:'uppercase', letterSpacing:'0.06em', color:'var(--ink-3)', fontWeight:600, marginRight: 4 },
  body: { flex: 1, display: 'grid', gridTemplateColumns: '1fr 380px', minHeight: 0 },
  gridWrap: { overflow:'auto', padding: 14 },
  table: { borderCollapse: 'separate', borderSpacing: 2, fontFamily:'var(--sans)' },
  th: { padding: '8px 12px', minWidth: 80, background:'var(--bg-elev)', textAlign: 'center', fontWeight: 500, border:'1px solid var(--rule)', borderRadius: 4 },
  rowHead: { padding: '8px 12px', minWidth: 130, background:'var(--bg-elev)', textAlign:'left', border:'1px solid var(--rule)', borderRadius: 4 },
  cell: { padding: '14px 12px', minWidth: 80, textAlign: 'center', borderRadius: 4, border: '1px solid var(--rule)' },
  totalCell: { padding: '14px 12px', textAlign:'center', background:'var(--bg-sunk)', border:'1px solid var(--rule)', borderRadius: 4 },
  drillPane: { borderLeft:'1px solid var(--rule)', background:'var(--bg-elev)', display:'flex', flexDirection:'column', minHeight: 0 },
  drillHeader: { display:'flex', justifyContent:'space-between', alignItems:'flex-start', padding: '12px 14px', borderBottom: '1px solid var(--rule)' },
  drillRow: { padding: '10px 14px', borderBottom:'1px solid var(--rule)' },
};

window.PivotDirection = PivotDirection;
