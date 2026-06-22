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
| DocuControl Web-Interface | **VOLLSTAENDIG** | — | Dashboard v3 + Settings (Maschinennummer, iface2Badge, iface2Enable-Fix, USB-Formatieren, Netzwerk-Speicherort SMB) + Dateien (Mode-Toggle PDF/Rohdaten, SQL-Paginierung) — Stand 2026-06-12 |
| Netzwerk-Speicherort (SMB-Sync) | **PRODUKTIV + SOFORTKOPIE** | — | Konto `docucontrol` auf 192.168.0.99 (gland), Freigabe `temp`=C:\temp, via eth1 (Host-Route), Sofortkopie nach jeder Charge (2026-06-15) |
| USB Auto-Sync | **IMPLEMENTIERT + SOFORTKOPIE** | — | udev-Trigger, sofort nach Charge (copy_pdf_to_usb_instant in tcp_print_capture.py), Intervall-Sync 15 Min, USB-Mount-Fix (Log+Sleep+Retry) — 2026-06-15 |
| Live-Monitor | **GEFIXT** | — | Bug d.text→d.content behoben, Terminal zeigt jetzt empfangene Rohdaten |
| PDF-Branding/Maschinen-Nr | **GEFIXT** | — | PDF zeigt jetzt konfigurierte Maschinennummer (10980) statt Rohprotokoll-Wert, Footer "DocuPi-3000"/"DocuPi" → "DocuControl" (2026-06-12) |
| Backup DocuControl | Erstellt 2026-06-13 | — | backups/pi-backup-2026-06-13b: DB (851 Protokolle), 851 PDFs, 1702 Captures, Code, Logs, System-Configs (inkl. nftables-Override) |
| nftables-Boot-Race | **GEFIXT** | — | systemd-Override `/etc/systemd/system/nftables.service.d/override.conf` wartet auf eth1, per Reboot-Test verifiziert (2026-06-13) |
| Dateimanager Storage-Status | **IMPLEMENTIERT** | — | USB- und Netzwerk-Speicherort-Status als zwei Badges nebeneinander in Karte "USB / Externer Speicher" (2026-06-13) |
| Netzwerk-Management | **IMPLEMENTIERT** | — | IP-Bug gefixt (sudoers), DHCP aktiv, Router-MAC-Binding gibt .171, Multi-Interface UI, Hostname, NTP/RTC, VLAN-Feld |
| IP Live-Anzeige | **IMPLEMENTIERT** | — | pollCurrentIPs() alle 5s, aktualisiert current_ip/badge ohne Input-Felder zu überschreiben |
| Pi5_Display | **IN BETRIEB** | — | HDMI-Kiosk via Docker+cage+Chromium, seit 2026-06-16, SMB-Mount-Fix 2026-06-18 (cifs-utils) |
| docucontrol3 (Autoklavenbuch) | **IN BETRIEB** | Tierlabor-Test | SD→NVMe-Migration 2026-06-21, Autoklavenbuch-Workflow von Felix' Repo uebernommen 2026-06-22 |
| OWASP-Sicherheitsreview (Web+Host) | **KRITISCHE PUNKTE BEHOBEN** | — | Secrets, Brute-Force-Schutz, XSS, Access-Control, CORS/CSRF/HTTPS, rpcbind, SSH-Pubkey-only (2026-06-21/22) |
| Offline-Faehigkeit | **HERGESTELLT** | — | Bootstrap/Icons/Socket.IO lokal vendored, keine externen Backend-Abhaengigkeiten (2026-06-22) |
| Service-Login + Settings-Sperre | **IMPLEMENTIERT** | — | Rolle "user" vs. Service, serverseitige Guards auf sensiblen Endpunkten (2026-06-22) |
| Bildschirmschoner + Boot-Splash | **IMPLEMENTIERT** | — | GeTmatic-Logo (DVD-Stil + Boot), Plymouth-Quit-Race behoben (2026-06-22) |
| Drucker Netzwerk/USB-Umschalter | **IMPLEMENTIERT** | — | IPP-Everywhere driverless fuer Netzwerkdrucker zusaetzlich zu IPP-over-USB (2026-06-22) |
| Passwort-Rollout Geraeteflotte | **TEILWEISE** | Alle Geraete | Pi5_Display/docucontrol3 individuelle Passwoerter gesetzt; DocuControl (.171) + DocuPi-3000 (.83) noch mit altem gemeinsamem Passwort (nicht erreichbar beim Rollout) |

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
- User: docucontrol (Passwort: Xtend1478), SSH: `ssh docucontrol` (Alias, IdentityFile `~/.ssh/docucontrol_id`)
- Hostname: DocuControl, Service: docucontrol.service (active+enabled, Restart < 1s via os._exit Fix)
- Code: /home/docucontrol/docupi/, venv: /home/docucontrol/docupi/venv
- Architektur: TCP/9100-Capture -> parse -> PDF -> DB (automatisch)
- DB: /home/docucontrol/docupi/data/docupi.db (protocols-Tabelle: id, timestamp, device_name, raw_data, pdf_path, pdf_filename, file_size, status, charge_nr_int, program — 851 Eintraege Stand 2026-06-13, letzte Charge CH022773)
- PDFs: /home/docucontrol/docupi/data/pdfs/ (Dateiname-Format ab 2026-06-11: DATUM_ZEIT_CHxxxxxx_MaschinNr_Geraet.pdf)
- Port-Redirect: nftables /etc/nftables-docucontrol.conf (80 -> 5000, Regeln: iif eth0 + iif eth1, beide IPs erreichbar)
- Drucker: Epson XP-4150 als "DocuPrinter" via CUPS **IPP-over-USB** (`ipp://EPSON%20XP-4150%20Series%20(USB)._ipp._tcp.local/`) — Druck verifiziert 2026-06-15, Sudoers fuer lpadmin+lpinfo gesetzt
- Web: Dashboard v3 + Settings vollstaendig (Maschinennummer-Feld, iface2Badge, USB-Formatieren, Button "USB einrichten") + Dateien vollstaendig (Mode-Toggle PDF/Rohdaten, SQL-Paginierung 50/Seite)
- Drucker-Settings: zeigt "EPSON XP-4150 Series" (echter Modellname via sysfs), "kein Drucker verbunden" wenn offline
- USB: Auto-Sync via udev + storage_manager.py, Mount: /media/usbstick, Trigger: /var/lib/docucontrol/usb.trigger
- USB Sofortkopie: copy_pdf_to_usb_instant() in tcp_print_capture.py eingehängt (2026-06-15) — PDF landet sofort auf Stick nach Charge
- Netzwerk Sofortkopie: copy_pdf_to_network_instant() in network_storage_manager.py + tcp_print_capture.py (2026-06-15) — PDF sofort auf \\192.168.0.99\temp
- USB Auto-Mount Fix: logging bei Mount-Fehler + sleep nach Lazy-Unmount + Mount-Versuch in copy_pdf_to_usb_instant (2026-06-15)
- USB Device-Name: nach Re-Enumeration kann sdb1 -> sda1 wechseln (detect_usb_device() findet es dynamisch via lsblk)
- Netzwerk-Sync Ziel: 192.168.0.99 (gland, eth1=192.168.0.181), Host-Route 192.168.0.99 -> eth1 persistent via NM
- eth1 (192.168.0.181) kommuniziert mit 192.168.0.99 via statische Host-Route (nmcli, 2026-06-15)
- Abteilung in Test-Chargen + config.json Default: "ZTL" (war "AEMP") — 2026-06-15
- VPR-Template in send_test_charges.py ergänzt (Index 3: Aufheizen & VPR, ~46 min) — 2026-06-15
- eth0 DHCP-Problem: nach Reboot manchmal kein IP — Workaround: `nmcli con down/up docucontrol-eth0`; Langfrist-Fix: eth0 statisch auf .171 konfigurieren (noch offen)
- Naechster Schritt: Sample-Druckauftrag Tierlabor analysieren, Installation vor Ort; eth0 statisch konfigurieren
- Geplanter Einsatz: Tierlabor Uni Essen — Maschinentyp bestätigt: Belimed PST 14-8-12 HS1

### Pi5_Display (dritte Hardware-Linie, in Betrieb seit 2026-06-16)
- Eigenstaendiger DocuControl-Pi mit HDMI-Kiosk-Display, Betrieb via Docker
- SSH: `ssh docucontrol2` (Alias, Key-only seit 2026-06-22), eth0 192.168.0.218 (DHCP), eth1 192.168.0.107 (statisch)
- Netzwerk-Speicherort (SMB) zu \\192.168.0.86\temp (Konto docucontrol) seit 2026-06-18 produktiv (SMB-Mount-Fix: cifs-utils im Docker-Image, vers=3.0)
- Sudo-Passwort seit 2026-06-22 individuell (nicht mehr im Klartext in CLAUDE.md, siehe lokale secrets/-Ablage)
- **Hinweis:** stellte sich am 2026-06-21/22 als identische physische Hardware wie docucontrol3 heraus (SD-Karte neu geflasht im Rahmen der SSD-Migration) — Konfiguration teils ueberschrieben, siehe docucontrol3
- Offen: Maschinennummer/Name in Settings, Drucker anschliessen, eth0 statisch
- Details: CLAUDE.md Abschnitt "Pi5_Display", plans/2026-06-16-pi5-display-setup.md

### docucontrol3 (vierte Hardware-Linie, Autoklavenbuch-Testgeraet, in Betrieb seit 2026-06-22)
- Physisch dieselbe Hardware wie Pi5_Display, jetzt komplett von NVMe-SSD (Geekworm X1001) statt SD-Karte
- SSH: `ssh docucontrol@192.168.0.11` (eth1, DHCP) oder `.218` (eth0, DHCP), individuelles Sudo-Passwort seit 2026-06-22
- RTC: Pi5-Onboard-RTC (`rpi-rtc`, /dev/rtc0) + nachgeruestete CR1632-Batterie (kein externes DS3231-Modul)
- SD→NVMe-Migration 2026-06-21: EEPROM-Boot-Order auf NVMe gesetzt, Overlay-Root (`overlayroot=tmpfs`) deaktiviert (inkompatibel mit Docker overlay2 + wuerde DB/PDFs bei jedem Reboot zuruecksetzen), Docker-Storage-Driver auf `vfs` umgestellt
- Autoklavenbuch-Workflow (2026-06-22) aus Felix' separatem Repo `DocuControl-Belimed-Autoklav-Uni-Essen` uebernommen: Chargen landen erst im Status `pending_form`, SocketIO-Formular-Modal am Touchscreen, erst nach Bestaetigung PDF (Formular 268627 Rev. 004/01.2024); eigener PST-Parser fuer UNIKLINIK_ESSEN_10980-Format (6-Sensor-Spalten, mehrseitig)
- Mehrere Bugs in Felix' Code gefixt: `get_usb_info()` Zeilenumbruch-Bug, `timedatectl` funktioniert nicht in Docker (auf `date -s`+`hwclock` umgestellt), fehlendes `util-linux-extra`-Paket, CSS-Spaltenausrichtung Datei-Manager, PDF-Modal-Vollbild
- OWASP-Fixes, Offline-Vendoring, Service-Login, Bildschirmschoner, Boot-Splash, Drucker-Netzwerk-Umschalter (s. Tabelle oben) — alle live auf diesem Geraet umgesetzt
- Details: CLAUDE.md Abschnitt "docucontrol3"

### Ziel-Hardware (langfristig)
- Unipi Neuron / RevPi Connect (CE-zertifiziert)

## Feldtest-Daten (Helios Krefeld)

- Maschine: Belimed 9-6-18 HS2, Nr. 27163
- Zeitraum: 25.03. - 13.04.2026
- Chargen: CH021714 - CH021853 (140 lueckenlos)
- Programme: Instrumente 134°C (103x), Bowie Dick (18x), VPR (19x)
- Backup: backups/pi-backup-2026-04-13/ (52 MB)
