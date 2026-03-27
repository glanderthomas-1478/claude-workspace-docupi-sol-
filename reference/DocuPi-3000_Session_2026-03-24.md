# DocuPi-3000 — Session-Zusammenfassung 24.03.2026

## Gerät & Zugang
- **Kunde:** Helios Krefeld, AEMP
- **Gerät:** Sterilisator 9-6-18 HS2, Nr. 27163, Alias "Steri 1"
- **Pi:** Raspberry Pi (aarch64), Hostname `DocuPi-3000`
- **SSH:** `belimed@192.168.178.83`, Passwort `sb261` (SSH-Key von Cowork ist hinterlegt)
- **Hotspot-IP:** 10.3.141.1 (kein Internet über Hotspot!)
- **App-Pfad:** `/home/belimed/docupi/`
- **Service:** `docupi.service` (systemd, enabled)
- **USB-Adapter:** FTDI FT232R, `/dev/ttyUSB0`
- **Seriell:** 9600 8E1 (`dsrdtr=False`, `rtscts=False`)

## Ausgangssituation
Nach Stromausfall lief der DocuPi nicht mehr korrekt: Dashboard-Uhr zeigte `--:--:--`, keine seriellen Daten sichtbar, keine PDFs erzeugt. config.json war verschwunden (SD-Karten-Schreibfehler).

## Diagnose-Ergebnis
Die serielle Verbindung hat tatsächlich **funktioniert** — 5 Protokolle (Charge 021693, Bowie Dick Test, je ~4257 Zeichen) wurden am 23.03. korrekt empfangen und in die DB geschrieben. Das Problem war **nicht** die serielle Schnittstelle, sondern ein Bug in der PDF-Generierung.

### Root Cause: `_clean_wide_chars()` in `protocol_parser.py`
Die Belimed-Sterilisatoren senden einige Felder in UTF-16LE (mit `\x00`-Null-Bytes). Nach dem Entfernen der Null-Bytes lief der Text durch `_clean_wide_chars()`, die für normale Strings >6 Zeichen `None` zurückgab — das `return text` am Funktionsende war versehentlich unter `apply_config_overrides()` gelandet (toter Code). Dadurch crashte der Parser bei der Betreiber-Namenkorrektur (`NoneType has no attribute 'startswith'`), und die PDF-Generierung schlug still fehl. Alle Protokolle blieben auf `status='received'` hängen und waren im Dashboard unsichtbar.

## Durchgeführte Fixes

### 1. protocol_parser.py (Bug-Fix)
- `_clean_wide_chars()`: `return text` am Ende hinzugefügt
- Toten `return text` aus `apply_config_overrides()` entfernt
- Null-Safety bei Betreiber-Namenkorrektur (`if result['betreiber'] and ...`)
- **Backup:** `protocol_parser.py.bak.20260323_*`

### 2. serial_receiver.py (Härtung)
- `dsrdtr=False`, `rtscts=False` beim Port-Öffnen (verhindert FTDI-EOF-Problem)
- Erweitertes Logging mit vollständiger Konfigurationsanzeige (z.B. "9600 8E1, dsrdtr=off")
- Zusätzlicher `except Exception`-Block in `open_port()`
- **Backup:** `serial_receiver.py.bak.20260323_*`

### 3. config.py (Robustheit)
- `save_config()` nutzt Atomic Write (tempfile + `os.replace`), Stromausfall-sicher
- Automatisches Backup nach jedem Speichern (`config.json.backup`)
- DEFAULT_CONFIG Parity von `"N"` auf `"E"` geändert (Fallback stimmt jetzt mit Maschine überein)

### 4. database.py (Crash-Resilienz)
- SQLite WAL-Modus (`PRAGMA journal_mode=WAL`) bei jeder Connection
- `PRAGMA synchronous=NORMAL` (guter Kompromiss zwischen Sicherheit und Performance)
- Connection-Timeout auf 10s erhöht

### 5. health_check.py (NEU)
Neues Modul, wird bei jedem App-Start automatisch ausgeführt:
- Prüft config.json (valid JSON? richtige Sektionen?) → repariert aus Backup oder Default
- Prüft SQLite-Integrität (integrity_check + WAL-Checkpoint) → sichert kaputte DB und erstellt neue
- Prüft/erstellt alle nötigen Verzeichnisse
- Loggt alles unter `docupi.health`

### 6. app.py (Graceful Shutdown)
- Signal-Handler für SIGTERM/SIGINT: stoppt Serial Receiver und Watchdog sauber
- `atexit`-Handler als zusätzliche Absicherung
- Health-Check-Aufruf beim Start integriert

### 7. systemd Service (Härtung)
- `KillSignal=SIGTERM`, `TimeoutStopSec=15`, `FinalKillSignal=SIGKILL`
- `StartLimitIntervalSec=300`, `StartLimitBurst=10` (Rate-Limiting)
- `PrivateTmp=yes`
- `After=local-fs.target` hinzugefügt

### 8. storage_manager.py (USB-Härtung)
- `dosfsck -a` vor jedem USB-Mount (repariert FAT-Fehler automatisch)
- Mount mit `sync,flush` (Daten sofort auf Stick, nicht im Cache)

### 9. Web-UI (Cross-Browser-Fix)
**Problem:** Bootstrap CSS/JS/Icons + Socket.IO wurden vom CDN geladen. Über den Pi-Hotspot (kein Internet) konnten Android/Windows-Geräte die Dateien nicht laden → komplett kaputtes Layout.
**Fix:** Alle Assets lokal auf den Pi kopiert:
- `/home/belimed/docupi/static/css/bootstrap.min.css`
- `/home/belimed/docupi/static/css/bootstrap-icons.min.css`
- `/home/belimed/docupi/static/js/bootstrap.bundle.min.js`
- `/home/belimed/docupi/static/js/socket.io.min.js`
- `/home/belimed/docupi/static/fonts/bootstrap-icons.woff2` + `.woff`
- Font-Pfade in CSS angepasst auf `/static/fonts/`
- Alle CDN-Referenzen in `base.html` und `filemanager.html` durch lokale Pfade ersetzt

**Responsive-Fixes:**
- `base.html`: Font-Stack erweitert (Roboto für Android), mobile Padding
- `dashboard.html`: Stat-Cards `col` → `col-6 col-md-4 col-xl-2`, Terminal responsive (35vh auf Mobile)
- `filemanager.html`: Spalten auf Mobile ausgeblendet, touch-freundliche Buttons, overflow-x
- `settings.html`: Tab-Pills wrappen auf Mobile

### 10. Sonstiges
- `folder_structure` in Config auf `"flat"` gestellt (keine Unterordner mehr für PDFs)
- Alle 5 Protokolle vom 23.03. nachträglich als PDF generiert (4 Duplikate gelöscht, 1 behalten)
- SSH-Key von Cowork auf dem Pi hinterlegt

## Offene Punkte / Empfehlungen
- **Stromausfall-Test:** Pi wurde am 24.03. stromlos geschaltet — Ergebnis morgen prüfen
- **Error-Status im Dashboard:** Fehlgeschlagene PDF-Generierung als `status='error'` sichtbar machen (aktuell bleibt es unsichtbar auf 'received')
- **USB-Stick fsck:** `/dev/sda1` war nicht sauber ausgehängt — fsck wird jetzt automatisch bei Mount gemacht
- **Log-Rotation:** docupi.log und docupi-service.log wachsen unbegrenzt — logrotate einrichten
- **systemd Watchdog:** Vorbereitet aber auskommentiert — sd_notify-Integration in app.py nötig
