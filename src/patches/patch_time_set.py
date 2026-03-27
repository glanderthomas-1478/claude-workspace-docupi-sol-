#!/usr/bin/env python3
"""Add manual time setting API + UI to DocuPi"""

# ========== 1. Add API endpoint to app.py ==========
with open("/home/belimed/docupi/app.py", "r") as f:
    code = f.read()

time_api = '''
@app.route("/api/system/time", methods=["GET"])
def api_get_time():
    """Get current system and RTC time."""
    import subprocess
    data = {"system_time": "", "rtc_time": "", "ntp_active": False, "timezone": ""}
    try:
        r = subprocess.run(["timedatectl", "show", "--no-pager"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            if line.startswith("Timezone="):
                data["timezone"] = line.split("=", 1)[1]
            elif line.startswith("NTP="):
                data["ntp_active"] = line.split("=")[1].strip().lower() == "yes"
            elif line.startswith("NTPSynchronized="):
                data["ntp_synced"] = line.split("=")[1].strip().lower() == "yes"
    except:
        pass
    from datetime import datetime
    data["system_time"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    data["system_time_display"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    # RTC time
    try:
        r = subprocess.run(["sudo", "/usr/sbin/hwclock", "-r", "--rtc", "/dev/rtc1"],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            data["rtc_time"] = r.stdout.strip()
            data["rtc_available"] = True
        else:
            data["rtc_available"] = False
    except:
        data["rtc_available"] = False
    return jsonify(data)


@app.route("/api/system/time", methods=["POST"])
def api_set_time():
    """Set system time manually and sync to RTC."""
    import subprocess
    d = request.get_json()
    if not d or "datetime" not in d:
        return jsonify({"success": False, "message": "Kein Datum/Zeit angegeben"})

    dt_str = d["datetime"]  # Expected: "2026-03-18T14:30:00"

    try:
        # Disable NTP first so manual time sticks
        subprocess.run(["sudo", "/usr/bin/timedatectl", "set-ntp", "false"],
                       capture_output=True, timeout=5)

        # Set system time
        r = subprocess.run(["sudo", "/usr/bin/date", "-s", dt_str],
                           capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return jsonify({"success": False, "message": f"date -s fehlgeschlagen: {r.stderr}"})

        # Sync to hardware RTC (DS3231)
        rtc_msg = ""
        try:
            r2 = subprocess.run(["sudo", "/usr/sbin/hwclock", "-w", "--rtc", "/dev/rtc1"],
                                capture_output=True, text=True, timeout=5)
            if r2.returncode == 0:
                rtc_msg = " und in RTC gespeichert"
            else:
                rtc_msg = " (RTC-Sync fehlgeschlagen)"
        except:
            rtc_msg = " (keine RTC verfuegbar)"

        from datetime import datetime
        now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        logger.info(f"Uhrzeit manuell gesetzt: {now}")
        log_event("INFO", f"Uhrzeit manuell gesetzt: {now}")

        return jsonify({
            "success": True,
            "message": f"Uhrzeit gesetzt: {now}{rtc_msg}",
            "current_time": now
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Fehler: {e}"})


@app.route("/api/system/ntp", methods=["POST"])
def api_toggle_ntp():
    """Enable or disable NTP."""
    import subprocess
    d = request.get_json()
    enable = d.get("enable", True) if d else True
    try:
        r = subprocess.run(
            ["sudo", "/usr/bin/timedatectl", "set-ntp", "true" if enable else "false"],
            capture_output=True, text=True, timeout=5
        )
        state = "aktiviert" if enable else "deaktiviert"
        if r.returncode == 0:
            return jsonify({"success": True, "message": f"NTP {state}"})
        else:
            return jsonify({"success": False, "message": r.stderr})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

'''

# Insert before the watchdog API
marker = '@app.route("/api/watchdog/status")'
if "/api/system/time" not in code:
    code = code.replace(marker, time_api + marker)
    with open("/home/belimed/docupi/app.py", "w") as f:
        f.write(code)
    print("OK: time API added to app.py")
else:
    print("SKIP: time API already exists")


# ========== 2. Add sudoers for timedatectl, date, hwclock ==========
import subprocess
sudoers_line = "belimed ALL=(ALL) NOPASSWD: /usr/bin/timedatectl, /usr/bin/date, /usr/sbin/hwclock"
try:
    with open("/etc/sudoers.d/docupi-network", "r") as f:
        existing = f.read()
    if "timedatectl" not in existing:
        with open("/etc/sudoers.d/docupi-network", "a") as f:
            f.write("\n" + sudoers_line + "\n")
        print("OK: sudoers updated")
    else:
        print("SKIP: sudoers already has timedatectl")
except PermissionError:
    # Write via sudo
    import os
    os.system(f'echo "{sudoers_line}" | sudo tee -a /etc/sudoers.d/docupi-network > /dev/null')
    print("OK: sudoers updated via sudo")


# ========== 3. Update settings.html - replace RTC card with time-setting card ==========
with open("/home/belimed/docupi/templates/settings.html", "r") as f:
    html = f.read()

# Replace the basic RTC card with a full time-management card
old_rtc = '''<!-- RTC -->
  <div class="col-md-6">
    <div class="health-card">
      <h6><i class="bi bi-clock"></i> Echtzeituhr (DS3231)</h6>
      <div class="info-row"><span class="label">Hardware RTC</span><span class="value" id="rtcStatus">--</span></div>
      <div class="info-row"><span class="label">RTC Zeit</span><span class="value" id="rtcTime">--</span></div>
      <div class="info-row"><span class="label">Batterie</span><span class="value" id="rtcBattery">--</span></div>
      <div class="info-row"><span class="label">NTP Sync</span><span class="value" id="rtcNtp">--</span></div>
    </div>
  </div>'''

new_rtc = '''<!-- Uhrzeit & RTC -->
  <div class="col-md-6">
    <div class="health-card">
      <h6><i class="bi bi-clock"></i> Uhrzeit &amp; Echtzeituhr</h6>
      <div class="info-row"><span class="label">Systemzeit</span><span class="value" id="sysTimeDisplay">--</span></div>
      <div class="info-row"><span class="label">RTC (DS3231)</span><span class="value" id="rtcTime">--</span></div>
      <div class="info-row"><span class="label">NTP</span><span class="value" id="rtcNtp">--</span></div>
      <div class="info-row"><span class="label">Zeitzone</span><span class="value" id="rtcTimezone">--</span></div>
      <hr style="margin:10px 0">
      <p class="text-muted" style="font-size:.8rem;margin-bottom:8px"><i class="bi bi-pencil-square"></i> Uhrzeit manuell einstellen (fuer Offline-Betrieb)</p>
      <div class="d-flex gap-2 align-items-end flex-wrap">
        <div>
          <label class="form-label" style="font-size:.75rem;margin-bottom:2px">Datum &amp; Uhrzeit</label>
          <input type="datetime-local" class="form-control form-control-sm" id="manualDateTime" style="width:220px">
        </div>
        <button class="btn btn-sm btn-primary" onclick="setManualTime()"><i class="bi bi-check-lg"></i> Setzen</button>
        <button class="btn btn-sm btn-outline-secondary" onclick="setTimeFromBrowser()"><i class="bi bi-laptop"></i> Browser-Zeit</button>
      </div>
      <div class="d-flex gap-2 mt-2">
        <button class="btn btn-sm btn-outline-success" id="btnNtpOn" onclick="toggleNtp(true)"><i class="bi bi-globe"></i> NTP ein</button>
        <button class="btn btn-sm btn-outline-warning" id="btnNtpOff" onclick="toggleNtp(false)"><i class="bi bi-globe2"></i> NTP aus</button>
      </div>
    </div>
  </div>'''

html = html.replace(old_rtc, new_rtc)

# Replace old JS RTC section with new time-management JS
old_rtc_js = """    // RTC
    document.getElementById('rtcStatus').innerHTML = '<span class="text-success"><i class="bi bi-check-circle-fill"></i> DS3231 aktiv</span>';
    document.getElementById('rtcTime').textContent = new Date().toLocaleString('de-DE');
    document.getElementById('rtcBattery').innerHTML = '<span class="text-warning"><i class="bi bi-exclamation-triangle"></i> Nicht eingesetzt</span>';
    document.getElementById('rtcNtp').innerHTML = '<span class="text-success">Synchronisiert</span>';"""

new_rtc_js = """    // Time & RTC - loaded separately
    loadTimeInfo();"""

html = html.replace(old_rtc_js, new_rtc_js)

# Add the time management JS functions before the auto-refresh interval
old_interval = "// Auto-refresh system health every 10s"
time_js = """
// --- Time Management ---
function loadTimeInfo() {
  fetch('/api/system/time').then(function(r){return r.json()}).then(function(d) {
    document.getElementById('sysTimeDisplay').innerHTML = '<strong>' + d.system_time_display + '</strong>';
    if (d.rtc_available) {
      document.getElementById('rtcTime').innerHTML = '<span class="text-success"><i class="bi bi-check-circle-fill"></i></span> ' + d.rtc_time;
    } else {
      document.getElementById('rtcTime').innerHTML = '<span class="text-muted">Nicht verfuegbar</span>';
    }
    if (d.ntp_active) {
      document.getElementById('rtcNtp').innerHTML = d.ntp_synced
        ? '<span class="badge bg-success">Aktiv &amp; synchronisiert</span>'
        : '<span class="badge bg-warning">Aktiv, nicht synchronisiert</span>';
      document.getElementById('btnNtpOn').disabled = true;
      document.getElementById('btnNtpOff').disabled = false;
    } else {
      document.getElementById('rtcNtp').innerHTML = '<span class="badge bg-secondary">Deaktiviert (Offline-Modus)</span>';
      document.getElementById('btnNtpOn').disabled = false;
      document.getElementById('btnNtpOff').disabled = true;
    }
    document.getElementById('rtcTimezone').textContent = d.timezone || '-';
    // Pre-fill the datetime input with current time
    if (d.system_time) {
      document.getElementById('manualDateTime').value = d.system_time.substring(0, 16);
    }
  }).catch(function(){});
}

function setManualTime() {
  var dt = document.getElementById('manualDateTime').value;
  if (!dt) { showToast('Zeit', 'Bitte Datum und Uhrzeit eingeben', false); return; }
  fetch('/api/system/time', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({datetime: dt + ':00'})
  }).then(function(r){return r.json()}).then(function(d) {
    showToast('Uhrzeit', d.message, d.success);
    if (d.success) { setTimeout(loadTimeInfo, 1000); loadSystemHealth(); }
  }).catch(function(e) { showToast('Fehler', e.toString(), false); });
}

function setTimeFromBrowser() {
  var now = new Date();
  var pad = function(n) { return n < 10 ? '0' + n : '' + n; };
  var dt = now.getFullYear() + '-' + pad(now.getMonth()+1) + '-' + pad(now.getDate()) +
           'T' + pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds());
  document.getElementById('manualDateTime').value = dt.substring(0, 16);
  fetch('/api/system/time', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({datetime: dt})
  }).then(function(r){return r.json()}).then(function(d) {
    showToast('Uhrzeit', d.message, d.success);
    if (d.success) { setTimeout(loadTimeInfo, 1000); loadSystemHealth(); }
  }).catch(function(e) { showToast('Fehler', e.toString(), false); });
}

function toggleNtp(enable) {
  fetch('/api/system/ntp', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({enable: enable})
  }).then(function(r){return r.json()}).then(function(d) {
    showToast('NTP', d.message, d.success);
    if (d.success) setTimeout(loadTimeInfo, 1500);
  }).catch(function(e) { showToast('Fehler', e.toString(), false); });
}

""" + old_interval

html = html.replace(old_interval, time_js)

with open("/home/belimed/docupi/templates/settings.html", "w") as f:
    f.write(html)

print("OK: settings.html updated with time UI")
