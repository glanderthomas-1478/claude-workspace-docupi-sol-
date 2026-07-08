# CLAUDE.md — DocuControl-SOL (Druckgasflaschen-Abfuellung)

Diese Datei gibt Claude Code Anweisungen fuer die Arbeit in diesem Repository.

---

## Was das hier ist

**DocuControl-SOL** — Dokumentationstool fuer die **Abfuellung von Druckgasflaschen**: erfasst
Flaschen-Barcodes (Scanner) und Temperaturmessung waehrend des Fuellvorgangs, generiert daraus
pruefbare Dokumentation (Dashboard + PDF), auf einem Raspberry Pi 5 mit SSD und Display.

**Herkunft:** Dieses Repository ist ein Fork von `claude-workspace-docupi` (DocuPi-3000/DocuControl —
Sterilisator-Felddiagnostik). Die Pi5+SSD+Display+Dashboard-Architektur, das Web-Frontend
(Dashboard/Settings/Datei-Manager) und diverse Backend-Bausteine (Netzwerk, Speicher, Drucker,
Security-Haertung) werden **1:1 wiederverwendet** — nur die Datenquelle (RS232-Maschinenprotokoll)
und die Dokumentinhalte (Sterilisationscharge) werden durch Barcode-Scan + Temperaturverlauf
(Druckgasflaschen-Abfuellung) ersetzt. Die vollstaendige Entwicklungshistorie der Herkunfts-Codebasis
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
- Per **zwei identischen USB-Dongles** als Service-Techniker-Zugriffskontrolle abgesichert wird
  (2026-07-07 vom User mehrfach praezisiert): **eine** Keyfile-Kopie auf zwei physische USB-Sticks
  dupliziert (Redundanz). **Wichtig — finales Modell (2026-07-07):** Der Pi bootet im Normalbetrieb
  automatisch OHNE Dongle (Keyfile zusaetzlich auf der unverschluesselten Boot-Partition, LUKS ist
  also kein Boot-Gate mehr) — der Dongle wird stattdessen fuer **SSH-Zugriff** (PAM-Regel) und fuer
  **Service-Aktionen in der Web-App** (Aendern/Loeschen von Daten) zwingend gebraucht. Damit kann
  ein Anwender die Anlage taeglich nutzen ohne Dongle, aber nur ein Service-Techniker mit Dongle
  kommt an Software/Konfiguration heran

### Offene Entscheidungen (Stand 2026-07-07)

- **Barcode-Scanner:** **Modell entschieden (2026-07-08):** Inateck BCST-70 (kabellos, Bluetooth,
  35m Funkreichweite, 180 Tage Standby). Laeuft im Bluetooth-**HID-Modus** (Tastatur-Emulation) —
  bestaetigt die schon länger angenommene USB-HID/Tastatur-Emulation-Anbindung, tippt gescannte Codes
  direkt als Tastatureingabe, **kein Code noetig** (Scan-Seite `sol_charge_scan.html` funktioniert
  bereits unveraendert damit). Physisches Geraet fuer die eigentliche Bluetooth-Kopplung noch nicht
  verfuegbar — Vorbereitung + Pairing-Anleitung siehe "Wichtiger Kontext" unten
- **Temperatursensor:** **entschieden (2026-07-08):** BTMETER Infrarot-Thermometer mit Bluetooth
  (Modell BT-1500APP oder aehnlich, 30:1 Dual-Laser-Pyrometer, -50..1500°C). Anbindung per BLE geplant
  (nicht RS232/1-Wire) — physisches Geraet fuer die Protokoll-Erfassung noch nicht verfuegbar,
  Vorbereitung siehe "Wichtiger Kontext" unten (`scripts/ble_scan_thermometer.py`)
- **Dokumentationsfelder:** Minimal bestaetigt (Flaschen-ID, Zeitstempel, Temperaturverlauf);
  Bediener/Fuelldruck/weitere Prozesswerte noch offen
- **Hardware:** **erstes Geraet in Betrieb** (2026-07-07) — Raspberry Pi 5, Hostname `DocuControlSOL`,
  IP 192.168.0.172, SSH-User `docucontrol`. Root laeuft LUKS-verschluesselt von NVMe-SSD
  (`/dev/mapper/cryptroot`), bootet seit der finalen Umstellung automatisch (Keyfile auf
  Boot-Partition, s.o.), SD-Karte bleibt als EEPROM-Boot-Fallback. Projekt-Code (`src/docucontrol/`),
  Kiosk (cage+Chromium) und beide Dongles sind fertig eingerichtet — Details siehe
  `context/current-data.md`
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
│       ├── app.py                 # Flask-Backend, alle Routen/API-Endpunkte, inkl. neuer /api/sol/charges*-Routen (Chargenseite Flaschen-Scan, 2026-07-07); TCP/9100-Start auskommentiert
│       ├── config.py              # load_config/save_config (config.json), inkl. neuer "sol"-Sektion (Sensor-Namen, Toleranz, Warnschwelle, Standort-Kuerzel)
│       ├── database.py            # SQLite-Layer: protocols/charge_forms (Sterilisator-Referenz) + neue sol_charges/sol_bottles-Tabellen (Flaschen-Scan, 2026-07-07)
│       ├── sol_pdf_generator.py   # NEU (2026-07-07): PDF-Generator Temperaturprotokoll (Struktur wie IF.103A), DejaVu-Sans-Unicode-Font
│       ├── network_manager.py     # Hotspot/LAN/Multi-Interface/Hostname/NTP/RTC/nftables
│       ├── network_storage_manager.py  # SMB/CIFS-Netzwerkfreigabe: Mount, Verbindungstest, Auto-Sync (PDFs + Captures)
│       ├── print_manager.py       # Drucker-Management (CUPS, pycups)
│       ├── storage_manager.py     # USB-Erkennung, Mount, Auto-Sync (PDFs + Captures), udev-Trigger
│       ├── static/
│       │   ├── docucontrol.css    # Kanonisches CSS (Design-Tokens + Komponenten)
│       │   ├── bootstrap/, bootstrap-icons/, socketio/  # CDN-Bibliotheken lokal vendored (Offline-Faehigkeit, 2026-06-22)
│       │   └── screensaver-logo.png
│       ├── templates/
│       │   ├── base.html          # Topbar, Nav, Footer (Autoklavenbuch-Modal bleibt als inerte Referenz, wird von SOL nicht mehr ausgeloest)
│       │   ├── dashboard.html     # SOL-Chargenuebersicht (2026-07-07 umgebaut): Stat-Karten, Filter, Chargen-Tabelle, offene-Charge-Banner
│       │   ├── sol_charge_scan.html  # NEU (2026-07-07): Charge starten/scannen/abschliessen (Kernseite der Flaschen-Dokumentation)
│       │   ├── settings.html      # 2 Sub-Tabs: Geraete & Netzwerk (inkl. SOL-Einstellungskarte) / System — TCP-Empfang-Karte + Live-Monitor-Tab am 2026-07-08 entfernt (TCP/9100 inaktiv)
│       │   └── filemanager.html   # Dual-Pane intern (aus sol_charges) + USB, Rohdaten/Captures-Tab entfernt (2026-07-08, TCP-Listener inaktiv)
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
    ├── clone_ssd_to_sd.sh     # Referenz: unverschluesselter SSD → SD Klon (Herkunftsprojekt-Vorlage, fuer SOL durch setup_luks_sd_failover.sh ersetzt, da SOL-SD auch dongle-pflichtig sein muss)
    ├── setup_luks_sd_failover.sh  # NEU (2026-07-08): verschluesselter SD-Notfall-Klon der SSD, eigene LUKS-UUID, KEIN Keyfile auf SD-Boot-Partition (nur per Dongle/Backup-Passphrase entsperrbar) — siehe "Wichtiger Kontext" unten
    ├── setup_kiosk_display.sh # Kiosk-Display-Setup (Referenzskript, gilt auch fuer SOL)
    ├── setup_luks_nvme.sh     # LUKS-Verschluesselung — Referenz, muss fuer SOL auf 2 USB-Dongle-Slots erweitert werden (bisher 1 Dongle + Backup-Passphrase)
    ├── ble_scan_thermometer.py  # NEU (2026-07-08): BLE-Diagnosewerkzeug (Scan + GATT-Inspect) fuer die BTMETER-Thermometer-Anbindung, laeuft auf dem Pi-Host (python3-bleak)
    ├── usb_scan_thermometer.py  # NEU (2026-07-08): USB-Diagnosewerkzeug (lsusb-Scan + Deskriptor-Inspect) fuer die Testo-835-T1-Anbindung, laeuft auf dem Pi-Host (python3-serial/python3-usb)
    ├── simulate_sol_charge.py  # NEU (2026-07-08): simuliert eine komplette SOL-Charge (Start bis PDF-Abschluss) realistischer Groessenordnung inkl. NOK-Faellen gegen die laufende Pi-App, fuer End-to-End-Tests
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
  bootet seit 2026-07-07 automatisch ohne Dongle (Keyfile zusaetzlich auf der Boot-Partition, siehe
  "Boot ohne Dongle"-Eintrag unten); SD-Karte bleibt als EEPROM-Fallback (`BOOT_ORDER=0xf416`)
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
- **Passwort-Login komplett entfernt** (2026-07-07, User-Vorgabe: "wir nutzen zum Einstellen
  ausschliesslich das Dongle"): `_service_logged_in()` in `app.py` ist jetzt nur noch
  `return dongle_present()` — kein Passwort, keine Session, kein Timeout mehr. Entfernt:
  `/api/auth/login`, `/api/auth/logout`, `/api/auth/touch`, Brute-Force-Schutz
  (`_login_locked_out()`), Session-Timeout-Konstanten. `auth_secrets.json` enthaelt nur noch den
  Flask-`secret_key`. Frontend (`base.html`): Login-Button/-Modal/Countdown/Abmelden entfernt,
  Topbar zeigt nur noch ein Badge "Service-Modus (Dongle)" wenn der Dongle steckt — sonst nichts.
  `.locked-card`-Freischaltung in `settings.html` (ueber `window.AUTH.role`/`onAuthChange`) bleibt
  unveraendert kompatibel. Getestet: geschuetzte Aktionen funktionieren komplett ohne Cookie/Login,
  rein durch Dongle-Anwesenheit
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
- **SD-Karte als verschluesselter Notfall-Klon der SSD eingerichtet** (2026-07-08, User-Vorgabe:
  bei SSD-Ausfall soll die SD-Karte mit vollem App-Betrieb einspringen, dabei aber genau wie die SSD
  nur per Dongle lesbar/veraenderbar sein): alte, unverschluesselte SD-Karte komplett geloescht,
  neues Skript `scripts/setup_luks_sd_failover.sh` legt einen eigenen LUKS2-Container auf
  `/dev/mmcblk0p2` an (eigene UUID, unabhaengig von der SSD) und klont das komplette Root-Dateisystem
  per rsync hinein (Docker-Layer ausgeschlossen). **Zentraler Unterschied zur SSD:** die SD-Karte
  bekommt bewusst **kein** Keyfile auf ihrer eigenen Boot-Partition — waehrend die SSD dadurch
  automatisch ohne Dongle bootet, faellt das identische Keyscript bei der SD-Karte sofort auf die
  Dongle-Suche zurueck. Slot 0 = dasselbe Keyfile wie die SSD (beide physischen SOLDONGLE-Sticks
  funktionieren unveraendert auch fuer die SD), Slot 1 = dieselbe Backup-Passphrase wie die SSD.
  fstab/crypttab/cmdline.txt auf die neuen SD-eigenen UUIDs umgeschrieben, Initramfs im Chroot neu
  gebaut. **Bug gefunden+gefixt:** `luksAddKey` fuer die Passphrase ohne explizites `--key-slot 1`
  erzeugte einen Slot, der sich per Keyfile-Vergleich aber nicht per interaktiver Tastatureingabe
  entsperren liess — mit explizitem `--key-slot 1` behoben. Verifiziert: kein Keyfile auf der
  SD-Boot-Partition, beide Entsperrwege (Dongle-Keyfile + Backup-Passphrase, auch per stdin-Eingabe)
  funktionieren. EEPROM-Bootreihenfolge (`0xf416`, NVMe zuerst) war bereits korrekt gesetzt. **Ein
  echter physischer Boot-Failover-Test (SSD abklemmen, von SD booten) steht noch aus.** SD-Klon muss
  nach groesseren SSD-Aenderungen manuell erneut mit dem Skript aktualisiert werden (kein
  laufender Sync)
- Fix: Settings-Karten hatten einen Flexbox-Overflow-Bug (`.set-row`-Kinder ohne `min-width:0`) —
  der "Setzen"-Button lief bei 220px-breiten Eingabefeldern (Anlage-Karte: Maschinenname/Standort)
  ueber den Kartenrand hinaus und wurde abgeschnitten. In `docucontrol.css` gefixt (2026-07-07)
- Fix: `kiosk.service` war fuer `graphical.target` aktiviert, gebootet wird aber in
  `multi-user.target` — Kiosk startete deshalb bei echten Reboots nie automatisch (wirkte wie ein
  Boot-Haenger). Fix: `WantedBy=multi-user.target`, per Kaltstart-Reboot verifiziert (2026-07-07)
- **Boot ohne Dongle (finales Modell, 2026-07-07, User-Vorgabe "Service-Techniker"):** Pi soll im
  Normalbetrieb ganz ohne Dongle laufen, Software-Zugriff (SSH, Aenderungen) aber weiterhin einen
  Dongle erfordern. Umsetzung: `docupi-sol.key` zusaetzlich auf `/boot/firmware/` (unverschluesselte
  Boot-Partition) hinterlegt, Keyscript prueft das zuerst (sofort, kein Warten mehr), danach
  USB-Dongle, danach Passphrase; initramfs neu gebaut. **Per echtem Reboot ganz ohne Dongle
  verifiziert:** Pi bootet automatisch, SSH bleibt trotzdem blockiert (`Connection closed`),
  Web-App-Service-Aktionen bleiben blockiert (`"Service-Dongle erforderlich"`). Nebeneffekt: die
  LUKS-Verschluesselung selbst bietet dadurch keinen Offline-Diebstahlschutz mehr (Schluessel liegt
  auf derselben Platte) — Schutzziel wird jetzt vollstaendig von SSH-PAM-Sperre + Service-Dongle-Gate
  getragen, nicht mehr von der Verschluesselung als Boot-Voraussetzung
- Die in diesem Repo wiederverwendete Codebasis (`src/docucontrol/`) stammt von den Herkunfts-Geraeten
  (DocuControl .171, Pi5_Display .218, docucontrol3 .11) des Projekts `claude-workspace-docupi` — deren
  Zugangsdaten/IPs/Betriebshistorie gehoeren NICHT zu SOL und werden hier nicht dupliziert (siehe
  Herkunftsprojekt bei Bedarf)
- Geschaeftsmodell/Vertriebskontext (Kunde, Betreiber, Vertriebsweg): noch offen, siehe
  `context/business-info.md`
- **Chargenseite umgebaut auf Flaschen-Scan** (2026-07-07, per `/create-plan` + `/implement`,
  Plan: `plans/2026-07-07-sol-chargenseite-flaschen-scan-umbau.md`): Referenzfotos des echten
  SOL-Temperaturprotokolls (IF.103A) und der Chargennummern-Verfahrensanweisung (PR.128.07.9) in
  `reference/screenshots/Bilder SOL Daten/` ausgewertet. Neue Tabellen `sol_charges`/`sol_bottles`,
  neue Routen `/api/sol/charges*` (Start/Scan/Abschluss bewusst NICHT hinter dem Service-Dongle
  gesperrt — das ist die taegliche Kernaufgabe des Geraets, analog zum bisherigen
  Autoklavenbuch-Formular; nur die SOL-Einstellungen sind gesperrt), neuer PDF-Generator
  `sol_pdf_generator.py`, neue Scan-Seite `templates/sol_charge_scan.html`, Dashboard komplett auf
  SOL-Chargen umgebaut. TCP/9100-Capture-Server-Start in `app.py` deaktiviert (Code bleibt als
  Referenz). Charge-Nummer wird vom Techniker eingegeben/gescannt (kein eigenes RAMSES-Nachbau).
  NOK-Kriterium vorlaeufig: IR-Temp minus Raumtemp < Toleranz (Default 5°C, konfigurierbar in
  Settings) — muss mit SOL final bestaetigt werden. End-to-End auf dem Pi getestet (inkl. NOK-Fall,
  Duplikat-Scan, Fehlzeilen-Loeschung, PDF-Kontrolle, USB-Sofortkopie), Testdaten danach entfernt.
  **Finaler Ablauf nach mehreren User-Korrekturen (Stand 2026-07-08):** Charge-Start = Chargen-Barcode
  EINMALIG scannen + **Referenztemperatur** EINMALIG messen (UI/PDF-Label von "Raumtemperatur"
  umbenannt, DB-Feldname `room_temp` unveraendert) + Abfueller-Name. Danach pro Flasche NUR NOCH
  2 Schritte (kein Chargen-Barcode-Rescan mehr, ein zwischenzeitlich gebautes "Chargen-Barcode pro
  Flasche"-Sicherheitsmodell wurde per User-Korrektur wieder entfernt): Flaschen-Code scannen → IR-Temp
  eingeben. OK/NOK-Formel final bestaetigt: Differenz IR-Temp minus Referenztemp. > 5°C = OK,
  < 5°C = NOK. Bei NOK spielt die Seite automatisch einen Fehlerton (Web-Audio-API-Doppelpiepton)
  und bietet eine "Nochmal messen"-Schnellkorrektur (loescht die NOK-Zeile, oeffnet direkt wieder
  die Temp-Eingabe fuer denselben Flaschen-Code, kein erneuter Barcode-Scan noetig) — NOK-Werte
  werden trotzdem gespeichert, wenn nicht erneut gemessen wird. **Abschluss-Ablauf:** "Charge
  abschließen" → Bestaetigungs-Checkbox ("Ich bestätige, dass ich alle Flaschen korrekt gemessen
  habe") mit Zusammenfassung (Anzahl/NOK-Anzahl) → eigenstaendiges Canvas-Unterschriften-Pad
  (Pointer-Events, PNG-Export, NICHT das bestehende `#sigOverlay` aus `base.html` wiederverwendet,
  da eng an den inerten Autoklavenbuch-Flow gekoppelt) → Abfueller-Name + Unterschrift sind
  Pflichtfelder. Ersetzt die urspruengliche separate LQK-Name/-Kuerzel-Eingabe komplett (User-
  Entscheidung: nur der Bediener/Abfueller bestaetigt+unterschreibt, kein zweiter LQK-Schritt) —
  neue DB-Spalte `sol_charges.confirmed_signature` (Base64-PNG, per idempotenter Inline-Migration in
  `init_db()` ergaenzt, da `CREATE TABLE IF NOT EXISTS` bei bereits existierender Tabelle keine neue
  Spalte mehr anlegt). PDF-Fusszeile zeigt das eingebettete Unterschriftsbild statt zweier reiner
  Textzeilen. **PDF ist jetzt "nicht beschreibbar":** `fpdf2.set_encryption()` mit Owner-Passwort +
  eingeschraenkten Permissions (Drucken/Kopieren erlaubt, Bearbeiten/Kommentieren/Formularfelder/
  Neuzusammenstellen gesperrt), kein User-Passwort noetig zum Ansehen — bewusst als "weicher"
  Manipulationsschutz dokumentiert, keine kryptografische Sicherheitsgarantie. Alles auf dem Pi
  end-to-end verifiziert (inkl. `/Encrypt`-Objekt + restriktive `/P`-Permissions im Roh-PDF, echtes
  nicht-transparentes Test-Unterschriftsbild korrekt eingebettet). **Nachtrag 2026-07-08 (3):**
  PDF-Tabelle auf **zweispaltiges Layout + dynamische Paginierung** umgebaut (`sol_pdf_generator.py`,
  `_paginate()`), Zeilenhoehe 7mm→5mm — Seitenzahl richtet sich jetzt nach tatsaechlich verfuegbarem
  Platz statt festem `rows_per_page`-Wert (der Config-Wert bleibt bestehen, wird aber nicht mehr
  gelesen). Ergebnis: volle 160-Flaschen-Charge passt auf **2 Seiten** statt vorher 9. Neues
  Test-Hilfsskript `scripts/simulate_sol_charge.py` (simuliert komplette Chargen realistischer
  Groessenordnung inkl. NOK-Faellen gegen die laufende Pi-App) — damit 3/45/160-Flaschen-Chargen
  end-to-end verifiziert, alle korrekt paginiert, Testdaten jeweils entfernt.
  **Nachtrag 2026-07-08 (4):** `templates/filemanager.html` war beim urspruenglichen Umbau übersehen
  worden — interne Dateiliste hing noch komplett an der alten `protocols`-Tabelle, SOL-PDFs waren dort
  unsichtbar (nicht nur ohne Vorschau). Neue Routen `DELETE /api/sol/charges/<id>`,
  `POST /api/sol/charges/bulk-delete`, `POST /api/sol/charges/bulk-download-zip` (hinter
  `_require_service()`, da destruktive Aktion an bereits abgeschlossenen Chargen); `filemanager.html`
  auf `/api/sol/charges?status=completed` + `/sol/view|download/<id>` umgestellt. Bug beim Schreiben
  vermieden: `sol_bottles.ON DELETE CASCADE` greift nicht, da `PRAGMA foreign_keys` in dieser App nie
  aktiviert wird — `delete_sol_charge()` loescht `sol_bottles` deshalb explizit zuerst.
  Details: `context/current-data.md`
- **GeTMatic-Boot-Splash eingerichtet** (2026-07-08): Auf dem SOL-Pi war noch kein Plymouth-Theme
  vorhanden (anders als evtl. bei anderen Geraeten des Herkunftsprojekts erwartet — dieser Pi wurde
  komplett neu aufgesetzt). `plymouth` + `plymouth-themes` + `librsvg2-bin` installiert, eigenes
  Script-Theme `getmatic` unter `/usr/share/plymouth/themes/getmatic/` angelegt (Logo aus
  `reference/boot_splash_logo.svg`, per `rsvg-convert` auf exakt die Kiosk-Aufloesung 1024×600
  gerendert), per `plymouth-set-default-theme -R getmatic` aktiviert + initramfs neu gebaut,
  `splash quiet plymouth.ignore-serial-consoles` in `/boot/firmware/cmdline.txt` ergaenzt (Backup:
  `cmdline.txt.bak-plymouth`). Auf Wunsch des Users soll das Logo waehrend des **gesamten**
  Boot-Vorgangs sichtbar bleiben (nicht nur frueher Boot) — dafuer `plymouth-quit.service` und
  `plymouth-quit-wait.service` maskiert (kein automatisches Wegschalten mehr beim Erreichen von
  `multi-user.target`) und `kiosk.service` um zwei `ExecStartPre`-Schritte erweitert: (1) Warteschleife
  bis `curl http://localhost:5000/` antwortet (max. 30s Timeout als Fail-Safe), (2) danach `plymouth quit`
  — dadurch bleibt das Logo bis kurz vor dem tatsaechlichen Chromium-Rendering sichtbar, praktisch
  nahtloser Uebergang statt Luecke waehrend Docker-Container-Start. **Bug gefunden+gefixt:**
  `ExecStartPre=/usr/bin/plymouth quit` schlug beim ersten Testreboot fehl (lief als `User=docucontrol`
  ohne Root-Rechte auf die Plymouth-Kontrollsteckdose) und riss dadurch `kiosk.service` in eine
  Neustart-Schleife (Kiosk startete gar nicht mehr) — klassischer Fall von "nur per manuellem Restart
  getestet waere der Bug nicht aufgefallen", diesmal aber sofort per echtem Reboot erkannt. Fix:
  `ExecStartPre=-+/usr/bin/plymouth quit` (`+` = mit vollen/Root-Rechten ausfuehren trotz `User=docucontrol`
  im Service, `-` = Fehler dieses Schritts nicht fatal fuer den restlichen Service). Per zwei
  aufeinanderfolgenden echten Kaltstart-Reboots verifiziert (User-Bestaetigung: Logo durchgehend
  sichtbar, sauberer Uebergang zum Dashboard, kein Crash-Loop, `kiosk.service` startet genau einmal)
- **Temperatursensor entschieden: BTMETER-Bluetooth-Thermometer** (2026-07-08): User nutzt ein
  BTMETER Infrarot-Thermometer mit Bluetooth (30:1 Dual-Laser-Pyrometer, -50..1500°C, vermutlich
  Modell BT-1500APP). BTMETER veroeffentlicht **kein** SDK/Protokoll fuer die BLE-Anbindung (per
  Websuche bestaetigt: weder auf btmeter-store.com noch in verfuegbaren Handbuechern) — die genaue
  GATT-Struktur (Services/Characteristics/Datenformat einer Messung) muss empirisch mit dem
  physischen Geraet ermittelt werden. Vorbereitung abgeschlossen: `python3-bleak` 0.22.3 auf dem
  SOL-Pi-**Host** installiert (nicht im Docker-Container, da BLE direkten BlueZ/D-Bus-Zugriff
  braucht), Bluetooth-Adapter (`hci0`, onboard Pi5) bestaetigt aktiv. Neues Diagnose-Skript
  `scripts/ble_scan_thermometer.py`: ohne Argument scannt es nach BLE-Geraeten in Reichweite (Name/
  MAC/RSSI/Advertisement-Daten, hilft die MAC-Adresse des Thermometers zu identifizieren); mit
  MAC-Adresse als Argument verbindet es sich, listet alle GATT-Services/Characteristics inkl.
  read/write/notify-Eigenschaften, liest lesbare Characteristics einmalig aus und abonniert alle
  notify/indicate-Characteristics 30s lang (waehrenddessen am Geraet eine Messung ausloesen, um das
  Rohdatenformat zu sehen) — per Scan-Smoke-Test auf dem Pi verifiziert (fand zwei andere BLE-Geraete
  in Reichweite, Thermometer selbst war zu diesem Zeitpunkt nicht eingeschaltet/anwesend). **Naechster
  Schritt sobald Geraet physisch verfuegbar:** `python3 /home/docucontrol/ble_scan_thermometer.py`
  (Scan) → MAC identifizieren → `python3 /home/docucontrol/ble_scan_thermometer.py <MAC>` (Inspect,
  dabei am Geraet eine Messung ausloesen) → Rohdaten-Hexdump analysieren → darauf aufbauend echtes
  Anbindungsmodul `src/docucontrol/ble_thermometer.py` schreiben, das `ir_temp` in
  `sol_charge_scan.html` automatisch befuellt statt manueller Eingabe
- **Zweites Thermometer-Modell in Vorbereitung: Testo 835-T1** (2026-07-08) — dasselbe Geraet, das
  bereits als Default-Wert in `config['sol']['sensor_names']` hinterlegt ist (stammt aus den echten
  SOL-Referenzfotos des Papierformulars). **Wichtiger Unterschied zum BTMETER:** der Testo 835-T1 hat
  **kein Bluetooth**, nur USB, und Testo bietet fuer Live-Werte-Abfrage offiziell nur ein
  **Windows-only .NET-SDK** ("Toolbox", Teil der PC-Software EasyClimate, siehe
  `github.com/testo/toolbox_example_t480_t835`) — kein offenes/dokumentiertes Protokoll gefunden
  (Websuche inkl. Handbuch-Fetch ohne Ergebnis). Eine Linux-native Anbindung ist dadurch **nicht
  garantiert moeglich** (anders als beim BLE-basierten BTMETER) — haengt davon ab, ob sich das Geraet
  am Pi als einfacher CDC-virtueller-COM-Port zeigt (guter Fall, direkt per `pyserial` lesbar) oder
  als HID/vendor-spezifisches USB-Geraet (schwieriger Fall, braucht Windows-SDK oder USB-Paketmitschnitt).
  Vorbereitung abgeschlossen: `python3-serial`+`python3-usb` auf dem SOL-Pi-Host installiert,
  `usbutils`(`lsusb`) war schon vorhanden. Neues Diagnose-Skript `scripts/usb_scan_thermometer.py`:
  ohne Argument listet es alle angeschlossenen USB-Geraete (`lsusb`, hilft die Vendor:Product-ID des
  Testo-Geraets zu identifizieren); mit `Vendor:Product-ID` als Argument zeigt es per `pyusb` die
  vollstaendigen USB-Deskriptoren (Interface-Klasse, Endpoints) — die Geraeteklasse verraet direkt den
  moeglichen Integrationsweg (CDC/HID/Vendor-spezifisch). Per Scan-Smoke-Test auf dem Pi verifiziert
  (Testo-Geraet noch nicht angeschlossen). **Naechster Schritt sobald Geraet physisch verfuegbar:**
  `python3 /home/docucontrol/usb_scan_thermometer.py` (Scan) → Vendor:Product-ID identifizieren →
  `python3 /home/docucontrol/usb_scan_thermometer.py <VID:PID>` (Inspect) → je nach gefundener
  USB-Klasse entscheiden, ob eine Linux-native Anbindung ueberhaupt realistisch ist oder ob auf den
  BTMETER als primaeres Messgeraet gesetzt werden sollte
- **Barcode-Scanner-Modell entschieden: Inateck BCST-70** (2026-07-08): kabelloser Bluetooth-Scanner,
  laeuft im **HID-Modus** (Bluetooth-Tastatur-Emulation) — im Gegensatz zum Thermometer braucht das
  **keine eigene Code-Integration**: einmal gekoppelt, tippt der Scanner gescannte Barcodes einfach
  als Tastatureingabe + Enter direkt ins fokussierte Feld, genau das Verhalten, auf das
  `sol_charge_scan.html` (Chargen-Barcode/Flaschen-Code-Eingabefelder) schon ausgelegt ist. Pi-seitig
  geprueft und bereit: `bluetooth.service` aktiv, `hci0`-Adapter (onboard Pi5) laeuft, User
  `docucontrol` ist bereits Mitglied der `input`-Gruppe (noetig, damit cage/Wayland die
  Tastatur-Events eines neu gekoppelten Bluetooth-HID-Geraets lesen kann), keine widerspruechlichen
  bereits gekoppelten Geraete vorhanden. Physischer Scanner noch nicht verfuegbar — **Kopplungsablauf
  sobald verfuegbar** (laut Inateck-Anleitung): am Scanner den "Enter Setup"-Barcode aus dem
  mitgelieferten Handbuch scannen, danach den "Bluetooth Mode (HID)"-Barcode scannen, dann am Pi
  `bluetoothctl` → `agent on` → `default-agent` → `scan on` → Scanner in der Liste per MAC/Namen
  identifizieren → `pair <MAC>` → `trust <MAC>` → `connect <MAC>` (Bestaetigungston am Scanner =
  erfolgreich gekoppelt). Laut Hersteller verbindet sich der Scanner nach einmaliger Kopplung bei
  jedem Einschalten automatisch wieder mit dem zuletzt gekoppelten Geraet — keine erneute Kopplung
  pro Boot noetig. Test danach: Scan-Seite (`/sol/scan`) am Kiosk oeffnen, Eingabefeld fokussiert
  (Standardzustand), Testbarcode scannen — sollte wie eine Tastatureingabe im Feld erscheinen

## Wiederverwendete Architektur aus DocuControl (Herkunftsprojekt)

Der komplette Betriebs-Werdegang von DocuControl/Pi5_Display/docucontrol3 (Sterilisator-Dokumentation,
Belimed PST 14-8-12 HS1, Autoklavenbuch-Workflow, OWASP-Haertung, Boot-Splash/Screensaver, etc.) ist
NICHT Teil von SOL und wurde hier bewusst nicht dupliziert — er gehoert zu anderen physischen Geraeten
eines anderen Projekts. Vollstaendige Historie: `github.com/lordboombastic/claude-workspace-docupi`.

Fuer SOL direkt wiederverwendbar (aus `src/docucontrol/`):

- **Web-Frontend-Geruest**: `templates/base.html` (Topbar, Nav, Footer, Soft-Keyboard, Screensaver-Hooks),
  `settings.html` (Tab-Struktur, Service-Login-Sperre `.locked-card`), `filemanager.html`
  (Dual-Pane intern/extern) — Layout/CSS (`static/docucontrol.css`) 1:1 uebernommen.
  `dashboard.html` wurde bereits auf SOL-Chargen umgestellt (2026-07-07, siehe oben)
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

Nicht uebertragbar, bereits neu gebaut (siehe "Chargenseite umgebaut" oben):

- TCP/9100-Capture + RS232/S-Bus-Parser (`app.py`-Route, `wd_protocol_parser.py`,
  `serial_receiver.py`) — SOL hat keine Maschinenprotokoll-Quelle. Ersetzt durch Barcode/QR-Scan
  (USB-HID, laeuft ueber normale Browser-Input-Events in `sol_charge_scan.html`) + manuelle
  IR-Temperatur-Eingabe (Sensor-Hardware-Anbindung weiterhin offen, Datenmodell aendert sich bei
  Anbindung eines digitalen Sensors nicht). TCP/9100-Start in `app.py` auskommentiert, Code bleibt
  als Referenz
- `pdf_generator.py`/`chart_generator.py`-Inhalte (Sterilisationscharge-spezifische Felder) — durch
  neues `sol_pdf_generator.py` ersetzt (Temperaturprotokoll-Tabelle statt Diagramm, da das echte
  SOL-Papierformular kein Diagramm zeigt)
- Autoklavenbuch-Formular-Workflow (`pending_form`, `charge_forms`-Tabelle) — diente als
  Architektur-Vorbild fuer den neuen SOL-Workflow (neue eigene Tabellen `sol_charges`/`sol_bottles`,
  da 1:n-Beziehung Charge→Flaschen nicht ins bestehende Schema passt), bleibt selbst unveraendert
  als Referenz erhalten (Uni-Essen-spezifische Feldinhalte)

---

## Kritische Anweisung: Diese Datei pflegen

Wann immer Claude Aenderungen am Workspace macht, MUSS Claude pruefen, ob CLAUDE.md aktualisiert werden muss.
