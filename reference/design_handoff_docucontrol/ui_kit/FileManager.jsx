// FileManager.jsx — Dateien: dual-pane internal storage / USB with sync

const SD_FILES = [
  { name: 'CH021667_Instrumente_134C_2026-04-13.pdf', date: '13.04.2026', size: '48,2 KB' },
  { name: 'CH021666_Instrumente_134C_2026-04-13.pdf', date: '13.04.2026', size: '47,9 KB' },
  { name: 'CH021665_BowieDick_2026-04-13.pdf', date: '13.04.2026', size: '31,4 KB' },
  { name: 'CH021664_Vakuumtest_2026-04-13.pdf', date: '13.04.2026', size: '22,8 KB' },
  { name: 'CH021663_Instrumente_134C_2026-04-12.pdf', date: '12.04.2026', size: '49,1 KB' },
  { name: 'CH021662_Textilien_121C_2026-04-12.pdf', date: '12.04.2026', size: '52,7 KB' },
];

const USB_FILES = [
  { name: 'CH021666_Instrumente_134C_2026-04-13.pdf', date: '13.04.2026', size: '47,9 KB' },
  { name: 'CH021665_BowieDick_2026-04-13.pdf', date: '13.04.2026', size: '31,4 KB' },
  { name: 'CH021663_Instrumente_134C_2026-04-12.pdf', date: '12.04.2026', size: '49,1 KB' },
];

function FileTable({ files }) {
  return (
    <table className="filelist">
      <thead>
        <tr><th>Dateiname</th><th>Datum</th><th>Größe</th><th className="right">Aktionen</th></tr>
      </thead>
      <tbody>
        {files.map((f) => (
          <tr key={f.name}>
            <td className="fn"><i className="bi bi-file-earmark-pdf-fill"></i> {f.name}</td>
            <td className="muted">{f.date}</td>
            <td className="muted">{f.size}</td>
            <td className="right">
              <div className="act">
                <button className="icon-btn" title="Herunterladen"><i className="bi bi-download"></i></button>
                <button className="icon-btn danger" title="Löschen"><i className="bi bi-trash"></i></button>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function FileManager() {
  return (
    <div className="two-col">
      <div className="card">
        <div className="card-head"><span><i className="bi bi-hdd"></i> Interner Speicher</span></div>
        <div className="card-body">
          <div className="storagebar">
            <div className="top"><span>Belegt</span><span className="used">12,4 GB / 32 GB</span></div>
            <div className="meter"><div className="fill" style={{ width: '39%' }}></div></div>
          </div>
          <FileTable files={SD_FILES} />
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <span><i className="bi bi-usb-drive"></i> USB / Externer Speicher</span>
          <span className="usb-status"><span className="dot"></span> Verbunden</span>
        </div>
        <div className="card-body">
          <div className="storagebar">
            <div className="top"><span>Belegt</span><span className="used">3,1 GB / 16 GB</span></div>
            <div className="meter"><div className="fill" style={{ width: '19%' }}></div></div>
          </div>
          <FileTable files={USB_FILES} />
          <div className="sync-row">
            <span className="lbl">Synchronisation</span>
            <span className="ok"><i className="bi bi-check-circle-fill"></i> Aktuell</span>
            <span className="spacer"></span>
            <button className="btn btn-outline"><i className="bi bi-arrow-repeat"></i> Jetzt sync.</button>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { FileManager });
