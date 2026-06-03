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
│   └── docucontrol/        # DocuControl Design-System — DEPLOYED auf 192.168.0.171
│       ├── static/
│       │   └── docucontrol.css    # Kanonisches CSS (Design-Tokens + Komponenten)
│       ├── templates/
│       │   ├── base.html          # Topbar "DocuControl by GeTmatic", 3-Tab-Nav, Footer
│       │   ├── dashboard.html     # 2 Stat-Karten + Filter + Protokoll-Tabelle + Print-Toast
│       │   ├── settings.html      # 3 Sub-Tabs: Geraete & Netzwerk / System / Live-Monitor
│       │   └── filemanager.html   # Dual-Pane intern (aus DB) + USB
│       └── app_additions.py       # Context Processor + /api/protocols (bereits in app.py integriert)
├── tests/                  # Test-Skripte
│   ├── fixtures/           # Test-PDFs + WD390-Fixture
│   ├── test_wd_parser.py   # WD-Parser Tests (34 Tests)
│   ├── test_wd_e2e.py      # WD End-to-End Tests
│   └── *.py                # Weitere Tests
├── reference/              # Dokumentation, Konzepte
│   ├── design_handoff_docucontrol/  # hifi Design-Handoff (GeTmatic) — React-Mockup + CSS-Tokens
│   └── neues Design recap/  # Screenshots des laufenden DocuControl-Interface (2026-06-03)
├── plans/                  # Implementierungsplaene (alle 2026-06-03 implementiert)
├── outputs/                # Arbeitsergebnisse (Konzeptpapiere, generierte PDFs)
│   └── docupi-3000_konzept_getmatic.{md,pdf}  # Vertriebs-Konzept fuer getmatic
├── backups/                # Pi-Backups (komplette Snapshots, gitignored)
│   └── pi-backup-2026-04-13/  # Code, DB, PDFs, Logs, System-Configs
└── scripts/                # Hilfsskripte
    ├── fix_ssh.sh
    ├── render_konzept_pdf.py     # Markdown -> PDF (WeasyPrint) fuer outputs/
    ├── deploy_docucontrol_design.sh   # Deployment-Script fuer Linux/Mac
    ├── deploy_docucontrol_win.ps1     # Deployment-Script fuer Windows (OpenSSH)
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
- SSH-Key fuer DocuControl: `~/.ssh/docucontrol_id` (key-based, kein Passwort noetig), SSH-Config: Host docucontrol
- Langfristiges Ziel: CE-zertifizierte Linux-Controller (Unipi Neuron / RevPi Connect)
- Geschaeftsmodell: Softwarelizenz + Sensor-Kit
- Erster Feldtest abgeschlossen: 3 Wochen, 140 Chargen, Helios Krefeld (Belimed 9-6-18 HS2)
- Erster Kunden-Deal in Umsetzung ueber externen Vertriebspartner getmatic — Ethernet-Print-Abgriff statt RS232

## DocuControl (zweite Hardware-Linie) — WEB-INTERFACE PRODUKTIV

**DocuControl** ist der Whitelabel-Name fuer die Kunden-Hardware ueber getmatic.
- Erster Einsatz geplant: **Tierlabor Uni Essen** (Maschinentyp tbd, echter Druckauftrag noch ausstehend)
- Pi 5 bei getmatic: Kernel 6.18.33, RTC DS3231, WLAN off, Service docucontrol.service aktiv
- Architektur: TCP/9100-Capture -> Parse -> PDF -> DB (automatisch), USB-Drucker via CUPS
- SSH: `ssh docucontrol` (Key in ~/.ssh/docucontrol_id), Passwort: Xtend1478 (fuer sudo)

### DocuControl Web-Interface (2026-06-03 vollstaendig deployed)

**Drucker:** Epson XP-4150 als `DocuPrinter` via CUPS/IPP Everywhere (`ipps://EPSON41D474.local:631/ipp/print`)

**Neue API-Endpunkte (alle in app.py auf Pi):**
- `GET /api/protocols` — paginiert, filterbar, sortierbar (Charge-Nr. per Regex aus raw_data)
- `GET /api/protocols/programs` — distinct Programmnamen fuer Filter-Select
- `DELETE /api/protocols/<id>` — loescht DB-Eintrag + PDF-Datei
- `GET /api/printer/ready` — Drucker-Bereitschaft (`ready: bool`)
- `GET /api/printer/status` — CUPS-Status mit Drucker-Liste
- `POST /api/printer/detect` — Drucker-Erkennung
- `POST /api/printer/test` — Testdruck
- `POST /api/printer/auto_print` — Auto-Druck Toggle
- `POST /api/print/<id>` — Drucken per Protokoll-ID

**Stabilitaets-Fixes (2026-06-03):**
- `os._exit(0)` in graceful_shutdown: Restart-Dauer 15s SIGKILL -> **47ms sauber**
- `request.get_json(silent=True)` in allen POST-Routen
- `d.tcp_enabled` statt `d.enabled` ueberall konsistent

**Naechster Schritt:** Sample-Druckauftrag vom Tierlabor-Geraet analysieren, Installation vor Ort

---

## Kritische Anweisung: Diese Datei pflegen

Wann immer Claude Aenderungen am Workspace macht, MUSS Claude pruefen, ob CLAUDE.md aktualisiert werden muss.
