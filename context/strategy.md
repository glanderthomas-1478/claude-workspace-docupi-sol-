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

### 5. Erster Kunden-Deal (DocuControl, Tierlabor Uni Essen) — WEB-INTERFACE FERTIG

- Vertrieb laeuft verdeckt ueber getmatic / Thomas Glander (Whitelabel)
- Zielmaschine: **Belimed PST 14-8-12 HS1** (bestaetigt 2026-06-08)
- **ERLEDIGT 2026-06-02**: Pi 5 aufgebaut, Service aktiv, TCP/9100-Pipeline produktiv
- **ERLEDIGT 2026-06-03**: Web-Interface v2 deployed (Dashboard, Einstellungen, Datei-Manager, Drucker, USB-Sync)
- **ERLEDIGT 2026-06-09**: Dashboard v3 Liquid-Glass deployed:
  - v3 Design-Handoff von getmatic empfangen und implementiert
  - Machine-Bar (Belimed PST 14-8-12 HS1, 6050/6060 FIS, VAFI/KOST, TCP-Status live)
  - 3 Stat-Karten: Chargen gesamt / heute / Monat (inkl. Vormonat-Trend)
  - Dauer-Spalte + Programm-Icons in Tabelle
  - Liquid-Glass-CSS, Square-Font, Live-Uhr, pulsierender Aktiv-Badge
  - Neuer /api/dashboard/stats Endpunkt
- OFFEN: Einstellungen + Datei-Manager auf v3 migrieren (separater Plan)
- OFFEN: Sample-Druckauftrag vom Tierlabor-Geraet analysieren, Installation vor Ort

## Wie Erfolg aussieht

- ~~Funktionierender Prototyp, der im Feld einsetzbar ist~~ ERREICHT
- ~~RS232-Protokoll entschluesselt und implementiert~~ ERREICHT (MST)
- ~~Erste Feldtests erfolgreich durchgefuehrt~~ ERREICHT (Helios Krefeld)
- Naechster Meilenstein: DocuControl-Pi fertig konfigurieren, Sample-Druckauftrag analysieren, Installation im Tierlabor Uni Essen, Sensoren anschliessen, WD/RDG-Feldtest, Patch-Konsolidierung
