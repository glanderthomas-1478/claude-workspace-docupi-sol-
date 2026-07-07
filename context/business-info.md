# Business-Informationen

## Produkt

**DocuControl-SOL** — Dokumentationstool fuer die Abfuellung von Sauerstoffflaschen: erfasst
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

- Raspberry Pi 5 + SSD (NVMe) + Display (Kiosk-Betrieb wie docucontrol3/Pi5_Display) — noch nicht
  beschafft, reine Vorbereitung
- **USB-Dongle** zur LUKS-Entschluesselung von Anfang an vorgesehen (nicht nachtraeglich wie beim
  Herkunftsprojekt geplant) — Referenzskript `scripts/setup_luks_nvme.sh` bereits vorhanden
- Barcode-Scanner: USB-HID (Tastatur-Emulation), Modell noch offen
- Temperatursensor: Anbindung noch offen (1-Wire/I2C direkt am Pi vs. externes Messgeraet per
  RS232/Modbus)
