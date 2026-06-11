# Plan: Dashboard-Fixes — Chargen-heute-Zähler und Dauer-Spalte

**Erstellt:** 2026-06-10
**Status:** Implementiert
**Anforderung:** Dashboard zeigt "Chargen heute = 0" obwohl Protokolle vorhanden, und Dauer-Spalte zeigt immer "—" statt echter Laufzeit.

---

## Überblick

### Was dieser Plan erreicht

Zwei unabhängige Bugs in `app.py` werden gefixt: (1) Der "Chargen heute"-Zähler zählt korrekt alle heutigen Protokolle, (2) die Dauer-Spalte in der Protokollliste zeigt die echte Programmlaufzeit im Format `HH:MM:SS`. Beide Fixes sind reine Backend-Änderungen — kein Frontend-Umbau nötig.

### Warum das wichtig ist

Nächste Woche ist Kundentermin (Tierlabor Uni Essen / getmatic). Das Dashboard ist das erste was der Kunde sieht. Falsche Zähler und leere Dauer-Felder wirken unprofessionell und wecken Zweifel an der Datenqualität.

---

## Aktueller Zustand

### Relevante bestehende Struktur

- `app.py` auf Pi — `api_dashboard_stats()` (ca. Zeile 1605): berechnet `today_count` und `last_today`
- `app.py` auf Pi — `_extract_protocol_fields()` (ca. Zeile 1468): extrahiert `duration` aus `raw_data` via Regex
- `templates/dashboard.html` — zeigt `d.today` als "Chargen heute" und `p.duration || '—'` in Tabelle
- DB `protocols`-Tabelle: Timestamps gespeichert als ISO-String mit `T`-Trenner, z.B. `2026-06-10T17:38:00.500569`
- Raw-Data-Format (Belimed PST / MST): enthält `Programmstart : DD.MM.YYYY / HH:MM` und `MM:SS Programm Ende`

### Lücken oder Probleme, die adressiert werden

**Bug 1 — Chargen heute = 0 (Root Cause: ASCII-Sortierung):**
- DB speichert Timestamps als `2026-06-10T17:38:00.500569` (ISO 8601, `T`-Trenner)
- Query prüft: `timestamp <= '2026-06-10 23:59:59'` (Space-Trenner)
- SQLite String-Vergleich: `T` (ASCII 84) > ` ` (Space, ASCII 32)
- Ergebnis: `'2026-06-10T17:38...'` > `'2026-06-10 23:59:59'` → obere Schranke schlägt fehl → `today_count = 0`
- Gleiches Problem in der `last_today`-Abfrage (letzte Uhrzeit "Letzte um X Uhr")

**Bug 2 — Dauer = "—" (Root Cause: falsche Regex-Muster):**
- `_START_RE` sucht nach: `Beginn\s*...\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})` — ISO-Datumsformat
- `_END_RE` sucht nach: `Ende\s*...\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})` — ISO-Datumsformat
- Tatsächliches Protokollformat: `Programmstart : 10.06.2026 / 17:37` (Deutsch) und `33:29 Programm Ende` (verstrichene Minuten:Sekunden seit Programmstart)
- Beide Regexes matchen nie → `duration` bleibt immer leer

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

- `app.py`: `today_count`- und `last_today`-Query auf `date(timestamp) = today_str` umstellen
- `app.py`: `_extract_protocol_fields()` — neue Regex für `(\d+):(\d+)\s+Programm\s+Ende` → Dauer direkt aus verstrichener Zeit ableiten

### Neue Dateien erstellen

Keine.

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|---|---|
| `app.py` (Pi) | `today_count`-Query: `date(timestamp) = ?` statt `>= AND <=`; `last_today`-Query analog; neuer Regex `_PROG_ENDE_RE` + Dauer-Extraktion in `_extract_protocol_fields()` |

### Zu löschende Dateien

Keine.

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **`date(timestamp) = today_str` statt `>= / <=`**: SQLite's `date()`-Funktion normalisiert beide Timestamp-Formate (`T`- und Space-Trenner) korrekt. Robust gegen alle ISO-8601-Varianten, kein Risiko neuer Randfälle.

2. **Dauer aus `Programm Ende`-Zeitstempel, nicht aus Start+End berechnen**: Das Protokoll enthält `MM:SS Programm Ende` als verstrichene Zeit seit Programmstart — das ist exakt die Zyklusdauer. Kein Parsen des Datums nötig, kein Risiko von Zeitzonenfehlern. Direktester Weg.

3. **Ausgabe-Format `HH:MM:SS`**: Konsistent mit dem bestehenden Fallback-Format in `_extract_protocol_fields()` (Zeile 1489). Bei typischen Sterilisationszyklen (20–60 min) ergibt das z.B. `00:33:29`.

4. **`_START_RE` / `_END_RE` bleiben erhalten**: Die alten Regexes werden nicht gelöscht — sie könnten für andere Maschinenprotokolle noch relevant sein. Der neue `_PROG_ENDE_RE` hat Vorrang wenn er matcht, der alte Pfad bleibt als Fallback.

### Betrachtete Alternativen

- **`timestamp >= X AND timestamp < X+1day`**: Würde auch funktionieren (`2026-06-10T...` < `2026-06-11`), aber `date()` ist semantisch klarer.
- **Dauer aus `Programmstart` + DB-Timestamp berechnen**: Ungenauer (DB-Timestamp = TCP-Eingang, nicht Programmende), aufwändigeres Parsing des deutschen Datumsformats.
- **Frontend-Fix (JS)**: Datum-Vergleich im Browser — falscher Ort, Problem liegt im Backend-Query.

### Offene Fragen

Keine — Root Causes sind eindeutig identifiziert.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: Bug 1 fixen — today_count-Query in `api_dashboard_stats()`

In `app.py` die `today_count`- und `last_today`-Queries umstellen.

**Aktueller Code (ca. Zeile 1624):**
```python
today_count = db.execute(
    "SELECT COUNT(*) FROM protocols WHERE timestamp >= ? AND timestamp <= ?",
    (today_str + " 00:00:00", today_str + " 23:59:59")
).fetchone()[0]
```

**Neuer Code:**
```python
today_count = db.execute(
    "SELECT COUNT(*) FROM protocols WHERE date(timestamp) = ?",
    (today_str,)
).fetchone()[0]
```

**Aktueller Code `last_today` (ca. Zeile 1636):**
```python
last_today = db.execute(
    "SELECT timestamp FROM protocols WHERE timestamp >= ? AND timestamp <= ? ORDER BY timestamp DESC LIMIT 1",
    (today_str + " 00:00:00", today_str + " 23:59:59")
).fetchone()
```

**Neuer Code:**
```python
last_today = db.execute(
    "SELECT timestamp FROM protocols WHERE date(timestamp) = ? ORDER BY timestamp DESC LIMIT 1",
    (today_str,)
).fetchone()
```

**Aktionen:**
- `app.py` via SSH-Python-Script patchen (beide Queries in einem Durchgang)
- Verifizieren: `curl http://localhost:5000/api/dashboard/stats` → `today` muss > 0 sein

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/app.py`

---

### Schritt 2: Bug 2 fixen — Dauer-Extraktion in `_extract_protocol_fields()`

Neuen Regex `_PROG_ENDE_RE` definieren und in `_extract_protocol_fields()` einbauen.

**Neuer Regex** (direkt nach den bestehenden `_START_RE` / `_END_RE` Definitionen, ca. Zeile 1474):
```python
_PROG_ENDE_RE = _re.compile(r'^\s*(\d+):(\d+)\s+Programm\s+Ende', _re.MULTILINE | _re.IGNORECASE)
```

**Neue Dauer-Logik** in `_extract_protocol_fields()` — ersetze den bestehenden `try/except`-Block für `duration` (ca. Zeile 1478–1491):

```python
duration = ''
try:
    # Primär: verstrichene Zeit aus "MM:SS Programm Ende"
    em = _PROG_ENDE_RE.search(raw)
    if em:
        total_sec = int(em.group(1)) * 60 + int(em.group(2))
        duration = '{:02d}:{:02d}:{:02d}'.format(
            total_sec // 3600,
            (total_sec % 3600) // 60,
            total_sec % 60
        )
    else:
        # Fallback: ISO-Timestamps Beginn/Ende (älteres Format)
        sm = _START_RE.search(raw)
        em2 = _END_RE.search(raw)
        if sm and em2:
            from datetime import datetime as _dt
            start_dt = _dt.strptime(sm.group(1), '%Y-%m-%d %H:%M')
            end_dt   = _dt.strptime(em2.group(1), '%Y-%m-%d %H:%M')
            delta = int((end_dt - start_dt).total_seconds())
            if delta > 0:
                duration = '{:02d}:{:02d}:{:02d}'.format(
                    delta // 3600, (delta % 3600) // 60, delta % 60)
except Exception:
    pass
```

**Aktionen:**
- `_PROG_ENDE_RE`-Definition nach `_END_RE` einfügen (ca. Zeile 1474)
- `duration`-Block in `_extract_protocol_fields()` ersetzen
- Verifizieren: `curl 'http://localhost:5000/api/protocols?per_page=5'` → `duration`-Felder müssen Werte wie `00:33:29` enthalten

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/app.py`

---

### Schritt 3: Deploy und Service-Restart

**Aktionen:**
- Service neu starten: `sudo systemctl restart docucontrol.service`
- Status prüfen: `systemctl is-active docucontrol.service`

---

### Schritt 4: Verifikation beider Fixes

**Aktionen:**
- `curl http://localhost:5000/api/dashboard/stats` → `today` > 0, `today_last_time` gesetzt
- `curl 'http://localhost:5000/api/protocols?per_page=3'` → `duration` enthält `HH:MM:SS`-Werte
- Browser `http://192.168.0.171/` → "Chargen heute"-Karte zeigt korrekte Zahl, Dauer-Spalte zeigt Werte

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- `templates/dashboard.html` — rendert `d.today`, `d.today_last_time`, `p.duration` — kein Änderungsbedarf
- `database.py` — `get_today_count()` hat möglicherweise denselben Bug (wird aber nicht im Dashboard genutzt, sondern nur in Legacy-Routen)

### Nötige Updates für Konsistenz

- `database.py`: `get_today_count()` prüfen ob selber Bug — falls ja, analog fixen (separater Schritt, nicht kritisch für Dashboard)
- `CLAUDE.md`: keine Änderung nötig (API-Endpunkte ändern sich nicht)

### Auswirkungen auf bestehende Workflows

- Bestehende Protokollliste: `duration` wird jetzt befüllt — keine Breaking Change, nur additive Daten
- PDF-Generierung: nutzt `cycle_duration` aus `protocol_parser.py`, nicht `_extract_protocol_fields()` — kein Einfluss

---

## Validierungs-Checkliste

- [ ] `GET /api/dashboard/stats` → `today` > 0 (entspricht Anzahl heutiger DB-Einträge)
- [ ] `GET /api/dashboard/stats` → `today_last_time` zeigt korrekte Uhrzeit des letzten Protokolls
- [ ] `GET /api/protocols?per_page=5` → alle Einträge haben `duration`-Wert im Format `HH:MM:SS`
- [ ] Dashboard-Karte "Chargen heute" zeigt korrekte Zahl (nicht 0)
- [ ] Dauer-Spalte in Protokollliste zeigt z.B. `00:33:29` statt `—`
- [ ] Service nach Restart `active`

---

## Erfolgskriterien

1. "Chargen heute"-Karte zeigt die korrekte Anzahl heutiger Protokolle (verifiziert gegen DB-Einträge)
2. Dauer-Spalte zeigt für alle Protokolle mit `Programm Ende`-Zeile eine Laufzeit im Format `HH:MM:SS`
3. Service startet sauber durch, keine Python-Fehler im Log

---

## Notizen

- `get_today_count()` in `database.py` (genutzt in Legacy-Routen `/status`, `/api/status`) hat wahrscheinlich denselben Timestamp-Bug. Nicht kritisch für den Kundentermin, aber sollte zeitnah gefixt werden.
- Dauer-Werte für bestehende Protokolle (vor diesem Fix) werden dynamisch neu berechnet — da `_extract_protocol_fields()` live aus `raw_data` liest, gibt es kein Daten-Migrationsschritt.
- Typische Zyklusdauer Instrumente 134°C: ~33–40 min → Anzeige `00:33:29` bis `00:40:xx`. Plausibilitätscheck beim Validieren.

---

## Implementierungsnotizen

**Implementiert:** 2026-06-10

### Zusammenfassung

Alle vier Änderungen via SSH-Python-Skript in einem Durchgang angewendet: (1) `today_count`-Query auf `date(timestamp) = ?`, (2) `last_today`-Query analog, (3) `_PROG_ENDE_RE` nach `_END_RE` eingefügt, (4) Duration-Block mit neuem primären Pfad über `_PROG_ENDE_RE`.

### Abweichungen vom Plan

Keine.

### Aufgetretene Probleme

Keine. Verifikation: `today = 3`, `today_last_time = "17:38"`, alle Protokolle zeigen `duration = "00:33:29"`.
