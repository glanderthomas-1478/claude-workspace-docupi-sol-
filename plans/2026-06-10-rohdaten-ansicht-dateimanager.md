# Plan: Rohdaten-Ansicht im Dateimanager

**Erstellt:** 2026-06-10
**Status:** Implementiert
**Anforderung:** Dropdown im linken Pane des Dateimanagers, das zwischen PDF-Protokollen und Rohdaten (raw_captures) umschaltet — inkl. Download und USB-Sync für Captures.

---

## Überblick

### Was dieser Plan erreicht

Der linke Pane des Dateimanagers ("Interner Speicher") erhält ein Dropdown-Menü direkt über der Dateiliste. Der Nutzer wählt zwischen **PDF-Protokolle** (bestehend) und **Rohdaten (.txt/.bin)** — die empfangenen Raw-Captures aus `/data/raw_captures/`. Captures können einzeln heruntergeladen und über den bestehenden USB-Sync-Mechanismus auf USB kopiert werden.

### Warum das wichtig ist

Die `raw_captures/`-Verzeichnis hat 55+ `.bin`+`.txt`-Paare seit Tag 1 — die Daten existieren, sind aber in der UI komplett unsichtbar. Für Schritt 2 der offenen Punkte (Kalibrierung von `protocol_parser.py` auf echten PST 14-8-12 HS1 Daten) müssen diese `.txt`-Dateien heruntergeladen und analysiert werden können. Datensammlermodus-Captures aus dem Tierlabor landen hier.

---

## Aktueller Zustand

### Relevante bestehende Struktur

- `templates/filemanager.html` — Dual-Pane (intern: PDFs | USB), `loadInternalFiles()` via `/api/protocols`, `syncUsb()` via `/api/storage/sync/now`
- `app.py` Zeilen 1287–1368:
  - `GET /api/tcp_capture/captures` — Liste aller Capture-Dateien `[{name, size}]`
  - `GET /api/tcp_capture/captures/<fname>` — Download einer Datei
  - `POST /api/tcp_capture/captures/delete` — Alle löschen
  - `GET /api/dashboard/chargen` — Letzte 20 mit Preview (ungenutzt im UI)
- `data/raw_captures/` — `YYYYMMDD_HHMMSS_jobXXXX.{bin,txt}` Paare
- `storage_manager.py` `sync_pdfs_to_usb()` — kopiert PDFs nach `USB_MOUNT_POINT/docucontrol/pdfs/`

### Lücken oder Probleme, die adressiert werden

- Captures sind in der UI komplett unsichtbar — keine Möglichkeit zu sehen was gespeichert wurde
- Kein einzelner Delete pro Capture (nur "Alle löschen")
- USB-Sync deckt nur PDFs ab, keine Captures
- Für Parser-Kalibrierung müssen `.txt`-Dateien manuell per SSH runtergeladen werden

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

- `filemanager.html`: Dropdown über interner Dateiliste, Capture-Renderlogik, adaptive Sync-Button-Logik
- `app.py`: Neuer `DELETE /api/tcp_capture/captures/<fname>` Endpunkt (löscht `.txt` + `.bin` Paar), neuer `POST /api/storage/sync/captures` Endpunkt (kopiert Captures auf USB)

### Neue Dateien erstellen

Keine neuen Dateien.

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|---|---|
| `templates/filemanager.html` | Dropdown-Select, `switchIntMode()`, `loadCaptureFiles()`, `renderCaptureRow()`, adaptive `syncUsb()` |
| `app.py` | `DELETE /api/tcp_capture/captures/<fname>` + `POST /api/storage/sync/captures` |

### Zu löschende Dateien

Keine.

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **Dropdown statt drittem Tab**: Der linke Pane-Kontext bleibt "Interner Speicher" — der Modus bestimmt was gezeigt wird. Klarer als Tab-Erweiterung, keine Layout-Änderung nötig.

2. **Nur `.txt`-Dateien in der Liste, `.bin` als Zusatz-Download**: `.txt` ist der dekodierte Klartext — das was für Parser-Kalibrierung relevant ist. `.bin` ist der rohe Bytestrom — nützlich für tiefe Analyse, aber kein Standard-Download. Pro Zeile: primär `.txt` herunterladen, sekundär Knopf für `.bin` wenn vorhanden.

3. **Sync-Button adaptiert sich je nach Modus**: In PDF-Modus → `syncUsb()` wie bisher (PDFs). In Rohdaten-Modus → `syncCaptures()` ruft neuen Endpunkt auf, kopiert `.txt`+`.bin` nach `USB_MOUNT_POINT/docucontrol/captures/`. Sync-Label und Icon ändern sich entsprechend.

4. **Timestamp aus Dateiname parsen (Frontend)**: Format `YYYYMMDD_HHMMSS` (erste 15 Zeichen) ist deterministisch. Kein Backend-Umbau nötig, `/api/tcp_capture/captures` bleibt unverändert.

5. **Einzelnes Löschen als neuer DELETE-Endpunkt**: `POST /api/tcp_capture/captures/delete` (alle) bleibt erhalten. Neuer `DELETE /api/tcp_capture/captures/<fname>` löscht gezielt `.txt` + `.bin` für denselben Basename.

6. **Kein Preview inline**: Preview-Inhalt kann 3000+ Zeichen sein. Download reicht für Analyse.

### Betrachtete Alternativen

- **Dritter Tab im Dateimanager**: Sauber strukturell, aber bricht das bestehende Two-Column-Layout. Dropdown ist weniger invasiv.
- **Sub-Tab in Settings → Live-Monitor**: User sagte "irgendwo in Einstellungen" — aber Dateimanager ist semantisch richtiger. Settings würde noch voller.
- **Captures immer in USB-Sync einbeziehen**: Einfacher, aber PDFs und Captures haben unterschiedliche Workflows. Explizite Trennung ist klarer.

### Offene Fragen

Keine — Ansatz mit User abgestimmt.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: Backend — DELETE Einzeldatei + Captures-Sync-Endpunkt in app.py

Zwei neue API-Routen direkt nach dem bestehenden `DELETE /api/tcp_capture/captures/delete` Block (ca. Zeile 1368).

**Aktionen:**

- `DELETE /api/tcp_capture/captures/<fname>` hinzufügen:
  - `fname` validieren: nur `[A-Za-z0-9_\-.]` erlaubt, kein `/` (Path-Traversal-Schutz)
  - Base = `fname` ohne Extension → lösche `.txt` und `.bin` wenn vorhanden
  - Rückgabe: `{ok: true, deleted: [filenames]}`

- `POST /api/storage/sync/captures` hinzufügen:
  - Prüfe ob USB gemountet (`os.path.ismount(USB_MOUNT_POINT)`) — wenn nicht: mount versuchen via `storage_manager.mount_usb()`
  - Zielverzeichnis: `{USB_MOUNT_POINT}/docucontrol/captures/` — erstellen wenn nötig
  - Alle Dateien aus `CAPTURE_DIR` (`raw_captures/`) kopieren die noch nicht auf USB liegen (size-check wie in `sync_pdfs_to_usb`)
  - `_run("sync")` danach
  - Rückgabe: `{ok: true, copied: N, errors: E}`

**Betroffene Dateien:**
- `/home/docucontrol/docupi/app.py`

---

### Schritt 2: Frontend — Dropdown und Capture-Ansicht in filemanager.html

Alle Änderungen nur in `filemanager.html` — kein CSS in `docucontrol.css` nötig, Inline-Styles wo nötig.

**Aktionen:**

**A) HTML — Dropdown über interner Dateiliste einfügen:**

Direkt vor `<div style="overflow-x:auto">` (nach dem `storagebar`-Div) im linken Pane:

```html
<div style="display:flex;align-items:center;gap:8px;padding:8px 0 4px 0">
    <label style="font-size:0.8rem;color:var(--muted);white-space:nowrap">Ansicht:</label>
    <select id="intModeSelect" style="flex:1;padding:4px 8px;border:1px solid var(--border);border-radius:6px;background:var(--surface);color:var(--text);font-size:0.85rem" onchange="switchIntMode(this.value)">
        <option value="pdf">PDF-Protokolle</option>
        <option value="captures">Rohdaten (.txt / .bin)</option>
    </select>
</div>
```

**B) JS — `switchIntMode(mode)` Funktion:**

```javascript
var intMode = 'pdf';

function switchIntMode(mode) {
    intMode = mode;
    if (mode === 'pdf') {
        loadInternalFiles();
        document.getElementById('btnSync').innerHTML = '<i class="bi bi-arrow-repeat"></i> Jetzt sync.';
    } else {
        loadCaptureFiles();
        document.getElementById('btnSync').innerHTML = '<i class="bi bi-arrow-repeat"></i> Captures → USB';
    }
}
```

**C) JS — `loadCaptureFiles()` Funktion:**

```javascript
function parseCaptureTimestamp(fname) {
    // Format: YYYYMMDD_HHMMSS_jobXXXX.txt
    try {
        var ts = fname.substring(0, 15); // "20260610_174230"
        return ts.substring(6,8) + '.' + ts.substring(4,6) + '.' + ts.substring(0,4)
               + ' ' + ts.substring(9,11) + ':' + ts.substring(11,13);
    } catch(e) { return fname; }
}

function loadCaptureFiles() {
    fetch('/api/tcp_capture/captures')
        .then(function(r) { return r.json(); })
        .then(function(files) {
            // Nur .txt Dateien anzeigen, .bin separat abrufbar
            var txts = files.filter(function(f) { return f.name.endsWith('.txt'); })
                            .sort(function(a,b) { return b.name.localeCompare(a.name); });
            var bins = {};
            files.filter(function(f) { return f.name.endsWith('.bin'); })
                 .forEach(function(f) { bins[f.name.replace('.bin','')] = f.size; });
            
            var body = document.getElementById('intFileBody');
            if (txts.length === 0) {
                body.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:20px;color:var(--muted)"><i class="bi bi-inbox"></i> Keine Captures gespeichert</td></tr>';
                return;
            }
            body.innerHTML = txts.map(function(f) {
                return renderCaptureRow(f, bins);
            }).join('');
        }).catch(function() {
            document.getElementById('intFileBody').innerHTML =
                '<tr><td colspan="4" style="text-align:center;padding:20px;color:var(--danger)">Fehler beim Laden</td></tr>';
        });
}
```

**D) JS — `renderCaptureRow(f, bins)` Funktion:**

```javascript
function renderCaptureRow(f, bins) {
    var base = f.name.replace('.txt', '');
    var hasBin = bins.hasOwnProperty(base);
    var ts = parseCaptureTimestamp(f.name);
    var size = formatBytes(f.size);
    return '<tr>'
        + '<td style="max-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
        +   '<div class="fn" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
        +   '<i class="bi bi-file-earmark-text" style="color:var(--accent)"></i> ' + escHtml(base) + '</div></td>'
        + '<td class="muted" style="white-space:nowrap">' + escHtml(ts) + '</td>'
        + '<td class="muted">' + escHtml(size) + '</td>'
        + '<td class="right"><div class="act">'
        + '<a class="icon-btn" title=".txt laden" href="/api/tcp_capture/captures/' + encodeURIComponent(f.name) + '" download="' + escHtml(f.name) + '"><i class="bi bi-download"></i></a>'
        + (hasBin ? '<a class="icon-btn" title=".bin laden" href="/api/tcp_capture/captures/' + encodeURIComponent(base + '.bin') + '" download="' + escHtml(base + '.bin') + '"><i class="bi bi-file-binary"></i></a>' : '')
        + '<button class="icon-btn danger" title="Löschen" onclick="delCapture(' + "'" + escHtml(base) + "'" + ')"><i class="bi bi-trash"></i></button>'
        + '</div></td>'
        + '</tr>';
}
```

**E) JS — `delCapture(base)` Funktion:**

```javascript
window.delCapture = function(base) {
    if (!confirm('Capture "' + base + '" wirklich löschen?')) return;
    fetch('/api/tcp_capture/captures/' + encodeURIComponent(base + '.txt'), { method: 'DELETE' })
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.ok) loadCaptureFiles();
            else alert('Fehler: ' + (d.error || 'Unbekannt'));
        }).catch(function() {});
};
```

**F) JS — `syncUsb()` anpassen:**

Die bestehende `syncUsb()` Funktion erweitern: wenn `intMode === 'captures'`, rufe `/api/storage/sync/captures` statt `/api/storage/sync/now` auf.

```javascript
window.syncUsb = function() {
    var btn = document.getElementById('btnSync');
    btn.disabled = true;
    var isCaptures = intMode === 'captures';
    btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> ' + (isCaptures ? 'Kopiere …' : 'Synchronisiere ...');
    var endpoint = isCaptures ? '/api/storage/sync/captures' : '/api/storage/sync/now';
    fetch(endpoint, { method: 'POST' })
        .then(function(r) { return r.json(); })
        .then(function() {
            if (!isCaptures) { loadInternalFiles(); loadUsbFiles(); }
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> ' + (isCaptures ? 'Captures → USB' : 'Jetzt sync.');
        }).catch(function() {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> ' + (isCaptures ? 'Captures → USB' : 'Jetzt sync.');
        });
};
```

**Betroffene Dateien:**
- `/home/docucontrol/docupi/templates/filemanager.html`

---

### Schritt 3: Deploy auf Pi

Deploy via SSH — direkt auf den Pi schreiben.

**Aktionen:**
- Geänderte `filemanager.html` via `scp` auf Pi deployen: `/home/docucontrol/docupi/templates/filemanager.html`
- Geändertes `app.py` via `scp` auf Pi deployen: `/home/docucontrol/docupi/app.py`
- Service neu starten: `sudo systemctl restart docucontrol.service`
- Service-Status prüfen: `systemctl status docucontrol.service`

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/templates/filemanager.html`
- Pi: `/home/docucontrol/docupi/app.py`

---

### Schritt 4: Verifikation

**Aktionen:**
- Browser: `http://192.168.0.171/files` öffnen
- Dropdown erscheint über der linken Dateiliste
- "Rohdaten" wählen → Captures erscheinen mit Datum, Größe, Download-Buttons
- `.txt`-Download eines Captures testen
- `.bin`-Download testen (falls vorhanden)
- Löschen eines einzelnen Captures testen → Zeile verschwindet
- Sync-Button-Label wechselt je nach Modus
- "PDF-Protokolle" zurückwählen → PDFs erscheinen wieder, Label "Jetzt sync."

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- `app.py` — `/api/tcp_capture/captures` und neuer DELETE-Endpunkt
- `tcp_print_capture.py` — schreibt in `CAPTURE_DIR`, keine Änderung nötig
- `storage_manager.py` — `mount_usb()` und `USB_MOUNT_POINT` werden vom neuen Sync-Endpunkt genutzt (import bereits in app.py)

### Nötige Updates für Konsistenz

- `CLAUDE.md` — neuen API-Endpunkt `DELETE /api/tcp_capture/captures/<fname>` und `POST /api/storage/sync/captures` in die Endpunkt-Liste eintragen
- `context/strategy.md` und `context/current-data.md` — Rohdaten-Ansicht als erledigt markieren

### Auswirkungen auf bestehende Workflows

- Bestehende PDF-Ansicht im Dateimanager: keine Änderung, nur Erweiterung um Dropdown
- USB-Sync PDFs: unverändert (nur wenn intMode === 'pdf')
- Datensammlermodus: Captures, die durch den Sammelmodus entstehen, erscheinen automatisch in der neuen Ansicht

---

## Validierungs-Checkliste

- [ ] Dropdown erscheint über der linken Dateiliste in `/files`
- [ ] "Rohdaten" Modus zeigt alle `.txt`-Captures mit korrektem Datum aus Dateiname
- [ ] `.txt`-Download funktioniert (direkter Download via Browser)
- [ ] `.bin`-Download erscheint nur wenn `.bin`-Datei existiert
- [ ] Einzellöschen entfernt `.txt` UND `.bin` für denselben Basename
- [ ] PDF-Modus bleibt unverändert funktionsfähig
- [ ] Sync-Button-Label wechselt korrekt je nach Modus
- [ ] "Captures → USB": kopiert `.txt`+`.bin` nach `USB_MOUNT_POINT/docucontrol/captures/` (wenn USB verbunden)
- [ ] Service-Restart sauber (< 1s, os._exit Fix aktiv)
- [ ] CLAUDE.md aktualisiert

---

## Erfolgskriterien

1. Alle 55+ bestehenden Captures sind im UI sichtbar und downloadbar
2. Neue Captures (Datensammlermodus Tierlabor) erscheinen sofort in der Liste
3. `.txt`-Dateien können per Browser heruntergeladen und direkt in einem Texteditor für Parser-Analyse geöffnet werden
4. USB-Copy der Captures ist per Button auslösbar

---

## Notizen

- Die `bi-file-binary` Bootstrap-Icon-Klasse ist ab Bootstrap Icons 1.10+ verfügbar. Falls sie nicht rendert, `bi-file-earmark-code` als Fallback nutzen.
- Für den Captures-USB-Sync muss kein Datums-Cutoff wie bei PDFs gelten — alle Captures kopieren (meist < 1 MB gesamt).
- Spätere Erweiterung denkbar: Captures direkt im Browser anzeigen (Modal mit `.txt`-Inhalt). Nicht in diesem Plan.

---

## Implementierungsnotizen

**Implementiert:** 2026-06-10

### Zusammenfassung

- Zwei neue Backend-Routen in `app.py` eingefügt (nach Zeile 1368): `DELETE /api/tcp_capture/captures/<fname>` und `POST /api/storage/sync/captures`
- `filemanager.html` vollständig überarbeitet: Dropdown, `switchIntMode()`, `loadCaptureFiles()`, `renderCaptureRow()`, `parseCaptureTimestamp()`, `delCapture()`, adaptive `syncUsb()`
- Beide Dateien auf Pi deployed, Service neu gestartet (active)
- CLAUDE.md aktualisiert

### Abweichungen vom Plan

- `.bin`-Icon: `bi-file-binary` durch `bi-file-earmark-code` ersetzt (robuster, verfügbar in allen Bootstrap Icons Versionen)
- Interval-Reload in Init: adaptiert — ruft `loadCaptureFiles()` wenn Modus aktiv, sonst `loadInternalFiles()`

### Aufgetretene Probleme

Keine. Alle drei API-Tests bestanden: Liste (60 Dateien), DELETE-Einzeldatei (60→58, `.txt`+`.bin` gelöscht), Sync-Captures (korrekte USB-Fehlermeldung).
