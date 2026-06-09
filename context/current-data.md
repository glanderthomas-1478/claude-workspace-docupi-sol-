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
| DocuControl Pi 5 | Produktiv + stabil | Tierlabor-Deployment | Kernel 6.18.33, RTC DS3231, WLAN off, Service <1s Restart, 13 Test-Protokolle in DB (Betreiber: Uniklinik Essen Tierlabor) |
| DocuControl Web-Interface | **v3 DASHBOARD + Settings optimiert** | Einstellungen+Dateien v3-Redesign ausstehend | Machine-Bar Ping-Status, Anlage-Card, Drucker USB-sysfs, Auto-Print gefixt, Print-Button Race-Fix, Dashboard "Chargen gesamt" zeigt höchste Charge-Nr. (2026-06-09) |
| USB Auto-Sync | **IMPLEMENTIERT** | Feldtest ausstehend | udev-Trigger, sofort + Intervall-Sync, Toggle in Einstellungen, Dateiliste im Datei-Manager |
| Live-Monitor | **GEFIXT** | — | Bug d.text→d.content behoben, Terminal zeigt jetzt empfangene Rohdaten |
| Backup DocuControl | Erstellt 2026-06-08 | — | backups/pi-backup-2026-06-08: DB, 11 PDFs, 18 Captures, Code, System-Configs |
| Netzwerk-Management | **IMPLEMENTIERT** | — | IP-Bug gefixt (sudoers), DHCP aktiv, Router-MAC-Binding gibt .171, Multi-Interface UI, Hostname, NTP/RTC, VLAN-Feld |
| IP Live-Anzeige | **IMPLEMENTIERT** | — | pollCurrentIPs() alle 5s, aktualisiert current_ip/badge ohne Input-Felder zu überschreiben |

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

### DocuControl (bei getmatic, Web-Interface produktiv — 2026-06-03)
- Raspberry Pi 5 mit DS3231 RTC (I2C 0x68, /dev/rtc1, dtoverlay=i2c-rtc,ds3231)
- OS: Debian Trixie (aarch64), Kernel 6.18.33, WLAN hardware-deaktiviert (dtoverlay=disable-wifi)
- User: docucontrol (Passwort: Xtend1478), SSH: `ssh -i ~/.ssh/id_ed25519 docucontrol@192.168.0.171`
- Hostname: DocuControl, Service: docucontrol.service (active+enabled, Restart < 1s via os._exit Fix)
- Code: /home/docucontrol/docupi/, venv: /home/docucontrol/docupi/venv
- Architektur: TCP/9100-Capture -> parse -> PDF -> DB (automatisch)
- DB: /home/docucontrol/docupi/data/docupi.db (protocols-Tabelle, 13 Eintraege)
- PDFs: /home/docucontrol/docupi/data/pdfs/ (11 PDFs, Ordnerstruktur 2026/2026-06/)
- Port-Redirect: nftables /etc/nftables-docucontrol.conf (80 -> 5000, Regel: iif eth0, DHCP-kompatibel)
- Drucker: Epson XP-4150 als "DocuPrinter" via CUPS IPP Everywhere
- Web: Dashboard v3 (Machine-Bar Belimed PST 14-8-12 HS1, 3 Stat-Karten+Trend, Dauer-Spalte, Programm-Icons, Liquid-Glass), Einstellungen (3 Tabs, noch v2), Dateien (noch v2)
- Drucker-Settings: zeigt "EPSON XP-4150 Series" (echter Modellname via ipptool), "kein Drucker verbunden" wenn offline; "Drucker erkennen"-Button entfernt (2026-06-09)
- USB: Auto-Sync via udev + storage_manager.py, Mount: /media/usbstick, Trigger: /var/lib/docucontrol/usb.trigger
- Naechster Schritt: Sample-Druckauftrag Tierlabor analysieren, Installation vor Ort
- Geplanter Einsatz: Tierlabor Uni Essen — Maschinentyp bestätigt: Belimed PST 14-8-12 HS1

### Ziel-Hardware (langfristig)
- Unipi Neuron / RevPi Connect (CE-zertifiziert)

## Feldtest-Daten (Helios Krefeld)

- Maschine: Belimed 9-6-18 HS2, Nr. 27163
- Zeitraum: 25.03. - 13.04.2026
- Chargen: CH021714 - CH021853 (140 lueckenlos)
- Programme: Instrumente 134°C (103x), Bowie Dick (18x), VPR (19x)
- Backup: backups/pi-backup-2026-04-13/ (52 MB)
