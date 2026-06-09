# Plan: Drucker-Darstellung in Settings optimieren

**Erstellt:** 2026-06-09
**Status:** Implementiert
**Anforderung:** "Drucker erkennen"-Button entfernen, echten Gerätenamen (statt CUPS-Alias) anzeigen, bei fehlendem Gerät "kein Drucker verbunden" zeigen.

---

## Überblick

### Was dieser Plan erreicht

Die Drucker-Card in Settings → "Geräte & Netzwerk" zeigt statt des internen CUPS-Alias "DocuPrinter" den echten Gerätenamen des angeschlossenen Druckers (z. B. "EPSON XP-4150 Series"). Ist kein Drucker verbunden, erscheint "kein Drucker verbunden". Der nutzlose "Drucker erkennen"-Button (war nur ein manueller Refresh desselben Status) wird entfernt.

### Warum das wichtig ist

Der erste Kunden-Pi läuft beim externen Vertriebspartner getmatic — die Settings sind für Endnutzer sichtbar. "DocuPrinter" als Anzeigenamen zu sehen ist verwirrend und wirkt unfertig. Der echte Gerätename gibt dem Nutzer Feedback darüber, was tatsächlich angeschlossen ist.

---

## Aktueller Zustand

### Relevante bestehende Struktur

- `src/docucontrol/templates/settings.html` — Drucker-Card (Zeilen 27–63)
  - Set-Row 1: "USB-Drucker erkennen" + Button `detectPrinter()` → ruft `POST /api/printer/detect` auf
  - Set-Row 2: "Erkannter Drucker" → `<span id="printerName">` wird mit `d.printer` aus `GET /api/printer/status` befüllt
- `src/print_manager.py` — `get_printers()` liefert CUPS-Attributes; `info`-Feld = `printer-info` aus CUPS = "DocuPrinter"
- Pi `app.py` Zeile 1007–1026:
  - `GET /api/printer/status` gibt `printer_name = printers[0]['info']` zurück → "DocuPrinter"
  - `POST /api/printer/detect` gibt exakt dasselbe zurück

### Lücken oder Probleme, die adressiert werden

1. **CUPS-Alias statt echtem Gerätename:** CUPS speichert den Druckernamen als "DocuPrinter" (Alias). `printer-make-and-model` aus CUPS liefert nur "Printer - IPP Everywhere" (generischer IPP-Everywhere-Treiber). Das echte Modell "EPSON XP-4150 Series" ist nur direkt am Gerät per IPP abrufbar.
2. **"Drucker erkennen"-Button ohne Mehrwert:** `POST /api/printer/detect` ruft nur `get_printer_status()` auf und gibt dieselben Daten zurück. Kein Scan für neue Drucker, kein Re-Pairing. Nutzlos und verwirrend.
3. **Kein "disconnected"-Zustand:** Bei `printer_count === 0` zeigt die UI `(kein Drucker erkannt)` — korrekte Meldung, aber Label "Erkannter Drucker" passt nicht zum v3-Design-Ton.

### Technische Grundlage (bereits ermittelt)

```
# ipptool-Abfrage direkt am Gerät liefert das echte Modell:
$ ipptool -v 'ipps://EPSON41D474.local:631/ipp/print' get-printer-attributes.test
  → printer-make-and-model: EPSON XP-4150 Series   ✓

# CUPS-Abfrage (aktuell genutzt):
  → printer-info: DocuPrinter                       ✗ (Alias)
  → printer-make-and-model: Printer - IPP Everywhere ✗ (generisch)

# device-uri aus CUPS ist Einstiegspunkt für ipptool:
  → ipps://EPSON41D474.local:631/ipp/print
```

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

1. `print_manager.py` — neue Funktion `get_real_printer_model(device_uri)` mit In-Memory-Cache (TTL 5 min), `get_printers()` ergänzt um Feld `model`
2. Pi `app.py` — `/api/printer/status` gibt `model` statt `info` zurück; `/api/printer/detect` kann bleiben (schadet nicht), wird aber im Frontend nicht mehr aufgerufen
3. `settings.html` — "Drucker erkennen"-Row entfernen, Label und JS aktualisieren

### Neue Dateien erstellen

Keine.

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|---|---|
| `src/print_manager.py` | Neue Funktion `get_real_printer_model()` + `model`-Feld in `get_printers()` |
| `src/docucontrol/templates/settings.html` | Row "Drucker erkennen" entfernen, Label + JS für echten Namen |

### Zu löschende Dateien

Keine.

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **`ipptool` via Subprocess für echten Modellnamen**: Einzige zuverlässige Quelle für `printer-make-and-model` direkt am Gerät. `ipptool` ist auf dem Pi bereits vorhanden (CUPS-Paket). Kein neuer Dependency.

2. **In-Memory-Cache mit 5-Minuten-TTL**: Der `ipptool`-Aufruf dauert ~100–300 ms (Netzwerk zum Drucker). `get_printers()` wird alle 30 s durch Frontend-Polling aufgerufen → Cache verhindert unnötigen Overhead. Cache-Key = `device_uri`, Cache wird pro Prozess-Session gehalten.

3. **Fallback-Kette**: `model` → falls `ipptool` fehlschlägt → `printer-info` aus CUPS → falls leer → `printer-name`. Robustes Verhalten bei Netzwerkproblemen.

4. **"Drucker erkennen"-Row komplett entfernen**: CUPS erkennt IPP-Everywhere-Drucker beim Einstecken automatisch via Avahi/mDNS. Ein manueller Trigger ist nicht nötig. Der Button hat keinen sichtbaren Effekt und verursacht Verwirrung beim Kunden.

5. **Label "Verbundener Drucker"**: Passender als "Erkannter Drucker" — beschreibt den Zustand (verbunden / nicht verbunden) statt einen Prozess (erkennen).

### Betrachtete Alternativen

- **USB-Gerät via `lsusb` auslesen**: Funktioniert nicht für Netzwerk-/WiFi-Drucker (Epson XP-4150 ist über WLAN/mDNS verbunden, nicht USB).
- **Hostname aus `device-uri` parsen** ("EPSON41D474"): Nicht lesbar, seriell-basierter Hostname.
- **CUPS `printer-info` umbenennen** (einmalig beim Setup auf "EPSON XP-4150 Series" setzen): Fragil, wird nicht automatisch aktualisiert wenn Drucker wechselt.
- **`python-ipp`-Library**: Unnötiger neuer Dependency, `ipptool` bereits vorhanden.

### Offene Fragen

Keine — alle Entscheidungen sind eindeutig.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: `print_manager.py` — `get_real_printer_model()` hinzufügen

Neue Funktion nach `get_printers()` einfügen. Ruft `ipptool` als Subprocess auf, parst `printer-make-and-model` aus der Ausgabe, cached das Ergebnis pro URI mit TTL.

**Aktionen:**

- Modul-Level Cache-Dict `_model_cache: dict[str, tuple[str, float]]` hinzufügen (`uri → (model, timestamp)`)
- Funktion `get_real_printer_model(device_uri: str) -> str` implementieren:
  ```python
  import subprocess, time, re

  _model_cache = {}  # {uri: (model_str, fetched_at_ts)}
  _MODEL_CACHE_TTL = 300  # 5 Minuten

  def get_real_printer_model(device_uri):
      now = time.time()
      if device_uri in _model_cache:
          model, ts = _model_cache[device_uri]
          if now - ts < _MODEL_CACHE_TTL:
              return model
      try:
          result = subprocess.run(
              ['ipptool', '-v', device_uri,
               '/usr/share/cups/ipptool/get-printer-attributes.test'],
              capture_output=True, text=True, timeout=4
          )
          match = re.search(r'printer-make-and-model \([^)]+\) = (.+)', result.stdout)
          model = match.group(1).strip() if match else ''
      except Exception:
          model = ''
      _model_cache[device_uri] = (model, now)
      return model
  ```
- In `get_printers()`: nach dem Aufbau des Printer-Dicts `model`-Feld hinzufügen:
  ```python
  device_uri = attrs.get("device-uri", "")
  model = get_real_printer_model(device_uri) if device_uri else ''
  # Fallback-Kette:
  if not model:
      model = attrs.get("printer-info", name)
  printer_dict["model"] = model
  ```

**Betroffene Dateien:**

- `src/print_manager.py`

---

### Schritt 2: Pi `app.py` — `/api/printer/status` gibt `model` zurück

Auf dem Pi ist `app.py` deployed. Der Endpunkt muss `model` statt `info` liefern.

**Aktionen:**

- SSH auf Pi, Zeilen 1007–1026 in `/home/docucontrol/docupi/app.py` anpassen:
  ```python
  # Alt:
  printer_name = printers[0]['info'] if printers else ''
  return jsonify({'printer': printer_name, ...})

  # Neu:
  printer_model = printers[0].get('model') or printers[0]['info'] if printers else ''
  return jsonify({
      'printer': printer_model,        # kompatibel: Frontend nutzt d.printer
      'model': printer_model,          # explizit neues Feld
      'printer_count': len(printers),
      ...
  })
  ```
- Gleiches für `/api/printer/detect` (Zeile 1022–1026): `info` → `model`-Fallback

**Betroffene Dateien:**

- `/home/docucontrol/docupi/app.py` (direkt auf Pi via SSH + sed oder deploy-script)

---

### Schritt 3: `settings.html` — UI anpassen

Drei Änderungen in der Drucker-Card:
1. Row "USB-Drucker erkennen" (inkl. Button) komplett entfernen
2. Label "Erkannter Drucker" → "Verbundener Drucker"
3. JS in `loadDeviceSettings()` und `detectPrinter()` anpassen

**Aktionen:**

- **Zeilen 31–37 entfernen** (Set-Row "USB-Drucker erkennen"):
  ```html
  <!-- WEG: -->
  <div class="set-row">
      <div class="info">
          <div class="name">USB-Drucker erkennen</div>
          <div class="desc">Angeschlossene Drucker suchen</div>
      </div>
      <button class="btn btn-outline" onclick="detectPrinter()">...</button>
  </div>
  ```

- **Zeile 40**: Label ändern:
  ```html
  <!-- Alt: --> <div class="name">Erkannter Drucker</div>
  <!-- Neu: --> <div class="name">Verbundener Drucker</div>
  ```

- **Zeile 41**: Desc ändern:
  ```html
  <!-- Alt: --> <div class="desc">Aktuell verbundenes Gerät</div>
  <!-- Neu: --> <div class="desc">Angeschlossener Drucker</div>
  ```

- **Zeile 546** in `loadDeviceSettings()`:
  ```javascript
  // Alt:
  document.getElementById('printerName').textContent = d.printer || '(kein Drucker erkannt)';
  // Neu:
  document.getElementById('printerName').textContent =
      (d.printer_count === 0 || !d.printer) ? 'kein Drucker verbunden' : d.printer;
  ```

- **Zeile 549** (catch-Handler):
  ```javascript
  // Alt:
  document.getElementById('printerName').textContent = '(kein Drucker erkannt)';
  // Neu:
  document.getElementById('printerName').textContent = 'kein Drucker verbunden';
  ```

- **Zeilen 862–870** (`detectPrinter()`-Funktion): Funktion kann bestehen bleiben oder entfernt werden (Button ist weg, wird nicht mehr aufgerufen). Zur Sicherheit lassen.

**Betroffene Dateien:**

- `src/docucontrol/templates/settings.html`

---

### Schritt 4: Deployment auf Pi

Geänderte Dateien auf den Pi übertragen und Service neu starten.

**Aktionen:**

- `print_manager.py` deployen: `scp -i ~/.ssh/id_ed25519 src/print_manager.py docucontrol@192.168.0.171:/home/docucontrol/docupi/`
- `settings.html` deployen: `scp -i ~/.ssh/id_ed25519 src/docucontrol/templates/settings.html docucontrol@192.168.0.171:/home/docucontrol/docupi/templates/`
- `app.py` auf Pi direkt bearbeiten (nur 2–3 Zeilen) oder lokal anpassen und übertragen
- Service neu starten: `ssh -i ~/.ssh/id_ed25519 docucontrol@192.168.0.171 "sudo systemctl restart docucontrol"`

**Betroffene Dateien:**

- Pi: `/home/docucontrol/docupi/print_manager.py`
- Pi: `/home/docucontrol/docupi/templates/settings.html`
- Pi: `/home/docucontrol/docupi/app.py`

---

### Schritt 5: Validierung im Browser

Settings-Tab aufrufen und Drucker-Card prüfen.

**Aktionen:**

- Browser: `http://192.168.0.171/settings` aufrufen, Tab "Geräte & Netzwerk"
- Erwartetes Ergebnis: "Verbundener Drucker" → "EPSON XP-4150 Series"
- Kein "Drucker erkennen"-Button mehr sichtbar
- Epson-Drucker ausschalten/abstecken, Seite neu laden → "kein Drucker verbunden"
- API direkt prüfen: `curl http://192.168.0.171/api/printer/status` → `model`-Feld vorhanden

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- `src/docucontrol/templates/settings.html` — einzige Template-Datei die Drucker-Status rendert
- `src/print_manager.py` — Modul für alle Drucker-Operationen (auch Testdruck, Auto-Print)
- Pi `app.py` — API-Endpunkte (`/api/printer/status`, `/api/printer/detect`, `/api/printer/ready`)

### Nötige Updates für Konsistenz

- `CLAUDE.md` — Drucker-API-Sektion aktualisieren: `d.printer` enthält jetzt echten Modellnamen, `printer_count`-Feld neu
- `context/current-data.md` — Drucker-Zeile aktualisieren: "EPSON XP-4150 Series" statt "DocuPrinter"

### Auswirkungen auf bestehende Workflows

- Dashboard: keine Drucker-Anzeige betroffen
- Auto-Print, Testdruck, Print-Button: alle nutzen `printer-name` intern (CUPS-Name "DocuPrinter") — unberührt
- `/api/printer/ready`: gibt `p.get('info') or p['name']` zurück — sollte nach Änderung auch `model` nutzen (kleiner Fix in Schritt 2 miterfassen)

---

## Validierungs-Checkliste

- [ ] Settings-Tab "Geräte & Netzwerk" zeigt "Verbundener Drucker" als Label
- [ ] Bei verbundenem Epson: "EPSON XP-4150 Series" wird angezeigt (nicht "DocuPrinter")
- [ ] "Drucker erkennen"-Button ist nicht mehr sichtbar
- [ ] Bei fehlendem/ausgeschaltetem Drucker: "kein Drucker verbunden"
- [ ] Testdruck und Auto-Print funktionieren weiterhin (CUPS-Name intern unverändert)
- [ ] `GET /api/printer/status` gibt Feld `model` zurück
- [ ] Service-Restart sauber: `systemctl status docucontrol` zeigt `active (running)`
- [ ] CLAUDE.md und context/current-data.md aktualisiert

---

## Erfolgskriterien

1. Die Drucker-Card in Settings zeigt "EPSON XP-4150 Series" für den aktuell verbundenen Epson-Drucker
2. Bei keinem verbundenen Drucker steht dort "kein Drucker verbunden"
3. Der "Drucker erkennen"-Button existiert nicht mehr in der UI

---

---

## Implementierungsnotizen

**Implementiert:** 2026-06-09

### Zusammenfassung

`print_manager.py` um `get_real_printer_model()` mit `ipptool -tv` + 5-min-Cache ergänzt. Pi `app.py` patched: `/api/printer/status`, `/api/printer/detect`, `/api/printer/ready` geben echten Modellnamen zurück. `settings.html`: "Drucker erkennen"-Row entfernt, Label → "Verbundener Drucker", JS zeigt "kein Drucker verbunden" wenn `printer_count === 0`. Alles deployed und validiert — API liefert `"model": "EPSON XP-4150 Series"`.

### Abweichungen vom Plan

- **`-v` → `-tv`**: Die Plan-Implementierung nutzte `ipptool -v` — das gibt bei subprocess kein stdout aus. Korrigiert zu `ipptool -tv` (test + verbose), das erzeugt die geparste Ausgabe auf stdout.

### Aufgetretene Probleme

- `ipptool -v` via subprocess liefert leeres stdout (tty-abhängig). `ipptool -tv` funktioniert korrekt und gibt parsed output auf stdout aus.

---

## Notizen

- **Erster `ipptool`-Aufruf nach Service-Start dauert ~200–300 ms**: danach gecacht für 5 min — kein spürbarer Effekt auf Page-Load (asynchrones Polling alle 30 s)
- **CUPS-Alias "DocuPrinter" bleibt intern erhalten**: Auto-Print, Druckjobs, `POST /api/print/<id>` — alles weiter stabil, da CUPS-Name nie in der UI propagiert wird
- **Zukunft: Mehrere Drucker**: `model`-Feld pro Drucker in Liste — Frontend-Anpassung wäre dann trivial
- **Pi `app.py` nicht in Workspace-Repo versioniert**: Änderungen in Schritt 2 direkt auf Pi oder als Patch-Skript dokumentieren
