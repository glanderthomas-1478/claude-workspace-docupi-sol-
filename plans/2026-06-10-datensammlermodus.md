# Plan: Datensammlermodus

**Erstellt:** 2026-06-10
**Status:** Implementiert
**Anforderung:** Toggle in Einstellungen, der bei Aktivierung das Maschinenprotokoll 1:1 an den Drucker leitet (kein PDF, kein DB-Eintrag) und alle Raw-Captures speichert — zur Protokollanalyse in der Anfangsphase mit unbekanntem Dateiformat.

---

## Überblick

### Was dieser Plan erreicht

Ein neuer Toggle "Datensammlermodus" erscheint in der Settings-Card "TCP-Empfang". Wenn aktiv, wird nach jedem empfangenen TCP-Job der extrahierte Rohtext direkt per `lpr` an den Drucker geschickt — ohne Parser, ohne PDF-Generierung, ohne DB-Eintrag. Die `.bin`- und `.txt`-Captures werden wie immer in `data/raw_captures/` gespeichert. Wenn deaktiviert, läuft die normale Pipeline (Parse → PDF → DB).

### Warum das wichtig ist

Beim Tierlabor-Einsatz (Belimed PST 14-8-12 HS1) sind noch nicht alle Programm-Varianten bekannt. Der Modus erlaubt, die Maschine einfach laufen zu lassen, alle Protokollvarianten physisch zu drucken und zu sammeln — und danach den `protocol_parser.py` auf echten Daten zu kalibrieren. Kein blinder Feldtest mehr.

---

## Aktueller Zustand

### Relevante bestehende Struktur

- `tcp_print_capture.py` → zentraler Ort der Capture-Logik (auf Pi: `/home/docucontrol/docupi/`)
  - `_process_job()` → ruft Parser, PDF-Generator und DB auf (Zeilen 126–151)
  - `_auto_print_text()` → druckt `.txt` via `lpr` (Zeilen 107–121, bereits vorhanden)
  - `_handle()` → Entscheidungslogik nach Capture (Zeilen 162–224)
  - `load_capture_config()` / `save_capture_config()` → nutzt `capture_config.json`
  - `DEFAULT_CONFIG` → `{tcp_enabled, auto_print, port}` — hier fehlt `collector_mode`
- `capture_config.json` → `/home/docucontrol/docupi/data/capture_config.json` (persistente TCP-Config)
- `app.py` (auf Pi) → enthält alle API-Endpunkte; zuständig für `/api/tcp/*`
- `src/docucontrol/templates/settings.html` → Card "TCP-Empfang" zeigt Toggle + Statistik (Zeilen 95–124)
- `src/docucontrol/static/docucontrol.css` → bestehende CSS-Patterns für `set-row`, `switch`, `badge`

### Lücken oder Probleme, die adressiert werden

- `_handle()` ruft `_process_job()` bedingungslos auf (kein Mode-Gate)
- `capture_config.json` kennt kein `collector_mode`-Flag
- Settings-UI hat keinen entsprechenden Toggle
- Kein API-Endpunkt zum Lesen/Schreiben des Modus

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

- `tcp_print_capture.py`: `collector_mode` zu `DEFAULT_CONFIG` hinzufügen, `_handle()` verzweigt je nach Modus
- `app.py`: 2 neue API-Endpunkte (`GET/POST /api/capture/collector`)
- `settings.html`: neuer Toggle-Row in Card "TCP-Empfang" + JS-Funktionen

### Neue Dateien erstellen

Keine neuen Dateien nötig.

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|---|---|
| `tcp_print_capture.py` (Pi) | `DEFAULT_CONFIG` + `collector_mode`, `_handle()` Verzweigung, `get_status()` erweitern |
| `app.py` (Pi) | `GET /api/capture/collector` + `POST /api/capture/collector` |
| `src/docucontrol/templates/settings.html` | Toggle-Row in TCP-Empfang Card + `loadCollectorMode()` + `toggleCollectorMode()` JS |

### Zu löschende Dateien

Keine.

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **Flag in `capture_config.json`, nicht `config.json`**: `collector_mode` ist TCP-Capture-Verhalten, nicht Serial/PDF/Web-Config. Passt semantisch zu `tcp_enabled` und `auto_print` die dort schon liegen.

2. **`lpr` statt CUPS `print_pdf()`**: Im Sammelmodus liegt kein PDF vor — es gibt nur `.txt`. `_auto_print_text()` nutzt bereits `lpr txt_path` und ist genau dafür gedacht. Keine neue Abhängigkeit, kein CUPS-Overhead.

3. **`_process_job()` wird im Sammelmodus komplett übersprungen**: Kein DB-Eintrag, kein PDF. Der Modus soll explizit sauber trennen: entweder Produktion (Parse+PDF+DB) oder Sammeln (Raw+Druck). Mischbetrieb würde die DB mit kaputten/unvollständigen Protokollen füllen.

4. **Bin+Txt werden immer gespeichert**: Unabhängig vom Modus. Der Sammelmodus lebt davon, dass die Captures vorhanden sind. Dieser Teil ist schon in `_handle()` vor der Verzweigung und bleibt unverändert.

5. **Amber-Warn-Banner im UI wenn Modus aktiv**: Der Nutzer soll nicht vergessen, den Modus nach Datenbeschaffung wieder auszuschalten. Ein gelbes Info-Banner (CSS: `warn-banner`, bereits im Design-System vorhanden) erscheint wenn `collector_mode=true`.

6. **Toggle in Card "TCP-Empfang", nicht "Drucker"**: Sammelmodus ist eine Capture-Pipeline-Entscheidung, kein Drucker-Feature. Drucker-Card bleibt für Drucker.

### Betrachtete Alternativen

- **Eigene neue Settings-Card "Betriebsmodus"**: Overkill für einen einzelnen Toggle. TCP-Empfang ist die richtige Sektion.
- **Flag in `config.json` unter neuer Sektion `mode`**: Möglich, aber `capture_config.json` ist näher dran und wird von `tcp_print_capture.py` direkt gelesen.
- **Sammelmodus druckt `.bin` statt `.txt`**: Funktioniert nicht mit `lpr` (Binärdata). `.txt` ist der extrahierte lesbare Rohtext — genau das was gedruckt werden soll.

### Offene Fragen

Keine — Anforderung ist klar.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: `tcp_print_capture.py` — collector_mode zu DEFAULT_CONFIG

`DEFAULT_CONFIG` bekommt ein neues Feld. `get_status()` gibt den Wert zurück.

**Aktionen:**

- `DEFAULT_CONFIG` erweitern:
  ```python
  DEFAULT_CONFIG = {
      "tcp_enabled": True,
      "auto_print": False,
      "port": 9100,
      "collector_mode": False,   # NEU
  }
  ```
- In `get_status()` den Wert aus Config lesen und zurückgeben:
  ```python
  cfg = load_capture_config()
  return {
      ...
      "collector_mode": cfg.get("collector_mode", False),  # NEU
  }
  ```

**Betroffene Dateien:**

- `tcp_print_capture.py` auf Pi (`/home/docucontrol/docupi/tcp_print_capture.py`)

---

### Schritt 2: `tcp_print_capture.py` — `_handle()` Verzweigung

Nach dem Speichern von `.bin` und `.txt` verzweigt `_handle()` jetzt:
- **Sammelmodus aktiv**: `_auto_print_text(txt_path)` aufrufen (direkt per `lpr`)
- **Sammelmodus inaktiv**: `_process_job()` aufrufen (bisheriges Verhalten)

**Aktionen:**

Den Block ab Zeile 213 (aktuell: `if self.auto_print and txt_path`) ersetzen durch:

```python
cfg = load_capture_config()
collector_mode = cfg.get("collector_mode", False)

if collector_mode:
    # Sammelmodus: Rohtext 1:1 drucken, kein Parse, keine PDF, kein DB-Eintrag
    if txt_path:
        logger.info("Sammelmodus: Rohtext-Druck ohne PDF-Generierung")
        threading.Thread(
            target=_auto_print_text, args=(txt_path,), daemon=True
        ).start()
else:
    # Normalmodus: Parse → PDF → DB
    if txt_path:
        with open(txt_path, "r", encoding="utf-8", errors="replace") as _f:
            _raw_text = _f.read()
        threading.Thread(
            target=_process_job, args=(txt_path, _raw_text), daemon=True
        ).start()
    # Legacy auto_print (aus alter Config, wird ignoriert wenn collector_mode aktiv)
    if self.auto_print and txt_path and not collector_mode:
        threading.Thread(
            target=_auto_print_text, args=(txt_path,), daemon=True
        ).start()
```

**Hinweis:** `self.auto_print` ist der alte Instance-Parameter (aus `start_capture_server(auto_print=False)`). Im Normalmodus bleibt er wie er war. Im Sammelmodus ersetzt `collector_mode` seinen Zweck vollständig.

**Betroffene Dateien:**

- `tcp_print_capture.py` auf Pi

---

### Schritt 3: `app.py` — API-Endpunkte

Zwei neue Routen nach dem bestehenden `/api/tcp/*`-Block einfügen.

**Aktionen:**

```python
@app.route('/api/capture/collector', methods=['GET'])
def api_collector_get():
    from tcp_print_capture import load_capture_config
    cfg = load_capture_config()
    return jsonify({'collector_mode': cfg.get('collector_mode', False)})


@app.route('/api/capture/collector', methods=['POST'])
def api_collector_set():
    from tcp_print_capture import load_capture_config, save_capture_config
    data = request.get_json(silent=True) or {}
    enabled = bool(data.get('enabled', False))
    cfg = load_capture_config()
    cfg['collector_mode'] = enabled
    save_capture_config(cfg)
    return jsonify({'collector_mode': enabled, 'ok': True})
```

**Betroffene Dateien:**

- `app.py` auf Pi (`/home/docucontrol/docupi/app.py`)

---

### Schritt 4: `settings.html` — Toggle-Row in TCP-Empfang Card

In der Card "TCP-Empfang" (nach dem `lastCapture`-Row, vor `</div></div>`) eine neue Set-Row mit Toggle + Warn-Banner einfügen.

**Aktionen:**

Direkt nach dem `lastCapture`-Row (nach `</div>` Zeile ~123) einfügen:

```html
<div class="set-row">
    <div class="info">
        <div class="name">Datensammlermodus</div>
        <div class="desc">Rohprotokoll direkt drucken — kein PDF, kein Datenbank-Eintrag</div>
    </div>
    <label class="switch">
        <input type="checkbox" id="collectorModeToggle" onchange="toggleCollectorMode(this.checked)">
        <span class="track"></span>
    </label>
</div>
<div id="collectorWarning" style="display:none;margin:8px 0 0 0;padding:10px 14px;background:var(--warn-banner-bg,#fff7e6);border:1px solid var(--warn-banner-border,#ffe1a8);border-radius:8px;color:var(--warn-banner-fg,#8a5a00);font-size:13px">
    <i class="bi bi-exclamation-triangle-fill" style="margin-right:6px"></i>
    <strong>Sammelmodus aktiv</strong> — Empfangene Protokolle werden nicht verarbeitet. Bitte nach der Datenbeschaffung deaktivieren.
</div>
```

**JS-Funktionen** im `<script>`-Block der settings.html ergänzen:

```javascript
function loadCollectorMode() {
    fetch('/api/capture/collector')
        .then(r => r.json())
        .then(d => {
            const cb = document.getElementById('collectorModeToggle');
            if (cb) cb.checked = !!d.collector_mode;
            document.getElementById('collectorWarning').style.display =
                d.collector_mode ? 'block' : 'none';
        })
        .catch(() => {});
}

function toggleCollectorMode(enabled) {
    fetch('/api/capture/collector', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({enabled})
    })
        .then(r => r.json())
        .then(d => {
            document.getElementById('collectorWarning').style.display =
                d.collector_mode ? 'block' : 'none';
        })
        .catch(() => {});
}
```

`loadCollectorMode()` beim Init aufrufen — im bestehenden Initialisierungsblock am Ende der settings.html wo `loadTcpStatus()`, `loadPrinterStatus()` etc. aufgerufen werden:

```javascript
loadCollectorMode();
```

**Betroffene Dateien:**

- `src/docucontrol/templates/settings.html`

---

### Schritt 5: Deployment auf Pi

Geänderte Dateien per SSH auf den Pi übertragen und Service neu starten.

**Aktionen:**

```bash
# tcp_print_capture.py deployen
scp -i ~/.ssh/id_ed25519 <lokaler_pfad>/tcp_print_capture.py docucontrol@192.168.0.171:/home/docucontrol/docupi/tcp_print_capture.py

# app.py deployen  
scp -i ~/.ssh/id_ed25519 <lokaler_pfad>/app.py docucontrol@192.168.0.171:/home/docucontrol/docupi/app.py

# settings.html deployen
scp -i ~/.ssh/id_ed25519 src/docucontrol/templates/settings.html docucontrol@192.168.0.171:/home/docucontrol/docupi/templates/settings.html

# Service neu starten
ssh -i ~/.ssh/id_ed25519 docucontrol@192.168.0.171 "echo Xtend1478 | sudo -S systemctl restart docucontrol.service"

# Status prüfen
ssh -i ~/.ssh/id_ed25519 docucontrol@192.168.0.171 "systemctl status docucontrol.service --no-pager"
```

**Alternativ:** Das bestehende `scripts/deploy_docucontrol_design.sh` anpassen, damit es die neuen Dateien mitüberträgt.

**Betroffene Dateien:**

- Deploy-Script oder manuelles SCP

---

### Schritt 6: CLAUDE.md + context/strategy.md aktualisieren

Den neuen Feature-Status dokumentieren.

**Aktionen:**

- In `CLAUDE.md` unter "DocuControl Web-Interface" einen Eintrag für den Datensammlermodus hinzufügen
- In `context/strategy.md` unter Punkt 5 den Status updaten

**Betroffene Dateien:**

- `CLAUDE.md`
- `context/strategy.md`

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- `app.py` → importiert `tcp_print_capture` (get_capture_status, start_capture_server)
- `settings.html` → ruft `/api/tcp/status`, `/api/tcp/toggle`, `/api/printer/status` — neue Endpunkte ergänzen diese Liste
- `capture_config.json` → von `tcp_print_capture.py` gelesen/geschrieben, wird um `collector_mode` erweitert

### Nötige Updates für Konsistenz

- `CLAUDE.md` → neue API-Endpunkte dokumentieren
- `context/current-data.md` → Metrik-Tabelle aktualisieren

### Auswirkungen auf bestehende Workflows

- **Normalbetrieb unverändert** — `collector_mode` defaults zu `False`, Pipeline läuft wie bisher
- **Auto-Print (print_config.json)** bleibt separat und unverändert — er greift nur im Normalmodus nach PDF-Generierung
- **USB Auto-Sync** nicht betroffen — synct PDFs, im Sammelmodus entstehen keine PDFs (korrekt)
- **Dashboard Protokoll-Tabelle** zeigt im Sammelmodus keine neuen Einträge (korrekt — kein DB-Eintrag)

---

## Validierungs-Checkliste

- [ ] Toggle in Settings sichtbar und korrekt positioniert (unterhalb "Letzter Empfang")
- [ ] Warn-Banner erscheint beim Aktivieren, verschwindet beim Deaktivieren
- [ ] `GET /api/capture/collector` gibt `{"collector_mode": false}` zurück (Standardwert)
- [ ] `POST /api/capture/collector` mit `{"enabled": true}` schreibt in `capture_config.json`
- [ ] Nach Page-Reload bleibt Toggle-Zustand erhalten (Persistenz via JSON)
- [ ] Sammelmodus aktiv: eingehender TCP-Job erzeugt `.bin` + `.txt` aber kein PDF, kein DB-Eintrag
- [ ] Sammelmodus aktiv: Druckauftrag wird via `lpr` an Drucker geschickt (sofern angeschlossen)
- [ ] Normalmodus: Pipeline unverändert (Parse → PDF → DB → optional Auto-Print)
- [ ] Service startet nach Neustart ohne Fehler (systemctl status)

---

## Erfolgskriterien

1. Toggle in Settings speichert Zustand dauerhaft in `capture_config.json`
2. Im Sammelmodus: ein empfangener TCP-Job landet als Rohtext beim Drucker — kein Eintrag in DB, kein PDF in `data/pdfs/`
3. Im Normalmodus: Verhalten exakt wie vor der Änderung (kein Regressionsrisiko)

---

## Notizen

- **Nächster Schritt nach Sammlung**: Die gesammelten `.txt`-Dateien aus `data/raw_captures/` analysieren und `protocol_parser.py` damit kalibrieren. Dafür ggf. separater Plan "Parser-Kalibrierung PST 14-8-12 HS1".
- **Druckt auch wenn kein Drucker da**: `lpr` gibt einen Fehler zurück, der geloggt wird — aber der Capture-Prozess läuft weiter. Captures sind also immer vorhanden, Druck ist Best-Effort.
- **Fernzugriff**: Wenn der Pi nicht erreichbar ist (Tierlabor, kein VPN), kann der Modus nicht remote umgeschaltet werden. Vor Ort per Browser auf `http://192.168.0.171` ist immer möglich.

---

## Implementierungsnotizen

**Implementiert:** 2026-06-10

### Zusammenfassung

- `tcp_print_capture.py`: `collector_mode` zu `DEFAULT_CONFIG` + `get_capture_status()` hinzugefügt; `_handle()` verzweigt jetzt per Flag; gleichzeitig 2026-06-09 Auto-Print-Fix (`auto_print_pdf()`) in `_process_job()` integriert
- `app.py`: `GET/POST /api/capture/collector` vor `if __name__` eingefügt — auf Pi's aktuelle Version (nicht Backup) angewendet um 2026-06-09 machine/ping/stats-Änderungen nicht zu verlieren
- `settings.html`: Toggle-Row + Warn-Banner in Card "TCP-Empfang", `loadCollectorMode()`/`toggleCollectorMode()` JS, Init-Aufruf in `loadDeviceSettings()`
- Deployment: alle 3 Dateien live deployed, Service neu gestartet, API-Endpunkte getestet

### Abweichungen vom Plan

- `app.py` nicht per Backup-Datei deployed, sondern Pi's aktuelle Version heruntergeladen, gepatch und hochgeladen — Backup wäre veraltet (2026-06-09 Änderungen fehlten)
- Legacy `self.auto_print`-Zweig im Plan vorgesehen aber weggelassen: `auto_print_pdf()` wird jetzt direkt in `_process_job()` aufgerufen (sauberer, kein doppelter Thread)

### Aufgetretene Probleme

Keine.
