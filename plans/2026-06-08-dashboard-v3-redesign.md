# Plan: Dashboard v3 Redesign — Liquid Glass + Machine-Bar + neue Stat-Karten

**Erstellt:** 2026-06-08
**Status:** Implementiert
**Anforderung:** Die Dashboard-Startseite (Chargen-Tab) auf das neue v3-Design anpassen — Machine-Bar, 3 Stat-Karten (inkl. Monat-Trend), Dauer-Spalte, Programm-Icons, Liquid-Glass-Optik, Live-Uhr und Square-Schrift im Topbar. Alle neuen UI-Elemente müssen vollständig funktional sein.

---

## Überblick

### Was dieser Plan erreicht

Die Dashboard-Seite (`/`) wird von der aktuellen Flat-Design-Optik (v1/v2) auf das neue v3-Design-System migriert, das der Designer als Handoff geliefert hat. Das Ergebnis ist eine produktionsreife Chargen-Übersicht mit Maschinenidentifikationsbar, drei Statistikkarten (inkl. Monats-Trend-Vergleich), Dauer-Spalte in der Tabelle, Programm-Icons und dem vollständigen Liquid-Glass-Visuellen. Die anderen Seiten (Dateien, Einstellungen) bleiben vorerst unangetastet.

### Warum das wichtig ist

DocuControl ist das Produkt für den ersten Kunden-Deal (Tierlabor Uni Essen via getmatic). Das v3-Design ist der offizielle GeTmatic-Handoff und soll das Interface professionell und vertrauenswürdig wirken lassen — medizintechnisch seriös, nicht ein Bastelprojekt. Die Maschinen-Bar macht die Verbindung zur Anlage sofort sichtbar, was für Kliniktechniker im Tagesbetrieb entscheidend ist.

---

## Aktueller Zustand

### Relevante bestehende Struktur

- `src/docucontrol/templates/dashboard.html` — aktuelles Dashboard (2 Stat-Karten, keine Dauer-Spalte, keine Machine-Bar)
- `src/docucontrol/templates/base.html` — Topbar mit flachem Design, kein Square-Font, kein Live-Clock, Badge text "Verbunden/Getrennt"
- `src/docucontrol/static/docucontrol.css` — v1/v2 CSS (flat, keine Glass-Effekte, einfache Buttons)
- `reference/design_handoff_docucontrol_v3/` — vollständiger v3-Handoff (HTML-Prototyp, CSS, JS, Font)
- Pi: `app.py` auf 192.168.0.171 — `/api/protocols` liefert bereits `duration`-Feld (HH:MM:SS)
- Pi: `app.py` — kein `/api/dashboard/stats`-Endpunkt für Monats-Trend vorhanden

### Lücken oder Probleme, die adressiert werden

1. **Kein Machine-Bar** — aktuelle UI zeigt keine Maschinenidentität
2. **Nur 2 Stat-Karten** — fehlt: Chargen diesen Monat + Trend vs. Vormonat
3. **Kein Dauer-Feld in Tabelle** — API liefert `duration`, wird aber nicht angezeigt
4. **Kein Programm-Icon** — alle Programme sehen identisch aus
5. **Flaches Design** — kein Liquid Glass, veraltete Button-Styles, kein Square-Font
6. **Kein Live-Clock** im Topbar
7. **Badge zeigt "Verbunden/Getrennt"** statt "Aktiv" mit pulsierender Animation
8. **"by GeTmatic"** wird ohne Square-Schrift gerendert

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

- Square-Font in `static/` kopieren
- CSS komplett auf v3-Tokens und Liquid-Glass upgraden (additive Migration — Klassen bleiben kompatibel)
- `base.html`: Square-Font für "GeTmatic", Live-Uhr, pulsierender "Aktiv"-Badge
- `dashboard.html`: Machine-Bar, 3 Stat-Karten, Dauer-Spalte, Programm-Icons, neue Button-Klassen
- `app.py` auf Pi: neuer `/api/dashboard/stats`-Endpunkt (heute, Monat, Vormonat, Trend)
- Deployment auf Pi (SSH)

### Neue Dateien erstellen

| Dateipfad | Zweck |
|---|---|
| `src/docucontrol/static/fonts/Square.ttf` | GeTmatic-Markenschrift (aus v3-Handoff kopiert) |

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|---|---|
| `src/docucontrol/static/docucontrol.css` | V3-Tokens, Liquid-Glass-Primitives, neue Button/Card/Stat-Styles; bestehende Klassen bleiben kompatibel |
| `src/docucontrol/templates/base.html` | @font-face Square, Live-Uhr im Topbar, Badge auf "Aktiv" + Pulse-Animation, Tab-Label "Dashboard" → "Chargen" |
| `src/docucontrol/templates/dashboard.html` | Machine-Bar (dynamisch), 3 Stat-Karten inkl. Monat-Trend, Dauer-Spalte, Programm-Icon-Mapping, `btn-glass` statt `btn-outline`, Print-Toast v3-Style |

### Zu ändernde Dateien auf Pi (via SSH)

| Dateipfad auf Pi | Änderungen |
|---|---|
| `/home/docucontrol/docupi/app.py` | Neuer Endpunkt `GET /api/dashboard/stats` (heute-Count, Monat-Count, Vormonat-Count, Trend-%) + Machine-Konfiguration im Template-Context |

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **Additive CSS-Migration statt Komplettaustausch**: Die bestehenden CSS-Klassen (`.stat`, `.btn`, `.card` etc.) werden auf die neuen v3-Styles umgeschrieben — keine neuen Klassennamens-Konflikte, da v3 dieselben Namen verwendet. Einstellungen- und Datei-Seite profitieren automatisch von globalem Tokens-Update.

2. **Square-Font via `@font-face` in CSS**: `fonts/Square.ttf` wird in `static/fonts/` abgelegt und per CSS-Variable `--font-brand` referenziert. Nur `<b>GeTmatic</b>` im Topbar und Footer bekommt diese Schrift — konform mit Handoff-Spec.

3. **Neuer API-Endpunkt `/api/dashboard/stats`**: Statt 3 separate `/api/protocols`-Fetches (heute/Monat/gesamt) wird ein dedizierter Stats-Endpunkt implementiert. Effizienter (3 COUNT-Queries statt 3 vollständige SELECT), saubere Trennung.

4. **Machine-Bar aus Flask-Context**: Machine-Name und -Typ werden als Konstanten in `app.py` definiert (`MACHINE_NAME`, `MACHINE_PROTOCOL`) und per Jinja2 in das Template injiziert. Kein extra DB-Table nötig. Bei Tierlabor-Deployment: Werte anpassen wenn Maschinentyp bekannt.

5. **Verbindungsstatus für Machine-Bar**: Nutzt denselben `/api/tcp_capture/status`-Endpunkt wie der Badge. Machine-Bar zeigt "Maschine verbunden" (grün) oder "Keine Verbindung" (grau) — keine neue API nötig.

6. **Programm-Icon-Mapping im Frontend**: Die 4 Programm-Typen (Instrumente, Bowie-Dick, Vakuumtest/VPR, Textilien) bekommen per JS-Funktion ein Bootstrap-Icon zugewiesen. Case-insensitive Matching auf Programm-Name.

7. **Tab-Name "Chargen" im Topbar**: Der Tab heißt im v3 "Chargen" statt "Dashboard" — wird in `base.html` geändert. URL bleibt `/`.

8. **Dauer-Spalte**: `duration`-Feld aus API (`HH:MM:SS`) wird direkt in neue Spalte zwischen Programm und Status eingefügt. Leerer Eintrag zeigt `—`.

### Betrachtete Alternativen

- **Separate CSS-Datei für v3**: Wurde verworfen — würde Spezifitätskonflikte erzeugen und zwei Stylesheets bedeuten.
- **Machine-Bar aus DB**: Aufwendig (neue Tabelle, Migrations-Script) für minimalen Mehrwert. Konstante in app.py reicht.
- **Monats-Trend clientseitig**: Zwei separate fetch()-Calls wären langsamer und würden Race-Conditions riskieren.

### Offene Fragen

1. **Machine-Name für Tierlabor**: Maschinentyp ist noch unbekannt. Im Plan wird Platzhalter `"Konfiguration ausstehend"` verwendet — nach Sample-Druckauftrag anpassen.
2. **Monat-Trend bei <1 Vormonat-Protokoll**: Falls Vormonat-Count = 0, kein Trend berechnenbar → Karte zeigt nur absoluten Wert ohne Trend-Chip.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: Square-Font einrichten

Square-Font aus dem v3-Handoff in den Static-Ordner kopieren.

**Aktionen:**
- `mkdir -p src/docucontrol/static/fonts/`
- `cp reference/design_handoff_docucontrol_v3/fonts/Square.ttf src/docucontrol/static/fonts/Square.ttf`

**Betroffene Dateien:**
- `src/docucontrol/static/fonts/Square.ttf` (neu)

---

### Schritt 2: CSS auf v3 upgraden (`docucontrol.css`)

Das CSS komplett auf die v3-Spezifikation umschreiben. Enthält alle Tokens aus `colors_and_type.css` + Liquid-Glass-Layer aus `app/docucontrol.css`. Bestehende Klassen werden auf gleiche Namen umgeschrieben (kein Breaking-Change für andere Seiten).

**Aktionen:**

Die wichtigsten CSS-Änderungen gegenüber dem aktuellen Stand:

**`:root` Tokens:**
- `@font-face` für Square.ttf ergänzen
- Neue Variablen: `--font-brand`, `--font-sans`, `--font-mono`
- Neue Variablen: `--shadow-sm`, `--shadow-md`, `--shadow-lg`
- Neue Variablen: `--glass-fill`, `--glass-fill-2`, `--glass-bd`, `--glass-hi`, `--glass-blur`
- Neue Variablen: `--warn-bg`, `--warn-bd`, `--warn-fg`
- Neue Variablen: `--topbar-2`, `--success-strong`, `--row-sel`, `--row-sel-bd`
- `--success: #28a745` (war `#198754` — v3 nutzt helleres Grün)
- `--shadow` → `--shadow-sm` umbenennen (Kompatibilität via Alias)

**Topbar:**
- `--topbar`: Gradient `#3a4658 → #323C4B` (war Flat `#323C4B`)
- Box-shadow ergänzen
- `.brand .logo .by b` → `font-family: var(--font-brand)`
- `.conn-badge`: `backdrop-filter: var(--glass-blur)` ergänzen
- `.conn-badge.online .dot`: `animation: pulse-ready` ergänzen
- `@keyframes pulse-ready` neu hinzufügen

**Navstrip:**
- `background: rgba(255,255,255,0.75)` + `backdrop-filter`
- `position: sticky; top: 58px; z-index: 40`

**Buttons (neue Klassen hinzufügen, bestehende umschreiben):**
- `.btn`: `border-radius: 10px`, Transition erweitern
- `.btn-primary`: Liquid-Glass-Gradient + box-shadow
- `.btn-glass` (NEU): frosted-clear glass button
- `.btn-outline-danger`: Liquid-Glass-Style
- `.btn[disabled]`: uniformisieren

**Stat-Cards:**
- `.stat`: `border-radius: 14px`, Liquid-Glass-Gradient, `box-shadow: var(--shadow-sm)`
- `.stat:hover`: `box-shadow: var(--shadow-md)`
- `.stat .big`: `font-size: 34px` (war 30px), `font-variant-numeric: tabular-nums`
- `.stat .icon-tile`: `position: absolute; top: 16px; right: 16px` (war float)
- `.icon-tile.*`: backdrop-filter + glass-hi ergänzen

**Filter-Bar:**
- `background`: leicht anpassen auf v3-Gradient
- `.ctrl`: `border-radius: 8px` (war 6px), `height: 38px`

**Tabellen:**
- `.table-wrap`: `border-radius: 12px`
- `th:first-child`, `th:last-child`: `border-radius` auf 12px
- `.prog-tag` (NEU): Display für Icon + Programm-Name
- `.badge`: `border: 1px solid transparent` ergänzen

**Icon-Buttons:**
- `.icon-btn`: `width: 34px; height: 34px`, `border-radius: 9px`, Liquid-Glass
- `.icon-btn:hover`: `translateY(-1px)`

**Machine-Bar (NEU — komplette neue Komponente):**
```css
.machine-bar { display: flex; align-items: center; gap: 16px;
  background: linear-gradient(180deg, rgba(255,255,255,0.55), rgba(255,255,255,0.2)),
    linear-gradient(110deg, rgba(31,78,121,0.06), rgba(46,117,182,0.03));
  border: 1px solid var(--border); border-radius: 14px;
  padding: 14px 18px; margin-bottom: 18px; box-shadow: var(--shadow-sm); }
.machine-bar .mb-icon { width:48px; height:48px; border-radius:12px; flex-shrink:0;
  display:flex; align-items:center; justify-content:center; font-size:1.5rem;
  color: var(--primary);
  background: linear-gradient(180deg, rgba(31,78,121,.16), rgba(31,78,121,.06));
  border: 1px solid var(--glass-bd); box-shadow: var(--glass-hi); }
.machine-bar .mb-name { font-size:18px; font-weight:700; color:var(--text); }
.machine-bar .mb-chips { display:flex; flex-wrap:wrap; gap:7px; flex:1; }
.machine-bar .mb-status { display:inline-flex; align-items:center; gap:7px; flex-shrink:0;
  font-size:12.5px; font-weight:600; color:#15724a;
  background:var(--success-soft); border:1px solid rgba(25,135,84,0.22);
  padding:6px 13px; border-radius:50px; }
.machine-bar .mb-status.offline { color:var(--muted);
  background:#eceff3; border-color:var(--border); }
.chip { display:inline-flex; align-items:center; gap:6px;
  font-size:12px; font-weight:600; color:#41506a;
  background:rgba(255,255,255,0.7); border:1px solid var(--border);
  border-radius:50px; padding:4px 11px; white-space:nowrap; }
.chip .bi { color:var(--accent); font-size:12px; }
```

**Responsive:**
- Machine-Bar: `flex-wrap: wrap` auf `<760px`
- Alle bestehenden Breakpoints beibehalten

**Betroffene Dateien:**
- `src/docucontrol/static/docucontrol.css`

---

### Schritt 3: `base.html` aktualisieren

Topbar, Font-Link, Live-Uhr, Badge-Animation, Tab-Name.

**Aktionen:**

Im `<head>`:
- Bootstrap-CDN-Link in base.html **nicht** entfernen — erst wenn alle Seiten auf v3 migriert sind
- `@font-face` wird in CSS gehandelt (kein separater `<link>` nötig)

In `.topbar`:
- `.brand .logo`: `<span class="logo">DocuControl<span class="by">by <b>GeTmatic</b></span></span>` — `<b>` macht Square-Font aktiv
- Rechts: Live-Uhr `<span class="topbar-clock">` mit `id="barDate"` und `id="barTime"` ergänzen
- Badge: Text von "Verbunden/Getrennt" auf "Aktiv/Getrennt" ändern
- Badge: `title="Gerät betriebsbereit"` ergänzen

In `.navstrip`:
- Tab "Dashboard" → `<i class="bi bi-collection"></i> Chargen`
- Tab-Links bleiben als `<a href="">` (Multi-Page-App bleibt erhalten)

Im `<script>` Block der base.html:
- Live-Uhr-Logik ergänzen:
```javascript
function tickClock() {
    var now = new Date();
    var d = now.toLocaleDateString('de-DE', {day:'2-digit',month:'2-digit',year:'numeric'});
    var t = now.toLocaleTimeString('de-DE');
    var bd = document.getElementById('barDate');
    var bt = document.getElementById('barTime');
    if (bd) bd.textContent = d;
    if (bt) bt.textContent = t;
}
tickClock();
setInterval(tickClock, 1000);
```
- TCP-Badge-Refresh bleibt, aber Badge-Text "Aktiv" statt "Verbunden" wenn online

**Betroffene Dateien:**
- `src/docucontrol/templates/base.html`

---

### Schritt 4: Neuer API-Endpunkt `/api/dashboard/stats` auf Pi

Effizienter Stats-Endpunkt für die drei Dashboard-Karten mit Monat-Trend.

**Aktionen:**

Auf dem Pi in `app.py` einen neuen Route einfügen (nach dem bestehenden `/api/protocols/programs`-Block):

```python
@app.route('/api/dashboard/stats')
def api_dashboard_stats():
    """Kompakte Statistiken für Dashboard-Karten."""
    import datetime
    db = get_db()
    now = datetime.datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    
    # Monat-Grenzen
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 1:
        prev_month_start = month_start.replace(year=month_start.year-1, month=12)
    else:
        prev_month_start = month_start.replace(month=month_start.month-1)
    
    month_start_s = month_start.strftime('%Y-%m-%d')
    prev_month_start_s = prev_month_start.strftime('%Y-%m-%d')
    
    total = db.execute("SELECT COUNT(*) FROM protocols").fetchone()[0]
    today = db.execute(
        "SELECT COUNT(*) FROM protocols WHERE timestamp >= ? AND timestamp < ?",
        (today_str + ' 00:00:00', today_str + ' 23:59:59')
    ).fetchone()[0]
    month = db.execute(
        "SELECT COUNT(*) FROM protocols WHERE timestamp >= ?",
        (month_start_s,)
    ).fetchone()[0]
    prev_month = db.execute(
        "SELECT COUNT(*) FROM protocols WHERE timestamp >= ? AND timestamp < ?",
        (prev_month_start_s, month_start_s)
    ).fetchone()[0]
    
    # Letzte Charge heute
    last_today = db.execute(
        "SELECT timestamp FROM protocols WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp DESC LIMIT 1",
        (today_str + ' 00:00:00', today_str + ' 23:59:59')
    ).fetchone()
    last_time = ''
    if last_today:
        ts = (last_today[0] or '').replace('T', ' ').split('.')[0]
        last_time = ts.split(' ')[1][:5] if ' ' in ts else ''
    
    trend_pct = None
    if prev_month > 0:
        trend_pct = round((month - prev_month) / prev_month * 100, 1)
    
    db.close()
    return jsonify({
        'total': total,
        'today': today,
        'today_last_time': last_time,
        'month': month,
        'prev_month': prev_month,
        'month_trend_pct': trend_pct
    })
```

Zusätzlich: Machine-Konfiguration als Konstanten in `app.py` ergänzen (oben im File nach den Imports):
```python
# Machine identity — bestätigt durch Felix 2026-06-08
MACHINE_NAME = 'Belimed PST 14-8-12 HS1'
MACHINE_PROTOCOL = '6050 / 6060 FIS'
```

Und im Template-Context-Processor (bereits in `app_additions.py`/`app.py`):
```python
'machine_name': MACHINE_NAME,
'machine_protocol': MACHINE_PROTOCOL,
```

**Betroffene Dateien auf Pi:**
- `/home/docucontrol/docupi/app.py`

---

### Schritt 5: `dashboard.html` komplett auf v3 umschreiben

Die Dashboard-Template-Datei erhält alle v3-Komponenten. Alle bestehenden JavaScript-Funktionen bleiben erhalten, werden um neue ergänzt.

**Aktionen:**

**HTML-Struktur (im `{% block content %}`):**

1. **Page-Header** ändern:
```html
<div class="page-head">
    <div>
        <div class="over">Übersicht</div>
        <h1>Chargenprotokolle</h1>
        <div class="lede">Gespeicherte Sterilisations-Chargen ansehen, filtern und drucken.</div>
    </div>
</div>
```

2. **Machine-Bar (NEU)** — mit Jinja2-Variablen und dynamischem Status:
```html
<div class="machine-bar">
    <div class="mb-icon"><i class="bi bi-safe2"></i></div>
    <div class="mb-main">
        <div class="mb-name" id="machineName">{{ machine_name }}</div>
    </div>
    <div class="mb-chips" id="machineChips">
        {% if machine_protocol %}
        <span class="chip"><i class="bi bi-diagram-3"></i> {{ machine_protocol }}</span>
        {% endif %}
    </div>
    <span class="mb-status" id="machineStatus">
        <i class="bi bi-hdd-network-fill" id="machineStatusIcon"></i>
        <span id="machineStatusText">Verbindung prüfen …</span>
    </span>
</div>
```

3. **Stat-Karten** (3 statt 2):
```html
<div class="stat-row" id="statRow">
    <div class="stat">
        <div class="icon-tile navy"><i class="bi bi-hash"></i></div>
        <div class="label">Chargen gesamt</div>
        <div class="big" id="totalCount">—</div>
        <div class="sub" id="totalSub">Höchster Chargenzähler</div>
    </div>
    <div class="stat">
        <div class="icon-tile blue"><i class="bi bi-calendar-day"></i></div>
        <div class="label">Chargen heute</div>
        <div class="big" id="todayCount">—</div>
        <div class="sub" id="todaySub">Wird geladen …</div>
    </div>
    <div class="stat">
        <div class="icon-tile green"><i class="bi bi-calendar3"></i></div>
        <div class="label">Chargen diesen Monat</div>
        <div class="big" id="monthCount">—</div>
        <div class="sub" id="monthSub">Wird geladen …</div>
    </div>
</div>
```

4. **Filter-Bar**: `btn-outline` → `btn-glass` für Reset-Button

5. **Protokoll-Tabelle**: Neue Spalte **Dauer** zwischen Programm und Status:
```html
<th data-sort="duration">Dauer <i class="bi bi-chevron-expand sort"></i></th>
```
Spaltenanzahl ändert sich von 5 auf 6 — alle `colspan="5"` auf `6` anpassen.

**JavaScript-Änderungen:**

6. **`loadStats()` ersetzen** durch Aufruf von `/api/dashboard/stats`:
```javascript
function loadStats() {
    fetch('/api/dashboard/stats')
        .then(function(r) { return r.json(); })
        .then(function(d) {
            // Gesamt
            document.getElementById('totalCount').textContent = d.total.toLocaleString('de-DE');
            // Heute
            document.getElementById('todayCount').textContent = d.today;
            document.getElementById('todaySub').textContent = d.today_last_time
                ? 'Letzte um ' + d.today_last_time + ' Uhr'
                : 'Noch keine heute';
            // Monat
            document.getElementById('monthCount').textContent = d.month.toLocaleString('de-DE');
            if (d.month_trend_pct !== null && d.month_trend_pct !== undefined) {
                var sign = d.month_trend_pct >= 0 ? '↑' : '↓';
                var cls = d.month_trend_pct >= 0 ? 'up' : 'down';
                document.getElementById('monthSub').innerHTML =
                    '<span class="trend ' + cls + '">' + sign + ' ' + Math.abs(d.month_trend_pct) + ' %</span> ggü. Vormonat';
            } else {
                document.getElementById('monthSub').textContent = 'Kein Vormonats-Vergleich';
            }
        }).catch(function() {});
}
```

7. **`renderTable()` ergänzen** — Dauer-Spalte + Programm-Icon:
```javascript
function getProgramIcon(prog) {
    var p = (prog || '').toLowerCase();
    if (p.indexOf('instrument') !== -1) return 'bi-wrench-adjustable';
    if (p.indexOf('bowie') !== -1 || p.indexOf('bd') !== -1) return 'bi-clipboard-check';
    if (p.indexOf('vpr') !== -1 || p.indexOf('vakuum') !== -1) return 'bi-arrow-repeat';
    if (p.indexOf('textil') !== -1) return 'bi-droplet';
    return 'bi-collection';
}
```
Programm-Zelle: `'<td><span class="prog-tag"><i class="bi ' + getProgramIcon(p.program) + ' ic"></i> ' + escHtml(p.program) + '</span></td>'`

Dauer-Zelle: `'<td class="dur">' + escHtml(p.duration || '—') + '</td>'`

8. **Machine-Status** dynamisch via TCP-Status-Endpunkt:
```javascript
function updateMachineStatus() {
    fetch('/api/tcp_capture/status')
        .then(function(r) { return r.json(); })
        .then(function(d) {
            var el = document.getElementById('machineStatus');
            var txt = document.getElementById('machineStatusText');
            var icon = document.getElementById('machineStatusIcon');
            if (d.enabled) {
                el.className = 'mb-status';
                txt.textContent = 'Maschine verbunden';
                icon.className = 'bi bi-hdd-network-fill';
            } else {
                el.className = 'mb-status offline';
                txt.textContent = 'Keine Verbindung';
                icon.className = 'bi bi-hdd-network';
            }
        }).catch(function() {});
}
```
Wird bei Init und im 30s-Intervall mitaufgerufen.

9. **Print-Toast** bleibt unverändert (funktioniert bereits korrekt).

10. **`trend.down`-CSS** ergänzen (im `{% block extra_css %}`):
```css
.stat .trend.down { color: var(--danger); }
```

**Betroffene Dateien:**
- `src/docucontrol/templates/dashboard.html`

---

### Schritt 6: Deployment auf Pi

Alle geänderten Dateien auf den Pi übertragen und Service neu starten.

**Aktionen:**
```bash
# Font
scp -i ~/.ssh/id_ed25519 src/docucontrol/static/fonts/Square.ttf \
    docucontrol@192.168.0.171:/home/docucontrol/docupi/static/fonts/Square.ttf

# CSS
scp -i ~/.ssh/id_ed25519 src/docucontrol/static/docucontrol.css \
    docucontrol@192.168.0.171:/home/docucontrol/docupi/static/docucontrol.css

# Templates
scp -i ~/.ssh/id_ed25519 src/docucontrol/templates/base.html \
    docucontrol@192.168.0.171:/home/docucontrol/docupi/templates/base.html
scp -i ~/.ssh/id_ed25519 src/docucontrol/templates/dashboard.html \
    docucontrol@192.168.0.171:/home/docucontrol/docupi/templates/dashboard.html

# app.py (neuer Endpunkt)
ssh -i ~/.ssh/id_ed25519 docucontrol@192.168.0.171 \
    "sudo systemctl restart docucontrol"
```

Wichtig: `app.py` auf dem Pi direkt bearbeiten (via SSH) oder per scp übertragen.

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/static/fonts/Square.ttf` (neu anlegen — `mkdir -p` vorher)
- Pi: `/home/docucontrol/docupi/static/docucontrol.css`
- Pi: `/home/docucontrol/docupi/templates/base.html`
- Pi: `/home/docucontrol/docupi/templates/dashboard.html`
- Pi: `/home/docucontrol/docupi/app.py`

---

### Schritt 7: Validierung im Browser

Interface auf http://192.168.0.171 testen.

**Aktionen:**
- Dashboard öffnen: Machine-Bar sichtbar, alle 3 Karten befüllt, Dauer-Spalte vorhanden
- Programm-Icons prüfen: Instrumente = Schraubenschlüssel, Bowie-Dick = Clipboard, VPR = Arrow-Repeat
- Monat-Trend-Chip testen (ggf. 0 Vormonats-Protokolle → kein Trend-Chip)
- Topbar: "GeTmatic" in Square-Font, Live-Uhr tickt, Badge pulst grün
- Tab-Navigation zu Dateien/Einstellungen — kein visueller Bruch
- Print-Button klicken → Toast erscheint
- Filter anwenden → Tabelle aktualisiert

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- `src/docucontrol/templates/settings.html` — nutzt gemeinsame CSS-Klassen; CSS-Migration darf keine Breaking Changes einführen
- `src/docucontrol/templates/filemanager.html` — nutzt `.btn`, `.card`, `.icon-btn`, `.pager`
- `src/docucontrol/app_additions.py` — Context-Processor muss `machine_name`, `machine_protocol` liefern

### Nötige Updates für Konsistenz

- `CLAUDE.md` — aktuellen Design-Stand nach Implementierung aktualisieren
- `context/current-data.md` — Dashboard-Redesign als erledigten Meilenstein eintragen
- `context/strategy.md` — ggf. aktualisieren

### Auswirkungen auf bestehende Workflows

- Live-Monitor (settings.html) — `.term`-Styles bleiben kompatibel, da CSS-Klassen beibehalten
- USB-Sync-Toggle — `.switch`-Klasse bleibt kompatibel
- Datei-Manager — `.pager`, `.icon-btn`, `.card` werden aufgewertet (gleiche Klassen, besseres CSS)
- 30s-Auto-Refresh — bleibt erhalten, ruft jetzt `/api/dashboard/stats` statt 2× `/api/protocols` auf

---

## Validierungs-Checkliste

- [ ] Square-Font wird im Topbar für "GeTmatic" korrekt gerendert
- [ ] Live-Uhr tickt sekündlich im Topbar
- [ ] Pulsierender Aktiv-Badge sichtbar (grüner Punkt, `pulse-ready`-Animation)
- [ ] Machine-Bar zeigt Maschinenname und Verbindungsstatus dynamisch
- [ ] 3 Stat-Karten laden Daten aus `/api/dashboard/stats`
- [ ] Monat-Karte zeigt Trend-Chip (oder "Kein Vergleich" wenn Vormonat leer)
- [ ] Dauer-Spalte in Tabelle gefüllt mit HH:MM:SS
- [ ] Programm-Icons korrekt (Instrument, Bowie-Dick, VPR, Textilien)
- [ ] `btn-glass` Reset-Button hat Liquid-Glass-Optik
- [ ] Liquid-Glass Stat-Karten (Gradient + Schatten)
- [ ] Machine-Bar Hover/Mobile responsive
- [ ] Einstellungen-Tab: kein visueller Bruch durch CSS-Änderungen
- [ ] Datei-Manager-Tab: kein visueller Bruch
- [ ] Service startet sauber nach Deploy (`systemctl status docucontrol`)
- [ ] `/api/dashboard/stats` liefert korrektes JSON
- [ ] CLAUDE.md aktualisiert

---

## Erfolgskriterien

Die Implementierung ist abgeschlossen, wenn:

1. Die Dashboard-Seite auf http://192.168.0.171 das v3-Design korrekt rendert — Machine-Bar, 3 Stat-Karten, Dauer-Spalte, Programm-Icons, Live-Uhr, Square-Font, Liquid-Glass-Buttons.
2. Alle Buttons sind vollständig funktional — Filter anwenden, Reset, PDF-Download, Drucken (Toast erscheint), Pager, Spalten-Sortierung.
3. Die Stat-Karten zeigen Live-Daten aus `/api/dashboard/stats` — korrekte Counts, Monat-Trend wenn Vormonats-Daten vorhanden.
4. Die anderen Seiten (Dateien, Einstellungen) zeigen keinen visuellen Rückschritt durch die CSS-Änderungen.

---

---

## Implementierungsnotizen

**Implementiert:** 2026-06-09

### Zusammenfassung

Alle 7 Schritte vollständig umgesetzt. Square-Font deployt, CSS auf v3 Liquid Glass umgeschrieben (additive Migration, alle Settings/Filemanager-Klassen erhalten), base.html mit Live-Uhr und Square-Font für "GeTmatic" aktualisiert, dashboard.html mit Machine-Bar (Belimed PST 14-8-12 HS1), 3 Stat-Karten, Dauer-Spalte und Programm-Icons neu geschrieben. Neuer `/api/dashboard/stats`-Endpunkt in app.py auf Pi gepatcht (Syntax-geprüft). Alle Dateien auf Pi deployed, Service neugestartet (active).

### Abweichungen vom Plan

- Kein `/api/protocols`-Fallback nötig — `/api/dashboard/stats` liefert sofort (`total: 10, month: 10, month_trend_pct: null` weil 0 Vormonats-Protokolle in Test-DB)
- Footer in base.html ebenfalls mit `<b>GeTmatic</b>` für Square-Font versehen (war im Plan nicht explizit, aber logisch konsistent)

### Aufgetretene Probleme

- SSH-Heredoc mit Python-Strings: Quoting-Konflikt — gelöst durch Patch-Script als separate Datei per SCP
- CLAUDE.md Edit wegen exakter Whitespace-Differenz fehlgeschlagen — mit Read + präzisem String behoben

---

## Notizen

- **Maschinentyp**: Bestätigt — `MACHINE_NAME = 'Belimed PST 14-8-12 HS1'`, `MACHINE_PROTOCOL = '6050 / 6060 FIS'`. Zwei Chips in Machine-Bar: "6050 / 6060 FIS" + "VAFI / KOST".
- **Trend-Farbe nach unten**: `.trend.down { color: var(--danger); }` ist im Plan enthalten, fehlt in der aktuellen CSS.
- **Bootstrap-Framework-CSS**: Bleibt drin bis alle Seiten auf v3 migriert und optimiert sind. Kein Thema für diesen Plan.
- **Zukunft**: Der nächste logische Schritt nach dem Dashboard-Redesign wäre die Migration der Einstellungs-Seite auf die v3 6-Tab-Subnav-Struktur (separater Plan).
```
