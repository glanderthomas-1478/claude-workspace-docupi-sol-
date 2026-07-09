# Strategie

## Aktueller Fokus

Kern-Architektur, Hardware-Setup und die komplette Chargenseite (Flaschen-Scan-Workflow) sind fertig
implementiert und end-to-end getestet. Barcode-Scanner (Inateck BCST-70) ist seit 2026-07-08
gekoppelt und einsatzbereit, inkl. Geraete-Erreichbarkeits-Alarm (Topbar-weit + lauter Banner/Ton
auf der Scan-Seite), der auch fuer den Temperatursensor vorbereitet ist. Barcode-/Chargen-Nr.-Formate
wurden anhand echter Referenzfotos zweimal korrigiert (urspruengliche Lesefehler bei aehnlich
aussehenden Zeichen). Solange kein Temperatursensor angebunden ist, wird die IR-Temp automatisch
mit einem Platzhalterwert (36°C) befuellt (TEMPORAER, muss beim Sensor-Anschluss wieder raus).
**Regulatorisch geklaert (2026-07-09):** SOL fuellt an diesem Standort medizinischen Sauerstoff
(AMG/AMWHV/EU-GMP-Anhang 6 einschlaegig), unser System dokumentiert bewusst nur den Abfuellprozess
selbst, Freigabe laeuft nachgelagert ueber QM/Apotheke. Auf dieser Basis Sichtpruefung + Restdruck-
Pruefung als weitere Sammel-NOK-Kriterien beim Chargen-Abschluss ergaenzt, Chargen-Start per
Barcode-Scan funktioniert jetzt app-weit auch aus dem Kiosk-Grundmodus (Dashboard) heraus. **Echter
Praxisbetrieb mit SOL-Mitarbeitern laeuft bereits** (mehrfach live beobachtet). Fokus jetzt:
Temperatursensor anbinden (36°C-Platzhalter entfernen), laufendes Nutzer-Feedback zur Scan-Seite
einholen. **BTMETER-Reverse-Engineering gestartet (2026-07-09):** physisches Geraet erstmals
verfuegbar, GATT-Profil + Rohdaten-Paketformat groesstenteils entschluesselt, vorlaeufige
Temperatur-Formel aus 2 Kalibrierpunkten. Offen: Verbindungsstabilitaet (Geraet trennt nach ~3-5s
von selbst) und weitere Kalibrierung, bevor das echte Anbindungsmodul gebaut werden kann — siehe
CLAUDE.md fuer Details.

## Strategische Prioritaeten

### 1. Herkunfts-Codebasis sichten und uebernehmen — ERLEDIGT (2026-07-07)

- Ordner von `claude-workspace-docupi` kopiert, CLAUDE.md + context/ auf SOL-Projekt umgestellt
- Wiederverwendbare Bausteine identifiziert und in CLAUDE.md dokumentiert (Web-Frontend, Netzwerk-/
  Speicher-/Drucker-Management, Security-Haertungs-Checkliste, LUKS-Skript)
- Git-Remote: eigenes privates Repo angelegt, Origin umgestellt

### 2. Kern-Entscheidungen fuer die SOL-Architektur — GROESSTENTEILS ERLEDIGT

- **Barcode-Scanner**: Inateck BCST-70 (Bluetooth-HID) — **gekoppelt und einsatzbereit (2026-07-08)**
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
