# Plan: Globaler Ansicht-Toggle + Captures Auto-Sync auf USB

**Erstellt:** 2026-06-10
**Status:** Implementiert
**Anforderung:** Rohdaten (Captures) werden automatisch auf USB synchronisiert; Datei-Manager hat einen gemeinsamen Modus-Toggle der beide Panes gleichzeitig zwischen "PDF" und "Rohdaten" umschaltet.

---

## Überblick

### Was dieser Plan erreicht

Der Datei-Manager erhält einen globalen Modus-Toggle ("PDF-Protokolle" / "Rohdaten") oberhalb beider Panes. In "PDF"-Modus zeigt die linke Pane interne PDFs und die rechte Pane USB-PDFs — wie bisher. In "Rohdaten"-Modus zeigt die linke Pane interne Captures (`data/raw_captures/`) und die rechte Pane die Captures auf dem USB-Stick. Zusätzlich werden Captures automatisch per Auto-Sync auf USB kopiert (bei Einstecken + alle 15 min), genauso wie PDFs.

### Warum das wichtig ist

Für den Kundentermin Tierlabor Uni Essen nächste Woche sollen Rohdaten (PST 14-8-12 HS1 Protokollvarianten) auf USB mitgenommen werden können — sowohl manuell als auch automatisch beim Einstecken — um `protocol_parser.py` zu kalibrieren. Der globale Toggle macht die Bedienung intuitiv: ein Schalter steuert beide Panes.

---

## Aktueller Zustand

### Relevante bestehende Struktur

- `storage_manager.py`: `USB_PDF_SUBDIR = "DocuControl"`, `sync_pdfs_to_usb()`, `_auto_sync_loop()` (ruft nur `sync_pdfs_to_usb()` auf)
- `app.py`:
  - `GET /api/storage/pdfs/<pane>` — listet PDFs (sd oder usb)
  - `POST /api/storage/sync/captures` — manueller Captures-Sync auf USB (schreibt nach `docucontrol/captures/`)
  - Kein `GET /api/storage/captures/usb` Endpunkt
- `filemanager.html`:
  - `intMode` Dropdown (`intModeSelect`) nur für linke Pane, per `switchIntMode()`
  - Rechte Pane ruft immer `loadUsbFiles()` → `GET /api/storage/pdfs/usb` — kein Captures-Modus
  - Sync-Button wechselt bereits Endpunkt je nach `intMode` (`sync/now` vs `sync/captures`)

### Lücken oder Probleme, die adressiert werden

1. **Auto-Sync ist einseitig**: `_auto_sync_loop()` synchronisiert nur PDFs, Captures werden nie automatisch auf USB kopiert.
2. **Kein USB-Captures-Endpunkt**: Es gibt keine API um Captures vom USB-Stick aufzulisten.
3. **Rechte Pane ignoriert den Modus**: USB-Pane zeigt immer nur PDFs, egal welcher Modus links gewählt ist — das ist inkonsistent.
4. **Dropdown ist links-lokal**: Der Toggle sitzt nur über der linken Pane — ein globaler Toggle über beiden Panes wäre klarer.

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

- `storage_manager.py`: `USB_CAPTURE_SUBDIR` Konstante, `sync_captures_to_usb()` Funktion, `_auto_sync_loop()` ruft beides auf
- `app.py`: `GET /api/storage/captures/usb` Endpunkt (listet `.txt`/`.bin` vom USB-Stick)
- `filemanager.html`: Dropdown entfernen, globaler Toggle im Seiten-Header; rechte Pane lädt je nach Modus PDFs oder Captures

### Neue Dateien erstellen

Keine.

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|---|---|
| Pi: `storage_manager.py` | `USB_CAPTURE_SUBDIR` Konstante; `sync_captures_to_usb()` Funktion; `_auto_sync_loop()` erweitern |
| Pi: `app.py` | `GET /api/storage/captures/usb` Endpunkt hinzufügen |
| Pi: `templates/filemanager.html` | Globaler Mode-Toggle, rechte Pane adaptiert sich, `switchIntMode` → `switchMode` (global) |

### Zu löschende Dateien

Keine.

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **Globaler Toggle über beiden Panes**: Ein `<select>` oder zwei Buttons ("PDF-Protokolle" / "Rohdaten") in der Seiten-Überschrift, oberhalb beider Tabellen. Klarer als ein lokaler Dropdown links.

2. **USB-Captures-Pfad: `docucontrol/captures/`**: Bereits von `POST /api/storage/sync/captures` verwendet (aus Vorkontext). Konsistent halten statt neuen Subdir einführen.

3. **Auto-Sync: Captures UND PDFs zusammen**: `_auto_sync_loop()` ruft nach dem PDF-Sync auch `sync_captures_to_usb()` auf. Kein eigener Intervall-Mechanismus — beide teilen denselben Timer.

4. **USB-Captures-Listing zeigt nur `.txt`-Dateien** (nicht `.bin`): Die `.bin` sind Binärdaten ohne direkten Nutzwert für den Datei-Manager. `.bin` wird beim Sync mitgenommen, aber im Listing nur `.txt` angezeigt (plus Info `+bin`). Damit bleibt die Anzeige lesbar.

5. **Sync-Button verhält sich wie bisher**: Bei Modus "pdf" → `POST /api/storage/sync/now`; bei "captures" → `POST /api/storage/sync/captures`. Kein Änderungsbedarf.

### Betrachtete Alternativen

- **Separater Tab "Rohdaten"**: Zu viel Aufwand, bricht das Dual-Pane-Konzept.
- **Toggle nur links, rechts bleibt PDF**: Wäre inkonsistent — wenn links Captures, sollte rechts auch Captures zeigen.
- **Alle Dateien auf USB anzeigen**: Würde `.bin` mitanzeigen — zu technisch für Endnutzer.

### Offene Fragen

Keine — alle Design-Entscheidungen sind klar.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: `storage_manager.py` — Captures-Sync hinzufügen

Drei Ergänzungen per SSH-Patch:

**1a — Konstante** direkt nach `USB_PDF_SUBDIR`:
```python
USB_CAPTURE_SUBDIR = "docucontrol/captures"  # Subfolder on USB for raw captures
```

**1b — Funktion** `sync_captures_to_usb()` direkt nach `sync_pdfs_to_usb()`:
```python
def sync_captures_to_usb(days=None):
    """Sync raw capture files from last N days from SD to USB stick."""
    config = load_sync_config()
    if days is None:
        days = config.get("sync_days", 7)

    if not os.path.ismount(USB_MOUNT_POINT):
        ok, msg = mount_usb()
        if not ok:
            return False, msg, 0

    capture_dir = "/home/docucontrol/docupi/data/raw_captures"
    usb_capture_dir = os.path.join(USB_MOUNT_POINT, USB_CAPTURE_SUBDIR)
    os.makedirs(usb_capture_dir, exist_ok=True)

    cutoff = datetime.now() - timedelta(days=days)
    synced = 0
    errors = 0

    if os.path.isdir(capture_dir):
        for fname in sorted(os.listdir(capture_dir)):
            src = os.path.join(capture_dir, fname)
            if not os.path.isfile(src):
                continue
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(src))
                if mtime < cutoff:
                    continue
                dst = os.path.join(usb_capture_dir, fname)
                if os.path.exists(dst) and os.path.getsize(src) == os.path.getsize(dst):
                    continue
                shutil.copy2(src, dst)
                synced += 1
            except Exception as e:
                logger.error(f"Captures-Sync Fehler {fname}: {e}")
                errors += 1

    msg = f"{synced} Capture-Dateien synchronisiert (letzte {days} Tage)"
    if errors:
        msg += f", {errors} Fehler"
    logger.info(msg)
    return True, msg, synced
```

**1c — `_auto_sync_loop()` erweitern**: nach `ok, msg, count = sync_pdfs_to_usb()` und vor `last_sync_time = time.time()` einfügen:
```python
                    try:
                        sync_captures_to_usb()
                    except Exception as e:
                        logger.error(f"Captures Auto-Sync Fehler: {e}")
```

**Aktionen:**
- Python-Patch-Skript per SSH auf Pi ausführen
- Verifizieren: `grep -n 'USB_CAPTURE_SUBDIR\|sync_captures_to_usb' /home/docucontrol/docupi/storage_manager.py`

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/storage_manager.py`

---

### Schritt 2: `app.py` — `GET /api/storage/captures/usb` hinzufügen

Endpunkt direkt nach `@app.route("/api/storage/sync/captures", ...)` einfügen.

Der Endpunkt listet `.txt`-Dateien aus `USB_CAPTURE_SUBDIR` auf dem USB-Stick:

```python
@app.route("/api/storage/captures/usb")
def api_storage_captures_usb():
    import os as _os
    from datetime import datetime as _dt
    from storage_manager import get_usb_info, USB_MOUNT_POINT, USB_CAPTURE_SUBDIR
    usb = get_usb_info()
    if not usb.get("mounted"):
        return jsonify({"files": [], "error": "USB nicht gemountet"})
    base = _os.path.join(USB_MOUNT_POINT, USB_CAPTURE_SUBDIR)
    files = []
    if _os.path.isdir(base):
        for fname in sorted(_os.listdir(base)):
            if not fname.lower().endswith(".txt"):
                continue
            fp = _os.path.join(base, fname)
            try:
                stat = _os.stat(fp)
                sz = stat.st_size
                sh = str(round(sz/1024, 1)) + " KB" if sz < 1048576 else str(round(sz/1048576, 1)) + " MB"
                # Prüfe ob passendes .bin existiert
                bin_path = _os.path.join(base, fname.replace(".txt", ".bin"))
                has_bin = _os.path.exists(bin_path)
                files.append({
                    "name": fname,
                    "path": fname,
                    "size": sz,
                    "size_human": sh,
                    "has_bin": has_bin,
                    "modified": _dt.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M")
                })
            except Exception:
                pass
    return jsonify({"files": files})
```

**Aktionen:**
- Endpunkt per SSH-Python-Patch in `app.py` einfügen
- Verifizieren: `curl http://localhost:5000/api/storage/captures/usb` (auch wenn keine Dateien da — sollte `{"files": []}` zurückgeben, nicht 404)

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/app.py`

---

### Schritt 3: `filemanager.html` — Globaler Mode-Toggle

Dies ist die größte Änderung. Der lokale Dropdown wird ersetzt durch einen globalen Toggle, der beide Panes gleichzeitig steuert.

**3a — Globaler Toggle im Header** (oberhalb beider Panes):

Der aktuelle Header-Bereich (oberhalb der `.dual-pane`-Tabellen) bekommt einen Toggle. Aktueller Code suchen:
```html
<!-- oberhalb der split-view/dual-pane div -->
```

Neuer Toggle-Block (vor `.dual-pane`):
```html
<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
  <span style="font-size:0.85rem;color:var(--text-muted)">Ansicht:</span>
  <div style="display:flex;border:1px solid var(--border);border-radius:8px;overflow:hidden">
    <button id="btnModePdf" onclick="switchMode('pdf')"
      style="padding:5px 16px;font-size:0.85rem;border:none;cursor:pointer;background:var(--accent);color:#fff">
      PDF-Protokolle
    </button>
    <button id="btnModeCaptures" onclick="switchMode('captures')"
      style="padding:5px 16px;font-size:0.85rem;border:none;cursor:pointer;background:var(--surface);color:var(--text)">
      Rohdaten
    </button>
  </div>
  <span id="modeHint" style="font-size:0.8rem;color:var(--text-muted)">interne PDFs ↔ USB-PDFs</span>
</div>
```

**3b — Linken Dropdown entfernen**: `<select id="intModeSelect" ...>` inklusive umgebendem Container entfernen.

**3c — Rechte Pane Header-Titel dynamisch**: Statt statisch "USB-Stick" je nach Modus "USB / PDF" oder "USB / Rohdaten" anzeigen. Kleines Update in `renderUsbPane()` oder direkt im HTML `<span id="usbPaneTitle">`.

**3d — `switchMode(mode)` Funktion** (ersetzt `switchIntMode`):
```javascript
function switchMode(mode) {
    intMode = mode;
    // Toggle-Buttons stylen
    document.getElementById('btnModePdf').style.background = mode === 'pdf' ? 'var(--accent)' : 'var(--surface)';
    document.getElementById('btnModePdf').style.color = mode === 'pdf' ? '#fff' : 'var(--text)';
    document.getElementById('btnModeCaptures').style.background = mode === 'captures' ? 'var(--accent)' : 'var(--surface)';
    document.getElementById('btnModeCaptures').style.color = mode === 'captures' ? '#fff' : 'var(--text)';
    // Hint-Text
    document.getElementById('modeHint').textContent = mode === 'pdf' ? 'interne PDFs ↔ USB-PDFs' : 'interne Captures ↔ USB-Captures';
    // USB-Pane Titel
    var usbTitle = document.getElementById('usbPaneTitle');
    if (usbTitle) usbTitle.textContent = mode === 'pdf' ? 'USB-Stick / PDFs' : 'USB-Stick / Rohdaten';
    // Sync-Button Label
    var syncBtn = document.getElementById('btnBulkSyncUsb');
    if (syncBtn) syncBtn.textContent = mode === 'pdf' ? 'Auf USB kopieren' : 'Auf USB kopieren';
    // Selektion leeren
    selectedInt.clear(); selectedUsb.clear();
    updateBulkBarInt(); updateBulkBarUsb();
    // Beide Panes neu laden
    loadInternalFiles();
    loadUsbFiles();
}
```

**3e — `loadUsbFiles()` anpassen**: Je nach `intMode` unterschiedlichen Endpunkt aufrufen:
```javascript
function loadUsbFiles() {
    fetch('/api/storage/stats')
        .then(r => r.json())
        .then(d => {
            var connected = !!(d.usb && d.usb.connected);
            usbConnected = connected;
            // Sync-Button
            var syncBtn = document.getElementById('btnBulkCopyUsb');
            if (syncBtn) syncBtn.disabled = !connected;

            if (!connected) {
                // USB nicht verbunden
                document.getElementById('usbFilesTbody').innerHTML =
                    '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:20px">Kein USB-Stick verbunden</td></tr>';
                return;
            }
            // Richtigen Endpunkt je nach Modus
            var endpoint = intMode === 'captures' ? '/api/storage/captures/usb' : '/api/storage/pdfs/usb';
            fetch(endpoint)
                .then(r => r.json())
                .then(data => {
                    var files = data.files || [];
                    var tbody = document.getElementById('usbFilesTbody');
                    if (!files.length) {
                        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:20px">' +
                            (intMode === 'captures' ? 'Keine Captures auf USB' : 'Keine PDFs auf USB') + '</td></tr>';
                        return;
                    }
                    tbody.innerHTML = files.map(f => renderUsbFileRow(f)).join('');
                })
                .catch(() => {
                    document.getElementById('usbFilesTbody').innerHTML =
                        '<tr><td colspan="5" style="text-align:center;color:var(--error);padding:20px">Fehler beim Laden</td></tr>';
                });
        });
}
```

**3f — `renderUsbFileRow()` anpassen**: Bei Captures-Modus Dateiname ohne Download-Link anzeigen (wie interne Captures-Ansicht); `has_bin`-Flag als Badge `+bin` anzeigen:
```javascript
function renderUsbFileRow(f) {
    var fn = f.name || '';
    var fp = f.path || fn;
    var checked = selectedUsb.has(fp) ? 'checked' : '';
    var label = fn;
    if (intMode === 'captures' && f.has_bin) label += ' <span style="font-size:0.75rem;color:var(--text-muted)">[+bin]</span>';
    return '<tr class="file-row">' +
        '<td><input type="checkbox" class="row-sel" value="' + _esc(fp) + '" ' + checked + ' onchange="toggleSelUsb(this)"></td>' +
        '<td>' + label + '</td>' +
        '<td>' + (f.modified || '') + '</td>' +
        '<td>' + (f.size_human || '') + '</td>' +
        '<td><button class="btn btn-sm btn-danger" onclick="delUsbFile(' + JSON.stringify(fp) + ')">Löschen</button></td>' +
        '</tr>';
}
```

**3g — `bulkDeleteUsb()` anpassen**: USB-Captures löschen ist noch nicht implementiert — fürs erste kein Löschen von USB-Captures (Button disabled oder Fehlermeldung). Alternativ: DELETE-Endpunkt für USB-Captures ergänzen (einfach, da flaches Verzeichnis).

Einfachste Lösung: Beim Löschen im Captures-Modus eine Fehlermeldung zeigen ("Löschen von USB-Captures nicht unterstützt").

**3h — `bulkCopyUsb()` im Captures-Modus**: Bereits implementiert (`POST /api/tcp_capture/captures/bulk-copy-usb`). Kein Änderungsbedarf.

**Aktionen:**
- Aktuelles `filemanager.html` vom Pi lesen (komplette Datei)
- Alle Änderungen präzise anwenden
- Neue Version auf Pi deployen

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/templates/filemanager.html`

---

### Schritt 4: Service neu starten und verifizieren

**Aktionen:**
- `sudo systemctl restart docucontrol.service`
- `systemctl is-active docucontrol.service`
- `curl http://localhost:5000/api/storage/captures/usb` → `{"files": [...]}`
- `grep -n 'USB_CAPTURE_SUBDIR\|sync_captures_to_usb' /home/docucontrol/docupi/storage_manager.py`
- Browser: `http://192.168.0.171/files` → Toggle-Buttons "PDF-Protokolle" / "Rohdaten" erscheinen; Klick auf "Rohdaten" → beide Panes zeigen Captures

**Betroffene Dateien:**
- Pi: systemd-Service

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- `app.py`: importiert `USB_PDF_SUBDIR` aus `storage_manager` — neue `USB_CAPTURE_SUBDIR` Konstante muss dort auch importiert werden
- `filemanager.html`: `switchIntMode()` wird durch `switchMode()` ersetzt — alter Funktionsname sollte entfernt werden um Konfusion zu vermeiden

### Nötige Updates für Konsistenz

- `CLAUDE.md`: neuen API-Endpunkt `GET /api/storage/captures/usb` dokumentieren; Auto-Sync beschreibt jetzt auch Captures
- `context/strategy.md`: keine Änderung nötig

### Auswirkungen auf bestehende Workflows

- Auto-Sync beim USB-Einstecken: bisher nur PDFs → jetzt auch Captures. Sync-Dauer erhöht sich minimal (Captures sind kleiner als PDFs).
- Manueller Sync-Button: Verhalten unverändert (Endpunkt wechselt je nach Modus).
- Bulk-Aktionen in der linken Pane: unverändert.

---

## Validierungs-Checkliste

- [ ] `grep 'USB_CAPTURE_SUBDIR\|sync_captures_to_usb' storage_manager.py` → beide vorhanden
- [ ] `_auto_sync_loop()` enthält `sync_captures_to_usb()` Aufruf
- [ ] `curl http://localhost:5000/api/storage/captures/usb` → 200, `{"files": [...]}`
- [ ] Browser `/files` → globaler Toggle "PDF-Protokolle" / "Rohdaten" sichtbar (kein Dropdown mehr links)
- [ ] Klick "Rohdaten" → beide Panes zeigen Captures (links intern, rechts USB wenn verbunden)
- [ ] Klick "PDF-Protokolle" → beide Panes zeigen PDFs (Zustand wie vorher)
- [ ] USB-Pane-Titel ändert sich je nach Modus
- [ ] Hint-Text unter Toggle ändert sich je nach Modus
- [ ] Service nach Restart `active`

---

## Erfolgskriterien

1. Globaler Toggle im Datei-Manager schaltet beide Panes gleichzeitig um — ein Klick, beide Seiten reagieren
2. Im Rohdaten-Modus lädt die rechte Pane Captures vom USB-Stick (oder zeigt "Keine Captures auf USB" wenn leer)
3. Auto-Sync synchronisiert beim USB-Einstecken und im 15-min-Intervall sowohl PDFs als auch Captures

---

## Notizen

- USB-Captures-Pfad `docucontrol/captures/` ist bereits von `POST /api/storage/sync/captures` (manuellem Sync) festgelegt — neue `sync_captures_to_usb()` schreibt in denselben Pfad.
- `USB_CAPTURE_SUBDIR` sollte auch in `app.py` aus `storage_manager` importiert werden (in `api_storage_sync_captures` ist der Pfad aktuell hardcodiert als `"docucontrol", "captures"` — nach dem Refactor über die Konstante lösen).
- Delete von USB-Captures: Für v1 reicht eine Fehlermeldung ("nicht unterstützt"). Echtes Delete braucht einen neuen Endpunkt `/api/storage/captures/usb/<fname>` DELETE — kann als separater Schritt später folgen.
- `.bin`-Dateien werden auf USB synchronisiert aber im Listing nicht als eigene Zeile gezeigt, nur als `[+bin]`-Badge zur `.txt`-Zeile — cleaner UI.

---

## Implementierungsnotizen

**Implementiert:** 2026-06-10

### Zusammenfassung

- `storage_manager.py`: `USB_CAPTURE_SUBDIR = "docucontrol/captures"` Konstante hinzugefügt; `sync_captures_to_usb()` Funktion implementiert; `_auto_sync_loop()` ruft jetzt nach `sync_pdfs_to_usb()` auch `sync_captures_to_usb()` auf
- `app.py`: `GET /api/storage/captures/usb` Endpunkt hinzugefügt (listet `.txt`-Captures vom USB-Stick mit `has_bin`-Flag); `api_storage_delete()` unterstützt jetzt `pane='usb_captures'` (Base = `docucontrol/captures/` auf USB)
- `filemanager.html`: Lokaler `intModeSelect`-Dropdown entfernt; globaler Toggle-Button-Pair ("PDF-Protokolle" / "Rohdaten") oberhalb beider Panes; `switchMode()` steuert beide Panes; `loadUsbFiles()` ruft je nach Modus `pdfs/usb` oder `captures/usb` auf; `renderUsbFileRow()` zeigt Captures mit Text-Icon und `[+bin]`-Badge; `delUsbFile()` und `bulkDeleteUsb()` übergeben `pane='usb_captures'` im Captures-Modus

### Abweichungen vom Plan

Keine inhaltlichen Abweichungen. Zusätzlich implementiert: `pane='usb_captures'` in `api_storage_delete()` für sofortiges Löschen von USB-Captures (Plan hatte Fehlermeldung als Fallback vorgesehen, echte Unterstützung ist besser).

### Aufgetretene Probleme

Keine. Verifikation: `GET /api/storage/captures/usb` → 200, 29 Captures gelistet (USB war bereits verbunden mit vorhandenen Captures).
