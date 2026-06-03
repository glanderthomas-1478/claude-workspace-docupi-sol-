# Plan: DocuControl Dashboard-Umbau & USB-Druck-Integration

**Erstellt:** 2026-06-02
**Status:** Implementiert
**Anforderung:** Dashboard auf Chargen-Fokus umbauen, Live-Monitor auslagern, TCP-Capture umschalten und USB-Druck als einzigen Ausgabeweg etablieren

---

## Überblick

### Was dieser Plan erreicht

Das Dashboard wird von einer technischen Capture-Log-Ansicht zu einer **betriebsorientierten Chargen-Übersicht** umgebaut. Jeder empfangene TCP/9100-Druckauftrag erscheint als Charge mit Zeitstempel, Format-Erkennung und Text-Vorschau. Der Live-Monitor wird auf eine eigene Seite ausgelagert. Der Proxy-/Weiterleitungsmechanismus entfällt vollständig; stattdessen gibt es einen **USB-Auto-Druck-Toggle** (CUPS-Drucker, der bereits per USB angeschlossen ist).

### Warum das wichtig ist

DocuControl ist kein Netzwerk-Proxy, sondern ein **Dokumentationstool**. Der Endnutzer im Tierlabor soll auf einen Blick sehen: Wie viele Chargen heute, was war die letzte Charge, wann — nicht welche TCP-Ports offen sind. Der USB-Drucker am Gerät macht Netzwerk-Weiterleitung obsolet.

---

## Aktueller Zustand

### Relevante bestehende Struktur

| Datei | Aktueller Stand |
|---|---|
| `templates/dashboard.html` | Clock, TCP-Status, Chargen-Zähler, USB, Temperatur + raw Job-List (technisch) |
| `templates/settings.html` → tabProxy | Proxy-Weiterleitungs-Felder (forward_host, forward_port) |
| `templates/monitor.html` | Vorhanden, aber noch auf Serial-Daten ausgerichtet |
| `tcp_print_capture.py` | Capture-Server mit forward_host-Logik |
| `app.py` | set_forward_host-Import, /api/tcp_capture/config (POST mit forward_host) |
| `database.py` | protocols-Tabelle: id, timestamp, device_name, raw_data, pdf_path, pdf_filename, file_size, status |
| `print_manager.py` | CUPS-Integration vorhanden (auto_print_pdf, get_printers) |
| `data/raw_captures/` | .bin + .txt Dateien je Druckauftrag |

### Lücken oder Probleme

- Dashboard zeigt technische Rohdaten (Dateinamen, Bytes), nicht Chargen-Info
- Proxy-Logik ergibt für USB-Only-Betrieb keinen Sinn
- Live-Monitor blockiert Dashboard-Platz, gehört auf eigene Seite
- Kein Toggle für TCP-Capture-Aktivierung/Deaktivierung
- Kein Auto-Druck-Toggle für USB-Drucker
- TCP-Capture-Config nicht persistiert (geht bei Neustart verloren)

---

## Vorgeschlagene Änderungen

### Zusammenfassung

1. **tcp_print_capture.py**: Forwarding-Code entfernen, persistente Config (JSON), Auto-Print-Hook einbauen
2. **app.py**: Neue API-Endpoints (toggle, auto-print), `/api/dashboard/chargen` für Dashboard-Daten, Config-Persistenz
3. **dashboard.html**: Chargen-zentriertes Layout, letzte Chargen als Cards, kein Raw-Terminal
4. **settings.html → tabProxy → umbenannt zu "Empfang"**: TCP on/off Toggle, Port, Auto-Druck Toggle; Proxy-Felder raus
5. **templates/monitor.html**: TCP-Capture Live-Feed statt Serial-Terminal
6. **base.html**: Nav-Link "Monitor" hinzufügen

### Neue Dateien erstellen

| Dateipfad | Zweck |
|---|---|
| `/home/docucontrol/docupi/data/capture_config.json` | Persistiert tcp_enabled, auto_print, port (wird beim ersten Start angelegt) |

### Zu ändernde Dateien (auf dem DocuControl-Pi)

| Datei | Änderungen |
|---|---|
| `tcp_print_capture.py` | Forwarding entfernen; Config aus JSON laden; Auto-Print-Callback |
| `app.py` | 5 neue Endpoints; Config-Lesen beim Start; Import anpassen |
| `templates/dashboard.html` | Komplett neu: Chargen-Liste als Cards, Letzte-Charge-Preview, Monitor-Link |
| `templates/settings.html` | tabProxy → tabEmpfang: Toggle + Port + Auto-Druck; Proxy-Felder weg |
| `templates/monitor.html` | TCP-Capture Live-Feed (letztes .txt anzeigen, Auto-Refresh) |
| `templates/base.html` | Monitor-Nav-Link hinzufügen |

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **Captures bleiben Dateisystem, keine DB-Erweiterung**: Die protocols-Tabelle ist für geparste, abgeschlossene Chargen. Rohe Captures bleiben in `/data/raw_captures/`. Wenn der Parser kommt, werden Captures in die DB überführt. Saubere Trennung.

2. **Dashboard-Chargen = aus Dateisystem lesen**: Neuer Endpoint `/api/dashboard/chargen` liest die letzten N `.bin`+`.txt` aus raw_captures, extrahiert Metadaten (Timestamp aus Dateiname, Größe, erste 3 Zeilen aus .txt als Vorschau) und gibt JSON zurück. Kein DB-Overhead für den Betrieb ohne Parser.

3. **Auto-Print = CUPS, nicht Forwarding**: `print_manager.auto_print_pdf` ist bereits vorhanden. Der Druck-Hook in tcp_print_capture soll nach Empfang eines Jobs die .txt-Datei (oder eine mini-PDF-Zusammenfassung) an CUPS schicken. Konkret: raw text auf konfiguriertem USB-Drucker ausdrucken, bis der PDF-Parser kommt.

4. **TCP-Toggle persistiert in JSON-Datei**: `capture_config.json` mit Feldern `tcp_enabled` (bool), `auto_print` (bool), `port` (int, default 9100). Wird beim Start gelesen; Änderungen via API werden sofort in die Datei geschrieben.

5. **Live-Monitor = letztes .txt anzeigen**: `/monitor` zeigt den Inhalt der zuletzt empfangenen `.txt`-Datei mit Auto-Refresh alle 5s. Einfach, wartbar, kein WebSocket nötig.

6. **"Seriell"-Tab in Settings bleibt**: Wird für DocuControl nicht genutzt, aber für spätere WD-RDG-Variante eventuell. Nicht anfassen.

### Betrachtete Alternativen

- **nginx als Reverse-Proxy für Port 80**: Verworfen, nftables-Lösung reicht.
- **WebSocket für Live-Monitor**: Verworfen, Polling auf .txt-Datei ist für diesen Use-Case ausreichend und einfacher.
- **Captures direkt in DB speichern**: Verworfen, zu früh — Datenbankschema würde sich mit dem Parser ändern.

### Offene Fragen

- Soll der Auto-Druck die rohe `.txt`-Datei drucken oder eine Mini-PDF? → Vorschlag: Text-Druck (lpr) bis Parser fertig ist, dann PDF.
- Soll der "Empfang"-Tab auch die Captures löschen können (Aufräumen)? → Vorschlag: Ja, einfacher "Alle löschen"-Button.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: tcp_print_capture.py — Forwarding raus, Config + Auto-Print rein

**Ziel:** Forwarding-Code entfernen, persistente Config einlesen, optionalen Auto-Print-Hook nach Capture auslösen.

**Aktionen:**
- `CAPTURE_CONFIG_FILE = "/home/docucontrol/docupi/data/capture_config.json"` einführen
- `DEFAULT_CONFIG = {"tcp_enabled": True, "auto_print": False, "port": 9100}`
- `load_capture_config()` und `save_capture_config()` Funktionen
- `forward_host`, `forward_port`, `set_forward_host()` vollständig entfernen
- `PrintCaptureServer.__init__`: kein forward_host mehr; stattdessen `auto_print` Flag
- Nach erfolgreichem Capture: wenn `auto_print` → Callback `_on_job_received(bin_path, txt_path)` aufrufen
- `_on_job_received`: Text-Datei via `lpr` an Standard-CUPS-Drucker schicken (subprocess)
- `start_capture_server(auto_print=False)` Signatur vereinfachen
- `get_capture_status()` gibt `auto_print` und `tcp_enabled` mit zurück

**Betroffene Dateien:**
- `tcp_print_capture.py`

---

### Schritt 2: app.py — Neue Endpoints, Config-Import anpassen

**Ziel:** Neue API-Endpoints für Toggle, Auto-Print, Dashboard-Chargen. Import von `set_forward_host` entfernen.

**Aktionen:**

Import-Zeile anpassen:
```python
# Alt:
from tcp_print_capture import start_capture_server, get_capture_status, set_forward_host
# Neu:
from tcp_print_capture import start_capture_server, get_capture_status, load_capture_config, save_capture_config
```

Boot-Sequenz anpassen (nach `start_hotspot_monitor()`):
```python
_cap_cfg = load_capture_config()
if _cap_cfg.get("tcp_enabled", True):
    start_capture_server(auto_print=_cap_cfg.get("auto_print", False))
    logger.info("TCP/9100 capture server gestartet")
```

Neue Endpoints hinzufügen (vor `if __name__ == "__main__":`):

```python
@app.route("/api/tcp_capture/config", methods=["GET"])
def api_tcp_capture_config_get():
    return jsonify(load_capture_config())

@app.route("/api/tcp_capture/config", methods=["POST"])
def api_tcp_capture_config_post():
    data = request.json or {}
    cfg = load_capture_config()
    if "tcp_enabled" in data:
        cfg["tcp_enabled"] = bool(data["tcp_enabled"])
    if "auto_print" in data:
        cfg["auto_print"] = bool(data["auto_print"])
    if "port" in data:
        cfg["port"] = int(data["port"])
    save_capture_config(cfg)
    return jsonify({"ok": True, "config": cfg})

@app.route("/api/dashboard/chargen")
def api_dashboard_chargen():
    """Letzte N Captures als Chargen-Metadaten zurückgeben."""
    import os
    capture_dir = "/home/docucontrol/docupi/data/raw_captures"
    result = []
    if os.path.exists(capture_dir):
        bins = sorted(
            [f for f in os.listdir(capture_dir) if f.endswith(".bin")],
            reverse=True
        )[:20]
        for fname in bins:
            fpath = os.path.join(capture_dir, fname)
            txt_path = fpath.replace(".bin", ".txt")
            size = os.path.getsize(fpath)
            # Timestamp aus Dateiname: YYYYMMDD_HHMMSS_jobNNNN.bin
            try:
                ts_raw = fname[:15]
                ts_fmt = f"{ts_raw[6:8]}.{ts_raw[4:6]}.{ts_raw[0:4]} {ts_raw[9:11]}:{ts_raw[11:13]}:{ts_raw[13:15]}"
            except Exception:
                ts_fmt = fname
            preview = ""
            if os.path.exists(txt_path):
                try:
                    with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
                        lines = [l.strip() for l in f.readlines() if l.strip()][:4]
                        preview = " | ".join(lines)[:120]
                except Exception:
                    pass
            result.append({
                "filename": fname,
                "timestamp": ts_fmt,
                "size": size,
                "has_text": os.path.exists(txt_path),
                "preview": preview,
            })
    return jsonify(result)

@app.route("/api/tcp_capture/captures/<fname>")
def api_tcp_capture_download_fixed(fname):
    import os
    capture_dir = "/home/docucontrol/docupi/data/raw_captures"
    fp = os.path.join(capture_dir, fname)
    if not os.path.exists(fp):
        return jsonify({"error": "not found"}), 404
    return send_file(fp, as_attachment=True)

@app.route("/api/tcp_capture/captures/delete", methods=["POST"])
def api_tcp_capture_delete_all():
    import os, glob
    capture_dir = "/home/docucontrol/docupi/data/raw_captures"
    deleted = 0
    for f in glob.glob(os.path.join(capture_dir, "*")):
        try:
            os.remove(f)
            deleted += 1
        except Exception:
            pass
    log_event("INFO", f"Captures gelöscht: {deleted} Dateien")
    return jsonify({"ok": True, "deleted": deleted})
```

Alten `api_tcp_capture_config`-Endpoint (mit forward_host) entfernen.

**Betroffene Dateien:**
- `app.py`

---

### Schritt 3: dashboard.html — Chargen-zentriertes Layout

**Ziel:** Dashboard zeigt Chargen-Liste mit Vorschau statt raw Job-List. Live-Monitor-Link statt Terminal-Embed.

**Neues Layout:**

```
Zeile 1 (6 Kacheln): Uhr | Empfang-Status | Chargen heute | Chargen gesamt | USB | Temperatur
Banner: Neue Charge empfangen (Flash, 8s)
Zeile 2: Letzte Chargen (Cards, volle Breite)
  - Je Charge: Datum/Uhrzeit, Größe, Format-Preview (erste 4 Zeilen), Download-Icon
  - Leer-Zustand: "Warte auf ersten Druckauftrag..."
Zeile 3: Link → "Live-Monitor öffnen" (→ /monitor)
```

**Status-Kachel "Empfang":**
- Icon: `bi-hdd-network`
- Wert: `Aktiv` (grün) / `Inaktiv` (rot)
- Label: `TCP :9100 — N Chargen`

**Chargen-Card-Design** (Bootstrap card, nicht dark terminal):
```
[Datum/Zeit]    [Format-Badge]    [Größe KB]    [Download-Icon]
[Text-Preview: erste 4 Zeilen, grau, font-size .8rem]
```

**JS:**
- `loadChargen()` → `GET /api/dashboard/chargen` → Cards rendern
- `loadCaptures()` → `GET /api/tcp_capture/status` → Status-Kachel + Flash-Banner
- Auto-Refresh alle 8s
- Clock-Sync bleibt wie gehabt

**Was entfernt wird:**
- Dunkles Terminal-Style Job-List
- `fwdInfo`-Span
- Proxy-Config-Block (schon entfernt)
- `clearFwd()`/`saveFwd()` JS

**Betroffene Dateien:**
- `templates/dashboard.html`

---

### Schritt 4: settings.html → tabProxy → tabEmpfang

**Ziel:** Proxy-Felder raus, TCP-Toggle + Port + Auto-Druck-Toggle rein.

**Tab-Nav-Link ändern:**
```html
<!-- Alt -->
<li class="nav-item"><a class="nav-link" data-bs-toggle="pill" href="#tabProxy">
  <i class="bi bi-arrow-left-right"></i> TCP / Proxy</a></li>
<!-- Neu -->
<li class="nav-item"><a class="nav-link" data-bs-toggle="pill" href="#tabEmpfang">
  <i class="bi bi-hdd-network"></i> Empfang</a></li>
```

**Tab-Content (tabProxy → tabEmpfang):**
```
Section: TCP-Empfang
  Toggle: "Empfang aktiviert" (Ja/Nein) — POST /api/tcp_capture/config {tcp_enabled}
  Input: Port (default 9100)
  [Speichern-Button]
  Info-Box: "Empfang-Änderungen werden erst nach Neustart des Dienstes wirksam."

Section: USB-Automatikdruck
  Toggle: "Nach Empfang automatisch drucken" (Ja/Nein)
  Info: "Druckt den Textinhalt jedes empfangenen Auftrags auf den Standard-USB-Drucker."
  [Speichern-Button]
  
Section: Aufräumen
  Button "Alle Captures löschen" → POST /api/tcp_capture/captures/delete
```

**JS in settings.html ergänzen:**
```javascript
function loadEmpfangConfig() {
  fetch('/api/tcp_capture/config').then(r => r.json()).then(cfg => {
    document.getElementById('tcpEnabled').checked = cfg.tcp_enabled !== false;
    document.getElementById('tcpPort').value = cfg.port || 9100;
    document.getElementById('autoPrint').checked = cfg.auto_print === true;
  });
}
function saveEmpfangConfig() { ... POST /api/tcp_capture/config ... }
function saveAutoPrint() { ... POST /api/tcp_capture/config {auto_print} ... }
loadEmpfangConfig();
```

**Betroffene Dateien:**
- `templates/settings.html`

---

### Schritt 5: monitor.html — TCP Live-Feed

**Ziel:** `/monitor` zeigt letzten empfangenen Druckauftrag (`.txt`) statt Serial-Terminal.

**Neues Layout:**
```
Header: "Live-Monitor — Letzter empfangener Druckauftrag"
Status-Zeile: Dateiname, Timestamp, Größe, Format
Text-Box (dark terminal style): Inhalt der .txt-Datei
Footer: "Auto-Refresh alle 5s | Zurück zum Dashboard"
```

**API-Erweiterung in app.py** (Schritt 2 ergänzen):
```python
@app.route("/api/tcp_capture/last_text")
def api_tcp_last_text():
    import os
    capture_dir = "/home/docucontrol/docupi/data/raw_captures"
    txts = sorted(
        [f for f in os.listdir(capture_dir) if f.endswith(".txt")],
        reverse=True
    ) if os.path.exists(capture_dir) else []
    if not txts:
        return jsonify({"filename": None, "content": ""})
    fname = txts[0]
    fpath = os.path.join(capture_dir, fname)
    try:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(50000)
    except Exception:
        content = ""
    return jsonify({"filename": fname, "content": content})
```

**monitor.html:**
- Entfernt: Serial-WebSocket-Terminal
- Hinzugefügt: `setInterval(() => fetch('/api/tcp_capture/last_text')...`, 5000)
- Text in `<pre>`-Block anzeigen

**Betroffene Dateien:**
- `templates/monitor.html`
- `app.py` (Endpoint `/api/tcp_capture/last_text`)

---

### Schritt 6: base.html — Monitor-Link in Navbar

**Ziel:** Monitor-Seite direkt aus der Navbar erreichbar.

**Aktion:**
Nav-Link nach "Protokolle" einfügen:
```html
<li class="nav-item">
  <a class="nav-link {% if request.endpoint == 'monitor' %}active{% endif %}" href="/monitor">
    <i class="bi bi-terminal"></i> Monitor
  </a>
</li>
```

**Betroffene Dateien:**
- `templates/base.html`

---

### Schritt 7: Service neu starten und validieren

**Aktionen:**
- `sudo systemctl restart docucontrol.service`
- HTTP 200 auf `/`, `/settings`, `/monitor` prüfen
- `/api/dashboard/chargen` aufrufen — leere Liste OK
- `/api/tcp_capture/config` GET — gibt `{tcp_enabled: true, auto_print: false, port: 9100}`
- Test-Job via `echo "TEST" | nc -q1 localhost 9100` senden
- Dashboard aufrufen — Charge erscheint in der Liste
- Monitor aufrufen — Text des Test-Jobs sichtbar
- Settings → Empfang-Tab öffnen — Toggle sichtbar

---

## Verbindungen & Abhängigkeiten

### Dateien, die diese Bereiche referenzieren

- `app.py` importiert `tcp_print_capture` — Schritt 1+2 müssen synchron sein
- `print_manager.py` — `auto_print_pdf()` und `lpr`-Befehl für Auto-Druck
- `data/raw_captures/` — Lesezugriff in Schritt 2 (dashboard/chargen)

### Auswirkungen auf bestehende Workflows

- Proxy-Forwarding-Feature fällt ersatzlos weg (war noch nie produktiv genutzt)
- Monitor-Seite wird von Serial → TCP umgestellt (Serial-Funktion nicht mehr erreichbar, ist für DocuControl ohnehin deaktiviert)
- USB-Druck-Toggle ist neu; bestehende CUPS-Integration (print_manager.py) bleibt unverändert

---

## Validierungs-Checkliste

- [ ] `docucontrol.service` startet ohne Fehler im Log
- [ ] Dashboard HTTP 200, zeigt Chargen-Kacheln
- [ ] Test-Job via nc → erscheint in Dashboard-Liste innerhalb 10s
- [ ] Monitor-Seite zeigt Text des Test-Jobs
- [ ] Settings → Empfang-Tab: Toggle + Port + Auto-Druck sichtbar, speicherbar
- [ ] `/api/tcp_capture/config` GET gibt korrektes JSON
- [ ] `/api/dashboard/chargen` gibt leere Liste oder vorhandene Captures
- [ ] Kein "forward_host" mehr in Code oder API-Antworten
- [ ] `capture_config.json` wird nach Neustart geladen

---

## Erfolgskriterien

1. Ein Benutzer öffnet das Dashboard und sieht die letzten empfangenen Chargen als übersichtliche Cards — nicht als Dateinamen-Liste
2. Im Einstellungen-Tab "Empfang" kann der TCP-Capture per Toggle ein/ausgeschaltet und Auto-Druck aktiviert werden
3. Der Live-Monitor ist über Navbar und Dashboard-Link erreichbar und zeigt den letzten empfangenen Druckauftrag im Klartext

---

---

## Implementierungsnotizen

**Implementiert:** 2026-06-02

### Zusammenfassung

Alle 7 Schritte umgesetzt: tcp_print_capture.py (Forwarding raus, Config-JSON, Auto-Print via lpr), app.py (6 neue Endpoints, Boot-Sequenz aus Config), dashboard.html (Chargen-Cards, Monitor-Link), settings.html (tabProxy → tabEmpfang mit Toggle/Auto-Druck/Löschen), monitor.html (TCP Live-Feed), base.html (Monitor-Link in Navbar). Service läuft stabil, Test-Job wurde empfangen und erscheint korrekt im Dashboard.

### Abweichungen vom Plan

- monitor.html hatte CSS-Konflikt (`{#monitorBox` → Jinja2-Kommentar-Syntax), mit Leerzeichen behoben: `{ #monitorBox`
- `capture_config.json` wird automatisch beim ersten API-Call angelegt (nicht manuell vorab)

### Aufgetretene Probleme

- Jinja2-Fehler in monitor.html durch `{#` in CSS-Selektor — behoben durch Leerzeichen-Einfügung

---

## Notizen

- **Parser-Vorbereitung**: Wenn der WD/RDG-Parser kommt, wird `/api/dashboard/chargen` angepasst um parsed Daten (Chargennummer, Programm, Ergebnis) aus der DB einzubinden — Dateisystem-Fallback bleibt für ungeparste Captures
- **Steri-Daten auf Dashboard**: Sobald der Parser Felder wie `charge_nr`, `programm`, `ergebnis`, `geraet` liefert, können diese als extra Kachel oben rechts im Dashboard erscheinen ("Letzte Charge: CH021854 | Instrumente 134° | BESTANDEN")
- **Auto-Druck Verbesserung**: Aktuell lpr auf raw text. Sobald PDF-Generator für das jeweilige Protokollformat gebaut ist, wird der Hook auf PDF-Druck umgestellt
