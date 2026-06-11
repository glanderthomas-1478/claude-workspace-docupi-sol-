# Plan: Skalierbarkeit bei großen Datenmengen — DB-Spalten + Server-seitige Paginierung

**Erstellt:** 2026-06-11
**Status:** Implementiert
**Anforderung:** System auf 10.000+ Protokolle skalieren: echte SQL-Paginierung auf Dashboard und Dateimanager, kein vollständiges Laden aller Zeilen in Python

---

## Überblick

### Was dieser Plan erreicht

Die `api_protocols`-Route lädt aktuell **alle** Protokolle aus der DB, filtert und paginiert dann in Python. Bei 10.000 Einträgen à ~3 KB raw_data wären das 30 MB pro Request — alle 30 Sekunden durch den Auto-Refresh. Dieser Plan fügt `charge_nr_int` und `program` als echte DB-Spalten hinzu, stellt `api_protocols` auf SQL-Paginierung mit `LIMIT/OFFSET` um und ergänzt im Dateimanager eine Blätter-Steuerung (50 Dateien pro Seite).

### Warum das wichtig ist

Das Tierlabor Uni Essen läuft die Maschine täglich — nach 2–3 Jahren kommen schnell 5.000–10.000 Chargen zusammen. Das Dashboard wird alle 30 s neu geladen; ein vollständiger DB-Scan würde dann den Pi blockieren und den Browser einfrieren. Performantes Handling ist Grundvoraussetzung für den produktiven Dauerbetrieb.

---

## Aktueller Zustand

### Relevante bestehende Struktur

| Datei | Relevanz |
|---|---|
| `app.py` (Pi: `/home/docucontrol/docupi/app.py`) | `api_protocols`-Route, `_extract_protocol_fields`, DB-Insert |
| `src/docucontrol/templates/dashboard.html` | Tabelle + Pager (Frontend fertig, API ist Bottleneck) |
| `src/docucontrol/templates/filemanager.html` | Interne Dateiliste — hardcoded `per_page=200`, kein Pager |
| DB: `data/docupi.db` | Tabelle `protocols`: `id, timestamp, device_name, raw_data, pdf_path, pdf_filename, file_size, status` |

### Lücken oder Probleme, die adressiert werden

1. **API lädt alles:** `SELECT ... FROM protocols` ohne LIMIT, dann Python-Loop über alle Zeilen → O(n) Speicher und CPU pro Request.
2. **Charge-Nr. und Programm nur in raw_data:** Regex-Extraktion in Python verhindert SQL-Filter → kein Index nutzbar.
3. **Dateimanager kein Pager:** `per_page=200` hartcodiert, ab Zeile 201 werden Einträge still abgeschnitten.
4. **Auto-Refresh alle 30 s:** Ohne SQL-Pagination steigt die Last mit der DB-Größe linear.

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

- DB-Migration: Spalten `charge_nr_int INTEGER` und `program TEXT` zur `protocols`-Tabelle hinzufügen, aus `raw_data` vorausfüllen
- Insert-Logik: beim Speichern neuer Protokolle `charge_nr_int` und `program` direkt schreiben
- `api_protocols`: Umstellung auf echte SQL-Paginierung (`LIMIT/OFFSET`), Charge-Nr. und Programm-Filter per SQL
- `filemanager.html`: Paginierung für interne PDF-Liste (50/Seite, Mini-Pager)
- Migrations-Script als einmaliges Werkzeug auf dem Pi

### Neue Dateien erstellen

| Dateipfad | Zweck |
|---|---|
| `scripts/migrate_add_charge_program_cols.py` | Einmalig auf Pi ausführen: fügt Spalten hinzu, befüllt sie aus raw_data |

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|---|---|
| `app.py` (Pi) | `api_protocols` → SQL LIMIT/OFFSET; neue Spalten in WHERE; Insert-Hook erweitern |
| `src/docucontrol/templates/filemanager.html` | `loadInternalFiles()` → Paginierung + Mini-Pager |

### Zu löschende Dateien

Keine.

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **Neue DB-Spalten statt View oder In-Memory-Cache:** Spalten können indiziert werden, sind persistent, erfordern kein zusätzliches Caching-System. SQLite ALTER TABLE ist sicher bei laufendem Service.
2. **`charge_nr_int INTEGER` (nicht TEXT):** Ermöglicht `WHERE charge_nr_int BETWEEN ? AND ?` und `ORDER BY charge_nr_int` — kein String-Vergleich nötig.
3. **`program TEXT` (bis 60 Zeichen):** Ermöglicht `WHERE program = ?` direkt in SQL; der gleiche Regex wie bisher.
4. **Dauer (`duration`) bleibt in Python berechnet:** Zu komplex für reines SQL; wird nur für angezeigte Seite berechnet, nicht für alle Zeilen.
5. **`COUNT(*)` für Gesamtanzahl:** Separate COUNT-Query vor der Datenseite — schnell mit Index, vermeidet volles Laden.
6. **Dashboard: per_page bleibt 20** — gut lesbar, kein Änderungsbedarf am Frontend.
7. **Dateimanager: per_page = 50** — kompaktere Tabelle, sinnvollere Seitengröße für Dateiverwaltung.
8. **Kein Volltext-Scan mehr für charge_nr/program nach Migration** — Python-Filter in `api_protocols` werden entfernt; SQL übernimmt alles.

### Betrachtete Alternativen

- **Nur LIMIT/OFFSET ohne neue Spalten:** Würde charge_nr- und program-Filter nicht in SQL lösen → bei aktiven Filtern weiterhin voller Scan. Unvollständige Lösung.
- **Separate Indextabelle / FTS5:** Overengineering für diesen Use-Case; einfache Spalten reichen.
- **Infinite Scroll statt Pager im Dateimanager:** Komplexer, schlechter für Keyboard-Navigation. Klassischer Pager passt besser zum bestehenden Design.

### Offene Fragen

Keine — alle Entscheidungen sind mit vorhandener Architektur vereinbar.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: Migrations-Script erstellen

Script läuft einmal auf dem Pi, ist idempotent (prüft ob Spalten bereits existieren).

**Aktionen:**

- Script `scripts/migrate_add_charge_program_cols.py` erstellen
- Öffnet `/home/docucontrol/docupi/data/docupi.db`
- Prüft per `PRAGMA table_info(protocols)` ob `charge_nr_int` und `program` bereits existieren
- Wenn nicht: `ALTER TABLE protocols ADD COLUMN charge_nr_int INTEGER` und `ADD COLUMN program TEXT`
- Iteriert über alle Zeilen, extrahiert charge_nr und program per denselben Regexes wie `_extract_protocol_fields`
- `UPDATE protocols SET charge_nr_int=?, program=? WHERE id=?` für jede Zeile
- Erstellt Index: `CREATE INDEX IF NOT EXISTS idx_charge_nr_int ON protocols(charge_nr_int)` und `idx_program ON protocols(program)`
- Gibt Zusammenfassung aus: wie viele Zeilen aktualisiert, wie viele charge_nr null (kein Treffer)

**Betroffene Dateien:**

- `scripts/migrate_add_charge_program_cols.py` (neu)

---

### Schritt 2: `app.py` — Insert-Logik erweitern

Beim Speichern neuer Protokolle `charge_nr_int` und `program` direkt befüllen. Suche nach der DB-INSERT-Stelle in `app.py` (vermutlich im TCP-Capture-Handler oder `store_protocol()`-Funktion).

**Aktionen:**

- Die Funktion finden, die `INSERT INTO protocols` ausführt (grep nach `INSERT INTO protocols`)
- Nach dem Insert oder im INSERT selbst `charge_nr_int` und `program` mitschreiben:
  ```python
  cm = _CHARGE_RE.search(raw_data or '')
  charge_nr_int = int(cm.group(1)) if cm else None
  pm = _PROG_RE.search(raw_data or '')
  program_val = pm.group(1).strip()[:60] if pm else None
  ```
- INSERT-Statement um die zwei Felder erweitern

**Betroffene Dateien:**

- `app.py` (Pi: `/home/docucontrol/docupi/app.py`)

---

### Schritt 3: `api_protocols` auf SQL-Paginierung umstellen

Kompletter Umbau der `api_protocols`-Route: statt alle Rows laden + Python-Filter → SQL WHERE + SQL LIMIT/OFFSET.

**Aktionen:**

Die aktuelle Logik:
```python
rows = db.execute(sql, params).fetchall()   # lädt ALLES
result = []
for row in rows:
    rec = _extract_protocol_fields(row)
    if charge_nr_filter ... : continue      # Python-Filter
    result.append(rec)
total = len(result)
page_data = result[start:start+per_page]   # Python-Slice
```

Neue Logik:
```python
# 1. WHERE-Klauseln bauen (jetzt auch charge_nr + program in SQL)
if charge_from.isdigit():
    where_clauses.append("charge_nr_int >= ?")
    params.append(int(charge_from))
if charge_to.isdigit():
    where_clauses.append("charge_nr_int <= ?")
    params.append(int(charge_to))
if program_f:
    where_clauses.append("program = ?")
    params.append(program_f)

where = ('WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''

# 2. Total per COUNT(*) — schnell, kein Datenladen
total_row = db.execute(f"SELECT COUNT(*) FROM protocols {where}", params).fetchone()
total = total_row[0]

# 3. Sortierung
order_col = 'charge_nr_int' if sort_by == 'charge_nr' else 'timestamp'
order_dir = 'DESC' if sort_dir == 'desc' else 'ASC'

# 4. Nur eine Seite laden
offset = (page - 1) * per_page
sql = f"SELECT id, timestamp, device_name, raw_data, pdf_path, pdf_filename, file_size, status FROM protocols {where} ORDER BY {order_col} {order_dir} LIMIT ? OFFSET ?"
rows = db.execute(sql, params + [per_page, offset]).fetchall()

# 5. Felder nur für diese Seite extrahieren
page_data = [_extract_protocol_fields(row) for row in rows]
for p in page_data:
    del p['charge_nr_num']
```

- Python-Charge/Program-Filter-Loop entfernen
- `result.sort(...)` für charge_nr entfernen (jetzt in SQL)
- `result.reverse()` für asc entfernen (jetzt in SQL ORDER BY ... ASC)

**Betroffene Dateien:**

- `app.py` (Pi)

---

### Schritt 4: `api_protocols/programs` prüfen

Dieser Endpunkt lädt alle raw_data für distinct programme — mit neuer `program`-Spalte kann er vereinfacht werden.

**Aktionen:**

- Aktuell: `SELECT raw_data FROM protocols WHERE raw_data IS NOT NULL` → Python-Regex → distinct set
- Neu: `SELECT DISTINCT program FROM protocols WHERE program IS NOT NULL ORDER BY program`
- Viel schneller, kein raw_data laden

**Betroffene Dateien:**

- `app.py` (Pi)

---

### Schritt 5: Dateimanager — Paginierung einbauen

`filemanager.html` — `loadInternalFiles()` bekommt Seitenstate und einen Mini-Pager analog zum Dashboard.

**Aktionen:**

- Variable `intPage = 1` als Modulvariable einführen
- `loadInternalFiles(page)` nimmt Page-Parameter, ruft `/api/protocols?per_page=50&page=N&sort_by=timestamp&sort_dir=desc`
- Unterhalb der internen Dateitabelle: `<div class="table-foot">` mit `<span id="intCountInfo">` und `<div class="pager" id="intPager"></div>`
- `renderIntPager(page, pages)` — identische Logik wie `renderPager()` im Dashboard, aber ruft `goIntPage(p)` auf
- `window.goIntPage = function(p) { loadInternalFiles(p); }`
- Bei leerem Ergebnis nach Löschen: Seite auf `Math.max(1, intPage - 1)` zurückspringen

**Betroffene Dateien:**

- `src/docucontrol/templates/filemanager.html`

---

### Schritt 6: Migration auf dem Pi ausführen

**Aktionen:**

- `scripts/migrate_add_charge_program_cols.py` auf den Pi kopieren
- Script ausführen (Service muss nicht gestoppt werden — SQLite erlaubt gleichzeitige Reads, ALTER TABLE sperrt kurz)
- Output prüfen: alle Zeilen aktualisiert, Indizes erstellt
- `curl http://localhost:5000/api/protocols?charge_from=21720` testen — liefert jetzt Ergebnis via SQL-Filter
- Service neu starten (damit neuer Insert-Code aktiv ist)

**Betroffene Dateien:**

- `scripts/migrate_add_charge_program_cols.py`

---

### Schritt 7: Templates deployen

**Aktionen:**

- `filemanager.html` mit `deploy_docucontrol_design.sh` auf Pi deployen
- Oder manuell: `scp src/docucontrol/templates/filemanager.html docucontrol@192.168.0.171:/home/docucontrol/docupi/templates/`
- Browser-Cache leeren (Shift+F5), Dateimanager öffnen
- Paginierung prüfen: zeigt erste 50 Dateien, Pager erscheint sobald > 50

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- `dashboard.html` — ruft `api_protocols` auf (profitiert direkt, kein Frontend-Änderungsbedarf)
- `filemanager.html` — ruft `api_protocols?per_page=200` auf (wird geändert)
- `app_additions.py` — enthält bereits den `api_protocols`-Endpunkt-Stub (ggf. doppelter Code, prüfen)

### Nötige Updates für Konsistenz

- `CLAUDE.md`: neue DB-Spalten `charge_nr_int`, `program` in der Architektur-Beschreibung ergänzen
- `context/current-data.md`: DB-Schema-Eintrag aktualisieren
- `context/strategy.md`: Skalierbarkeits-Fix als erledigt markieren nach Deployment

### Auswirkungen auf bestehende Workflows

- `api/protocols/bulk-delete` und `bulk-copy-usb`: keine Änderung nötig (nutzen nur `id`)
- `api/dashboard/stats`: keine Änderung (eigene Query)
- Datensammlermodus: nicht betroffen (schreibt keine DB-Einträge)

---

## Validierungs-Checkliste

- [ ] Migrations-Script läuft durch, gibt `N Zeilen aktualisiert` aus, keine Fehler
- [ ] `PRAGMA table_info(protocols)` zeigt Spalten `charge_nr_int` und `program`
- [ ] `GET /api/protocols?per_page=5&page=2` liefert korrekt die Zeilen 6–10
- [ ] `GET /api/protocols?charge_from=21720&charge_to=21725` filtert korrekt via SQL
- [ ] `GET /api/protocols?program=Instrumente+134+°C` filtert korrekt
- [ ] `GET /api/protocols/programs` liefert distinct Programme (schnell, kein raw_data-Scan)
- [ ] Dashboard: Pager zeigt korrekte Seitenzahlen, Blättern funktioniert
- [ ] Dateimanager: Pager erscheint bei >50 Einträgen, Blättern funktioniert
- [ ] Neues Protokoll via send_test_charges.py einspielen → `charge_nr_int` und `program` in DB gesetzt
- [ ] Auto-Refresh (30 s) im Dashboard: keine spürbaren Verzögerungen
- [ ] CLAUDE.md aktualisiert

---

## Erfolgskriterien

Die Implementierung ist abgeschlossen, wenn:

1. `api_protocols` ohne Filter lädt genau `per_page` Zeilen aus der DB (verifizierbar mit `EXPLAIN QUERY PLAN` oder Logs)
2. Bei 10.000 simulierten Zeilen antwortet die API unter 200 ms (statt mehrerer Sekunden)
3. Dateimanager zeigt 50 Einträge pro Seite mit funktionierendem Pager — keine Einträge werden still abgeschnitten

---

## Notizen

- **Warum kein `LIMIT` beim Sortieren nach `charge_nr`?** Aktuell wird `charge_nr` per Python-Sort nach dem Laden gemacht. Mit der neuen Spalte `charge_nr_int` übernimmt SQLite das — der Index macht `ORDER BY charge_nr_int` schnell.
- **Kann `charge_nr_int` NULL sein?** Ja, bei beschädigten/leeren raw_data-Einträgen. `WHERE charge_nr_int BETWEEN ? AND ?` schließt NULLs automatisch aus — kein Problem.
- **USB-Dateiliste:** Nicht paginiert (lädt von Filesystem, nicht DB). USB hat in der Praxis deutlich weniger Dateien als die DB. Kein Handlungsbedarf jetzt.
- **Captures-Liste im Dateimanager:** Ebenfalls nicht paginiert. Kann in einem Folge-Plan bei Bedarf analog umgesetzt werden.
- **Langfristig (~50.000 Protokolle):** SQLite kommt mit den Indizes problemlos bis in den Millionen-Bereich. Kein Datenbankwechsel nötig.

---

## Implementierungsnotizen

**Implementiert:** 2026-06-11

### Zusammenfassung

- Migrations-Script `scripts/migrate_add_charge_program_cols.py` erstellt und auf Pi ausgeführt — alle 11 Protokolle migriert (0 ohne Charge-Nr., 0 ohne Programm)
- `database.py` überarbeitet: Regexes `_CHARGE_RE`/`_PROG_RE` auf Modulebene, `save_protocol()` schreibt `charge_nr_int` + `program` bei jedem Insert; `init_db()` enthält neue Spalten + Indizes
- `app.py` — `api_protocols`: vollständige SQL-Paginierung mit COUNT(*)/LIMIT/OFFSET, Charge-Nr. und Programm-Filter per SQL WHERE (kein Python-Loop mehr)
- `app.py` — `api_protocols_programs`: vereinfacht zu `SELECT DISTINCT program`
- `filemanager.html`: Mini-Pager (50/Seite), `intPage`-State, `renderIntPager()`, `goIntPage()`, Lede-Untertitel
- Service neugestartet, Insert-Test mit CH021730 bestätigt — charge_nr_int + program korrekt gesetzt
- CLAUDE.md, context/current-data.md, context/strategy.md aktualisiert

### Abweichungen vom Plan

- `database.py` wurde als neue Datei unter `src/docucontrol/database.py` abgelegt und per SCP deployed (kein separates Patch-Script nötig)
- Patch-Script `scripts/_patch_app_protocols.py` als Hilfswerkzeug für die app.py-Änderungen erstellt und auf Pi ausgeführt

### Aufgetretene Probleme

- Heredoc-Escaping via SSH zu komplex für mehrzeilige Python-Strings → Lösung: Script lokal schreiben, per SCP deployen, auf Pi ausführen
