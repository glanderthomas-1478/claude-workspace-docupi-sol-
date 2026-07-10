# Strategie

## Aktueller Fokus

Kern-Architektur, Hardware-Setup und die komplette Chargenseite (Flaschen-Scan-Workflow) sind fertig
implementiert und end-to-end getestet. Barcode-Scanner (Inateck BCST-70) ist seit 2026-07-08
gekoppelt und einsatzbereit, inkl. Geraete-Erreichbarkeits-Alarm (Topbar-weit + lauter Banner/Ton
auf der Scan-Seite). Barcode-/Chargen-Nr.-Formate wurden anhand echter Referenzfotos zweimal
korrigiert (urspruengliche Lesefehler bei aehnlich aussehenden Zeichen).
**Regulatorisch geklaert (2026-07-09):** SOL fuellt an diesem Standort medizinischen Sauerstoff
(AMG/AMWHV/EU-GMP-Anhang 6 einschlaegig), unser System dokumentiert bewusst nur den Abfuellprozess
selbst, Freigabe laeuft nachgelagert ueber QM/Apotheke. Auf dieser Basis Sichtpruefung + Restdruck-
Pruefung als weitere Sammel-NOK-Kriterien beim Chargen-Abschluss ergaenzt, Chargen-Start per
Barcode-Scan funktioniert jetzt app-weit auch aus dem Kiosk-Grundmodus (Dashboard) heraus. **Echter
Praxisbetrieb mit SOL-Mitarbeitern laeuft bereits** (mehrfach live beobachtet).
**BTMETER-Temperatursensor (2026-07-09 Reverse-Engineering, 2026-07-10 Live-Test erfolgreich):**
vom ersten Reverse-Engineering (GATT-Profil, Rohdaten-Paketformat, vorlaeufige Kalibrierformel aus
2 Punkten) ueber die produktive Anbindung bis zum ersten erfolgreichen Live-Test mit echtem Geraet
durchgezogen. Am 2026-07-10 per Live-Nutzer-Feedback drei Runden nachgebessert (Kiosk-Tastatur-Bug,
zu langsame Pro-Messung-Verbindung durch dauerhafte Hintergrundverbindung ersetzt, Trigger-Timing
korrigiert) — danach eine komplette Charge mit 22 Flaschen erfolgreich durchgezogen (0 NOK, PDF
erzeugt), ein Verbindungsabbruch hat sich von selbst erholt. **Fokus fuer die naechste Session:**
weitere Kalibrierpunkte sammeln (bisher nur 2), Geraet-Einschlaf-Verhalten in der Praxis
beobachten (Reconnect faengt es ab, aber nicht ganz verschwunden). Details siehe CLAUDE.md.

## Strategische Prioritaeten

### 1. Herkunfts-Codebasis sichten und uebernehmen — ERLEDIGT (2026-07-07)

- Ordner von `claude-workspace-docupi` kopiert, CLAUDE.md + context/ auf SOL-Projekt umgestellt
- Wiederverwendbare Bausteine identifiziert und in CLAUDE.md dokumentiert (Web-Frontend, Netzwerk-/
  Speicher-/Drucker-Management, Security-Haertungs-Checkliste, LUKS-Skript)
- Git-Remote: eigenes privates Repo angelegt, Origin umgestellt

### 2. Kern-Entscheidungen fuer die SOL-Architektur — GROESSTENTEILS ERLEDIGT

- **Barcode-Scanner**: Inateck BCST-70 (Bluetooth-HID) — **gekoppelt und einsatzbereit (2026-07-08)**
- **Temperatursensor**: BTMETER Bluetooth-IR-Thermometer — **Anbindung gebaut (2026-07-09)**,
  echter Test mit physischem Geraet + Feinkalibrierung noch offen (siehe CLAUDE.md). Testo 835-T1
  (USB) bleibt als Reserve-Kandidat, falls BTMETER sich nicht zuverlaessig stabilisieren laesst
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
  kein TCP/9100-Capture noetig), automatische IR-Temp-Messung per BLE (Fallback auf manuelle
  Eingabe, falls Sensor nicht erreichbar), NOK-Erkennung mit Fehlerton, Bestaetigung+Unterschrift,
  nicht beschreibbares PDF
- Dashboard/PDF/DB-Schema von Sterilisationscharge auf Flaschen-Dokumentation umgestellt
  (`sol_charges`/`sol_bottles`, `sol_pdf_generator.py`)
- SMB-Netzwerk-Speicherort + verschluesselter SD-Notfall-Klon zusaetzlich eingerichtet

## Wie Erfolg aussieht

- Kern-Architekturentscheidungen (Scanner, Sensor, Dokumentationsfelder) getroffen — **erledigt**
- Hardware beschafft und mit LUKS/USB-Dongle abgesichert aufgesetzt — **erledigt**
- Barcode- und Temperatur-Ingestion implementiert und auf der DocuControl-Dashboard/PDF-Basis
  lauffaehig — **erledigt, erster Live-Test mit echtem BTMETER erfolgreich (2026-07-10, 22 Flaschen,
  0 NOK)**, Kalibrierformel weiterhin nur grob (2 Punkte), Geraet schlaeft gelegentlich noch ein
- Naechster Meilenstein: weitere Kalibrierpunkte sammeln, Geraet-Einschlafverhalten im laufenden
  Praxisbetrieb mit SOL-Mitarbeitern weiter beobachten
