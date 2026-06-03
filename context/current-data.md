# Aktuelle Daten

## Projektmetriken

| Metrik | Aktueller Wert | Zielwert | Notizen |
| ------ | -------------- | -------- | ------- |
| Konzeptdokument | Fertig | — | Hardware, Software, Regulatorik, Roadmap |
| Prototyp-Hardware | Raspberry Pi 5 im Feld getestet | Sensoren pending | 3 Wochen Dauerbetrieb, stabil |
| S-Bus/UDP Software | Fertig | — | 9-Dateien-Paket (SQLite, FastAPI, Web-Dashboard) |
| RS232-Protokoll (MST) | Produktiv im Feld | Produktionsreif | 140 Chargen lueckenlos, Fixes deployed |
| RS232-Protokoll (WD) | Parser fertig | Feldtest pending | UTF-16LE Klartext, .ht + RS232, 42 Tests |
| MST-PDF-Generator | Produktiv | Produktionsreif | v4, Feldtest-Fixes (VPR, Abbruch, Amber) |
| Erster Feldtest | ABGESCHLOSSEN | Weitere geplant | Helios Krefeld, 25.03.-13.04.2026, 327 Protokolle |
| Erster Kunden-Deal | In Umsetzung | Abschluss | DocuControl fuer Tierlabor Uni Essen, getmatic-Vertrieb, Pi 5 betriebsbereit seit 2026-06-02 |
| DocuControl Pi 5 | Pipeline produktiv | Design-Umbau ausstehend | Kernel 6.18.33, RTC DS3231 (/dev/rtc1), WLAN off, TCP/9100-Capture → Parse → PDF → DB vollautomatisch, 3 Test-Protokolle in DB |
| DocuControl Web-Interface | Funktional (altes Design) | GeTmatic-Design | Design-Handoff-Paket in reference/design_handoff_docucontrol/, Plan: plans/2026-06-03-docucontrol-design-system.md |

## Quellcode-Uebersicht

- `pdf_generator.py` (23 KB) — PDF-Generierung
- `chart_generator.py` (4.5 KB) — Charts
- `print_manager.py` (9.5 KB) — Drucker
- `watchdog_manager.py` (6 KB) — Service-Ueberwachung
- `add_system_health.py` (8 KB) — Health-Metriken
- 15+ `patch_*.py` Dateien — Feature-Erweiterungen
- 3 HTML-Dateien (Dashboard, Base, Captive Portal)

## Hardware

### DocuPi-3000 (produktiv, zu Hause)
- Raspberry Pi 5, 8GB RAM, Debian Trixie (aarch64)
- SSH: belimed@192.168.178.83 (Passwort: sb261)
- Hostname: DocuPi-3000, Service: docupi.service
- Hotspot: SSID DocuPi-3000, PW DocuPi2026

### DocuControl (bei getmatic, betriebsbereit)
- Raspberry Pi 5 mit DS3231 RTC (I2C 0x68, /dev/rtc1, dtoverlay=i2c-rtc,ds3231)
- OS: Debian Trixie (aarch64), Kernel 6.18.33, WLAN hardware-deaktiviert (dtoverlay=disable-wifi)
- User: docucontrol (Passwort: Xtend1478), SSH: docucontrol@192.168.0.171
- Hostname: DocuControl, Service: docucontrol.service (active+enabled)
- Code: /home/docucontrol/docupi/, venv: /home/docucontrol/docupi/venv
- Architektur: TCP/9100-Capture -> parse_serial_protocol -> generate_pdf -> save_protocol (automatisch)
- Templates: base.html, dashboard.html, filemanager.html, settings.html, monitor.html, network.html
- DB: /home/docucontrol/docupi/data/docucontrol.db (protocols-Tabelle, 3 Test-Eintraege)
- PDFs: /home/docucontrol/docupi/data/pdfs/
- Config: /home/docucontrol/docupi/data/capture_config.json
- Port-Redirect: nftables /etc/nftables-docucontrol.conf (80 -> 5000)
- Naechster Schritt: Design-System-Umbau (GeTmatic-Handoff), Plan bereit
- Geplanter Einsatz: Tierlabor Uni Essen (Maschinentyp noch unbekannt)

### Ziel-Hardware (langfristig)
- Unipi Neuron / RevPi Connect (CE-zertifiziert)

## Feldtest-Daten (Helios Krefeld)

- Maschine: Belimed 9-6-18 HS2, Nr. 27163
- Zeitraum: 25.03. - 13.04.2026
- Chargen: CH021714 - CH021853 (140 lueckenlos)
- Programme: Instrumente 134°C (103x), Bowie Dick (18x), VPR (19x)
- Backup: backups/pi-backup-2026-04-13/ (52 MB)
