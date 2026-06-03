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
│   ├── print_manager.py    # Drucker-Management
│   ├── watchdog_manager.py # Service-Ueberwachung
│   ├── add_system_health.py # System-Health-Metriken
│   ├── patches/            # Feature-Patches (15+ Dateien)
│   └── web/                # Web-Frontend
│       ├── base.html       # Basis-Template
│       ├── dashboard.html  # Haupt-Dashboard
│       └── captive.html    # Captive Portal (Hotspot)
├── tests/                  # Test-Skripte
│   ├── fixtures/           # Test-PDFs + WD390-Fixture
│   ├── test_wd_parser.py   # WD-Parser Tests (34 Tests)
│   ├── test_wd_e2e.py      # WD End-to-End Tests
│   └── *.py                # Weitere Tests
├── reference/              # Dokumentation, Konzepte
│   ├── design_handoff_docucontrol/  # hifi Design-Handoff (GeTmatic) — React-Mockup + CSS-Tokens
├── plans/                  # Implementierungsplaene
├── outputs/                # Arbeitsergebnisse (Konzeptpapiere, generierte PDFs)
│   └── docupi-3000_konzept_getmatic.{md,pdf}  # Vertriebs-Konzept fuer getmatic
├── backups/                # Pi-Backups (komplette Snapshots, gitignored)
│   └── pi-backup-2026-04-13/  # Code, DB, PDFs, Logs, System-Configs
└── scripts/                # Hilfsskripte
    ├── fix_ssh.sh
    ├── render_konzept_pdf.py  # Markdown -> PDF (WeasyPrint) fuer outputs/
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
- Langfristiges Ziel: CE-zertifizierte Linux-Controller (Unipi Neuron / RevPi Connect)
- Geschaeftsmodell: Softwarelizenz + Sensor-Kit
- Erster Feldtest abgeschlossen: 3 Wochen, 140 Chargen, Helios Krefeld (Belimed 9-6-18 HS2)
- Konzeptdokument mit Hardware, Sensoren, Softwarearchitektur, Regulatorik und Roadmap existiert
- Erster Kunden-Deal in Umsetzung ueber externen Vertriebspartner getmatic — Ethernet-Print-Abgriff statt RS232 (Box-Replacement zwischen HMI und Drucker)

## DocuControl (zweite Hardware-Linie)

Parallel zum DocuPi-3000 entsteht **DocuControl** — Whitelabel-Name fuer die Kunden-Hardware ueber getmatic.
- Erster Einsatz geplant: **Tierlabor Uni Essen** (Maschinentyp tbd, echter Druckauftrag noch ausstehend)
- Pi 5 bei getmatic vollstaendig eingerichtet (2026-06-02): Kernel 6.18.33, RTC DS3231 (/dev/rtc1), WLAN hardware-deaktiviert, Service docucontrol.service aktiv
- Architektur: TCP/9100-Capture statt RS232, USB-Drucker (CUPS), Flask-App auf Port 5000
- Pipeline vollstaendig: TCP-Empfang -> Parse -> PDF -> DB-Eintrag (automatisch)
- SSH: docucontrol@192.168.0.171 (bei getmatic), User: docucontrol, Passwort: Xtend1478
- Naechster Schritt: **Design-System-Umbau** (Plan fertig: `plans/2026-06-03-docucontrol-design-system.md`)

---

## Kritische Anweisung: Diese Datei pflegen

Wann immer Claude Aenderungen am Workspace macht, MUSS Claude pruefen, ob CLAUDE.md aktualisiert werden muss.
