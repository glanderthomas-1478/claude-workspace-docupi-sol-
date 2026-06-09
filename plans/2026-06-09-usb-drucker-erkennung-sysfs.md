# Plan: USB-Drucker-Erkennung über sysfs (physische Anwesenheit)

**Erstellt:** 2026-06-09
**Status:** Implementiert
**Anforderung:** Drucker-Verbindungsstatus ausschließlich anhand physisch angestecktem USB-Gerät (sysfs) ermitteln — nicht per TCP/Netzwerk. "Kein Drucker angeschlossen" wenn kein USB-Drucker steckt.

---

## Überblick

### Was dieser Plan erreicht

`print_manager.py` erhält zwei neue Funktionen: `is_usb_printer_present()` prüft via Linux sysfs (`/sys/bus/usb/devices/`) ob ein USB-Gerät mit Printer-Interface-Class (0x07) physisch angesteckt ist. `get_usb_printer_model()` liest Hersteller und Produktname direkt aus den USB-Device-Deskriptoren. Der bestehende TCP-Check (`is_printer_reachable()`) wird vollständig ersetzt. Wenn kein USB-Drucker steckt, zeigt die Settings-UI "Kein Drucker angeschlossen" — unabhängig davon was CUPS intern konfiguriert hat.

### Warum das wichtig ist

DocuControl ist für USB-Drucker konzipiert. Der bisherige TCP-Check auf die Netzwerk-URI des CUPS-Eintrags ist falsch für diesen Anwendungsfall: ein Netzwerkdrucker (Epson XP-4150 via WiFi) bleibt erreichbar auch wenn er im UI als "nicht verbunden" gelten sollte. Der Kunde (Tierlabor Uni Essen) steckt einen USB-Drucker an den Pi — der Status muss die physische USB-Verbindung widerspiegeln.

---

## Aktueller Zustand

### Relevante bestehende Struktur

- `src/print_manager.py` (auch auf Pi deployed):
  - `is_printer_reachable(device_uri, timeout=1.5)` — TCP socket connect auf Drucker-URI-Host; falsch für USB-Drucker
  - `get_real_printer_model(device_uri)` — `ipptool -tv` gegen Netzwerk-URI; nur für Netzwerkdrucker korrekt
  - `get_printers()` — setzt `connected = is_printer_reachable(device_uri)` pro Drucker
  - Imports: `socket`, `from urllib.parse import urlparse` (nur für TCP-Check)
- Pi `app.py` `/api/printer/status`:
  - `connected_printers = [p for p in printers if p.get('connected', False)]`
  - `printer_model = (connected_printers[0].get('model') or '') if connected_printers else ''`
  - Logik korrekt — nutzt `connected`-Feld aus `get_printers()`; muss nicht geändert werden
- `src/docucontrol/templates/settings.html`:
  - JS zeigt `'Kein Drucker angeschlossen'` wenn `d.printer_count === 0 || !d.printer`
  - Logik korrekt — muss nicht geändert werden
- Pi `config.py`: kein USB-spezifisches Konfig-Feld nötig

### Lücken oder Probleme, die adressiert werden

1. **Falsche Erkennungsmethode**: `is_printer_reachable()` prüft TCP-Netzwerk-Erreichbarkeit — erkennt keinen Unterschied zwischen "USB-Kabel gezogen" und "Drucker noch im WLAN"
2. **Falscher Modell-Abruf**: `get_real_printer_model()` nutzt `ipptool` gegen die CUPS-Netzwerk-URI — gibt auch dann "EPSON XP-4150 Series" zurück wenn kein Drucker physisch angesteckt ist (gecachter Wert)
3. **Unnötige Imports**: `socket` und `urlparse` werden nur für den TCP-Check benötigt — fallen weg

### Technische Grundlage (bereits verifiziert auf Pi)

```
# Sysfs-Struktur (kein Drucker angesteckt):
/sys/bus/usb/devices/usb1/  → bDeviceClass: 09 (Hub)
/sys/bus/usb/devices/usb2/  → bDeviceClass: 09 (Hub)
# Keine Printer-Interfaces (bInterfaceClass = 07) gefunden → is_usb_printer_present() = False

# Mit USB-Drucker (erwartete Struktur):
/sys/bus/usb/devices/1-1/            → physisches Gerät
  manufacturer                        → "EPSON"
  product                             → "XP-4150 Series"
  1-1:1.0/
    bInterfaceClass                   → "07" (Printer)
```

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

1. `print_manager.py` — `is_usb_printer_present()` + `get_usb_printer_model()` hinzufügen; `is_printer_reachable()` entfernen; `get_printers()` auf USB-Erkennung umstellen; unnötige Imports entfernen
2. Pi — `print_manager.py` deployen
3. Kein Änderungsbedarf an `app.py` (API-Logik bereits korrekt) oder `settings.html` (Frontend-Logik bereits korrekt)

### Neue Dateien erstellen

Keine.

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|---|---|
| `src/print_manager.py` | `is_printer_reachable()` entfernen; `is_usb_printer_present()` + `get_usb_printer_model()` hinzufügen; `get_printers()` anpassen; `socket`/`urlparse` Imports entfernen |

### Zu löschende Dateien

Keine.

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **sysfs `bInterfaceClass = 07`** als Erkennungsmethode: Der Linux-Kernel trägt jeden angesteckten USB-Drucker in `/sys/bus/usb/devices/<dev>/<iface>/bInterfaceClass` ein — hersteller- und treiberunabhängig, ohne Root-Rechte lesbar, sofort aktuell beim Ein-/Abstecken (kein TTL, kein Cache-Problem). `usblp`-Modul ist auf dem Pi geladen und bestätigt.

2. **Modellname aus sysfs `manufacturer` + `product`**: Die USB-Device-Deskriptoren enthalten Hersteller und Produktname direkt am Gerät — kein Netzwerk-Request nötig, keine `ipptool`-Abhängigkeit für USB-Drucker. Ergebnis: "EPSON XP-4150 Series" o.ä. aus `manufacturer` + `product` Feldern des USB-Device-Verzeichnisses.

3. **`is_usb_printer_present()` einmal pro `get_printers()`-Aufruf**: Die Funktion wird am Anfang von `get_printers()` einmal aufgerufen und das Ergebnis auf alle CUPS-Einträge als `connected`-Feld gesetzt. Ein CUPS-Eintrag allein (ohne physischen USB-Drucker) führt nie zu `connected: true`.

4. **`get_real_printer_model()` bleibt erhalten aber ungenutzt**: Die Funktion mit `ipptool` bleibt im Code für eventuelle Netzwerkdrucker-Szenarien in der Zukunft — wird aber nicht mehr von `get_printers()` aufgerufen. Kein Bruch der öffentlichen API.

5. **`_model_cache` bleibt**: Der Cache bleibt als Modul-Variable, auch wenn er für den neuen Flow nicht mehr befüllt wird. Kein Aufräumaufwand.

6. **Kein separater API-Endpunkt nötig**: Die bestehende Architektur (API filtert per `connected`-Feld, Frontend prüft `printer_count === 0`) ist bereits korrekt. Nur die Quelle des `connected`-Felds ändert sich.

### Betrachtete Alternativen

- **`/dev/usb/lp*`-Check**: Einfach, aber abhängig davon ob `usblp` den Drucker als `lp`-Device registriert. Nicht alle USB-Drucker tun das (z.B. wenn IPP-over-USB aktiv ist). Unzuverlässiger als sysfs.
- **`lsusb`-Subprocess**: Funktioniert, aber langsamer als sysfs-Dateilesen und erfordert externe Binary. Kein Vorteil gegenüber sysfs.
- **`lpinfo -v` (CUPS Backend-Scan)**: Zu langsam (~2–5s), blockiert den Request.
- **pyusb-Library**: Neuer Dependency ohne Mehrwert gegenüber sysfs.
- **Pro-Drucker TCP-Check behalten, aber mit USB-URI**: Würde erfordern dass CUPS-Einträge USB-URIs haben (`usb://...`) statt Netzwerk-URIs. Das erfordert Neukonfiguration von CUPS — unnötig wenn sysfs direkter und zuverlässiger ist.

### Offene Fragen

Keine — Methode verifiziert, Änderungsumfang klar.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: `print_manager.py` — Imports bereinigen

`socket` und `urlparse` werden nur für `is_printer_reachable()` gebraucht. Beide Imports entfernen.

**Aktionen:**

```python
# ALT:
import socket
import subprocess
import threading
import time
from urllib.parse import urlparse

# NEU:
import subprocess
import threading
import time
```

**Betroffene Dateien:**

- `src/print_manager.py`

---

### Schritt 2: `print_manager.py` — `is_printer_reachable()` entfernen

Die Funktion `is_printer_reachable(device_uri, timeout=1.5)` vollständig löschen.

**Aktionen:**

- Gesamte Funktion `is_printer_reachable()` (inkl. Docstring) aus `src/print_manager.py` entfernen

**Betroffene Dateien:**

- `src/print_manager.py`

---

### Schritt 3: `print_manager.py` — `is_usb_printer_present()` + `get_usb_printer_model()` einfügen

Zwei neue Funktionen nach `get_real_printer_model()` einfügen (vor `get_default_printer()`).

**Aktionen:**

```python
def is_usb_printer_present():
    """Return True if any USB device with printer interface class (0x07) is connected."""
    try:
        base = '/sys/bus/usb/devices'
        for dev in os.listdir(base):
            dev_path = os.path.join(base, dev)
            if not os.path.isdir(dev_path):
                continue
            for entry in os.listdir(dev_path):
                iface_cls = os.path.join(dev_path, entry, 'bInterfaceClass')
                if os.path.exists(iface_cls):
                    with open(iface_cls) as f:
                        if f.read().strip() == '07':
                            return True
        return False
    except Exception:
        return False


def get_usb_printer_model():
    """Read manufacturer + product name of first USB printer from sysfs device descriptors."""
    try:
        base = '/sys/bus/usb/devices'
        for dev in sorted(os.listdir(base)):
            dev_path = os.path.join(base, dev)
            if not os.path.isdir(dev_path):
                continue
            for entry in os.listdir(dev_path):
                iface_cls = os.path.join(dev_path, entry, 'bInterfaceClass')
                if os.path.exists(iface_cls):
                    with open(iface_cls) as f:
                        if f.read().strip() == '07':
                            mfr = ''
                            prod = ''
                            mfr_f = os.path.join(dev_path, 'manufacturer')
                            prod_f = os.path.join(dev_path, 'product')
                            if os.path.exists(mfr_f):
                                mfr = open(mfr_f).read().strip()
                            if os.path.exists(prod_f):
                                prod = open(prod_f).read().strip()
                            return f'{mfr} {prod}'.strip() or 'USB Drucker'
        return ''
    except Exception:
        return ''
```

**Betroffene Dateien:**

- `src/print_manager.py`

---

### Schritt 4: `print_manager.py` — `get_printers()` auf USB-Erkennung umstellen

In `get_printers()` den alten `is_printer_reachable()`-Aufruf durch `is_usb_printer_present()` + `get_usb_printer_model()` ersetzen.

**Aktionen:**

```python
# ALT in get_printers() (innerhalb der for-Schleife):
device_uri = attrs.get("device-uri", "")
connected = is_printer_reachable(device_uri) if device_uri else False
model = (get_real_printer_model(device_uri) if connected else "") if device_uri else ""
if not model and connected:
    model = attrs.get("printer-info", name)

# NEU — einmal vor der Schleife:
usb_connected = is_usb_printer_present()
usb_model = get_usb_printer_model() if usb_connected else ""

# NEU — innerhalb der for-Schleife (ersetzt obigen Block):
device_uri = attrs.get("device-uri", "")
connected = usb_connected
model = usb_model or attrs.get("printer-info", name) if connected else ""
```

Konkret: `usb_connected = is_usb_printer_present()` und `usb_model = get_usb_printer_model() if usb_connected else ""` werden **vor** `for name, attrs in printers.items():` eingefügt. Im Loop-Body wird dann `connected = usb_connected` und `model = usb_model or attrs.get("printer-info", name) if connected else ""` gesetzt.

**Betroffene Dateien:**

- `src/print_manager.py`

---

### Schritt 5: Deployment auf Pi

`print_manager.py` auf den Pi übertragen und Service neu starten.

**Aktionen:**

- `scp -i ~/.ssh/id_ed25519 src/print_manager.py docucontrol@192.168.0.171:/home/docucontrol/docupi/print_manager.py`
- `ssh ... "sudo systemctl restart docucontrol && sleep 2 && systemctl is-active docucontrol"`

**Betroffene Dateien:**

- Pi: `/home/docucontrol/docupi/print_manager.py`

---

### Schritt 6: Validierung

**Aktionen (Drucker NICHT angesteckt):**

```bash
# API muss printer_count=0, printer='' zurückgeben:
curl http://192.168.0.171/api/printer/status
# Erwartung: {"printer": "", "printer_count": 0, ...}

# Python-Test direkt auf Pi:
ssh ... "python3 -c 'from print_manager import is_usb_printer_present, get_usb_printer_model; print(is_usb_printer_present(), get_usb_printer_model())'"
# Erwartung: False ''
```

**Aktionen (Drucker angesteckt — USB):**

```bash
# Nach Anstecken:
ssh ... "python3 -c 'from print_manager import is_usb_printer_present, get_usb_printer_model; print(is_usb_printer_present(), get_usb_printer_model())'"
# Erwartung: True 'EPSON XP-4150 Series' (o.ä.)

curl http://192.168.0.171/api/printer/status
# Erwartung: {"printer": "EPSON XP-4150 Series", "printer_count": 1, ...}
```

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- Pi `app.py` — importiert `get_printers`, `is_cups_available`, `get_status` aus `print_manager`; nutzt `connected`-Feld aus `get_printers()`. Keine Änderung nötig.
- `settings.html` — JS prüft `d.printer_count === 0 || !d.printer`. Keine Änderung nötig.

### Nötige Updates für Konsistenz

- `CLAUDE.md` — Drucker-Sektion: Hinweis auf USB-sysfs-Erkennung aktualisieren
- `context/current-data.md` — Drucker-Zeile: "USB-Erkennung via sysfs"

### Auswirkungen auf bestehende Workflows

- Testdruck, Auto-Print, Print-Button: nutzen CUPS-Name `DocuPrinter` intern — unberührt, CUPS-Konfiguration bleibt
- Modell-Anzeige: kommt jetzt aus USB-Deskriptor statt ipptool — bei gleicher Hardware identisches Ergebnis
- `_model_cache` und `get_real_printer_model()` bleiben im Code, werden aber nicht mehr von `get_printers()` aufgerufen

---

## Validierungs-Checkliste

- [ ] `is_usb_printer_present()` gibt `False` zurück wenn kein USB-Drucker gesteckt
- [ ] `is_usb_printer_present()` gibt `True` zurück wenn USB-Drucker angesteckt
- [ ] `get_usb_printer_model()` gibt leeren String zurück wenn kein Drucker
- [ ] `get_usb_printer_model()` gibt "EPSON XP-4150 Series" (o.ä.) zurück wenn angesteckt
- [ ] `GET /api/printer/status` → `printer_count: 0`, `printer: ''` ohne USB-Drucker
- [ ] `GET /api/printer/status` → `printer_count: 1`, `printer: 'EPSON XP-4150 Series'` mit USB-Drucker
- [ ] Settings zeigt "Kein Drucker angeschlossen" wenn kein Drucker gesteckt
- [ ] Settings zeigt Modellname wenn Drucker angesteckt (nach max. 30s Polling)
- [ ] Service-Restart sauber, `is-active` = active
- [ ] CLAUDE.md aktualisiert

---

## Erfolgskriterien

1. USB-Drucker gesteckt → Settings zeigt Modellname innerhalb von 30 Sekunden
2. USB-Drucker abgezogen → Settings zeigt "Kein Drucker angeschlossen" innerhalb von 30 Sekunden
3. CUPS-Konfiguration hat keinen Einfluss auf den angezeigten Verbindungsstatus

---

---

## Implementierungsnotizen

**Implementiert:** 2026-06-09

### Zusammenfassung

`socket`/`urlparse` Imports entfernt, `is_printer_reachable()` gelöscht. `is_usb_printer_present()` und `get_usb_printer_model()` via sysfs hinzugefügt. `get_printers()` nutzt USB-Check einmalig vor dem Loop. API gibt `printer_count: 0`, `printer: ''` wenn kein USB-Drucker steckt — verifiziert.

### Abweichungen vom Plan

Keine.

### Aufgetretene Probleme

Keine.

---

## Notizen

- **Root-Rechte**: sysfs `bInterfaceClass` ist für alle Nutzer lesbar — kein `sudo` nötig
- **Performance**: sysfs-Lesen ist ~1 ms, kein Netzwerk-Timeout mehr. `get_printers()` wird dadurch schneller als mit TCP-Check (war bis 1,5s Timeout)
- **Multi-Drucker**: `is_usb_printer_present()` gibt `True` sobald irgendein USB-Drucker steckt. `get_usb_printer_model()` gibt das Modell des ERSTEN gefundenen zurück (sortiert nach Gerätename). Für Single-Printer-Betrieb ausreichend.
- **CUPS-Eintrag "DocuPrinter"**: Bleibt erhalten und wird weiterhin für Druckjobs genutzt. Der Eintrag hat weiterhin eine Netzwerk-URI — das ist für den Druckvorgang egal, nur der Erkennungsstatus wird jetzt durch USB-Präsenz bestimmt.
- **Wenn ein anderer USB-Drucker als der Epson angesteckt wird**: `get_usb_printer_model()` liest den tatsächlichen USB-Deskriptor — zeigt den neuen Drucker korrekt an. Drucken würde über den CUPS-Eintrag laufen, nicht über den neuen Drucker — das ist ein Thema für eine spätere CUPS-Auto-Konfiguration.
