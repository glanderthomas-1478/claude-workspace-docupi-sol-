# Plan: Chargenseite umbauen — Flaschen-Scan + IR-Temperaturmessung für SOL

**Erstellt:** 2026-07-07
**Status:** Implementiert
**Anforderung:** Die "Chargen"-Seite (bisher Sterilisator-Chargenprotokolle) durch einen Barcode/QR-Scan-Workflow mit IR-Temperaturmessung für bis zu 160 Sauerstoffflaschen pro Charge ersetzen, orientiert am realen Prozess von SOL Deutschland GmbH (Referenzmaterial: Temperaturprotokoll IF.103A + Verfahrensanweisung PR.128.07.9)

---

## Überblick

### Was dieser Plan erreicht

Die aktuell wiederverwendete "Chargen"-Seite (zeigt Sterilisator-Chargenprotokolle aus einem TCP/9100-Empfang) wird durch einen neuen Workflow ersetzt, der den echten SOL-Prozess abbildet: Ein Techniker startet eine Charge, scannt nacheinander bis zu 160 Sauerstoffflaschen per USB-HID-Scanner (Barcode Code128 oder QR-Code), erfasst pro Flasche eine IR-Temperaturmessung, und schließt die Charge mit Abfüller-/LQK-Bestätigung ab. Daraus wird ein PDF-Temperaturprotokoll generiert, das dem echten Papierformular (IF.103A) strukturell entspricht.

### Warum das wichtig ist

Das ist der Kern des SOL-Projekts: Die bisherige Chargenseite ist 1:1 aus dem Herkunftsprojekt (Sterilisator-Dokumentation) übernommen und hat mit dem eigentlichen SOL-Anwendungsfall (Sauerstoffflaschen-Abfüllung) nichts zu tun außer der wiederverwendeten Web-Oberfläche. Erst mit diesem Umbau wird aus dem Fork ein tatsächlich nutzbares Werkzeug für SOL Deutschland GmbH — die restliche Infrastruktur (Kiosk, LUKS/Dongle-Absicherung, Dashboard-Grundgerüst, Drucker/USB-Sync) steht bereits.

---

## Aktueller Zustand

### Relevante bestehende Struktur

- `src/docucontrol/database.py` — SQLite-Schema: `protocols` (eine Zeile pro Sterilisator-Chargenprotokoll, `raw_data`-Textblob wird per Regex geparst), `charge_forms` (Autoklavenbuch-Formular: `form_data_json`, `confirmed_by`, `confirmed_initials`, `preselected_program`), `system_log`. Funktionen für den Autoklavenbuch-Workflow: `get_pending_protocols()`, `save_form_draft()`, `confirm_form()`, `discard_pending()`, `get_form_confirmed_protocols()`.
- `src/docucontrol/app.py`:
  - `_extract_protocol_fields()` (~Zeile 2020-2093) — parst `raw_data` in Anzeige-Felder (Programm, Dauer, Status)
  - `GET /api/protocols`, `GET /api/protocols/programs`, `GET /api/dashboard/stats` — Chargenliste + Statistik-Karten
  - `GET/POST /api/pending-charges*` (~Zeile 2261-2380) — kompletter Autoklavenbuch-Workflow: Charge kommt als `pending_form` rein, Techniker füllt Formular aus (`confirmed_by`, `confirmed_initials`, `result`), bestätigt, PDF wird asynchron generiert (`_finalize_charge_pdf`), SocketIO-Events (`new_pending_charge`, `charge_completed`, `charge_pdf_error`) halten die UI live aktuell
- `src/docucontrol/tcp_print_capture.py` — TCP/9100-Listener, parst Sterilisator-Rohprotokoll, legt bei erkanntem PST-Format (Uniklinik-Essen-Variante) einen `pending_form`-Eintrag an; `_finalize_charge_pdf()` ruft `pdf_generator.generate_pdf()` auf und stößt USB-/Netzwerk-Sofortkopie + Auto-Print an
- `src/docucontrol/pdf_generator.py` — `generate_pdf(raw_data, protocol_id, timestamp, config, form_data=None)`, `build_filename()`, `build_subfolder()` — komplett auf das Parsen von Sterilisator-Rohtext zugeschnitten, `config["pdf"]["notfall_rows"] = 18` (bereits vorhandene Paginierungs-Konvention: 18 Zeilen/Seite für handschriftliche Notfall-Einträge — deckt sich zufällig mit der Zeilenzahl pro Seite im echten SOL-Papierformular)
- `src/docucontrol/protocol_parser.py` — PST-Format-Parser (Uniklinik Essen), `preselect_autoclave_program()`
- `src/docucontrol/templates/dashboard.html` — Seitenkopf "Chargenprotokolle", `pending-section`-Karte (Ausstehende Dokumentation), Machine-Bar, Stat-Karten (Chargen gesamt/heute/Monat), Filterleiste, Datentabelle
- `src/docucontrol/templates/settings.html` — "Anlage"-Karte mit `set-row`-Pattern (Label+Beschreibung links, Input+Button rechts), `.locked-card` fürs Service-Dongle-Gate
- `src/docucontrol/static/docucontrol.css` — Design-System (Karten, `.set-row`, `.stat`, `.badge`, `.pending-item` etc.)
- `context/current-data.md` — Barcode-Scanner-Anbindung ist **bestätigt: USB-HID/Tastatur-Emulation**. Temperatursensor-Hardware ist **noch offen**.
- `reference/screenshots/Bilder SOL Daten/` — 6 Fotos: 3x Temperaturprotokoll IF.103A (echtes SOL-Formular), 3x Verfahrensanweisung PR.128.07.9 (Chargennummern-Systematik)

### Lücken oder Probleme, die adressiert werden

- Die Chargenseite zeigt Sterilisator-spezifische Daten (Programm, Dauer, Belimed-Maschine), die für SOL irrelevant sind
- Es gibt keinen Weg, eine Charge aus mehreren Einzelmessungen (bis zu 160 Flaschen) zusammenzusetzen — das aktuelle Datenmodell ist "eine Zeile = eine Charge" (aus einem einzelnen Text-Rohprotokoll geparst), SOL braucht "eine Charge = viele Flaschen-Einzelmessungen"
- Es gibt keinen Barcode/QR-Scan-Eingabe-Workflow (der TCP/9100-Empfang ist für SOL komplett irrelevant, da keine Maschine Daten sendet — der Techniker scannt manuell)
- Die PDF-Struktur (`pdf_generator.py`) kann keine Flaschen-Liste mit Einzelmessungen abbilden
- Keine SOL-spezifischen Einstellungen (Chargen-Präfix, Sensor-Namen, Toleranzgrenze für OK/NOK)

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

- Neues Datenbank-Schema (`sol_charges` + `sol_bottles`) parallel zu den bestehenden Sterilisator-Tabellen (diese bleiben unangetastet als Referenz/totes Gleis, werden nicht gelöscht)
- Neuer Scan-Workflow: Charge starten → Flaschen nacheinander scannen (Barcode/QR per USB-HID) + Temperatur erfassen → Charge abschließen (Abfüller + LQK) → PDF wird generiert
- Neue Chargenübersicht (ersetzt die bisherige Sterilisator-Tabelle auf der Dashboard-Seite)
- Neue Live-Scan-Seite für die laufende Charge
- Neuer PDF-Generator, der die Struktur von IF.103A nachbildet
- Neue SOL-Einstellungen (Sensor-Namen, Standort-Kürzel, OK/NOK-Toleranz) in `settings.html`
- Der bestehende TCP/9100-Listener (`tcp_print_capture.py`) wird beim App-Start **nicht mehr automatisch gestartet** (SOL hat keine Maschine, die darauf sendet) — Code bleibt erhalten, wird aber nicht mehr aufgerufen

### Neue Dateien erstellen

| Dateipfad                                         | Zweck                                                                 |
| -------------------------------------------------- | ---------------------------------------------------------------------- |
| `src/docucontrol/sol_pdf_generator.py`             | PDF-Generierung für SOL-Temperaturprotokoll (Layout wie IF.103A), analog zu `wd_pdf_generator.py` |
| `src/docucontrol/templates/sol_charge_scan.html`   | Vollbild-Scan-Seite für eine laufende Charge (Barcode-Eingabe, Live-Liste, Temperatur-Erfassung, Abschluss-Dialog) |
| `src/docucontrol/templates/sol_charge_detail.html` | Detailansicht einer abgeschlossenen Charge (alle Flaschen, PDF-Link, Druck) — optional, kann in Schritt 8 ggf. mit `sol_charge_scan.html` zusammengelegt werden (nur-Lese-Modus) |

### Zu ändernde Dateien

| Dateipfad                                    | Änderungen                                                                                     |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `src/docucontrol/database.py`                | Neue Tabellen `sol_charges`, `sol_bottles` + CRUD-Funktionen (siehe Schritt 1)                  |
| `src/docucontrol/config.py`                  | Neue Config-Sektion `sol` (Sensor-Namen, Toleranzwert, Standort-Kürzel, Anzahl-Warnschwelle)    |
| `src/docucontrol/app.py`                     | Neue Routen unter `/api/sol/charges*` (siehe Schritt 3), Dashboard-Route liefert SOL-Daten statt Sterilisator-Daten, TCP-Listener-Start auskommentieren/entfernen |
| `src/docucontrol/templates/dashboard.html`   | Seitenkopf, Stat-Karten und Tabelle auf SOL-Chargen umstellen; "Ausstehende Dokumentation"-Karte durch "Offene Charge fortsetzen"-Hinweis ersetzen; "Neue Charge starten"-Button ergänzen |
| `src/docucontrol/templates/settings.html`    | Neue Karte "Sauerstoffflaschen-Abfüllung" (Sensor-Namen, Toleranzgrenze, Standort-Kürzel)       |
| `src/docucontrol/static/docucontrol.css`     | Neue Klassen für die Scan-Seite (großes Scan-Eingabefeld, Flaschen-Live-Liste, OK/NOK-Badges) — Rest wiederverwenden |

### Zu löschende Dateien

Keine. `pdf_generator.py`, `protocol_parser.py`, `tcp_print_capture.py`, `wd_*` bleiben als Referenz erhalten (bereits so in `CLAUDE.md` dokumentiert: "nicht übertragbar / muss neu gebaut werden", nicht "löschen").

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **Neue, eigene DB-Tabellen statt Wiederverwendung von `protocols`/`charge_forms`**: Das Sterilisator-Schema ist auf "eine Zeile = ein geparster Text-Rohprotokoll" ausgelegt. SOL braucht "eine Charge = N Einzelmessungen" — eine echte 1:n-Beziehung. Eine saubere neue Tabellenstruktur ist verständlicher und robuster als das bestehende Schema zu verbiegen.
2. **Charge-Nummer wird vom Techniker eingegeben/gescannt, nicht vom System generiert**: Das Referenzformular zeigt ein bereits ausgefülltes `Charge:`-Feld (z.B. `G750010726X000547D`) — die Chargennummer kommt bei SOL aus dem vorgelagerten RAMSES-System (siehe PR.128.07.9). Dieses Kiosk-Tool ist nicht an RAMSES angebunden; es wäre falsch, eine eigene RAMSES-artige Nummer zu erfinden. Stattdessen: Freitextfeld beim Charge-Start, das auch per Scan befüllt werden kann (falls die Chargennummer selbst als Barcode auf einem Arbeitsschein vorliegt).
3. **Temperatur wird zunächst manuell erfasst**: Laut `context/current-data.md` ist die Temperatursensor-Hardware noch nicht entschieden. Die Testo-Geräte aus dem Referenzformular (835-T1, 608-H1) haben keine bekannte, bereits integrierte Schnittstelle. Der Workflow wird so gebaut, dass nach jedem Barcode-Scan ein Temperatur-Eingabefeld automatisch fokussiert wird (schneller Tastatur-Workflow: scannen → Temp tippen → Enter → nächster Scan). Sobald ein Sensor mit digitaler Schnittstelle feststeht, kann das Eingabefeld leicht durch eine automatische Befüllung ersetzt werden (Datenmodell ändert sich dadurch nicht).
4. **Neuer, eigener PDF-Generator (`sol_pdf_generator.py`) statt Erweiterung von `pdf_generator.py`**: Folgt der bestehenden Konvention (`wd_pdf_generator.py` für das WD/RDG-Format). `generate_pdf()` in `pdf_generator.py` ist untrennbar mit dem Text-Parsing verwoben; ein sauberer neuer Generator ist wartbarer.
5. **Bestehende Tabellen/Module bleiben unangetastet**: Kein Löschen von Sterilisator-Code — er dient als Referenz und könnte für ein anderes Projekt wieder gebraucht werden (siehe `CLAUDE.md`-Konvention).
6. **Kein Diagramm im PDF**: Das echte Papierformular zeigt nur eine Tabelle, kein Diagramm. Kein `sol_chart_generator.py` in diesem Plan — vermeidet Scope über das tatsächlich Gebrauchte hinaus.
7. **18 Zeilen pro PDF-Seite**: Deckt sich mit der bereits vorhandenen `notfall_rows`-Konvention und mit der Zeilenzahl pro Seite im echten Referenzformular.

### Betrachtete Alternativen

- **`protocols`-Tabelle um SOL-Felder erweitern**: Verworfen, da das 1:n-Verhältnis (Charge → viele Flaschen) nicht sauber in eine einzelne Zeile passt, ohne JSON-Blobs zu missbrauchen.
- **Eigene Chargennummern-Generierung nach RAMSES-Schema**: Verworfen (siehe Entscheidung 2) — ohne echte RAMSES-Anbindung wäre das geraten und potenziell irreführend für ein Qualitätsdokument.
- **Diagramm im PDF ergänzen**: Verworfen (siehe Entscheidung 6) — nicht Teil des echten Formulars, wäre ungefragte Zusatzarbeit.

### Offene Fragen

Diese Punkte sollten vor oder während `/implement` mit dem User geklärt werden — die Implementierung kann mit sinnvollen Platzhaltern starten, aber folgende Punkte sind sicherheits-/qualitätsrelevant und aktuell nicht zweifelsfrei aus dem Referenzmaterial ablesbar:

1. ~~**OK/NOK-Toleranzkriterium**~~ — **GEKLÄRT (2026-07-08, User-Bestätigung):** Nach dem Scannen des Chargen-Barcodes wird eine **Referenztemperatur**-Messung durchgeführt (nicht einfach "Raumtemperatur" — Bezeichnung im UI/PDF entsprechend angepasst). Formel bestätigt: Differenz IR-Temp minus Referenztemp. **> 5°C = OK, < 5°C = NOK**. Deckt sich exakt mit der bereits implementierten Logik (`_sol_is_nok()` in `app.py`), Toleranzwert bleibt konfigurierbar (Default 5.0°C).
2. **Barcode-Inhalt der Flasche**: Enthält der Flaschen-Barcode eine reine Seriennummer, oder ist er strukturiert (z.B. inkl. Flaschengröße/Produkt)? Bestimmt, ob wir den Scan-Wert 1:1 speichern (aktueller Plan) oder parsen müssen.
3. **Chargennummer-Eingabe**: Wird die Chargennummer selbst gescannt (Barcode auf einem Arbeitsschein) oder von Hand eingetippt? Beeinflusst nur die UI-Beschriftung, nicht die Datenstruktur — aktueller Plan unterstützt beides (Freitextfeld mit Scan-Fokus).
4. **Maximalzahl 160**: Ist das eine harte Grenze (Charge kann nicht mehr als 160 Flaschen haben) oder eine übliche Obergrenze (Warnung, aber kein Stopp)? Aktueller Plan: weiche Warnung ab 160, kein hartes Limit.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: Datenbank-Schema erweitern

Neue Tabellen für Chargen und Flaschen-Einzelmessungen in `database.py` ergänzen, analog zur bestehenden `AUTOKLAVENBUCH WORKFLOW`-Sektion (eigener klar kommentierter Block, keine Änderung an `protocols`/`charge_forms`).

**Aktionen:**

- Neue Sektion `# SOL CHARGEN-WORKFLOW — Flaschen-Scan` in `database.py` ergänzen (nach der Autoklavenbuch-Sektion)
- Tabelle `sol_charges`: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `charge_nr TEXT NOT NULL`, `started_at TEXT NOT NULL`, `closed_at TEXT DEFAULT NULL`, `room_temp REAL DEFAULT NULL`, `sensor_names TEXT DEFAULT ''`, `operator_name TEXT DEFAULT ''`, `lqk_name TEXT DEFAULT ''`, `lqk_initials TEXT DEFAULT ''`, `status TEXT DEFAULT 'open'` (`open` / `completed`), `pdf_path TEXT DEFAULT ''`, `pdf_filename TEXT DEFAULT ''`, `file_size INTEGER DEFAULT 0`
- Tabelle `sol_bottles`: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `charge_id INTEGER NOT NULL`, `seq_nr INTEGER NOT NULL`, `scan_code TEXT NOT NULL`, `scanned_at TEXT NOT NULL`, `ir_temp REAL DEFAULT NULL`, `is_nok INTEGER DEFAULT 0`, `FOREIGN KEY (charge_id) REFERENCES sol_charges(id) ON DELETE CASCADE`
- Indizes: `idx_sol_charges_status`, `idx_sol_charges_started`, `idx_sol_bottles_charge`
- Funktionen ergänzen (Signaturen, Verhalten):
  - `create_sol_charge(charge_nr, room_temp, sensor_names, operator_name) -> charge_id`
  - `get_open_sol_charge()` — die aktuell offene Charge (falls vorhanden; nur eine gleichzeitig offene Charge zulassen)
  - `add_sol_bottle(charge_id, scan_code, ir_temp, is_nok) -> bottle_id` (setzt `seq_nr` automatisch = `COUNT(*) + 1` für diese Charge)
  - `delete_sol_bottle(bottle_id)` (Korrektur eines Fehlscans, `seq_nr` der übrigen Zeilen NICHT neu nummerieren — Protokoll-Nr. bleibt lückenhaft nachvollziehbar, wie im echten Formular üblich bei Streichungen)
  - `get_sol_charge(charge_id)` mit allen `sol_bottles`-Zeilen (JOIN oder zwei Queries)
  - `close_sol_charge(charge_id, lqk_name, lqk_initials, pdf_path, pdf_filename, file_size)` — setzt `status='completed'`, `closed_at=now()`
  - `list_sol_charges(limit, offset, status_filter=None)` — für die Übersichtstabelle
  - `count_sol_charges(status_filter=None)`, `get_sol_charges_today_count()`

**Betroffene Dateien:**

- `src/docucontrol/database.py`

---

### Schritt 2: Config-Sektion für SOL-Einstellungen

**Aktionen:**

- In `config.py` `DEFAULT_CONFIG` neue Sektion `"sol"` ergänzen:
  ```python
  "sol": {
      "sensor_names": "Testo 835-T1 / Testo 608-H1",
      "temp_tolerance_c": 5.0,
      "bottle_warn_count": 160,
      "standort_kuerzel": "",
  }
  ```

**Betroffene Dateien:**

- `src/docucontrol/config.py`

---

### Schritt 3: API-Routen für den Charge-Scan-Workflow

Neue Routen-Sektion in `app.py`, analog zur bestehenden `AUTOKLAVENBUCH WORKFLOW`-Sektion. Alle datenverändernden Routen (Charge starten/abschließen, Flasche löschen) durchlaufen `_require_service()` — Konsistenz mit dem bereits etablierten Dongle-Gate (Bearbeiten braucht den Service-Dongle, reines Scannen/Anzeigen einer offenen Charge ebenfalls, da es Dateneingabe ist).

**Aktionen:**

- `POST /api/sol/charges` — startet neue Charge (`charge_nr`, `room_temp`, `sensor_names`, `operator_name` im Body); lehnt ab (409), falls bereits eine offene Charge existiert
- `GET /api/sol/charges/open` — liefert die aktuell offene Charge inkl. aller bisherigen Flaschen (für Reload der Scan-Seite ohne Datenverlust)
- `POST /api/sol/charges/<id>/bottles` — fügt eine Flaschen-Messung hinzu (`scan_code`, `ir_temp` im Body), berechnet `is_nok` serverseitig anhand `config["sol"]["temp_tolerance_c"]` und `room_temp` der Charge, gibt die neue Zeile inkl. `is_nok`+`seq_nr` zurück
- `DELETE /api/sol/charges/<id>/bottles/<bottle_id>` — löscht eine fehlerhafte Scan-Zeile
- `POST /api/sol/charges/<id>/close` — Pflichtfelder `lqk_name`, `lqk_initials`; ruft `sol_pdf_generator.generate_sol_pdf()` auf, aktualisiert DB, stößt USB-/Netzwerk-Sofortkopie an (bestehende Funktionen aus `storage_manager.py`/`network_storage_manager.py` wiederverwenden), optional Auto-Print (bestehende `print_manager.py`-Funktion wiederverwenden)
- `GET /api/sol/charges` — paginierte Liste für die Dashboard-Tabelle (Query-Parameter analog zu `/api/protocols`: `page`, `per_page`, `status`, `date_from`, `date_to`)
- `GET /api/sol/charges/<id>` — Detailansicht (alle Flaschen)
- `GET /api/sol/charges/stats` — ersetzt/ergänzt `/api/dashboard/stats` mit SOL-Zahlen (Chargen gesamt, heute, dieser Monat, letzte Charge)
- SocketIO-Events ergänzen: `sol_bottle_added` (Live-Update falls Charge auf einem zweiten Bildschirm mitverfolgt wird — optional, kann entfallen falls nur ein Bildschirm genutzt wird)
- Bestehenden TCP/9100-Listener-Start (Suche nach `start_capture_server` bzw. Aufrufstelle in `app.py`) auskommentieren mit Kommentar, warum (SOL hat keine sendende Maschine)

**Betroffene Dateien:**

- `src/docucontrol/app.py`

---

### Schritt 4: PDF-Generator für das SOL-Temperaturprotokoll

Neues Modul, das die Struktur von IF.103A nachbildet.

**Aktionen:**

- `sol_pdf_generator.py` anlegen mit `generate_sol_pdf(charge, bottles, config) -> (pdf_path, pdf_filename, file_size)`
- Kopfbereich: Firma/Anlage (aus `config["pdf"]["header_text"]`-artigem Feld oder neuem `config["sol"]`-Feld), "Temperaturprotokoll", Charge-Nr., Abfüller-Name, LQK-Name/Kürzel, Raumtemperatur, verwendete Fühler, Anzahl Messung Flaschen
- Tabellenbereich: Spalten `Protokoll Nr.` / `Datum/Uhrzeit` / `IR Temp [°C]`, 18 Zeilen pro Seite (Konvention aus `notfall_rows` übernehmen), NOK-Zeilen optisch hervorheben (z.B. rote Schrift/Hintergrund, passend zum bestehenden `has_fault`-Rot-Muster aus dem Sterilisator-PDF)
- Fußbereich letzte Seite: `Min (gesamt)` und `Max (gesamt)`, Anzahl OK/NOK
- `build_sol_filename()` analog zu `build_filename()`: Pattern z.B. `{datum}_{zeit}_SOL_{charge}.pdf`
- Seitenformat/Font-Size aus bestehendem `config["pdf"]` wiederverwenden (`page_format`, `font_size`) für Konsistenz mit dem restlichen System

**Betroffene Dateien:**

- `src/docucontrol/sol_pdf_generator.py` (neu)

---

### Schritt 5: Scan-Seite (Frontend)

Neue Vollbild-Seite für die laufende Charge — das zentrale Arbeitswerkzeug für den Techniker am Kiosk.

**Aktionen:**

- `templates/sol_charge_scan.html` anlegen (extends `base.html`)
- Zustand "keine offene Charge": Formular "Charge starten" (Charge-Nr. Eingabefeld mit Scan-Fokus, Raumtemperatur, Abfüller-Name, Sensor-Namen vorausgefüllt aus Settings)
- Zustand "Charge läuft":
  - Kopfbereich: Charge-Nr., Start-Zeit, Raumtemperatur, Zähler "X Flaschen erfasst" (Warnhinweis ab `config["sol"]["bottle_warn_count"]`)
  - Großes, permanent fokussiertes Eingabefeld "Flasche scannen" (nimmt Enter-terminierte USB-HID-Scanner-Eingabe entgegen)
  - Nach jedem Scan: Temperatur-Eingabefeld erscheint/fokussiert automatisch, Enter bestätigt und fügt die Zeile per `POST .../bottles` hinzu, Fokus springt zurück auf das Scan-Feld
  - Live-Tabelle aller bisher gescannten Flaschen dieser Charge (neueste oben oder unten — Konsistenz mit bestehenden Tabellen prüfen), OK/NOK-Badge pro Zeile (wiederverwendet `.badge`-Klassen aus `docucontrol.css`), Lösch-Icon pro Zeile für Korrektur
  - Duplikat-Warnung (Toast), falls derselbe `scan_code` innerhalb der offenen Charge erneut gescannt wird (kein automatisches Verwerfen, nur Hinweis — Techniker entscheidet)
  - Button "Charge abschließen" → Modal mit Pflichtfeldern LQK-Name + LQK-Kürzel (Pattern wie das bestehende Autoklavenbuch-Confirm-Modal), nach Bestätigung: `POST .../close`, danach Redirect/Anzeige des PDF-Links
- Beim Laden der Seite: `GET /api/sol/charges/open` aufrufen, um nach einem Reload nahtlos weiterzumachen (kein Datenverlust bei Browser-Refresh)

**Betroffene Dateien:**

- `src/docucontrol/templates/sol_charge_scan.html` (neu)
- `src/docucontrol/static/docucontrol.css` (neue Klassen: großes Scan-Eingabefeld, Live-Tabelle, Zähler-Badge)

---

### Schritt 6: Dashboard-Seite umbauen

**Aktionen:**

- `page-head`-Titel/Untertitel von "Chargenprotokolle" / "Gespeicherte Sterilisations-Chargen" auf SOL-Wortlaut umstellen (z.B. "Sauerstoffflaschen-Chargen")
- `pending-section`-Karte ("Ausstehende Dokumentation") ersetzen durch: falls `GET /api/sol/charges/open` eine offene Charge liefert, prominenten Hinweis/Button "Charge läuft — X Flaschen erfasst, weiter scannen" anzeigen, der zu `sol_charge_scan.html` verlinkt
- "Neue Charge starten"-Button ergänzen (verlinkt auf `sol_charge_scan.html`, dort greift der "Charge starten"-Zustand)
- `machine-bar` entfernen oder auf SOL-Kontext umstellen (Belimed-Maschinen-Anzeige ergibt für SOL keinen Sinn) — je nach Entscheidung im Zuge dieses Schritts ggf. ganz entfernen, da SOL keine "Maschine" im bisherigen Sinne hat
- Stat-Karten auf `GET /api/sol/charges/stats` umstellen (Chargen gesamt/heute/Monat)
- Datentabelle: Spalten `Charge-Nr.` / `Datum` / `Anzahl Flaschen` / `Davon NOK` / `Abfüller` / `Status` / PDF-Download-Icon, Datenquelle `GET /api/sol/charges`
- Filterleiste anpassen (Status Offen/Abgeschlossen statt Bestanden/Störung/Wartet auf Formular, Datum-Range behalten, Programm-Filter entfernen)

**Betroffene Dateien:**

- `src/docucontrol/templates/dashboard.html`

---

### Schritt 7: Settings-Karte für SOL-Einstellungen

**Aktionen:**

- Neue `.card.locked-card` in `settings.html` (Tab "Geräte & Netzwerk" oder neuer Tab "Abfüllung", je nachdem was zum bestehenden Subtab-Muster passt) mit `set-row`-Zeilen:
  - Sensor-Namen (Freitext, Default aus `config["sol"]["sensor_names"]`)
  - Temperatur-Toleranz °C (Zahleneingabe, Default `5.0` — mit Hinweistext, dass dies vorläufig ist, siehe offene Frage 1)
  - Warnschwelle Flaschenanzahl (Zahleneingabe, Default `160`)
  - Standort-Kürzel (Freitext, für Anzeige im PDF-Kopf)
- Speichern-Button analog zum bestehenden `saveMachineConfig()`-Muster, neue API-Route `POST /api/sol/config` (oder in bestehende Konfig-Speicherroute integrieren, falls es eine generische gibt — prüfen)

**Betroffene Dateien:**

- `src/docucontrol/templates/settings.html`
- `src/docucontrol/app.py` (Config-Speicher-Route)

---

### Schritt 8: TCP/9100-Listener deaktivieren, App-Start bereinigen

**Aktionen:**

- Aufrufstelle des TCP/9100-Capture-Servers in `app.py` (Suche `start_capture_server`) auskommentieren, mit Kommentar `# SOL hat keine sendende Maschine — TCP/9100-Empfang bleibt Code-Referenz, wird nicht gestartet`
- Prüfen, ob `receiver = SerialReceiver(...)` (RS232-Empfänger, ganz oben in `app.py`) ebenfalls beim Start aktiv wird und ob das für SOL Ressourcen bindet oder Fehler wirft — falls ja, ebenfalls deaktivieren
- Kurzer Neustart-Test des Containers, um sicherzustellen, dass das Deaktivieren keine Folgefehler wirft (andere Module könnten `receiver`/Capture-Status abfragen)

**Betroffene Dateien:**

- `src/docucontrol/app.py`

---

### Schritt 9: Deployment + Live-Test auf dem SOL-Pi

**Aktionen:**

- Geänderte/neue Dateien per `scp` auf `/home/docucontrol/docupi/` kopieren (bestehendes Vorgehen aus dieser Session)
- `docker-compose up -d --force-recreate` (bei Bedarf, z.B. falls neue Python-Abhängigkeiten nötig werden — aktuell nicht absehbar, reine stdlib/`reportlab`/`fpdf2` bereits vorhanden)
- Test-Sequenz (mit gestecktem Service-Dongle, da Schreibaktionen jetzt dongle-gated sind):
  1. Neue Charge starten mit Test-Chargennummer
  2. 3-5 Test-"Flaschen" scannen (Barcode-Scanner oder manuelle Eingabe simulieren), Temperaturen eintragen, mindestens eine bewusst außerhalb der Toleranz für NOK-Test
  3. Fehlerhafte Zeile löschen, prüfen dass Zähler korrekt bleibt
  4. Charge abschließen, PDF prüfen (Layout, NOK-Hervorhebung, Fußzeile Min/Max)
  5. Dashboard-Liste + Stat-Karten prüfen
  6. Reload der Scan-Seite während einer offenen Charge testen (Datenverlust-Check)
- Ergebnisse in `context/current-data.md` dokumentieren

**Betroffene Dateien:**

- Keine (Deployment-/Testschritt)

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- `templates/base.html` — Navigation (`Chargen`-Tab-Link bleibt bestehen, zeigt aber jetzt SOL statt Sterilisator-Übersicht)
- `storage_manager.py`, `network_storage_manager.py` — USB-/Netzwerk-Sofortkopie-Funktionen werden für SOL-PDFs wiederverwendet (gleiche Funktionssignatur wie bisher, kein Bug erwarten — die USB-Dongle-Ausschluss-Logik aus dem Service-Dongle-Feature bleibt unberührt, da sie geräteseitig, nicht dateiseitig filtert)
- `print_manager.py` — Auto-Print-Funktion wird für SOL-PDFs wiederverwendet
- `CLAUDE.md` / `context/current-data.md` — nach Abschluss aktualisieren (SOL-Chargenseite implementiert, TCP-Listener deaktiviert)

### Nötige Updates für Konsistenz

- `CLAUDE.md`: Abschnitt "Wiederverwendete Architektur aus DocuControl" / "Nicht übertragbar" aktualisieren — TCP/9100-Pipeline ist jetzt formal deaktiviert (nicht nur "muss neu gebaut werden", sondern faktisch durch den SOL-Workflow ersetzt)
- `context/current-data.md`: Zeile "Neu zu bauen" durch "Chargenseite umgebaut" ersetzen, offene Punkte (Temperatursensor-Hardware, Barcode-Format der Flaschen) bleiben bestehen, bis geklärt

### Auswirkungen auf bestehende Workflows

- Der komplette Autoklavenbuch-Workflow (`pending_form`/`charge_forms`, docucontrol3-spezifisch) wird durch das Deaktivieren des TCP-Listeners **nicht mehr erreicht** — er bleibt Code-Referenz, ist aber für SOL funktional tot. Das ist beabsichtigt (SOL hat keinen Sterilisator, keine Uniklinik-Essen-Formulare).
- USB-Sync, Netzwerk-Sync, Drucker-Auto-Print funktionieren unverändert weiter, jetzt nur für SOL-PDFs statt Sterilisator-PDFs.
- Das Service-Dongle-Gate (`_require_service()`) gilt unverändert für alle neuen datenverändernden SOL-Routen — kein zusätzlicher Aufwand nötig, das Muster wird einfach auf die neuen Routen angewendet.

---

## Validierungs-Checkliste

- [ ] `sol_charges`/`sol_bottles`-Tabellen werden beim Container-Start ohne Fehler angelegt
- [ ] Charge starten, scannen, Temperatur erfassen, abschließen funktioniert Ende-zu-Ende ohne Dongle-Fehler (Dongle gesteckt)
- [ ] Ohne Dongle: Scan-Seite lässt sich zwar ansehen, aber keine Schreibaktion (Charge starten/Flasche hinzufügen/abschließen) geht durch — `403 "Service-Dongle erforderlich"`
- [ ] PDF wird korrekt generiert, zeigt alle gescannten Flaschen, NOK-Zeilen optisch markiert, Fußzeile mit Min/Max korrekt
- [ ] Bei >18 Flaschen: PDF paginiert korrekt auf mehrere Seiten
- [ ] Dashboard zeigt neue SOL-Chargen in der Liste + korrekte Stat-Karten-Werte
- [ ] Reload der Scan-Seite während offener Charge verliert keine Daten
- [ ] Duplikat-Scan (gleicher Code zweimal in derselben Charge) zeigt Warnung, verhindert aber nicht das Hinzufügen
- [ ] USB-/Netzwerk-Sofortkopie + Auto-Print funktionieren für neue SOL-PDFs wie zuvor für Sterilisator-PDFs
- [ ] TCP/9100-Listener startet nicht mehr beim App-Start (Log-Zeile "TCP/9100 Capture-Server gestartet" fehlt jetzt)
- [ ] `CLAUDE.md` und `context/current-data.md` widerspiegeln den neuen Stand

---

## Erfolgskriterien

Die Implementierung ist abgeschlossen, wenn:

1. Ein Techniker am Kiosk eine komplette Charge (Start → N Flaschen scannen inkl. Temperaturmessung → Abschluss) ohne Rückgriff auf die Kommandozeile durchführen kann
2. Das erzeugte PDF strukturell dem echten SOL-Temperaturprotokoll (IF.103A) entspricht (Kopf-Metadaten, Flaschen-Tabelle, Min/Max-Fußzeile)
3. Die Dashboard-Übersicht ausschließlich SOL-Chargen zeigt, keine Sterilisator-Reste mehr sichtbar sind
4. Alle Schreibaktionen weiterhin korrekt hinter dem Service-Dongle-Gate liegen

---

## Notizen

- Die genaue OK/NOK-Formel (offene Frage 1) ist der wichtigste Punkt, der vor einem echten Produktiveinsatz mit dem User/SOL geklärt werden sollte — falsche Toleranzlogik in einem Qualitätsdokument ist sicherheitsrelevant. Die Implementierung sollte den Grenzwert klar konfigurierbar halten (kein Hardcoding), damit eine spätere Korrektur ohne Code-Änderung möglich ist.
- Sobald die Temperatursensor-Hardware-Entscheidung (siehe `context/current-data.md`) getroffen ist, ist der nächste natürliche Ausbauschritt, das manuelle Temperatur-Eingabefeld durch eine automatische Sensor-Anbindung zu ersetzen — das Datenmodell (`sol_bottles.ir_temp`) muss dafür nicht geändert werden.
- RFID als alternative Flaschen-Identifikation (in den handschriftlichen Notizen erwähnt) ist in diesem Plan nicht berücksichtigt — Barcode/QR ist bereits bestätigt, RFID wäre ein separates, größeres Hardware-Thema (eigener Reader nötig).
- Die 18-Zeilen/Seite-Konvention (`notfall_rows`) ist eine praktische Übernahme aus dem Bestandssystem, keine architektonische Kopplung — kann in `sol_pdf_generator.py` unabhängig angepasst werden, falls das SOL-Layout mehr/weniger Platz pro Zeile braucht.

---

## Implementierungsnotizen

**Implementiert:** 2026-07-07

### Zusammenfassung

Alle 9 Schritte umgesetzt: neue Tabellen `sol_charges`/`sol_bottles` in `database.py` (inkl. CRUD-Funktionen), neue Config-Sektion `sol` in `config.py`, neue Routen `/api/sol/charges*` + `/api/sol/config` + Seiten-Routen (`/sol/scan`, `/sol/download/<id>`, `/sol/view/<id>`) in `app.py`, neues Modul `sol_pdf_generator.py`, neue Scan-Seite `templates/sol_charge_scan.html`, `dashboard.html` komplett auf SOL-Chargen umgebaut, neue Settings-Karte "Sauerstoffflaschen-Abfüllung" in `settings.html`, TCP/9100-Capture-Start in `app.py` deaktiviert. Auf dem SOL-Pi deployed und end-to-end getestet (Charge mit 4 Flaschen inkl. 1 NOK-Fall + 1 Duplikat-Scan, Fehlzeilen-Löschung, Abschluss, PDF-Kontrolle, USB-Sofortkopie, Dashboard-Stats, Reload-Persistenz einer offenen Charge). Testdaten anschließend von SSD und USB-Stick entfernt. `CLAUDE.md` und `context/current-data.md` aktualisiert.

### Abweichungen vom Plan

1. **Service-Dongle-Gate nur auf Settings, nicht auf den Kern-Workflow**: Der Plan sah ursprünglich vor, dass Charge starten/Flasche hinzufügen/löschen/abschließen alle hinter `_require_service()` liegen. Während der Umsetzung bewusst korrigiert: Diese Routen sind die tägliche Kernaufgabe des Geräts (analog zum bestehenden Autoklavenbuch-Workflow, dessen `api_pending_form_save`/`api_pending_form_confirm` ebenfalls nicht gesperrt sind) — eine Dongle-Pflicht dafür hätte den Praxisbetrieb (Linienpersonal ohne Dongle) blockiert. Nur `/api/sol/config` (Einstellungen) ist weiterhin gesperrt.
2. **`rows_per_page` als neuer eigener Config-Wert statt `notfall_rows`-Wiederverwendung**: Beim Schreiben von `sol_pdf_generator.py` festgestellt, dass `config["pdf"]["notfall_rows"]` im Bestandscode nirgends tatsächlich für die PDF-Paginierung ausgelesen wird (nur ein Formularwert ohne Wirkung) — daher stattdessen ein neuer, tatsächlich verdrahteter Wert `config["sol"]["rows_per_page"]` (Default 18) angelegt.
3. **DejaVu-Sans-Unicode-Font statt Helvetica**: Im Live-Test schlug die PDF-Generierung fehl, weil Helvetica (Latin-1-only) beim Gedankenstrich-Zeichen crasht. Gefixt durch Laden von DejaVu Sans (gleiches Muster wie in `pdf_generator.py._draw_autoklavenbuch_page()`), inkl. Safe-Fallback-Sanitizer falls die Schriftdatei einmal fehlen sollte.
4. **`charge_nr`-Textsuche ergänzt**: `list_sol_charges`/`count_sol_charges`/`GET /api/sol/charges` um einen `charge_nr`-Suchparameter (LIKE-Filter) erweitert — im Plan nicht explizit spezifiziert, aber für die Dashboard-Filterleiste nötig, da die Charge-Nr. jetzt Freitext statt Zahl ist.
5. **Machine-Bar entfernt statt umgestellt**: Von den zwei im Plan genannten Optionen ("entfernen oder auf SOL-Kontext umstellen") wurde Entfernen gewählt, da SOL kein Maschinen-/IP-Konzept im bisherigen Sinne hat.
6. **Keine separate Ergänzung in `docucontrol.css`**: Seiten-spezifische Styles der neuen Scan-Seite liegen im `extra_css`-Block des Templates selbst — folgt damit demselben Muster wie das bestehende `dashboard.html` (Print-Toast-Styles waren dort ebenfalls lokal, nicht in der globalen CSS-Datei).

### Aufgetretene Probleme

1. **PDF-Generierung crashte beim ersten Live-Test** (`Character "—" ... outside the range of characters supported by the font "helvetica"`) — behoben durch DejaVu-Sans-Umstellung (siehe Abweichung 3).
2. **LQK-Name/-Kürzel fehlten im ersten generierten Test-PDF**, obwohl korrekt übermittelt: Die `close`-Route holte das Charge-Dict für den PDF-Generator, bevor `close_sol_charge()` die LQK-Felder in der DB speicherte. Gefixt durch Injektion von `lqk_name`/`lqk_initials` ins bereits geladene Dict, bevor `generate_sol_pdf()` aufgerufen wird (`app.py`, `api_sol_charge_close`). Mit einer zweiten Test-Charge erfolgreich nachgetestet.
3. **`sqlite3`-CLI nicht auf dem Pi-Host installiert** (nur im Docker-Image) — Testdaten-Bereinigung der DB stattdessen über `docker exec docupi-docucontrol-1 python3 -c "..."` durchgeführt statt direktem `sqlite3`-Aufruf.
4. **SSH/Deployment zunächst blockiert**, da kein Service-Dongle gesteckt war (erwartetes Verhalten des bestehenden Sicherheitsmodells, keine Anpassung nötig) — nach Einstecken des Dongles durch den User normal fortgesetzt.

### Nachtrag 2026-07-08: Zwei-Scan-Ablauf pro Flasche

Nach Abschluss der ursprünglichen Implementierung stellte der User klar, dass der reale Scan-Vorgang pro Flasche **zwei** Barcodes umfasst, nicht einen: zuerst das Chargen-Etikett (auf jede Flasche der Charge aufgeklebt, Barcode immer identisch), dann der eindeutige Flaschen-Barcode. Das Chargen-Etikett dient als Sicherheits-Check gegen Verwechslung mit einer anderen Charge. Korrigiert:

- `app.py`, `api_sol_bottle_add`: neues Pflichtfeld `charge_barcode`, serverseitig gegen `charge['charge_nr']` geprüft (bei Abweichung `400` mit klarer Fehlermeldung, kein stiller Fallback).
- `sol_charge_scan.html`: Scan-Flow von 2 auf 3 Stufen erweitert (Chargen-Barcode → Flaschen-Code → IR-Temp), mit sofortigem Client-seitigem Abgleich des Chargen-Barcodes für schnelles Feedback plus serverseitiger Validierung als verbindlicher Check.
- Auf dem Pi end-to-end getestet: falscher Chargen-Barcode wird mit `400` abgelehnt, korrekter akzeptiert. Testdaten entfernt.

### Nachtrag 2026-07-08: Referenztemperatur + OK/NOK-Formel final bestätigt

User-Klarstellung: Direkt nach dem Scannen des Chargen-Barcodes wird eine **Referenztemperatur**-Messung durchgeführt (Umbenennung von "Raumtemperatur" in `sol_charge_scan.html`, `sol_pdf_generator.py`, `settings.html`, `app.py`-Fehlermeldungen — der interne DB-/API-Feldname `room_temp` bleibt unveraendert, nur User-sichtbare Labels geaendert). OK/NOK-Formel bestätigt: Differenz IR-Temp minus Referenztemp. > 5°C = OK, < 5°C = NOK — entspricht exakt der bereits implementierten Logik, damit ist die "offene Frage 1" geklärt. Am Toleranz-Grenzfall (exakt 5,0°C Differenz → OK, 4,9°C → NOK, 5,1°C → OK) auf dem Pi verifiziert.

### Nachtrag 2026-07-08 (2): Kompletter Scan-/Abschluss-Ablauf final korrigiert

User-Klarstellung des tatsächlichen Ablaufs widersprach dem vorherigen Nachtrag zum Zwei-Scan-pro-Flasche-Modell und ergänzte einen kompletten Abschluss-Workflow. Umgesetzt:

- **Chargen-Barcode wird nur EINMAL gescannt** (beim Charge-Start, zusammen mit der einmaligen Referenztemperatur-Messung), NICHT mehr pro Flasche — der `charge_barcode`-Sicherheits-Check aus dem vorherigen Nachtrag wurde wieder entfernt (`app.py` `api_sol_bottle_add`, `sol_charge_scan.html` Scan-Flow zurück auf 2 Stufen: Flaschen-Code → IR-Temp).
- **Fehlerton bei NOK**: Web-Audio-API-Doppelpiepton (kein externes Audio-Asset) spielt automatisch, sobald eine übermittelte Messung als NOK erkannt wird.
- **"Nochmal messen"**: Nach einer NOK-Messung erscheint eine Inline-Leiste mit Button, der die zuletzt hinzugefügte (NOK-)Zeile löscht und direkt die Temperatur-Eingabe für denselben Flaschen-Code erneut öffnet, ohne dass der Barcode neu gescannt werden muss. NOK-Werte werden weiterhin normal gespeichert, wenn der Bediener nicht erneut misst — es ist keine Zwangs-Sperre, sondern eine Erleichterung bei vermuteten Fehlmessungen.
- **Bestätigungs-Schritt vor Abschluss**: "Charge abschließen" öffnet jetzt zuerst eine Zusammenfassung (Anzahl Flaschen, davon NOK) mit Pflicht-Checkbox "Ich bestätige, dass ich alle Flaschen korrekt gemessen habe" — Weiter-Button bleibt bis zum Anhaken deaktiviert.
- **Digitale Unterschrift statt LQK-Textfelder**: Die separate LQK-Name/-Kürzel-Eingabe wurde entfernt (User-Entscheidung: nur der Bediener/Abfüller bestätigt und unterschreibt, kein zweiter LQK-Schritt). Neuer, eigenständiger Canvas-Unterschriften-Pad in `sol_charge_scan.html` (Pointer-Events, PNG-Export via `toDataURL`) — bewusst NICHT die bestehende `#sigOverlay`-Komponente aus `base.html` wiederverwendet, da diese eng an den inerten Autoklavenbuch-Flow gekoppelt ist (`abSubmitConfirm`, `sigBack` → `abOverlay`); stattdessen eigenständige Implementierung nach demselben Muster, um das gemeinsam genutzte `base.html` nicht anzufassen.
- **DB-Schema**: neue Spalte `sol_charges.confirmed_signature` (Base64-PNG-Data-URL) per idempotenter Inline-Migration in `init_db()` ergänzt (`PRAGMA table_info` + bedingtes `ALTER TABLE`, da `CREATE TABLE IF NOT EXISTS` bei bereits existierender Tabelle keine neue Spalte mehr anlegt). `close_sol_charge()`-Signatur geändert: `lqk_name`/`lqk_initials` → `confirmed_signature`.
- **PDF**: Fußzeile zeigt jetzt einen Block "Bestätigt korrekt gemessen von (Bediener/Abfüller)" mit eingebettetem Unterschriftsbild (`FPDF.image()` aus dekodierten Base64-PNG-Bytes) statt zweier reiner Textzeilen; die zweite "LQK"-Zeile wurde entfernt.
- **Nicht beschreibbares PDF**: `fpdf2.set_encryption()` mit Owner-Passwort + eingeschränkten `AccessPermission`-Flags (Drucken/Kopieren erlaubt, Bearbeiten/Kommentieren/Formularfelder/Neuzusammenstellen gesperrt) — kein User-Passwort, PDF bleibt ohne Passwort-Eingabe ansehbar. Bewusst als "weicher" Manipulationsschutz dokumentiert (RC4-PDF-Standardschutz ist mit Fremdwerkzeugen umgehbar), nicht als kryptografische Sicherheitsgarantie.
- Auf dem Pi end-to-end getestet: Ein-Scan-Flow ohne charge_barcode, Validierungsfehler bei fehlender Bestätigung/Unterschrift (400), erfolgreicher Abschluss mit echtem (nicht-transparentem) Test-Unterschriftsbild — korrekt im PDF eingebettet, `/Encrypt`-Objekt + restriktive `/P`-Permissions im Roh-PDF bestätigt. Testdaten entfernt.

### Nachtrag 2026-07-08 (3): PDF-Tabelle zweispaltig + dynamische Paginierung (maximale Zeilendichte pro Seite)

User-Wunsch: so viele Protokollzeilen wie möglich pro PDF-Seite unterbringen, optional per Zweispalten-Layout. `sol_pdf_generator.py` grundlegend umgebaut:

- Flaschen-Tabelle nutzt jetzt zwei nebeneinander liegende Spaltenblöcke (je 87mm breit, 6mm Abstand) statt einer einzelnen 180mm-Spalte; Zeilenhöhe von 7mm auf 5mm reduziert (7pt Schrift), Tabellenkopf von 7mm auf 6mm.
- Seitenzahl wird **dynamisch** anhand des tatsächlich verfügbaren Platzes berechnet (`SolTemperaturProtokollPDF._paginate()`), nicht mehr über einen festen `rows_per_page`-Konfigurationswert — Seite 1 hat wegen des Kopf-Metadatenblocks weniger Platz als Folgeseiten, die letzte Seite reserviert zusätzlich Platz für Zusammenfassung + Unterschriftsblock. Der `config['sol']['rows_per_page']`-Wert aus Schritt 2 wird dadurch nicht mehr gelesen (bleibt als harmloser ungenutzter Config-Wert bestehen, keine Migration nötig).
- Ergebnis: eine volle 160-Flaschen-Charge passt jetzt auf **2 Seiten** statt vorher 9; eine typische 45-Flaschen-Charge passt auf **1 Seite** statt vorher 3.
- Auf dem Pi mit dem neuen Simulationsskript getestet: 3, 45 und 160 Flaschen — alle drei PDFs korrekt paginiert (1/1, 1/1, 2/2), NOK-Hervorhebung und Grenzfälle (ungerade Flaschenanzahl, sehr kleine Chargen) fehlerfrei. Testdaten jeweils entfernt.
- Neues Hilfsskript `scripts/simulate_sol_charge.py`: simuliert eine komplette Charge (Start → N Flaschen mit realistisch gestreuten Temperaturen inkl. ~10% bewusster NOK-Fälle → Bestätigung → Unterschrift → Abschluss → PDF-Download) gegen die laufende App auf dem Pi — nützlich für zukünftige Tests bei realistischer Größenordnung statt einzelner manueller curl-Aufrufe.

### Nachtrag 2026-07-08 (4): Interne Dateiliste zeigte SOL-PDFs gar nicht an (Lücke aus dem ursprünglichen Umbau)

User-Frage "warum wird bei Dateien kein PDF intern angezeigt" deckte auf: `templates/filemanager.html` war beim ursprünglichen Chargenseiten-Umbau übersehen worden — die interne Dateiliste hing weiterhin komplett an der alten Sterilisator-Tabelle `protocols` (`/api/protocols`, `/view/<id>`, `/download/<id>`, `/api/protocols/bulk-*`), sodass neu erzeugte SOL-Chargen-PDFs dort nie erschienen (nicht nur keine Vorschau — komplett unsichtbar). Behoben:

- `database.py`: neue Funktionen `get_sol_charge_pdf_path()`, `delete_sol_charge()`. **Bug beim Schreiben gefunden+vermieden:** `sol_bottles` hat zwar `ON DELETE CASCADE` im Schema, aber `PRAGMA foreign_keys` wird in dieser App nirgends aktiviert (SQLite-Standard: aus) — ein reines `DELETE FROM sol_charges` hätte verwaiste `sol_bottles`-Zeilen hinterlassen. `delete_sol_charge()` löscht `sol_bottles` deshalb explizit zuerst.
- `app.py`: drei neue Routen — `DELETE /api/sol/charges/<id>`, `POST /api/sol/charges/bulk-delete`, `POST /api/sol/charges/bulk-download-zip` (Pendants zu den alten `/api/protocols/*`-Routen). Löschen ist hinter `_require_service()` gesperrt (administrative/destruktive Aktion an bereits abgeschlossenen, unterschriebenen Chargen — anders als der tägliche Scan-Workflow), analog zum bestehenden Autoklavenbuch-"discard"-Muster.
- `filemanager.html`: interne Dateiliste auf `/api/sol/charges?status=completed` umgestellt (nur abgeschlossene Chargen mit PDF, offene Chargen ohne PDF werden nicht gelistet), View/Download/Delete/Bulk-Aktionen auf die neuen SOL-Routen umgestellt, Tab-Label "PDF-Protokolle" → "PDF-Chargen". "Rohdaten"-Tab (TCP/9100-Captures) bewusst unverändert gelassen (inert, da TCP-Listener deaktiviert ist — kein Schaden, zeigt einfach dauerhaft "keine Captures").
- Auf dem Pi verifiziert: zuvor gesendete Test-Charge (160 Flaschen, absichtlich nicht geloescht) erscheint jetzt korrekt in der internen Liste, PDF-Vorschau-Route liefert 200, Lösch-Route mit ungueltiger ID liefert korrekt 404 (nicht 403) bei gestecktem Dongle.

### Nachtrag 2026-07-08 (5): "Rohdaten"-Reiter entfernt

User-Wunsch: den "Rohdaten"-Tab (TCP/9100-Capture-Ansicht, seit der Deaktivierung des Sterilisator-Listeners komplett tot) aus `filemanager.html` entfernen. Kompletter Captures-Modus-Codepfad entfernt: Moduswechsel-Toggle, `loadCaptureFiles()`, `renderCaptureRow()`, `parseCaptureTimestamp()`, `delCapture()`, `viewTxt`/`txtClose`/`txtOverlay`-Modal, USB-Captures-Zweig in `renderUsbFileRow()`/`loadUsbFiles()`, Captures-Zweig in `deleteSelectedInternal()`/`syncUsb()`. Seite zeigt jetzt ausschliesslich die SOL-Chargen-PDF-Liste (intern + USB), kein Moduswechsel mehr noetig. Dabei einen vorbestehenden Bug mitgefixt: `downloadSelectedInternal()` nutzte bei genau 1 ausgewaehlter Datei noch die alte Route `/download/<id>` statt `/sol/download/<id>`. Backend-Routen fuer TCP-Captures (`/api/tcp_capture/captures*`) bleiben unveraendert im Code (inerte Referenz, nicht mehr von der UI aufgerufen). Auf dem Pi deployed, Seite laedt (HTTP 200).

### Nachtrag 2026-07-08 (6): "Datensammlermodus" aus den Einstellungen entfernt

User-Wunsch: den "Datensammlermodus"-Schalter (Sterilisator-Rohprotokoll-Direktdruck ohne PDF/DB-Eintrag, TCP/9100-spezifisch) aus der "TCP-Empfang"-Karte in `settings.html` entfernen. Entfernt: Settings-Zeile inkl. Toggle, die zugehoerige Warnbanner-Box ("Sammelmodus aktiv"), sowie die JS-Funktionen `loadCollectorMode()`/`toggleCollectorMode()` und deren Init-Aufruf. Bewusst eng am gefragten Umfang geblieben — die restliche "TCP-Empfang"-Karte (Port-9100-Toggle, Capture-Statistik, Schnittstellen-Karten) bleibt unveraendert, auch wenn ebenfalls TCP-bezogen, da nicht explizit genannt. Backend-Route `/api/capture/collector` bleibt unveraendert im Code (inerte Referenz). Auf dem Pi deployed, Settings-Seite laedt (HTTP 200).

### Nachtrag 2026-07-08 (7): Ganze "TCP-Empfang"-Karte entfernt

User bestaetigte direkt im Anschluss: die restliche "TCP-Empfang"-Karte (Port-9100-Toggle, Capture-Statistik, Letzter-Empfang) ist ebenfalls ueberfluessig. Komplett aus `settings.html` entfernt: die Karte selbst, `toggleTcp()`, der TCP-Status-Fetch-Block in `loadDeviceSettings()` (`tcpToggle`/`captureCount`/`lastCapture`). Backend-Route `/api/tcp_capture/status` bleibt unveraendert im Code (inerte Referenz, auch weiterhin vom separaten "Live-Monitor"-Tab genutzt). Auf dem Pi deployed, Settings-Seite laedt (HTTP 200).

**Hinweis fuer spaeter:** Der komplette "Live-Monitor"-Tab (`tabMonitor`) in `settings.html` ist ebenfalls vollstaendig auf TCP/9100+Sterilisator-`protocols`-Tabelle aufgebaut (`loadMonitorStats()`, `/api/protocols?...`, Terminal-Ansicht via `/api/tcp_capture/last_text`) und damit fuer SOL genauso tot wie die entfernten Karten — wurde in diesem Schritt bewusst NICHT angefasst, da nicht explizit genannt (deutlich groesserer, eigener Tab statt einer einzelnen Karte).

### Nachtrag 2026-07-08 (8): "Live-Monitor"-Tab komplett entfernt

User bestaetigte: der ganze "Live-Monitor"-Tab kann weg. Entfernt aus `settings.html`: Sub-Nav-Button `tabMonitor`, kompletter Panel-Inhalt `panelMonitor` (4 Stat-Karten, "Letztes Protokoll"-Banner, TCP-Terminal-Ansicht), sowie JS: `loadMonitorStats()`, `updateTerminal()`, `tickMonitor()`, `clearTerminal()`, Variablen `lastPdfFilename`/`rxBytes`/`lastText`/`monitorInterval`, der `#monitor`-Hash-Init-Aufruf, und der `monitor`-Zweig in `switchTab()` (Schleife von `['Devices','System','Monitor']` auf `['Devices','System']` reduziert, sonst haette `switchTab()` beim Start auf `null`-Elemente zugegriffen und wäre gecrasht). Settings hat jetzt nur noch 2 Tabs: "Geräte & Netzwerk" und "System". Backend-Routen (`/api/tcp_capture/*`, `/api/protocols`) bleiben unveraendert im Code (inerte Referenz). Auf dem Pi deployed, Seite laedt (HTTP 200), keine Reste von `tabMonitor`/`panelMonitor` im gerenderten HTML.

### Nachtrag 2026-07-08 (9): Kleinere UI-Nacharbeiten an den SOL-Settings + "Anlage"-Karte entfernt

Drei kleine, vom User angestossene Korrekturen an `settings.html`:

1. Eingabefelder "Temperatur-Toleranz" und "Warnschwelle Flaschenanzahl" waren mit 100px zu schmal (Rest der Karte nutzt 140-220px) — auf 140px vergroessert, passend zum "Standort-Kürzel"-Feld daneben.
2. Beide Felder liefen als `type="number"` mit nativen Auf/Ab-Pfeilen — auf User-Wunsch auf `type="text"` mit `inputmode="decimal"`/`"numeric"` + Ziffern-`pattern` umgestellt (kein Spinner mehr, weiterhin Ziffern-Tastatur bei Touch-Eingabe). Kein Backend-/JS-Anpassungsbedarf, da `.value` schon immer als String gelesen und serverseitig per `float()`/`int()` geparst wurde.
3. **"Anlage"-Karte komplett entfernt** (User: "wir verbinden uns mit keiner Anlage" — SOL hat kein Maschinen-/IP-Konzept wie das Herkunftsprojekt). Entfernt: Kartenmarkup (Maschinenname/-nummer/IP-Adresse/Standort/Verbindungstest-Ping), JS-Funktionen `loadMachineConfig()`, `saveMachineConfig()`, `testMachinePing()`, sowie der `loadMachineConfig()`-Aufruf in `loadDeviceSettings()`. Backend-Routen `/api/machine/config`+`/api/machine/ping` und der globale `machine_name`/`machine_protocol`-Context-Processor in `app.py` bleiben unveraendert im Code (inerte Referenz — keine Vorlage referenziert diese Variablen mehr, wie per Grep bestaetigt). Auf dem Pi deployed und verifiziert (HTTP 200, `/api/sol/config`-Speichern mit String-Werten erfolgreich getestet).

### Nachtrag 2026-07-08 (10): "Gerätename im Netzwerk"-Karte entfernt, Hostname in Netzwerk-Speicherort verschoben

User-Wunsch: die eigenstaendige "Gerätename im Netzwerk"-Karte (Hostname-Anzeige + -Aenderung, Beschriftung "DNS-Name im Kliniknetz" — Krankenhaus-Terminologie aus dem Herkunftsprojekt, fuer SOL unpassend) entfernen, Hostname-Funktion aber in die "Netzwerk-Speicherort"-Karte (SMB/CIFS) verschieben statt komplett zu streichen. Umgesetzt: Kartenmarkup verschoben (nicht dupliziert) an den Anfang der Netzwerk-Speicherort-Karte, vor das Server/Freigabename-Feld, mit Trennlinie danach; Beschriftung "DNS-Name im Kliniknetz" → "DNS-Name dieses Geräts im lokalen Netzwerk" korrigiert. Kein JS-Änderungsbedarf, da `loadHostname()`/`saveHostname()` rein ueber Element-IDs (`currentHostname`/`newHostname`) arbeiten, die unveraendert blieben. Auf dem Pi deployed und verifiziert (`/api/system/hostname` liefert weiterhin korrekt `DocuControlSOL`).

### Nachtrag 2026-07-08 (11): Dashboard-Statistik "Flaschen gesamt" → "Flaschen heute"

User-Wunsch: die vierte Stat-Karte im Dashboard soll die Tagesmenge statt der Gesamtsumme ueber alle Zeit zeigen (Tagesproduktion ist die operativ relevantere Kennzahl). `database.py`: `get_sol_charges_stats()` um `today_bottles` ergaenzt (`COUNT(*) FROM sol_bottles WHERE date(scanned_at) = heute` — filtert nach dem Scan-Zeitpunkt der einzelnen Flasche, nicht nach Charge-Start, fuer den seltenen Fall einer Charge, die ueber Mitternacht laeuft). `dashboard.html`: Karten-Label "Flaschen gesamt" → "Flaschen heute", Unterzeile "Über alle Chargen" → "Seit Mitternacht", JS liest jetzt `d.today_bottles` statt `d.total_bottles`. `total_bottles` bleibt zusaetzlich in der API-Antwort erhalten (harmlos, evtl. spaeter nuetzlich). Auf dem Pi deployed und verifiziert (`/api/sol/charges/stats` liefert korrekt `today_bottles`).

### Nachtrag 2026-07-08 (12): System-Aufraeumung auf dem Pi-Host (ausserhalb der App)

Auf User-Anfrage den SOL-Pi nach nicht mehr benoetigter Software durchsucht (Pakete, Docker, Dienste). Ergebnis: Docker sauber (nur 1 aktives Image, kein Build-Cache-Muell), keine Desktop-Umgebung installiert (schlanke Lite-Basis + gezielt nachinstallierter Kiosk), `apt autoremove` zeigte 0 verwaiste Pakete. Einziger klarer Fund: `mkvtoolnix` (~28,6MB, Matroska/Video-Werkzeug) war manuell installiert, hatte aber **keine** Reverse-Dependencies — komplett funktionslos fuer dieses Geraet, vermutlich Rest der urspruenglichen Image-Vorbereitung. Nach User-Bestaetigung entfernt (`apt purge mkvtoolnix` + `autoremove`, zusaetzlich 8 verwaiste Abhaengigkeiten mitentfernt: libqt6core6t64, libb2-1, libdvdread8t64, libmatroska7, libebml5, libicu76, libpcre2-16-0, libpugixml1v5). Der Compiler-Toolchain (gcc-14/g++-14/git, ~170MB) wurde bewusst NICHT angefasst — laut `apt`'s eigener Abhaengigkeitspruefung noch von anderen Basispaketen benoetigt (keine verwaisten Pakete dort), Entfernen haette in eine groessere Abhaengigkeitskette eingegriffen fuer minimalen Gewinn (Speicher war ohnehin nur bei 2% Auslastung). Per echtem Kaltstart-Reboot verifiziert: `kiosk.service` und `docker.service` laufen nach der Bereinigung weiterhin sauber.

### Nachtrag 2026-07-08 (13): PDF-Zoom auf 125% + Tabellenkopf-Ueberlappung im PDF gefixt

Zwei kleine, vom User per Screenshot gemeldete Korrekturen:

1. **PDF-Viewer-Zoom**: `pdfOpen()` in `dashboard.html` und `filemanager.html` oeffnete PDFs bisher mit `#zoom=89&pagemode=none` — `pagemode=none` (keine Seitenübersicht/Thumbnail-Sidebar) war also schon korrekt gesetzt, nur der Zoom-Wert wurde auf `zoom=125` erhoeht.
2. **Tabellenkopf-Ueberlappung im PDF**: Per Screenshot bestaetigt, dass die zweispaltige Tabelle aus Nachtrag (3) einen echten Renderfehler hatte — die Kopfzeilen-Beschriftung "Flaschen-Code" (21mm Spaltenbreite, 7pt fett) war zu breit und lief sichtbar in "IR Temp [°C]" hinein (kein Text-Extraktions-Artefakt, wie zunaechst vermutet, sondern ein echtes visuelles Ueberlappen in `sol_pdf_generator.py draw_table_head()`). Fix: Beschriftung auf "Code" gekuerzt (User-Vorgabe) — jetzt reichlich Platz in der 21mm-Spalte, keine Ueberlappung mehr. Mit frischer 5-Flaschen-Test-Charge visuell verifiziert (Kopfzeile jetzt sauber getrennt "Nr. | Datum / Uhrzeit | Code | IR Temp [°C]").

### Nachtrag 2026-07-08 (14): Tabellenkopf "IR Temp" → "Temp"

User-Wunsch: Spaltenkopf weiter gekuerzt von "IR Temp [°C]" auf "Temp [°C]". Ein Vorkommen in `sol_pdf_generator.py draw_table_head()` geaendert, kompiliert und deployed.

### Nachtrag 2026-07-08 (15): Automatisches Anlegen des "captures"-Ordners auf USB/Netzwerk gestoppt

User-Wunsch: kein "captures"-Ordner mehr auf USB-Stick und Netzwerk-Speicherort noetig (weiterer Rest des deaktivierten TCP/9100-Empfangs). Zwei aktive Hintergrundprozesse legten trotz deaktiviertem TCP-Listener weiterhin periodisch einen leeren Captures-Ordner an:

- `storage_manager.py`: Der USB-Auto-Sync-Loop rief bei jedem Intervall/Einstecken zusaetzlich zu `sync_pdfs_to_usb()` auch `sync_captures_to_usb()` auf — Aufruf entfernt (Funktion bleibt als Referenz erhalten).
- `network_storage_manager.py`: Zwei Stellen betroffen — (1) der periodische Netzwerk-Sync-Loop rief `sync_captures_to_network()` auf, entfernt; (2) `mount_network_share()` legte den Captures-Unterordner sogar unabhaengig vom Sync-Loop bei **jedem** erfolgreichen Mount proaktiv per `os.makedirs()` an — dieser Aufruf ebenfalls entfernt, nur der PDF-Unterordner wird noch angelegt.

Auf dem Pi war zum Zeitpunkt der Pruefung weder USB noch Netzwerk-Freigabe gemountet, daher kein bereits vorhandener leerer Ordner zu entfernen. Beide Dateien deployed, Container startet sauber, USB-Sync laeuft weiterhin normal (PDFs synchronisiert) ohne die bisherige "Captures Auto-Sync"-Logzeile.

### Nachtrag 2026-07-08 (16): PDF-Rand asymmetrisch + Download-Link im Kiosk-PDF-Viewer

Zwei vom User gemeldete Punkte:

1. **PDF-Rand rechts breiter als links**: Echter Layout-Bug bestaetigt — die zweispaltige Tabelle (`CONTENT_WIDTH=180`, `CONTENT_LEFT=10`) endete bei x=190, ergab bei A4 (210mm breit) einen 20mm rechten Rand gegenueber nur 10mm links. Der Header-Bereich (Charge-/Seiten-Info bei x=150, Breite 50 → Ende x=200) und die Footer-Zeitangabe (x=110, Breite 90 → Ende x=200) nutzten dagegen schon korrekt x=200 als rechte Grenze — die Tabelle und der Meta-Block waren die einzigen inkonsistenten Elemente. Fix in `sol_pdf_generator.py`: `CONTENT_WIDTH` 180→190 (Tabellenspalten `COL_WIDTH` 87→92mm, `SUBCOL["dt"]` 36→41mm aufgenommen), Meta-Block-Trennlinie 190→200, "Flaschen gesamt/NOK"-Zeile 90→100mm Breite (Ende ebenfalls 190→200). Jetzt durchgehend symmetrische 10mm-Raender auf allen Seitenelementen.
2. **Download-Link im Kiosk-PDF-Viewer**: Der eingebaute Chromium-PDF-Betrachter (iframe) zeigt standardmaessig eine eigene Toolbar mit Download-/Druck-Icons, unabhaengig von den selbstgebauten "Ansehen"/"Herunterladen"-Buttons der App. Fix: `pdfOpen()` in `dashboard.html` (dort fehlte bisher jegliche Kiosk-Erkennung, `isKiosk()` neu ergaenzt) und `filemanager.html` haengt jetzt `&toolbar=0` an den PDF-URL-Fragment an, aber **nur wenn `isKiosk()`** (Hostname `localhost`/`127.0.0.1`) — bei externem Browserzugriff (z.B. vom Buero-PC) bleibt die volle Toolbar inkl. Download/Druck erhalten, da dort legitim gebraucht.

Mit frischer 6-Flaschen-Test-Charge visuell verifiziert (symmetrische Raender bestaetigt), Testdaten danach entfernt (nur zur visuellen Pruefung erzeugt, nicht explizit zum Behalten angefordert).

### Nachtrag 2026-07-08 (17): Dritte uebersehene captures-Aufrufstelle im manuellen Netzwerk-Sync

Nach Einrichtung des neuen SMB-Netzwerk-Speicherorts (`\\192.168.0.85\temp`) tauchte trotz des Fixes aus Nachtrag (15) erneut ein leerer `captures`-Ordner auf der Freigabe auf. Ursache: `app.py`s `POST /api/storage/network/sync` (der manuelle "Jetzt sync."-Button-Endpunkt, unabhaengig vom periodischen Hintergrund-Loop) rief `sync_captures_to_network()` weiterhin direkt auf — diese dritte Aufrufstelle wurde beim urspruenglichen Fix uebersehen. Aufruf entfernt, Route liefert jetzt nur noch das PDF-Sync-Ergebnis. USB-Pendant (`api_storage_sync_now` o.ae.) hat keine analoge Stelle, blieb unberuehrt. Bereits vorhandenen leeren Ordner auf `C:\temp\DocuControl\captures` entfernt, Fix deployed und durch erneuten manuellen Sync-Aufruf verifiziert (Ordner kommt nicht wieder).
