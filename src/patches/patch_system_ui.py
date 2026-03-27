#!/usr/bin/env python3
"""Add RTC + Watchdog cards to System tab in settings.html"""

with open("/home/belimed/docupi/templates/settings.html", "r") as f:
    html = f.read()

# Add RTC + Watchdog cards before the Actions card
old_actions = '''<!-- Actions -->
  <div class="col-md-6">
    <div class="health-card">
      <h6><i class="bi bi-tools"></i> Wartung</h6>'''

rtc_wd_cards = '''<!-- RTC -->
  <div class="col-md-6">
    <div class="health-card">
      <h6><i class="bi bi-clock"></i> Echtzeituhr (DS3231)</h6>
      <div class="info-row"><span class="label">Hardware RTC</span><span class="value" id="rtcStatus">--</span></div>
      <div class="info-row"><span class="label">RTC Zeit</span><span class="value" id="rtcTime">--</span></div>
      <div class="info-row"><span class="label">Batterie</span><span class="value" id="rtcBattery">--</span></div>
      <div class="info-row"><span class="label">NTP Sync</span><span class="value" id="rtcNtp">--</span></div>
    </div>
  </div>

  <!-- Watchdog -->
  <div class="col-md-6">
    <div class="health-card">
      <h6><i class="bi bi-shield-check"></i> Hardware-Watchdog</h6>
      <div class="info-row"><span class="label">HAT erkannt</span><span class="value" id="wdAvailable">--</span></div>
      <div class="info-row"><span class="label">Status</span><span class="value" id="wdEnabled">--</span></div>
      <div class="info-row"><span class="label">Firmware</span><span class="value" id="wdFirmware">--</span></div>
      <div class="info-row"><span class="label">Timeout</span><span class="value" id="wdTimeout">--</span></div>
      <div class="info-row"><span class="label">Verbleibend</span><span class="value" id="wdRemaining">--</span></div>
      <div class="info-row"><span class="label">Feed-Intervall</span><span class="value" id="wdFeed">--</span></div>
    </div>
  </div>

  <!-- Actions -->
  <div class="col-md-6">
    <div class="health-card">
      <h6><i class="bi bi-tools"></i> Wartung</h6>'''

html = html.replace(old_actions, rtc_wd_cards)

# Add JS to populate RTC + Watchdog in loadSystemHealth
old_os = "    // OS"
new_js = """    // Watchdog
    if (d.watchdog) {
      document.getElementById('wdAvailable').innerHTML = d.watchdog.available
        ? '<span class="text-success"><i class="bi bi-check-circle-fill"></i> Ja</span>'
        : '<span class="text-muted">Nicht erkannt</span>';
      document.getElementById('wdEnabled').innerHTML = d.watchdog.enabled
        ? '<span class="badge bg-success">Aktiv</span>'
        : '<span class="badge bg-secondary">Inaktiv</span>';
      document.getElementById('wdFirmware').textContent = d.watchdog.fw_version ? 'v' + d.watchdog.fw_version : '-';
      document.getElementById('wdTimeout').textContent = d.watchdog.timeout ? d.watchdog.timeout + 's' : '-';
      document.getElementById('wdRemaining').textContent = d.watchdog.remaining >= 0 ? d.watchdog.remaining + 's' : '-';
      document.getElementById('wdFeed').textContent = d.watchdog.feed_interval ? 'alle ' + d.watchdog.feed_interval + 's' : '-';
    }

    // RTC
    document.getElementById('rtcStatus').innerHTML = '<span class="text-success"><i class="bi bi-check-circle-fill"></i> DS3231 aktiv</span>';
    document.getElementById('rtcTime').textContent = new Date().toLocaleString('de-DE');
    document.getElementById('rtcBattery').innerHTML = '<span class="text-warning"><i class="bi bi-exclamation-triangle"></i> Nicht eingesetzt</span>';
    document.getElementById('rtcNtp').innerHTML = '<span class="text-success">Synchronisiert</span>';

    // OS"""

html = html.replace(old_os, new_js)

with open("/home/belimed/docupi/templates/settings.html", "w") as f:
    f.write(html)

print("OK: RTC + Watchdog UI added")
