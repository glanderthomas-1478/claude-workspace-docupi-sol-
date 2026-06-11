# Strategie

## Aktueller Fokus

Prototyp fertigstellen und erste Feldtests im eigenen Arbeitsumfeld durchfuehren.

## Strategische Prioritaeten

### 1. RS232-Kommunikation — ERLEDIGT (MST)

- MST-Protokollformat entschluesselt (UTF-16LE Klartext ueber RS232)
- Live-RS232-Listener laeuft produktiv (serial_receiver.py)
- Parser + PDF-Generator + Chart-Generator implementiert
- **Erster Feldtest erfolgreich: 3 Wochen, 140 Chargen, 0 Fehler** (Helios Krefeld, Belimed 9-6-18 HS2)
- OFFEN: WD/RDG-Protokoll (WD290/WD390) — separater Parser vorhanden, noch nicht im Feld getestet

### 2. Software stabilisieren — IN ARBEIT

- Feldtest-Fixes deployed (2026-04-13):
  - VPR/Lecktest-Erkennung korrigiert (NICHT STERIL = BESTANDEN)
  - Abbruch-Handling und unvollstaendige Protokolle (Stromausfall)
  - USB Auto-Mount nach Reboot
  - Serial-Port Log-Spam eliminiert (Exponential Backoff)
- OFFEN: Patch-Dateien konsolidieren (15+ separate Patches in app.py integriert)
- OFFEN: Tests automatisieren

### 3. Hardware-Prototyp — ERSTER FELDTEST ABGESCHLOSSEN

- Raspberry Pi 5 lief 3 Wochen am Sterilisator in Krefeld
- RS232-Empfang, PDF-Generierung, WebIF, Hotspot — alles stabil
- 327 Protokolle in DB, 140 PDFs generiert (nach Fix)
- OFFEN: Sensoren (Druck, Strom) noch nicht angeschlossen

### 4. Langfristig: CE-konforme Hardware

- Migration auf Unipi Neuron oder RevPi Connect
- Regulatorik klaeren (kein eigenes Medizinprodukt, nur Diagnosetool)

### 5. Erster Kunden-Deal (DocuControl, Tierlabor Uni Essen) — WEB-INTERFACE FERTIG

- Vertrieb laeuft verdeckt ueber getmatic / Thomas Glander (Whitelabel)
- Zielmaschine: **Belimed PST 14-8-12 HS1** (bestaetigt 2026-06-08)
- **ERLEDIGT 2026-06-02**: Pi 5 aufgebaut, Service aktiv, TCP/9100-Pipeline produktiv
- **ERLEDIGT 2026-06-03**: Web-Interface v2 deployed (Dashboard, Einstellungen, Datei-Manager, Drucker, USB-Sync)
- **ERLEDIGT 2026-06-09**: Dashboard v3 Liquid-Glass deployed:
  - v3 Design-Handoff von getmatic empfangen und implementiert
  - Machine-Bar (Belimed PST 14-8-12 HS1, 6050/6060 FIS, VAFI/KOST, TCP-Status live)
  - 3 Stat-Karten: Chargen gesamt / heute / Monat (inkl. Vormonat-Trend)
  - Dauer-Spalte + Programm-Icons in Tabelle
  - Liquid-Glass-CSS, Square-Font, Live-Uhr, pulsierender Aktiv-Badge
  - Neuer /api/dashboard/stats Endpunkt
- **ERLEDIGT 2026-06-09**: Settings + Drucker-Erkennung optimiert:
  - Maschinenname + IP in Settings konfigurierbar, Ping-basierter Status in Machine-Bar
  - Drucker-Erkennung via USB sysfs (physisch), Auto-Print Bug gefixt, Race-Condition Print-Button behoben
  - Topbar-Badge entfernt, 5 Testchargen (CH021709-CH021713) erfolgreich verarbeitet und gedruckt
  - Dashboard "Chargen gesamt"-Karte zeigt höchste Charge-Nr. (z.B. 21713) statt DB-Zeilenanzahl — `/api/dashboard/stats` liefert `max_charge_nr` via CHARGE_RE über raw_data
- **ERLEDIGT 2026-06-10**: Datensammlermodus vollstaendig implementiert und verifiziert:
  - Toggle in Settings schreibt `collector_mode` Flag in `capture_config.json` (Merker-Architektur)
  - Browser-Cache-Bug gefixt: `Cache-Control: no-store` via Flask `@after_request`
  - Verifiziert: CH021718 (Normalmodus → PDF+DB+Druck) und CH021719 (Sammelmodus → Rohtext direkt gedruckt, kein PDF, kein DB)
- **ERLEDIGT 2026-06-11**: v3 Makeover Settings + Datei-Manager deployed:
  - Button-Hierarchie: `btn-primary` (Speichern), `btn-glass` (Ping/Test/Sync), `btn-outline-danger` (Reboot)
  - `.segmented`-Toggle in Datei-Manager (CSS statt Inline-Styles), JS auf `classList.toggle('active')`
  - `.lede`-Untertitel in Page-Head beider Seiten
- **ERLEDIGT 2026-06-11**: Dashboard-Bugs behoben (Kundentermin-kritisch):
  - "Chargen heute" Zaehler: `date(timestamp) = ?` statt String-Vergleich (ISO-T vs Space-Trenner-Bug)
  - Dauer-Spalte: `_PROG_ENDE_RE` liest `MM:SS Programm Ende` direkt aus raw_data statt ISO-Timestamps
- **ERLEDIGT 2026-06-11**: USB-Ethernet (Schnittstelle 2) vollstaendig funktionsfaehig:
  - eth1 statisch 192.168.0.181/24 konfiguriert und stabil
  - nftables auf interface-basierte Regeln umgestellt (iif eth0 + iif eth1) — beide IPs erreichbar
  - Connected-Status basiert jetzt auf `/sys/class/net/<iface>/carrier` (physischer Link statt IP-Check)
  - `iface2StatusBadge` im Settings Card-Header hinzugefuegt — zeigt Verbunden/Getrennt wie bei Schnittstelle 1
  - Toggle-Bug behoben: `applyIfaceStatus()` setzt jetzt `iface2Enabled`-Checkbox korrekt aus API
- **ERLEDIGT 2026-06-11**: `scripts/send_test_charges.py` erstellt:
  - 3 Templates: Instrumente 134°C, Bowie Dick, Instrumente 121°C
  - UTF-16LE mit BOM, 10 Chargen CH021720-021729, 30s Intervall
  - Laufzeiten variiert (18-42 min), `--dry-run`, `--count`, `--interval`, `--start-charge` Flags
  - Testlauf erfolgreich: alle 10 Chargen in DB, duration HH:MM:SS, alle 3 Programme erkannt
- **ERLEDIGT 2026-06-11**: Skalierbarkeit 10.000+ Protokolle: DB-Spalten charge_nr_int + program, SQL LIMIT/OFFSET in api_protocols, Dateimanager-Paginierung (50/Seite)
- **ERLEDIGT 2026-06-11**: PDF-Dateinamen + Maschinennummer:
  - Dateiname-Reihenfolge: `{datum}_{zeit}_{charge}_{masch_nr}_{geraet}` (Charge-Nr. direkt nach Zeitstempel)
  - Maschinennummer (`machine_nr`) als neues konfigurierbares Feld in Settings → Anlage-Card
  - `build_filename()` in pdf_generator.py um `{masch_nr}`-Token erweitert
  - Verifiziert: CH021732 → `2026-06-11_175105_CH021732_27163_Belimed_PST_14-8-12_HS1.pdf`
- **ERLEDIGT 2026-06-11**: Datei-Manager Rohdaten-Toggle wiederhergestellt (war durch Skalierbarkeits-Deploy überschrieben)
- **ERLEDIGT 2026-06-11**: Settings-Fixes (waren Pi-only Patches, jetzt committed):
  - `iface2StatusBadge` im Schnittstelle-2-Card-Header (Verbunden/Getrennt)
  - `applyIfaceStatus()` setzt `iface2Enabled`-Checkbox korrekt aus `d.enabled`
  - USB-Stick formatieren Button (POST /api/storage/usb/format, FAT32, Label DOCUCTRL)
- **ERLEDIGT 2026-06-11**: GitHub Collaboration: Thomas Glander (glanderthomas-1478) als Collaborator mit Push-Zugriff hinzugefügt
- OFFEN: Echten Druckauftrag vom Tierlabor-Geraet (Belimed PST 14-8-12 HS1) empfangen und Captures analysieren
- OFFEN: protocol_parser.py auf echten PST 14-8-12 HS1 Daten kalibrieren
- OFFEN: Maschinennummer des Tierlabor-Geraets in Settings eintragen
- OFFEN: Installation vor Ort Tierlabor Uni Essen

## Wie Erfolg aussieht

- ~~Funktionierender Prototyp, der im Feld einsetzbar ist~~ ERREICHT
- ~~RS232-Protokoll entschluesselt und implementiert~~ ERREICHT (MST)
- ~~Erste Feldtests erfolgreich durchgefuehrt~~ ERREICHT (Helios Krefeld)
- Naechster Meilenstein: DocuControl-Pi fertig konfigurieren, Sample-Druckauftrag analysieren, Installation im Tierlabor Uni Essen, Sensoren anschliessen, WD/RDG-Feldtest, Patch-Konsolidierung
