# Plan: Einstellungen komplett — Drucker-APIs, LAN-Config, System-Tab

**Erstellt:** 2026-06-03
**Status:** Implementiert
**Anforderung:** Einstellungsseite vollständig reparieren — fehlende Drucker-APIs ergänzen, LAN-Konfiguration mit statischer IP, System-Status-Tab mit CPU/RAM/Disk/Reboot

---

## Überblick

### Was dieser Plan erreicht

Die Einstellungsseite wird von einer teilweise kaputten Ansicht zu einer vollständigen
Konfigurationsoberfläche. Drucker-Erkennung zeigt den echten CUPS-Drucker, LAN-Einstellungen
erlauben statische IP-Konfiguration, und ein neuer System-Tab zeigt CPU-Temperatur, RAM, Disk,
Uptime und einen Reboot-Button — alles via bereits vorhandener `/api/system/health` API.

### Warum das wichtig ist

Beim Kunden (Tierlabor Uni Essen) muss der Techniker Drucker erkennen, IP konfigurieren und
den System-Status prüfen können — alles ohne SSH. Die aktuelle Seite zeigt "Drucker-API nicht
erreichbar" und hat keine Netzwerk-Konfiguration.

---

## Aktueller Zustand

### Relevante bestehende Struktur

**Vorhandene APIs (alle funktionsfähig):**
- `GET /api/printers` → `{cups_available, printer_count, printers:[{name,info,state,state_text,...}], auto_print, ...}`
- `GET /api/printer/ready` → `{ready, printer, state}`
- `GET /api/print/test` POST → `{success, message, job_id}`
- `POST /api/print/config` → setzt `auto_print`, `default_printer`, `copies`
- `GET /api/network/lan/status` → `{current_ip, current_gateway, current_dns, mode, mac, speed, connected}`
- `POST /api/network/lan/static` → setzt statische IP (body: `{ip, netmask, gateway, dns}`)
- `POST /api/network/lan/dhcp` → wechselt zurück zu DHCP
- `GET /api/system/health` → vollständige Health-Daten (CPU, RAM, Disk, Uptime, Temp, OS)
- `POST /api/system/reboot` → Neustart
- `GET /api/tcp_capture/status` → `{tcp_enabled, running, port, job_count, last_job_ts, ...}`
- `POST /api/tcp_capture/start` / `stop` → TCP-Capture an/aus

**Kaputte / fehlende APIs (aufgerufen in settings.html):**
- `GET /api/printer/status` → 404 (in settings.html aufgerufen)
- `POST /api/printer/detect` → 404
- `POST /api/printer/test` → 404 (Alias für `/api/print/test`)
- `POST /api/printer/auto_print` → 404 (Alias für `/api/print/config`)

**settings.html Bugs:**
- `d.enabled` statt `d.tcp_enabled` → TCP-Toggle zeigt immer false
- `d.enabled` statt `d.tcp_enabled` in loadMonitorStats() → Monitor-Karte falsch
- LAN-Karte: nur Anzeige, kein Formular für statische IP
- Kein System-Tab

### Lücken oder Probleme, die adressiert werden

1. 4 fehlende Printer-API-Endpoints → Drucker-Karte zeigt Fehlermeldung
2. Falsche Feldnamen TCP (`enabled` vs `tcp_enabled`) → Toggle/Badge falsch
3. Keine LAN-Konfiguration → Techniker kann IP nicht umstellen
4. Kein System-Tab → kein CPU-/RAM-/Disk-Überblick, kein Reboot-Button

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

- 4 fehlende Printer-API-Stubs in app.py ergänzen (Thin Wrappers um bestehende Funktionen)
- settings.html: `d.enabled` → `d.tcp_enabled` (2 Stellen), LAN-Karte mit statischer IP erweitern, System-SubTab hinzufügen
- Lokale settings.html ebenfalls synchronisieren

### Neue Dateien erstellen

Keine.

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|---|---|
| Pi: `app.py` | 4 Printer-API-Stubs ergänzen |
| Pi: `templates/settings.html` | Bugs + LAN-Config + System-Tab |
| Lokal: `src/docucontrol/templates/settings.html` | Gleiche Änderungen |

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **Printer-Stubs als Thin-Wrapper**: `GET /api/printer/status` gibt dasselbe zurück wie
   `/api/printers`, aber mit `printer`-Feld auf den ersten Drucker gesetzt — settings.html
   braucht kein Refactoring.

2. **3 Sub-Tabs**: Geräte & Netzwerk / System / Live-Monitor. System bekommt eigenen Tab
   statt in Netzwerk integriert zu sein — übersichtlicher und passt zu Handoff-Pattern.

3. **LAN-Config als Inline-Formular**: Aktuell nur Anzeige der IP. Neues Formular
   (2 Felder: IP/Prefix + Gateway + DNS + Speichern-Button) klappt auf wenn "Statisch"
   ausgewählt wird. DHCP/Statisch via Radio oder Select. Nutzt vorhandene
   `POST /api/network/lan/static` und `/api/network/lan/dhcp` APIs.

4. **System-Tab: Read-only + Reboot**: Zeigt CPU-Temp, Load, RAM-Nutzung, Disk-Nutzung, 
   Uptime, Hostname, OS, Python-Version. Reboot-Button mit Bestätigungs-Dialog.
   Daten von `/api/system/health`. Auto-Refresh alle 10s wenn Tab aktiv.

5. **Kein Hotspot-UI**: WLAN ist hardware-deaktiviert auf DocuControl-Pi — Hotspot-Buttons
   würden nichts tun und verwirren. Nicht einbauen.

### Betrachtete Alternativen

- Settings-JS komplett auf vorhandene API-Namen umschreiben: Mehr JS-Arbeit, gleiches Ergebnis.
  Dünne Wrapper in app.py sind einfacher und reversibel.
- System-Info in Netzwerk-Card einbauen: Zu voll, Tab ist klarer.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: Fehlende Printer-API-Stubs in app.py ergänzen

4 fehlende Endpunkte als Thin-Wrapper um bestehende Funktionen hinzufügen.

**Aktionen:**

Nach der bestehenden `@app.route('/api/printer/ready')` Route einfügen:

```python
@app.route('/api/printer/status')
def api_printer_status():
    status = get_printer_status()          # kommt aus print_manager.get_status()
    printers = status.get('printers', [])
    printer_name = printers[0]['info'] if printers else ''
    return jsonify({
        'printer': printer_name,
        'cups_available': status['cups_available'],
        'printer_count': status['printer_count'],
        'auto_print': status['auto_print'],
        'printers': printers,
    })


@app.route('/api/printer/detect', methods=['POST'])
def api_printer_detect():
    status = get_printer_status()
    printers = status.get('printers', [])
    printer_name = printers[0]['info'] if printers else ''
    return jsonify({
        'success': True,
        'printer': printer_name,
        'count': len(printers),
    })


@app.route('/api/printer/test', methods=['POST'])
def api_printer_test_alias():
    d = request.get_json() or {}
    ok, msg, job_id = printer_test_print(d.get('printer', ''))
    return jsonify({'success': ok, 'message': msg, 'job_id': job_id})


@app.route('/api/printer/auto_print', methods=['POST'])
def api_printer_auto_print():
    d = request.get_json() or {}
    config = load_print_config()
    config['auto_print'] = bool(d.get('enabled', False))
    save_print_config(config)
    return jsonify({'success': True, 'auto_print': config['auto_print']})
```

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/app.py`

---

### Schritt 2: settings.html — Bugs fixen (tcp_enabled, d.enabled)

Zwei Stellen in settings.html: `loadDeviceSettings()` und `loadMonitorStats()`.

**Aktionen:**

In `loadDeviceSettings()`:
```javascript
// Alt:
document.getElementById('tcpToggle').checked = d.enabled || false;
// Neu:
document.getElementById('tcpToggle').checked = d.tcp_enabled || false;
```

In `loadMonitorStats()`:
```javascript
// Alt:
var on = d.enabled;
// Neu:
var on = d.tcp_enabled || d.enabled;
```

**Betroffene Dateien:**
- Pi: `templates/settings.html`
- Lokal: `src/docucontrol/templates/settings.html`

---

### Schritt 3: settings.html — LAN-Karte um statische IP erweitern

Die Netzwerk-Karte bekommt ein ausklappbares Konfigurations-Formular.

**Aktionen:**

Nach der letzten `set-row` in der Netzwerk-Card (nach "Letzter Empfang") einfügen:

```html
<hr style="margin:12px 0;border-color:var(--border)">
<div class="set-row">
    <div class="info">
        <div class="name">IP-Modus</div>
        <div class="desc">DHCP oder statische IP</div>
    </div>
    <select class="ctrl" id="ipMode" onchange="toggleIpForm(this.value)" style="width:120px">
        <option value="dhcp">DHCP</option>
        <option value="static">Statisch</option>
    </select>
</div>
<div id="staticIpForm" style="display:none;margin-top:8px">
    <div class="set-row" style="margin-bottom:6px">
        <div class="info"><div class="name">IP-Adresse / Prefix</div></div>
        <input type="text" class="ctrl" id="cfgIp" placeholder="192.168.0.171/24" style="width:180px">
    </div>
    <div class="set-row" style="margin-bottom:6px">
        <div class="info"><div class="name">Gateway</div></div>
        <input type="text" class="ctrl" id="cfgGw" placeholder="192.168.0.1" style="width:180px">
    </div>
    <div class="set-row" style="margin-bottom:6px">
        <div class="info"><div class="name">DNS</div></div>
        <input type="text" class="ctrl" id="cfgDns" placeholder="192.168.0.1" style="width:180px">
    </div>
    <div style="text-align:right;margin-top:8px">
        <button class="btn btn-primary" onclick="saveStaticIp()">
            <i class="bi bi-save"></i> Speichern &amp; Neu starten
        </button>
    </div>
</div>
```

JS-Funktionen ergänzen:
```javascript
window.toggleIpForm = function(mode) {
    document.getElementById('staticIpForm').style.display = mode === 'static' ? '' : 'none';
};

window.saveStaticIp = function() {
    var ip = document.getElementById('cfgIp').value.trim();
    var gw = document.getElementById('cfgGw').value.trim();
    var dns = document.getElementById('cfgDns').value.trim();
    if (!ip || !gw) { alert('IP und Gateway sind Pflichtfelder'); return; }
    var parts = ip.split('/');
    if (!confirm('IP auf ' + ip + ' setzen? Verbindung trennt kurz.')) return;
    fetch('/api/network/lan/static', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ ip: parts[0], netmask: parts[1] || '24', gateway: gw, dns: dns || gw })
    }).then(function(r) { return r.json(); })
      .then(function(d) { alert(d.message || 'Gespeichert'); })
      .catch(function() { alert('Fehler beim Speichern'); });
};
```

In `loadDeviceSettings()` nach IP-Anzeige ergänzen:
```javascript
// Modus-Select vorwählen
document.getElementById('ipMode').value = d.mode === 'static' ? 'static' : 'dhcp';
if (d.mode === 'static') {
    document.getElementById('staticIpForm').style.display = '';
    document.getElementById('cfgIp').value = d.config_ip + '/' + (d.config_netmask || '24');
    document.getElementById('cfgGw').value = d.config_gateway || '';
    document.getElementById('cfgDns').value = d.config_dns || '';
}
```

**Betroffene Dateien:**
- Pi: `templates/settings.html`
- Lokal: `src/docucontrol/templates/settings.html`

---

### Schritt 4: settings.html — System-Sub-Tab hinzufügen

Dritten Sub-Tab "System" mit Health-Daten und Reboot-Button einfügen.

**Aktionen:**

**Sub-Nav** — dritten Tab ergänzen:
```html
<div class="subtab" id="tabSystem" onclick="switchTab('system')">
    <i class="bi bi-cpu"></i> System
</div>
```

**Panel** — `id="panelSystem"` nach `panelMonitor` einfügen:
```html
<div id="panelSystem" style="display:none">
    <div class="set-grid">

        <!-- System-Status -->
        <div class="card">
            <div class="card-head"><span><i class="bi bi-cpu"></i> System-Status</span></div>
            <div class="card-body">
                <div class="set-row">
                    <div class="info"><div class="name">Hostname</div></div>
                    <span class="mono-ip" id="sysHostname">—</span>
                </div>
                <div class="set-row">
                    <div class="info"><div class="name">CPU-Temperatur</div></div>
                    <span class="value" id="sysCpuTemp">—</span>
                </div>
                <div class="set-row">
                    <div class="info"><div class="name">CPU-Last (1min)</div></div>
                    <span class="value" id="sysCpuLoad">—</span>
                </div>
                <div class="set-row">
                    <div class="info"><div class="name">RAM-Nutzung</div></div>
                    <span class="value" id="sysRam">—</span>
                </div>
                <div class="set-row">
                    <div class="info"><div class="name">Speicherkarte</div></div>
                    <span class="value" id="sysDisk">—</span>
                </div>
                <div class="set-row">
                    <div class="info"><div class="name">Laufzeit</div></div>
                    <span class="value" id="sysUptime">—</span>
                </div>
                <div class="set-row">
                    <div class="info"><div class="name">OS / Kernel</div></div>
                    <span class="value" id="sysOs" style="font-size:12px;color:var(--muted)">—</span>
                </div>
            </div>
        </div>

        <!-- Aktionen -->
        <div class="card">
            <div class="card-head"><span><i class="bi bi-gear-wide-connected"></i> Wartung</span></div>
            <div class="card-body">
                <div class="set-row">
                    <div class="info">
                        <div class="name">System neu starten</div>
                        <div class="desc">Pi sauber herunterfahren und neu starten</div>
                    </div>
                    <button class="btn btn-outline" id="rebootBtn" onclick="rebootSystem()" style="color:var(--danger);border-color:var(--danger)">
                        <i class="bi bi-power"></i> Neustart
                    </button>
                </div>
                <div class="set-row">
                    <div class="info">
                        <div class="name">Protokolle seit Start</div>
                        <div class="desc">Empfangene Chargen gesamt</div>
                    </div>
                    <span class="value" id="sysTotalCount">—</span>
                </div>
                <div class="set-row">
                    <div class="info">
                        <div class="name">Service gestartet</div>
                        <div class="desc">Letzter Service-Start</div>
                    </div>
                    <span class="value" id="sysServiceStart" style="font-size:12px;color:var(--muted)">—</span>
                </div>
            </div>
        </div>

    </div>
</div>
```

**switchTab-Funktion** erweitern: `panelSystem` hide/show, System-Intervall starten/stoppen.

**loadSystemStatus()-Funktion** ergänzen:
```javascript
var systemInterval = null;

function loadSystemStatus() {
    fetch('/api/system/health')
        .then(function(r) { return r.json(); })
        .then(function(d) {
            document.getElementById('sysHostname').textContent = d.os.hostname || '—';
            document.getElementById('sysCpuTemp').textContent = d.cpu.temp + ' °C (' + (d.cpu.temp_status || '') + ')';
            document.getElementById('sysCpuLoad').textContent = d.cpu.load_1.toFixed(2);
            document.getElementById('sysRam').textContent = d.memory.used_mb + ' MB / ' + d.memory.total_mb + ' MB (' + d.memory.percent + '%)';
            document.getElementById('sysDisk').textContent = d.sd_card.used_gb.toFixed(1) + ' GB / ' + d.sd_card.total_gb.toFixed(1) + ' GB (' + d.sd_card.percent + '%)';
            document.getElementById('sysUptime').textContent = d.uptime.text;
            document.getElementById('sysOs').textContent = d.os.distro + ' · Kernel ' + d.os.kernel.split('+')[0];
            document.getElementById('sysTotalCount').textContent = (d.service.today_count || 0) + ' heute, ' + (d.service.total_count || 0) + ' gesamt';
            document.getElementById('sysServiceStart').textContent = d.service.started || '—';
        }).catch(function() {});
}

window.rebootSystem = function() {
    if (!confirm('System wirklich neu starten? Verbindung trennt für ca. 30 Sekunden.')) return;
    var btn = document.getElementById('rebootBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Startet neu …';
    fetch('/api/system/reboot', { method: 'POST' })
        .then(function() {
            setTimeout(function() { window.location.reload(); }, 35000);
        }).catch(function() {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-power"></i> Neustart';
        });
};
```

In `switchTab`:
```javascript
// system
if (tab === 'system') {
    loadSystemStatus();
    if (!systemInterval) systemInterval = setInterval(loadSystemStatus, 10000);
} else {
    if (systemInterval) { clearInterval(systemInterval); systemInterval = null; }
}
```

**Betroffene Dateien:**
- Pi: `templates/settings.html`
- Lokal: `src/docucontrol/templates/settings.html`

---

### Schritt 5: Service neu starten + Validierung

**Aktionen:**

- `sudo systemctl restart docucontrol.service`
- `curl http://localhost:5000/api/printer/status` → `{printer: "DocuPrinter", cups_available: true, ...}`
- `curl http://localhost:5000/api/printer/detect -X POST` → `{success: true, printer: "DocuPrinter"}`
- Browser: Einstellungen → "Erkannter Drucker" zeigt "DocuPrinter" (nicht "Drucker-API nicht erreichbar")
- Browser: Einstellungen → TCP-Toggle steht auf ein (tcp_enabled: true)
- Browser: Einstellungen → System-Tab zeigt CPU-Temp, RAM, Uptime
- Browser: Einstellungen → IP-Adresse zeigt 192.168.0.171

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- `app.py` — neue Stubs importieren bereits `get_printer_status`, `printer_test_print`,
  `load_print_config`, `save_print_config` — alles schon importiert

### Nötige Updates für Konsistenz

- `CLAUDE.md` nach Abschluss aktualisieren

### Auswirkungen auf bestehende Workflows

- Bestehende Routes `/api/printers`, `/api/print/test`, `/api/print/config` bleiben erhalten —
  keine Breaking Changes

---

## Validierungs-Checkliste

- [ ] `GET /api/printer/status` → `{printer: "DocuPrinter", cups_available: true}`
- [ ] `POST /api/printer/detect` → `{success: true, printer: "DocuPrinter"}`
- [ ] `POST /api/printer/test` → `{success: true, job_id: ...}`
- [ ] `POST /api/printer/auto_print` → `{success: true, auto_print: false}`
- [ ] Einstellungen → Drucker: "DocuPrinter" sichtbar (nicht Fehlermeldung)
- [ ] Einstellungen → TCP-Toggle zeigt korrekt "an" (tcp_enabled: true)
- [ ] Einstellungen → IP-Adresse: "192.168.0.171"
- [ ] Einstellungen → System-Tab: CPU-Temp, RAM, Uptime korrekt befüllt
- [ ] Einstellungen → Reboot-Button: Bestätigungsdialog erscheint

---

## Erfolgskriterien

Die Implementierung ist abgeschlossen, wenn:

1. Die Drucker-Karte zeigt "DocuPrinter" ohne Fehlermeldung
2. Der System-Tab zeigt aktuelle Messwerte des Pi (CPU-Temp, RAM, Uptime)
3. Der TCP-Toggle ist korrekt vorbelegt

---

## Notizen

- WLAN-Hardware ist deaktiviert (dtoverlay=disable-wifi) — kein Hotspot-UI einbauen
- `POST /api/network/lan/static` ist bereits implementiert — LAN-Form nutzt direkt
- Reboot: nach Klick 35s warten dann reload — Pi braucht ~25-30s zum Neustart
- System-Tab Auto-Refresh alle 10s (nur wenn Tab aktiv) — keine unnötige Last

---

## Implementierungsnotizen

**Implementiert:** 2026-06-03

### Zusammenfassung

- 4 fehlende Printer-API-Stubs in app.py ergänzt (`/api/printer/status`, `/api/printer/detect`, `/api/printer/test`, `/api/printer/auto_print`)
- settings.html komplett neu: 3 Sub-Tabs (Geräte & Netzwerk / System / Live-Monitor), durchgehend Design-System-Klassen
- Bugs gefixt: `d.enabled` → `d.tcp_enabled`, `d.ip` → `d.current_ip`, `d.capture_count` → `d.captures.length`
- LAN-Karte: IP-Modus-Select + ausklappbares Formular für statische IP + DHCP-Zurück-Button
- System-Tab: CPU-Temp farbkodiert, CPU-Last, RAM, Disk, Uptime, OS, Reboot-Button mit 35s Reload

### Abweichungen vom Plan

1. **`capture_count`**: TCP-Status gibt `captures: [...]` Array zurück → JS nutzt `d.captures.length`
2. **DHCP-Button**: Zusätzlicher "DHCP"-Button neben "Speichern" für einfachen Rückwechsel (nicht im Plan)
3. **CPU-Temp farbkodiert**: >70°C rot, >55°C gelb, sonst grün — sinnvolle Ergänzung

### Aufgetretene Probleme

Keine.
