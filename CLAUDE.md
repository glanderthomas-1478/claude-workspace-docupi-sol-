# CLAUDE.md — DocuPi-3000 Felddiagnostik

Diese Datei gibt Claude Code Anweisungen fuer die Arbeit in diesem Repository.

---

## Was das hier ist

Workspace fuer die Entwicklung des **DocuPi-3000** — ein portables Felddiagnose- und Dokumentationstool fuer industrielle Maschinen (Sterilisatoren, RDG). Laeuft auf Raspberry Pi, liest Maschinenprotokolle via RS232/S-Bus und generiert PDF-Dokumentationen.

**Diese Datei (CLAUDE.md) ist das Fundament.** Halte sie aktuell.

---

## Projektbeschreibung

Das DocuPi-3000 ist ein Raspberry Pi-basiertes System, das:
- Sterilisator-Chargenprotokolle via RS232 mitliest und aufzeichnet
- Echtzeit-Dashboard im Browser anzeigt (lokales WLAN/Hotspot)
- PDF-Protokolle mit Charts generiert
- Drucker-Anbindung fuer Vor-Ort-Dokumentation bietet
- SAIA PLC Daten via S-Bus/UDP ausliest (separates Softwarepaket, fertig)

### Zwei Kommunikationswege

1. **S-Bus/UDP** fuer SAIA PLCs — Software fertig (9-Dateien-Paket)
2. **RS232** fuer WD/RDG-ECU — Protokollformat entschluesselt (UTF-16LE Klartext), Parser + PDF-Generator implementiert

---

## Workspace-Struktur

```
.
├── CLAUDE.md
├── .claude/commands/       # /prime, /create-plan, /implement, /shutdown
├── context/                # Projekt-Kontext
├── src/                    # Python-Quellcode
│   ├── pdf_generator.py    # PDF-Generierung MST (Sterilisatoren)
│   ├── chart_generator.py  # Chart-Erstellung MST
│   ├── wd_protocol_parser.py  # WD/RDG-Protokoll-Parser (.ht + RS232)
│   ├── wd_pdf_generator.py    # PDF-Generierung WD/RDG
│   ├── wd_chart_generator.py  # Temperatur-Chart WD/RDG
│   ├── print_manager.py    # Drucker-Management (CUPS, pycups)
│   ├── watchdog_manager.py # Service-Ueberwachung
│   ├── add_system_health.py # System-Health-Metriken
│   ├── patches/            # Feature-Patches (15+ Dateien)
│   ├── web/                # Web-Frontend (DocuPi-3000 Legacy)
│   │   ├── base.html       # Basis-Template
│   │   ├── dashboard.html  # Haupt-Dashboard
│   │   └── captive.html    # Captive Portal (Hotspot)
│   └── docucontrol/        # DocuControl Backend + Design-System — vollstaendiger 1:1-Spiegel von 192.168.0.171
│       ├── app.py                 # Flask-Backend, alle Routen/API-Endpunkte (2026-06-12 aus Pi uebernommen)
│       ├── config.py              # load_config/save_config (config.json)
│       ├── database.py            # SQLite-Layer (protocols-Tabelle, Pagination)
│       ├── network_manager.py     # Hotspot/LAN/Multi-Interface/Hostname/NTP/RTC/nftables
│       ├── network_storage_manager.py  # SMB/CIFS-Netzwerkfreigabe: Mount, Verbindungstest, Auto-Sync (PDFs + Captures)
│       ├── print_manager.py       # Drucker-Management (CUPS, pycups)
│       ├── storage_manager.py     # USB-Erkennung, Mount, Auto-Sync (PDFs + Captures), udev-Trigger
│       ├── static/
│       │   ├── docucontrol.css    # Kanonisches CSS (Design-Tokens + Komponenten)
│       │   ├── bootstrap/, bootstrap-icons/, socketio/  # CDN-Bibliotheken lokal vendored (Offline-Faehigkeit, 2026-06-22)
│       │   └── screensaver-logo.png
│       ├── templates/
│       │   ├── base.html          # Topbar "DocuControl by GeTmatic", 3-Tab-Nav, Footer
│       │   ├── dashboard.html     # 2 Stat-Karten + Filter + Protokoll-Tabelle + Print-Toast
│       │   ├── settings.html      # 3 Sub-Tabs: Geraete & Netzwerk / System / Live-Monitor + USB-Sync-Toggle
│       │   └── filemanager.html   # Dual-Pane intern (aus DB) + USB (Dateiliste rekursiv)
│       └── app_additions.py       # Context Processor + /api/protocols (Inhalt bereits in app.py integriert, Datei als Referenz behalten)
├── tests/                  # Test-Skripte
│   ├── fixtures/           # Test-PDFs + WD390-Fixture
│   ├── test_wd_parser.py   # WD-Parser Tests (34 Tests)
│   ├── test_wd_e2e.py      # WD End-to-End Tests
│   └── *.py                # Weitere Tests
├── reference/              # Dokumentation, Konzepte
│   ├── design_handoff_docucontrol/   # hifi Design-Handoff v1/v2 (GeTmatic)
│   ├── design_handoff_docucontrol_v3/  # hifi Design-Handoff v3 (2026-06-08) — Liquid Glass, Machine-Bar, 6-Tab-Settings
│   ├── neues Design recap/  # Screenshots des laufenden DocuControl-Interface (laufend aktualisiert, zuletzt 2026-06-12)
│   ├── 3D Druck/            # Raspberry Pi 5 Geekworm X1001 NVMe-Gehaeuse (STL/STEP/3MF) — Basis fuer DocuControl-Branding-Variante (weiss, getmatic-Logo + "DocuControl"-Schriftzug), getmatic_logo.jpeg als Logo-Quelle
│   ├── 10980_Essen/         # Belimed-CD-ROM-Material (Installer/Doku) zur Uni-Essen-Maschine Nr. 10980
│   ├── getmatic_logo_stacked.svg, boot_splash_logo.svg  # Logo-Vorlagen fuer Screensaver + Boot-Splash (Pi5_Display)
│   └── getmatic_logo_transparent.png  # Freigestelltes Logo fuer 3D-Druck-Gravur (offener Punkt, s.u.)
├── plans/                  # Implementierungsplaene
├── outputs/                # Arbeitsergebnisse (Konzeptpapiere, generierte PDFs, Sicherheitsberichte)
│   ├── docupi-3000_konzept_getmatic.{md,pdf}  # Vertriebs-Konzept fuer getmatic
│   └── docucontrol_owasp_*.{md,pdf}  # OWASP-Sicherheitsberichte (Web-App + Host-Ebene, 2026-06-22)
├── backups/                # Pi-Backups (komplette Snapshots, gitignored)
│   ├── pi-backup-2026-04-13/  # DocuPi-3000 nach Feldtest Helios Krefeld
│   ├── pi-backup-2026-06-08/  # DocuControl — 13 Protokolle, 11 PDFs, Storage-Manager, Templates
│   ├── pi-backup-2026-06-11/  # DocuControl — Code+Patches, DB, Configs, Captures, System-Configs
│   └── pi-backup-2026-06-12/  # DocuControl — Code, DB, Configs (inkl. Netzwerk-Speicherort), 14 PDFs, 37 Captures, Logs, System-Configs
├── secrets/                # Passwort-Material, lokal/gitignored (2026-06-22) — NIE committen
│   └── docucontrol_passwort_vorschlaege.{md,pdf}  # Generierte Passwoerter zur Rollout-Freigabe
└── scripts/                # Hilfsskripte
    ├── fix_ssh.sh
    ├── render_konzept_pdf.py     # Markdown -> PDF (WeasyPrint) fuer outputs/
    ├── render_owasp_report_pdf.py  # Markdown -> PDF fuer OWASP-Sicherheitsberichte
    ├── deploy_docucontrol_design.sh   # Deployment-Script fuer Linux/Mac
    ├── deploy_docucontrol_win.ps1     # Deployment-Script fuer Windows (OpenSSH)
    ├── send_test_charges.py  # Sendet simulierte Belimed-Protokolle via TCP/9100 (UTF-16LE, 3 Templates)
    └── saia_test_toolkit/
```

---

## Commands

- `/prime` — Session-Start, Kontext laden
- `/create-plan` — Implementierungsplaene erstellen
- `/implement` — Plaene umsetzen
- `/shutdown` — Session sauber beenden

---

## Wichtiger Kontext

- Hardware: Raspberry Pi — DocuPi-3000 (SSH: belimed@192.168.178.83, zu Hause) | DocuControl (SSH: docucontrol@192.168.0.171, bei getmatic) | Pi5_Display (SSH: `ssh docucontrol2`, 192.168.0.218)
- SSH fuer DocuControl: Alias `ssh docucontrol` (Host 192.168.0.171, User docucontrol, IdentityFile `~/.ssh/docucontrol_id`), Passwort: Xtend1478 (fuer sudo)
- SSH fuer Pi5_Display: Alias `ssh docucontrol2` (Host 192.168.0.218, User docucontrol, IdentityFile `~/.ssh/docucontrol_id`), sudo-Passwort seit 2026-06-22 individuell + nicht mehr im Klartext hier dokumentiert (siehe lokale `secrets/`-Ablage) — SSH-Login ohnehin Key-only (PasswordAuthentication=no)
- Langfristiges Ziel: CE-zertifizierte Linux-Controller (Unipi Neuron / RevPi Connect)
- Geschaeftsmodell: Softwarelizenz + Sensor-Kit
- Erster Feldtest abgeschlossen: 3 Wochen, 140 Chargen, Helios Krefeld (Belimed 9-6-18 HS2)
- Erster Kunden-Deal in Umsetzung ueber externen Vertriebspartner getmatic — Ethernet-Print-Abgriff statt RS232

## DocuControl (zweite Hardware-Linie) — WEB-INTERFACE PRODUKTIV

**DocuControl** ist der Whitelabel-Name fuer die Kunden-Hardware ueber getmatic.
- Erster Einsatz geplant: **Tierlabor Uni Essen** (Maschinentyp: Belimed PST 14-8-12 HS1, echter Druckauftrag noch ausstehend)
- Pi 5 bei getmatic: Kernel 6.18.33, RTC DS3231, WLAN off, Service docucontrol.service aktiv
- Architektur: TCP/9100-Capture -> Parse -> PDF -> DB (automatisch), USB-Drucker via CUPS
- SSH: `ssh docucontrol` (Alias, siehe `~/.ssh/config`), Passwort: Xtend1478 (fuer sudo)

### DocuControl Web-Interface (2026-06-03 vollstaendig deployed)

**Drucker:** Epson XP-4150 als `DocuPrinter` via CUPS/IPP Everywhere (`ipps://EPSON41D474.local:631/ipp/print`)
- Drucker-Erkennung via **USB sysfs** (`/sys/bus/usb/devices/`, `bInterfaceClass=07`): physisch angesteckt = verbunden, unabhaengig von CUPS-State oder Netzwerk
- Modellname aus USB-Deskriptor (`manufacturer` + `product` aus sysfs), kein ipptool noetig
- Bei kein USB-Drucker: `printer_count=0`, `printer=''` → Settings zeigt "Kein Drucker angeschlossen"

**Maschinenname + IP (2026-06-09 konfigurierbar):**
- `MACHINE_NAME`/`MACHINE_PROTOCOL` nicht mehr hardcodiert — kommen aus `config.json` Sektion `machine`
- Settings-Card "Anlage": Maschinenname + IP editierbar, manueller Ping-Button
- Machine-Bar-Status basiert auf ICMP-Ping zur konfigurierten IP (60s-Intervall), nicht mehr TCP-Receiver-Status
- Bei leerer IP: "IP nicht konfiguriert" im Dashboard

**Neue API-Endpunkte (alle in `src/docucontrol/app.py`):**
- `GET /api/machine/config` — Maschinenname, Maschinennummer (`machine_nr`), IP, Protokoll lesen
- `POST /api/machine/config` — Maschinenname, Maschinennummer + IP speichern (in config.json)
- `GET /api/machine/ping` — ICMP-Ping zur konfigurierten IP; `{reachable, configured, ip, latency_ms}`
- `GET /api/dashboard/stats` — Dashboard-Karten: `max_charge_nr` (höchste Charge-Nr. numerisch aus raw_data), Heute, Monat, Vormonat-Trend (2026-06-09)
- `GET /api/protocols` — paginiert (SQL LIMIT/OFFSET), filterbar, sortierbar; Charge-Nr. + Programm als DB-Spalten (charge_nr_int, program) — kein raw_data-Scan mehr
- `GET /api/protocols/programs` — distinct Programmnamen via `SELECT DISTINCT program` (kein raw_data-Scan)
- `DELETE /api/protocols/<id>` — loescht DB-Eintrag + PDF-Datei
- `GET /api/printer/ready` — Drucker-Bereitschaft (`ready: bool`, `printer` = echter Modellname)
- `GET /api/printer/status` — CUPS-Status mit Drucker-Liste; `printer`/`model` = echter Modellname; `printer_count` = Anzahl
- `POST /api/printer/detect` — Drucker-Erkennung (intern, Button in Settings entfernt)
- `POST /api/printer/test` — Testdruck
- `POST /api/printer/auto_print` — Auto-Druck Toggle
- `POST /api/print/<id>` — Drucken per Protokoll-ID
- `GET /api/capture/collector` — Datensammlermodus lesen (`{collector_mode: bool}`)
- `POST /api/capture/collector` — Datensammlermodus setzen (`{enabled: bool}`) → schreibt in capture_config.json
- `GET /api/tcp_capture/captures` — Liste aller Raw-Captures in `data/raw_captures/` `[{name, size}]`
- `GET /api/tcp_capture/captures/<fname>` — Download einzelner Capture-Datei
- `DELETE /api/tcp_capture/captures/<fname>` — Loescht `.txt` + `.bin` Paar (2026-06-10)
- `POST /api/storage/sync/captures` — Kopiert alle Captures auf USB nach `docucontrol/captures/` (2026-06-10)
- `POST /api/protocols/bulk-delete` — Batch-Loeschung `{ids:[...]}` DB + PDF-Datei (2026-06-10)
- `POST /api/protocols/bulk-copy-usb` — Kopiert ausgewaehlte PDFs auf USB `{ids:[...]}` (2026-06-10)
- `POST /api/tcp_capture/captures/bulk-copy-usb` — Kopiert ausgewaehlte Captures auf USB `{basenames:[...]}` (2026-06-10)
- `GET /api/storage/captures/usb` — Liste Captures vom USB-Stick `[{name, path, size_human, has_bin, modified}]` (2026-06-10)
- `GET/POST /api/storage/network/config` — Netzwerk-Speicherort (SMB) Konfiguration lesen/speichern; GET liefert `has_password` statt Klartext-Passwort (2026-06-12)
- `GET /api/storage/network/status` — Mount-Status, freier Speicher, letzter Sync, `last_error` (2026-06-12)
- `POST /api/storage/network/test` — Testet SMB-Verbindung mit (ggf. uebergebenen) Zugangsdaten, gibt deutsche Fehlermeldung zurueck (2026-06-12)
- `POST /api/storage/network/sync` — Sofort-Sync PDFs + Rohdaten-Captures auf Netzwerk-Freigabe (2026-06-12)

**Stabilitaets-Fixes (2026-06-03):**
- `os._exit(0)` in graceful_shutdown: Restart-Dauer 15s SIGKILL -> **47ms sauber**
- `request.get_json(silent=True)` in allen POST-Routen
- `d.tcp_enabled` statt `d.enabled` ueberall konsistent

**USB Auto-Sync (2026-06-08 implementiert, 2026-06-10 erweitert):**
- udev-Rule `/etc/udev/rules.d/99-docucontrol-usb.rules` + Trigger-Script `/usr/local/bin/docucontrol-usb-trigger.sh`
- Trigger-Datei: `/var/lib/docucontrol/usb.trigger` (wegen PrivateTmp=yes im Service)
- Sofort-Sync beim Einstecken + Intervall-Sync alle 15 min
- Auto-Sync synchronisiert **PDFs und Captures** gleichzeitig (storage_manager.py: `sync_pdfs_to_usb()` + `sync_captures_to_usb()`)
- PDF-Pfad auf USB: `DocuControl/` | Captures-Pfad auf USB: `docucontrol/captures/`
- Auto-Sync-Toggle in Einstellungen (Geraete & Netzwerk)
- Sudoers: `/etc/sudoers.d/docucontrol-storage` (mount, umount, blkid, dosfsck ohne Passwort)

**Netzwerk-Speicherort / SMB-Sync (2026-06-12 implementiert):**
- Neues Modul `network_storage_manager.py`: mountet eine SMB/CIFS-Freigabe (Windows-Rechner im
  Kliniknetz) nach `/mnt/docucontrol_share` und synct PDFs + Rohdaten-Captures automatisch
- Settings-Card "Netzwerk-Speicherort" (Tab Geraete & Netzwerk, nach USB-Synchronisation):
  Server/Freigabename/Benutzer/Passwort/Domain, Status-Badge, "Verbindung testen"/"Jetzt sync."/"Speichern"
- Konfiguration in `data/network_storage_config.json` (eigene Datei, analog `sync_config.json`),
  Zugangsdaten zusaetzlich in `data/network_share.cred` (chmod 600, `credentials=`-Option fuer
  `mount.cifs` — Passwort landet nicht in der Prozessliste)
- Passwort wird **nie** ueber `GET /api/storage/network/config` zurueckgegeben (nur `has_password`)
- Pfade auf der Freigabe identisch zum USB-Stick: `DocuControl/` (PDFs) + `docucontrol/captures/` (Rohdaten)
- Hintergrund-Thread (`start_network_sync()`, 30s-Takt, Mount-Backoff 60s) laeuft parallel zum
  USB-Auto-Sync; Sync-Intervall konfigurierbar (Default 15 Min, wie USB)
- Verbindungstest uebersetzt `mount.cifs`-Fehler in deutsche Klartexte (Zugriff verweigert /
  Freigabe nicht gefunden / Server nicht erreichbar)
- Sudoers: keine Erweiterung noetig — bestehende `NOPASSWD: /usr/bin/mount, /usr/bin/umount, ...`
  Zeile in `/etc/sudoers.d/docucontrol-storage` deckt `mount -t cifs` bereits ab (verifiziert)
- Server/Freigabename werden per Regex validiert, alle Mount-Aufrufe nutzen `subprocess.run([...],
  shell=False)` (Listenform) — kein Shell-Injection-Risiko bei diesem neuen Code

**Datei-Manager Globaler Modus-Toggle (2026-06-10 implementiert):**
- Toggle-Buttons "PDF-Protokolle" / "Rohdaten" oberhalb beider Panes — ein Klick steuert beide Seiten gleichzeitig
- PDF-Modus: linke Pane = interne PDFs, rechte Pane = USB-PDFs
- Rohdaten-Modus: linke Pane = interne Captures, rechte Pane = USB-Captures (`docucontrol/captures/` auf USB)
- USB-Pane zeigt `.txt`-Captures mit `[+bin]`-Badge wenn passendes `.bin` vorhanden
- Loeschen, Bulk-Copy, Sync-Button adaptieren sich je nach Modus

**Netzwerk-Management (2026-06-08 implementiert):**
- Root-Cause IP-Bug behoben: `/etc/sudoers.d/docucontrol-network` (nmcli, ip, hostnamectl, timedatectl, hwclock ohne Passwort)
- **Aktuelle IP: 192.168.0.171** (DHCP, Router gibt immer dieselbe IP via MAC-Binding)
- `network_manager.py` v3: Multi-Interface, Hostname, NTP/RTC, VLAN, korrekte Fehler-Propagierung
- Neue API-Endpunkte:
  - `GET /api/network/interfaces` — alle verfuegbaren NICs mit Status
  - `GET/POST /api/network/iface/<dev>/status|static|dhcp` — Interface-Konfiguration
  - `GET/POST /api/system/hostname` — Hostname lesen/setzen (hostnamectl)
  - `GET/POST /api/system/ntp` — NTP-Server + RTC DS3231 Status
  - `POST /api/system/time/manual` — manuelle Zeitstellung + hwclock --systohc
- Settings-Tab "Geraete & Netzwerk" komplett neu: Schnittstelle 1 (DHCP/Statisch, DNS2, VLAN), Schnittstelle 2 (USB-Ethernet Dropdown), Hostname-Card, Zeit & Uhr (RTC + NTP optional)

**Live-Monitor Fix (2026-06-08):**
- `updateTerminal()` las `d.text` statt korrektem `d.content` — Terminal war immer leer
- Fix: `d.content || d.text` in settings.html

**IP-Anzeige Live-Poll (2026-06-08):**
- `pollCurrentIPs()` in settings.html: alle 5s nur current_ip/mac/speed/badge aktualisieren (keine Input-Felder)
- Poll laeuft nur wenn Tab "Geraete & Netzwerk" aktiv, stoppt bei Tab-Wechsel
- nftables-Bug gefixt: `_write_nftables_conf()` wird jetzt VOR `nmcli con down/up` aufgerufen (verhindert Dashboard-Ausfall beim DHCP-Wechsel)
- nftables-Regel auf Interface-basiert umgestellt: `iif eth0` statt `ip daddr <static-ip>` (DHCP-kompatibel)

**Settings-Optimierungen (2026-06-09):**
- Topbar-Badge (rot/gruen "Aktiv/Getrennt") entfernt — Status nur noch in Machine-Bar
- Settings Card "Anlage" (erste Card): Maschinenname + IP editierbar, Ping-Button
- Settings Card "Drucker": "Drucker erkennen"-Button entfernt, Label -> "Verbundener Drucker", zeigt echten Modellnamen oder "Kein Drucker angeschlossen"
- Machine-Bar-Status basiert jetzt auf ICMP-Ping zur konfigurierten Maschinen-IP (60s-Intervall)
- Drucker-Erkennung via sysfs USB (bInterfaceClass=07) statt TCP-Check — physisch angesteckt = verbunden
- Auto-Print Bug gefixt: `_process_job()` in tcp_print_capture.py prueft jetzt print_config.json und druckt PDF automatisch nach Empfang
- Dashboard Print-Button Race-Condition gefixt: `loadPrinterStatus()` gibt Promise zurueck, `loadProtocols()` wartet darauf

**TCP-Test-Protokolle (2026-06-09 gesendet):**
- CH021709–CH021713: 5 Testchargen (Instrumente 134°C + Bowie Dick) erfolgreich empfangen, PDF generiert, gedruckt
- Auto-Print Pipeline bestaetigt: TCP → Parse → Chart → PDF → CUPS-Job < 1 Sekunde

**Datensammlermodus (2026-06-10 implementiert, UI-Fix 2026-06-10):**
- Toggle in Settings-Card "TCP-Empfang": aktiviert Sammelmodus ohne PDF-Generierung
- Wenn aktiv: TCP-Job → `.bin`+`.txt` gespeichert → Rohtext per `/usr/bin/lp` direkt gedruckt — kein Parse, kein PDF, kein DB-Eintrag
- Wenn inaktiv: normale Pipeline (Parse → PDF → DB → Auto-Print)
- **Merker**: Flag `collector_mode` in `capture_config.json` — von API geschrieben, von `_handle()` per Job gelesen
- **API**: `GET/POST /api/capture/collector` — liest/schreibt Flag; POST gibt `{collector_mode, ok}` zurueck
- **UI**: `window.toggleCollectorMode(enabled)` (global scope) — POST + Toast-Bestaetigung; `loadCollectorMode()` einmalig beim Seitenaufruf
- **Browser-Cache-Fix**: `Cache-Control: no-store` in Flask `@after_request` fuer `/`, `/settings`, `/files`
- Amber-Warn-Banner im UI wenn aktiv; Toast-Bestaetigung beim Schalten
- Zweck: Protokollvarianten der PST 14-8-12 HS1 erfassen um `protocol_parser.py` zu kalibrieren

**Rohdaten-Ansicht im Dateimanager (2026-06-10 implementiert):**
- Dropdown "Ansicht" ueber der linken Dateiliste: "PDF-Protokolle" (Standard) oder "Rohdaten (.txt / .bin)"
- Rohdaten-Modus zeigt alle `.txt`-Captures aus `data/raw_captures/` mit Datum (aus Dateiname), Groesse, Download-Buttons
- Pro Zeile: `.txt`-Download, `.bin`-Download (falls vorhanden), Einzelloeschen (loescht `.txt` + `.bin` Paar)
- Sync-Button adaptiv: in Rohdaten-Modus → "Captures → USB" ruft `POST /api/storage/sync/captures` auf

**v3 Makeover Settings + Datei-Manager (2026-06-11 deployed):**
- `settings.html`: `btn-primary` fuer alle Speichern/Setzen-Buttons, `btn-glass` fuer Ping/Testdruck/Sync, `btn-outline-danger` fuer Reboot
- `filemanager.html`: Modus-Toggle auf `.segmented` CSS-Klasse umgestellt (kein Inline-Style), `switchMode()` JS nutzt `classList.toggle('active')`
- Beide Seiten haben `.lede`-Untertitel im Page-Head

**Dashboard-Bugs behoben (2026-06-11):**
- "Chargen heute"-Zaehler: Query auf `date(timestamp) = ?` (SQLite) — war kaputt wegen ISO-T vs Space-Trenner-Bug beim String-Vergleich
- Dauer-Spalte: `_PROG_ENDE_RE` = `^\s*(\d+):(\d+)\s+Programm\s+Ende` liest MM:SS direkt aus raw_data (alte ISO-Timestamp-Regexes trefren nie)

**USB-Ethernet Schnittstelle 2 (2026-06-11 konfiguriert + Bugs behoben):**
- eth1 statisch: `192.168.0.181/24`, Gateway `192.168.0.1` — persistent in NM-Keyfile
- nftables `/etc/nftables-docucontrol.conf`: interface-basierte Regeln `iif eth0` + `iif eth1` (beide IPs erreichbar auf Port 80 + 9100)
- `network_manager.py`: `_write_nftables_conf()` generiert immer interface-basierte Regeln — nicht mehr IP-spezifisch (Bug: IP-basiert ueberschrieb eth0-Regel beim eth1-Setup)
- `network_manager.py`: `connected`-Feld aus `/sys/class/net/<iface>/carrier` (physischer Link: 1=Kabel da, 0=kein Kabel) statt IP-Check
- `settings.html`: `iface2StatusBadge` im Card-Header von Schnittstelle 2 — zeigt Verbunden/Getrennt
- `settings.html`: `applyIfaceStatus()` setzt `iface2Enabled`-Checkbox korrekt aus `d.enabled` (war immer unchecked)

**Skalierbarkeit 10.000+ Protokolle (2026-06-11 deployed):**
- DB: `protocols`-Tabelle hat neue Spalten `charge_nr_int INTEGER` + `program TEXT` (aus raw_data extrahiert, indiziert)
- `database.py`: `save_protocol()` extrahiert + speichert charge_nr_int + program beim Insert direkt
- `api_protocols`: echte SQL-Paginierung (LIMIT/OFFSET), COUNT(*) fuer Total — kein vollstaendiges Laden mehr
- `api_protocols_programs`: `SELECT DISTINCT program` statt raw_data-Scan
- `filemanager.html`: Paginierung (50/Seite, Mini-Pager mit Seitenangabe) fuer interne PDF-Liste
- Migrations-Script: `scripts/migrate_add_charge_program_cols.py` (bereits ausgefuehrt)

**Test-Chargen-Sender (2026-06-11):**
- `scripts/send_test_charges.py`: 3 Templates (Instrumente 134°C / Bowie Dick / Instrumente 121°C), UTF-16LE+BOM, CLI-Flags
- 10 Chargen CH021720–021729 gesendet + verifiziert: duration HH:MM:SS, alle 3 Programme erkannt, Dashboard "Chargen heute" korrekt
- Verwendung: `python3 scripts/send_test_charges.py [--count N] [--interval SECS] [--start-charge N] [--dry-run]`

**PDF-Dateiname (2026-06-11):** `{datum}_{zeit}_{charge}_{masch_nr}_{geraet}` → z.B. `2026-06-11_175105_CH021732_27163_Belimed_PST_14-8-12_HS1.pdf`
- `masch_nr` kommt aus `config.json machine.machine_nr` (konfigurierbar in Settings → Anlage → Maschinennummer)
- Leer = kein doppelter Unterstrich dank bestehender `while sep+sep` Bereinigung in `build_filename()`
- Settings-Card "Anlage": hat jetzt drittes Feld "Maschinennummer" zwischen Maschinenname und IP
- Datei-Manager Mode-Toggle (2026-06-11 wiederhergestellt): `.segmented` Toggle "PDF-Protokolle / Rohdaten" oberhalb der two-col-Div

**Settings-Fixes (2026-06-11 in Workspace committed, waren vorher Pi-only Patches):**
- `iface2StatusBadge` im Card-Header von Schnittstelle 2 — zeigt Verbunden/Getrennt (wie Schnittstelle 1)
- `applyIfaceStatus()` setzt `iface2Enabled`-Checkbox korrekt aus `d.enabled` (war immer unchecked)
- USB-Stick formatieren: Button in USB-Synchronisation-Card, POST `/api/storage/usb/format` `{label:"DOCUCTRL"}`, FAT32, Bestätigungs-Dialog, Danger-Styling

**GitHub Collaboration (2026-06-11):** Thomas Glander (`glanderthomas-1478`) als Collaborator mit Push-Zugriff auf `lordboombastic/claude-workspace-docupi` hinzugefügt

**Backend-Sync Pi → Repo (2026-06-12):**
- `src/docucontrol/` ist jetzt ein **vollstaendiger 1:1-Spiegel** der Pi-Codebasis: `app.py`, `config.py`, `network_manager.py`, `storage_manager.py` vom Pi (Stand 2026-06-10/12) ins Repo geholt und gepusht — keine Pi-only-Dateien mehr
- `network_manager.py`: `connected` jetzt via `/sys/class/net/<iface>/carrier`, nftables interface-basiert (`iif eth0`+`iif eth1`)
- `storage_manager.py`: `sync_captures_to_usb()` + `USB_CAPTURE_SUBDIR` ergaenzt (Auto-Sync synct jetzt PDFs + Captures)
- GitHub-Backup vor dem Sync: `backups/github-backup-2026-06-12/claude-workspace-docupi.bundle` (Bundle, Commit `e4cc7d1`)
- **Wichtiger Hinweis:** Vor jedem Deploy auf den Pi pruefen, ob die Pi-Version neuer ist als das Repo (z.B. `md5sum`/`diff` gegen `src/docucontrol/`), sonst werden Pi-Fixes ueberschrieben — Workflow jetzt: Aenderungen direkt im Repo machen, dann per `scp`/Deploy-Skript auf den Pi spielen

**Netzwerk-Speicherort-Einrichtung — ERLEDIGT (2026-06-12):**
- Auf Thomas' Windows-Rechner (192.168.0.86) dediziertes lokales Konto `docucontrol` angelegt
  (PasswordNeverExpires, UserMayNotChangePassword), `C:\temp` als SMB-Freigabe `temp` mit
  Vollzugriff fuer `docucontrol` freigegeben, NTFS-Rechte via
  `icacls --% C:\temp /grant docucontrol:(OI)(CI)M` (PowerShell-Klammer-Workaround: `--%`
  Stop-Parsing-Token oder cmd.exe verwenden, sonst `(OI)(CI)` Parse-Fehler)
- DocuControl-Config aktualisiert: Server `192.168.0.86`, Freigabe `temp`, User `docucontrol`,
  Domain leer (lokales Konto, kein `GIGANETZ`-Workgroup-Eintrag), Passwort gesetzt
- Verbindungstest: `success:true` ("Verbindung erfolgreich")
- Sofort-Sync: 88 Dateien uebertragen (14 PDFs + 74 Captures), Status `mounted:true`,
  `last_error:""`, 281.6 GB frei auf `C:\temp`-Laufwerk
- Verifiziert auf Windows-Seite: `C:\temp\DocuControl\2026\2026-06\*.pdf` +
  `C:\temp\DocuControl\captures\*.{txt,bin}` vollstaendig vorhanden
- Hintergrund-Thread synct jetzt automatisch alle 15 Min parallel zum USB-Sync
- Validierungs-Checkliste in `plans/2026-06-12-netzwerk-speicherort-sync.md` jetzt vollstaendig
  abgehakt — Feature komplett abgeschlossen

**PDF-Branding + Maschinen-Nr (2026-06-12 behoben):**
- `src/pdf_generator.py`: `generate_pdf()` ueberschreibt `protocol_data["maschinen_nr"]` jetzt immer mit
  `config["machine"]["machine_nr"]` (statt der aus dem Rohprotokoll geparsten, ggf. veralteten Nummer)
  — Kopf-Bereich ("Nr: 10980") und Footer ("... Nr:10980 / ...") zeigen damit konsistent die
  konfigurierte Maschinennummer
- Footer: "DocuPi-3000" -> "DocuControl" (Geraete-Zeile) und "DocuPi" -> "DocuControl"
  (Branding unten rechts, Schriftgroesse 14 -> 10 damit der Text in die 28mm-Zelle passt)
- `build_filename()`: fehlenden `masch_nr`-Token (`config["machine"]["machine_nr"]`) aus Pi-Version
  nachgezogen — lokale Datei war nicht mehr 1:1-Spiegel
- Verifiziert per Testcharge CH021740 + `pdftotext`/`pdftoppm`-Render: "Nr: 10980", "DocuControl"
  korrekt in Kopf- und Fusszeile

**OWASP-Sicherheitsreview + Fixes (2026-06-21/22):**
- Manuelles Review nach OWASP Top 10 (Code-Review + Live-Endpunkt-Tests) auf Pi5_Display durchgefuehrt
- **Kritisch (sofort behoben):**
  - Hardcodierte Secrets (`SECRET_KEY`, Service-Passwort) aus dem Quellcode entfernt — werden jetzt
    beim ersten Start generiert/persistiert in `data/auth_secrets.json` (chmod 600, analog
    `network_share.cred`), `_load_or_create_auth_secrets()` in `app.py`
  - Brute-Force-Schutz fuer Service-Login: 5 Fehlversuche → 5 Minuten Sperre (in-memory
    `_login_failures`, `_login_locked_out()`)
  - XSS-Luecke in `escHtml()` (dashboard.html + filemanager.html) — Single-Quote-Escaping ergaenzt
    (filemanager.html escapte vorher nicht einmal doppelte Anfuehrungszeichen)
- **Weitere Punkte (2026-06-22 behoben):**
  - Broken Access Control: `_require_service()`-Guard auf allen destruktiven Endpunkten ergaenzt
    (`/api/protocols/<id>` DELETE, `/api/protocols/bulk-delete`, `/api/tcp_capture/captures/*`
    DELETE/bulk-delete, `/api/storage/delete`, `/api/pending-charges/<id>` DELETE) — vorher konnte
    jeder ohne Service-Anmeldung Protokolle/Captures loeschen
  - CORS: Flask-SocketIO `cors_allowed_origins="*"` entfernt, Same-Origin-Default reicht (Web-UI und
    Socket.IO laufen immer auf demselben Host)
  - CSRF: `SESSION_COOKIE_SAMESITE="Lax"` fuer das Service-Login-Cookie gesetzt
  - HTTPS: zusaetzlicher TLS-Listener auf Port 5443 (selbstsigniertes Zertifikat, generiert beim
    ersten Start in `data/tls/`, `_ensure_self_signed_cert()`), laeuft **parallel** zum bestehenden
    Port 5000 in eigenem Thread — Kiosk-URL `http://localhost:5000` bleibt bewusst unveraendert, um
    den produktiven Kiosk nicht durch Zertifikatswarnungen zu gefaehrden; nftables
    `docucontrol_redirect`-Tabelle um `iif eth0/eth1 tcp dport 443 redirect to :5443` erweitert
  - Dockerfile: `openssl`-Paket fuer Zertifikatsgenerierung ergaenzt, Port 5443 exponiert
- Alle Fixes auf Pi5_Display deployed (Docker-Rebuild noetig wg. Dockerfile-Aenderung), live verifiziert:
  HTTP 200 + HTTPS 200, unauthentifizierte DELETE-Requests → 403, authentifizierte DELETE-Requests
  funktionieren, Lockout nach 5 Fehlversuchen ausgeloest und wieder zurueckgesetzt
- **Verbleibend (nicht kritisch, bewusst nicht behoben):** offener TCP/9100 ohne Auth (Protokoll-Format
  erlaubt keine Authentifizierung, Risiko durch LAN-only-Betrieb gemindert), kein automatisiertes
  Audit-Logging fuer alle Aktionen (nur `log_event()` fuer ausgewaehlte Ereignisse)

**OWASP Host-Level-Audit + Fixes auf Pi5_Display (2026-06-22):**
- Zusaetzlich zum Web-App-Review (s.o.) Host-Ebene geprueft: SSH-Konfig, sudo-Rechte, offene Ports,
  Docker-Privilegien, Updates — Bericht in `outputs/docucontrol_owasp_host_sicherheitsbericht.{md,pdf}`
- **rpcbind deaktiviert** (`systemctl disable --now rpcbind.service rpcbind.socket`): war ungenutzte
  Abhaengigkeit von `rpd-common` (Raspberry-Pi-Desktop-Paket, nicht fuer den Cage/Chromium-Kiosk
  benoetigt), lauschte unnoetig auf Port 111 (TCP+UDP, alle Interfaces). Pakete nicht entfernt,
  nur Dienst gestoppt — kein Abhaengigkeits-Risiko. Port 111 verifiziert geschlossen.
- **SSH `PasswordAuthentication no`** gesetzt (system-only `/etc/ssh/sshd_config`, nicht im Repo):
  vor der Umstellung Pubkey-Login explizit mit frischer Verbindung verifiziert, nach der Umstellung
  per `systemctl reload ssh` aktiviert und erneut verifiziert (Key-Login funktioniert, Passwort-Login
  wird mit "Permission denied (publickey)" abgelehnt)
- **Verbleibend, bewusst zurueckgestellt:** Klartext-Passwort `Xtend1478` in dieser CLAUDE.md (mehrfach,
  ueber die gesamte Geraeteflotte identisch) — Nutzer hat Behebung explizit auf spaeter verschoben
  (2026-06-22), da Passwortrotation ueber mehrere Produktivgeraete koordiniert erfolgen muss; Docker
  `privileged: true` + `network_mode: host` (funktional begruendet durch CUPS/nmcli/USB-Mount/Watchdog,
  Reduktion auf gezielte Capabilities braucht sorgfaeltige Einzelanalyse + Testfenster, nicht spontan
  umgesetzt)

**Passwort-Rollout Pi5_Display/docucontrol3 (2026-06-22):** Individuelle, zufaellig generierte
Passwoerter fuer SSH/sudo (Linux-Account `docucontrol`) und Web-UI-Service-Login live gesetzt und
verifiziert (altes Passwort abgelehnt, neues funktioniert, App nach Container-Restart weiterhin
fehlerfrei). DocuControl (.171) und DocuPi-3000 (.83) waren beim Rollout-Versuch nicht erreichbar
(andere Netze/Standorte) — dort gilt also weiterhin das alte gemeinsame Passwort, Rollout steht noch
aus. SMB-Maschinenkonto auf 192.168.0.86 (von .171 + .218 gemeinsam genutzt) ebenfalls noch nicht
geaendert — kein Remote-Admin-Zugriff (RDP/WinRM) auf den Windows-Rechner von dieser Session aus.
Neue Passwoerter liegen in `secrets/docucontrol_passwort_vorschlaege.{md,pdf}` (lokal, per
`.gitignore` ausgeschlossen, nicht im Repo).

**nftables-Boot-Race behoben (2026-06-13):**
- Nach Reboot war Web-Interface auf beiden IPs nicht erreichbar (Ping/SSH ok, `docucontrol.service`
  aktiv, aber `curl` -> Connection refused). Ursache: `nftables.service` startete vor Enumeration
  des USB-Ethernet-Adapters (`eth1`, RTL8153) und scheiterte komplett mit "Interface does not exist"
  fuer die `iif eth1`-Regel in `/etc/nftables-docucontrol.conf` — dadurch fehlte die komplette
  Port-80->5000-Weiterleitung (auch fuer eth0)
- Sofort-Fix: `systemctl restart nftables`
- Permanent-Fix (system-only, nicht im Repo): `/etc/systemd/system/nftables.service.d/override.conf`
  mit `After=`/`Wants=sys-subsystem-net-devices-eth1.device` + `ExecStartPre=/bin/sleep 2`,
  `systemctl daemon-reload` ausgefuehrt und verifiziert

**Drucker USB-Setup (2026-06-15 gefixt):**
- Problem: DocuPrinter war als `ipps://EPSON41D474.local:631/ipp/print` (WiFi) konfiguriert — druckte nicht wenn Drucker nur per USB angeschlossen
- Epson XP-4150 nutzt auf modernem Debian **IPP-over-USB** via `ipp-usb`-Dienst (kein klassisches `usb://`-Backend)
- `print_manager.py`: `setup_usb_printer()` erkennt jetzt beide URI-Typen: `direct usb://` (klassisch) und `network ipp://...(USB)._ipp._tcp.local` (IPP-over-USB)
- Verwendet `sudo /usr/sbin/lpinfo` (nicht im PATH, braucht root)
- Sudoers: `/etc/sudoers.d/docucontrol-cups` mit `NOPASSWD: /usr/sbin/lpadmin, /usr/sbin/lpinfo`
- Startup-Auto-Setup: beim Service-Start wird USB-Drucker automatisch konfiguriert
- Settings-Button "USB einrichten" fuer manuellen Reset
- Verifiziert: DocuPrinter jetzt auf `ipp://EPSON%20XP-4150%20Series%20(USB)._ipp._tcp.local/`, Druck funktioniert

**Netzwerk-Speicherort auf gland-Rechner umgezogen (2026-06-15):**
- SMB-Freigabe `\\192.168.0.99\temp` eingerichtet (lokales Konto `docucontrol`, C:\temp, FAT-Rechte)
- Routing: Pi eth1 (192.168.0.181) → 192.168.0.99 via persistente Host-Route (`nmcli connection modify docucontrol-eth1 +ipv4.routes "192.168.0.99/32"`)
- Pi SSH-Zugang via paramiko (Python) mit Passwort (SSH-Key fehlt auf diesem Rechner)

**USB + Netzwerk Sofortkopie (2026-06-15 implementiert):**
- `copy_pdf_to_usb_instant()` in `tcp_print_capture.py` eingehängt: PDF landet sofort nach Charge auf USB-Stick (nicht erst nach 15-Min-Zyklus)
- `copy_pdf_to_network_instant()` neu in `network_storage_manager.py` + in `tcp_print_capture.py` eingehängt: PDF sofort auf Netzwerk-Freigabe
- Root-Cause USB-Sync-Problem: `copy_pdf_to_usb_instant()` war zwar in storage_manager.py definiert, wurde aber nirgendwo aufgerufen
- USB Auto-Mount Fix: Warning-Log bei Mount-Fehler, 10s Sleep nach Lazy-Unmount, Mount-Versuch in copy_pdf_to_usb_instant()
- USB Device-Name: kann nach Re-Enumeration wechseln (sdb1 -> sda1) — detect_usb_device() findet es dynamisch via lsblk

**VPR-Template in send_test_charges.py (2026-06-15):**
- Template 4 "Aufheizen & VPR" (Index 3): Basislaufzeit 46 min, Leckrate 0.7 mbar/min, "PROGRAMM BEENDET NICHT STERIL"
- Verwendung: `--sequence 3`

**Naechster Schritt (Tierlabor):** Echten Druckauftrag vom Tierlabor-Geraet (Belimed PST 14-8-12 HS1) empfangen, Maschinennummer des Tierlabor-Geraets in Settings eintragen, Installation vor Ort vorbereiten

---

## Pi5_Display (dritte Hardware-Linie) — IN BETRIEB SEIT 2026-06-16

Zweiter unabhaengiger DocuControl-Pi mit HDMI-Kiosk-Display.
- IP: eth0 192.168.0.218 (DHCP), eth1 192.168.0.107 (statisch), SSH: `ssh docucontrol2` (Key-only seit 2026-06-22), sudo-Passwort individuell (siehe lokale `secrets/`-Ablage, nicht in CLAUDE.md)
- OS: Debian Trixie aarch64, Kernel 6.12.75, Pi 5 (8 GB)
- Betrieb: **Docker** (`docker-compose up`, Image `docupi-docucontrol`)
- Architektur: identisch DocuControl — TCP/9100 -> Parse -> PDF -> DB, Flask :5000
- Display: HDMI + cage (Wayland-Kiosk) + Chromium → http://localhost:5000
- Webzugriff extern: http://192.168.0.218 oder http://192.168.0.107 (nftables Port 80→5000)
- Services: `docucontrol.service` (Docker), `kiosk.service` (cage+Chromium), `cups.service`, `seatd.service`, `nftables-docucontrol.service`
- App-Pfad auf Pi: `/home/docucontrol/docupi/` (Volume-gemountet in Container als `/app`)
- Docker-Befehle: `sudo docker-compose restart` (kein Rebuild noetig), `sudo docker-compose build --no-cache` (nach Dockerfile-Aenderung)
- Docker-Image enthaelt: poppler-utils (PDF→PNG), iproute2 + network-manager (nmcli), sudo, dosfstools
- Cursor: udev `99-vc4-hdmi-noinput.rules` unterdrueckt HDMI-CEC-Pointer; Touchscreen: `99-qdtech-touch.rules`
- Virtuelle Tastatur: JS-Keyboard in `base.html` oeffnet sich bei jedem Input-Fokus (QWERTZ, Umlaute)
- PDF-Viewer: Modal mit pdftoppm-Rendering (PNG pro Seite), kein Browser-PDF-Plugin noetig
- Noch offen: Maschinennummer/Name in Settings, Drucker anschliessen, eth0 statisch
- Projektdokumentation: `plans/2026-06-16-pi5-display-setup.md`

**Pi5_Display-spezifische Aenderungen (2026-06-16):**
- `app.py`: `/pdf-info/<id>` + `/pdf-page/<id>/<page>` — PDF-Seiten als PNG via pdftoppm
- `dashboard.html`: PDF-Modal-Viewer (Bilder statt iframe), PDF-Button oeffnet Modal
- `base.html`: Virtuelle Tastatur (QWERTZ+Umlaute), touchstart + inputmode=none + MutationObserver
- `network_manager.py`: docker0/br-*/veth* aus get_available_interfaces() gefiltert
- `Dockerfile`: poppler-utils + iproute2 + network-manager
- `docker-compose.yml`: /var/run/dbus gemountet fuer nmcli-Zugriff auf Host-NetworkManager

**Netzwerk-Speicherort SMB-Mount im Docker-Container gefixt (2026-06-18):**
- Root-Cause: `cifs-utils` (mount.cifs-Helper) fehlte im Docker-Image — bare `mount -t cifs` im Container
  kennt die Option `credentials=...` nicht (das ist reine mount.cifs-Funktionalitaet), der Kernel bekam
  dadurch keine echten Zugangsdaten und verband sich quasi anonym → `STATUS_ACCESS_DENIED` vom SMB-Server,
  obwohl Username/Passwort korrekt waren und der identische Mount-Befehl auf dem Host (ausserhalb des
  Containers) einwandfrei funktionierte
- Fix: `Dockerfile` um `cifs-utils` ergaenzt, Image neu gebaut (`docker-compose build --no-cache`)
- Zusaetzlich `network_storage_manager.py`: `vers=3.0` explizit in den Mount-Optionen ergaenzt (automatische
  SMB-Dialekt-Aushandlung schlug mit diesem Windows-Server fehl, explizite Versionsangabe behebt es)
- Verifiziert: Pi5_Display SMB-Sync zu `\\192.168.0.86\temp` (Konto `docucontrol`) laeuft jetzt produktiv,
  `mounted:true`, Sofort-Sync getestet (3 PDFs uebertragen)
- Lehre: Bei Docker-Containern mit `mount`-Funktionalitaet immer pruefen, ob die noetigen Userspace-Helper
  (hier `cifs-utils`) im Image installiert sind — der nackte `mount`-Befehl aus util-linux reicht nicht

---

## docucontrol3 (vierte Hardware-Linie) — Autoklavenbuch-Testgeraet, IN BETRIEB SEIT 2026-06-22

Dritter/vierter DocuControl-Pi, urspruenglich als "neuer Pi" vorbereitet, stellte sich aber als
**dieselbe physische Hardware wie Pi5_Display heraus** (SD-Karte wurde im Rahmen der SSD-Migration
neu geflasht, alte Pi5_Display-Konfiguration dadurch ueberschrieben/verloren). Laeuft jetzt komplett
von einer NVMe-SSD (Geekworm X1001), SD-Karte ist entfernt.

- IP: eth0 192.168.0.218 (DHCP), eth1 192.168.0.11 (DHCP), SSH: `ssh docucontrol@192.168.0.11` (oder .218),
  sudo-Passwort individuell seit 2026-06-22 (siehe lokale `secrets/`-Ablage, nicht in CLAUDE.md)
- Port 80 → 5000 Weiterleitung per eigenem nftables-Table `docucontrol_redirect`
  (`/etc/nftables-docucontrol.conf` + `nftables-docucontrol.service`, interface-basiert `iif eth0`/`iif eth1`,
  System-only nicht im Repo)
- RTC: **eingebaute Pi5-Onboard-RTC** (`rpi-rtc`, `/dev/rtc0`) + nachgeruestete Batterie (CR1632) —
  kein externes DS3231-Modul wie bei anderen Pis

**SD→NVMe-Migration (2026-06-21):**
- `scripts/migrate_sd_to_nvme.sh` als manuelles Referenzskript erstellt; tatsaechliche Migration lief
  ueber ein on-the-fly geschriebenes Firstboot-Skript (cloud-init `user-data` + systemd-Service),
  da die SD-Karte nur per Windows-Kartenleser zugaenglich war
- EEPROM-Bootreihenfolge erfolgreich auf `BOOT_ORDER=0xf416` (NVMe vor SD) gesetzt — funktioniert
  trotz `dtoverlay=nospi10` (SPI deaktiviert), da `rpi-eeprom-update` das Update als Staged-File
  hinterlegt und der Bootloader es beim naechsten Boot selbst flasht (kein Live-SPI-Zugriff noetig)
- **Overlay-Root bewusst deaktiviert**: Das Basisimage hatte `overlayroot=tmpfs` (RAM-Schutz fuer
  SD-Karten-Verschleiss) aktiv. Zwei fundamentale Inkompatibilitaeten mit unserem Docker-Setup:
  1. Docker's `overlay2`-Storage-Driver kann nicht auf einem bereits ueberlagerten (overlayfs)
     Root-Dateisystem mounten ("failed to mount overlay: invalid argument" / "driver not supported") —
     verschachteltes OverlayFS wird vom Kernel nicht unterstuetzt
  2. Selbst mit anderem Storage-Driver wuerden Protokoll-Datenbank/PDFs bei jedem Reboot auf den
     letzten "eingefrorenen" Stand zurueckgesetzt, da Overlay-Root das gesamte Root-FS inkl. `/home`
     schuetzt, nicht nur Systemdateien
  - Fix: `overlayroot=tmpfs` dauerhaft aus `/boot/firmware/cmdline.txt` entfernt, `/etc/fstab` auf
    einen normalen (nicht-Overlay) Eintrag zurueckgesetzt, Docker auf Storage-Driver `vfs`
    (`/etc/docker/daemon.json: {"storage-driver":"vfs"}`) umgestellt — laeuft jetzt wie das
    produktive DocuControl (.171), das ebenfalls ohne Overlay-Schutz auskommt

**Autoklavenbuch-Workflow aus separatem Repo uebernommen (2026-06-22):**
- Quelle: `github.com/lordboombastic/DocuControl-Belimed-Autoklav-Uni-Essen` (privat, Entwickler: Felix,
  Collaborator: Thomas Glander) — eigenstaendige Weiterentwicklung speziell fuer die Uni-Essen-Maschine
  (Belimed PST 14-8-12 HS1), deutlich weiter als unser bisheriger `src/docucontrol`-Stand
- Neue Funktionalitaet: Chargen landen erst im Status `pending_form` ("Wartet auf Formular") statt
  direkt als PDF — am Touchscreen erscheint per SocketIO-Push ein Modal, in dem der Bediener
  Pflichtfelder ausfuellen muss (Name + Kuerzel, Autoklaviergut, Sicherheits-/Abfallangaben,
  ggf. Programmkorrektur). Erst nach Bestaetigung wird das kombinierte PDF erzeugt
  (Maschinenprotokoll + Autoklavenbuch-Seite, Formular 268627 Rev. 004/01.2024)
- Neue DB-Tabelle `charge_forms`, Status-Flow `pending_form` → `form_confirmed`/`completed`
- Eigener PST-Format-Parser (`protocol_parser.py`) fuer UNIKLINIK_ESSEN_10980-Maschinenformat
  (6-Sensor-Spalten T1-T6, Vakuumtest, mehrseitige Protokolle) zusaetzlich zum alten BELIMED-Format
- `scripts/send_test_charges.py` aktualisiert: jetzt `--format pst|old` + `--via-lpd`-Flag,
  5 PST-Test-Templates (Aufheizprogramm, Vakuumtest, Kaefige, Passage, Futter)
- Im Felix-Repo fehlende Module (nie committed, nur live auf seinem Pi): `lpd_server.py`,
  `serial_receiver.py`, `watchdog_manager.py`, `health_check.py`, `chart_generator.py` — aus dem
  bereits vorhandenen `src/docucontrol`-Stand wiederverwendet. `lpd_server.py` ist eine **eigene,
  generische RFC1179-Implementierung** (nicht Felix' Original, das eine Linksys-PSUS4-Emulation
  auf Port 515→5150 macht und nur live auf seinem Pi existiert)
- `scripts/setup_kiosk_display.sh` als Referenz uebernommen (dokumentiert Pi5-Dual-DRM-Problem:
  X.org kann ohne BusID nicht zwischen card0=vc4-Display und card1=V3D-GPU unterscheiden → cage
  als Wayland-Kiosk-Compositor loest das auf KMS-Ebene)

**Bugs in Felix' Code gefunden + gefixt:**
- `storage_manager.py get_usb_info()`: `findmnt -rno TARGET {dev}` kann bei Mehrfach-Mounts mehrere
  Zeilen liefern, `out.strip()` entfernte nur aeussere Whitespaces, nicht den eingebetteten Zeilenumbruch
  → kaputter `mount_point`-String ("/media/usbstick\n/media/usbstick") → Datei-Listing lieferte immer
  leer. Fix: `out.strip().splitlines()[0]`
- `network_manager.py set_manual_time()`: nutzte `timedatectl set-time`, das in **jeder** Docker-
  Container-Umgebung fehlschlaegt ("System has not been booted with systemd as init system") —
  auf `date -s` + `hwclock --systohc` umgestellt
- `Dockerfile`: `hwclock`-Binary fehlte — liegt unter Debian Trixie nicht in `util-linux`, sondern im
  separaten Paket `util-linux-extra`
- `docucontrol.css`: `.two-col` (Datei-Manager Intern/USB-Spalten) hatte `align-items:start` →
  Spalten ungleich hoch je nach Zeilenanzahl; zusaetzlich liess das zweizeilige USB-Karten-Header
  (Titel + Status-Badges) die Kopfzeilen nicht fluchten. Fix: `align-items:stretch` +
  `.card`/`.card-body` als Flex-Column + einheitliche `min-height` auf `.card-head`
- `dashboard.html` PDF-Modal: Sidebar/Seitenuebersicht im Chromium-PDF-Viewer per `#pagemode=none`
  ausgeblendet, Zoom-Default auf `89%` (optimal fuer das Kiosk-Display), Modal auf echtes Vollbild
  (`100vw`/`100vh`, kein Rand) umgestellt

**Wichtig bei jeder Code-Aenderung:** Nach Deployment IMMER beide Caches leeren —
`docker-compose restart` (Flask cached Templates im Speicher bei `debug=off`) UND
`systemctl restart kiosk.service` (Chromium cached CSS/JS) — sonst zeigt das Display den alten Stand.

**Bildschirmschoner (2026-06-22):** Nach 5 Min. Inaktivitaet (kein Touch/Tastatur) erscheint ein
Bildschirmschoner mit dem GeTmatic-Logo (`static/screensaver-logo.png`, generiert aus
`reference/getmatic_logo_stacked.svg` per `rsvg-convert` — SVG nutzt `textLength`/`lengthAdjust`,
damit "GeTMatic" und "AUTOMATISIERUNGSTECHNIK" exakt gleich breit gerendert werden, unabhaengig
von Font-Groesse). Logo bewegt sich per `requestAnimationFrame` kreuz und quer und prallt an den
Bildschirmraendern ab (DVD-Screensaver-Stil). Wird durch Touch ODER eine neu ankommende Charge
(SocketIO `new_pending_charge`) sofort beendet, `body.screensaver-active{overflow:hidden}` blendet
dabei den Scrollbalken aus. Code in `base.html` (`window._screensaverWake`).

**Boot-Splash (2026-06-22, urspruengliche Fassung):** `/usr/share/plymouth/themes/pix/splash.png`
durch ein aus `reference/dokumentation.svg` gerendertes PNG (1024×600, via `rsvg-convert`) ersetzt —
zeigte eine Illustration von Autoklav + Prozess-Recorder + digitalem/analogem Ausdruck waehrend
des Bootens. Original als `splash.png.orig` gesichert, `update-initramfs -u` danach zwingend
(Plymouth-Assets liegen im Initramfs, nicht nur im Dateisystem). `kiosk.service` hat einen
zusaetzlichen `ExecStartPre=/bin/sleep 4` vor dem `cage`-Start, damit der Splash nach Boot-Abschluss
noch 4 Sekunden sichtbar bleibt, statt sofort vom Kiosk ueberschrieben zu werden (System-only,
nicht im Repo, wie alle anderen `*.service`-Units).

**Boot-Splash (2026-06-22, Update — nur noch Firmenlogo, mehrere Iterationen):** Auf Wunsch durch
ein reines GeTmatic-Logo-Bild ersetzt (Vorbild `reference/getmatic_logo_stacked.svg`, dieselbe Optik
wie der Screensaver) statt der Autoklav-Illustration — Quell-SVG `reference/boot_splash_logo.svg`
(1024×600, Logo zentriert auf dunklem `#3a3a3a`-Hintergrund), gerendert via `rsvg-convert`,
`update-initramfs -u` erneut ausgefuehrt.
- Erster Versuch (`disable_splash=1` in config.txt) wirkungslos — per `vcgencmd get_config int`
  bestaetigt, dass dieser Schluessel auf diesem Pi 5 ueberhaupt nicht von der Firmware erkannt wird
  (legacy VC4-Option, nicht Teil der Pi5-Bootarchitektur) — wieder entfernt.
- Zweiter Versuch (`logo.nologo` Kernel-Parameter in cmdline.txt, gegen das eingebaute
  Kernel-Konsolen-Logo) ebenfalls wirkungslos, blieb aber drin (schadet nicht, korrekt fuer den
  Fall dass der Konsolen-Logo-Pfad je aktiv wuerde).
- **Tatsaechliche Ursache gefunden:** Plymouth beendet sich automatisch ca. 3s nach Bootstart, sobald
  `systemd-user-sessions.service` aktiv wird (Standard-systemd-Verhalten, `plymouth-quit.service`).
  `kiosk.service` (cage+chromium) startet aber erst, wenn der Docker-Container per
  `curl --retry` antwortet — je nach Docker-Startzeit 15-30s spaeter. In dieser Luecke (Plymouth
  bereits beendet, Kiosk noch nicht da) zeigte ein anderer Mechanismus kurzzeitig das grosse
  zentrierte Raspberry-Pi-Logo (vermutlich `/usr/share/rpd-wallpaper/raspberry-pi-logo.png` ueber
  einen TTY1-bezogenen Pfad — Ursache nicht abschliessend isoliert, aber durch Schliessen der Luecke
  irrelevant geworden).
- **Fix (1. Versuch, verursachte Regression):** `/etc/systemd/system/plymouth-quit.service.d/override.conf`
  (System-only) mit `ExecStartPre=/bin/sleep 40` + `TimeoutSec=60`, PLUS `kiosk.service` zusaetzliches
  `ExecStartPre=-/usr/bin/plymouth quit` direkt vor dem `cage`-Start. Beide Trigger liefen aber
  **parallel/race**, nicht sequenziell — der `kiosk.service`-eigene `plymouth quit`-Aufruf schlug
  jedes Mal mit Exit-Code 1 fehl (vermutlich fehlende Rechte als `User=docucontrol`), der
  Override-Aufruf (root, erfolgreich) kam dadurch teils erst **nach** dem Cage-Start — Cage konnte
  in diesem Fenster keinen DRM-Master erhalten, Kiosk blieb komplett schwarz/eingefroren trotz
  laufender Prozesse (cage+chromium liefen, CPU-Last da, aber nichts auf dem Display). Vom User
  sofort gemeldet ("Display bootet nicht bis ins Kiosk").
- **Fix (2. Versuch, stabil):** Den fehlerhaften `ExecStartPre=-/usr/bin/plymouth quit` wieder aus
  `kiosk.service` entfernt, stattdessen `After=plymouth-quit.service` im `[Unit]`-Block von
  `kiosk.service` ergaenzt — dadurch startet `kiosk.service` (inkl. seiner eigenen curl-Wait +
  `sleep 4`-Kette) garantiert erst, NACHDEM `plymouth-quit.service` (mit der 40s-Verzoegerung)
  vollstaendig durchgelaufen ist. Kein Race mehr, nur noch ein einziger, erfolgreicher
  `plymouth quit`-Aufruf (root, ueber den Override). Erst per `systemctl restart kiosk.service` ohne
  Reboot wiederherstellen verifiziert (Display sofort wieder normal), dann per echtem Reboot
  bestaetigt: `plymouth-quit.service` "Finished" **vor** `Starting kiosk.service` im Journal,
  GeTmatic-Logo durchgehend sichtbar, Kiosk startet zuverlaessig (HTTP 200), kein Raspberry-Bild mehr.
  **Lehre:** zwei unabhaengige Trigger fuer denselben einmaligen Vorgang (hier: Plymouth beenden)
  ohne harte Ordnungs-Dependency (`After=`) sind ein Race — lieber einen einzigen, garantiert
  erfolgreichen Trigger sauber sequenzieren als zwei "soft" Trigger mit Hoffnung auf gute Reihenfolge.

**Service-Anmeldung / Einstellungen-Sperre (2026-06-22):** Topbar (`base.html`) hat jetzt ein
Login-Feld ("Anmelden"-Button bzw. "Service"-Badge mit Countdown + Abmelden). Flask-Session-basiert
(`app.py`: `/api/auth/login|logout|status|touch`, Passwort in `data/auth_secrets.json` persistiert
(seit 2026-06-22 individuell, nicht mehr Klartext in CLAUDE.md), 5 Min. Inaktivitaets-Timeout,
wird bei Touch/Tastatur/Klick per `/api/auth/touch` zurueckgesetzt — analog zum Bildschirmschoner).
Standardmaessig (Rolle "user") sind in Einstellungen NUR die Karten **Drucker**, **Zeit & Uhr** und
**USB-Synchronisation** bearbeitbar; alle anderen Karten (Anlage, TCP-Empfang, Schnittstelle 1/2,
Geraetename, Netzwerk-Speicherort, Wartung) sind per `.locked-card`-CSS-Klasse ausgegraut/inaktiv
(`pointer-events:none`) bis zur Service-Anmeldung. Ping- und Verbindungstest-Buttons bleiben ueber
`data-always-enabled="1"` immer benutzbar, auch in gesperrten Karten. **Wichtig:** Die Sperre ist
nicht nur kosmetisch — die zugehoerigen POST-Endpunkte (`/api/machine/config`, `/api/system/hostname`,
`/api/network/iface/<dev>/static|dhcp`, `/api/network/hotspot/config`, `/api/storage/network/config`,
`/api/system/reboot`, `/api/capture/collector`, sowie `tcp_enabled`/`port` auf `/api/tcp_capture/config`
— NICHT aber `auto_print` auf demselben Endpunkt, der gehoert zur Karte "Drucker") pruefen serverseitig
per `_require_service()`-Guard, geben sonst 403 zurueck. Reines Frontend-Verstecken waere durch direkte
API-Aufrufe umgehbar gewesen.

**Offline-Faehigkeit: CDN-Abhaengigkeiten entfernt (2026-06-22):** Der Pi soll spaeter dauerhaft ohne
Internetverbindung laufen. `base.html` lud bislang Bootstrap-CSS, Bootstrap-Icons (inkl. Webfonts) und
den Socket.IO-Client per CDN (`cdn.jsdelivr.net`, `cdn.socket.io`) — ohne Internet waeren Styling,
Icons und vor allem die komplette Live-Update-Funktion (Pending-Charge-Popups, Screensaver-Wake,
Cross-Client-Modal-Sync) ausgefallen, da Socket.IO ueberhaupt nicht mehr geladen haette. Alle drei
Bibliotheken jetzt unter `src/docucontrol/static/{bootstrap,bootstrap-icons,socketio}/` vendored,
`base.html` referenziert nur noch lokale Pfade. Live verifiziert: alle vier Assets (CSS, Icons-CSS,
Icons-Webfont, Socket.IO-JS) liefern 200 vom Pi selbst, WS-Client verbindet sich nach Kiosk-Neustart
weiterhin erfolgreich. Zusaetzlich geprueft und bestaetigt frei von Internet-Abhaengigkeiten: Backend
(`app.py` & Co. — keine `requests`/`urlopen`-Aufrufe an externe Hosts), Docker-Image (lokal gebaut/
gecached, `docker-compose up` braucht kein Internet), NTP (faellt bei fehlendem Internet automatisch
auf die Pi5-Onboard-RTC mit Batteriepufferung zurueck, keine Funktionsunterbrechung).

**Drucker: USB/Netzwerk-Umschalter (2026-06-22):** Settings-Karte "Drucker" hat jetzt einen
Verbindungstyp-Umschalter (USB/Netzwerk) statt nur fest verdrahtetem USB-Setup. Bei "Netzwerk"
zusaetzliches IP/Hostname-Feld. Backend: `print_manager.py` `setup_network_printer(host)` nutzt
denselben Driverless-Ansatz (IPP Everywhere, `-m everywhere`) wie der bestehende
IPP-over-USB-Pfad — funktioniert geraeteunabhaengig fuer alle IPP-Everywhere/AirPrint/
Mopria-zertifizierten Drucker (Mehrheit seit ca. 2014), kein modellspezifischer Treiber noetig.
Aeltere, nicht zertifizierte Netzwerkdrucker bräuchten weiterhin einen eigenen PPD. Konfiguration
(`connection_type`, `network_host`) in `print_config.json` persistiert, beim Boot automatisch
angewendet. Host-Eingabe per Regex validiert (`^[A-Za-z0-9][A-Za-z0-9.\-]*$`).
**Nebenbefund:** `cups-client` (lpadmin/lpinfo/lp) fehlte komplett im Docker-Image — betraf
auch die bisherige USB-Einrichtung auf diesem Geraet (Pi5_Display/docucontrol3), nicht nur die
neue Netzwerk-Funktion. Dockerfile ergaenzt, Image neu gebaut, live verifiziert (lpadmin jetzt
im Container vorhanden, Test-Setup gegen Dummy-IP korrekt fehlgeschlagen mit aussagekraeftiger
Meldung, danach zurueckgesetzt auf sauberen Ausgangszustand ohne konfigurierten Drucker).

**Monitor-Wechsel 7" → 10" + Soft-Keyboard-Fixes (2026-06-22):** docucontrol3 hat einen neuen,
groesseren Touchscreen erhalten. Aufloesung bleibt **1024×600** (per EDID/KMS automatisch erkannt,
`wlr-randr` zeigt "preferred, current") — Boot-Splash (bereits 1024×600 gerendert) und CSS
(durchgehend `vh`/`vw`/`min()`/`calc()`, keine Fixpixel-Annahmen) brauchten deshalb keine Anpassung.
Beim Test fielen zwei vorbestehende Soft-Keyboard-Bugs in `base.html`/`docucontrol.css` auf:
- Tastatur oeffnete sich nur fuer Felder innerhalb `#abModal`/`#authLoginOverlay` (Autoklavenbuch +
  Service-Login) — alle Settings-Felder (Maschinenname, IP, Netzwerk, Hostname, NTP, Netzwerk-
  Speicherort, Drucker-Host) bekamen nie eine Tastatur. Fix: `focusin`-Handler global auf jedes
  Text/Number/Password-Feld ausgeweitet (`base.html`, Zeile ~952).
- Tasten hatten feste Pixelbreiten (86px normal / 128px wide), macht bei 12 Tasten pro Reihe
  ca. 1129px aus — bei 1024px Bildschirmbreite ragten erste/letzte Taste (z.B. "1", "⌫"/"↵") aus
  dem sichtbaren Bereich. Fix: `.kbd-key` auf `flex:1 1 0` (CSS-Verhaeltnisse statt Fixpixel)
  umgestellt, `.kbd-wide` auf `flex:1.5`, `.kbd-space` auf `flex:6` — Tastatur fuellt jetzt
  automatisch die volle verfuegbare Breite, unabhaengig von der tatsaechlichen Bildschirmaufloesung.
- Beide Fixes per `scp` auf docucontrol2/docucontrol3 deployed (`docker-compose restart` +
  `systemctl restart kiosk.service`), live per Chrome DevTools Protocol (temporaerer
  `--remote-debugging-port=9222`, danach wieder entfernt) + `grim`-Screenshots verifiziert:
  Tastatur oeffnet sich in Einstellungen, alle Tasten vollstaendig sichtbar bei 1024×600.

**SD-Karte als bootfaehiger Notfall-Klon der SSD (2026-06-22):** Da nach der SD->NVMe-Migration
die SD-Karte ungenutzt herumlag, wurde sie als kalte Backup-Kopie der produktiven SSD bestueckt.
`BOOT_ORDER=0xf416` deckt damit den Fall "SSD faellt komplett aus/wird nicht erkannt" automatisch
ab (Pi versucht NVMe(6) -> SD(1) -> USB-MSD(4) -> Stop). Wichtig: ein echtes automatisches
OS-Health-Failover (SSD wird erkannt, aber Linux/Container starten nicht durch -> wechsle auf SD)
gibt es NICHT - der Pi-5-Bootloader prueft nur "Geraet da, gueltiger Bootloader gefunden?", nicht
den Erfolg des nachfolgenden Linux-Boots. Das waere nur ueber das tryboot/autoboot.txt-A/B-Schema
moeglich (fuer OS-Updates gedacht, nicht fuer zwei verschiedene physische Datentraeger erprobt,
bewusst nicht umgesetzt wegen Brick-Risiko auf dem produktiven Geraet).
- Vorgehen: bestehende Partitionstabelle auf der SD (512M FAT32 Boot + Rest ext4 Root, schon von
  der alten Pi5_Display-Installation vorhanden) neu formatiert, `rsync -aHAXx` fuer die
  Root-Hierarchie, `/var/lib/docker` bewusst ausgeschlossen (vfs-Storage-Driver dupliziert jeden
  Layer voll -> 29G/683k Einzeldateien, auf microSD viel zu langsam und unnoetig, da
  `docker-compose build` das Image beim ersten Start auf der SD-Karte neu baut)
- **Stolperstein:** `-x` bei rsync ("keine Dateisystemgrenzen ueberschreiten") gilt fuer die
  GESAMTE Quelle "/" - da `/boot/firmware` auf der NVMe eine eigene Partition/eigenes
  Dateisystem ist, wurde es dadurch komplett uebersprungen (kein start4.elf/cmdline.txt auf der
  SD-Kopie, waere nicht bootfaehig gewesen). Mit separatem `rsync -aHAX /boot/firmware/ ...` ohne
  `-x` nachgezogen. Referenzskript (inkl. Fix) in `scripts/clone_ssd_to_sd.sh`.
- PARTUUIDs in `/etc/fstab` + `cmdline.txt` der SD-Kopie auf die SD-eigenen PARTUUIDs (`9d04225d-01`
  /`-02`) umgeschrieben - sonst wuerde die SD beim Booten versuchen, die (dann ggf. defekte/fehlende)
  NVMe als Root zu mounten.
- Ergebnis: 7,7G auf der SD (statt 37G auf der SSD, da Docker-Images fehlen), Boot-Dateien +
  App-Code + Konfigs + DB-Stand zum Zeitpunkt des Klons vollstaendig. Kein Testreboot des
  produktiven Geraets durchgefuehrt (Risiko fuer den laufenden Kiosk-Betrieb).
- Backup-Kontext/Stand siehe `backups/pi-backup-2026-06-22_DocuControl-ZTL-Essen-10Zoll-SSD/`

**Wichtige Regel (User-Vorgabe 2026-06-22): kein laufender Sync der Maschinendokumente auf die
SD-Karte.** Die auf der Maschine erzeugten Chargendokumente (Rohdaten `.txt`/`.bin` + PDFs) duerfen
und sollen erst dann auf der SD-Karte landen, wenn die SSD tatsaechlich ausgefallen ist und die SD
zum aktiven Boot-Medium wird (danach schreibt der normale Betrieb dort ganz regulaer). Bis dahin
bleibt die SD-Karte auf dem statischen Stand vom Klon-Zeitpunkt - keine automatische
Mehrfach-Ablage waehrend die SSD laeuft. Vermutlich Compliance-Grund (eindeutige Quelle der
Wahrheit fuer die Sterilisationsdokumentation, keine zwei parallel fortschreibenden Kopien).
**Konsequenz fuer zukuenftige Arbeit:** Die SD-Karte darf NICHT in `storage_manager.py` /
`network_storage_manager.py` oder eine vergleichbare Auto-Sync-Logik als weiteres Sync-Ziel
aufgenommen werden, solange die SSD der aktive Datentraeger ist.

**Docker-Speicherplatz-Analyse + Cleanup auf docucontrol3 (2026-06-22):** Auf Nutzerfrage geprueft,
wie sich die 41G SSD-Belegung zusammensetzt. Ergebnis: echte Chargendaten (DB + PDFs + Rohdaten-
Captures) sind verschwindend gering (~2,4 MB) - praktisch die gesamte Belegung war Docker-Overhead.
`/var/lib/docker` allein war 33G, obwohl das laufende Image laut `docker system df` nur ~900MB
gross ist - Ursache: Storage-Driver `vfs` (siehe docucontrol3-Abschnitt, urspruenglich wegen
inkompatiblem `overlayroot=tmpfs` gewaehlt) dedupliziert Layer nicht und sammelt bei jedem
`docker-compose build --no-cache` (mehrere davon allein in dieser Session) ungenutzte Alt-Layer an,
die `docker system df` nicht vollstaendig als reclaimable auswies.
- `docker image prune -f` (alte dangling Images) + `docker builder prune -f` (Build-Cache) ausgefuehrt
- Ergebnis: SSD-Belegung 41G -> **15G**, `/var/lib/docker` 33G -> **6,4G** (~26G freigegeben, deutlich
  mehr als die ueber `docker system df` sichtbaren ~3,8G) - laufendes Image/Container unberuehrt,
  Betrieb (docucontrol.service + kiosk.service) waehrend und nach dem Cleanup unterbrechungsfrei
  verifiziert
- **Offene, vom User noch nicht beauftragte Option:** Wechsel des Storage-Drivers von `vfs` auf
  `overlay2` (Standard, mit Layer-Deduplizierung) wuerde die verbleibenden ~6,4G voraussichtlich auf
  <1G reduzieren. Der urspruengliche Grund fuer `vfs` (Inkompatibilitaet von Docker `overlay2` mit
  dem SD-Karten-`overlayroot`-Schutz) besteht auf der NVMe-SSD nicht mehr (normales ext4, kein
  Overlay-Root aktiv, `overlay`-Kernelmodul vorhanden). App-Daten liegen als Bind-Mount
  (`/home/docucontrol/docupi` -> `/app` in `docker-compose.yml`) ausserhalb des Docker-Storage,
  ein Treiberwechsel waere daher ohne Datenverlustrisiko - braucht aber einen Docker-Neustart +
  Image-Neubau und wurde bewusst nicht ohne explizite Rueckfrage umgesetzt.

**Autoklavenbuch Ergebnis-Pflichtfeld + PDF-Freigabebereich + USB-Mount-Fix (2026-06-25):**
- "Ergebnis" (Ablauf OK/Stoerung) im Autoklavenbuch-Formular ist jetzt Pflichtfeld, client- (`abValidate()`
  in `base.html`) UND serverseitig (`/api/pending-charges/<id>/confirm` in `app.py`) erzwungen
- PDF Seite 1 (Freigabebereich unten) zeigt jetzt das tatsaechliche Ergebnis aus dem Autoklavenbuch-
  Formular: "ja"/"nein"-Haekchen ausgefuellt, Kuerzel (`confirmed_initials`/`operator_initials`) und
  die echte eingebettete Unterschrift — vorher waren das nur leere Linien zum handschriftlichen
  Ausfuellen, obwohl die Daten laengst digital vorliegen (`pdf_generator.py draw_page1()`)
- Neuer Stoerungs-Alarm "USB-Stick nicht angeschlossen": erscheint nur, wenn USB-Auto-Sync in den
  Einstellungen aktiv ist, aber kein Stick erkannt/gemountet wird (`app.py /api/system/alerts`)
- **USB-Mount-Bug gefixt:** Nach Abziehen + Wiedereinstecken bekommt der Stick oft einen neuen
  Geraetenamen (z.B. `sda1` -> `sdb1`, klassisches Linux-Re-Enumeration-Verhalten). Der bisherige
  Check `os.path.ismount(USB_MOUNT_POINT)` prueft nur "haengt da ueberhaupt etwas", nicht "ist das
  AKTUELLE Geraet dort gemountet" — ein verwaister Mount des alten, nicht mehr existierenden Geraets
  wurde faelschlich als gueltig durchgelassen, der neue Stick nie gemountet, Dateimanager zeigte
  leer. Fix: neue Hilfsfunktion `_mountpoint_source()` (liest `/proc/mounts`) vergleicht das
  tatsaechlich gemountete Geraet mit dem aktuell erkannten — bei Mismatch wird automatisch
  ausgehaengt + neu gemountet (`storage_manager.py`, betrifft `get_usb_info()`, `mount_usb()`,
  `try_mount_usb_on_boot()`, beide Sync-Funktionen, Sofortkopie, Auto-Sync-Loop)
- Dateimanager-Layout (Kiosk 1024×600): Seitenauswahl im internen Speicher-Pane lief am Geraet ueber
  den rechten Rand, weil Auswahl-Info + Download-/Loeschen-Button + Pager in einer Zeile um Platz
  konkurrierten. Jetzt: Pager + Auswahl-Info in einer Kopfzeile, "Ausgewaehlte"/"Loeschen" darunter
  zentriert in einer gerahmten Box (`.sync-row`-Klasse wiederverwendet, gleiche Button-Groesse wie
  die "Jetzt sync."-Box im USB-Pane) — optisch jetzt symmetrisch zum USB-Pane
- "Neustart"-Button in Einstellungen → System ist jetzt auch ohne Service-Anmeldung nutzbar
  (`data-always-enabled` im Frontend, `_require_service()`-Guard im Backend entfernt), analog zu
  Ping/Verbindungstest-Buttons
- Alle Fixes auf docucontrol3 deployt (scp + `docker-compose restart` + Kiosk-Cache-Leeren) und live
  per Screenshot (CDP-Navigation + `grim`, temporaerer `--remote-debugging-port=9222` danach wieder
  entfernt) verifiziert. 3 Commits gepusht (`563245c`, `293ca9e`, `f397373`)
- **CEC-Test (2026-06-25):** Auf Nutzerfrage geprueft, ob sich das Display (10" Panel "DZX Z3") nach
  Abschalten per Seitentaste per Software automatisch wieder einschalten laesst. Pi-seitig ist CEC
  vorhanden (`/dev/cec0`, vc4-hdmi-Treiber, Topologie zeigt die physische Verbindung), aber alle
  CEC-Befehle ans Panel (Poll, Image View On, Power-Status-Abfrage via `cec-ctl`) kamen mit
  "Not Acknowledged" zurueck — das Panel implementiert CEC nicht (reagiert nicht mal elektrisch).
  Ergebnis: Seitentaste ist rein hardwareseitig, kein Software-Wake moeglich ohne Hardware-Umbau
  (z.B. Relais an der Stromversorgung). Auf Nutzerwunsch nicht weiter verfolgt.

---

## Offene Aufgabe: DocuControl-Gehaeuse-Branding (3D-Druck) — IN ARBEIT

Basis: Raspberry Pi 5 Geekworm X1001 NVMe-SSD-Case (`reference/3D Druck/`, v14/v15-Dateien).
Ziel: Gehaeuse-Variante in weiss mit getmatic-Logo + "DocuControl"-Schriftzug im Firmenstyle auf dem Deckel.

- FreeCAD 1.1.1 wurde lokal installiert (`C:\Users\tomto\AppData\Local\Programs\FreeCAD 1.1`), da keine
  CAD-Software (FreeCAD/OpenSCAD/Blender) und kein Python/ImageMagick auf dem Rechner vorhanden waren
- **Nuetzlicher Nebeneffekt:** FreeCAD bringt ein eigenstaendiges Python 3.11 mit
  (`C:\Users\tomto\AppData\Local\Programs\FreeCAD 1.1\bin\python.exe`) — auf diesem Windows-Rechner
  gibt es sonst kein echtes Python im PATH (`python`/`python3` loesen nur den Microsoft-Store-Stub
  aus). Fuer einmalige Skript-Laeufe (z.B. `scripts/send_test_charges.py`) kann dieses Python
  direkt mit vollem Pfad aufgerufen werden, solange nur Standardbibliothek (socket, argparse,
  datetime) benoetigt wird (2026-06-22 verifiziert: 20 PST-Testchargen an docucontrol3 gesendet)
- Logo-Quelle: `reference/3D Druck/getmatic_logo.jpeg` (niedrig aufgeloeste JPEG mit grauem Hintergrund,
  von `claude-workspace-docucontrol/reference/design_handoff_docucontrol/assets/GeTmatic_Logo.jpeg`
  kopiert) — User hat sich bewusst fuer "mit JPEG weiterarbeiten" entschieden statt eine bessere Quelle
  zu suchen; Hintergrund muss noch freigestellt werden
- Naechste Schritte: (1) Logo freistellen/fuer Gravur aufbereiten, (2) `caseupper-v14.stl` bzw.
  `rpi5-x1001-case-v15-heat-inserts.step` in FreeCAD per Skript laden, Logo + Schriftzug als
  Relief/Gravur auf die Deckelflaeche aufbringen, Materialfarbe weiss setzen, als neue STEP/STL exportieren
- Noch nicht begonnen: eigentliche FreeCAD-Bearbeitung (Step 3 der Aufgabe)

---

## Kritische Anweisung: Diese Datei pflegen

Wann immer Claude Aenderungen am Workspace macht, MUSS Claude pruefen, ob CLAUDE.md aktualisiert werden muss.
