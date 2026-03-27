# Aktuelle Daten

## Projektmetriken

| Metrik | Aktueller Wert | Zielwert | Notizen |
| ------ | -------------- | -------- | ------- |
| Konzeptdokument | Fertig | — | Hardware, Software, Regulatorik, Roadmap |
| Prototyp-Hardware | Komponenten bestellt | Getestet | Raspberry Pi + Sensoren |
| S-Bus/UDP Software | Fertig | — | 9-Dateien-Paket (SQLite, FastAPI, Web-Dashboard) |
| RS232-Protokoll (WD) | Entschluesselt + Parser fertig | Produktionsreif | UTF-16LE Klartext, .ht + RS232 |
| WD-PDF-Generator | Funktionsfaehig | Produktionsreif | Parser, Chart, PDF — 42 Tests gruen |
| MST-PDF-Generator | Funktionsfaehig | Produktionsreif | Mehrere Iterationen (v4-v9) |
| Erste Feldtests | Ausstehend | 1 Test | Im eigenen Arbeitsumfeld moeglich |

## Quellcode-Uebersicht

- `pdf_generator.py` (23 KB) — PDF-Generierung
- `chart_generator.py` (4.5 KB) — Charts
- `print_manager.py` (9.5 KB) — Drucker
- `watchdog_manager.py` (6 KB) — Service-Ueberwachung
- `add_system_health.py` (8 KB) — Health-Metriken
- 15+ `patch_*.py` Dateien — Feature-Erweiterungen
- 3 HTML-Dateien (Dashboard, Base, Captive Portal)

## Hardware

- Raspberry Pi (SSH: belimed@192.168.178.83)
- Ziel-Hardware: Unipi Neuron / RevPi Connect (CE-zertifiziert)
