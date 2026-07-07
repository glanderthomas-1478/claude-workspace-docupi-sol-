# CLAUDE.md — DocuControl-SOL (Sauerstoffflaschen-Abfuellung)

Diese Datei gibt Claude Code Anweisungen fuer die Arbeit in diesem Repository.

---

## Was das hier ist

**DocuControl-SOL** — Dokumentationstool fuer die **Abfuellung von Sauerstoffflaschen**: erfasst
Flaschen-Barcodes (Scanner) und Temperaturmessung waehrend des Fuellvorgangs, generiert daraus
pruefbare Dokumentation (Dashboard + PDF), auf einem Raspberry Pi 5 mit SSD und Display.

**Herkunft:** Dieses Repository ist ein Fork von `claude-workspace-docupi` (DocuPi-3000/DocuControl —
Sterilisator-Felddiagnostik). Die Pi5+SSD+Display+Dashboard-Architektur, das Web-Frontend
(Dashboard/Settings/Datei-Manager) und diverse Backend-Bausteine (Netzwerk, Speicher, Drucker,
Security-Haertung) werden **1:1 wiederverwendet** — nur die Datenquelle (RS232-Maschinenprotokoll)
und die Dokumentinhalte (Sterilisationscharge) werden durch Barcode-Scan + Temperaturverlauf
(Sauerstoffflaschen-Abfuellung) ersetzt. Die vollstaendige Entwicklungshistorie der Herkunfts-Codebasis
liegt in `github.com/lordboombastic/claude-workspace-docupi` (Origin-Remote dieses Repos zeigt aktuell
noch dorthin — muss vor dem ersten eigenen Commit/Push geklaert werden, siehe unten).

**Diese Datei (CLAUDE.md) ist das Fundament.** Halte sie aktuell.

---

## Projektbeschreibung

DocuControl-SOL ist ein Raspberry-Pi-5-basiertes System, das:
- Flaschen-Barcodes per **USB-HID-Scanner** (Tastatur-Emulation) erfasst — kein eigenes serielles
  Protokoll noetig, Scan landet direkt als Texteingabe im Browser/Input-Feld
- Temperatur waehrend des Fuellvorgangs misst (Sensorik/Anbindung noch offen, siehe "Offene
  Entscheidungen")
- Pro Abfuellvorgang einen Dokumentationssatz erzeugt: **Flaschen-ID (Barcode) + Zeitstempel +
  Temperaturverlauf** als Minimalumfang; Erweiterung um Bediener-Kuerzel/Fuelldruck moeglich
  (analog zum Autoklavenbuch-Formular bei docucontrol3)
- Echtzeit-Dashboard im Browser anzeigt (wiederverwendet aus DocuControl)
- PDF-Dokumentation mit Temperaturchart generiert (wiederverwendet aus DocuControl-PDF/Chart-Pipeline)
- Per **zwei identischen USB-Dongles** abgesichert wird (LUKS-Verschluesselung zum
  Software-/Quellcode-Schutz, 2026-07-07 vom User bestaetigt/korrigiert): **eine** Keyfile-Kopie auf
  zwei physische USB-Sticks dupliziert (Redundanz falls einer verloren geht/kaputt ist) — **ein**
  Dongle reicht zum Entschluesseln, kein zweiter Key-Slot noetig. Referenzskript
  `scripts/setup_luks_nvme.sh` muss dafuer nur um einen Kopier-Schritt (Keyfile auf zweiten Stick)
  ergaenzt werden, keine LUKS-Struktur-Aenderung noetig

### Offene Entscheidungen (Stand 2026-07-07)

- **Barcode-Scanner:** USB-HID/Tastatur-Emulation — bestaetigt. Kein serieller Listener noetig.
- **Temperatursensor:** noch nicht festgelegt (1-Wire/I2C direkt am Pi vs. externes Messgeraet per
  RS232/Modbus) — bestimmt, ob ein neuer GPIO-Sensor-Reader oder ein serieller Listener (aehnlich
  `serial_receiver.py`/`wd_protocol_parser.py` aus dem Herkunftsprojekt) gebraucht wird
- **Dokumentationsfelder:** Minimal bestaetigt (Flaschen-ID, Zeitstempel, Temperaturverlauf);
  Bediener/Fuelldruck/weitere Prozesswerte noch offen
- **Hardware:** **erstes Geraet in Betrieb** (2026-07-07) — Raspberry Pi 5, Hostname `DocuControlSOL`,
  IP 192.168.0.172, SSH-User `docucontrol`. Root laeuft LUKS-verschluesselt von NVMe-SSD
  (`/dev/mapper/cryptroot`), automatisch entsperrt durch einen USB-Dongle beim Boot (verifiziert per
  Reboot-Test), SD-Karte bleibt als EEPROM-Boot-Fallback. **Projekt-Code (`src/docucontrol/`) ist
  noch NICHT auf dem Geraet** — bisher nur OS + LUKS-Setup
- **Zweiter USB-Dongle:** noch nicht angelegt — Keyfile `docupi-sol.key` liegt bisher nur auf einem
  Stick, muss 1:1 auf einen zweiten identischen Stick kopiert werden (Redundanz)
- **Git-Remote:** **erledigt** — eigenes privates Repo `glanderthomas-1478/claude-workspace-docupi-sol-`
  angelegt, Origin umgestellt, erster Commit gepusht (2026-07-07)

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
│   ├── wd_protocol_parser.py  # Referenz: WD/RDG-Protokoll-Parser (.ht + RS232) — Vorlage falls Temp-Sensor seriell angebunden wird
│   ├── wd_pdf_generator.py    # Referenz: PDF-Generierung WD/RDG
│   ├── wd_chart_generator.py  # Referenz: Temperatur-Chart WD/RDG — direkt wiederverwendbar fuer SOL-Temperaturverlauf
│   ├── print_manager.py    # Drucker-Management (CUPS, pycups)
│   ├── watchdog_manager.py # Service-Ueberwachung
│   ├── add_system_health.py # System-Health-Metriken
│   ├── patches/            # Feature-Patches (15+ Dateien)
│   ├── web/                # Web-Frontend (DocuPi-3000 Legacy)
│   │   ├── base.html       # Basis-Template
│   │   ├── dashboard.html  # Haupt-Dashboard
│   │   └── captive.html    # Captive Portal (Hotspot)
│   └── docucontrol/        # Wiederverwendete Backend+Design-System-Basis aus DocuControl (Herkunftsprojekt) — Ausgangspunkt fuer SOL
│       ├── app.py                 # Flask-Backend, alle Routen/API-Endpunkte — Barcode/Temp-Routen werden hier ergaenzt, TCP/9100-Route entfaellt
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
├── reference/              # Geerbte Dokumentation/Konzepte aus dem Herkunftsprojekt (DocuControl-spezifisch, fuer SOL nur als Referenz)
│   ├── design_handoff_docucontrol/   # Referenz: hifi Design-Handoff v1/v2 (GeTmatic) — Layout-Vorbild, Branding nicht uebernehmbar
│   ├── design_handoff_docucontrol_v3/  # Referenz: hifi Design-Handoff v3 — Liquid Glass, Machine-Bar, 6-Tab-Settings
│   ├── neues Design recap/  # Referenz: Screenshots des DocuControl-Interface (Herkunftsprojekt)
│   ├── 3D Druck/            # Raspberry Pi 5 Geekworm X1001 NVMe-Gehaeuse (STL/STEP/3MF) — Case-Basis auch fuer SOL nutzbar, Branding/Logo muesste fuer SOL neu erstellt werden (bisher getmatic/DocuControl-Logo)
│   ├── 10980_Essen/         # Referenz: Belimed-CD-ROM-Material zur Uni-Essen-Maschine (fuer SOL nicht relevant)
│   ├── getmatic_logo_stacked.svg, boot_splash_logo.svg  # Referenz: Logo-Vorlagen Screensaver/Boot-Splash (Herkunftsprojekt-Branding, fuer SOL zu ersetzen)
│   └── getmatic_logo_transparent.png  # Referenz: freigestelltes Logo (Herkunftsprojekt-Branding, fuer SOL zu ersetzen)
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
    ├── send_test_charges.py  # Referenz: simulierte Belimed-Protokolle via TCP/9100 (Herkunftsprojekt, fuer SOL nicht direkt nutzbar)
    ├── migrate_sd_to_nvme.sh  # SD → NVMe Migration (Referenzskript, gilt auch fuer SOL-Hardware-Setup)
    ├── clone_ssd_to_sd.sh     # SSD → SD Klon (Notfall-Backup, gilt auch fuer SOL)
    ├── setup_kiosk_display.sh # Kiosk-Display-Setup (Referenzskript, gilt auch fuer SOL)
    ├── setup_luks_nvme.sh     # LUKS-Verschluesselung — Referenz, muss fuer SOL auf 2 USB-Dongle-Slots erweitert werden (bisher 1 Dongle + Backup-Passphrase)
    └── saia_test_toolkit/     # Referenz: SAIA-S-Bus-Testtools (Herkunftsprojekt, fuer SOL nicht relevant)
```

---

## Commands

- `/prime` — Session-Start, Kontext laden
- `/create-plan` — Implementierungsplaene erstellen
- `/implement` — Plaene umsetzen
- `/shutdown` — Session sauber beenden

---

## Wichtiger Kontext

- **Erstes SOL-Geraet in Betrieb** (2026-07-07): Raspberry Pi 5, Hostname `DocuControlSOL`,
  SSH `docucontrol@192.168.0.172` (Passwort aktuell identisch mit dem Fleet-Standard-Passwort aus dem
  Herkunftsprojekt — Rotation steht wie bei den anderen Geraeten noch aus)
- NVMe-SSD ist LUKS-verschluesselt und als Root-Dateisystem eingerichtet (`/dev/mapper/cryptroot`),
  automatischer Dongle-Unlock beim Boot verifiziert; SD-Karte bleibt als EEPROM-Fallback
  (`BOOT_ORDER=0xf416`)
- **Projekt-Code deployed** (2026-07-07): `src/docucontrol/` via Docker/docker-compose auf
  `/home/docucontrol/docupi/` gebracht, Container laeuft, Kiosk zeigt live das echte Dashboard
  (aktuell noch unveraenderte DocuControl-Sterilisator-Variante als Platzhalter). Zwei Docker-bedingte
  Bugs im uebernommenen Code gefunden+gefixt: `_root_device_is_nvme()` in `app.py` pruefte `/` im
  Container (immer `overlay`) statt des Host-Roots — liest jetzt `/hostproc/1/mountinfo`
  (neuer Bind-Mount in `docker-compose.yml`) und loest bis zur physischen NVMe-Partition durch den
  LUKS-`dm-mapper` hindurch auf; Chromium-Uebersetzungs-Popup liess sich nicht per Kommandozeilen-Flag
  abschalten, sondern nur per Chromium-Managed-Policy (`/etc/chromium/policies/managed/docupi-sol.json`)
- **Kiosk-Aufbau erledigt** (2026-07-07): `cage`+`seatd`+`chromium` installiert, `kiosk.service`
  zeigt Chromium im Kiosk-Modus auf dem physischen Display (`http://localhost:5000`), per Screenshot
  verifiziert. Wichtige Lehre: `getty@tty1.service` muss deaktiviert werden, sonst blockiert es
  `/dev/tty1` parallel zu cage (Service lief scheinbar, aber Chromium startete nie) — analog zu
  bekannten Kiosk-Stolpersteinen bei Pi5_Display/docucontrol3
- **Fix: Kiosk startete nach echtem Reboot nicht** (2026-07-07): `kiosk.service` war fuer
  `graphical.target` aktiviert, das System bootet aber tatsaechlich in `multi-user.target` — dieses
  Target wurde nie erreicht, Kiosk startete bei echten Kaltstarts nie automatisch (User meldete das
  als "Pi haengt im Boot fest", da tty1 ohne Getty und ohne Kiosk einfach bei den letzten Boot-Zeilen
  stehen blieb). Alle vorherigen Kiosk-Tests liefen ueber manuelles `systemctl restart`, nie ueber
  einen echten Reboot — Bug blieb dadurch unbemerkt. Fix: `WantedBy=multi-user.target`, per echtem
  Kaltstart-Reboot verifiziert
- **Beide USB-Dongles fertig** (2026-07-07): identisches Keyfile auf zwei SanDisk-Sticks, per
  `cryptsetup open --test-passphrase` gegengeprueft — beide entsperren die SSD einwandfrei
- **Service-Dongle-Konzept implementiert** (2026-07-07, User-Vorgabe): Dongle dient NIE als
  Datenspeicher, Pi laeuft ohne Dongle normal weiter, Dongle wird nur zusaetzlich zum Service-Login
  fuer das Lesen/Aendern von Daten gebraucht. Beide Sticks per `fatlabel` auf Label `SOLDONGLE`
  vereinheitlicht; `storage_manager.py` `detect_usb_device()` ignoriert dieses Label (nie als
  USB-Datenspeicher erkannt), neue Funktion `dongle_present()`; `app.py` `_require_service()` verlangt
  jetzt zusaetzlich `dongle_present()` — ohne Dongle liefert jede geschuetzte Aktion 403 trotz
  gueltiger Anmeldung. Mit beiden Dongles gegengetestet (erlaubt/blockiert je nach Anwesenheit)
- **SSH-Login zusaetzlich an den Dongle gekoppelt** (2026-07-07, User-Vorgabe: Software darf ohne
  Dongle weder ausgelesen noch veraendert werden koennen): PAM-Regel in `/etc/pam.d/sshd`
  (`account required pam_exec.so /usr/local/bin/check-service-dongle.sh`, Referenzkopie in
  `scripts/check-service-dongle.sh`) lehnt SSH-Logins ohne SOLDONGLE-Stick komplett ab — sicher
  getestet (neue Verbindung mit Dongle: ok; Label temporaer entfernt: Verbindung sofort
  abgelehnt, danach restauriert). **Wichtige Voraussetzung dafuer geschaffen:** da `getty@tty1`
  fuer den Kiosk deaktiviert ist, war SSH der einzige Zugangsweg — vor der PAM-Aenderung wurde
  `getty@tty2.service` als physischer Not-Konsolenzugang aktiviert (Strg+Alt+F2 am Geraet,
  unabhaengig von der SSH-Dongle-Pflicht, da `/etc/pam.d/login` nicht angepasst wurde). SD-Karte
  wurde vorsorglich auf Restsoftware geprueft — enthaelt keinerlei App-Code (Deployment erfolgte
  erst nach der SSD-Migration)
- **LUKS-Backup-Passphrase eingerichtet** (2026-07-07, User-Vorgabe: Boot ohne Dongle darf nicht
  komplett haengen bleiben): zweiter LUKS-Key-Slot mit Passphrase (Wert in `secrets/`, gitignored),
  nutzt den bereits im Keyscript vorhandenen Passphrase-Fallback nach 15s ohne Dongle. Per
  `--test-passphrase` verifiziert, echter Boot-Prompt-Test steht noch aus
- Fix: Settings-Karten hatten einen Flexbox-Overflow-Bug (`.set-row`-Kinder ohne `min-width:0`) —
  der "Setzen"-Button lief bei 220px-breiten Eingabefeldern (Anlage-Karte: Maschinenname/Standort)
  ueber den Kartenrand hinaus und wurde abgeschnitten. In `docucontrol.css` gefixt (2026-07-07)
- Die in diesem Repo wiederverwendete Codebasis (`src/docucontrol/`) stammt von den Herkunfts-Geraeten
  (DocuControl .171, Pi5_Display .218, docucontrol3 .11) des Projekts `claude-workspace-docupi` — deren
  Zugangsdaten/IPs/Betriebshistorie gehoeren NICHT zu SOL und werden hier nicht dupliziert (siehe
  Herkunftsprojekt bei Bedarf)
- Geschaeftsmodell/Vertriebskontext (Kunde, Betreiber, Vertriebsweg): noch offen, siehe
  `context/business-info.md`

## Wiederverwendete Architektur aus DocuControl (Herkunftsprojekt)

Der komplette Betriebs-Werdegang von DocuControl/Pi5_Display/docucontrol3 (Sterilisator-Dokumentation,
Belimed PST 14-8-12 HS1, Autoklavenbuch-Workflow, OWASP-Haertung, Boot-Splash/Screensaver, etc.) ist
NICHT Teil von SOL und wurde hier bewusst nicht dupliziert — er gehoert zu anderen physischen Geraeten
eines anderen Projekts. Vollstaendige Historie: `github.com/lordboombastic/claude-workspace-docupi`.

Fuer SOL direkt wiederverwendbar (aus `src/docucontrol/`):

- **Web-Frontend-Geruest**: `templates/base.html` (Topbar, Nav, Footer, Soft-Keyboard, Screensaver-Hooks),
  `dashboard.html` (Stat-Karten + Filter + Tabelle + Print-Toast), `settings.html` (Tab-Struktur,
  Service-Login-Sperre `.locked-card`), `filemanager.html` (Dual-Pane intern/extern) — Layout/CSS
  (`static/docucontrol.css`) 1:1 uebernehmbar, Inhalte (Spalten, Felder) muessen auf Flaschen-ID/
  Temperaturverlauf statt Charge-Nr./Programm umgestellt werden
- **Backend-Infrastruktur**: `config.py` (Config-Persistenz), `database.py`-Muster (SQLite +
  Pagination), `network_manager.py` (Hotspot/LAN/Multi-Interface/Hostname/NTP/RTC/nftables),
  `network_storage_manager.py` (SMB/CIFS-Sync), `storage_manager.py` (USB-Erkennung/Mount/Auto-Sync,
  inkl. Re-Enumeration-Fix), `print_manager.py` (CUPS, USB + Netzwerk-Drucker) — alle geraeteunabhaengig,
  keine Sterilisator-Spezifik enthalten
- **Security-Haertung als Checkliste** (bereits einmal vollstaendig durchexerziert, siehe OWASP-Berichte
  in `outputs/docucontrol_owasp_*`): Secrets nicht hardcodieren (`data/auth_secrets.json`-Muster),
  Brute-Force-Schutz Login, XSS-Escaping, `_require_service()`-Guards auf destruktiven Endpunkten,
  CORS/CSRF/HTTPS, SSH Pubkey-only, rpcbind/unnoetige Dienste deaktivieren — fuer SOL von Anfang an
  einplanen statt nachtraeglich patchen
- **Bildschirmschoner/Boot-Splash**: Mechanismus (base.html `_screensaverWake`, Plymouth-Theme-Ersatz)
  wiederverwendbar, Branding/Logo muesste auf SOL-Identitaet umgestellt werden
- **`scripts/setup_luks_nvme.sh`**: LUKS-Verschluesselung, fuer SOL **von Anfang an** Teil des
  Hardware-Setups (nicht erst nachtraeglich wie urspruenglich fuer "DocuControl 4" geplant) —
  **kleine Anpassung noetig**: bisher wird das Keyfile nur auf einen Stick geschrieben (Slot 0) +
  Backup-Passphrase (Slot 1); fuer SOL zusaetzlich dieselbe Keyfile-Datei 1:1 auf einen zweiten
  Stick kopieren (Redundanz-Dongle), keine LUKS-Struktur-/Slot-Aenderung noetig, da beide Sticks
  identisch sind und jeder allein zum Entschluesseln reicht
- **`scripts/migrate_sd_to_nvme.sh`, `clone_ssd_to_sd.sh`, `setup_kiosk_display.sh`**: Referenzskripte
  fuer Pi5-SSD-Boot-Setup + Kiosk-Display, gelten unveraendert auch fuer SOL-Hardware

Nicht uebertragbar / muss neu gebaut werden:

- TCP/9100-Capture + RS232/S-Bus-Parser (`app.py`-Route, `wd_protocol_parser.py`,
  `serial_receiver.py`) — SOL hat keine Maschinenprotokoll-Quelle, sondern Barcode-Scan (USB-HID,
  laeuft ueber normale Browser-Input-Events, kein Listener-Prozess) + Temperaturmessung (Anbindung
  noch offen)
- `pdf_generator.py`/`chart_generator.py`-Inhalte (Sterilisationscharge-spezifische Felder) — Konzept
  (PDF mit eingebettetem Chart) wiederverwendbar, Inhalt/Layout fuer Flaschen-Dokumentation neu
- Autoklavenbuch-Formular-Workflow (`pending_form`, `charge_forms`-Tabelle) — als Vorbild fuer ein
  moegliches SOL-Pflichtfeld-Formular (Bediener/Fuelldruck) relevant, aber Feldinhalte Uni-Essen-spezifisch

---

## Kritische Anweisung: Diese Datei pflegen

Wann immer Claude Aenderungen am Workspace macht, MUSS Claude pruefen, ob CLAUDE.md aktualisiert werden muss.
