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

## Wie Erfolg aussieht

- ~~Funktionierender Prototyp, der im Feld einsetzbar ist~~ ERREICHT
- ~~RS232-Protokoll entschluesselt und implementiert~~ ERREICHT (MST)
- ~~Erste Feldtests erfolgreich durchgefuehrt~~ ERREICHT (Helios Krefeld)
- Naechster Meilenstein: Sensoren anschliessen, WD/RDG-Feldtest, Patch-Konsolidierung
