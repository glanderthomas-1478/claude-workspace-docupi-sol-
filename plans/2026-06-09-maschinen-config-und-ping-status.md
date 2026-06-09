# Plan: Maschinenname + IP konfigurierbar, Machine-Bar-Status per Ping

**Erstellt:** 2026-06-09
**Status:** Implementiert
**Anforderung:** Maschinenname und IP-Adresse der Anlage in Settings editierbar machen; Machine-Bar-Verbindungsstatus auf minütlichen Ping zur konfigurierten IP umstellen.

---

## Überblick

### Was dieser Plan erreicht

In den Einstellungen erscheint eine neue Card "Anlage" (Tab "Geräte & Netzwerk") mit editierbaren Feldern für Maschinenname und IP-Adresse. Der Verbindungsstatus in der Machine-Bar des Dashboards wird statt via TCP-Receiver-Status künftig per ICMP-Ping zur konfigurierten Maschinen-IP ermittelt und alle 60 Sekunden aktualisiert. Maschinenname und -protokoll werden aus der Datenbank-Config gelesen statt hardcodiert.

### Warum das wichtig ist

Der erste Kunden-Pi läuft beim Endkunden (Tierlabor Uni Essen) und muss flexibel auf unterschiedliche Maschinenkonfigurationen angepasst werden können — ohne SSH-Zugang und Code-Änderungen. Der Ping-basierte Status zeigt realen Netzwerkerreichbarkeit der Anlage, nicht nur ob der eigene TCP-Receiver läuft.

---

## Aktueller Zustand

### Relevante bestehende Struktur

- Pi `app.py` Zeilen 7–8: `MACHINE_NAME` und `MACHINE_PROTOCOL` als hardcodierte Modul-Konstanten
- Pi `config.py`: `DEFAULT_CONFIG` mit Sektionen `serial`, `protocol`, `pdf`, `web`, `system` — kein `machine`-Abschnitt
- Pi `app.py` `context_processor` (Zeile 1335–1341): liest `MACHINE_NAME`/`MACHINE_PROTOCOL` aus Konstanten
- `dashboard.html` `updateMachineStatus()` (Zeile 215–233): ruft `GET /api/tcp_capture/status` auf, zeigt "Maschine verbunden" wenn `d.enabled` (= TCP-Receiver läuft)
- Dashboard-Polling-Intervall für Machine-Status: 30 Sekunden (Zeile 506–511)
- `settings.html` Tab "Geräte & Netzwerk": Karten für Drucker, TCP-Empfang, Schnittstelle 1, Schnittstelle 2, Gerätename im Netzwerk, Zeit & Uhr
- Save-Pattern in settings.html: Eingabefeld + Button `btn-outline` mit Icon `bi-check-lg` + Text "Setzen", ruft `fetch(url, {method:'POST', body:JSON.stringify(...)})` auf

### Lücken oder Probleme, die adressiert werden

1. **Maschinenname hardcodiert**: `MACHINE_NAME = "Belimed PST 14-8-12 HS1"` — nicht änderbar ohne Code-Edit + Service-Restart
2. **Keine Maschinen-IP gespeichert**: Ping-Ziel existiert nicht in der Config
3. **Machine-Bar-Status irreführend**: Zeigt `d.enabled` (= TCP-Receiver aktiv), nicht ob die Anlage tatsächlich im Netz erreichbar ist
4. **Polling zu häufig für Ping**: 30s-Interval macht für "minütlichen" Ping keinen Sinn

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

1. `config.py` — neuen Abschnitt `machine` in `DEFAULT_CONFIG` hinzufügen
2. Pi `app.py` — `MACHINE_NAME`/`MACHINE_PROTOCOL` aus Config lesen; neuen Endpunkt `GET /api/machine/ping`; neuen Endpunkt `GET/POST /api/machine/config`
3. `settings.html` — neue Card "Anlage" als erste Card in Tab "Geräte & Netzwerk"
4. `dashboard.html` — `updateMachineStatus()` auf `GET /api/machine/ping` umstellen, Intervall auf 60s

### Neue Dateien erstellen

Keine.

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|---|---|
| `src/docucontrol/templates/settings.html` | Neue Card "Anlage" mit Maschinenname + IP-Eingabe + Ping-Status |
| `src/docucontrol/templates/dashboard.html` | `updateMachineStatus()` auf `/api/machine/ping`, Intervall 60s |
| Pi `/home/docucontrol/docupi/config.py` | `machine`-Sektion in `DEFAULT_CONFIG` |
| Pi `/home/docucontrol/docupi/app.py` | Konstanten → Config-Reads, 2 neue API-Routen |

### Zu löschende Dateien

Keine.

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **Machine-Config in bestehender `config.json`**: Neue Sektion `machine` mit `name`, `ip`, `protocol` — konsistent mit existierendem Config-System. Kein neuer Speicherort, kein neues Format. Atomic-Write bereits implementiert.

2. **Ping via `subprocess` + `ping -c 1 -W 2 <ip>`**: Standard-Systembefehl, kein neuer Dependency. `-c 1` = ein Paket, `-W 2` = 2s Timeout. Latenz aus Ausgabe parsbar. Fallback: bei leerem IP-Feld → `{reachable: false, configured: false}`.

3. **Eigener Endpunkt `GET /api/machine/ping`** (kein Caching im Backend): Frontend ruft den Endpunkt alle 60s auf, Backend führt Ping live aus. Einfacher als Backend-seitiger Timer. Ping dauert max. 2s — kein Problem da nicht im Request-Critical-Path.

4. **`GET/POST /api/machine/config`**: Lesen und Schreiben von `name`, `ip`, `protocol` als JSON. POST triggert auch `context_processor`-Update (Module-Level Variable wird neu gelesen).

5. **Save-Pattern "Setzen"-Button**: Konsistent mit `saveHostname()` und `saveNtp()` — kein Auto-Save auf blur, expliziter Button. Verhindert ungewolltes Speichern beim Tippen.

6. **Ping-Status in Settings**: Separate Row "Verbindungstest" in der Anlage-Card zeigt letzten Ping-Ergebnis mit Timestamp. Kein automatisches Polling in Settings — nur einmaliger Ping auf Button-Klick ("Jetzt testen").

7. **Maschinenprotokoll nicht in Settings**: Das `protocol`-Feld (`"6050 / 6060 FIS"`) bleibt im Config-System, wird aber nicht in der Settings-UI exponiert — zu technisch für den Endnutzer. Nur `name` und `ip` sind editierbar.

8. **`context_processor` liest Config live**: `MACHINE_NAME` wird aus `app.py` entfernt, `context_processor` ruft `load_config()["machine"]["name"]` auf — damit Änderungen ohne Service-Restart im nächsten Page-Load sichtbar sind.

### Betrachtete Alternativen

- **WebSocket für Live-Ping**: Zu komplex für den Anwendungsfall. Ein 60s-Polling-Fetch genügt.
- **Backend-seitiger Ping-Timer**: Würde Background-Thread + Shared State erfordern. Frontend-Poll ist einfacher.
- **TCP-Port-Check statt ICMP-Ping**: Port 9100 prüfen würde zeigen ob Drucker-Interface aktiv ist. Aber ICMP-Ping ist generischer und funktioniert unabhängig von Port-Firewalls.
- **Auto-Save auf blur**: Führt zu versehentlichen Schreibvorgängen beim Tab-Wechsel. "Setzen"-Button ist stabiler.

### Offene Fragen

Keine — alle Entscheidungen eindeutig.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: Pi `config.py` — `machine`-Sektion hinzufügen

In `DEFAULT_CONFIG` eine neue Sektion `machine` mit den drei Feldern einfügen. Bestehendes Merge-Schema von `load_config()` greift automatisch.

**Aktionen:**

- Auf Pi: nach der `"system"`-Sektion in `DEFAULT_CONFIG` einfügen:
  ```python
  "machine": {
      "name": "Belimed PST 14-8-12 HS1",
      "ip": "",
      "protocol": "6050 / 6060 FIS"
  }
  ```
- In `load_config()` prüfen ob das bestehende Merge-Schema (`for section in DEFAULT_CONFIG`) die neue Sektion automatisch abdeckt — es tut es, da es über `DEFAULT_CONFIG.keys()` iteriert.

**Betroffene Dateien:**

- Pi `/home/docucontrol/docupi/config.py`

---

### Schritt 2: Pi `app.py` — Konstanten ersetzen + 2 neue Routen

Drei Änderungen in `app.py`:

**2a — Konstanten entfernen, context_processor auf Config umstellen:**

```python
# ALT (Zeilen 7–8 entfernen):
MACHINE_NAME = "Belimed PST 14-8-12 HS1"
MACHINE_PROTOCOL = "6050 / 6060 FIS"

# context_processor (Zeile ~1339) — ALT:
return {'tcp_connected': ..., 'machine_name': MACHINE_NAME, 'machine_protocol': MACHINE_PROTOCOL}

# context_processor NEU:
cfg = load_config().get('machine', {})
return {
    'tcp_connected': bool(status.get('enabled', False)),
    'machine_name': cfg.get('name', 'Anlage'),
    'machine_protocol': cfg.get('protocol', '')
}
```

**2b — Neuer Endpunkt `GET /api/machine/ping`:**

```python
@app.route('/api/machine/ping')
def api_machine_ping():
    cfg = load_config().get('machine', {})
    ip = cfg.get('ip', '').strip()
    if not ip:
        return jsonify({'reachable': False, 'configured': False, 'ip': '', 'latency_ms': None})
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', '2', ip],
            capture_output=True, text=True, timeout=5
        )
        reachable = result.returncode == 0
        latency = None
        if reachable:
            import re
            m = re.search(r'time=(\d+\.?\d*)', result.stdout)
            if m:
                latency = float(m.group(1))
        return jsonify({'reachable': reachable, 'configured': True, 'ip': ip, 'latency_ms': latency})
    except Exception as e:
        return jsonify({'reachable': False, 'configured': True, 'ip': ip, 'latency_ms': None, 'error': str(e)})
```

**2c — Neuer Endpunkt `GET/POST /api/machine/config`:**

```python
@app.route('/api/machine/config', methods=['GET', 'POST'])
def api_machine_config():
    if request.method == 'GET':
        cfg = load_config().get('machine', {})
        return jsonify({
            'name': cfg.get('name', ''),
            'ip': cfg.get('ip', ''),
            'protocol': cfg.get('protocol', '')
        })
    d = request.get_json(silent=True) or {}
    config = load_config()
    if 'machine' not in config:
        config['machine'] = {}
    if 'name' in d:
        config['machine']['name'] = d['name'].strip()
    if 'ip' in d:
        config['machine']['ip'] = d['ip'].strip()
    save_config(config)
    return jsonify({'success': True})
```

**Betroffene Dateien:**

- Pi `/home/docucontrol/docupi/app.py`

---

### Schritt 3: `settings.html` — neue Card "Anlage"

Neue Card als **erste Card** im Tab "Geräte & Netzwerk" (vor der Drucker-Card, Zeile 27).

**HTML — neue Card einfügen:**

```html
<!-- Anlage -->
<div class="card">
    <div class="card-head"><span><i class="bi bi-safe2"></i> Anlage</span></div>
    <div class="card-body">
        <div class="set-row">
            <div class="info">
                <div class="name">Maschinenname</div>
                <div class="desc">Angezeigter Name im Dashboard</div>
            </div>
            <div style="display:flex;gap:6px;align-items:center">
                <input type="text" class="ctrl" id="machineNameInput" placeholder="z.B. Belimed PST 14-8-12 HS1" style="width:220px" maxlength="64">
                <button class="btn btn-outline" onclick="saveMachineConfig()"><i class="bi bi-check-lg"></i> Setzen</button>
            </div>
        </div>
        <div class="set-row">
            <div class="info">
                <div class="name">IP-Adresse</div>
                <div class="desc">IP der Anlage für Ping-Test</div>
            </div>
            <div style="display:flex;gap:6px;align-items:center">
                <input type="text" class="ctrl mono-ip" id="machineIpInput" placeholder="192.168.0.x" style="width:140px" maxlength="15">
                <button class="btn btn-outline" onclick="saveMachineConfig()"><i class="bi bi-check-lg"></i> Setzen</button>
            </div>
        </div>
        <div class="set-row">
            <div class="info">
                <div class="name">Verbindungstest</div>
                <div class="desc">Ping zur konfigurierten IP</div>
            </div>
            <div style="display:flex;gap:8px;align-items:center">
                <span class="value" id="machinePingResult" style="font-size:12.5px;color:var(--muted)">—</span>
                <button class="btn btn-outline" onclick="testMachinePing()"><i class="bi bi-wifi"></i> Ping</button>
            </div>
        </div>
    </div>
</div>
```

**JS — Funktionen hinzufügen** (im `<script>`-Block, in der Sektion `// ── Tab: Geräte & Netzwerk`):

```javascript
// Maschinenconfig laden
function loadMachineConfig() {
    fetch('/api/machine/config')
        .then(function(r) { return r.json(); })
        .then(function(d) {
            document.getElementById('machineNameInput').value = d.name || '';
            document.getElementById('machineIpInput').value = d.ip || '';
        }).catch(function() {});
}

// Maschinenconfig speichern
window.saveMachineConfig = function() {
    var name = document.getElementById('machineNameInput').value.trim();
    var ip   = document.getElementById('machineIpInput').value.trim();
    fetch('/api/machine/config', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: name, ip: ip})
    }).then(function(r) { return r.json(); })
      .then(function(d) {
          if (d.success) showToast('Gespeichert', 'Anlage-Konfiguration aktualisiert.');
      }).catch(function() {});
};

// Ping-Test manuell
window.testMachinePing = function() {
    var el = document.getElementById('machinePingResult');
    el.textContent = 'Prüfen …';
    el.style.color = 'var(--muted)';
    fetch('/api/machine/ping')
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (!d.configured) {
                el.textContent = 'IP nicht konfiguriert';
                el.style.color = 'var(--muted)';
            } else if (d.reachable) {
                var lat = d.latency_ms ? ' (' + d.latency_ms.toFixed(1) + ' ms)' : '';
                el.textContent = 'Erreichbar' + lat;
                el.style.color = 'var(--success, #2fce7f)';
            } else {
                el.textContent = 'Nicht erreichbar (' + (d.ip || '—') + ')';
                el.style.color = 'var(--danger)';
            }
        }).catch(function() {
            el.textContent = 'Fehler';
            el.style.color = 'var(--danger)';
        });
};
```

**JS — `loadMachineConfig()` in `loadDeviceSettings()` aufrufen:**

In `loadDeviceSettings()` am Anfang ergänzen:
```javascript
loadMachineConfig();
```

**Betroffene Dateien:**

- `src/docucontrol/templates/settings.html`

---

### Schritt 4: `dashboard.html` — `updateMachineStatus()` auf Ping umstellen

**Änderung in `updateMachineStatus()`:**

```javascript
// ALT:
function updateMachineStatus() {
    fetch('/api/tcp_capture/status')
        .then(function(r) { return r.json(); })
        .then(function(d) {
            var el   = document.getElementById('machineStatus');
            var txt  = document.getElementById('machineStatusText');
            var icon = document.getElementById('machineStatusIcon');
            if (d.enabled) {
                el.className = 'mb-status';
                txt.textContent = 'Maschine verbunden';
                icon.className = 'bi bi-hdd-network-fill';
            } else {
                el.className = 'mb-status offline';
                txt.textContent = 'Keine Verbindung';
                icon.className = 'bi bi-hdd-network';
            }
        })
        .catch(function() {});
}

// NEU:
function updateMachineStatus() {
    fetch('/api/machine/ping')
        .then(function(r) { return r.json(); })
        .then(function(d) {
            var el   = document.getElementById('machineStatus');
            var txt  = document.getElementById('machineStatusText');
            var icon = document.getElementById('machineStatusIcon');
            if (!d.configured) {
                el.className = 'mb-status offline';
                txt.textContent = 'IP nicht konfiguriert';
                icon.className = 'bi bi-hdd-network';
            } else if (d.reachable) {
                el.className = 'mb-status';
                txt.textContent = 'Erreichbar';
                icon.className = 'bi bi-hdd-network-fill';
            } else {
                el.className = 'mb-status offline';
                txt.textContent = 'Keine Verbindung';
                icon.className = 'bi bi-hdd-network';
            }
        })
        .catch(function() {});
}
```

**Polling-Intervall auf 60s ändern:**

```javascript
// ALT:
}, 30000);

// NEU (nur für machine-status-Intervall):
}, 60000);
```

Achtung: Das 30s-Intervall im Dashboard-Block lädt mehrere Dinge (stats, protocols, machine-status). Prüfen ob der Block nur `updateMachineStatus()` enthält oder auch andere Calls — falls gemischt, nur `updateMachineStatus()` in ein eigenes separates 60s-Intervall auslagern.

**Betroffene Dateien:**

- `src/docucontrol/templates/dashboard.html`

---

### Schritt 5: Deployment auf Pi

Alle geänderten Dateien deployen und Service neu starten.

**Aktionen:**

- `scp config.py` → Pi (falls lokale Kopie existiert; sonst direkt auf Pi bearbeiten)
- `scp settings.html` → Pi `/home/docucontrol/docupi/templates/settings.html`
- `scp dashboard.html` → Pi `/home/docucontrol/docupi/templates/dashboard.html`
- Pi `app.py` direkt per Python-Patch-Skript anpassen (wie bisher)
- Pi `config.py` direkt per SSH bearbeiten
- `sudo systemctl restart docucontrol` + `is-active` prüfen

**Betroffene Dateien:**

- Pi: `app.py`, `config.py`, `templates/settings.html`, `templates/dashboard.html`

---

### Schritt 6: Validierung

**Aktionen:**

- `curl http://192.168.0.171/api/machine/config` → `{"name": "Belimed PST 14-8-12 HS1", "ip": "", "protocol": "6050 / 6060 FIS"}`
- IP setzen: `curl -X POST http://192.168.0.171/api/machine/config -H 'Content-Type: application/json' -d '{"ip":"192.168.0.50"}'` (Beispiel-IP)
- `curl http://192.168.0.171/api/machine/ping` → `{"reachable": false/true, "configured": true, "ip": "192.168.0.50", ...}`
- Settings aufrufen: `http://192.168.0.171/settings` → Tab "Geräte & Netzwerk" → Card "Anlage" sichtbar, Felder befüllt
- Maschinenname ändern, "Setzen" klicken → Dashboard neu laden → Machine-Bar zeigt neuen Namen
- Dashboard: Machine-Bar-Status nach ~5s "IP nicht konfiguriert" (bei leerer IP) oder Ping-Ergebnis

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- `dashboard.html` — `{{ machine_name }}` via Jinja-Template aus `context_processor`
- `app.py` `context_processor` — liest künftig `load_config()["machine"]["name"]`
- `settings.html` — neue Anlage-Card

### Nötige Updates für Konsistenz

- `CLAUDE.md` — neue API-Endpunkte dokumentieren, hardcodierte Konstanten-Notiz entfernen
- `context/current-data.md` — Maschinenname-Quelle aktualisieren
- `memory/machine-identity.md` — ggf. aktualisieren (war bisher "Belimed PST 14-8-12 HS1 hardcodiert")

### Auswirkungen auf bestehende Workflows

- Dashboard: Machine-Bar-Name kommt jetzt aus Config (Page-Reload nötig nach Settings-Änderung) — kein sofortiger Live-Update ohne Reload (akzeptabel)
- TCP-Capture läuft weiterhin unabhängig — Ping-Status ≠ TCP-Status (TCP-Status im Settings-Tab "Geräte & Netzwerk" bleibt erhalten via separater Capture-Statistik-Card)

---

## Validierungs-Checkliste

- [ ] `GET /api/machine/config` gibt `name`, `ip`, `protocol` zurück
- [ ] `POST /api/machine/config` schreibt in `config.json` unter `machine`-Sektion
- [ ] `GET /api/machine/ping` gibt `{reachable, configured, ip, latency_ms}` zurück
- [ ] Settings Card "Anlage" erscheint als erste Card in Tab "Geräte & Netzwerk"
- [ ] Maschinenname und IP laden korrekt in die Eingabefelder
- [ ] "Setzen"-Button speichert beide Felder in einem API-Call
- [ ] "Ping"-Button zeigt Ergebnis mit Latenz oder Fehlermeldung
- [ ] Dashboard Machine-Bar-Name wird aus Config gelesen (nach Reload)
- [ ] Machine-Bar-Status zeigt Ping-Ergebnis statt TCP-Status
- [ ] Bei leerer IP: "IP nicht konfiguriert" im Dashboard
- [ ] Polling-Intervall für Machine-Status: 60s
- [ ] Service-Restart sauber, `systemctl is-active` = active
- [ ] CLAUDE.md aktualisiert

---

## Erfolgskriterien

1. In Settings kann Maschinenname und IP editiert und gespeichert werden — ohne SSH-Zugang
2. Dashboard Machine-Bar zeigt "Erreichbar" wenn Ping zur konfigurierten IP erfolgreich (≤2s)
3. Dashboard Machine-Bar zeigt "Keine Verbindung" wenn kein Ping-Response — unabhängig vom TCP-Receiver-Status

---

---

## Implementierungsnotizen

**Implementiert:** 2026-06-09

### Zusammenfassung

Pi `config.py` um `machine`-Sektion ergänzt. `app.py`: `MACHINE_NAME`/`MACHINE_PROTOCOL`-Konstanten entfernt, `context_processor` liest aus Config, zwei neue Routen (`/api/machine/config`, `/api/machine/ping`) eingefügt. `settings.html`: Anlage-Card mit Maschinenname/IP-Input + Ping-Button als erste Card im Tab. `dashboard.html`: `updateMachineStatus()` auf `/api/machine/ping` umgestellt, eigenes 60s-Intervall. Alles deployed und validiert.

### Abweichungen vom Plan

- **`updateMachineStatus()` aus dem 30s-Block herausgelöst**: Plan sagte "prüfen ob gemischt" — es war gemischt. `updateMachineStatus()` läuft jetzt in einem eigenen `setInterval(updateMachineStatus, 60000)`, die anderen Calls bleiben bei 30s.
- **IP nach Test zurückgesetzt**: Während Validierung testweise auf `192.168.0.171` gesetzt, danach wieder auf leer gesetzt (echte Tierlabor-IP wird vor Ort eingetragen).

### Aufgetretene Probleme

Keine.

---

## Notizen

- **Ping erfordert keine Root-Rechte** auf Linux für ICMP (raw socket) wenn `ping` binary setuid-bit hat — Standard auf Debian. Kein `sudoers`-Eintrag nötig.
- **IP-Validierung**: Kein Frontend-Regex nötig — bei ungültiger IP schlägt `ping` einfach fehl und der Backend-Endpunkt gibt `reachable: false` zurück.
- **Maschinenname im Dashboard ohne Reload**: Falls Live-Update gewünscht, könnte Dashboard `GET /api/machine/config` beim Laden aufrufen und `mb-name` setzen — optional, für später.
- **Zukünftig**: Machine-Bar könnte auch Latenz-Wert anzeigen (z.B. "Erreichbar · 1.2 ms") — triviale Ergänzung.
- **30s-Intervall im Dashboard**: Das bestehende `setInterval`-Block auf Zeile 506–511 lädt `updateMachineStatus()` zusammen mit anderen Calls. Beim Refactoring prüfen ob alle in einem Block sind — ggf. `updateMachineStatus()` in eigenen 60s-Block auslagern.
