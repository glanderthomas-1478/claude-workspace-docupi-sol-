# Plan: Dateimanager-Tabelle — Charge-Nr. und Programm statt Dateiname

**Erstellt:** 2026-06-11
**Status:** Entwurf
**Anforderung:** Dateimanager-Tabellen umstrukturieren: statt abgeschnittenem Dateinamen die Felder Charge-Nr., Datum, Programm, Größe zeigen — analog zum Dashboard

---

## Überblick

### Was dieser Plan erreicht

Die interne und USB-Dateitabelle zeigen aktuell den rohen Dateinamen (`2026-06-11_124807_Belimed_PST_14-8-12_HS1_CH021730.pdf`), der immer an der Chargennummer abgeschnitten wird. Nach der Änderung zeigen beide Tabellen strukturierte Spalten: **Charge-Nr. | Datum | Programm | Größe | Aktionen** — identisches Layout zum Dashboard, alle relevanten Felder sichtbar ohne horizontales Scrollen.

### Warum das wichtig ist

Die Dateiseite ist die primäre Verwaltungsansicht für den Techniker vor Ort. Wenn man ein Protokoll sucht oder löscht, identifiziert man es über Charge-Nr. und Datum — nicht über den internen Dateinamen. Die aktuelle Darstellung erzwingt einen Workaround (Dashboard öffnen, Charge suchen, dann zurück zu Dateien). Nach der Änderung kann man direkt auf der Dateiseite navigieren und handeln.

---

## Aktueller Zustand

### Relevante bestehende Struktur

| Datei | Relevanz |
|---|---|
| `src/docucontrol/templates/filemanager.html` | Beide Dateitabellen + JS-Rendering |
| `src/docucontrol/templates/dashboard.html` | Referenz-Pattern: Charge-Nr.-Spalte + Programm-Icon |
| Pi: `api_protocols` | Gibt `charge_nr`, `program`, `timestamp`, `file_size`, `pdf_filename`, `id`, `status`, `duration` zurück |
| Pi: `GET /api/storage/pdfs/usb` | Gibt `{name, path, size_human, modified}` zurück — kein charge_nr-Feld |

### Lücken oder Probleme, die adressiert werden

1. **Dateiname als Primärinfo:** `renderFileRow` zeigt `pdf_filename` als einzige Kennung — bei langem Maschinennamen wird `CH021730` immer abgeschnitten.
2. **Redundante Info:** Datum steckt doppelt im Dateinamen und in der Datum-Spalte.
3. **Kein Programm sichtbar:** Welches Programm ein PDF enthält, sieht man im Dateimanager gar nicht.
4. **API liefert alle Felder bereits:** `charge_nr`, `program`, `status` sind im Response, werden aber nicht genutzt — `loadInternalFiles` übergibt nur `{id, filename, timestamp, file_size}`.
5. **colspan-Mismatch:** Leer-Zustände nutzen `colspan="4"` — nach Änderung auf 5 Spalten muss das angepasst werden.

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

- `renderFileRow` umbenennen zu `renderInternalFileRow`, komplett neu schreiben: 5 Spalten, Charge-Nr. als Badge, Programm mit Icon, Status-Badge entfällt (Dateiseite = nur "Bestanden")
- `renderUsbFileRow` umbenennen zu `renderUsbRow`, auf 5 Spalten bringen: Charge-Nr. + Datum aus Dateiname extrahieren, Programm = `—`
- `loadInternalFiles` übergibt alle API-Felder an die Render-Funktion (kein Mapping mehr)
- Tabellen-Header beider Cards: `Charge-Nr. | Datum | Programm | Größe | Aktionen`
- Leer-Zustände: `colspan="4"` → `colspan="5"`
- Programm-Icon-Logik aus `dashboard.html` in `filemanager.html` übernehmen (identische `getProgramIcon`-Funktion)

### Neue Dateien erstellen

Keine.

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|---|---|
| `src/docucontrol/templates/filemanager.html` | Tabellen-Header (beide), renderFileRow, renderUsbFileRow, loadInternalFiles-Mapping, colspan-Werte |

### Zu löschende Dateien

Keine.

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **Keine Dateiumbenennung:** Bestehende PDFs auf USB und in der DB behalten ihre Namen. Nur die Darstellungsebene ändert sich. Keine Migration nötig.
2. **5 Spalten statt 4:** `Charge-Nr. | Datum | Programm | Größe | Aktionen` — Programm ist die wertvollste neue Info. Datum bleibt wegen USB-Dateien (wo nur Datum aus Filename extrahierbar ist).
3. **Charge-Nr. aus USB-Dateiname via JS-Regex:** `/CH0*(\d+)/i` auf `f.name` — extrahiert `CH021730` ohne serverseitige Änderung. Kein Match → `—` anzeigen.
4. **Datum aus USB-Dateiname:** `f.name.substring(0, 10)` → `YYYY-MM-DD` → `DD.MM.YYYY` — funktioniert sicher am bekannten Dateinamen-Format.
5. **Programm für USB = `—`:** Das Programm steckt nicht im Dateinamen und ein extra API-Roundtrip für USB-Files ist nicht gerechtfertigt. `—` ist ehrlicher als leer.
6. **Kein Status-Badge im Dateimanager:** Der Dateimanager zeigt nur `completed`-Protokolle (mit PDF). Status ist hier immer "Bestanden" — redundant. Spart eine Spalte.
7. **Programm-Icon identisch zum Dashboard:** `getProgramIcon()`-Funktion aus `dashboard.html` kopieren — Konsistenz über alle Seiten.
8. **`charge`-CSS-Klasse für Charge-Nr.:** Selbe Klasse wie im Dashboard (`<span class="charge">`) — keine neue CSS nötig, da `docucontrol.css` die Klasse bereits definiert.
9. **`prog-tag`-CSS-Klasse für Programm:** Selbe Klasse wie im Dashboard — Konsistenz, kein neues CSS.

### Betrachtete Alternativen

- **Dateiname als zweite Zeile (Sub-Text):** Würde zwei-Zeilen-Rows erzeugen und die Tabelle aufblähen. Kein Mehrwert, da der Dateiname keine Info enthält, die nicht schon in den anderen Spalten ist.
- **Nur Charge-Nr. hinzufügen, Dateiname behalten:** Würde 6 Spalten erzeugen und das Problem der Enge verschlimmern.
- **Tabelle breiter machen (full-width statt two-col):** Würde das Two-Col-Layout zerstören und auf schmalen Bildschirmen schlecht aussehen.
- **Tooltip mit vollem Dateinamen:** Gute Ergänzung, aber kein Ersatz für strukturierte Spalten.

### Offene Fragen

Keine — alle Felder sind verfügbar, kein serverseitiger Änderungsbedarf.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: Tabellen-Header beider Cards umschreiben

Beide `<thead>`-Blöcke (intern + USB) erhalten die neuen 5 Spalten.

**Aktionen:**

Vorher (intern, Zeile 29–34):
```html
<tr>
    <th style="width:99%">Dateiname</th>
    <th style="white-space:nowrap">Datum</th>
    <th style="white-space:nowrap">Größe</th>
    <th class="right" style="white-space:nowrap">Aktionen</th>
</tr>
```

Nachher:
```html
<tr>
    <th style="white-space:nowrap">Charge-Nr.</th>
    <th style="white-space:nowrap">Datum</th>
    <th style="width:99%">Programm</th>
    <th style="white-space:nowrap">Größe</th>
    <th class="right" style="white-space:nowrap">Aktionen</th>
</tr>
```

Identische Änderung für den USB-Header (Zeile 71–75). Das `width:99%` wandert von "Dateiname" zu "Programm" — Programm bekommt den Flex-Platz, alle anderen Spalten sind eng.

**Betroffene Dateien:**
- `src/docucontrol/templates/filemanager.html`

---

### Schritt 2: Leer-Zustände auf colspan=5 aktualisieren

Alle `colspan="4"` in den Tabellen auf `colspan="5"` ändern.

**Aktionen:**

Betroffene Stellen:
- Zeile 37: `<tr><td colspan="4"` (interner Lade-Spinner)
- Zeile 78: `<tr><td colspan="4"` (USB kein USB-Speicher)
- In JS: alle `colspan="4"` in `innerHTML`-Strings in `loadInternalFiles` und `loadUsbFiles`

Alle `colspan="4"` → `colspan="5"` ersetzen (replace_all).

**Betroffene Dateien:**
- `src/docucontrol/templates/filemanager.html`

---

### Schritt 3: `getProgramIcon`-Funktion einfügen

Identische Funktion wie in `dashboard.html` (Zeile 167–175) in den `filemanager.html`-Script-Block einfügen, direkt nach `escHtml`.

**Aktionen:**

```javascript
function getProgramIcon(prog) {
    var p = (prog || '').toLowerCase();
    if (p.indexOf('instrument') !== -1) return 'bi-wrench-adjustable';
    if (p.indexOf('bowie') !== -1 || p.indexOf('bd-test') !== -1) return 'bi-clipboard-check';
    if (p.indexOf('vpr') !== -1 || p.indexOf('vakuum') !== -1) return 'bi-arrow-repeat';
    if (p.indexOf('textil') !== -1) return 'bi-droplet';
    return 'bi-collection';
}
```

Einfügen nach der `formatDate`-Funktion (nach Zeile 125).

**Betroffene Dateien:**
- `src/docucontrol/templates/filemanager.html`

---

### Schritt 4: `renderFileRow` für interne Dateien neu schreiben

Die Funktion komplett ersetzen. Verwendet jetzt `charge_nr`, `timestamp`, `program`, `file_size`, `id` direkt — kein `filename`-Feld mehr als Primäranzeige. `pdf_filename` bleibt im Objekt für den Download-Tooltip (title-Attribut).

**Aktionen:**

Vorher:
```javascript
function renderFileRow(f, isInternal) {
    var fn = f.filename || f.pdf_filename || '';
    var date = formatDate(f.timestamp || f.date || '');
    var size = formatBytes(f.file_size || f.size);
    var id = f.id || '';
    return '<tr>'
        + '<td style="max-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
        +   '<div class="fn" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
        +   '<i class="bi bi-file-earmark-pdf-fill"></i>' + escHtml(fn) + '</div></td>'
        + '<td class="muted">' + escHtml(date) + '</td>'
        + '<td class="muted">' + escHtml(size) + '</td>'
        + '<td class="right"><div class="act">'
        + (id ? '<button class="icon-btn" title="Herunterladen" onclick="dlFile(' + id + ')"><i class="bi bi-download"></i></button>' : '')
        + (isInternal && id ? '<button class="icon-btn danger" title="Loeschen" onclick="delFile(' + id + ')"><i class="bi bi-trash"></i></button>' : '')
        + '</div></td>'
        + '</tr>';
}
```

Nachher (Funktion umbenennen + neu schreiben):
```javascript
function renderInternalFileRow(f) {
    var charge = f.charge_nr || '—';
    var date   = formatDate(f.timestamp || '');
    var prog   = f.program || '—';
    var icon   = getProgramIcon(prog);
    var size   = formatBytes(f.file_size || 0);
    var id     = f.id || '';
    var fn     = f.pdf_filename || '';
    return '<tr>'
        + '<td style="white-space:nowrap"><span class="charge">' + escHtml(charge) + '</span></td>'
        + '<td class="muted" style="white-space:nowrap">' + escHtml(date) + '</td>'
        + '<td><span class="prog-tag"><i class="bi ' + icon + ' ic"></i> ' + escHtml(prog) + '</span></td>'
        + '<td class="muted" style="white-space:nowrap">' + escHtml(size) + '</td>'
        + '<td class="right"><div class="act">'
        + (id && fn ? '<button class="icon-btn" title="' + escHtml(fn) + '" onclick="dlFile(' + id + ')"><i class="bi bi-download"></i></button>' : '')
        + (id ? '<button class="icon-btn danger" title="Loeschen" onclick="delFile(' + id + ')"><i class="bi bi-trash"></i></button>' : '')
        + '</div></td>'
        + '</tr>';
}
```

Wichtig: `title="..."` am Download-Button zeigt den vollen Dateinamen als Tooltip.

**Betroffene Dateien:**
- `src/docucontrol/templates/filemanager.html`

---

### Schritt 5: `renderUsbFileRow` für USB-Dateien neu schreiben

USB-Dateien kommen von `/api/storage/pdfs/usb` mit `{name, path, size_human, modified}`. Charge-Nr. und Datum werden per JS-Regex aus dem Dateinamen extrahiert.

**Aktionen:**

Vorher:
```javascript
function renderUsbFileRow(f) {
    var fn = f.name || '';
    var date = f.modified || '---';
    var size = f.size_human || '---';
    var path = encodeURIComponent(f.path || fn);
    return '<tr>'
        + '<td style="max-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
        +   '<div class="fn" ...><i class="bi bi-file-earmark-pdf-fill"></i>' + escHtml(fn) + '</div></td>'
        + '<td class="muted">' + escHtml(date) + '</td>'
        + '<td class="muted">' + escHtml(size) + '</td>'
        + '<td class="right"><div class="act">'
        + '<a class="icon-btn" ... href="/api/storage/file/usb?path=' + path + '" download="' + escHtml(fn) + '"><i class="bi bi-download"></i></a>'
        + '</div></td>'
        + '</tr>';
}
```

Nachher:
```javascript
function renderUsbFileRow(f) {
    var fn   = f.name || '';
    var path = encodeURIComponent(f.path || fn);
    // Charge-Nr. aus Dateinamen extrahieren (z.B. "...CH021730.pdf" → "CH021730")
    var cm = fn.match(/CH0*(\d+)/i);
    var charge = cm ? 'CH' + cm[1] : '—';
    // Datum: erste 10 Zeichen des Dateinamens (YYYY-MM-DD) → DD.MM.YYYY
    var rawDate = fn.length >= 10 ? fn.substring(0, 10) : '';
    var date = '—';
    if (rawDate && rawDate.match(/^\d{4}-\d{2}-\d{2}$/)) {
        var dp = rawDate.split('-');
        date = dp[2] + '.' + dp[1] + '.' + dp[0];
    }
    var size = f.size_human || '—';
    return '<tr>'
        + '<td style="white-space:nowrap"><span class="charge">' + escHtml(charge) + '</span></td>'
        + '<td class="muted" style="white-space:nowrap">' + escHtml(date) + '</td>'
        + '<td class="muted">—</td>'
        + '<td class="muted" style="white-space:nowrap">' + escHtml(size) + '</td>'
        + '<td class="right"><div class="act">'
        + '<a class="icon-btn" title="' + escHtml(fn) + '" href="/api/storage/file/usb?path=' + path + '" download="' + escHtml(fn) + '"><i class="bi bi-download"></i></a>'
        + '</div></td>'
        + '</tr>';
}
```

**Betroffene Dateien:**
- `src/docucontrol/templates/filemanager.html`

---

### Schritt 6: `loadInternalFiles` — Mapping auf alle API-Felder erweitern

Aktuell übergibt `loadInternalFiles` nur `{id, filename, timestamp, file_size}` an `renderFileRow`. Das muss auf alle Felder erweitert werden, und der Aufruf muss auf `renderInternalFileRow` umgestellt werden.

**Aktionen:**

Vorher (Zeile 212–219):
```javascript
body.innerHTML = files.map(function(f) {
    return renderFileRow({
        id: f.id,
        filename: f.pdf_filename,
        timestamp: f.timestamp,
        file_size: f.file_size || 0
    }, true);
}).join('');
```

Nachher:
```javascript
body.innerHTML = files.map(function(f) {
    return renderInternalFileRow(f);
}).join('');
```

Die API gibt bereits alle nötigen Felder zurück (`charge_nr`, `program`, `timestamp`, `file_size`, `id`, `pdf_filename`) — kein zusätzlicher Mapping-Overhead.

**Betroffene Dateien:**
- `src/docucontrol/templates/filemanager.html`

---

### Schritt 7: Auf Pi deployen und verifizieren

**Aktionen:**

```bash
scp -i ~/.ssh/id_ed25519 \
  src/docucontrol/templates/filemanager.html \
  docucontrol@192.168.0.171:/home/docucontrol/docupi/templates/filemanager.html
```

Service-Neustart nicht nötig (Flask lädt Templates bei jedem Request neu in Debug-Mode, oder kurzer Restart für Sicherheit).

Im Browser prüfen:
- Interne Liste: Charge-Nr. sichtbar, Datum, Programm mit Icon, Größe korrekt
- Download-Button: Tooltip zeigt vollen Dateinamen
- Löschen: funktioniert noch
- USB-Liste (falls USB angeschlossen): Charge-Nr. + Datum aus Dateiname extrahiert, `—` in Programm-Spalte
- Leere Zustände: kein Layout-Bruch durch falsche colspan

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/templates/filemanager.html`

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- `dashboard.html` — unverändert; `charge`-CSS-Klasse und `prog-tag` sind dort bereits definiert und kommen via `docucontrol.css`
- `docucontrol.css` — wird genutzt, nicht geändert; `.charge`, `.prog-tag`, `.ic` sind vorhanden

### Nötige Updates für Konsistenz

- CLAUDE.md: kurzer Hinweis unter Datei-Manager-Sektion, dass Tabelle strukturierte Spalten statt Dateinamen zeigt
- Kein API-Änderungsbedarf — alle Felder bereits im Response

### Auswirkungen auf bestehende Workflows

- Download und Löschen: Funktionen `dlFile()` und `delFile()` unverändert — nutzen weiterhin `id`
- Paginierung: unverändert — `loadInternalFiles(page)` und Pager funktionieren wie vorher
- Auto-Refresh (30s): unverändert

---

## Validierungs-Checkliste

- [ ] Interne Tabelle zeigt 5 Spalten: Charge-Nr. | Datum | Programm | Größe | Aktionen
- [ ] Charge-Nr. als `charge`-Badge sichtbar (z.B. `CH021730`)
- [ ] Programm mit passendem Icon sichtbar (z.B. Schraubenschlüssel für Instrumente)
- [ ] Download-Button: Tooltip (`title`) zeigt vollen Dateinamen
- [ ] Löschen-Button: Protokoll wird korrekt gelöscht, Seite neu geladen
- [ ] USB-Tabelle: 5 Spalten, Charge-Nr. aus Dateinamen extrahiert, Datum korrekt, Programm = `—`
- [ ] Leere Zustände (kein Protokoll, kein USB): kein colspan-Bruch
- [ ] Paginierung funktioniert weiterhin (Pager + Zähler)
- [ ] Kein JavaScript-Fehler in Browser-Console

---

## Erfolgskriterien

Die Implementierung ist abgeschlossen, wenn:

1. Die Charge-Nr. (z.B. `CH021730`) auf der Dateiseite in der ersten Spalte sofort sichtbar ist — ohne scrollen, ohne Tooltip-Hover
2. Das Programm (z.B. `1: Instrumente 134°C`) mit Icon in der dritten Spalte sichtbar ist
3. USB-Dateien zeigen ebenfalls Charge-Nr. und Datum — auch ohne DB-Zugriff korrekt extrahiert

---

## Notizen

- **Warum kein Status-Badge?** Der Dateimanager zeigt implizit nur `completed`-Protokolle (nur die haben ein PDF). Ein "Bestanden"-Badge wäre redundant.
- **Programm-Werte haben `N: `-Prefix:** Aktuell liefert die API z.B. `"1: Instrumente 134°C"`. Das kommt aus dem Protokollformat. Für die Darstellung wird es unverändert übernommen — konsistent mit Dashboard. Eine Bereinigung (Prefix abschneiden) kann in einem späteren Plan erfolgen.
- **USB-Dateiname als Tooltip:** Bei USB-Dateien zeigt der Download-Button (`title`-Attribut) ebenfalls den vollen Dateinamen. Praktisch falls man den exakten Dateinamen braucht.
- **Zukünftig:** Wenn `/api/storage/pdfs/usb` erweitert wird (charge_nr, program aus DB), kann `renderUsbFileRow` die dann verfügbaren Felder nutzen statt der Regex-Extraktion.
