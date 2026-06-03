# Plan: Stabilitäts-Härtung für Dauerbetrieb

**Erstellt:** 2026-06-03
**Status:** Implementiert
**Anforderung:** 5 diagnostizierte Probleme beheben die den Dauerbetrieb gefährden: SIGTERM/SIGKILL-Loop, Verbunden/Getrennt-Flapping, Filemanager-API-Mismatch, Timestamp-Bug, Testdruck-415

---

## Überblick

### Was dieser Plan erreicht

Der Service beendet sich sauber innerhalb von 2s auf SIGTERM statt nach 15s per SIGKILL
gewaltsam abgewürgt zu werden. Das "Verbunden/Getrennt"-Flapping verschwindet durch einen
einzelnen geteilten Poll-Zustand und korrekte Feldnamen. Der Datei-Manager zeigt echte PDFs
aus der Datenbank an. Timestamps werden korrekt formatiert.

### Warum das wichtig ist

Beim Tierlabor-Einsatz läuft der Pi im Dauerbetrieb ohne Supervision. Jeder unkontrollierte
SIGKILL hinterlässt offene SQLite-WAL-Dateien, TCP-Port 9100 bleibt kurz belegt, und der
Eindruck beim Kunden ist ein instabiles Gerät. Der UI-Befund (grün oben, rot in der Karte)
untergräbt das Vertrauen in die Statusanzeige.

---

## Aktueller Zustand

### Root-Cause-Analyse (aus Systemdiagnose 2026-06-03)

**Problem 1 — SIGTERM/SIGKILL (kritisch):**
```
Stopping docucontrol.service...
State 'stop-sigterm' timed out. Killing.   ← 15s nach SIGTERM
Main process exited, code=killed, status=9/KILL
```
`graceful_shutdown()` läuft durch und loggt "Shutdown abgeschlossen", ruft aber nicht
`os._exit(0)`. Danach blockiert `socketio.run()` (werkzeug dev server) weiter — dieser
ignoriert den Return aus dem SIGTERM-Handler. Ergebnis: jeder `systemctl restart` dauert
15s und endet mit SIGKILL.

**Problem 2 — Verbunden/Getrennt-Flapping:**
- Topbar-Badge (base.html): prüft `d.tcp_enabled` → korrekt → zeigt "Verbunden"
- Stat-Karte (dashboard.html loadStats): prüft `d.enabled` → **Feld existiert nicht** → immer `false` → zeigt "Getrennt"
- Das ist ein reiner Feld-Namens-Bug, kein echter Verbindungsverlust

**Problem 3 — Filemanager "Fehler beim Laden":**
filemanager.html ruft auf:
- `GET /api/files/list` → **404** (Pi hat kein solches Endpoint)
- `DELETE /api/files/<id>` → **404**
- `GET /api/usb/status` → **404**
- `POST /api/usb/sync` → **404**

Vorhandene korrekte APIs auf dem Pi:
- `GET /api/protocols?per_page=100` — PDFs aus DB (hat `pdf_path`, `pdf_filename`, `timestamp`, `file_size`)
- `GET /api/storage/stats` — Disk-Info (`sd.used_percent`, `usb.detected`)
- `POST /api/storage/delete` — Löschen per `{pane, path}` (löscht physisch)
- `POST /api/storage/sync/now` — USB-Sync
- (Kein USB-Datei-Browse-API, da DocuControl kein USB-PDF-Browsing vorsieht)

Für das Löschen per ID: `/download/<id>` gibt die Datei, aber Löschen geht über
`POST /api/storage/delete {pane:"sd", path: pdf_filename}`.

Alternativ einfacher: neuen Endpunkt `DELETE /api/protocols/<id>` in app.py, der DB-Eintrag
und PDF-Datei entfernt — konsistent mit dem bestehenden Download-Pattern.

**Problem 4 — Timestamp in loadStats:**
`loadStats()` in dashboard.html für "Protokolle gesamt" Karte:
```javascript
var firstTs = d.protocols[0].timestamp || '';          // "2026-06-02T17:10:39.553484"
var firstDate = firstTs.split(' ')[0] || '';           // split(' ') → kein Treffer → ganzer String
var parts = firstDate.split('-');                       // ['2026', '06', '02T17:10:39.553484']
firstDate = parts[2] + '.' + parts[1] + '.' + parts[0]; // "02T17:10:39.553484.06.2026" ← BUG
```
Fix: `.replace('T', ' ').split('.')[0]` vor dem split(' ').

Gleicher Bug in der `todaySub`-Zeile ("Letztes um HH:MM Uhr").

**Problem 5 — Testdruck 415:**
`POST /api/printer/test` ohne Content-Type-Header → Flask gibt 415 zurück bevor Route
erreicht wird. Ursache: Route-Dekorator fehlt `methods` nicht, aber Flask's `request.get_json()`
mit `silent=False` (in manchen Kontexten) wirft 415. Fix: `force=True` oder `silent=True`
in allen `request.get_json()` Aufrufen in den neuen Stub-Routen.

### Lücken / Probleme

1. `os._exit(0)` fehlt in graceful_shutdown → SIGKILL bei jedem Restart
2. `d.enabled` statt `d.tcp_enabled` in dashboard loadStats → Stat-Karte zeigt immer "Getrennt"
3. Filemanager ruft 4 nicht-existente APIs auf → weißer Fehlertext
4. Timestamp-Split ohne T→Space-Konvertierung → kaputtes Datum in Stat-Karte
5. `request.get_json()` in Printer-Stubs ohne `silent=True` → 415 bei leerem Body

---

## Vorgeschlagene Änderungen

### Zusammenfassung

- `graceful_shutdown()` auf Pi: `os._exit(0)` nach Cleanup wenn via Signal aufgerufen
- `dashboard.html`: `d.enabled` → `d.tcp_enabled`, Timestamp-Fix in loadStats (2 Stellen)
- `filemanager.html`: 4 API-Aufrufe auf korrekte Endpoints umschreiben + neuer `/api/protocols/<id>` DELETE-Endpoint
- `app.py`: `request.get_json(silent=True)` in den 4 neuen Printer-Stubs + neuer `DELETE /api/protocols/<id>`

### Neue Dateien erstellen

Keine.

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|---|---|
| Pi: `app.py` | `graceful_shutdown` + `os._exit(0)`, `silent=True` in Printer-Stubs, neuer `DELETE /api/protocols/<int:pid>` |
| Pi: `templates/dashboard.html` | `d.enabled` → `d.tcp_enabled`, Timestamp-Fix |
| Pi: `templates/filemanager.html` | 4 API-Aufrufe korrigiert |
| Lokal: `src/docucontrol/templates/dashboard.html` | Gleiche Fixes |
| Lokal: `src/docucontrol/templates/filemanager.html` | Gleiche Fixes |

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **`os._exit(0)` statt `sys.exit()`**: `sys.exit()` löst `SystemExit` aus, was werkzeug/socketio
   fangen kann. `os._exit(0)` umgeht alle Python-Cleanup-Handler und terminiert den Prozess
   sofort auf OS-Ebene. Das ist nach erfolgreicher App-Cleanup sicher und garantiert
   Beendigung innerhalb 1-2s statt 15s SIGKILL.

2. **Nur bei Signal, nicht bei atexit**: `os._exit(0)` nur wenn `signum is not None`. Bei
   normalem Python-Exit (atexit) nicht nötig — da ist der Prozess ohnehin am Beenden.

3. **Filemanager nutzt `/api/protocols` statt `/api/storage/browse/sd`**: Die PDFs sind in
   der Datenbank mit Metadaten (charge_nr, timestamp, file_size, pdf_filename). Das ist
   robuster als Dateisystem-Browse und liefert direkt sortierbare Daten.

4. **Neuer `DELETE /api/protocols/<id>`**: Löscht DB-Eintrag UND PDF-Datei. Konsistent mit
   `GET /download/<id>` Pattern. Einfacher als `POST /api/storage/delete {pane, path}`.

5. **Keine Hysterese für Verbunden/Getrennt**: Der eigentliche Bug war `d.enabled` statt
   `d.tcp_enabled`. Mit dem Fix zeigen alle Elemente korrekt "Verbunden". Hysterese wäre
   Over-Engineering für ein Problem das nach dem Fix nicht mehr existiert.

### Betrachtete Alternativen

- **`socketio.stop()` statt `os._exit()`**: Flask-SocketIO hat `socketio.stop()` aber nur
  in async-Kontexten nutzbar, nicht aus einem Signal-Handler.
- **`TimeoutStopSec=30` erhöhen**: Behebt das SIGKILL nicht, verlängert nur die Wartezeit.
- **Gunicorn statt werkzeug**: Richtige Produktionslösung, aber erheblicher Umbau;
  für aktuellen Kunden-Scope nicht nötig.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: SIGTERM-Fix — `os._exit(0)` in graceful_shutdown

Einzeilige Änderung am Ende von `graceful_shutdown()` auf dem Pi.

**Aktionen:**

Aktuelle letzte Zeile der Funktion:
```python
    logger.info("Shutdown abgeschlossen")
```

Ersetzen durch:
```python
    logger.info("Shutdown abgeschlossen")
    if signum is not None:
        os._exit(0)
```

Testen: `sudo systemctl restart docucontrol.service` — muss in unter 3s durch sein,
kein "timeout" im journalctl.

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/app.py`

---

### Schritt 2: `request.get_json(silent=True)` in Printer-Stubs

Die 4 neuen Printer-Stub-Routen in app.py geben 415 zurück wenn kein JSON-Body
mitgesendet wird. Fix: `silent=True` ergänzen.

**Aktionen:**

In allen 4 neuen Routen (`api_printer_status`, `api_printer_detect`, `api_printer_test_alias`,
`api_printer_auto_print`) sowie im neuen `api_print_by_id`:

```python
# Alt:
d = request.get_json() or {}
# Neu:
d = request.get_json(silent=True) or {}
```

Auch in den bestehenden Routen `api_print` und `api_print_config_set` gleich nachrüsten
(defensive Härtung).

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/app.py`

---

### Schritt 3: Neuer `DELETE /api/protocols/<int:pid>` Endpoint

Filemanager braucht eine Möglichkeit Protokolle zu löschen. Dieser Endpoint löscht
DB-Eintrag und zugehörige PDF-Datei.

**Aktionen:**

Nach `api_print_by_id` einfügen:

```python
@app.route('/api/protocols/<int:pid>', methods=['DELETE'])
def api_protocol_delete(pid):
    db = get_db()
    row = db.execute('SELECT pdf_path FROM protocols WHERE id=?', (pid,)).fetchone()
    if not row:
        return jsonify({'success': False, 'error': 'Protokoll nicht gefunden'}), 404
    pdf_path = row['pdf_path']
    db.execute('DELETE FROM protocols WHERE id=?', (pid,))
    db.commit()
    if pdf_path and os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except Exception as e:
            logger.warning('PDF-Datei konnte nicht gelöscht werden: %s', e)
    return jsonify({'success': True})
```

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/app.py`

---

### Schritt 4: dashboard.html — `d.enabled` → `d.tcp_enabled` + Timestamp-Fix

Zwei Bugs in loadStats():

**Bug A — Feldname**: In loadStats(), TCP-Status-Abschnitt:
```javascript
// Alt:
var on = d.enabled;
// Neu:
var on = d.tcp_enabled || d.enabled;
```

**Bug B — Timestamp "heute"-Sub**: `todaySub` berechnet Uhrzeit aus Timestamp:
```javascript
// Alt:
var time = ts.split(' ')[1] ? ts.split(' ')[1].slice(0, 5) + ' Uhr' : '';
// Neu (ts könnte "2026-06-03T17:11:58.303141" sein):
var ts_clean = ts.replace('T', ' ').split('.')[0];
var time = ts_clean.split(' ')[1] ? ts_clean.split(' ')[1].slice(0, 5) + ' Uhr' : '';
```

**Bug C — Timestamp "gesamt"-Sub**: `firstTs` für "Seit"-Anzeige:
```javascript
// Alt:
var firstTs = d.protocols[0].timestamp || '';
var firstDate = firstTs.split(' ')[0] || '';
// Neu:
var firstTs = (d.protocols[0].timestamp || '').replace('T', ' ').split('.')[0];
var firstDate = firstTs.split(' ')[0] || '';
```

**Betroffene Dateien:**
- Pi: `templates/dashboard.html`
- Lokal: `src/docucontrol/templates/dashboard.html`

---

### Schritt 5: filemanager.html — API-Aufrufe korrigieren

4 API-Aufrufe auf vorhandene Endpoints umschreiben.

**Mapping:**

| Alt (nicht vorhanden) | Neu (vorhanden auf Pi) |
|---|---|
| `GET /api/files/list` | `GET /api/protocols?per_page=200&sort_by=timestamp&sort_dir=desc` |
| `DELETE /api/files/<id>` | `DELETE /api/protocols/<id>` (Schritt 3) |
| `GET /api/usb/status` | `GET /api/storage/stats` |
| `POST /api/usb/sync` | `POST /api/storage/sync/now` |

**`loadInternalFiles()` komplett neu:**

```javascript
function loadInternalFiles() {
    fetch('/api/protocols?per_page=200&sort_by=timestamp&sort_dir=desc')
        .then(function(r) { return r.json(); })
        .then(function(d) {
            var files = d.protocols || [];
            var body = document.getElementById('intFileBody');
            if (files.length === 0) {
                body.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:20px;color:var(--muted)"><i class="bi bi-inbox"></i> Keine PDFs gespeichert</td></tr>';
            } else {
                body.innerHTML = files.map(function(f) {
                    return renderFileRow({
                        id: f.id,
                        filename: f.pdf_filename,
                        timestamp: f.timestamp,
                        file_size: f.file_size || 0
                    }, true);
                }).join('');
            }
        }).catch(function() {
            document.getElementById('intFileBody').innerHTML =
                '<tr><td colspan="4" style="text-align:center;padding:20px;color:var(--danger)">Fehler beim Laden</td></tr>';
        });

    // Disk-Info separat
    fetch('/api/storage/stats')
        .then(function(r) { return r.json(); })
        .then(function(d) {
            var sd = d.sd || {};
            if (sd.total_gb !== undefined) {
                var usedGb = (sd.total_gb * (sd.used_percent||0) / 100).toFixed(1);
                document.getElementById('intUsed').textContent = usedGb + ' GB / ' + sd.total_gb.toFixed(0) + ' GB';
                document.getElementById('intFill').style.width = Math.min(100, sd.used_percent || 0) + '%';
            }
        }).catch(function() {});
}
```

**`loadUsbFiles()` — auf `/api/storage/stats` umstellen:**

```javascript
function loadUsbFiles() {
    fetch('/api/storage/stats')
        .then(function(r) { return r.json(); })
        .then(function(d) {
            var usb = d.usb || {};
            var connected = usb.detected || false;
            var statusEl = document.getElementById('usbStatus');
            document.getElementById('usbStatusText').textContent = connected ? 'Verbunden' : 'Nicht verbunden';
            statusEl.className = 'usb-status' + (connected ? '' : ' absent');
            document.getElementById('btnSync').disabled = !connected;
            if (connected && usb.total_gb) {
                var usedGb = ((usb.total_gb||0) * (usb.used_percent||0) / 100).toFixed(1);
                document.getElementById('usbUsed').textContent = usedGb + ' GB / ' + (usb.total_gb||0).toFixed(0) + ' GB';
                document.getElementById('usbFill').style.width = Math.min(100, usb.used_percent||0) + '%';
            } else {
                document.getElementById('usbUsed').textContent = '—';
                document.getElementById('usbFill').style.width = '0%';
            }
        }).catch(function() {});
}
```

**`delFile(id)` — auf neuen DELETE-Endpoint:**
```javascript
window.delFile = function(id) {
    if (!confirm('Protokoll #' + id + ' wirklich löschen?')) return;
    fetch('/api/protocols/' + id, { method: 'DELETE' })
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.success) loadInternalFiles();
            else alert('Fehler: ' + (d.error || 'Unbekannt'));
        }).catch(function() {});
};
```

**`syncUsb()` — auf korrekten Endpoint:**
```javascript
fetch('/api/storage/sync/now', { method: 'POST' })
```

Außerdem: `formatDate()` muss T→Space handeln:
```javascript
function formatDate(ts) {
    if (!ts) return '—';
    var clean = ts.replace('T', ' ').split('.')[0];
    var d = clean.split(' ')[0] || '';
    if (d) {
        var dp = d.split('-');
        if (dp.length === 3) d = dp[2] + '.' + dp[1] + '.' + dp[0];
    }
    return d;
}
```

**Betroffene Dateien:**
- Pi: `templates/filemanager.html`
- Lokal: `src/docucontrol/templates/filemanager.html`

---

### Schritt 6: Service-Neustart testen

Nach allen Änderungen:

**Aktionen:**

- `sudo systemctl restart docucontrol.service`
- `journalctl -u docucontrol.service -n 5 --no-pager` → kein "timeout", kein "SIGKILL"
- `systemctl is-active docucontrol.service` → `active`
- `curl http://localhost:5000/api/protocols?per_page=1` → JSON
- `curl http://localhost:5000/api/storage/stats` → JSON mit `sd` und `usb`
- `curl -X DELETE http://localhost:5000/api/protocols/999` → `{"error": "Protokoll nicht gefunden"}`

Restart-Timing messen: `time sudo systemctl restart docucontrol.service` → sollte < 5s sein.

**Validierung im Browser:**

- Dashboard: Stat-Karte "Verbindungsstatus" zeigt "Verbunden" (grün), Badge oben auch grün
- Dashboard: "Seit TT.MM.YYYY" korrekt (kein "T" im Datum)
- Dateien-Seite: Interne PDFs erscheinen, kein "Fehler beim Laden"
- Einstellungen → Testdruck: kein 415-Fehler

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- `app.py`: `graceful_shutdown` ist zentral für den gesamten Service-Lifecycle
- `templates/dashboard.html`: alle 30s-Polls hängen an den fixen Feldnamen
- `templates/filemanager.html`: vollständig abhängig von Storage-APIs

### Nötige Updates für Konsistenz

- `CLAUDE.md` nach Abschluss: Service-Lifecycle und bekannte Endpunkte aktualisieren
- Lokale Template-Dateien mit Pi synchron halten

### Auswirkungen auf bestehende Workflows

- `DELETE /api/protocols/<id>` ist ein neuer Endpoint — keine bestehenden Aufrufer
- `os._exit(0)` ändert das Shutdown-Verhalten: kein graceful Python-Teardown mehr nach
  Signal. Das ist OK da der App-Cleanup vorher explizit erfolgt.
- Alle bestehenden API-Pfade bleiben unverändert

---

## Validierungs-Checkliste

- [ ] `journalctl` zeigt nach Restart kein "timeout" und kein "SIGKILL" mehr
- [ ] Restart-Dauer < 5s (vorher: 15s + SIGKILL)
- [ ] Dashboard Stat-Karte "Verbindungsstatus": "Verbunden" wenn TCP aktiv
- [ ] Dashboard "Seit"-Anzeige: "Seit 02.06.2026" (kein T, keine Microsekunden)
- [ ] Dateien-Seite: PDFs aus DB laden, kein Fehler-Text
- [ ] Einstellungen → Testdruck: kein 415, gibt Ergebnis zurück
- [ ] `DELETE /api/protocols/1` löscht DB-Eintrag und PDF-Datei
- [ ] Topbar-Badge und Stat-Karte zeigen immer identischen Status

---

## Erfolgskriterien

Die Implementierung ist abgeschlossen, wenn:

1. `sudo systemctl restart` beendet den Service in unter 5s ohne SIGKILL im Log
2. Dashboard zeigt "Verbunden" in Stat-Karte und Topbar-Badge gleichzeitig (kein Flapping)
3. Datei-Manager zeigt die 3 Test-PDFs aus der Datenbank an

---

## Notizen

- Der SIGKILL tritt nur bei `systemctl restart/stop` auf, nicht im laufenden Betrieb —
  für Dauerbetrieb ohne Restarts weniger kritisch, aber für Deployments und Pi-Updates essentiell
- USB-PDFs werden in filemanager.html als "nicht vorhanden" angezeigt wenn kein USB — das ist korrekt
- `api/storage/stats` für USB: `detected` Flag + `used_percent`, `total_gb` wenn gemountet
- Kein Hotspot/WLAN da hardware-deaktiviert — kein UI dafür nötig
- Nach diesem Fix: nächster Milestone ist Kunden-Deployment Tierlabor Uni Essen

---

## Implementierungsnotizen

**Implementiert:** 2026-06-03

### Zusammenfassung

- `os._exit(0)` in graceful_shutdown eingefügt → Restart-Dauer von 15.211ms auf **47ms** reduziert, kein SIGKILL mehr
- `request.get_json(silent=True)` in 8 Routen → kein 415 mehr bei leerem POST-Body
- `DELETE /api/protocols/<pid>` hinzugefügt → Filemanager kann Protokolle löschen
- `dashboard.html`: `d.tcp_enabled` + Timestamp-Fix in loadStats (3 Stellen)
- `filemanager.html`: 4 API-Calls auf korrekte Endpoints + formatDate T→Space-Fix

### Abweichungen vom Plan

1. **Erster Restart noch SIGKILL**: Der erste `systemctl restart` nach dem Fix traf noch den alten Prozess (ohne `os._exit`). Zweiter Restart: 47ms, kein SIGKILL. Erwartetes Verhalten.

### Aufgetretene Probleme

Keine — alle Fixes direkt angewendet.
