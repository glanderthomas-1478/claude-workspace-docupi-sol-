# Plan: Dateimanager — Mode-Toggle wiederherstellen + Dateinamen-Reihenfolge + Maschinennummer

**Erstellt:** 2026-06-11
**Status:** Implementiert
**Anforderung:** (1) Maschinennummer als konfigurierbares Feld in Settings hinzufügen und in den PDF-Dateinamen hinter der Charge-Nr. aufnehmen. (2) PDF-Dateinamen umordnen: Charge-Nr. direkt hinter Datum+Zeit. (3) Den durch die Skalierbarkeits-Implementierung überschriebenen PDF/Rohdaten-Mode-Toggle in filemanager.html wiederherstellen.

---

## Überblick

### Was dieser Plan erreicht

PDF-Dateinamen folgen ab sofort dem Muster `DATUM_ZEIT_CHxxxxxx_MASCHINENNRxxx_Gerätename.pdf`. Charge-Nr. und Maschinennummer sind direkt am Anfang des Namens sichtbar, auch wenn der Name in der Tabelle abgeschnitten wird. Die Maschinennummer wird einmalig in den Einstellungen unter der Anlage-Karte konfiguriert und persistent in `config.json` gespeichert. Zusätzlich wird der `.segmented`-Toggle „PDF-Protokolle / Rohdaten" in der Dateien-Seite wiederhergestellt.

### Warum das wichtig ist

Im Feld und auf ausgedruckten PDFs muss die Maschinennummer (Seriennummer der Sterilisations-Anlage) auf dem Protokoll erscheinen — sie ist das primäre Identifikationsmerkmal für Audits. Bisher fehlte sie im Dateinamen komplett. Der Mode-Toggle ist für den Datensammlermodus essenziell: ohne ihn ist kein Zugriff auf Raw-Captures über die UI möglich.

---

## Aktueller Zustand

### Relevante bestehende Struktur

| Datei / Ort | Zustand |
|---|---|
| Pi: `pdf_generator.py` `build_filename()` | Pattern `{datum}_{zeit}_{geraet}_{charge}` aus `config.json` — kein `{masch_nr}` Placeholder, Charge zuletzt |
| Pi: `config.json` `pdf.filename_pattern` | `"{datum}_{zeit}_{geraet}_{charge}"` (zu ändern) |
| Pi: `config.json` `machine`-Sektion | Hat `name`, `ip`, `protocol` — kein `machine_nr`-Feld |
| Pi: `app.py` `GET/POST /api/machine/config` | Liest/schreibt `name`, `ip` — kein `machine_nr` |
| `src/docucontrol/templates/settings.html` | Settings-Card "Anlage": Felder Maschinenname + IP + Ping-Button — kein Maschinennummer-Feld |
| Pi: `templates/filemanager.html` | Aktuelle Version (nach Skalierbarkeits-Update): hat Paginierung, hat KEINEN Mode-Toggle |
| Workspace: `src/docucontrol/templates/filemanager.html` | Identisch zur Pi-Version (im Skalierbarkeits-Update deployed) |
| Pi: `app.py` | Hat `DELETE /api/tcp_capture/captures/<fname>` + `POST /api/storage/sync/captures` + `GET /api/storage/captures/usb` — alle noch aktiv |
| `src/docucontrol/static/docucontrol.css` | Hat `.segmented`-Klasse, kein CSS-Änderungsbedarf |

### Lücken oder Probleme, die adressiert werden

1. **Maschinennummer fehlt komplett:** Kein konfigurierbares Feld in Settings, kein `machine_nr` in `config.json`, kein `{masch_nr}` Placeholder in `pdf_generator.py`.
2. **Charge-Nr. abgeschnitten:** `Belimed_PST_14-8-12_HS1` ist 24 Zeichen lang — der Gerätename verdrängt Charge-Nr. ans Ende des Dateinamens.
3. **Mode-Toggle fehlt:** Das Skalierbarkeits-Update hat `filemanager.html` auf Basis einer älteren Version gebaut, die den Toggle noch nicht hatte.
4. **Paginierung soll erhalten bleiben:** Die in diesem Sprint eingeführte Paginierung (50/Seite, Mini-Pager) muss nach der Wiederherstellung aktiv bleiben.

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

- `config.json` auf Pi: `machine.machine_nr` Feld hinzufügen + `pdf.filename_pattern` auf `{datum}_{zeit}_{charge}_{masch_nr}_{geraet}` setzen
- Pi `pdf_generator.py`: `build_filename()` um `{masch_nr}` Substitution erweitern; leeres `masch_nr` → doppelte Unterstriche bereinigen
- Pi `app.py`: `GET /api/machine/config` gibt `machine_nr` zurück; `POST /api/machine/config` speichert `machine_nr` in config.json
- `settings.html`: Input-Feld "Maschinennummer" in der Anlage-Card ergänzen (zwischen Maschinenname und IP oder danach)
- `filemanager.html`: `.segmented`-Toggle-Buttons + alle JS-Funktionen für Captures-Modus wiederherstellen

### Neue Dateien erstellen

Keine.

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|---|---|
| Pi: `/home/docucontrol/docupi/config.json` | `machine.machine_nr` + `pdf.filename_pattern` aktualisieren |
| Pi: `/home/docucontrol/docupi/pdf_generator.py` | `build_filename()`: `{masch_nr}` Substitution + Doppelunterstrich-Bereinigung |
| Pi: `/home/docucontrol/docupi/app.py` | `/api/machine/config` GET+POST: `machine_nr` Feld |
| `src/docucontrol/templates/settings.html` | Maschinennummer-Input in Anlage-Card |
| `src/docucontrol/templates/filemanager.html` | Mode-Toggle HTML + alle JS-Funktionen |

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **`{masch_nr}` als Rohdaten-Wert:** Der User tippt die Maschinennummer as-is in das Settings-Feld (z.B. `27163` oder `NR27163`). Keine automatische Präfix-Logik — maximale Flexibilität. Leerzeichen werden durch `_` ersetzt.
2. **Leerfeld-Handling:** Ist `machine_nr` leer/nicht gesetzt, wird `{masch_nr}` durch leeren String ersetzt und entstehende Doppelunterstriche (`__`) im Dateinamen durch einfachen `_` bereinigt. Kein Hard-Fail bei fehlendem Feld.
3. **Code-Deploy für pdf_generator.py nötig:** Anders als bei reiner config.json-Änderung muss `build_filename()` den neuen Placeholder kennen. Deploy via SSH-Patch-Script (liest Datei auf Pi, patcht, schreibt zurück).
4. **API-Erweiterung minimal:** Nur `machine_nr` als neues Feld in `/api/machine/config` GET+POST — alle anderen Felder unverändert.
5. **settings.html in Workspace + Deploy:** `settings.html` liegt im Workspace; nach Änderung via `scp` deployen wie alle anderen Templates.
6. **Paginierung nur im PDF-Modus aktiv:** `loadInternalFiles(page)` mit Pager bleibt für PDF. Im Captures-Modus läuft `loadCaptureFiles()` ohne Paginierung.
7. **Auto-Refresh modusabhängig:** `setInterval` prüft `intMode` — lädt entweder `loadInternalFiles(intPage)` oder `loadCaptureFiles()`.

### Betrachtete Alternativen

- **Maschinennummer automatisch aus Protokoll extrahieren:** Protokoll enthält sie evtl. als Feld. Zu aufwändig zu implementieren und fehleranfällig — einmalige manuelle Konfiguration ist robuster.
- **Maschinennummer als festes Präfix (z.B. immer "MNR"):** Schränkt User ein. Raw-String-Ansatz ist flexibler.
- **Default-Wert in build_filename() statt config.json:** Würde Code-Deploy für Pattern-Änderung erfordern. Config-Änderung ist sauberer.

### Offene Fragen

Keine.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: config.json auf Pi — machine_nr + filename_pattern setzen

**Aktionen:**

```bash
ssh -i ~/.ssh/id_ed25519 docucontrol@192.168.0.171 python3 - << 'EOF'
import json
path = '/home/docucontrol/docupi/config.json'
with open(path) as f: c = json.load(f)
print('Vorher pattern:', c['pdf'].get('filename_pattern'))
print('Vorher machine_nr:', c.get('machine', {}).get('machine_nr', '<fehlt>'))
c.setdefault('machine', {})['machine_nr'] = ''
c['pdf']['filename_pattern'] = '{datum}_{zeit}_{charge}_{masch_nr}_{geraet}'
with open(path, 'w') as f: json.dump(c, f, indent=2, ensure_ascii=False)
print('Nachher pattern:', c['pdf']['filename_pattern'])
print('Nachher machine_nr:', c['machine']['machine_nr'])
EOF
```

Kein Service-Restart nötig — `config.json` wird bei jedem PDF-Job frisch geladen.

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/config.json`

---

### Schritt 2: pdf_generator.py auf Pi — {masch_nr} in build_filename() patchen

`build_filename()` kennt bisher nur `{datum}`, `{zeit}`, `{geraet}`, `{charge}`. Wir fügen `{masch_nr}` hinzu.

**Vorgehensweise:**
1. `build_filename()` auf Pi lesen (`ssh ... grep -n 'build_filename\|filename_pattern\|\.format(' pdf_generator.py`)
2. Exakte Zeilen identifizieren, an denen die Substitutions-Variablen gebaut werden
3. `masch_nr`-Variable ergänzen + Doppelunterstrich-Bereinigung nach `format()`

**Patch-Logik** (als Python-Script via SSH ausführen):

```python
import re

path = '/home/docucontrol/docupi/pdf_generator.py'
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

# Stelle 1: masch_nr-Variable vor dem format()-Aufruf einfügen
# Suche die Zeile, die "charge" für den Dateinamen baut (z.B. charge = f'CH{...}')
# Direkt danach masch_nr einfügen

# Suche das .format() oder pattern.format() in build_filename()
# und füge masch_nr=masch_nr als weiteres Argument hinzu

# Beispiel für typische Struktur (exakter Code muss beim Implement gelesen werden):
# VORHER:
#   charge = f'CH{charge_nr:06d}'
#   filename = pattern.format(datum=datum, zeit=zeit, geraet=geraet, charge=charge)
# NACHHER:
#   charge = f'CH{charge_nr:06d}'
#   masch_nr = (config.get('machine', {}).get('machine_nr', '') or '').strip().replace(' ', '_')
#   filename = pattern.format(datum=datum, zeit=zeit, geraet=geraet, charge=charge, masch_nr=masch_nr)
#   filename = re.sub(r'_{2,}', '_', filename)  # leeres masch_nr bereinigen

# WICHTIG: Die exakten Zeilen beim Implement zuerst lesen (grep), dann gezielt patchen
```

**Hinweis für den Implementer:** Die genaue Zeilenstruktur in `build_filename()` zuerst via SSH lesen:
```bash
ssh -i ~/.ssh/id_ed25519 docucontrol@192.168.0.171 \
  "grep -n 'filename_pattern\|\.format\|charge\s*=\|datum\s*=\|zeit\s*=' /home/docucontrol/docupi/pdf_generator.py | head -30"
```
Dann mit gezieltem `sed` oder Python-Script patchen. Sicherstellen, dass `import re` am Dateianfang vorhanden ist (wenn nicht, einfügen).

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/pdf_generator.py`

---

### Schritt 3: app.py auf Pi — /api/machine/config um machine_nr erweitern

**GET `/api/machine/config`:** `machine_nr` zum Response-Dict hinzufügen.
**POST `/api/machine/config`:** `machine_nr` aus Request-Body lesen und in `config.json` speichern.

**Aktuellen Code lesen:**
```bash
ssh -i ~/.ssh/id_ed25519 docucontrol@192.168.0.171 \
  "grep -n 'machine/config\|machine_nr\|machine.*name\|machine.*ip' /home/docucontrol/docupi/app.py | head -30"
```

**Patch-Logik (als Script auf Pi ausführen):**

GET-Route — `machine_nr` im Response ergänzen (typische Struktur):
```python
# VORHER (ungefähr):
return jsonify({'name': c.get('machine',{}).get('name',''), 'ip': c.get('machine',{}).get('ip',''), ...})

# NACHHER:
return jsonify({
    'name': c.get('machine',{}).get('name',''),
    'machine_nr': c.get('machine',{}).get('machine_nr',''),
    'ip': c.get('machine',{}).get('ip',''),
    ...
})
```

POST-Route — `machine_nr` speichern:
```python
# VORHER (ungefähr):
c.setdefault('machine', {})['name'] = data.get('name', '')
c.setdefault('machine', {})['ip'] = data.get('ip', '')

# NACHHER:
c.setdefault('machine', {})['name'] = data.get('name', '')
c.setdefault('machine', {})['machine_nr'] = data.get('machine_nr', '')
c.setdefault('machine', {})['ip'] = data.get('ip', '')
```

**Kein Service-Restart nötig** wenn `/api/machine/config` per PATCH-Script live ersetzt wird (Flask lädt Routes nicht nach — **doch:** Service-Restart ist nötig, da app.py neu geladen werden muss). Nach dem Patch:
```bash
ssh -i ~/.ssh/id_ed25519 docucontrol@192.168.0.171 "sudo systemctl restart docucontrol.service"
```

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/app.py`

---

### Schritt 4: settings.html — Maschinennummer-Input in Anlage-Card

Die bestehende Anlage-Card in `settings.html` hat die Felder: `#machineNameInput` (Maschinenname) und `#machineIpInput` (IP-Adresse). Wir fügen `#machineNrInput` (Maschinennummer) hinzu — zwischen Maschinenname und IP ist sinnvoll.

**HTML-Ergänzung** direkt nach dem Maschinenname-Feld einfügen:
```html
<div class="form-group">
    <label class="form-label" for="machineNrInput">Maschinennummer</label>
    <input type="text" class="form-control" id="machineNrInput"
           placeholder="z.B. 27163 oder NR27163">
</div>
```

**JS: `loadMachineConfig()` erweitern** — `machine_nr` aus API-Response in das Feld setzen:
```javascript
// Vorher (ungefähr):
document.getElementById('machineNameInput').value = d.name || '';
document.getElementById('machineIpInput').value = d.ip || '';

// Nachher:
document.getElementById('machineNameInput').value = d.name || '';
document.getElementById('machineNrInput').value = d.machine_nr || '';
document.getElementById('machineIpInput').value = d.ip || '';
```

**JS: `saveMachineConfig()` erweitern** — `machine_nr` mit senden:
```javascript
// Vorher (ungefähr):
fetch('/api/machine/config', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ name: ..., ip: ... })
})

// Nachher:
fetch('/api/machine/config', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        name: document.getElementById('machineNameInput').value.trim(),
        machine_nr: document.getElementById('machineNrInput').value.trim(),
        ip: document.getElementById('machineIpInput').value.trim()
    })
})
```

**Hinweis für Implementer:** `settings.html` zuerst lokal lesen und die genauen Funktionsnamen + Strukturen prüfen, da `loadMachineConfig()` und `saveMachineConfig()` möglicherweise anders benannt sind. Dann gezielt editieren.

**Betroffene Dateien:**
- `src/docucontrol/templates/settings.html`

---

### Schritt 5: filemanager.html — Mode-Toggle HTML einfügen

Direkt vor der `<div class="two-col">` den Toggle-Block einfügen:

```html
<div style="margin-bottom:14px;display:flex;align-items:center;gap:14px">
    <div class="segmented" id="modeToggle">
        <button id="btnModePdf" class="active" onclick="switchMode('pdf')">
            <i class="bi bi-file-earmark-pdf"></i> PDF-Protokolle
        </button>
        <button id="btnModeCaptures" onclick="switchMode('captures')">
            <i class="bi bi-file-earmark-text"></i> Rohdaten
        </button>
    </div>
</div>
```

**Betroffene Dateien:**
- `src/docucontrol/templates/filemanager.html`

---

### Schritt 6: filemanager.html — JS: `intMode`-Variable und `switchMode()` einfügen

Direkt nach der `var intPage = 1;`-Zeile einfügen:

```javascript
var intMode = 'pdf';

function switchMode(mode) {
    intMode = mode;
    document.getElementById('btnModePdf').classList.toggle('active', mode === 'pdf');
    document.getElementById('btnModeCaptures').classList.toggle('active', mode === 'captures');
    if (mode === 'pdf') {
        loadInternalFiles(intPage);
    } else {
        loadCaptureFiles();
    }
    loadUsbFiles();
}
```

**Betroffene Dateien:**
- `src/docucontrol/templates/filemanager.html`

---

### Schritt 7: filemanager.html — JS: Captures-Ladefunktionen einfügen

Nach der `renderIntPager`-Funktion (vor `loadInternalFiles`) einfügen:

```javascript
function parseCaptureTimestamp(fname) {
    try {
        return fname.substring(6,8) + '.' + fname.substring(4,6) + '.' + fname.substring(0,4)
               + ' ' + fname.substring(9,11) + ':' + fname.substring(11,13);
    } catch(e) { return fname; }
}

function loadCaptureFiles() {
    fetch('/api/tcp_capture/captures')
        .then(function(r) { return r.json(); })
        .then(function(files) {
            var txts = (files || []).filter(function(f) { return (f.name || '').endsWith('.txt'); })
                                   .sort(function(a, b) { return b.name.localeCompare(a.name); });
            var bins = {};
            (files || []).filter(function(f) { return (f.name || '').endsWith('.bin'); })
                         .forEach(function(f) { bins[f.name.replace('.bin', '')] = f.size; });
            var body = document.getElementById('intFileBody');
            var countEl = document.getElementById('intCountInfo');
            document.getElementById('intPager').innerHTML = '';
            if (txts.length === 0) {
                body.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:20px;color:var(--muted)"><i class="bi bi-inbox"></i> Keine Captures gespeichert</td></tr>';
                countEl.textContent = '';
                return;
            }
            body.innerHTML = txts.map(function(f) { return renderCaptureRow(f, bins); }).join('');
            countEl.textContent = txts.length + ' Captures';
        }).catch(function() {
            document.getElementById('intFileBody').innerHTML =
                '<tr><td colspan="4" style="text-align:center;padding:20px;color:var(--danger)">Fehler beim Laden</td></tr>';
        });
}
```

`renderCaptureRow` — beim Implementieren direkt in die Datei schreiben (nicht als Markdown-String, um Escape-Probleme zu vermeiden):
```javascript
function renderCaptureRow(f, bins) {
    var base = f.name.replace('.txt', '');
    var hasBin = Object.prototype.hasOwnProperty.call(bins, base);
    var ts = parseCaptureTimestamp(f.name);
    var size = formatBytes(f.size);
    var binBtn = hasBin
        ? '<a class="icon-btn" title=".bin laden" href="/api/tcp_capture/captures/' + encodeURIComponent(base + '.bin') + '" download="' + escHtml(base + '.bin') + '"><i class="bi bi-file-earmark-code"></i></a>'
        : '';
    return '<tr>'
        + '<td style="max-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
        +   '<div class="fn" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
        +   '<i class="bi bi-file-earmark-text" style="color:var(--accent)"></i> ' + escHtml(base)
        +   (hasBin ? ' <span style="font-size:0.75rem;color:var(--muted)">[+bin]</span>' : '')
        +   '</div></td>'
        + '<td class="muted" style="white-space:nowrap">' + escHtml(ts) + '</td>'
        + '<td class="muted">' + escHtml(size) + '</td>'
        + '<td class="right"><div class="act">'
        + '<a class="icon-btn" title=".txt laden" href="/api/tcp_capture/captures/' + encodeURIComponent(f.name) + '" download="' + escHtml(f.name) + '"><i class="bi bi-download"></i></a>'
        + binBtn
        + '<button class="icon-btn danger" title="Löschen" onclick="delCapture(\'' + escHtml(base) + '\')"><i class="bi bi-trash"></i></button>'
        + '</div></td>'
        + '</tr>';
}
```

**Betroffene Dateien:**
- `src/docucontrol/templates/filemanager.html`

---

### Schritt 8: filemanager.html — JS: `delCapture()` als globale Funktion einfügen

Nach `window.goIntPage` einfügen:

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

**Betroffene Dateien:**
- `src/docucontrol/templates/filemanager.html`

---

### Schritt 9: filemanager.html — `syncUsb()` modusabhängig machen

```javascript
window.syncUsb = function() {
    var btn = document.getElementById('btnSync');
    btn.disabled = true;
    var isCaptures = intMode === 'captures';
    btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> ' + (isCaptures ? 'Kopiere …' : 'Synchronisiere …');
    var endpoint = isCaptures ? '/api/storage/sync/captures' : '/api/storage/sync/now';
    fetch(endpoint, { method: 'POST' })
        .then(function(r) { return r.json(); })
        .then(function() {
            if (isCaptures) { loadCaptureFiles(); } else { loadInternalFiles(intPage); loadUsbFiles(); }
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> ' + (isCaptures ? 'Captures → USB' : 'Jetzt sync.');
        }).catch(function() {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> ' + (isCaptures ? 'Captures → USB' : 'Jetzt sync.');
        });
};
```

**Betroffene Dateien:**
- `src/docucontrol/templates/filemanager.html`

---

### Schritt 10: filemanager.html — `loadUsbFiles()` modusabhängig machen

Im `if (mounted)` Block den hardcodierten Endpunkt ersetzen:

```javascript
// Vorher:
if (mounted) {
    fetch('/api/storage/pdfs/usb')

// Nachher:
if (mounted) {
    var usbEndpoint = intMode === 'captures' ? '/api/storage/captures/usb' : '/api/storage/pdfs/usb';
    fetch(usbEndpoint)
```

Im gleichen Block die Leer-Meldung anpassen:
```javascript
// Vorher:
' Keine PDFs auf USB — Jetzt sync. starten'

// Nachher:
(intMode === 'captures' ? ' Keine Captures auf USB' : ' Keine PDFs auf USB — Jetzt sync. starten')
```

**Betroffene Dateien:**
- `src/docucontrol/templates/filemanager.html`

---

### Schritt 11: filemanager.html — Auto-Refresh modusabhängig machen

```javascript
// Vorher:
setInterval(function() { loadInternalFiles(intPage); loadUsbFiles(); }, 30000);

// Nachher:
setInterval(function() {
    if (intMode === 'captures') { loadCaptureFiles(); } else { loadInternalFiles(intPage); }
    loadUsbFiles();
}, 30000);
```

**Betroffene Dateien:**
- `src/docucontrol/templates/filemanager.html`

---

### Schritt 12: settings.html und filemanager.html deployen + Service neustarten

```bash
scp -i ~/.ssh/id_ed25519 \
  src/docucontrol/templates/settings.html \
  src/docucontrol/templates/filemanager.html \
  docucontrol@192.168.0.171:/home/docucontrol/docupi/templates/

# Service neustarten (wegen app.py-Patch aus Schritt 3)
ssh -i ~/.ssh/id_ed25519 docucontrol@192.168.0.171 \
  "sudo systemctl restart docucontrol.service && sleep 3 && systemctl is-active docucontrol.service"
```

**Verifizierung:**
- `curl -s http://192.168.0.171/api/machine/config | python3 -m json.tool` → enthält `machine_nr`
- Settings `http://192.168.0.171/settings`: Anlage-Card hat Feld "Maschinennummer"; Wert `27163` eingeben, speichern
- Testprotokoll senden: `python3 scripts/send_test_charges.py --count 1 --start-charge 21731`
- Neues PDF: Name ist `2026-06-11_HHMMSS_CH021731_27163_Belimed_PST_14-8-12_HS1.pdf`
- Maschinennummer leer lassen, erneut testen → `2026-06-11_HHMMSS_CH021732_Belimed_PST_14-8-12_HS1.pdf` (kein doppelter Unterstrich)
- Browser `http://192.168.0.171/files`: Toggle sichtbar, "PDF-Protokolle" aktiv
- Klick "Rohdaten": Captures-Liste, kein Pager, Count "N Captures"
- Zurück "PDF-Protokolle": Paginierung wieder sichtbar

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- Pi: `app.py` — `/api/machine/config` erweitern (Schritt 3)
- Pi: `pdf_generator.py` — `build_filename()` patchen (Schritt 2)
- Pi: `config.json` — neue Felder (Schritt 1)
- Pi: bestehende API-Endpunkte für Captures/USB bereits vorhanden, kein Änderungsbedarf

### Nötige Updates für Konsistenz

- CLAUDE.md: API-Endpunkt `/api/machine/config` um `machine_nr`-Feld dokumentieren; Dateinamen-Format in "DocuControl Web-Interface" aktualisieren; neue API-Endpunkte-Liste anpassen

### Auswirkungen auf bestehende Workflows

- Bestehende PDFs: unberührt (alter Name bleibt)
- Neue PDFs: `DATUM_ZEIT_CHxxxxxx_MASCHINENNRxxx_Gerätename.pdf` wenn Maschinennummer konfiguriert, `DATUM_ZEIT_CHxxxxxx_Gerätename.pdf` wenn leer
- Settings: Anlage-Card hat ein zusätzliches Eingabefeld, Speichern-Button deckt alle drei Felder ab
- Paginierung: bleibt aktiv im PDF-Modus; Captures-Modus hat keinen Pager
- Datensammlermodus: Captures weiterhin über "Rohdaten"-Toggle erreichbar

---

## Validierungs-Checkliste

- [ ] config.json: `machine.machine_nr` = `""` (leerer Default), `pdf.filename_pattern` = `"{datum}_{zeit}_{charge}_{masch_nr}_{geraet}"`
- [ ] `/api/machine/config` GET: Response enthält `machine_nr`-Feld
- [ ] `/api/machine/config` POST: `machine_nr` wird in config.json gespeichert
- [ ] Settings Anlage-Card: Feld "Maschinennummer" sichtbar, Wert speicherbar
- [ ] Nach Speichern "27163": nächstes PDF heißt `DATUM_ZEIT_CH*_27163_Belimed_*.pdf`
- [ ] Nach Löschen der Maschinennummer: PDF-Name ohne doppelten Unterstrich (`CH*_Belimed_*`, nicht `CH*__Belimed_*`)
- [ ] Browser `/files`: `.segmented`-Toggle sichtbar oberhalb der two-col-Div
- [ ] "PDF-Protokolle"-Button: aktiv (blau), PDF-Liste mit Paginierung sichtbar
- [ ] "Rohdaten"-Button: Klick → Captures-Liste, kein Pager, Count "N Captures"
- [ ] Zurück "PDF-Protokolle": Pager wieder sichtbar, PDFs geladen
- [ ] delCapture: Capture gelöscht, Liste aktualisiert
- [ ] syncUsb PDF-Modus: Label "Jetzt sync.", ruft `/api/storage/sync/now`
- [ ] syncUsb Rohdaten-Modus: Label "Captures → USB", ruft `/api/storage/sync/captures`
- [ ] loadUsbFiles Captures-Modus: ruft `/api/storage/captures/usb`
- [ ] Auto-Refresh (30s): lädt korrekte Daten je nach Modus
- [ ] CLAUDE.md aktualisiert

---

## Erfolgskriterien

1. Settings-Card "Anlage" hat Feld "Maschinennummer"; Wert wird gespeichert und nach Reload korrekt vorgeladen
2. Neues PDF-Protokoll trägt Namen `YYYY-MM-DD_HHMMSS_CHxxxxxx_[MaschinNr_]Gerätename.pdf` — Charge-Nr. und Maschinennummer in der Tabellenspalte sichtbar ohne Scroll
3. Leere Maschinennummer: kein doppelter Unterstrich im Dateinamen
4. `.segmented`-Toggle auf der Dateien-Seite vorhanden; PDF-Modus mit Paginierung und Captures-Modus koexistieren ohne gegenseitige Störung

---

## Notizen

- **Warum der Toggle verloren ging:** Das Skalierbarkeits-Update hat `src/docucontrol/templates/filemanager.html` als Basis genommen — diese war noch nicht auf dem Stand der Deployments vom 2026-06-10/11. Künftig: vor Template-Änderungen Pi-Version als Referenz nehmen.
- **`renderCaptureRow` Escape-Logik:** `.bin`-Button als separate Variable `binBtn` vorbereiten, dann inline einsetzen — vermeidet verschachtelte Anführungszeichen.
- **config.json-Änderung wirkt sofort** für neue PDF-Jobs. app.py-Patch erfordert Service-Restart.
- **pdf_generator.py-Patch:** Zuerst grep auf Pi ausführen, exakte Struktur von `build_filename()` verstehen, dann minimal patchen. Nur zwei Zeilen müssen geändert werden.

---

## Implementierungsnotizen

**Implementiert:** 2026-06-11

### Zusammenfassung

- `config.json` auf Pi: `machine.machine_nr = ""` hinzugefügt, `pdf.filename_pattern` auf `{datum}_{zeit}_{charge}_{masch_nr}_{geraet}` geändert
- `pdf_generator.py`: `masch_nr`-Key in `tokens`-Dict eingefügt (Zeile 539); bestehende Doppelunterstrich-Bereinigung greift automatisch bei leerem Feld
- `app.py`: `GET /api/machine/config` gibt `machine_nr` zurück; `POST` speichert es in config.json
- `settings.html`: neues Set-Row "Maschinennummer" zwischen Maschinenname und IP; `loadMachineConfig()` + `saveMachineConfig()` erweitert
- `filemanager.html`: Mode-Toggle wiederhergestellt (`.segmented` HTML + `switchMode()`, `loadCaptureFiles()`, `renderCaptureRow()`, `parseCaptureTimestamp()`, `delCapture()`); `loadUsbFiles()` + `syncUsb()` + Auto-Refresh modusabhängig; Paginierung im PDF-Modus erhalten

### Verifikation

- CH021731 (machine_nr leer): `2026-06-11_175050_CH021731_Belimed_PST_14-8-12_HS1.pdf` ✓
- CH021732 (machine_nr=27163): `2026-06-11_175105_CH021732_27163_Belimed_PST_14-8-12_HS1.pdf` ✓
- Service nach Restart: `active` ✓
- API `/api/machine/config` GET: enthält `machine_nr` ✓

### Abweichungen vom Plan

- `config.json` liegt in `data/config.json`, nicht in `docupi/config.json` — Pfad angepasst

### Aufgetretene Probleme

- Erster SSH-Patch-Versuch schlug fehl wegen falschem config.json-Pfad (`/home/docucontrol/docupi/config.json` statt `/home/docucontrol/docupi/data/config.json`) — durch `find`-Befehl ermittelt und korrigiert
