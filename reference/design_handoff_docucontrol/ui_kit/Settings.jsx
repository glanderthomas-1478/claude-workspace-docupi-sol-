// Settings.jsx — Einstellungen: sub-nav with "Geräte & Netzwerk" and the integrated "Live-Monitor"
const { useState, useEffect, useRef } = React;

// Synthetic sterilizer protocol lines, streamed to feel like RS232 traffic
const SAMPLE_LINES = [
  'STERILISATOR  Belimed 9-6-18 HS2   Nr. 27163',
  'PROGRAMM 01   VAKUUM-DAMPF 134 GRAD',
  'CHARGE       CH021667',
  'START        2026-04-13  14:30:25',
  'VORVAKUUM 1  -0.85 bar    OK',
  'VORVAKUUM 2  -0.86 bar    OK',
  'VORVAKUUM 3  -0.85 bar    OK',
  'PLATEAU      134.2 GRAD   3.12 bar',
  'HALTEZEIT    05:00 min    OK',
  'TROCKNUNG    08:00 min',
  'ENDE         2026-04-13  14:52:41',
  'ERGEBNIS     CHARGE FREIGEGEBEN   OK',
];

function DevicesNetwork() {
  return (
    <div className="set-grid">
      <div className="card">
        <div className="card-head"><span><i className="bi bi-printer"></i> Drucker</span></div>
        <div className="card-body">
          <div className="set-row">
            <div className="info"><div className="name">USB-Drucker erkennen</div><div className="desc">Angeschlossene Drucker suchen</div></div>
            <button className="btn btn-outline"><i className="bi bi-search"></i> Suchen</button>
          </div>
          <div className="set-row">
            <div className="info"><div className="name">Erkannter Drucker</div><div className="desc">Aktuell verbundenes Gerät</div></div>
            <span className="value">Brother QL-820NWB</span>
          </div>
          <div className="set-row">
            <div className="info"><div className="name">Testdruck</div><div className="desc">Eine Testseite ausgeben</div></div>
            <button className="btn btn-outline"><i className="bi bi-file-earmark-text"></i> Testdruck</button>
          </div>
          <div className="set-row">
            <div className="info"><div className="name">Automatisch drucken bei neuem Protokoll</div><div className="desc">Druckt jede abgeschlossene Charge automatisch</div></div>
            <label className="switch"><input type="checkbox" defaultChecked /><span className="track"></span></label>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head"><span><i className="bi bi-hdd-network"></i> Netzwerk</span></div>
        <div className="card-body">
          <div className="set-row">
            <div className="info"><div className="name">IP-Adresse</div><div className="desc">Aktuelle Adresse im Netzwerk</div></div>
            <span className="mono-ip">192.168.178.83</span>
          </div>
          <div className="set-row">
            <div className="info"><div className="name">Hotspot-Modus</div><div className="desc">Eigenes WLAN bereitstellen</div></div>
            <label className="switch"><input type="checkbox" defaultChecked /><span className="track"></span></label>
          </div>
          <div className="field-2">
            <div className="set-field"><label>SSID</label><input className="ctrl" defaultValue="DocuControl-AP" /></div>
            <div className="set-field"><label>Passwort</label><input className="ctrl" type="password" defaultValue="DocuPi2026" /></div>
          </div>
          <div className="set-row" style={{ marginTop: 6 }}>
            <div className="info"><div className="name">WLAN-Client</div><div className="desc">Mit vorhandenem Netzwerk verbinden</div></div>
            <span className="pill-status off"><span className="dot"></span> Getrennt</span>
          </div>
          <div className="field-2">
            <div className="set-field"><label>SSID</label><input className="ctrl" placeholder="Netzwerkname" /></div>
            <div className="set-field"><label>Passwort</label><input className="ctrl" type="password" placeholder="••••••••" /></div>
          </div>
          <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
            <button className="btn btn-primary"><i className="bi bi-wifi"></i> Verbinden</button>
            <button className="btn btn-outline-danger"><i className="bi bi-arrow-clockwise"></i> Netzwerk neu starten</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function LiveMonitor({ connected }) {
  const [lines, setLines] = useState([]);
  const [bytes, setBytes] = useState(0);
  const [today, setToday] = useState(18);
  const [total, setTotal] = useState(327);
  const [lastPdf, setLastPdf] = useState(null);
  const [lastCharge, setLastCharge] = useState('CH021667');
  const [rx, setRx] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const termRef = useRef(null);
  const idx = useRef(0);

  useEffect(() => {
    if (!connected) return undefined;
    const t = setInterval(() => {
      const line = SAMPLE_LINES[idx.current % SAMPLE_LINES.length];
      const isEnd = line.startsWith('ERGEBNIS');
      idx.current += 1;
      setRx(true);
      setTimeout(() => setRx(false), 220);
      setBytes((b) => b + line.length + 2);
      setLines((prev) => [...prev, { text: line, end: isEnd }].slice(-80));
      if (isEnd) {
        const charge = 'CH0' + (21667 + Math.floor(idx.current / SAMPLE_LINES.length));
        const fn = charge + '_Instrumente_134C_2026-04-13.pdf';
        setLines((prev) => [...prev, { text: '>>> PDF erzeugt: ' + fn + '  (48.213 B)', pdf: true }].slice(-80));
        setLastPdf(fn);
        setLastCharge(charge);
        setToday((c) => c + 1);
        setTotal((c) => c + 1);
      }
    }, 1100);
    return () => clearInterval(t);
  }, [connected]);

  useEffect(() => {
    if (autoScroll && termRef.current) termRef.current.scrollTop = termRef.current.scrollHeight;
  }, [lines, autoScroll]);

  return (
    <React.Fragment>
      <div className="stat-row mon">
        <div className="stat">
          <div className="icon-tile navy"><i className="bi bi-plug"></i></div>
          <div className="label">Empfänger</div>
          <div className={'conn ' + (connected ? 'online' : 'offline')} style={{ fontSize: 22 }}>
            <span className="dot"></span> {connected ? 'Verbunden' : 'Getrennt'}
          </div>
          <div className="sub">/dev/ttyUSB0 · 9600 · 8N1</div>
        </div>
        <div className="stat">
          <div className="icon-tile blue"><i className="bi bi-file-earmark-pdf"></i></div>
          <div className="label">Protokolle heute</div>
          <div className="big">{today}</div>
          <div className="sub">seit 00:00 Uhr</div>
        </div>
        <div className="stat">
          <div className="icon-tile navy"><i className="bi bi-collection"></i></div>
          <div className="label">Protokolle gesamt</div>
          <div className="big">{total.toLocaleString('de-DE')}</div>
          <div className="sub">seit Inbetriebnahme</div>
        </div>
        <div className="stat">
          <div className="icon-tile green"><i className="bi bi-check2-circle"></i></div>
          <div className="label">Letzte Charge</div>
          <div className="big" style={{ fontFamily: 'var(--mono)', fontSize: 22 }}>{lastCharge}</div>
          <div className="sub">Instrumente 134 °C</div>
        </div>
      </div>

      {lastPdf && (
        <div className="last-pdf">
          <span className="ic"><i className="bi bi-check-circle-fill"></i></span>
          <span><strong>Neues Protokoll gespeichert:</strong> <span style={{ fontFamily: 'var(--mono)' }}>{lastPdf}</span></span>
        </div>
      )}

      <div className="monitor-head">
        <h6><i className="bi bi-terminal"></i> Serieller Live-Monitor</h6>
        <div className="monitor-tools">
          <span className="badge mono"><i className="bi bi-arrow-down-circle"></i> {bytes.toLocaleString('de-DE')} Bytes</span>
          <label className="switch-mini">
            <input type="checkbox" checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} /> Auto-Scroll
          </label>
          <button className="btn btn-outline-danger sm" onClick={() => { setLines([]); setBytes(0); }}>
            <i className="bi bi-trash"></i> Leeren
          </button>
        </div>
      </div>
      <div className="th">
        <span><i className="bi bi-plug"></i> /dev/ttyUSB0 @ 9600 baud · 8N1</span>
        <span><span className="blink" style={{ color: '#00ff41', visibility: rx ? 'visible' : 'hidden' }}>&#9679;</span> RX</span>
      </div>
      <div id="terminal" ref={termRef}>
        {lines.length === 0 && connected && <div style={{ color: '#888' }}>— warte auf Daten vom Sterilisator …</div>}
        {lines.map((l, i) => (
          <div key={i} style={l.pdf ? { color: '#00bcd4', fontWeight: 'bold', margin: '5px 0' } : (l.end ? { color: '#00ff41', fontWeight: 'bold' } : null)}>
            {l.text}
          </div>
        ))}
        {!connected && <div style={{ color: '#888' }}>— Empfänger getrennt —</div>}
      </div>
    </React.Fragment>
  );
}

function Settings({ connected }) {
  const [tab, setTab] = useState('devices');
  return (
    <React.Fragment>
      <div className="subnav">
        <div className={'subtab' + (tab === 'devices' ? ' active' : '')} onClick={() => setTab('devices')}>
          <i className="bi bi-sliders"></i> Geräte &amp; Netzwerk
        </div>
        <div className={'subtab' + (tab === 'monitor' ? ' active' : '')} onClick={() => setTab('monitor')}>
          <i className="bi bi-terminal"></i> Live-Monitor
        </div>
      </div>
      {tab === 'devices' && <DevicesNetwork />}
      {tab === 'monitor' && <LiveMonitor connected={connected} />}
    </React.Fragment>
  );
}

Object.assign(window, { Settings });
