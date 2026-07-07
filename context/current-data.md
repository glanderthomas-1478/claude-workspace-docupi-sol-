# Aktuelle Daten

## Projektstand (Stand 2026-07-07)

| Bereich | Status | Notizen |
| ------- | ------ | ------- |
| Projekt-Setup | Repo geforkt von claude-workspace-docupi | Ordner kopiert, CLAUDE.md + context/ auf SOL umgestellt (2026-07-07) |
| Git-Remote | **ERLEDIGT** | Neues privates Repo `glanderthomas-1478/claude-workspace-docupi-sol-` angelegt, Origin umgestellt, erster Commit gepusht (2026-07-07) |
| Barcode-Scanner | Anbindung entschieden: USB-HID | Konkretes Geraet/Modell noch offen |
| Temperatursensor | **Offen** | 1-Wire/I2C direkt am Pi vs. externes Messgeraet per RS232/Modbus — bestimmt Architektur (GPIO-Reader vs. serieller Listener) |
| Dokumentationsfelder | Minimalumfang bestaetigt | Flaschen-ID + Zeitstempel + Temperaturverlauf; Bediener/Fuelldruck offen |
| Hardware (Pi5+SSD+Display) | **Erstes physisches Geraet in Betrieb** | Raspberry Pi 5, Hostname `DocuControlSOL`, IP 192.168.0.172 (SSH: `docucontrol@192.168.0.172`), erreichbar seit 2026-07-07. Urspruenglich per Raspberry Pi Imager (Debian 13 trixie) auf SD/MMC-Karte vorbereitet (Datum der Erstkonfiguration: 18.06.2026) |
| SD-Karte (fruehere Vorbereitung, Windows-PC) | **Fehlgeschlagen, nicht fortgesetzt** | Flash-Versuch mit Raspberry Pi Imager vom Windows-PC brach mit Hardware-E/A-Fehler ab (Event-ID 51, vermutlich alter Multi-Format-Kartenleser); nicht identisch mit der SD-Karte, die tatsaechlich im Pi steckt (die war schon vorher fertig vorbereitet) |
| **SSD-Migration + LUKS** | **ERLEDIGT (2026-07-07)** | NVMe-SSD (Sabrent Rocket Nano, 476GB) enthielt noch alte Fremd-Daten (ZIP, altes WinXP/PCS7-Installationsmedium, alte VM) — mit Freigabe des Users komplett geloescht. Migration durchgefuehrt: NVMe partitioniert (512MB Boot FAT32 + LUKS2-Root ext4), System von SD auf verschluesselte NVMe kopiert (rsync), crypttab/fstab/cmdline.txt umgestellt, USB-Keyfile-Keyscript + initramfs-Hook installiert, EEPROM BOOT_ORDER auf `0xf416` (NVMe zuerst, SD als Fallback). **Reboot verifiziert:** Pi bootet automatisch von `/dev/mapper/cryptroot` (LUKS auf `nvme0n1p2`), Dongle entsperrt automatisch ohne Passphrase-Abfrage |
| USB-Dongle/LUKS | **Erster Dongle aktiv, zweiter offen** | Design (2026-07-07 vom User bestaetigt): **ein** Keyfile (`docupi-sol.key`, LUKS-Slot 0, kein Passphrase-Fallback), auf einem SanDisk-USB-Stick hinterlegt (enthielt vorher nur werkseitige SanDisk-Installer, unproblematisch ueberschrieben). Zwei identische Dongles gewuenscht (Redundanz, jeder reicht allein) — **zweiter Dongle noch nicht angelegt**: sobald verfuegbar, `docupi-sol.key` 1:1 vom ersten Stick draufkopieren (kein erneuter LUKS-Eingriff noetig) |
| Wiederverwendbare Codebasis | Noch nicht deployed | Auf dem Pi ist aktuell nur das nackte Debian/Raspberry-Pi-OS + LUKS-Setup — `src/docucontrol/`-Code (Flask-Backend, Dashboard/Settings/Datei-Manager, Netzwerk-/Speicher-/Drucker-Manager) noch nicht auf das Geraet gebracht |
| Neu zu bauen | Noch nicht begonnen | Barcode-Ingestion (Browser-Input statt TCP/9100), Temperatur-Ingestion (abhaengig von Sensor-Entscheidung), PDF-/Dashboard-Inhalte fuer Flaschen-Dokumentation |

## Naechste konkrete Schritte

1. Zweiten identischen USB-Dongle anlegen (Keyfile `docupi-sol.key` vom ersten Stick kopieren) — Datei liegt aktuell nur auf dem einen SanDisk-Stick
2. Backup-Kopie des Keyfiles sichern (z.B. in `secrets/`-Ablage), falls beide Dongles verloren gehen
3. Temperatursensor-Hardware festlegen (bestimmt Architektur der Mess-Ingestion)
4. Barcode-Scanner-Modell festlegen
5. Dokumentationsfelder final klaeren (Bediener/Fuelldruck ja/nein)
6. `src/docucontrol/`-Codebasis auf den Pi bringen (Docker/Python-Umgebung einrichten, Deployment-Weg
   festlegen — SCP/Git-Clone direkt auf dem Pi, da GitHub-Repo jetzt existiert)
7. Erst danach: konkreter Implementierungsplan (`/create-plan`) fuer Barcode-/Temperatur-Ingestion
   + Anpassung von Dashboard/PDF/DB-Schema auf Flaschen-Dokumentation
