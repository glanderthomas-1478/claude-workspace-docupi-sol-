# Strategie

## Aktueller Fokus

Kern-Architektur, Hardware-Setup und die komplette Chargenseite (Flaschen-Scan-Workflow) sind fertig
implementiert und end-to-end getestet. Fokus jetzt: die beiden noch fehlenden physischen Geraete
(Barcode-Scanner, Temperatursensor) beschaffen und anbinden, danach echten Praxisbetrieb mit
SOL-Mitarbeitern testen.

## Strategische Prioritaeten

### 1. Herkunfts-Codebasis sichten und uebernehmen — ERLEDIGT (2026-07-07)

- Ordner von `claude-workspace-docupi` kopiert, CLAUDE.md + context/ auf SOL-Projekt umgestellt
- Wiederverwendbare Bausteine identifiziert und in CLAUDE.md dokumentiert (Web-Frontend, Netzwerk-/
  Speicher-/Drucker-Management, Security-Haertungs-Checkliste, LUKS-Skript)
- Git-Remote: eigenes privates Repo angelegt, Origin umgestellt

### 2. Kern-Entscheidungen fuer die SOL-Architektur — GROESSTENTEILS ERLEDIGT

- **Barcode-Scanner**: Inateck BCST-70 (Bluetooth-HID) entschieden — physisches Geraet fuer
  Kopplung noch nicht verfuegbar
- **Temperatursensor**: zwei Kandidaten in Vorbereitung (BTMETER Bluetooth-IR-Thermometer,
  Testo 835-T1 USB), finale Geraete-Entscheidung noch offen — beide Diagnose-Skripte bereit,
  physische Geraete fehlen noch
- **Dokumentationsfelder**: vollstaendig implementiert (Chargen-Barcode, Referenztemperatur,
  Abfueller-Name, pro Flasche Code+IR-Temp, Bestaetigung+Unterschrift, nicht beschreibbares PDF)
- OFFEN: Zielkunde/Betreiber/Vertriebsweg fuer SOL (im Unterschied zu DocuControl gibt es hier noch
  keinen bestaetigten Erstkunden)

### 3. Hardware-Beschaffung und Sicherheits-Setup — ERLEDIGT (2026-07-07/08)

- Erstes Pi-5-Geraet beschafft, SSD+SD-Karte beide LUKS-verschluesselt, Kiosk (cage+Chromium)
  eingerichtet
- USB-Dongle-Zugriffskontrolle (SSH + Service-Aktionen) fertig, zwei identische Dongles im Einsatz
- Sicherheits-Haertung von Anfang an mitgebaut (Service-Dongle-Gates, kein Passwort-Login mehr,
  SSH-PAM-Sperre ohne Dongle)

### 4. Implementierung — ERLEDIGT (2026-07-07/08)

- Chargenseite (`sol_charge_scan.html`) komplett implementiert: Barcode-Scan (Browser-Input-Handler,
  kein TCP/9100-Capture noetig), manuelle IR-Temp-Eingabe (bis Sensor-Anbindung steht), NOK-Erkennung
  mit Fehlerton, Bestaetigung+Unterschrift, nicht beschreibbares PDF
- Dashboard/PDF/DB-Schema von Sterilisationscharge auf Flaschen-Dokumentation umgestellt
  (`sol_charges`/`sol_bottles`, `sol_pdf_generator.py`)
- SMB-Netzwerk-Speicherort + verschluesselter SD-Notfall-Klon zusaetzlich eingerichtet

## Wie Erfolg aussieht

- Kern-Architekturentscheidungen (Scanner, Sensor, Dokumentationsfelder) getroffen — **erledigt**
  bis auf die finale Sensor-Geraeteauswahl
- Hardware beschafft und mit LUKS/USB-Dongle abgesichert aufgesetzt — **erledigt**
- Barcode- und Temperatur-Ingestion implementiert und auf der DocuControl-Dashboard/PDF-Basis
  lauffaehig — **erledigt** (Temperatur noch manuell, Sensor-Anbindung folgt)
- Naechster Meilenstein: Barcode-Scanner + Temperatursensor physisch beschaffen und anbinden, dann
  echten Praxisbetrieb mit SOL-Mitarbeitern testen
