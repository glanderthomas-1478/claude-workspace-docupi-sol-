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
| Erster Kunden-Deal | In Umsetzung | Abschluss | DocuControl fuer Tierlabor Uni Essen, getmatic-Vertrieb, Pi 5 in Aufbau (2026-06-02) |
| DocuControl Pi 5 | Setup begonnen | Produktiv | Hostname gesetzt, SSH-Key, I2C aktiv; RTC-Overlay/OS-Update/WLAN-Off pending |

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

### DocuControl (neu, bei getmatic im Aufbau)
- Raspberry Pi 5 mit externer RTC (Modul-Typ tbd, vermutlich DS3231 auf I2C 0x68)
- OS: Debian 13 (trixie / Bookworm-Successor), Kernel 6.12.75+rpt-rpi-2712, aarch64
- User: docucontrol (Passwort: Xtend1478), SSH-Key vom Workspace-Host installiert
- Hostname: DocuControl (geaendert von DCUETL am 2026-06-02)
- Setup-Status: Hostname OK, I2C aktiv (dtparam=i2c_arm=on), RTC-Overlay/OS-Update/WLAN-Off offen
- Geplanter Einsatz: Tierlabor Uni Essen

### Ziel-Hardware (langfristig)
- Unipi Neuron / RevPi Connect (CE-zertifiziert)

## Feldtest-Daten (Helios Krefeld)

- Maschine: Belimed 9-6-18 HS2, Nr. 27163
- Zeitraum: 25.03. - 13.04.2026
- Chargen: CH021714 - CH021853 (140 lueckenlos)
- Programme: Instrumente 134°C (103x), Bowie Dick (18x), VPR (19x)
- Backup: backups/pi-backup-2026-04-13/ (52 MB)
