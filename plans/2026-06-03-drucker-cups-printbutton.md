# Plan: USB-Drucker einrichten, RAW/IPP-Druck, Print-Button nur bei aktivem Drucker

**Erstellt:** 2026-06-03
**Status:** Implementiert
**Anforderung:** Epson XP-4150 USB-Drucker via CUPS (driverless/IPP Everywhere) aktivieren, Print-Button im Dashboard nur anzeigen wenn Drucker bereit ist

---

## Überblick

### Was dieser Plan erreicht

CUPS wird auf dem DocuControl-Pi installiert und gestartet, der angeschlossene Epson XP-4150 wird
als driverless IPP-Everywhere-Drucker eingerichtet. Der Dashboard-Print-Button erscheint nur wenn
ein Drucker tatsächlich bereit ist — statt immer. Ein neuer `/api/print/<id>`-Endpunkt verbindet
Protokoll-ID direkt mit dem Druckauftrag.

### Warum das wichtig ist

Der erste Kunden-Deal (Tierlabor Uni Essen) setzt voraus dass das System Chargenprotokolle
automatisch oder on-demand ausdruckt. Aktuell ist CUPS nicht aktiv, pycups liefert
`cups_available: false`, und der Print-Button im Dashboard funktioniert nicht. Außerdem ist
der Button immer sichtbar — auch ohne Drucker, was beim Kunden verwirrend wirkt.

---

## Aktueller Zustand

### Relevante bestehende Struktur

- `/dev/usb/lp0` — Epson XP-4150 erkannt (USB ID `04b8:119a`), Kernel-Device vorhanden
- `src/print_manager.py` — vollständiger CUPS-Manager mit pycups, **Pfad-Bug**: `PRINT_CONFIG_FILE` zeigt auf `/home/belimed/...` statt `/home/docucontrol/...`
- `pycups 2.0.4` — im venv installiert, aber CUPS-Daemon nicht aktiv
- `cups service` — `inactive` (nicht installiert oder nicht gestartet)
- `app.py` — Routen `/api/printers`, `/api/print` (POST, nimmt Body), `/api/print/test`, `/api/print/config` existieren
- `data/print_config.json` — `auto_print: false`, `default_printer: ""`
- `dashboard.html` — `printPdf(id)` ruft `POST /api/print/<id>` auf — **Route existiert nicht** (app.py hat nur `POST /api/print` ohne ID)

### Lücken oder Probleme, die adressiert werden

1. CUPS nicht installiert/aktiv → pycups gibt immer `cups_available: false`
2. `PRINT_CONFIG_FILE` Pfad falsch (`/home/belimed/` statt `/home/docucontrol/`)
3. Route `POST /api/print/<int:pid>` fehlt — Dashboard-Button schlägt immer fehl
4. Kein `/api/printer/ready`-Endpunkt → Dashboard kann Drucker-Status nicht abfragen
5. Print-Button immer sichtbar — auch ohne Drucker, verwirrend für Kunden
6. `docucontrol`-User nicht in `lp`-Gruppe → kein Zugriff auf `/dev/usb/lp0`

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

- CUPS + cups-client installieren, Service aktivieren
- `docucontrol` zu `lp`-Gruppe hinzufügen
- Epson XP-4150 driverless via `lpadmin -p` oder `lpinfo -l` + `lpadmin` einrichten
- `print_manager.py`: Pfad-Bug fixen
- `app.py`: Route `POST /api/print/<int:pid>` hinzufügen + `GET /api/printer/ready`
- `dashboard.html`: Print-Button-Sichtbarkeit an Drucker-Status koppeln

### Neue Dateien erstellen

Keine neuen Dateien nötig.

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|---|---|
| Pi: `app.py` | Route `POST /api/print/<int:pid>` + `GET /api/printer/ready` hinzufügen |
| Pi: `print_manager.py` | `PRINT_CONFIG_FILE` Pfad-Bug fixen (`belimed` → `docucontrol`) |
| Pi: `templates/dashboard.html` | Print-Button nur rendern wenn `printerReady === true` |
| Lokal: `src/docucontrol/templates/dashboard.html` | Gleiche Änderung für Konsistenz |
| Lokal: `src/print_manager.py` | Pfad-Bug fixen (für künftige Deployments) |

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **CUPS + IPP Everywhere (driverless)**: Epson XP-4150 unterstützt IPP Everywhere nativ.
   Kein spezifischer Epson-Treiber nötig. URI: `ipp://localhost/printers/<name>` oder direkt
   `usb://Epson/XP-4150%20Series`. Funktioniert mit praktisch allen modernen Druckern — wenn der
   Kunde das Gerät im Tierlabor tauscht, reicht ein `lpadmin` ohne Treiber-Suche.

2. **pycups als Interface, kein direktes lp0-Schreiben**: `print_manager.py` ist bereits fertig
   und battle-tested. Direktes Schreiben auf `/dev/usb/lp0` mit Ghostscript wäre fragiler
   (Drucker muss PCL/PS verstehen, kein Job-Tracking, kein Status).

3. **`/api/printer/ready` als separater Endpunkt**: Dashboard ruft diesen einmal beim Laden +
   alle 60s auf. Gibt `{"ready": bool, "printer": "name", "state": "bereit|gestoppt|..."}` zurück.
   Kopplung über API statt Template-Variable — passt zum bestehenden JS-Muster.

4. **Print-Button: CSS `display:none` statt DOM-Entfernung**: Tabelle wird neu gerendert bei
   Seitenänderung/Filter. `printerReady`-Variable wird gesetzt und in `renderTable` ausgewertet —
   kein separates DOM-Update nötig.

5. **`POST /api/print/<int:pid>`**: Schlägt die Brücke zwischen Protokoll-ID (aus Tabelle) und
   PDF-Pfad (aus DB). Ruft intern `print_pdf()` aus print_manager auf. Konsistent mit
   `/download/<int:pid>` Muster.

### Betrachtete Alternativen

- **Direktes Ghostscript auf lp0**: Kein CUPS-Overhead, aber kein Job-Tracking, keine
  Fehlerbehandlung, Epson XP-4150 braucht ESC/P oder PCL was manuell gerendert werden müsste.
- **python-escpos**: Nur für Bondrucker/Thermodrucker, nicht für A4-Drucker.
- **IPP direkt über ipputil/Python-ipp-Library**: Möglich aber kein bestehender Code dafür.

### Offene Fragen

Keine — Epson XP-4150 und CUPS sind klar definiert.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: CUPS installieren und Service starten

CUPS ist nicht installiert. `apt-get install` mit `-y` im non-interactive Modus.

**Aktionen:**

- `sudo apt-get install -y cups cups-client` — CUPS + Kommandozeilen-Tools
- `sudo systemctl enable cups` — autostart
- `sudo systemctl start cups` — sofort starten
- `sudo usermod -aG lp docucontrol` — Drucker-Gruppe (für /dev/usb/lp0 Zugriff)
- `sudo usermod -aG lpadmin docucontrol` — CUPS-Admin (für lpadmin ohne sudo)
- `newgrp lp` ist in non-interaktiven SSH-Sessions nicht nötig — Service-User wird beim
  nächsten Login / Service-Restart die Gruppe haben

**Betroffene Dateien:**

- System-Pakete, systemd-Units

---

### Schritt 2: Epson XP-4150 als driverless Drucker einrichten

CUPS IPP Everywhere / driverless erkennt moderne USB-Drucker automatisch.

**Aktionen:**

- Verfügbare Drucker-URIs anzeigen: `lpinfo -v | grep usb`
  - Erwartete Ausgabe: `direct usb://Epson/XP-4150%20Series?serial=...`
- Drucker hinzufügen:
  ```bash
  sudo lpadmin -p DocuPrinter \
    -E \
    -v "$(lpinfo -v | grep -i epson | head -1 | awk '{print $2}')" \
    -m driverless:ipp/2.0 \
    -o media=A4 \
    -o print-quality=4
  ```
  Flags: `-E` = aktivieren + akzeptieren, `-m driverless:ipp/2.0` = universelles Protokoll
- Drucker als Standard setzen: `sudo lpadmin -d DocuPrinter`
- Test: `echo "DocuControl Test" | lp -d DocuPrinter` oder CUPS-Testseite

**Fallback** falls driverless nicht erkannt wird:
- `lpadmin` mit `-m everywhere` versuchen
- Falls noch kein URI: `lpinfo -v 2>&1` zeigt alle verfügbaren Backends

**Betroffene Dateien:**

- CUPS-Konfiguration (`/etc/cups/printers.conf`)

---

### Schritt 3: Pfad-Bug in print_manager.py fixen

`PRINT_CONFIG_FILE` zeigt auf den alten DocuPi-Pfad `/home/belimed/docupi/data/print_config.json`
statt `/home/docucontrol/docupi/data/print_config.json`.

**Aktionen:**

- Auf dem Pi direkt patchen:
  ```python
  # Alt:
  PRINT_CONFIG_FILE = "/home/belimed/docupi/data/print_config.json"
  # Neu:
  PRINT_CONFIG_FILE = "/home/docucontrol/docupi/data/print_config.json"
  ```
- Lokal in `src/print_manager.py` ebenfalls korrigieren

**Betroffene Dateien:**

- Pi: `/home/docucontrol/docupi/print_manager.py`
- Lokal: `src/print_manager.py`

---

### Schritt 4: `GET /api/printer/ready` in app.py hinzufügen

Neuer Endpunkt — gibt Drucker-Bereitschaft zurück. Dashboard ruft diesen ab.

**Aktionen:**

- Route nach bestehenden `/api/printers`-Route einfügen:
  ```python
  @app.route("/api/printer/ready")
  def api_printer_ready():
      if not is_cups_available():
          return jsonify({"ready": False, "printer": "", "state": "CUPS nicht verfügbar"})
      printers = get_printers()
      if not printers:
          return jsonify({"ready": False, "printer": "", "state": "Kein Drucker"})
      config = load_print_config()
      name = config.get("default_printer") or printers[0]["name"]
      p = next((x for x in printers if x["name"] == name), printers[0])
      ready = p["state"] in (3,) and p["accepting"]  # state 3 = bereit
      return jsonify({
          "ready": ready,
          "printer": p["info"] or p["name"],
          "state": p["state_text"],
      })
  ```

**Betroffene Dateien:**

- Pi: `/home/docucontrol/docupi/app.py`

---

### Schritt 5: `POST /api/print/<int:pid>` in app.py hinzufügen

Verbindet Protokoll-ID mit Druckauftrag. Dashboard ruft diesen mit der Zeilen-ID auf.

**Aktionen:**

- Route einfügen (nach `/api/printer/ready`):
  ```python
  @app.route("/api/print/<int:pid>", methods=["POST"])
  def api_print_by_id(pid):
      db = get_db()
      row = db.execute(
          "SELECT pdf_path, pdf_filename FROM protocols WHERE id=?", (pid,)
      ).fetchone()
      if not row or not row["pdf_path"]:
          return jsonify({"success": False, "error": "Kein PDF für dieses Protokoll"})
      if not os.path.exists(row["pdf_path"]):
          return jsonify({"success": False, "error": f"PDF-Datei nicht gefunden: {row['pdf_filename']}"})
      ok, msg, job_id = print_pdf(row["pdf_path"])
      return jsonify({"success": ok, "message": msg, "job_id": job_id})
  ```

**Betroffene Dateien:**

- Pi: `/home/docucontrol/docupi/app.py`

---

### Schritt 6: dashboard.html — Print-Button an Drucker-Status koppeln

JS-Änderungen: `printerReady`-Variable, Initialisierung, Einbindung in `renderTable`.

**Aktionen:**

- Variable am Anfang der IIFE hinzufügen: `var printerReady = false;`
- Funktion `loadPrinterStatus()` hinzufügen:
  ```javascript
  function loadPrinterStatus() {
      fetch('/api/printer/ready')
          .then(function(r) { return r.json(); })
          .then(function(d) {
              printerReady = d.ready;
          }).catch(function() { printerReady = false; });
  }
  ```
- In `renderTable`: Print-Button-HTML abhängig von `printerReady`:
  ```javascript
  // Alt:
  actions += '<button class="icon-btn" title="Drucken" onclick="printPdf(' + p.id + ')">...';
  // Neu:
  if (printerReady) {
      actions += '<button class="icon-btn" title="Drucken" onclick="printPdf(' + p.id + ')">...';
  }
  ```
- `loadPrinterStatus()` im Init-Block aufrufen (zusammen mit `loadStats()`)
- In `setInterval` (30s) ebenfalls `loadPrinterStatus()` aufrufen

**Betroffene Dateien:**

- Pi: `/home/docucontrol/docupi/templates/dashboard.html`
- Lokal: `src/docucontrol/templates/dashboard.html`

---

### Schritt 7: Service neu starten + Validierung

**Aktionen:**

- `sudo systemctl restart docucontrol.service`
- `curl http://localhost:5000/api/printer/ready` — erwartet `{"ready": true, ...}`
- `curl http://localhost:5000/api/printers` — erwartet Epson in der Liste
- Dashboard im Browser: Print-Button sichtbar
- `POST /api/print/1` via curl: Druckauftrag absenden
- `lpstat -p` — Job-Status prüfen

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- `app.py` importiert `print_manager.py` — Pfad-Fix muss vor Service-Neustart sein
- `dashboard.html` → `/api/printer/ready` + `/api/print/<id>` — beide neuen Routen
- `data/print_config.json` — liegt bereits am richtigen Ort, Pfad-Bug betrifft nur das Lesen

### Nötige Updates für Konsistenz

- `CLAUDE.md` nach Abschluss: Drucker-Status und Print-Workflow dokumentieren
- `context/current-data.md`: Drucker-Status aktualisieren

### Auswirkungen auf bestehende Workflows

- `auto_print_pdf()` in tcp_print_capture.py funktioniert nach Fix sofort — wird nach jedem
  TCP-Capture aufgerufen, wenn `auto_print: true` in config gesetzt ist
- Bestehende Routes `/api/print` (POST mit Body), `/api/print/test` bleiben unverändert

---

## Validierungs-Checkliste

- [ ] `systemctl is-active cups` → `active`
- [ ] `lpstat -p` zeigt `DocuPrinter` im Status `bereit`
- [ ] `curl http://localhost:5000/api/printer/ready` → `{"ready": true, ...}`
- [ ] Dashboard lädt: Print-Button in Tabellenzeilen sichtbar
- [ ] `POST /api/print/1` via curl gibt `{"success": true, ...}` zurück
- [ ] Drucker gibt Seite aus (oder Testseite via `lp -d DocuPrinter`)
- [ ] Bei deaktiviertem Drucker (Drucker aus): Print-Button verschwindet nach 30s Refresh
- [ ] `auto_print` in Settings-Tab aktivierbar und schaltet auto_print_pdf ein

---

## Erfolgskriterien

Die Implementierung ist abgeschlossen, wenn:

1. Epson XP-4150 druckt eine PDF-Seite wenn der Print-Button in der Dashboard-Tabelle geklickt wird
2. Der Print-Button erscheint nur wenn `GET /api/printer/ready` `ready: true` zurückgibt
3. `auto_print` im Einstellungen-Tab aktivierbar und druckt automatisch nach jedem neuen TCP-Protokoll

---

## Notizen

- Epson XP-4150 ist ein Consumer-Tintenstrahldrucker — für Tierlabor-Einsatz ist ein
  Laserdrucker langfristig robuster (kein Tintenverstopfen bei seltener Nutzung)
- CUPS läuft auf Port 631 (Web-Admin-Interface) — nicht von außen erreichbar (nftables)
- Falls driverless nicht funktioniert: `sudo apt-get install printer-driver-escpr` für Epson-ESC/P-Treiber
- `auto_print` nach Tierlabor-Einrichtung aktivieren sobald Maschinentyp und Druckbedarf bekannt

---

## Implementierungsnotizen

**Implementiert:** 2026-06-03

### Zusammenfassung

- CUPS + cups-client installiert, Service aktiv, `docucontrol` in `lp` + `lpadmin` Gruppen
- Epson XP-4150 als `DocuPrinter` via IPP Everywhere (driverless) eingerichtet: `ipps://EPSON41D474.local:631/ipp/print`
- `print_manager.py` Pfad-Bug lokal gefixt (Pi war bereits korrekt)
- `GET /api/printer/ready` und `POST /api/print/<int:pid>` in app.py hinzugefügt
- `dashboard.html` (Pi + lokal): Print-Button nur wenn `printerReady === true`
- Testdruck Job #1 erfolgreich: `{"success": true, "message": "Druckauftrag #1 an DocuPrinter"}`

### Abweichungen vom Plan

1. **`accepting`-Flag**: pycups liest `printer-is-accepting-jobs` falsch (liefert `false` obwohl CUPS "accepting requests" meldet). Fix: `ready = p['state'] in (3, 4)` statt `state == 3 and accepting`.
2. **Drucker-URI**: Driverless löst auf `ipps://EPSON41D474.local:631/ipp/print` (mDNS-Hostname) statt des direkten USB-URI — funktioniert korrekt via Netzwerk-IPP.

### Aufgetretene Probleme

1. **pycups `accepting: false` Bug**: CUPS selbst meldet korrekt, pycups-Attribut stimmte nicht überein. Gelöst durch Entfernen der `accepting`-Bedingung aus dem Ready-Check.
