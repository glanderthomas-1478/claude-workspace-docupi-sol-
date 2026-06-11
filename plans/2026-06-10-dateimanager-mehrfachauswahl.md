# Plan: Dateimanager — Mehrfachauswahl und Bulk-Aktionen

**Erstellt:** 2026-06-10
**Status:** Implementiert
**Anforderung:** Checkboxen in allen drei Listenansichten (PDF intern, Rohdaten intern, USB) — Bulk-Löschen auf beiden Seiten, Bulk-Kopieren auf USB aus der internen Seite. USB-Zeilen: Download-Button entfernen (Quelle ist interne Karte), Einzel-Löschen hinzufügen.

---

## Überblick

### Was dieser Plan erreicht

Alle Tabellenzeilen im Dateimanager bekommen Checkboxen. Eine Bulk-Aktionsleiste erscheint oberhalb der Tabelle sobald mindestens eine Datei markiert ist und zeigt die Aktionen "Löschen" (beide Seiten) und "Auf USB kopieren" (nur linke Seite, nur wenn USB verbunden). Drei neue Backend-Endpunkte ermöglichen das atomare Batch-Löschen von Protokollen und das gezielte Kopieren ausgewählter PDFs und Captures auf USB.

### Warum das wichtig ist

Für den Kundentermin nächste Woche und den produktiven Einsatz im Tierlabor: wenn der Pi Testchargen enthält die vor der Installation entfernt werden sollen, oder wenn man nach einer Datensammelsession gezielt bestimmte Captures auf USB ziehen will, ist Einzelauswahl unpraktisch.

---

## Aktueller Zustand

### Relevante bestehende Struktur

- `templates/filemanager.html` — Dual-Pane, drei Render-Modi (PDF, Captures, USB), bestehende Einzelaktionen per Zeile
- `app.py`:
  - `DELETE /api/protocols/<id>` — Einzellöschung Protokoll (DB + PDF-Datei)
  - `DELETE /api/tcp_capture/captures/<fname>` — Einzellöschung Capture-Paar (.txt + .bin)
  - `POST /api/storage/delete` — Einzellöschung USB-Datei `{pane, path}`
  - `POST /api/storage/copy` — Einzelkopie `{from, to, path}` — nutzt Pfad relativ zu SD_PDF_DIR
  - `POST /api/storage/sync/captures` — kopiert ALLE Captures auf USB

### Lücken oder Probleme, die adressiert werden

- Keine Mehrfachauswahl vorhanden — nur Einzelaktionen
- Für Bulk-Löschen von Protokollen: `DELETE /api/protocols/<id>` akzeptiert nur eine ID
- `POST /api/storage/copy` benötigt den Dateipfad relativ zu SD_PDF_DIR — der Frontend kennt nur `pdf_filename` (Basename), nicht den Unterordner (`2026/2026-06/`)
- `POST /api/storage/sync/captures` kopiert immer alle Captures, nicht gezielt ausgewählte

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

**Backend (app.py):**
- `POST /api/protocols/bulk-delete` — nimmt `{ids: [1,2,3]}`, löscht Batch-weise DB-Einträge + PDF-Dateien
- `POST /api/protocols/bulk-copy-usb` — nimmt `{ids: [1,2,3]}`, löst Pfad aus DB auf, kopiert PDFs auf USB
- `POST /api/tcp_capture/captures/bulk-copy-usb` — nimmt `{basenames: ["...", "..."]}`, kopiert gezielt .txt+.bin auf USB

**Frontend (filemanager.html):**
- Checkbox-Spalte als erste Spalte in allen drei Tabellentypen (PDF, Captures, USB)
- Select-All-Checkbox im `<th>`
- Bulk-Aktionsleiste pro Pane (erscheint wenn Auswahl > 0)
- JS-Logik: `selectedInt = new Set()`, `selectedUsb = new Set()`, Event-Handler, Bulk-Aktions-Funktionen

### Neue Dateien erstellen

Keine.

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|---|---|
| `app.py` (Pi) | 3 neue POST-Endpunkte für Bulk-Operationen |
| `templates/filemanager.html` (Pi) | Checkboxen, Bulk-Leiste, JS-Logik |

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **Deletes als parallele Einzelrequests vom Frontend**: `Promise.all()` über bestehende Einzel-Endpunkte — kein neuer Bulk-Delete-Endpunkt nötig. Einfacher, robust, kein neues Backend-Code für Löschlogik.

2. **Kopier-Operationen als neue Batch-Endpunkte**: Weil der Frontend die vollständigen Dateipfade nicht kennt (`pdf_filename` ist nur Basename, echter Pfad enthält Datumsordner `2026/2026-06/`). Der Server löst Pfade aus DB auf.

3. **Bulk-Aktionsleiste oberhalb der Tabelle, pro Pane getrennt**: Je eine Leiste über der internen Tabelle und eine über der USB-Tabelle. Erscheint nur wenn ≥1 Element ausgewählt. Zeigt `N ausgewählt | [Löschen] [Auf USB kopieren]`.

4. **"Auf USB kopieren" nur wenn USB verbunden**: Button ist disabled wenn `!usbConnected`. Adapts sich wie der Sync-Button.

5. **Checkbox-Zustand wird beim Reload der Liste zurückgesetzt**: Nach einer Bulk-Aktion wird die Liste neu geladen → alle Checkboxen weg. Kein Persistenz-Overhead.

6. **intMode-aware Bulk-Logik**: In PDF-Modus nutzt Bulk-Delete `DELETE /api/protocols/<id>`, in Captures-Modus `DELETE /api/tcp_capture/captures/<fname>`. Bulk-Copy-Endpunkte analog.

### Betrachtete Alternativen

- **Ein einzelner Bulk-Endpunkt für alles**: Zu komplex, vermischt PDF- und Capture-Logik.
- **Drag-and-Drop statt Checkboxen**: Zu aufwändig für den Anwendungsfall.
- **Sync-all bei Capture-Copy**: Würde immer alle Captures kopieren, nicht nur ausgewählte — verwirrend für den User.

### Offene Fragen

Keine.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: Backend — 3 neue Bulk-Endpunkte in app.py

Einfügen nach `POST /api/storage/sync/captures` (ca. Zeile 1425).

**Endpunkt 1: `POST /api/protocols/bulk-delete`**
```python
@app.route('/api/protocols/bulk-delete', methods=['POST'])
def api_protocols_bulk_delete():
    data = request.get_json(silent=True) or {}
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'ok': False, 'error': 'keine IDs'}), 400
    db = get_db()
    deleted = 0
    errors = 0
    for pid in ids:
        try:
            row = db.execute('SELECT pdf_path FROM protocols WHERE id=?', (pid,)).fetchone()
            if not row:
                continue
            pdf_path = row['pdf_path']
            db.execute('DELETE FROM protocols WHERE id=?', (pid,))
            db.commit()
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
            deleted += 1
        except Exception as e:
            logger.error(f'Bulk-Delete Protokoll {pid}: {e}')
            errors += 1
    db.close()
    log_event('INFO', f'Bulk-Delete: {deleted} Protokolle gelöscht')
    return jsonify({'ok': True, 'deleted': deleted, 'errors': errors})
```

**Endpunkt 2: `POST /api/protocols/bulk-copy-usb`**
```python
@app.route('/api/protocols/bulk-copy-usb', methods=['POST'])
def api_protocols_bulk_copy_usb():
    import shutil as _shutil
    data = request.get_json(silent=True) or {}
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'ok': False, 'error': 'keine IDs'}), 400
    if not os.path.ismount(USB_MOUNT_POINT):
        ok, msg = mount_usb()
        if not ok:
            return jsonify({'ok': False, 'error': msg}), 400
    usb_pdf_dir = os.path.join(USB_MOUNT_POINT, USB_PDF_SUBDIR)
    os.makedirs(usb_pdf_dir, exist_ok=True)
    db = get_db()
    copied = 0
    errors = 0
    for pid in ids:
        try:
            row = db.execute('SELECT pdf_path, pdf_filename FROM protocols WHERE id=?', (pid,)).fetchone()
            if not row or not row['pdf_path']:
                continue
            src = row['pdf_path']
            if not os.path.exists(src):
                continue
            dst = os.path.join(usb_pdf_dir, row['pdf_filename'])
            if os.path.exists(dst) and os.path.getsize(src) == os.path.getsize(dst):
                copied += 1
                continue
            _shutil.copy2(src, dst)
            copied += 1
        except Exception as e:
            logger.error(f'Bulk-Copy PDF {pid}: {e}')
            errors += 1
    db.close()
    import subprocess as _sp
    _sp.run(['sync'], check=False)
    log_event('INFO', f'Bulk-Copy PDF auf USB: {copied} Dateien')
    return jsonify({'ok': True, 'copied': copied, 'errors': errors})
```

**Endpunkt 3: `POST /api/tcp_capture/captures/bulk-copy-usb`**
```python
@app.route('/api/tcp_capture/captures/bulk-copy-usb', methods=['POST'])
def api_captures_bulk_copy_usb():
    import shutil as _shutil
    data = request.get_json(silent=True) or {}
    basenames = data.get('basenames', [])
    if not basenames:
        return jsonify({'ok': False, 'error': 'keine Basenames'}), 400
    capture_dir = '/home/docucontrol/docupi/data/raw_captures'
    if not os.path.ismount(USB_MOUNT_POINT):
        ok, msg = mount_usb()
        if not ok:
            return jsonify({'ok': False, 'error': msg}), 400
    usb_cap_dir = os.path.join(USB_MOUNT_POINT, 'docucontrol', 'captures')
    os.makedirs(usb_cap_dir, exist_ok=True)
    copied = 0
    errors = 0
    for base in basenames:
        for ext in ('.txt', '.bin'):
            src = os.path.join(capture_dir, base + ext)
            if not os.path.exists(src):
                continue
            dst = os.path.join(usb_cap_dir, base + ext)
            try:
                if os.path.exists(dst) and os.path.getsize(src) == os.path.getsize(dst):
                    continue
                _shutil.copy2(src, dst)
                copied += 1
            except Exception as e:
                logger.error(f'Bulk-Copy Capture {base}{ext}: {e}')
                errors += 1
    import subprocess as _sp
    _sp.run(['sync'], check=False)
    log_event('INFO', f'Bulk-Copy Captures auf USB: {copied} Dateien')
    return jsonify({'ok': True, 'copied': copied, 'errors': errors})
```

**Aktionen:**
- Alle drei Endpunkte via SSH-Python-Script nach `api_storage_sync_captures` einfügen
- Verifizieren: `grep -n 'bulk' /home/docucontrol/docupi/app.py` → alle drei Routennamen sichtbar

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/app.py`

---

### Schritt 2: Frontend — filemanager.html komplett neu schreiben

Die Datei wird lokal in `/tmp/filemanager.html` aufgebaut und dann deployt.

**A) HTML: Bulk-Aktionsleisten** — je eine für linke und rechte Pane, direkt nach dem `storagebar`-Div und vor dem Dropdown (links) bzw. direkt vor der Tabelle (rechts):

Linke Pane (nach storagebar, vor Dropdown):
```html
<div id="bulkBarInt" style="display:none;padding:6px 0;display:none;align-items:center;gap:8px;flex-wrap:wrap">
    <span id="bulkCountInt" style="font-size:0.85rem;color:var(--muted)">0 ausgewählt</span>
    <button class="btn btn-sm btn-danger" onclick="bulkDeleteInt()" id="btnBulkDelInt">
        <i class="bi bi-trash"></i> Löschen
    </button>
    <button class="btn btn-sm btn-outline" onclick="bulkCopyUsb()" id="btnBulkCopyUsb" disabled>
        <i class="bi bi-usb-drive"></i> Auf USB kopieren
    </button>
</div>
```

Rechte Pane (vor der USB-Tabelle):
```html
<div id="bulkBarUsb" style="display:none;padding:6px 0;align-items:center;gap:8px">
    <span id="bulkCountUsb" style="font-size:0.85rem;color:var(--muted)">0 ausgewählt</span>
    <button class="btn btn-sm btn-danger" onclick="bulkDeleteUsb()" id="btnBulkDelUsb">
        <i class="bi bi-trash"></i> Löschen
    </button>
</div>
```

**B) HTML: Tabellen-Header** — erste Spalte wird Checkbox-Spalte (`width:32px`):

Für `intFileList` und USB-Tabelle — `<th>` ersetzen:
```html
<th style="width:32px;padding-right:0">
    <input type="checkbox" id="selAllInt" onchange="selectAllInt(this.checked)" style="cursor:pointer">
</th>
```

**C) JS: Selection-State**
```javascript
var selectedInt = new Set();   // IDs (PDF-Modus) oder Basenames (Captures-Modus)
var selectedUsb = new Set();   // Pfade (USB-Dateinamen)
var usbConnected = false;      // wird in loadUsbFiles() gesetzt
```

**D) JS: `updateBulkBarInt()` und `updateBulkBarUsb()`**
```javascript
function updateBulkBarInt() {
    var n = selectedInt.size;
    var bar = document.getElementById('bulkBarInt');
    bar.style.display = n > 0 ? 'flex' : 'none';
    document.getElementById('bulkCountInt').textContent = n + ' ausgewählt';
    document.getElementById('btnBulkCopyUsb').disabled = !usbConnected;
}
function updateBulkBarUsb() {
    var n = selectedUsb.size;
    var bar = document.getElementById('bulkBarUsb');
    bar.style.display = n > 0 ? 'flex' : 'none';
    document.getElementById('bulkCountUsb').textContent = n + ' ausgewählt';
}
```

**E) JS: `selectAllInt(checked)` und `selectAllUsb(checked)`**
```javascript
function selectAllInt(checked) {
    selectedInt.clear();
    document.querySelectorAll('#intFileBody .row-sel').forEach(function(cb) {
        cb.checked = checked;
        if (checked) selectedInt.add(cb.value);
    });
    updateBulkBarInt();
}
function selectAllUsb(checked) {
    selectedUsb.clear();
    document.querySelectorAll('#usbFileBody .row-sel').forEach(function(cb) {
        cb.checked = checked;
        if (checked) selectedUsb.add(cb.value);
    });
    updateBulkBarUsb();
}
```

**F) JS: Checkbox in `renderFileRow()` — PDF-Modus**

Erste `<td>` der Zeile wird Checkbox (value = ID):
```javascript
'<td style="width:32px;padding-right:0"><input type="checkbox" class="row-sel" value="' + id + '" onchange="toggleSelInt(this)" style="cursor:pointer"></td>'
```

`toggleSelInt(cb)`:
```javascript
function toggleSelInt(cb) {
    if (cb.checked) selectedInt.add(cb.value);
    else selectedInt.delete(cb.value);
    // Sync select-all Checkbox
    var all = document.querySelectorAll('#intFileBody .row-sel');
    document.getElementById('selAllInt').checked = all.length > 0 && selectedInt.size === all.length;
    updateBulkBarInt();
}
```

**G) JS: Checkbox in `renderCaptureRow()` — Captures-Modus**

Analog, value = Base-Name:
```javascript
'<td style="width:32px;padding-right:0"><input type="checkbox" class="row-sel" value="' + escHtml(base) + '" onchange="toggleSelInt(this)" style="cursor:pointer"></td>'
```

**H) JS: `renderUsbFileRow()` — USB-Modus überarbeiten**

- Download-Button (`<a class="icon-btn" ...download...>`) entfernen
- Einzel-Löschen pro Zeile hinzufügen: `<button class="icon-btn danger" onclick="delUsbFile('...')">` → ruft `POST /api/storage/delete` auf
- Checkbox-Spalte als erste Spalte (value = Dateiname/Pfad):

```javascript
'<td style="width:32px;padding-right:0"><input type="checkbox" class="row-sel" value="' + escHtml(fn) + '" onchange="toggleSelUsb(this)" style="cursor:pointer"></td>'
```

`delUsbFile(path)`:
```javascript
window.delUsbFile = function(path) {
    if (!confirm('Datei auf USB wirklich löschen?')) return;
    fetch('/api/storage/delete', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({pane: 'usb', path: path})
    }).then(function(r) { return r.json(); })
      .then(function(d) { if (d.success) loadUsbFiles(); })
      .catch(function() {});
};
```

`toggleSelUsb(cb)` analog zu `toggleSelInt`.

**I) JS: `bulkDeleteInt()`**
```javascript
window.bulkDeleteInt = function() {
    if (selectedInt.size === 0) return;
    if (!confirm(selectedInt.size + ' Einträge wirklich löschen?')) return;
    var ids = Array.from(selectedInt);
    var btn = document.getElementById('btnBulkDelInt');
    btn.disabled = true;
    if (intMode === 'pdf') {
        fetch('/api/protocols/bulk-delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ids: ids.map(Number)})
        }).then(function(r) { return r.json(); })
          .then(function(d) {
              selectedInt.clear();
              updateBulkBarInt();
              document.getElementById('selAllInt').checked = false;
              btn.disabled = false;
              loadInternalFiles();
          }).catch(function() { btn.disabled = false; });
    } else {
        // Captures-Modus: parallele DELETE-Requests
        Promise.all(ids.map(function(base) {
            return fetch('/api/tcp_capture/captures/' + encodeURIComponent(base + '.txt'), {method: 'DELETE'});
        })).then(function() {
            selectedInt.clear();
            updateBulkBarInt();
            document.getElementById('selAllInt').checked = false;
            btn.disabled = false;
            loadCaptureFiles();
        }).catch(function() { btn.disabled = false; });
    }
};
```

**J) JS: `bulkCopyUsb()`**
```javascript
window.bulkCopyUsb = function() {
    if (selectedInt.size === 0) return;
    var ids = Array.from(selectedInt);
    var btn = document.getElementById('btnBulkCopyUsb');
    btn.disabled = true;
    var origText = btn.innerHTML;
    btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> Kopiere …';
    var endpoint, body;
    if (intMode === 'pdf') {
        endpoint = '/api/protocols/bulk-copy-usb';
        body = JSON.stringify({ids: ids.map(Number)});
    } else {
        endpoint = '/api/tcp_capture/captures/bulk-copy-usb';
        body = JSON.stringify({basenames: ids});
    }
    fetch(endpoint, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: body
    }).then(function(r) { return r.json(); })
      .then(function(d) {
          btn.disabled = !usbConnected;
          btn.innerHTML = origText;
          loadUsbFiles();
      }).catch(function() {
          btn.disabled = !usbConnected;
          btn.innerHTML = origText;
      });
};
```

**K) JS: `bulkDeleteUsb()`**
```javascript
window.bulkDeleteUsb = function() {
    if (selectedUsb.size === 0) return;
    if (!confirm(selectedUsb.size + ' Dateien auf USB wirklich löschen?')) return;
    var paths = Array.from(selectedUsb);
    var btn = document.getElementById('btnBulkDelUsb');
    btn.disabled = true;
    Promise.all(paths.map(function(p) {
        return fetch('/api/storage/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({pane: 'usb', path: p})
        });
    })).then(function() {
        selectedUsb.clear();
        updateBulkBarUsb();
        document.getElementById('selAllUsb').checked = false;
        btn.disabled = false;
        loadUsbFiles();
    }).catch(function() { btn.disabled = false; });
};
```

**L) JS: `usbConnected` in `loadUsbFiles()` setzen**

In `loadUsbFiles()` bei der USB-Status-Auswertung: `usbConnected = connected;` setzen und `updateBulkBarInt()` aufrufen damit der Copy-Button korrekt enabled/disabled wird.

**M) JS: Selection beim Moduswechsel leeren**

In `switchIntMode()`: `selectedInt.clear(); updateBulkBarInt(); document.getElementById('selAllInt').checked = false;`

**N) JS: colspan in leeren Zustand-Rows anpassen**

Alle `colspan="4"` → `colspan="5"` in Empty-State-Rows (3 Stellen: PDF-Modus, Captures-Modus, USB-Tabelle).

**Aktionen:**
- Aktuelle `filemanager.html` von Pi laden
- Alle beschriebenen Änderungen einarbeiten
- Deployen via `scp`

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/templates/filemanager.html`

---

### Schritt 3: Deploy und Service-Restart

**Aktionen:**
- `scp` filemanager.html auf Pi
- `sudo systemctl restart docucontrol.service`
- Service-Status prüfen

---

### Schritt 4: Verifikation

**Aktionen:**
- Browser `http://192.168.0.171/files` → Checkbox-Spalte sichtbar in beiden Panes
- Einzelne Checkbox → Bulk-Leiste erscheint mit "1 ausgewählt"
- Select-All → alle markiert, Bulk-Leiste zeigt korrekte Anzahl
- Bulk-Löschen (PDF): 2 Protokolle markieren → löschen → verschwinden aus Liste
- Rohdaten-Modus: Captures markieren → Bulk-Delete funktioniert
- USB-Seite: Dateien markieren → Bulk-Delete erscheint

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- `app.py` — bestehende `DELETE /api/protocols/<id>` und `POST /api/storage/delete` bleiben unberührt (weiter für Einzelaktionen genutzt)
- `storage_manager.py` — keine Änderung

### Nötige Updates für Konsistenz

- `CLAUDE.md` — 3 neue API-Endpunkte dokumentieren

### Auswirkungen auf bestehende Workflows

- Einzelaktionen pro Zeile bleiben vollständig erhalten — Checkboxen sind additiv
- USB Auto-Sync bleibt unverändert

---

## Validierungs-Checkliste

- [ ] Checkbox-Spalte in allen drei Tabellen (PDF, Captures, USB) sichtbar
- [ ] Select-All-Checkbox im Header markiert/demarkiert alle Zeilen
- [ ] Bulk-Leiste (links) erscheint bei Auswahl, verschwindet bei leer
- [ ] Bulk-Leiste (rechts/USB) erscheint bei Auswahl, verschwindet bei leer
- [ ] "Auf USB kopieren" disabled wenn kein USB verbunden
- [ ] Bulk-Löschen PDF: löscht DB + PDF-Datei, Liste aktualisiert sich
- [ ] Bulk-Löschen Captures: löscht .txt + .bin Paare, Liste aktualisiert sich
- [ ] Bulk-Löschen USB: löscht Dateien von USB-Stick, Liste aktualisiert sich
- [ ] Moduswechsel (Dropdown) leert die Auswahl
- [ ] Einzelaktionen pro Zeile weiterhin funktionsfähig
- [ ] Service-Restart sauber

---

## Erfolgskriterien

1. Mehrere Protokolle auf einmal löschbar (PDF-Modus, linke Pane)
2. Mehrere Captures auf einmal auf USB kopierbar (Captures-Modus, linke Pane)
3. Mehrere USB-Dateien auf einmal löschbar (rechte Pane)
4. Alle Einzelaktionen unverändert funktionsfähig

---

## Notizen

- `colspan` in leeren Zustand-Rows von 4 auf 5 erhöhen — sonst verschiebt sich das Layout
- Nach Bulk-Aktion wird die Liste neu geladen → Checkboxen werden automatisch zurückgesetzt (kein gesonderter Reset-Code nötig außer für `selectedInt`/`selectedUsb` Sets)
- `btn-sm` und `btn-danger` CSS-Klassen sollten in docucontrol.css vorhanden sein — falls nicht, Inline-Style als Fallback

---

## Implementierungsnotizen

**Implementiert:** 2026-06-10

### Zusammenfassung

3 neue Backend-Endpunkte in app.py eingefügt (nach api_storage_sync_captures). filemanager.html vollständig neu geschrieben: Checkboxen in allen drei Tabellen, zwei Bulk-Leisten, alle Einzel- und Bulk-Aktionen. USB-Zeilen: Download-Button entfernt, Einzel-Löschen hinzugefügt.

### Abweichungen vom Plan

Keine.

### Aufgetretene Probleme

Keine. Alle drei Endpunkte antworten korrekt. `/files` liefert HTTP 200.
