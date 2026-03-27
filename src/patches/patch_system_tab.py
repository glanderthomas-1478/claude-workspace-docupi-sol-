#!/usr/bin/env python3
"""Add full System tab to settings.html"""

with open("/home/belimed/docupi/templates/settings.html", "r") as f:
    html = f.read()

# 1. Add System tab button to the nav pills
old_nav = '<li class="nav-item"><a class="nav-link" data-bs-toggle="pill" href="#tabUsb"><i class="bi bi-usb-drive"></i> USB / Wartung</a></li>'
new_nav = old_nav + '\n  <li class="nav-item"><a class="nav-link" data-bs-toggle="pill" href="#tabSystem"><i class="bi bi-cpu"></i> System</a></li>'
html = html.replace(old_nav, new_nav)

# 2. Remove the old inline system block from USB tab
old_system_block = '''<div class="col-md-6">
<div class="config-section">
<h5><span class="section-icon"><i class="bi bi-cpu"></i></span> System</h5>
<div class="info-panel mb-3" id="sysInfo">Lade...</div>
<div class="d-flex gap-2">
<button class="btn btn-outline-warning" onclick="if(confirm('DocuPi-3000 wirklich neustarten?')) fetch('/api/system/reboot',{method:'POST'}).then(()=>showToast('Neustart','System wird neu gestartet...',true))"><i class="bi bi-arrow-clockwise"></i> System Neustart</button>
<button class="btn btn-outline-secondary" onclick="fetch('/api/receiver/restart',{method:'POST'}).then(()=>showToast('Empfaenger','Serieller Empfaenger neu gestartet',true))"><i class="bi bi-arrow-repeat"></i> Empfaenger Neustart</button>
</div></div></div>'''
html = html.replace(old_system_block, '')

# 3. Add the full System tab pane before closing tab-content
system_tab = '''
<!-- ============ TAB: SYSTEM ============ -->
<div class="tab-pane fade" id="tabSystem">
<style>
.health-card{background:#fff;border-radius:10px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.08);height:100%}
.health-card h6{color:var(--db);font-weight:600;margin-bottom:15px;font-size:1rem}
.health-card .icon-lg{font-size:1.8rem;color:var(--db)}
.meter-bar{height:8px;border-radius:4px;background:#e9ecef;overflow:hidden;margin:6px 0}
.meter-bar .fill{height:100%;border-radius:4px;transition:width .5s}
.fill-ok{background:linear-gradient(90deg,#28a745,#20c997)}
.fill-warn{background:linear-gradient(90deg,#ffc107,#fd7e14)}
.fill-danger{background:linear-gradient(90deg,#dc3545,#c82333)}
.temp-gauge{display:inline-flex;align-items:center;gap:8px}
.temp-icon{font-size:2rem}
.temp-icon.ok{color:#28a745}
.temp-icon.warm{color:#ffc107}
.temp-icon.hot{color:#fd7e14}
.temp-icon.critical{color:#dc3545}
.stat-mini{text-align:center;padding:10px}
.stat-mini .val{font-size:1.5rem;font-weight:700;color:var(--db)}
.stat-mini .lbl{font-size:.75rem;color:#6c757d;text-transform:uppercase}
.health-badge{font-size:.8rem;padding:4px 10px;border-radius:12px;font-weight:600}
.health-good{background:#d4edda;color:#155724}
.health-warning{background:#fff3cd;color:#856404}
.health-critical{background:#f8d7da;color:#721c24}
.info-row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f0f0f0}
.info-row:last-child{border-bottom:none}
.info-row .label{color:#6c757d;font-size:.85rem}
.info-row .value{font-weight:500;font-size:.85rem}
.refresh-btn{position:absolute;top:15px;right:15px;border:none;background:none;color:var(--db);cursor:pointer;font-size:1.1rem}
.refresh-btn:hover{color:var(--docupi-light)}
</style>

<div class="d-flex justify-content-between align-items-center mb-3">
  <h5 class="mb-0"><i class="bi bi-speedometer2 text-primary"></i> Systemuebersicht</h5>
  <button class="btn btn-outline-primary btn-sm" onclick="loadSystemHealth()"><i class="bi bi-arrow-clockwise"></i> Aktualisieren</button>
</div>

<div class="row g-3" id="systemDashboard">

  <!-- Uptime & Service -->
  <div class="col-md-4">
    <div class="health-card">
      <h6><i class="bi bi-clock-history"></i> Betriebszeit</h6>
      <div class="stat-mini"><div class="val" id="sysUptime">--</div><div class="lbl">Laufzeit</div></div>
      <div class="info-row"><span class="label">Service Status</span><span class="value" id="sysSvcStatus">--</span></div>
      <div class="info-row"><span class="label">Gestartet</span><span class="value" id="sysSvcStarted">--</span></div>
      <div class="info-row"><span class="label">Seriell</span><span class="value" id="sysSerial">--</span></div>
      <div class="info-row"><span class="label">Protokolle heute</span><span class="value" id="sysTodayCount">--</span></div>
      <div class="info-row"><span class="label">Protokolle gesamt</span><span class="value" id="sysTotalCount">--</span></div>
    </div>
  </div>

  <!-- CPU -->
  <div class="col-md-4">
    <div class="health-card">
      <h6><i class="bi bi-cpu"></i> Prozessor</h6>
      <div class="d-flex align-items-center mb-3">
        <div class="temp-gauge">
          <i class="bi bi-thermometer-half temp-icon" id="cpuTempIcon"></i>
          <div><span style="font-size:2rem;font-weight:700" id="cpuTemp">--</span><span class="text-muted"> C</span></div>
        </div>
      </div>
      <div class="info-row"><span class="label">CPU Auslastung</span><span class="value" id="cpuUsage">--%</span></div>
      <div class="meter-bar"><div class="fill" id="cpuUsageBar" style="width:0%"></div></div>
      <div class="info-row"><span class="label">Load (1/5/15 min)</span><span class="value" id="cpuLoad">--</span></div>
      <div class="info-row"><span class="label">Modell</span><span class="value" id="cpuModel">--</span></div>
      <div class="info-row"><span class="label">Kerne</span><span class="value" id="cpuCores">--</span></div>
    </div>
  </div>

  <!-- Memory -->
  <div class="col-md-4">
    <div class="health-card">
      <h6><i class="bi bi-memory"></i> Arbeitsspeicher</h6>
      <div class="d-flex justify-content-between align-items-end mb-2">
        <div><span style="font-size:1.8rem;font-weight:700;color:var(--db)" id="memUsed">--</span><span class="text-muted"> / <span id="memTotal">--</span> MB</span></div>
        <span class="text-muted" id="memPercent">--%</span>
      </div>
      <div class="meter-bar"><div class="fill" id="memBar" style="width:0%"></div></div>
      <div class="info-row mt-2"><span class="label">Verfuegbar</span><span class="value" id="memFree">-- MB</span></div>
      <div class="info-row"><span class="label">Swap</span><span class="value" id="memSwap">--</span></div>
    </div>
  </div>

  <!-- SD Card -->
  <div class="col-md-6">
    <div class="health-card">
      <h6><i class="bi bi-sd-card"></i> SD-Karte (Systemspeicher)</h6>
      <div class="d-flex justify-content-between align-items-center mb-2">
        <div><span style="font-size:1.5rem;font-weight:700;color:var(--db)" id="sdUsed">--</span><span class="text-muted"> / <span id="sdTotal">--</span> GB belegt</span></div>
        <span class="health-badge" id="sdHealthBadge">--</span>
      </div>
      <div class="meter-bar"><div class="fill" id="sdBar" style="width:0%"></div></div>
      <div class="row mt-3">
        <div class="col-4 stat-mini"><div class="val" id="sdFree">--</div><div class="lbl">GB frei</div></div>
        <div class="col-4 stat-mini"><div class="val" id="sdPercent">--</div><div class="lbl">% belegt</div></div>
        <div class="col-4 stat-mini"><div class="val" id="sdWrites">--</div><div class="lbl">GB geschrieben</div></div>
      </div>
      <div class="info-row"><span class="label">I/O-Fehler (dmesg)</span><span class="value" id="sdErrors">--</span></div>
    </div>
  </div>

  <!-- Network -->
  <div class="col-md-6">
    <div class="health-card">
      <h6><i class="bi bi-hdd-network"></i> Netzwerk</h6>
      <table class="table table-sm table-borderless mb-2">
        <thead><tr><th style="font-size:.8rem;color:#6c757d">Interface</th><th style="font-size:.8rem;color:#6c757d">Status</th><th style="font-size:.8rem;color:#6c757d">IP-Adresse</th></tr></thead>
        <tbody>
          <tr><td><i class="bi bi-ethernet"></i> eth0</td><td id="netEth0State">--</td><td id="netEth0IP">--</td></tr>
          <tr><td><i class="bi bi-wifi"></i> wlan0</td><td id="netWlan0State">--</td><td id="netWlan0IP">--</td></tr>
        </tbody>
      </table>
      <div class="info-row"><span class="label">WiFi Clients verbunden</span><span class="value" id="netWifiClients">--</span></div>
    </div>
  </div>

  <!-- OS Info -->
  <div class="col-md-6">
    <div class="health-card">
      <h6><i class="bi bi-info-circle"></i> Systeminformationen</h6>
      <div class="info-row"><span class="label">Hostname</span><span class="value" id="osHostname">--</span></div>
      <div class="info-row"><span class="label">Betriebssystem</span><span class="value" id="osDistro">--</span></div>
      <div class="info-row"><span class="label">Kernel</span><span class="value" id="osKernel">--</span></div>
      <div class="info-row"><span class="label">Architektur</span><span class="value" id="osArch">--</span></div>
      <div class="info-row"><span class="label">Python</span><span class="value" id="osPython">--</span></div>
    </div>
  </div>

  <!-- Actions -->
  <div class="col-md-6">
    <div class="health-card">
      <h6><i class="bi bi-tools"></i> Wartung</h6>
      <p class="text-muted" style="font-size:.85rem">Service- und Systemsteuerung</p>
      <div class="d-grid gap-2">
        <button class="btn btn-outline-secondary" onclick="fetch('/api/receiver/restart',{method:'POST'}).then(()=>showToast('Empfaenger','Serieller Empfaenger neu gestartet',true))">
          <i class="bi bi-arrow-repeat"></i> Seriellen Empfaenger neustarten
        </button>
        <button class="btn btn-outline-warning" onclick="if(confirm('DocuPi-3000 Service wirklich neustarten?')) fetch('/api/receiver/restart',{method:'POST'}).then(()=>{showToast('Service','Wird neu gestartet...',true);setTimeout(()=>location.reload(),3000)})">
          <i class="bi bi-arrow-clockwise"></i> DocuPi Service neustarten
        </button>
        <button class="btn btn-outline-danger" onclick="if(confirm('Raspberry Pi wirklich neustarten? Das dauert ca. 30 Sekunden.')) fetch('/api/system/reboot',{method:'POST'}).then(()=>showToast('System','Neustart wird ausgefuehrt...',true))">
          <i class="bi bi-power"></i> System neustarten (Reboot)
        </button>
      </div>
      <div class="warning-box mt-3"><i class="bi bi-exclamation-triangle"></i> <strong>Hinweis:</strong> Beim Reboot wird der serielle Empfang kurzzeitig unterbrochen.</div>
    </div>
  </div>

</div><!-- row -->
</div>
'''

# Insert before closing tab-content div
marker = '</div><!-- tab-content -->'
html = html.replace(marker, system_tab + '\n' + marker)

# 4. Replace the old loadSysInfo with the new comprehensive loadSystemHealth
old_js = '''// --- System Info ---
function loadSysInfo() {
  fetch('/api/status').then(function(r){return r.json()}).then(function(d) {
    document.getElementById('sysInfo').innerHTML =
      '<table class="table table-sm table-borderless mb-0">' +
      '<tr><td class="text-muted">CPU Temp:</td><td><strong>' + d.cpu_temp + ' °C</strong></td></tr>' +
      '<tr><td class="text-muted">Seriell:</td><td>' + (d.serial.connected ? '<span class="text-success">Verbunden</span>' : '<span class="text-danger">Getrennt</span>') + ' (' + d.serial.port + ')</td></tr>' +
      '<tr><td class="text-muted">Protokolle:</td><td>Heute: ' + d.today_count + ' / Gesamt: ' + d.total_count + '</td></tr>' +
      '</table>';
  }).catch(function(){});
}

// Init
loadUsbStatus();
loadSysInfo();'''

new_js = '''// --- System Health ---
function meterClass(pct) { return pct < 70 ? 'fill-ok' : pct < 85 ? 'fill-warn' : 'fill-danger'; }
function stateHtml(state) {
  if (state === 'UP') return '<span class="text-success"><i class="bi bi-check-circle-fill"></i> UP</span>';
  if (state === 'DOWN') return '<span class="text-danger"><i class="bi bi-x-circle-fill"></i> DOWN</span>';
  return '<span class="text-muted">' + state + '</span>';
}

function loadSystemHealth() {
  fetch('/api/system/health').then(function(r){return r.json()}).then(function(d) {
    // Uptime & Service
    document.getElementById('sysUptime').textContent = d.uptime.text;
    document.getElementById('sysSvcStatus').innerHTML = d.service.status === 'active'
      ? '<span class="badge bg-success">active</span>' : '<span class="badge bg-danger">' + d.service.status + '</span>';
    document.getElementById('sysSvcStarted').textContent = d.service.started || '-';
    document.getElementById('sysSerial').innerHTML = d.service.serial.connected
      ? '<span class="text-success">Verbunden</span> (' + d.service.serial.port + ')'
      : '<span class="text-danger">Getrennt</span>';
    document.getElementById('sysTodayCount').textContent = d.service.today_count;
    document.getElementById('sysTotalCount').textContent = d.service.total_count;

    // CPU
    document.getElementById('cpuTemp').textContent = d.cpu.temp;
    var ti = document.getElementById('cpuTempIcon');
    ti.className = 'bi bi-thermometer-half temp-icon ' + d.cpu.temp_status;
    document.getElementById('cpuUsage').textContent = d.cpu.usage + '%';
    var ub = document.getElementById('cpuUsageBar');
    ub.style.width = d.cpu.usage + '%';
    ub.className = 'fill ' + meterClass(d.cpu.usage);
    document.getElementById('cpuLoad').textContent = d.cpu.load_1 + ' / ' + d.cpu.load_5 + ' / ' + d.cpu.load_15;
    document.getElementById('cpuModel').textContent = d.cpu.model || '-';
    document.getElementById('cpuCores').textContent = d.cpu.cores;

    // Memory
    document.getElementById('memUsed').textContent = d.memory.used_mb;
    document.getElementById('memTotal').textContent = d.memory.total_mb;
    document.getElementById('memPercent').textContent = d.memory.percent + '%';
    var mb = document.getElementById('memBar');
    mb.style.width = d.memory.percent + '%';
    mb.className = 'fill ' + meterClass(d.memory.percent);
    document.getElementById('memFree').textContent = d.memory.free_mb + ' MB';
    document.getElementById('memSwap').textContent = d.memory.swap_free_mb + ' / ' + d.memory.swap_total_mb + ' MB frei';

    // SD Card
    document.getElementById('sdUsed').textContent = d.sd_card.used_gb;
    document.getElementById('sdTotal').textContent = d.sd_card.total_gb;
    var sb = document.getElementById('sdBar');
    sb.style.width = d.sd_card.percent + '%';
    sb.className = 'fill ' + meterClass(d.sd_card.percent);
    document.getElementById('sdFree').textContent = d.sd_card.free_gb;
    document.getElementById('sdPercent').textContent = d.sd_card.percent;
    document.getElementById('sdWrites').textContent = d.sd_card.lifetime_writes_gb;
    document.getElementById('sdErrors').textContent = d.sd_card.io_errors;
    var hb = document.getElementById('sdHealthBadge');
    if (d.sd_card.health === 'good') { hb.textContent = 'Gesund'; hb.className = 'health-badge health-good'; }
    else if (d.sd_card.health === 'warning') { hb.textContent = 'Warnung'; hb.className = 'health-badge health-warning'; }
    else { hb.textContent = 'Kritisch'; hb.className = 'health-badge health-critical'; }

    // Network
    var ifaces = d.network.interfaces || {};
    if (ifaces.eth0) {
      document.getElementById('netEth0State').innerHTML = stateHtml(ifaces.eth0.state);
      document.getElementById('netEth0IP').textContent = ifaces.eth0.ip;
    }
    if (ifaces.wlan0) {
      document.getElementById('netWlan0State').innerHTML = stateHtml(ifaces.wlan0.state);
      document.getElementById('netWlan0IP').textContent = ifaces.wlan0.ip;
    }
    document.getElementById('netWifiClients').textContent = d.network.wifi_clients;

    // OS
    document.getElementById('osHostname').textContent = d.os.hostname;
    document.getElementById('osDistro').textContent = d.os.distro;
    document.getElementById('osKernel').textContent = d.os.kernel;
    document.getElementById('osArch').textContent = d.os.arch;
    document.getElementById('osPython').textContent = d.os.python;
  }).catch(function(e) { console.error('System health error:', e); });
}

// Init
loadUsbStatus();
loadSystemHealth();
// Auto-refresh system health every 10s
setInterval(loadSystemHealth, 10000);'''

html = html.replace(old_js, new_js)

with open("/home/belimed/docupi/templates/settings.html", "w") as f:
    f.write(html)

print("OK: System tab added")
