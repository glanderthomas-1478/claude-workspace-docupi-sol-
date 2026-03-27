# Plan: WD390 Chargenprotokoll-Parser & PDF-Generierung

**Erstellt:** 2026-03-27
**Status:** Implementiert
**Anforderung:** Parser fuer WD390 HyperTerminal-Aufzeichnungen (.ht) und WD-spezifische PDF-Generierung

---

## Ueberblick

### Was dieser Plan erreicht

Aufbau eines Parsers, der WD390/WD290 Chargenprotokolle aus HyperTerminal-Dateien (.ht, UTF-16LE) und perspektivisch aus dem Live-RS232-Stream liest, in strukturierte Daten umwandelt und darueber professionelle PDF-Protokolle generiert. Damit wird DocuPi vom reinen Sterilisator-Tool zum universellen Felddiagnose-System fuer **beide** Maschinentypen (MST + RDG/WD).

### Warum das wichtig ist

Die WD390-Aufzeichnung beweist: Die ECU sendet Klartext ueber RS232 — kein komplexes Reverse Engineering noetig. Das ist der Durchbruch fuer den zweiten Kommunikationsweg (RS232 fuer WD/RDG). Damit kann DocuPi kuenftig Sterilisatoren UND Waschdesinfektoren dokumentieren, was den Markt verdoppelt.

---

## Aktueller Zustand

### Relevante bestehende Struktur

| Datei | Rolle |
|-------|-------|
| `src/pdf_generator.py` | SterilizationPDF-Klasse — nur MST-Datenmodell (Phasen mit P2/T2/T3, FO-Wert) |
| `src/chart_generator.py` | Trend-Chart mit Druck + 2x Temperatur — MST-spezifisch |
| `reference/WD390_4.ht` | Neue HyperTerminal-Aufzeichnung, UTF-16LE, vollstaendiges WD-Chargenprotokoll |
| `reference/BELIMED CHARGEN-DOKUMENTATION - BD Test.txt` | MST-Referenzprotokoll (Klartext) |
| `src/patches/patch_protocol_v2.py` | MST-Parser (parse_serial_protocol) |
| `src/patches/patch_real_data.py` | MST-spezifische Regex-Patterns |

### Luecken oder Probleme, die adressiert werden

1. **Kein WD/RDG-Parser vorhanden** — nur MST-Sterilisatoren werden unterstuetzt
2. **Datenmodell ist MST-spezifisch** — Phasen haben P2/T2/T3, WD hat Schritte mit nom/act-Paaren (Zeit, Temperatur, Dosierung, A0-Wert, Leitwert)
3. **PDF-Layout nur fuer MST** — KPI-Boxen zeigen FO-Wert, Sterilisiertemperatur; WD braucht A0-Wert, Thermodesinfektion, Dosiermengen
4. **Chart-Generator MST-only** — WD hat keinen Druckverlauf, sondern Temperatur-Stufen ueber Schritte
5. **Kein .ht-Datei-Reader** — HyperTerminal-Format (Binaer-Header + UTF-16LE) muss dekodiert werden

---

## Vorgeschlagene Aenderungen

### Zusammenfassung der Aenderungen

- Neuer WD-Protokoll-Parser (`wd_protocol_parser.py`) fuer .ht-Dateien und RS232-Klartext
- Neues einheitliches Datenmodell das MST und WD abdeckt
- WD-spezifische PDF-Generierung (eigene Klasse oder Modus in bestehender Klasse)
- WD-spezifischer Chart-Generator (Temperaturverlauf ueber Schritte)
- Parser-Tests mit der echten WD390-Aufzeichnung als Fixture

### Neue Dateien erstellen

| Dateipfad | Zweck |
|-----------|-------|
| `src/wd_protocol_parser.py` | Parser fuer WD/RDG Chargenprotokolle (HyperTerminal .ht + Klartext RS232) |
| `src/wd_pdf_generator.py` | PDF-Generierung fuer WD/RDG-Protokolle (A0-Wert, Dosierung, Thermodesinfektion) |
| `src/wd_chart_generator.py` | Temperatur-Stufen-Chart fuer WD-Prozessschritte |
| `tests/test_wd_parser.py` | Tests mit WD390_4.ht als Fixture |
| `tests/fixtures/wd390/WD390_4.ht` | Kopie der Referenzdatei als Test-Fixture |

### Zu aendernde Dateien

| Dateipfad | Aenderungen |
|-----------|-------------|
| `CLAUDE.md` | Neue Dateien in Workspace-Struktur dokumentieren, WD-Support erwaehnen |
| `context/current-data.md` | WD390-Parser-Status aktualisieren |
| `context/strategy.md` | RS232-Status aktualisieren (Protokoll entschluesselt!) |

### Zu loeschende Dateien

Keine.

---

## Design-Entscheidungen

### Getroffene Schluesselentscheidungen

1. **Separate Parser-Datei statt Erweiterung des MST-Parsers**: Die Protokollformate sind fundamental verschieden (MST: tabellarisch mit Zeitreihen; WD: schrittbasiert mit Soll/Ist-Paaren). Ein gemeinsamer Parser waere unnoetig komplex. Stattdessen: eigene Module, gemeinsames Output-Interface.

2. **Eigene PDF-Klasse `WashDisinfectorPDF`**: Das WD-Layout braucht andere KPI-Boxen (A0 statt FO, Dosiermengen, Leitwert), eine andere Datentabelle (Schritte mit nom/act statt Zeitreihe), und einen anderen Chart. Eine Subklasse oder separate Klasse ist sauberer als if/else-Verzweigungen.

3. **Datenmodell-Convention ueber gemeinsame Basisstruktur**: Beide Parser liefern ein Dict mit gemeinsamen Top-Level-Keys (`machine_type`, `machine_nr`, `operator`, `charge_nr`, `program_name`, `cycle_start`, `cycle_end`, `result`) plus typ-spezifischen Keys (`phases` fuer MST, `steps` fuer WD). Das ermoeglicht spaeter einen einheitlichen Dispatcher.

4. **HyperTerminal-Header ueberspringen, UTF-16LE ab Offset**: Der .ht-Header ist irrelevant (Drucker-/COM-Port-Config). Der Parser sucht den UTF-16LE-Text ab dem bekannten Marker "belimed" und dekodiert ab dort.

5. **Parser akzeptiert sowohl .ht-Dateien als auch Klartext**: Fuer den spateren Live-RS232-Betrieb muss derselbe Parser auch reinen Text verarbeiten koennen. Daher: `parse_wd_protocol(text: str)` als Kernfunktion, plus `parse_ht_file(path: str)` als Wrapper der die .ht-Dekodierung macht.

### Betrachtete Alternativen

- **MST-Parser erweitern**: Verworfen — zu unterschiedliche Formate, wuerde den bestehenden Code verkomplizieren
- **Generischer "MachineProtocol"-Parser mit Plugins**: Overkill fuer 2 Formate, YAGNI
- **Nur .ht-Dateien unterstuetzen, kein Live-RS232**: Kurzsichtig — die Textstruktur ist identisch, der Wrapper kostet fast nichts

### Offene Fragen

1. **WD-Chargenprotokoll: Ist das Format bei WD290 identisch?** — Die HyperTerminal-Datei stammt von einer WD390-4. Vor Feldtest mit WD290 sollte ein Vergleichsprotokoll aufgezeichnet werden. Annahme: gleiches Format, da gleiche ECU-Software (ECU Cadi).

2. **PDF-Seitenformat**: Querformat A4 wie MST, oder Hochformat? Die WD-Protokolle haben weniger Spalten als MST (kein P2/T2/T3-Zeitverlauf). Vorschlag: Querformat beibehalten fuer Konsistenz.

3. **Chart-Typ**: Temperaturverlauf als Stufendiagramm (step chart) oder Balkendiagramm? Vorschlag: Stufendiagramm (x-Achse = Schritte/Uhrzeit, y-Achse = Temperatur act min/max als Band).

---

## WD390-Datenmodell

Aus der Analyse der HyperTerminal-Aufzeichnung ergibt sich folgendes Datenmodell:

```python
wd_protocol_data = {
    # Gemeinsame Felder (kompatibel mit MST)
    "machine_type": "wd",                    # "mst" oder "wd"
    "machine_model": "WD390-4",
    "machine_nr": "2015488",
    "operator": "Muenchen Klinik_DE",
    "user": "User",
    "charge_nr": "4575",
    "program_name": "OP-Universal",
    "program_nr": "01",
    "program_version": "1.00",
    "cycle_start": "2026-03-27T11:08:39",
    "cycle_end": "2026-03-27T12:10:56",
    "rack": "0087003601",
    "result": "BESTANDEN",
    "result_detail": "program without failure",

    # WD-spezifisch
    "steps": [
        {
            "id": "1.1",
            "time": "11:08:58",
            "name": "precleaning",
            "name_display": "Precleaning",
            "params": {
                "step_time": {"nom": 180, "act": 181, "unit": "sec"},
                "temp_nominal": {"min": 0.0, "max": 45.0, "unit": "C"},
                "temp_actual": {"min": 15.6, "max": 26.3, "unit": "C"},
            }
        },
        {
            "id": "1.2",
            "time": "11:13:43",
            "name": "cleaning_1",
            "name_display": "Cleaning 1",
            "params": {
                "step_time": {"nom": 300, "act": 313, "unit": "sec"},
                "temp_nominal": {"min": 40.0, "max": 50.0, "unit": "C"},
                "temp_actual": {"min": 40.6, "max": 46.6, "unit": "C"},
                "dosing": {"nom": 162, "act": 162, "unit": "ml"},
            }
        },
        # ... weitere Schritte
        {
            "id": "3.2",
            "time": "11:51:19",
            "name": "thermal_disinfection",
            "name_display": "Thermal Disinfection",
            "params": {
                "conductivity": {"max": 50.0, "act": 1.8, "unit": "uS/cm"},
                "step_time": {"nom": 300, "act": 393, "unit": "sec"},
                "temp_nominal": {"min": 90.0, "max": 95.0, "unit": "C"},
                "temp_actual": {"min": 90.6, "max": 93.6, "unit": "C"},
                "a0_value": {"nom": 3200, "act": 3408, "unit": ""},
            }
        },
    ],

    # KPIs (aus den Schritten abgeleitet)
    "kpi": {
        "a0_value": {"nom": 3200, "act": 3408, "passed": True},
        "thermal_disinfection_temp": {"min": 90.6, "max": 93.6, "passed": True},
        "conductivity": {"max_allowed": 50.0, "act": 1.8, "passed": True},
        "total_duration_sec": 3737,
    }
}
```

---

## Protokollformat-Analyse (aus WD390_4.ht)

### Encoding
- Datei: HyperTerminal .ht-Format
- Binaer-Header: 1087 Bytes (COM-Port-Config, Druckereinstellungen — irrelevant)
- Nutztext: UTF-16LE ab Offset des Markers "belimed" (UTF-16LE kodiert)
- Zeilenstruktur: Feste Feldbreiten, keine expliziten Zeilenumbrueche im Stream — Felder durch Abstaende getrennt

### Kopfdaten-Felder (Reihenfolge wie im Protokoll)

```
belimed batch dokumentation                               [DATUM] [ZEIT]
page   N of  M
operation company  :[WERT]
machine type       :[WERT]
user               :[WERT]
machine no .       :[WERT]
charge no.         :[WERT]
program name       :[WERT]
program start      :[ZEIT] [DATUM]
progr.no./version  :[NR]/[VERSION]
program end        :[ZEIT] [DATUM]
rack               :[WERT]
program cycle      :[ERGEBNIS]
```

### Schritt-Felder (wiederholt pro Prozessschritt)

```
[SCHRITT-ID] [ZEIT]  [SCHRITTNAME]
[SCHRITT-ID]         step time              nom. [WERT] sec  act. [WERT] sec
[SCHRITT-ID]         temperature nominal    min. [WERT] °C   max. [WERT] °C
[SCHRITT-ID]         temperature actual     min. [WERT] °C   max. [WERT] °C
[SCHRITT-ID]                                nom. [WERT] ml   act. [WERT] ml     (optional: Dosierung)
[SCHRITT-ID]                                max. [WERT] µS/cm act. [WERT] µS/cm (optional: Leitwert)
[SCHRITT-ID]         A0 Value               nom. [WERT]      act. [WERT]        (optional)
```

### Regex-Patterns (Kernlogik)

```python
# Kopfdaten
RE_OPERATOR    = r"operation company\s*:(.+?)(?=machine type)"
RE_MACHINE     = r"machine type\s*:(\S+)"
RE_USER        = r"user\s*:(\S+)"
RE_MACHINE_NR  = r"machine no\s*\.\s*:(\d+)"
RE_CHARGE      = r"charge no\.\s*:(\d+)"
RE_PROGRAM     = r"program name\s*:(.+?)(?=program start)"
RE_START       = r"program start\s*:(\d{2}:\d{2}:\d{2}\s+\d{2}\.\d{2}\.\d{2})"
RE_END         = r"program end\s*:(\d{2}:\d{2}:\d{2}\s+\d{2}\.\d{2}\.\d{2})"
RE_VERSION     = r"progr\.no\./version\s*:(\d+)/(\d+\.\d+)"
RE_RACK        = r"rack\s*:(\w+)"
RE_RESULT      = r"program cycle\s*:(.+?)(?=\d+\.\d+\s+\d{2}:)"

# Schritt-Erkennung
RE_STEP_HEADER = r"(\d+\.\d+)\s+(\d{2}:\d{2}:\d{2})\s+(.+?)(?=\d+\.\d+|$)"
RE_STEP_TIME   = r"step time\s+nom\.\s*(\d+)\s*sec\s+act\.\s*(\d+)\s*sec"
RE_TEMP_NOM    = r"temperature nominal\s+min\.\s*([\d.]+)\s*..C\s+max\.\s*([\d.]+)\s*..C"
RE_TEMP_ACT    = r"temperature actual\s+min\.\s*([\d.]+)\s*..C\s+max\.\s*([\d.]+)\s*..C"
RE_DOSING      = r"nom\.\s*(\d+)\s*ml\s+act\.\s*(\d+)\s*ml"
RE_CONDUCT     = r"max\.\s*([\d.]+)\s*..S/cm\s*act\.\s*([\d.]+)\s*..S/cm"
RE_A0          = r"A0\s*Value\s+nom\.\s*(\d+)\s+act\.\s*(\d+)"
```

---

## Schritt-fuer-Schritt-Aufgaben

### Schritt 1: Test-Fixture anlegen

Kopie der WD390-Aufzeichnung als Test-Fixture, damit Tests unabhaengig vom reference-Ordner laufen.

**Aktionen:**

- `reference/WD390_4.ht` nach `tests/fixtures/wd390/WD390_4.ht` kopieren
- Sicherstellen dass .gitignore die .ht-Datei nicht ausschliesst

**Betroffene Dateien:**

- `tests/fixtures/wd390/WD390_4.ht` (neu)

---

### Schritt 2: WD-Protokoll-Parser implementieren (`wd_protocol_parser.py`)

Kernmodul das den WD-Protokolltext parst und das strukturierte Datenmodell zurueckgibt.

**Aktionen:**

- `decode_ht_file(path: str) -> str` — Liest .ht-Datei, findet UTF-16LE-Abschnitt ab "belimed"-Marker, gibt Klartext zurueck
- `parse_wd_protocol(text: str) -> dict` — Kernparser: extrahiert Kopfdaten und Schritte per Regex
- `_parse_header(text: str) -> dict` — Kopfdaten extrahieren (Betreiber, Maschine, Charge, etc.)
- `_parse_steps(text: str) -> list[dict]` — Schritte mit allen Parametern parsen
- `_calculate_kpis(steps: list) -> dict` — KPIs aus Schritten ableiten (A0, Thermodesinfektion, Dosierung)
- `_normalize_text(text: str) -> str` — Steuerzeichen entfernen, Leerzeichen normalisieren
- Logging mit `logger = logging.getLogger("docupi.wd_parser")`

**Betroffene Dateien:**

- `src/wd_protocol_parser.py` (neu)

---

### Schritt 3: Parser-Tests schreiben (`test_wd_parser.py`)

Automatisierte Tests mit der echten WD390-Aufzeichnung.

**Aktionen:**

- Test `test_decode_ht_file` — Liest WD390_4.ht, prueft dass Klartext zurueckkommt mit "belimed" am Anfang
- Test `test_parse_header` — Prueft alle Kopfdaten (Betreiber, Maschine, Charge, Programm, Zeiten)
- Test `test_parse_steps` — Prueft Anzahl Schritte (7), Namen, IDs, Zeiten
- Test `test_step_parameters` — Prueft nom/act-Werte der Thermodesinfektion (A0=3408, Temp 90.6-93.6)
- Test `test_kpis` — Prueft KPI-Berechnung (A0 bestanden, Leitwert ok)
- Test `test_result_detection` — Prueft "program without failure" → BESTANDEN
- Test `test_plain_text_input` — Parser funktioniert auch mit bereits dekodiertem Klartext
- Ausfuehrbar mit: `python -m pytest tests/test_wd_parser.py -v`

**Betroffene Dateien:**

- `tests/test_wd_parser.py` (neu)

---

### Schritt 4: WD-Chart-Generator implementieren (`wd_chart_generator.py`)

Chart fuer WD-Prozesse: Temperatur-Stufendiagramm ueber die Prozessschritte.

**Aktionen:**

- `generate_wd_chart(steps: list, output_path: str, width=11, height=4) -> str | None`
- X-Achse: Uhrzeit der Schritte (HH:MM)
- Y-Achse: Temperatur (actual min/max als Band, nominal als gestrichelte Linie)
- Schrittlabels als vertikale gestrichelte Linien mit Beschriftung
- Farbschema: konsistent mit MST-Chart (DARK_BLUE fuer Temperatur, Gruen fuer Soll-Band)
- Spezialmarkierung fuer Thermodesinfektion (A0-Wert annotieren)
- Matplotlib mit Agg-Backend, PNG-Output

**Betroffene Dateien:**

- `src/wd_chart_generator.py` (neu)

---

### Schritt 5: WD-PDF-Generator implementieren (`wd_pdf_generator.py`)

PDF-Klasse fuer WD/RDG-Chargenprotokolle.

**Aktionen:**

- Klasse `WashDisinfectorPDF(FPDF)` mit identischem Basis-Layout wie SterilizationPDF (Corporate Design, Seitenformat)
- **Seite 1 — Header:**
  - Geraetename (WD390-4), Charge Nr., Programm
  - Start-/Endzeit, Gesamtlaufzeit
  - Ergebnis-Box (gruen/rot)
- **Seite 1 — KPI-Boxen (4 Stueck):**
  - A0-Wert (nom/act)
  - Thermodesinfektion Temp (min/max)
  - Leitwert (act vs. max)
  - Gesamtlaufzeit
- **Seite 1 — Schritt-Tabelle:**
  - Spalten: Schritt | Uhrzeit | Name | Zeit nom/act | Temp nom | Temp act | Dosierung | Sonstiges
  - Pro Schritt eine Zeile, alternierend grau/weiss
  - Farbkodierung: Werte ausserhalb Toleranz rot markieren
- **Seite 1 — Freigabe:**
  - Signatur-Bereich, Freigabe ja/nein, Datum
- **Seite 2 — Chart:**
  - Temperaturverlauf aus wd_chart_generator
- Funktion `generate_wd_pdf(protocol_data: dict, config: dict, output_path: str) -> str`

**Betroffene Dateien:**

- `src/wd_pdf_generator.py` (neu)

---

### Schritt 6: Integration testen

End-to-End-Test: .ht-Datei → Parser → Chart → PDF.

**Aktionen:**

- Testskript `tests/test_wd_e2e.py`:
  - Liest `tests/fixtures/wd390/WD390_4.ht`
  - Parst mit `decode_ht_file()` + `parse_wd_protocol()`
  - Generiert Chart mit `generate_wd_chart()`
  - Generiert PDF mit `generate_wd_pdf()`
  - Prueft: PDF existiert, hat 2 Seiten, Dateigroesse > 10KB
- Output nach `tests/fixtures/wd390/` fuer visuelle Kontrolle

**Betroffene Dateien:**

- `tests/test_wd_e2e.py` (neu)
- `tests/fixtures/wd390/` (generierte PDF)

---

### Schritt 7: Dokumentation aktualisieren

**Aktionen:**

- `CLAUDE.md`: Neue Dateien in Workspace-Struktur, WD-Support dokumentieren
- `context/current-data.md`: RS232-Status auf "Protokoll entschluesselt" aendern, WD-Parser-Status hinzufuegen
- `context/strategy.md`: Prioritaet 1 (RS232 knacken) als teilweise erledigt markieren — WD-Format entschluesselt, WD290-Vergleich noch ausstehend

**Betroffene Dateien:**

- `CLAUDE.md`
- `context/current-data.md`
- `context/strategy.md`

---

## Verbindungen & Abhaengigkeiten

### Dateien, die diesen Bereich referenzieren

- `src/pdf_generator.py` — Bestehender MST-Generator, wird NICHT geaendert
- `src/chart_generator.py` — Bestehender MST-Chart, wird NICHT geaendert
- `src/patches/patch_protocol_v2.py` — MST-Parser-Referenz fuer Pattern-Konsistenz

### Noetige Updates fuer Konsistenz

- CLAUDE.md Workspace-Struktur muss die neuen Dateien listen
- context-Dateien muessen den Fortschritt reflektieren

### Auswirkungen auf bestehende Workflows

- **Kein Breaking Change** — alle neuen Dateien sind additiv
- Bestehende MST-Pipeline bleibt komplett unberuehrt
- Spaeter (nicht in diesem Plan): Dispatcher der anhand des Protokoll-Formats automatisch MST oder WD-Parser waehlt

---

## Validierungs-Checkliste

- [ ] `decode_ht_file()` liest WD390_4.ht und liefert lesbaren Klartext
- [ ] `parse_wd_protocol()` extrahiert alle 7 Schritte korrekt
- [ ] Kopfdaten vollstaendig: Betreiber, Maschine, Charge, Programm, Start/Ende
- [ ] A0-Wert korrekt: nom=3200, act=3408
- [ ] Thermodesinfektion-Temperaturen: 90.6-93.6 °C
- [ ] Leitwert: act=1.8 µS/cm
- [ ] Dosiermengen: Cleaning 1 = 162ml, Cleaning 2 = 288ml
- [ ] `generate_wd_chart()` erzeugt PNG ohne Fehler
- [ ] `generate_wd_pdf()` erzeugt 2-seitiges PDF
- [ ] PDF visuell geprueft: Tabelle lesbar, KPIs korrekt, Chart eingebettet
- [ ] Alle Tests grueen: `python -m pytest tests/test_wd_parser.py tests/test_wd_e2e.py -v`
- [ ] CLAUDE.md aktualisiert
- [ ] context-Dateien aktualisiert

---

## Erfolgskriterien

1. WD390-Chargenprotokoll wird fehlerfrei aus .ht-Datei geparst — alle Felder korrekt extrahiert
2. Generiertes PDF ist professionell, visuell konsistent mit MST-PDFs, und enthaelt alle relevanten WD-Daten
3. Parser-Code ist sauber genug, dass er spaeter fuer Live-RS232-Integration wiederverwendet werden kann

---

## Notizen

- **WD290-Kompatibilitaet:** Sollte zeitnah mit einer WD290-Aufzeichnung validiert werden. Die ECU Cadi Software ist auf beiden Geraetetypen identisch, daher hohe Wahrscheinlichkeit dass das Format gleich ist.
- **Live-RS232-Integration:** Nicht Teil dieses Plans. Naechster Schritt waere ein Serial Listener der den Text-Stream buffert, Protokoll-Ende erkennt (vermutlich durch Timeout oder "signature" als Marker), und dann den Parser aufruft.
- **Dispatcher-Logik:** Spaeter: Automatische Erkennung ob eingehender Text MST oder WD ist (Marker: "BELIMED CHARGEN-DOKUMENTATION" = MST, "belimed batch dokumentation" = WD).
- **Encoding-Hinweis:** Die WD/ECU sendet UTF-16LE ueber die serielle Schnittstelle. Im Live-Betrieb muss der Serial Listener das beruecksichtigen (Baudrate, Encoding). Die HyperTerminal-Aufzeichnung zeigt: Der Text kommt als UTF-16LE-Zeichen an, nicht als ASCII.

---

## Implementierungsnotizen

**Implementiert:** 2026-03-27

### Zusammenfassung

Alle 7 Schritte des Plans wurden ausgefuehrt:
- WD-Protokoll-Parser (`wd_protocol_parser.py`) — liest .ht-Dateien und Klartext
- WD-Chart-Generator (`wd_chart_generator.py`) — Temperatur-Stufendiagramm
- WD-PDF-Generator (`wd_pdf_generator.py`) — 2-seitiges PDF mit KPIs, Tabelle, Chart
- 42 Tests geschrieben und bestanden (34 Parser + 8 E2E)
- Dokumentation aktualisiert (CLAUDE.md, context/current-data.md, context/strategy.md)

### Abweichungen vom Plan

1. **Python 3.9 Kompatibilitaet**: `list[dict]` und `str | None` Type Hints mussten zu `list` und `Optional[str]` geaendert werden (macOS system Python 3.9 statt 3.10+).
2. **CR statt LF**: Die HyperTerminal-Aufzeichnung nutzt `\r` als Zeilentrenner statt `\n`. Der `_normalize_text()` wurde angepasst um `\r` -> `\n` zu konvertieren.
3. **Step-Parser komplett umgeschrieben**: Der Regex-basierte Ansatz aus dem Plan funktionierte nicht mit dem kontinuierlichen Textstream. Stattdessen: zeilenbasiertes Parsing mit Step-ID-Erkennung und Block-Merging fuer doppelte Step-IDs.
4. **E2E-Tests**: PDF-Textsuche brauchte zlib-Dekomprimierung da fpdf2 FlateDecode nutzt.

### Aufgetretene Probleme

- HT-Datei hatte `\r` statt `\n` als Zeilentrenner — behoben durch Normalisierung
- Erster Step-Parser-Ansatz fand nur 1 von 7 Schritten — kompletter Rewrite auf zeilenbasiert
- Python 3.9 unterstuetzt keine modernen Type Hints — auf kompatible Syntax gewechselt
