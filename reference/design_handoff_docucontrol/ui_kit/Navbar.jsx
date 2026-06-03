// Navbar.jsx — DocuControl top navigation: dark topbar + tab strip
function Navbar({ active, onNavigate, connected, onToggleConn }) {
  const items = [
    { id: 'dashboard', label: 'Dashboard', icon: 'bi-speedometer2' },
    { id: 'files', label: 'Dateien', icon: 'bi-folder2-open' },
    { id: 'settings', label: 'Einstellungen', icon: 'bi-gear' },
  ];
  return (
    <React.Fragment>
      <div className="topbar">
        <div className="brand" style={{ cursor: 'pointer' }} onClick={() => onNavigate('dashboard')}>
          <span className="logo">DocuControl<span className="by">by GeTmatic</span></span>
        </div>
        <span
          className={'conn-badge ' + (connected ? 'online' : 'offline')}
          style={{ cursor: 'pointer' }}
          onClick={onToggleConn}
          title="Verbindung umschalten"
        >
          <span className="dot"></span>
          <span>{connected ? 'Verbunden' : 'Getrennt'}</span>
        </span>
      </div>
      <nav className="navstrip">
        {items.map((it) => (
          <div
            key={it.id}
            className={'tab' + (active === it.id ? ' active' : '')}
            data-view={it.id}
            onClick={() => onNavigate(it.id)}
          >
            <i className={'bi ' + it.icon}></i> {it.label}
          </div>
        ))}
      </nav>
    </React.Fragment>
  );
}

Object.assign(window, { Navbar });
