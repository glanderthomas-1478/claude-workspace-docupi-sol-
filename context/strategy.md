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
**BTMETER-Temperatursensor (2026-07-09, ganzer Tag):** vom ersten Reverse-Engineering (GATT-Profil,
Rohdaten-Paketformat, vorlaeufige Kalibrierformel aus 2 Punkten) bis zur produktiven Anbindung
(`src/docucontrol/ble_thermometer.py`, `sol_charge_scan.html` misst jetzt automatisch nach jedem
Flaschen-Scan, 36°C-Platzhalter komplett entfernt) an einem Tag durchgezogen. **Fokus fuer die
naechste Session: mit dem echten Geraet durchtesten** (in dieser Session nicht mehr geschafft) —
dabei die weiterhin ungeloeste Verbindungsinstabilitaet (Geraet trennt nach ~3-5s von selbst) und
die nur grob kalibrierte Formel im Blick behalten, ggf. nachjustieren. Details siehe CLAUDE.md.

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
  lauffaehig — **erledigt, aber Temperatursensor noch nicht mit echtem Geraet verifiziert**
  (Verbindungsstabilitaet + Kalibrierformel offen)
- Naechster Meilenstein: BTMETER mit echtem Geraet durchtesten und feinkalibrieren, dann
  echten Praxisbetrieb mit SOL-Mitarbeitern testen
