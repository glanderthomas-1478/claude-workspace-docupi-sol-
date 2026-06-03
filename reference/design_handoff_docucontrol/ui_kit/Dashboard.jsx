// Dashboard.jsx — batch-protocol table (the Dashboard hero): stat cards + filter bar + sortable table

const PROTOCOLS = [
  { charge: 'CH021667', date: '13.04.2026', time: '14:52 Uhr', prog: 'Instrumente 134 °C', dur: '00:48:12', ok: true },
  { charge: 'CH021666', date: '13.04.2026', time: '14:03 Uhr', prog: 'Instrumente 134 °C', dur: '00:47:39', ok: true },
  { charge: 'CH021665', date: '13.04.2026', time: '10:33 Uhr', prog: 'Bowie-Dick-Test', dur: '00:24:05', ok: true },
  { charge: 'CH021664', date: '13.04.2026', time: '07:15 Uhr', prog: 'Vakuumtest (VPR)', dur: '00:16:48', ok: true },
  { charge: 'CH021663', date: '12.04.2026', time: '16:48 Uhr', prog: 'Instrumente 134 °C', dur: '00:31:22', ok: false },
  { charge: 'CH021662', date: '12.04.2026', time: '13:22 Uhr', prog: 'Textilien 121 °C', dur: '01:02:55', ok: true },
  { charge: 'CH021661', date: '12.04.2026', time: '09:51 Uhr', prog: 'Instrumente 134 °C', dur: '00:48:31', ok: true },
  { charge: 'CH021660', date: '12.04.2026', time: '06:30 Uhr', prog: 'Bowie-Dick-Test', dur: '00:24:11', ok: true },
];

function FilterBar() {
  const reset = (e) => {
    const bar = e.target.closest('.filterbar');
    bar.querySelectorAll('select').forEach((s) => { s.selectedIndex = 0; });
    bar.querySelectorAll('input[type=number]').forEach((i) => { i.value = ''; });
  };
  return (
    <div className="filterbar">
      <div className="fld">
        <label>Status</label>
        <select className="ctrl"><option>Alle</option><option>Bestanden</option><option>Fehlgeschlagen</option></select>
      </div>
      <div className="fld">
        <label>Programm</label>
        <select className="ctrl">
          <option>Alle</option><option>Instrumente 134 °C</option><option>Bowie-Dick-Test</option>
          <option>Vakuumtest (VPR)</option><option>Textilien 121 °C</option>
        </select>
      </div>
      <div className="fld">
        <label>Datum</label>
        <div className="range-pair">
          <input type="date" className="ctrl date" defaultValue="2026-04-12" />
          <span className="sep">bis</span>
          <input type="date" className="ctrl date" defaultValue="2026-04-13" />
        </div>
      </div>
      <div className="fld">
        <label>Charge-Nr.</label>
        <div className="range-pair">
          <input type="number" className="ctrl num" placeholder="von" defaultValue="21660" />
          <span className="sep">bis</span>
          <input type="number" className="ctrl num" placeholder="bis" defaultValue="21667" />
        </div>
      </div>
      <div className="spacer"></div>
      <button className="btn btn-primary"><i className="bi bi-funnel"></i> Filter anwenden</button>
      <button className="btn btn-outline" onClick={reset}><i className="bi bi-arrow-counterclockwise"></i> Zurücksetzen</button>
    </div>
  );
}

function Dashboard({ connected }) {
  return (
    <React.Fragment>
      <div className="stat-row">
        <div className="stat">
          <div className="icon-tile navy"><i className="bi bi-plug"></i></div>
          <div className="label">Verbindungsstatus</div>
          <div className={'conn ' + (connected ? 'online' : 'offline')}>
            <span className="dot"></span> {connected ? 'Verbunden' : 'Getrennt'}
          </div>
          <div className="sub">/dev/ttyUSB0 · 9600 Baud · 8N1</div>
        </div>
        <div className="stat">
          <div className="icon-tile blue"><i className="bi bi-file-earmark-pdf"></i></div>
          <div className="label">Protokolle heute</div>
          <div className="big">18</div>
          <div className="sub">Letztes um 14:52 Uhr</div>
        </div>
        <div className="stat">
          <div className="icon-tile blue"><i className="bi bi-collection"></i></div>
          <div className="label">Protokolle gesamt</div>
          <div className="big">327</div>
          <div className="sub">Seit Inbetriebnahme 24.01.2026</div>
        </div>
      </div>

      <FilterBar />

      <div className="card">
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th className="sorted">Charge-Nr. <i className="bi bi-arrow-down sort"></i></th>
                <th>Datum &amp; Uhrzeit <i className="bi bi-chevron-expand sort"></i></th>
                <th>Programm <i className="bi bi-chevron-expand sort"></i></th>
                <th>Dauer <i className="bi bi-chevron-expand sort"></i></th>
                <th>Status <i className="bi bi-chevron-expand sort"></i></th>
                <th className="right">Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {PROTOCOLS.map((p) => (
                <tr key={p.charge}>
                  <td><span className="charge">{p.charge}</span></td>
                  <td><div className="dt-main">{p.date}</div><div className="dt-sub">{p.time}</div></td>
                  <td>{p.prog}</td>
                  <td className="dur">{p.dur}</td>
                  <td>
                    {p.ok
                      ? <span className="badge ok"><span className="bdot"></span> Bestanden</span>
                      : <span className="badge fail"><span className="bdot"></span> Fehlgeschlagen</span>}
                  </td>
                  <td className="right">
                    <div className="act">
                      <button className="icon-btn" title="PDF herunterladen"><i className="bi bi-file-earmark-pdf"></i></button>
                      <button className="icon-btn" title="Drucken"><i className="bi bi-printer"></i></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="table-foot">
          <span>1–20 von <strong>327</strong> Protokollen</span>
          <div className="pager">
            <span className="pg disabled"><i className="bi bi-chevron-left"></i></span>
            <span className="pg active">1</span>
            <span className="pg">2</span>
            <span className="pg">3</span>
            <span className="pg">…</span>
            <span className="pg">17</span>
            <span className="pg"><i className="bi bi-chevron-right"></i></span>
          </div>
        </div>
      </div>
    </React.Fragment>
  );
}

Object.assign(window, { Dashboard });
