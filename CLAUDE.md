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
│       │   └── docucontrol.css    # Kanonisches CSS (Design-Tokens + Komponenten)
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
│   └── neues Design recap/  # Screenshots des laufenden DocuControl-Interface (laufend aktualisiert, zuletzt 2026-06-12)
├── plans/                  # Implementierungsplaene
├── outputs/                # Arbeitsergebnisse (Konzeptpapiere, generierte PDFs)
│   └── docupi-3000_konzept_getmatic.{md,pdf}  # Vertriebs-Konzept fuer getmatic
├── backups/                # Pi-Backups (komplette Snapshots, gitignored)
│   ├── pi-backup-2026-04-13/  # DocuPi-3000 nach Feldtest Helios Krefeld
│   └── pi-backup-2026-06-08/  # DocuControl — 13 Protokolle, 11 PDFs, Storage-Manager, Templates
└── scripts/                # Hilfsskripte
    ├── fix_ssh.sh
    ├── render_konzept_pdf.py     # Markdown -> PDF (WeasyPrint) fuer outputs/
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

- Hardware: Raspberry Pi — DocuPi-3000 (SSH: belimed@192.168.178.83, zu Hause) | DocuControl (SSH: docucontrol@192.168.0.171, bei getmatic)
- SSH fuer DocuControl: Alias `ssh docucontrol` (Host 192.168.0.171, User docucontrol, IdentityFile `~/.ssh/docucontrol_id`, siehe `~/.ssh/config`), Passwort: Xtend1478 (fuer sudo)
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

**Netzwerk-Speicherort-Einrichtung (2026-06-12, in Arbeit):**
- Feature ist implementiert und funktioniert (Fehlerpfad vollstaendig verifiziert, siehe
  `plans/2026-06-12-netzwerk-speicherort-sync.md`)
- Versuch, Thomas' eigenen Windows-Rechner (192.168.0.86, Freigabe `temp` = `C:\temp`) als
  Test-Ziel einzurichten: bisher `STATUS_LOGON_FAILURE` (per `dmesg` auf dem Pi verifiziert) —
  Server/Freigabe werden korrekt erreicht, Problem liegt an den Zugangsdaten
- Identifizierte Ursachen: eingegebenes "Passwort" war eine 4-stellige Windows-PIN (PIN
  funktioniert nicht fuer SMB, nur das echte Kontopasswort) und der Benutzername (`tom tom`,
  mit Leerzeichen) ist wahrscheinlich nicht der echte SAM-Anmeldename (Profilordner heisst
  `C:\Users\tomto`)
- Empfehlung an Thomas: dediziertes lokales Windows-Konto (z.B. `docucontrol` + echtes Passwort)
  anlegen, diesem in `C:\temp` Freigabe- UND NTFS-Berechtigungen geben, dann in DocuControl
  eintragen
- Pi-Konfig aktuell: `enabled:true`, Server `192.168.0.86`, Freigabe `temp`, weiterhin
  `last_error: "Zugriff verweigert..."` — Hintergrund-Thread retried alle 60s, harmlos aber
  noch nicht erfolgreich
- **Naechster Schritt (Netzwerk-Speicherort):** dediziertes Konto auf 192.168.0.86 anlegen,
  Zugangsdaten in DocuControl eintragen, "Verbindung testen" erneut pruefen (per `dmesg`)

**Naechster Schritt (Tierlabor):** Echten Druckauftrag vom Tierlabor-Geraet (Belimed PST 14-8-12 HS1) empfangen, Maschinennummer des Tierlabor-Geraets in Settings eintragen, Installation vor Ort vorbereiten

---

## Kritische Anweisung: Diese Datei pflegen

Wann immer Claude Aenderungen am Workspace macht, MUSS Claude pruefen, ob CLAUDE.md aktualisiert werden muss.
