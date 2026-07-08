# Business-Informationen

## Produkt

**DocuControl-SOL** — Dokumentationstool fuer die Abfuellung von Druckgasflaschen: erfasst
Flaschen-Barcode (Scanner) und Temperaturverlauf waehrend des Fuellvorgangs, dokumentiert dies
pruefbar (Dashboard + PDF).

### Herkunft

Fork von `claude-workspace-docupi` (DocuPi-3000/DocuControl — Sterilisator-Felddiagnostik fuer
Medizintechnik/Sterilgutversorgung). Gleiche Hardware-Basis (Raspberry Pi 5 + SSD + Display) und
weitgehend dieselbe Software-Architektur (Flask-Backend, Dashboard/Settings/Datei-Manager,
Netzwerk-/Speicher-/Drucker-Management, Security-Haertung) — nur Datenquelle und Dokumentinhalt
sind neu.

### Was es tun soll

- Flaschen-Barcode per USB-HID-Scanner erfassen (Tastatur-Emulation)
- Temperatur waehrend des Abfuellvorgangs messen (Sensorik noch offen)
- Pro Abfuellvorgang einen Dokumentationssatz erzeugen: Flaschen-ID + Zeitstempel +
  Temperaturverlauf (Minimalumfang bestaetigt), ggf. erweitert um Bediener/Fuelldruck
- Echtzeit-Dashboard + PDF-Dokumentation (wiederverwendet aus DocuControl)
- Datenintegritaet/Manipulationsschutz per LUKS-Verschluesselung mit USB-Dongle-Unlock

### Zielgruppe / Geschaeftsmodell

- Noch offen — Kunde, Betreiber, Vertriebsweg fuer SOL sind noch nicht festgelegt (im Unterschied
  zu DocuControl, das ueber getmatic als Whitelabel an die Uniklinik Essen vertrieben wird)
- Regulatorischer Kontext (z.B. Druckgasflaschen-Vorschriften, Pruefpflichten) noch zu klaeren

### Hardware-Plattform

- **Erstes Geraet voll eingerichtet** (Stand 2026-07-08): Raspberry Pi 5 + NVMe-SSD + Display,
  Kiosk-Betrieb (cage+Chromium), Hostname `DocuControlSOL`. SSD und SD-Karte beide LUKS-
  verschluesselt (SSD bootet automatisch ohne Dongle, SD-Karte als dongle-pflichtiger Notfall-Klon)
- **USB-Dongle** zur Zugriffskontrolle (SSH + Service-Aktionen) fertig eingerichtet, zwei identische
  SOLDONGLE-Sticks im Einsatz
- Barcode-Scanner: **Modell entschieden** — Inateck BCST-70 (Bluetooth-HID), physisches Geraet fuer
  Kopplung noch nicht verfuegbar
- Temperatursensor: **zwei Kandidaten in Vorbereitung** (BTMETER Bluetooth-IR-Thermometer,
  Testo 835-T1 USB), finale Geraete-Entscheidung noch offen — siehe CLAUDE.md
