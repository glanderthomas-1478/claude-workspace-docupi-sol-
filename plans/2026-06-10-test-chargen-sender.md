# Plan: Test-Chargen-Sender — 10 simulierte Belimed-Protokolle via TCP

**Erstellt:** 2026-06-10
**Status:** Implementiert
**Anforderung:** Python-Skript das 10 realistische Belimed-Protokolle im 30-Sekunden-Takt via TCP/9100 an den DocuControl-Pi sendet — mit wechselnden Chargennummern, Programmnamen und Laufzeiten.

---

## Überblick

### Was dieser Plan erreicht

Ein lokales Python-Skript (`scripts/send_test_charges.py`) generiert 10 Belimed-Chargenprotokolle im exakten TCP-Sendeformat des Originalgeräts (UTF-16LE mit BOM) und schickt sie einzeln im 30-Sekunden-Abstand an Port 9100. Jede Charge hat eine eindeutige Chargennummer (ab 021720), wechselnden Programmnamen und variierende Laufzeiten, sodass Dashboard, Tabelle und PDF-Generierung realistische Daten zeigen.

### Warum das wichtig ist

Kundentermin Tierlabor Uni Essen steht bevor. Das Dashboard muss mit mehreren verschiedenen Chargen gefüllt sein — unterschiedliche Programme, verschiedene Laufzeiten, korrekte "Chargen heute"-Zählung und befüllte Dauer-Spalte. Manuelles Eintippen oder Warten auf echte Maschinendaten dauert zu lang.

---

## Aktueller Zustand

### Relevante bestehende Struktur

- `scripts/` — bestehende Hilfsskripte (deploy, render_konzept_pdf, saia_test_toolkit)
- Pi `tcp_print_capture.py` — TCP-Listener auf Port 9100, dekodiert eingehende Bytes
- Pi `data/raw_captures/` — 20+ Captures vorhanden, letzter Test: CH021719 (2026-06-10)
- Protokollformat bekannt: UTF-16LE mit BOM (`\xff\xfe`), Belimed-Chargen-Dokumentation
- Charge-Regex in `app.py`: `Laufende\s+Nr\.?\s*:\s*0*(\d+)`
- Dauer-Regex: `^\s*(\d+):(\d+)\s+Programm\s+Ende`
- Decoder in `tcp_print_capture.py`: prüft UTF-16LE BOM zuerst, dann UTF-8 Fallback

### Lücken oder Probleme, die adressiert werden

- Kein Sender-Skript vorhanden — bisherige Tests wurden ad-hoc gesendet
- Ohne Testdaten zeigt das Dashboard "0 Chargen heute" und leere Dauer-Spalten vor dem Kundentermin
- Manuell Chargen nachbauen ist fehleranfällig

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

- Neues Skript `scripts/send_test_charges.py` erstellen
- Kein Pi-seitiger Code ändert sich — das Skript nutzt den bestehenden TCP/9100-Listener

### Neue Dateien erstellen

| Dateipfad | Zweck |
|---|---|
| `scripts/send_test_charges.py` | Sendet 10 simulierte Chargenprotokolle im 30s-Takt an Pi Port 9100 |

### Zu ändernde Dateien

Keine.

### Zu löschende Dateien

Keine.

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **UTF-16LE mit BOM**: Das Skript kodiert den Text als `utf-16-le` und setzt den BOM `\xff\xfe` voran — exakt wie das Originalgerät. Der Decoder auf dem Pi erkennt das sofort, kein Fallback nötig.

2. **Startcharge 021720**: Letzte bekannte Charge CH021719 (Sammlermodus-Test). Das Skript beginnt bei 021720 und zählt hoch bis 021729.

3. **3 rotierende Programme**: 
   - `1: Instrumente 134°C` (4× — häufigster Typ, Laufzeit 30–38 min)
   - `3: Bowie Dick` (3× — Funktionstest, kürzere Laufzeit 18–22 min)
   - `2: Instrumente 121°C` (3× — alternativer Sterilzyklus, Laufzeit 38–46 min)
   
4. **Laufzeit-Variation**: `Programm Ende`-Zeitstempel wird pro Charge leicht variiert (±2–4 Minuten gegenüber Basisdauer). Die Phasentabelle bleibt für den jeweiligen Programm-Template fix — nur der Endzeit-Eintrag ändert sich. Das ist realistisch weil Aufwärmphase und Vakuumfraktionen stets ähnlich dauern.

5. **Programmstart-Zeitstempel**: Jede Charge bekommt `datetime.now()` zum Sendezeitpunkt. Die Chargen liegen 30s auseinander, also unterscheiden sich die Timestamps.

6. **Zieldaten im Protokoll**: Betreiber `Uniklinik Essen Tierlabor`, Abt. `AEMP`, Maschinentyp `PST 14-8-12 HS1`, Nr. `28441` (realistisch für PST-Baureihe). Damit wirken die Daten wie echte Protokolle vom Zielgerät.

7. **Keine Verbindung halten**: Pro Charge: `connect → send → close`. Der Listener erwartet genau dieses Verhalten (TCP-Session endet = Job abgeschlossen).

8. **Trockenlauf-Modus**: `--dry-run` Flag druckt die Protokolle auf stdout ohne zu senden — für Inspektion vor dem echten Test.

### Betrachtete Alternativen

- **Bestehende .bin-Datei kopieren und senden**: Würde immer dieselbe Charge senden (Charge-Nr., Datum fix). Nicht brauchbar.
- **Nur UTF-8 senden**: Würde funktionieren (Fallback-Decoder), aber nicht authentisch. Für Produktionstests besser das echte Format.
- **Laufzeiten komplett neu berechnen (alle Phasen-Timestamps skalieren)**: Überkomplex für den Zweck. Der Parser liest nur `Programm Ende` für die Dauer — nur dieser eine Wert muss variieren.

### Offene Fragen

Keine — Protokollformat vollständig bekannt, Ziel-IP und Port fix.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: Skript `scripts/send_test_charges.py` erstellen

Das Skript besteht aus drei Teilen: Protokoll-Templates, Generator-Funktion, Send-Loop.

**Protokoll-Templates (eine Funktion pro Programm):**

Jede Template-Funktion nimmt `charge_nr: int`, `start_dt: datetime`, `ende_mm: int`, `ende_ss: int` und gibt den Protokoll-Text zurück.

**Template 1 — `Instrumente 134°C`:**
```
Basis: Capture 20260610_173800_job0001.txt (CH021718)
Betreiber     : Uniklinik Essen Tierlabor
Abteilung     : AEMP
Maschinen-Typ : PST 14-8-12 HS1    Nr:28441
Laufende Nr.  : {charge_nr:06d}
Benutzer      : User
Programm      :  1: Instrumente 134°C
Sollwerte     : Anz. Fraktionen         9
                Sterilisierzeit    5.0min
                Sterilisiertemp.  134.2°C
                Trocknungszeit    17.0min
Programmstart : {start_dt.strftime('%d.%m.%Y / %H:%M')}
[... Phase-Tabelle wie in Capture, letzter Eintrag {ende_mm}:{ende_ss:02d} Programm Ende ...]
PROGRAMM KORREKT BEENDET
```
Basislaufzeit: 33 min (ende_mm=33), variiert ±3 min

**Template 2 — `Bowie Dick`:**
```
Programm      :  3: Bowie Dick
Sollwerte     : Sterilisierzeit    3.5min
                Sterilisiertemp.  134.2°C
                Trocknungszeit     5.0min
Basislaufzeit: 20 min (ende_mm=20), variiert ±2 min
Kürzere Phasentabelle (weniger Fraktionen)
```

**Template 3 — `Instrumente 121°C`:**
```
Programm      :  2: Instrumente 121°C
Sollwerte     : Anz. Fraktionen         3
                Sterilisierzeit   15.0min
                Sterilisiertemp.  121.0°C
                Trocknungszeit    20.0min
Basislaufzeit: 42 min (ende_mm=42), variiert ±4 min
```

**Generator-Funktion `build_protocol(i)`:**
```python
PROGRAMS = [
    (1, 'prog_instrumente_134', 33, 3),   # (index, func, base_min, variance)
    (2, 'prog_bowie_dick',      20, 2),
    (3, 'prog_instrumente_121', 42, 4),
]
rotation = [0,1,0,2,0,1,2,0,1,0]          # 10 Chargen: 4× Instr134, 3× BD, 3× Instr121
charge_nr = 21720 + i
prog_idx = rotation[i]
base_min, variance = PROGRAMS[prog_idx][2], PROGRAMS[prog_idx][3]
ende_mm = base_min + (i % (2*variance+1)) - variance   # deterministisch variiert
start_dt = datetime.now()
text = template_func(charge_nr, start_dt, ende_mm, 29)  # :29s fix
```

**Send-Loop:**
```python
for i in range(10):
    payload = build_protocol(i)
    raw = b'\xff\xfe' + payload.encode('utf-16-le')
    sock = socket.create_connection((HOST, PORT), timeout=10)
    sock.sendall(raw)
    sock.close()
    print(f"CH{21720+i} gesendet ({payload.count(chr(10))} Zeilen, {len(raw)} Bytes)")
    if i < 9:
        time.sleep(30)
```

**CLI-Interface:**
```
python3 scripts/send_test_charges.py [--host IP] [--count N] [--interval SECS] [--dry-run]
Defaults: host=192.168.0.171, count=10, interval=30
```

**Aktionen:**
- `scripts/send_test_charges.py` erstellen mit vollständigem Code aller drei Templates plus Loop
- Alle drei Template-Funktionen ausimplementieren (vollständiger Protokolltext, nicht nur Skeleton)

**Betroffene Dateien:**
- `scripts/send_test_charges.py` (neu)

---

### Schritt 2: Lokaler Dry-Run — Protokolle auf stdout prüfen

Vor dem echten Senden überprüfen ob die generierten Protokolle korrekt aussehen.

**Aktionen:**
- `python3 scripts/send_test_charges.py --dry-run` ausführen
- Ausgabe prüfen: Charge-Nr. 021720–021729 korrekt, Programme wechseln, `Programm Ende`-Zeile variiert, Datum stimmt

**Betroffene Dateien:**
- Nur Stdout-Ausgabe

---

### Schritt 3: Ersten Test mit 1 Charge senden

Einzelne Charge senden und Ende-to-Ende-Pipeline verifizieren.

**Aktionen:**
- `python3 scripts/send_test_charges.py --count 1` ausführen
- Auf Pi: `journalctl -u docucontrol.service -n 30` — Job soll erscheinen
- `curl -s http://192.168.0.171/api/protocols?per_page=1` — neue Charge in DB
- Browser `http://192.168.0.171/` — Dauer-Spalte zeigt Wert, nicht `—`

**Betroffene Dateien:**
- Keine

---

### Schritt 4: Alle 10 Chargen senden

Vollständigen Test durchführen.

**Aktionen:**
- `python3 scripts/send_test_charges.py` (läuft ~4:30 min)
- Fortschritt auf Stdout mitverfolgen
- Nach Abschluss: Browser-Reload — Dashboard zeigt 10 neue Chargen

**Betroffene Dateien:**
- Keine

---

### Schritt 5: Dashboard-Verifikation

**Aktionen:**
- `http://192.168.0.171/` im Browser öffnen
- "Chargen gesamt"-Karte: Zahl muss bei ~021729 liegen
- "Chargen heute"-Karte: muss 10 zeigen
- Protokolltabelle: alle 10 Chargen sichtbar, Dauer-Spalte befüllt, Programm-Icons wechseln
- Mindestens eine Charge über Print-Button drucken — PDF muss korrekt generiert werden

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- `Pi: tcp_print_capture.py` — empfängt die gesendeten Bytes, kein Änderungsbedarf
- `Pi: app.py` — `_extract_protocol_fields()` liest `Laufende Nr.` und `Programm Ende` aus den Captures
- `Pi: protocol_parser.py` — parst für PDF-Generierung; Template-Format muss kompatibel sein

### Nötige Updates für Konsistenz

- `CLAUDE.md`: Skript unter `scripts/` eintragen nach Implementierung

### Auswirkungen auf bestehende Workflows

- Keine — das Skript ist ein reines Testwerkzeug, ändert nichts am Pi
- Generierte Chargen landen in der echten DB → nach dem Test ggf. via Datei-Manager löschen falls gewünscht

---

## Validierungs-Checkliste

- [ ] `--dry-run` zeigt 10 Protokolle mit korrekten Charge-Nr. 021720–021729
- [ ] Programme wechseln: mind. 2 verschiedene in den 10 Chargen
- [ ] `Programm Ende`-Zeilen haben unterschiedliche Minutenwerte
- [ ] `Programmstart`-Datum entspricht dem heutigen Datum
- [ ] Einzeltest (--count 1): Charge erscheint in DB und Dashboard
- [ ] Volltest (10 Chargen): "Chargen heute" = 10
- [ ] Dauer-Spalte zeigt HH:MM:SS für alle 10 Chargen
- [ ] PDF-Generierung funktioniert für mindestens 1 Charge
- [ ] Service bleibt nach allen 10 Jobs stabil (kein Crash)

---

## Erfolgskriterien

1. Skript läuft lokal ohne Installation zusätzlicher Pakete (nur stdlib: `socket`, `time`, `datetime`, `argparse`)
2. Alle 10 Chargen erscheinen im Dashboard mit korrekter Dauer und wechselndem Programmname
3. "Chargen heute"-Karte zeigt 10 nach dem Test

---

## Notizen

- Skript läuft von localhost — kein SSH oder Remote-Ausführung nötig, direkter TCP-Connect zu 192.168.0.171:9100
- Nach dem Test: Testchargen bleiben in DB (realistischer für Demo). Können bei Bedarf über Datei-Manager bulk-gelöscht werden.
- Für künftige Nutzung: `--interval 7200` simuliert echten Produktionsbetrieb (~alle 2h eine Charge)
- `protocol_parser.py` ist auf `9-6-18 HS2`-Format kalibriert; Templates verwenden `PST 14-8-12 HS1` als Maschinentyp — der Parser kann scheitern und kein PDF generieren. Falls das passiert: Datensammlermodus prüfen oder Parser-Anpassung planen.

---

## Implementierungsnotizen

**Implementiert:** 2026-06-10

### Zusammenfassung

`scripts/send_test_charges.py` erstellt mit 3 vollständigen Protokoll-Templates (Instrumente 134°C, Bowie Dick, Instrumente 121°C), CLI-Interface (--host, --count, --interval, --dry-run, --start-charge) und UTF-16LE-Encoding mit BOM. 10 Chargen CH021720–CH021729 erfolgreich gesendet und verifiziert.

### Abweichungen vom Plan

Keine.

### Aufgetretene Probleme

Keine. Verifikation: `max_charge_nr=21729`, `today=14` (10 neue + 4 frühere), alle Dauer-Werte im Format `HH:MM:SS`, alle 3 Programme erkannt.
