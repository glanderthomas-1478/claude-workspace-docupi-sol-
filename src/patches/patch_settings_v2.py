#!/usr/bin/env python3
"""Fix CSS variables, add Logs tab to settings"""

# ===================== SETTINGS HTML =====================
with open("/home/belimed/docupi/templates/settings.html", "r") as f:
    html = f.read()

# 1. Fix all var(--db) and var(--bg) references
html = html.replace("var(--db)", "var(--docupi-blue)")
html = html.replace("var(--bg)", "var(--docupi-bg)")

# 2. Make active tab more visible - add stronger styling
old_pill_css = ".nav-pills .nav-link.active{background:var(--docupi-blue);color:#fff}"
new_pill_css = ".nav-pills .nav-link.active{background:var(--docupi-blue);color:#fff !important;box-shadow:0 2px 6px rgba(31,78,121,.35)}"
html = html.replace(old_pill_css, new_pill_css)

# Also fix the hover state for better visibility
old_pill_base = ".nav-pills .nav-link{color:#495057;border-radius:8px;padding:10px 20px;font-weight:500}"
new_pill_base = ".nav-pills .nav-link{color:#495057;background:#e9ecef;border-radius:8px;padding:10px 20px;font-weight:500;margin-right:4px;transition:all .2s}\n.nav-pills .nav-link:hover:not(.active){background:#dee2e6;color:#1f4e79}"
html = html.replace(old_pill_base, new_pill_base)

# 3. Add Logs tab button to nav pills
old_system_tab = '<li class="nav-item"><a class="nav-link" data-bs-toggle="pill" href="#tabSystem"><i class="bi bi-cpu"></i> System</a></li>'
new_tabs = old_system_tab + '\n  <li class="nav-item"><a class="nav-link" data-bs-toggle="pill" href="#tabLogs"><i class="bi bi-journal-text"></i> Logs</a></li>'
html = html.replace(old_system_tab, new_tabs)

# 4. Add Logs tab pane before closing tab-content
logs_tab = '''
<!-- ============ TAB: LOGS ============ -->
<div class="tab-pane fade" id="tabLogs">
<style>
.log-terminal{background:#1e1e1e;color:#d4d4d4;font-family:'Courier New',monospace;font-size:12px;padding:12px;border-radius:8px;height:400px;overflow-y:auto;white-space:pre-wrap;word-wrap:break-word;border:1px solid #333}
.log-terminal .log-warn{color:#ffc107}
.log-terminal .log-err{color:#ff6b6b}
.log-terminal .log-info{color:#69c0ff}
.log-terminal .log-ok{color:#52c41a}
.log-toolbar{display:flex;gap:8px;align-items:center;margin-bottom:10px}
</style>

<div class="row g-4">
  <!-- Serial Logs -->
  <div class="col-12">
    <div class="config-section">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="mb-0"><i class="bi bi-plug" style="color:var(--docupi-blue)"></i> Serielle Kommunikation</h5>
        <div class="d-flex gap-2">
          <select class="form-select form-select-sm" id="serialLogLines" style="width:auto" onchange="loadSerialLogs()">
            <option value="50">50 Zeilen</option>
            <option value="100" selected>100 Zeilen</option>
            <option value="200">200 Zeilen</option>
            <option value="500">500 Zeilen</option>
          </select>
          <button class="btn btn-sm btn-outline-primary" onclick="loadSerialLogs()"><i class="bi bi-arrow-clockwise"></i></button>
        </div>
      </div>
      <div class="log-terminal" id="serialLogBox">Lade Serial-Logs...</div>
    </div>
  </div>

  <!-- System / Service Logs -->
  <div class="col-md-6">
    <div class="config-section">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="mb-0"><i class="bi bi-gear" style="color:var(--docupi-blue)"></i> DocuPi Service</h5>
        <button class="btn btn-sm btn-outline-primary" onclick="loadServiceLogs()"><i class="bi bi-arrow-clockwise"></i></button>
      </div>
      <div class="log-terminal" id="serviceLogBox" style="height:300px">Lade Service-Logs...</div>
    </div>
  </div>

  <!-- Kernel / dmesg Logs -->
  <div class="col-md-6">
    <div class="config-section">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="mb-0"><i class="bi bi-motherboard" style="color:var(--docupi-blue)"></i> System (Kernel)</h5>
        <div class="d-flex gap-2">
          <select class="form-select form-select-sm" id="kernelLogFilter" style="width:auto" onchange="loadKernelLogs()">
            <option value="all">Alle</option>
            <option value="usb">USB</option>
            <option value="mmc">SD-Karte</option>
            <option value="net">Netzwerk</option>
            <option value="error">Fehler</option>
          </select>
          <button class="btn btn-sm btn-outline-primary" onclick="loadKernelLogs()"><i class="bi bi-arrow-clockwise"></i></button>
        </div>
      </div>
      <div class="log-terminal" id="kernelLogBox" style="height:300px">Lade Kernel-Logs...</div>
    </div>
  </div>
</div>
</div>
'''

marker = '</div><!-- tab-content -->'
html = html.replace(marker, logs_tab + '\n' + marker)

# 5. Add JS for loading logs (before closing script tag)
logs_js = '''

// --- Logs ---
function colorizeLog(text) {
  return text.replace(/^(.*(?:error|fail|critical|fatal).*)$/gmi, '<span class="log-err">$1</span>')
    .replace(/^(.*(?:warn|warning).*)$/gmi, '<span class="log-warn">$1</span>')
    .replace(/^(.*(?:info|started|success|active).*)$/gmi, '<span class="log-info">$1</span>')
    .replace(/^(.*(?:ok|connected|mounted|synced).*)$/gmi, '<span class="log-ok">$1</span>');
}

function loadSerialLogs() {
  var n = document.getElementById('serialLogLines').value;
  fetch('/api/logs/serial?lines=' + n).then(function(r){return r.json()}).then(function(d) {
    var box = document.getElementById('serialLogBox');
    box.innerHTML = colorizeLog(d.logs || 'Keine Logs vorhanden');
    box.scrollTop = box.scrollHeight;
  }).catch(function(){ document.getElementById('serialLogBox').textContent = 'Fehler beim Laden'; });
}

function loadServiceLogs() {
  fetch('/api/logs/service?lines=80').then(function(r){return r.json()}).then(function(d) {
    var box = document.getElementById('serviceLogBox');
    box.innerHTML = colorizeLog(d.logs || 'Keine Logs vorhanden');
    box.scrollTop = box.scrollHeight;
  }).catch(function(){ document.getElementById('serviceLogBox').textContent = 'Fehler beim Laden'; });
}

function loadKernelLogs() {
  var filter = document.getElementById('kernelLogFilter').value;
  fetch('/api/logs/kernel?lines=80&filter=' + filter).then(function(r){return r.json()}).then(function(d) {
    var box = document.getElementById('kernelLogBox');
    box.innerHTML = colorizeLog(d.logs || 'Keine Logs vorhanden');
    box.scrollTop = box.scrollHeight;
  }).catch(function(){ document.getElementById('kernelLogBox').textContent = 'Fehler beim Laden'; });
}

// Load logs when tab is shown
document.querySelector('a[href="#tabLogs"]').addEventListener('shown.bs.tab', function() {
  loadSerialLogs(); loadServiceLogs(); loadKernelLogs();
});'''

# Insert before the closing </script> in the extra_js block
html = html.replace('// Auto-refresh system health every 10s', logs_js + '\n// Auto-refresh system health every 10s')

with open("/home/belimed/docupi/templates/settings.html", "w") as f:
    f.write(html)

print("OK: settings.html patched")

# ===================== APP.PY - Add log endpoints =====================
with open("/home/belimed/docupi/app.py", "r") as f:
    appcode = f.read()

log_routes = '''
@app.route("/api/logs/serial")
def api_logs_serial():
    """Get serial communication logs."""
    lines = request.args.get("lines", 100, type=int)
    log_file = "/home/belimed/docupi/data/serial.log"
    try:
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                all_lines = f.readlines()
            return jsonify({"logs": "".join(all_lines[-lines:])})
        else:
            # Fallback: app log
            log_file2 = "/home/belimed/docupi/data/docupi.log"
            if os.path.exists(log_file2):
                with open(log_file2, "r") as f:
                    all_lines = f.readlines()
                serial_lines = [l for l in all_lines if "serial" in l.lower() or "receiver" in l.lower() or "protocol" in l.lower() or "pdf" in l.lower()]
                return jsonify({"logs": "".join(serial_lines[-lines:]) or "Keine seriellen Logs gefunden"})
            return jsonify({"logs": "Keine Log-Datei gefunden"})
    except Exception as e:
        return jsonify({"logs": f"Fehler: {e}"})


@app.route("/api/logs/service")
def api_logs_service():
    """Get DocuPi service logs from journalctl."""
    lines = request.args.get("lines", 80, type=int)
    try:
        r = subprocess.run(
            ["journalctl", "-u", "docupi.service", "--no-pager", "-n", str(lines)],
            capture_output=True, text=True, timeout=10
        )
        return jsonify({"logs": r.stdout or "Keine Logs"})
    except Exception as e:
        return jsonify({"logs": f"Fehler: {e}"})


@app.route("/api/logs/kernel")
def api_logs_kernel():
    """Get kernel/dmesg logs with optional filter."""
    lines = request.args.get("lines", 80, type=int)
    filt = request.args.get("filter", "all")
    try:
        r = subprocess.run(["dmesg", "--time-format=reltime"], capture_output=True, text=True, timeout=10)
        all_lines = r.stdout.splitlines()
        if filt == "usb":
            all_lines = [l for l in all_lines if "usb" in l.lower() or "sda" in l.lower()]
        elif filt == "mmc":
            all_lines = [l for l in all_lines if "mmc" in l.lower() or "mmcblk" in l.lower()]
        elif filt == "net":
            all_lines = [l for l in all_lines if any(k in l.lower() for k in ["eth0", "wlan", "wifi", "net", "link", "dhcp", "ip"])]
        elif filt == "error":
            all_lines = [l for l in all_lines if any(k in l.lower() for k in ["error", "fail", "warn", "critical", "timeout"])]
        return jsonify({"logs": "\\n".join(all_lines[-lines:]) or "Keine passenden Logs"})
    except Exception as e:
        return jsonify({"logs": f"Fehler: {e}"})

'''

# Insert before reboot route
reboot_marker = '@app.route("/api/system/reboot", methods=["POST"])'
if reboot_marker in appcode and "/api/logs/serial" not in appcode:
    appcode = appcode.replace(reboot_marker, log_routes + reboot_marker)
    with open("/home/belimed/docupi/app.py", "w") as f:
        f.write(appcode)
    print("OK: app.py log routes added")
else:
    if "/api/logs/serial" in appcode:
        print("SKIP: log routes already exist")
    else:
        print("ERROR: marker not found")
