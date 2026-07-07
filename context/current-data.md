# Aktuelle Daten

## Projektstand (Stand 2026-07-07)

| Bereich | Status | Notizen |
| ------- | ------ | ------- |
| Projekt-Setup | Repo geforkt von claude-workspace-docupi | Ordner kopiert, CLAUDE.md + context/ auf SOL umgestellt (2026-07-07) |
| Git-Remote | **Noch alt** | Zeigt auf `lordboombastic/claude-workspace-docupi` — vor erstem Push fuer SOL klaeren/umstellen |
| Barcode-Scanner | Anbindung entschieden: USB-HID | Konkretes Geraet/Modell noch offen |
| Temperatursensor | **Offen** | 1-Wire/I2C direkt am Pi vs. externes Messgeraet per RS232/Modbus — bestimmt Architektur (GPIO-Reader vs. serieller Listener) |
| Dokumentationsfelder | Minimalumfang bestaetigt | Flaschen-ID + Zeitstempel + Temperaturverlauf; Bediener/Fuelldruck offen |
| Hardware (Pi5+SSD+Display) | **Nicht beschafft** | Reine Vorbereitung/Planung, kein physisches Geraet |
| USB-Dongle/LUKS | Vorbereitet | `scripts/setup_luks_nvme.sh` aus Herkunftsprojekt uebernommen, fuer SOL von Anfang an eingeplant |
| Wiederverwendbare Codebasis | Uebernommen (`src/docucontrol/`) | Flask-Backend, Dashboard/Settings/Datei-Manager-Templates, Netzwerk-/Speicher-/Drucker-Manager, Security-Haertungs-Checkliste |
| Neu zu bauen | Noch nicht begonnen | Barcode-Ingestion (Browser-Input statt TCP/9100), Temperatur-Ingestion (abhaengig von Sensor-Entscheidung), PDF-/Dashboard-Inhalte fuer Flaschen-Dokumentation |

## Naechste konkrete Schritte

1. Temperatursensor-Hardware festlegen (bestimmt Architektur der Mess-Ingestion)
2. Barcode-Scanner-Modell festlegen
3. Dokumentationsfelder final klaeren (Bediener/Fuelldruck ja/nein)
4. Git-Remote fuer SOL klaeren (eigenes Repo anlegen oder Origin umstellen)
5. Hardware beschaffen (Pi 5, SSD, Display, USB-Dongle)
6. Erst danach: konkreter Implementierungsplan (`/create-plan`) fuer Barcode-/Temperatur-Ingestion
   + Anpassung von Dashboard/PDF/DB-Schema auf Flaschen-Dokumentation
