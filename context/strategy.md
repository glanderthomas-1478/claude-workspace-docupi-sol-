# Strategie

## Aktueller Fokus

DocuControl-SOL vom Fork zu einem eigenstaendigen, funktionsfaehigen Konzept bringen: Architektur
fuer Barcode-Erfassung + Temperaturmessung festlegen, dann auf der bestehenden DocuControl-Basis
(Dashboard, Backend, Security) implementieren. Hardware ist noch nicht beschafft — aktuell reine
Vorbereitung/Planung.

## Strategische Prioritaeten

### 1. Herkunfts-Codebasis sichten und uebernehmen — ERLEDIGT (2026-07-07)

- Ordner von `claude-workspace-docupi` kopiert, CLAUDE.md + context/ auf SOL-Projekt umgestellt
- Wiederverwendbare Bausteine identifiziert und in CLAUDE.md dokumentiert (Web-Frontend, Netzwerk-/
  Speicher-/Drucker-Management, Security-Haertungs-Checkliste, LUKS-Skript)
- OFFEN: Git-Remote zeigt noch auf das Herkunftsprojekt — vor erstem eigenen Push klaeren (eigenes
  Repo anlegen oder Origin umstellen)

### 2. Kern-Entscheidungen fuer die SOL-Architektur — IN ARBEIT

- **Barcode-Scanner**: USB-HID/Tastatur-Emulation — bestaetigt (2026-07-07). Kein serieller Listener
  noetig, Scan kann direkt als Input-Event im Browser verarbeitet werden
- **Temperatursensor**: OFFEN — 1-Wire/I2C direkt am Pi vs. externes Messgeraet per RS232/Modbus.
  Diese Entscheidung bestimmt, ob ein neuer GPIO-Sensor-Reader gebaut wird oder ein serieller
  Listener (analog `serial_receiver.py`/`wd_protocol_parser.py` aus dem Herkunftsprojekt)
  wiederverwendet werden kann
- **Dokumentationsfelder**: Minimalumfang bestaetigt (Flaschen-ID, Zeitstempel, Temperaturverlauf);
  Erweiterung um Bediener-Kuerzel/Fuelldruck noch zu klaeren (Vorbild: Autoklavenbuch-Formular bei
  docucontrol3)
- OFFEN: Zielkunde/Betreiber/Vertriebsweg fuer SOL (im Unterschied zu DocuControl gibt es hier noch
  keinen bestaetigten Erstkunden)

### 3. Hardware-Beschaffung und Sicherheits-Setup — NOCH NICHT BEGONNEN

- Raspberry Pi 5 + SSD + Display beschaffen (gleiche Basis wie docucontrol3/Pi5_Display)
- **USB-Dongle fuer LUKS-Verschluesselung von Anfang an einplanen** (nicht nachtraeglich wie beim
  Herkunftsprojekt) — Referenzskript `scripts/setup_luks_nvme.sh` liegt bereits vor
- Sicherheits-Haertung (Secrets, Brute-Force-Schutz, Access-Control-Guards, SSH Pubkey-only, etc.)
  von Anfang an mitbauen statt wie beim Herkunftsprojekt nachtraeglich per OWASP-Review nachzuruesten

### 4. Implementierung — NOCH NICHT BEGONNEN

- Barcode-Ingestion (Browser-Input-Handler statt TCP/9100-Capture)
- Temperatur-Ingestion (abhaengig von Sensor-Entscheidung, Punkt 2)
- Dashboard/PDF/DB-Schema von Sterilisationscharge auf Flaschen-Dokumentation umstellen
- Fuer strukturelle Aenderungen: `/create-plan` verwenden, sobald die offenen Entscheidungen
  (Sensor, Scanner-Modell, Dokumentationsfelder) geklaert sind

## Wie Erfolg aussieht

- Kern-Architekturentscheidungen (Scanner, Sensor, Dokumentationsfelder) getroffen
- Hardware beschafft und mit LUKS/USB-Dongle abgesichert aufgesetzt
- Barcode- und Temperatur-Ingestion implementiert und auf der DocuControl-Dashboard/PDF-Basis
  lauffaehig
- Naechster Meilenstein: offene Entscheidungen (Temperatursensor, Scanner-Modell, Dokumentationsfelder,
  Git-Remote) klaeren, dann `/create-plan` fuer die erste Implementierungsrunde
