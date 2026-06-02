# Strategie

## Aktueller Fokus

Prototyp fertigstellen und erste Feldtests im eigenen Arbeitsumfeld durchfuehren.

## Strategische Prioritaeten

### 1. RS232-Kommunikation — ERLEDIGT (MST)

- MST-Protokollformat entschluesselt (UTF-16LE Klartext ueber RS232)
- Live-RS232-Listener laeuft produktiv (serial_receiver.py)
- Parser + PDF-Generator + Chart-Generator implementiert
- **Erster Feldtest erfolgreich: 3 Wochen, 140 Chargen, 0 Fehler** (Helios Krefeld, Belimed 9-6-18 HS2)
- OFFEN: WD/RDG-Protokoll (WD290/WD390) — separater Parser vorhanden, noch nicht im Feld getestet

### 2. Software stabilisieren — IN ARBEIT

- Feldtest-Fixes deployed (2026-04-13):
  - VPR/Lecktest-Erkennung korrigiert (NICHT STERIL = BESTANDEN)
  - Abbruch-Handling und unvollstaendige Protokolle (Stromausfall)
  - USB Auto-Mount nach Reboot
  - Serial-Port Log-Spam eliminiert (Exponential Backoff)
- OFFEN: Patch-Dateien konsolidieren (15+ separate Patches in app.py integriert)
- OFFEN: Tests automatisieren

### 3. Hardware-Prototyp — ERSTER FELDTEST ABGESCHLOSSEN

- Raspberry Pi 5 lief 3 Wochen am Sterilisator in Krefeld
- RS232-Empfang, PDF-Generierung, WebIF, Hotspot — alles stabil
- 327 Protokolle in DB, 140 PDFs generiert (nach Fix)
- OFFEN: Sensoren (Druck, Strom) noch nicht angeschlossen

### 4. Langfristig: CE-konforme Hardware

- Migration auf Unipi Neuron oder RevPi Connect
- Regulatorik klaeren (kein eigenes Medizinprodukt, nur Diagnosetool)

### 5. Erster Kunden-Deal (DocuControl, Tierlabor Uni Essen) — IN UMSETZUNG

- Vertrieb laeuft verdeckt ueber getmatic / Thomas Glander (Whitelabel)
- Zielmaschine: Geraet im Tierlabor Uni Essen (Typ tbd)
- Ansatz: Pi ersetzt die Printserver-Box, uebernimmt deren IP, fangt Druckauftraege auf TCP/9100 ab
- Zwei Netzwerk-Interfaces: eth0 Maschinen-LAN, USB-Eth Klinik-LAN, WLAN deaktiviert
- Drei Betriebsmodi: Integriert (Klinik-LAN), Hotspot, USB-Export
- Konzeptpapier erstellt (outputs/docupi-3000_konzept_getmatic.{md,pdf})
- **2026-06-02 bei getmatic im Buero (192.168.0.0/24)**:
  - Neuer Pi 5 mit RTC-Modul aufgebaut, OS Debian 13 (Bookworm-Successor)
  - SSH eingerichtet (user docucontrol, key-based)
  - Hostname gesetzt: DocuControl (war DCUETL aus Klon-Image)
  - I2C aktiviert, RTC auf 0x68 erkannt (Chip-Typ Felix-bestaetigung pending — DS3231 vermutet)
  - OFFEN: RTC-dtoverlay setzen, OS-Update, WLAN deaktivieren, DocuPi-Code rueberbringen
- OFFEN allgemein: Sample-Druckauftrag analysieren, ggf. WebIF-Auth + HTTPS implementieren

## Wie Erfolg aussieht

- ~~Funktionierender Prototyp, der im Feld einsetzbar ist~~ ERREICHT
- ~~RS232-Protokoll entschluesselt und implementiert~~ ERREICHT (MST)
- ~~Erste Feldtests erfolgreich durchgefuehrt~~ ERREICHT (Helios Krefeld)
- Naechster Meilenstein: DocuControl-Pi fertig konfigurieren, Sample-Druckauftrag analysieren, Installation im Tierlabor Uni Essen, Sensoren anschliessen, WD/RDG-Feldtest, Patch-Konsolidierung
