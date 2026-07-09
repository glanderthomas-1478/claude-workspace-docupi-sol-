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
- **Regulatorischer Kontext geklaert (2026-07-09):** SOL Krefeld fuellt an diesem Standort
  **medizinischen Sauerstoff** (Arzneimittel, nicht nur technisches Gas) — es gelten AMG/AMWHV +
  EU-GMP-Anhang 6 "Herstellung medizinischer Gase". Scope-Klaerung mit dem User: DocuControl-SOL
  dokumentiert bewusst **nur den Abfuellprozess selbst** (Barcode-Scan, Temperatur, Sichtpruefung,
  Restdruck); die eigentliche GMP-Chargenfreigabe (Pruefung durch QM, danach durch die Apotheke)
  laeuft nachgelagert ausserhalb dieses Systems. Details/Vergleich mit den vollstaendigen
  GMP-Anforderungen: siehe CLAUDE.md-Eintrag vom 2026-07-09

### Hardware-Plattform

- **Erstes Geraet voll eingerichtet** (Stand 2026-07-08): Raspberry Pi 5 + NVMe-SSD + Display,
  Kiosk-Betrieb (cage+Chromium), Hostname `DocuControlSOL`. SSD und SD-Karte beide LUKS-
  verschluesselt (SSD bootet automatisch ohne Dongle, SD-Karte als dongle-pflichtiger Notfall-Klon)
- **USB-Dongle** zur Zugriffskontrolle (SSH + Service-Aktionen) fertig eingerichtet, zwei identische
  SOLDONGLE-Sticks im Einsatz
- Barcode-Scanner: **Gekoppelt und einsatzbereit (2026-07-08)** — Inateck BCST-70 (Bluetooth-HID),
  per `bluetoothctl` gekoppelt (`AC:2B:00:26:4A:10`), Erreichbarkeits-Ueberwachung aktiv, echter
  Flaschen-Code-Scan vom User bestaetigt
- Temperatursensor: **BTMETER Bluetooth-IR-Thermometer, Anbindung gebaut (2026-07-09)** — echter
  Test mit physischem Geraet + Feinkalibrierung noch offen, siehe CLAUDE.md
