#!/usr/bin/env python3
"""Add live clock to Dashboard + timezone setting to settings"""

# ========== 1. DASHBOARD: Add clock card + live JS ==========
with open("/home/belimed/docupi/templates/dashboard.html", "r") as f:
    html = f.read()

# Add clock CSS
old_css = ".last-pdf .icon{color:#28a745;font-size:1.2rem}"
new_css = """.last-pdf .icon{color:#28a745;font-size:1.2rem}
.quick-stat .icon-box.clock{background:rgba(31,78,121,.08);color:var(--docupi-blue)}
.live-clock{font-size:1.6rem;font-weight:700;color:var(--docupi-blue);line-height:1.1;font-variant-numeric:tabular-nums}
.live-date{font-size:.75rem;color:#6c757d}"""
html = html.replace(old_css, new_css)

# Add clock card as first stat card
old_first_card = """<div class="row g-3 mb-3 stat-cards">
  <div class="col">
    <div class="card p-3">
      <div class="quick-stat">
        <div class="icon-box serial"><i class="bi bi-plug"></i></div>"""

new_first_card = """<div class="row g-3 mb-3 stat-cards">
  <div class="col">
    <div class="card p-3">
      <div class="quick-stat">
        <div class="icon-box clock"><i class="bi bi-clock"></i></div>
        <div class="info">
          <div class="live-clock" id="liveClock">--:--:--</div>
          <div class="live-date" id="liveDate">--</div>
        </div>
      </div>
    </div>
  </div>
  <div class="col">
    <div class="card p-3">
      <div class="quick-stat">
        <div class="icon-box serial"><i class="bi bi-plug"></i></div>"""

html = html.replace(old_first_card, new_first_card)

# Add clock JS - uses server time to avoid browser timezone mismatch
old_js_end = "},15000);\n</script>"
new_js_end = """},15000);

// --- Live Clock (syncs from server, ticks locally) ---
var serverOffset = 0;
function syncServerTime() {
  fetch('/api/system/time').then(function(r){return r.json()}).then(function(d) {
    if (d.system_time) {
      var serverNow = new Date(d.system_time);
      serverOffset = serverNow.getTime() - Date.now();
    }
  }).catch(function(){});
}
function updateClock() {
  var now = new Date(Date.now() + serverOffset);
  var pad = function(n) { return n < 10 ? '0' + n : '' + n; };
  document.getElementById('liveClock').textContent =
    pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds());
  var days = ['So','Mo','Di','Mi','Do','Fr','Sa'];
  document.getElementById('liveDate').textContent =
    days[now.getDay()] + ', ' + pad(now.getDate()) + '.' + pad(now.getMonth()+1) + '.' + now.getFullYear();
}
syncServerTime();
setInterval(updateClock, 1000);
setInterval(syncServerTime, 60000);
updateClock();
</script>"""

html = html.replace(old_js_end, new_js_end)

with open("/home/belimed/docupi/templates/dashboard.html", "w") as f:
    f.write(html)

print("OK: dashboard clock added")


# ========== 2. SETTINGS: Add timezone dropdown to time card ==========
with open("/home/belimed/docupi/templates/settings.html", "r") as f:
    shtml = f.read()

# Add timezone selector after the NTP buttons
old_ntp_buttons = """      <div class="d-flex gap-2 mt-2">
        <button class="btn btn-sm btn-outline-success" id="btnNtpOn" onclick="toggleNtp(true)"><i class="bi bi-globe"></i> NTP ein</button>
        <button class="btn btn-sm btn-outline-warning" id="btnNtpOff" onclick="toggleNtp(false)"><i class="bi bi-globe2"></i> NTP aus</button>
      </div>"""

new_ntp_buttons = """      <div class="d-flex gap-2 mt-2">
        <button class="btn btn-sm btn-outline-success" id="btnNtpOn" onclick="toggleNtp(true)"><i class="bi bi-globe"></i> NTP ein</button>
        <button class="btn btn-sm btn-outline-warning" id="btnNtpOff" onclick="toggleNtp(false)"><i class="bi bi-globe2"></i> NTP aus</button>
      </div>
      <hr style="margin:10px 0">
      <div class="d-flex gap-2 align-items-end">
        <div>
          <label class="form-label" style="font-size:.75rem;margin-bottom:2px">Zeitzone</label>
          <select class="form-select form-select-sm" id="timezoneSelect" style="width:220px">
            <option value="Europe/Zurich">Europe/Zurich (CH)</option>
            <option value="Europe/Berlin">Europe/Berlin (DE)</option>
            <option value="Europe/Vienna">Europe/Vienna (AT)</option>
            <option value="Europe/Amsterdam">Europe/Amsterdam (NL)</option>
            <option value="Europe/Paris">Europe/Paris (FR)</option>
            <option value="Europe/London">Europe/London (UK)</option>
            <option value="Europe/Rome">Europe/Rome (IT)</option>
            <option value="Europe/Madrid">Europe/Madrid (ES)</option>
            <option value="Europe/Stockholm">Europe/Stockholm (SE)</option>
            <option value="Europe/Warsaw">Europe/Warsaw (PL)</option>
            <option value="Europe/Prague">Europe/Prague (CZ)</option>
            <option value="Europe/Istanbul">Europe/Istanbul (TR)</option>
            <option value="America/New_York">America/New_York (US East)</option>
            <option value="America/Chicago">America/Chicago (US Central)</option>
            <option value="America/Los_Angeles">America/Los_Angeles (US West)</option>
            <option value="Asia/Tokyo">Asia/Tokyo (JP)</option>
            <option value="Asia/Shanghai">Asia/Shanghai (CN)</option>
            <option value="Asia/Dubai">Asia/Dubai (AE)</option>
          </select>
        </div>
        <button class="btn btn-sm btn-primary" onclick="setTimezone()"><i class="bi bi-check-lg"></i> Setzen</button>
      </div>
      <small class="text-muted" style="font-size:.75rem"><i class="bi bi-info-circle"></i> Sommer-/Winterzeit wird automatisch umgestellt</small>"""

shtml = shtml.replace(old_ntp_buttons, new_ntp_buttons)

# Add timezone select pre-fill in loadTimeInfo and setTimezone function
old_timezone_js = "    document.getElementById('rtcTimezone').textContent = d.timezone || '-';"
new_timezone_js = """    document.getElementById('rtcTimezone').textContent = d.timezone || '-';
    // Pre-select current timezone in dropdown
    var tzSelect = document.getElementById('timezoneSelect');
    if (d.timezone) {
      for (var i = 0; i < tzSelect.options.length; i++) {
        if (tzSelect.options[i].value === d.timezone) {
          tzSelect.selectedIndex = i; break;
        }
      }
    }"""
shtml = shtml.replace(old_timezone_js, new_timezone_js)

# Add setTimezone function before the auto-refresh
old_auto_refresh = "// Auto-refresh system health every 10s"
new_functions = """function setTimezone() {
  var tz = document.getElementById('timezoneSelect').value;
  fetch('/api/system/timezone', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({timezone: tz})
  }).then(function(r){return r.json()}).then(function(d) {
    showToast('Zeitzone', d.message, d.success);
    if (d.success) setTimeout(loadTimeInfo, 1000);
  }).catch(function(e) { showToast('Fehler', e.toString(), false); });
}

// Auto-refresh system health every 10s"""
shtml = shtml.replace(old_auto_refresh, new_functions)

with open("/home/belimed/docupi/templates/settings.html", "w") as f:
    f.write(shtml)

print("OK: settings timezone added")


# ========== 3. APP.PY: Add timezone API endpoint ==========
with open("/home/belimed/docupi/app.py", "r") as f:
    code = f.read()

tz_api = '''
@app.route("/api/system/timezone", methods=["POST"])
def api_set_timezone():
    """Set system timezone."""
    import subprocess
    d = request.get_json()
    tz = d.get("timezone", "") if d else ""
    if not tz:
        return jsonify({"success": False, "message": "Keine Zeitzone angegeben"})
    try:
        r = subprocess.run(["sudo", "/usr/bin/timedatectl", "set-timezone", tz],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            # Also sync to RTC
            subprocess.run(["sudo", "/usr/sbin/hwclock", "-w", "--rtc", "/dev/rtc1"],
                           capture_output=True, timeout=5)
            logger.info(f"Zeitzone gesetzt: {tz}")
            return jsonify({"success": True, "message": f"Zeitzone: {tz}"})
        else:
            return jsonify({"success": False, "message": r.stderr})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

'''

if "/api/system/timezone" not in code:
    marker = '@app.route("/api/system/ntp", methods=["POST"])'
    code = code.replace(marker, tz_api + marker)
    with open("/home/belimed/docupi/app.py", "w") as f:
        f.write(code)
    print("OK: timezone API added")
else:
    print("SKIP: timezone API exists")
