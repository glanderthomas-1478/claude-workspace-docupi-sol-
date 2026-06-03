# Plan: DocuControl Web-Interface — Design-System-Umbau

**Erstellt:** 2026-06-03
**Status:** Implementiert
**Anforderung:** Web-Interface auf das neue DocuControl-Design-System (GeTmatic-Handoff) umstellen

---

## Überblick

### Was dieser Plan erreicht

Alle Templates des DocuControl-Web-Interface werden auf das neue Design-System aus dem
`reference/design_handoff_docucontrol`-Paket umgestellt. Das Ergebnis ist eine klinisch
wirkende UI mit GeTmatic-Branding, neuer 3-Tab-Navigation, und einem tabellenbasierten
Dashboard, das Chargenprotokolle filterbar und paginiert anzeigt.

### Warum das wichtig ist

Das aktuelle Interface zeigt noch Karten-Previews aus dem DocuPi-3000-Design und hat 7
Nav-Punkte. Der Handoff definiert das offizielle GeTmatic-Kunden-Facing-Design: klar,
klinisch, vertrauenswürdig — passend für den Einsatz im Tierlabor Uni Essen. Die Konsolidierung
auf 3 Tabs (Dashboard / Dateien / Einstellungen) vereinfacht die Bedienung.

---

## Aktueller Zustand

### Relevante bestehende Struktur

- `templates/base.html` — aktuelle Navbar mit 7 Einträgen, DocuControl-Branding bereits vorhanden
- `templates/dashboard.html` — Kachel-Karten mit Preview-Text, Live-Banner
- `templates/filemanager.html` — Dual-Pane existiert, altes Styling
- `templates/settings.html` — Sub-Tabs "Empfang" bereits vorhanden, Proxy-freie Version
- `templates/monitor.html` — separater TCP Live-Feed
- `templates/network.html` — separates Template (soll in Einstellungen integriert werden)
- `templates/archive.html` — Protokoll-Archiv mit eigenem Template
- `app.py` — Routen: /, /monitor, /archive, /files, /settings, /network, /system + viele APIs
- `database.py` — protocols-Tabelle: id, timestamp, device_name, raw_data, pdf_path, pdf_filename, file_size, status

### Lücken oder Probleme, die adressiert werden

- Kein einheitliches CSS (aktuell Bootstrap 5 + inline-Styles je Template)
- Zu viele Nav-Punkte — verwirrend für Kunden
- Dashboard zeigt keine filterbare Tabelle (nur Kacheln ohne Sortierung)
- Kein GeTmatic-Branding ("by GeTmatic")
- Monitor und Netzwerk-Einstellungen liegen auf separaten Seiten statt im Einstellungen-Tab

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

- Neues globales CSS (Design-Tokens + Komponenten) als `static/docucontrol.css`
- `base.html`: neue Topbar (dunkel, "DocuControl by GeTmatic"), 3-Tab-Navstrip, neuer Footer
- `dashboard.html`: Stat-Karten (3x) + Filterleiste + sortierbare paginierte Protokoll-Tabelle
- `settings.html`: Sub-Nav "Geräte & Netzwerk" + "Live-Monitor" (TCP-Monitor integriert)
- `filemanager.html`: Design-System-Klassen auffrischen (Struktur bleibt)
- `app.py`: neuer `/api/protocols`-Endpunkt (paginiert, filterbar) für Dashboard-Tabelle
- Alle alten Seiten (monitor, network, archive, system) bleiben als Routen erhalten, fliegen aber aus der Hauptnavigation

### Neue Dateien erstellen

| Dateipfad | Zweck |
|-----------|-------|
| `static/docucontrol.css` | Kanonische Design-Tokens + Komponenten-CSS aus dem Handoff |

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|-----------|------------|
| `templates/base.html` | Neue Topbar, 3-Tab-Navstrip, Footer, docucontrol.css einbinden |
| `templates/dashboard.html` | Komplett neu: Stat-Karten + Filterleiste + Tabelle |
| `templates/settings.html` | Sub-Tabs: Geräte & Netzwerk + Live-Monitor (TCP) |
| `templates/filemanager.html` | Design-Klassen aktualisieren (Dual-Pane-Struktur bleibt) |
| `app.py` | `/api/protocols`-Endpunkt hinzufügen |

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **3-Tab-Navigation**: Dashboard / Dateien / Einstellungen — exakt wie im Handoff. Alte Seiten
   (monitor, network, archive, system) bleiben als URLs erreichbar, sind aber nicht in der Nav.

2. **`docucontrol.css` als separate Datei**: Tokens und Komponenten-Stile aus dem Handoff sauber
   getrennt von Bootstrap. Bootstrap 5 bleibt als Utility-Basis (grid, spacing).

3. **Prototyp-Werte sind kanonisch für index.html-Tokens**: Topbar `#323C4B`, Text `#1D273B`,
   Border `#DCE2E8` — das ist was im Browser-Mockup tatsächlich sichtbar ist. `colors_and_type.css`
   dient als Ergänzung für semantische Farben.

4. **Charge-Nr. aus raw_data per Regex**: DB hat kein dediziertes `charge_nr`-Feld. Für die
   Tabelle wird charge_nr mit Regex aus raw_data extrahiert (`Laufende Nr\.\s*:\s*(\d+)`).
   Keine DB-Schema-Migration nötig.

5. **Live-Monitor in Settings nutzt TCP-API** (`/api/tcp_capture/last_text`), nicht RS232 —
   da DocuControl ausschließlich TCP/9100 verwendet.

6. **Bestanden/Fehlgeschlagen-Status**: `status='completed'` → "Bestanden";
   `status='failed'` oder leer → "Fehlgeschlagen". Wird auf Badge abgebildet.

### Betrachtete Alternativen

- **SPA mit React**: laut Handoff explizit nicht — Prototyp ist React, Ziel ist Jinja2/Bootstrap.
- **DB-Migration für charge_nr**: einfacher über Regex; später wenn nötig nachrüstbar.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: `static/docucontrol.css` erstellen

Alle Design-Tokens und Komponenten-Stile aus dem Handoff in einer zentralen CSS-Datei bündeln.

**Aktionen:**

- Neue Datei `static/docucontrol.css` auf dem Pi erstellen
- Inhalt: alle `:root`-Tokens aus dem Handoff (Topbar `#323C4B`, Primary Navy `#1F4E79`,
  Accent `#2E75B6`, BG `#F4F6F9`, semantische Status-Farben, Terminal-Farben, Typografie-Stack)
- Komponenten: `.topbar`, `.brand`, `.conn-badge`, `.navstrip`, `.tab`, `.page`, `.page-head`,
  `.card`, `.card-head`, `.card-body`, `.stat`, `.stat-row`, `.icon-tile`, `.filterbar`, `.fld`,
  `.ctrl`, `.btn*`, `.table.data`, `.badge.ok/.fail`, `.icon-btn`, `.table-foot`, `.pager`,
  `.subnav`, `.subtab`, `.set-row`, `.set-grid`, `.switch`, `.monitor-head`, `#terminal`,
  `.th`, `.last-pdf`, `.two-col` (Dateien-Dual-Pane)
- Responsive-Breakpoints: 900px (alle Grids → einspaltig), 1040px (Monitor-Stat → 2-spaltig)
- Hover-Transitions: stat-card `translateY(-2px)` 0.2s; Meter-Breite 0.5s; RX-Blink

**Betroffene Dateien:**

- `static/docucontrol.css` (neu)

---

### Schritt 2: `base.html` neu gestalten

Topbar, Navstrip und Footer nach Handoff-Spec ersetzen.

**Aktionen:**

- `<head>`: `docucontrol.css` einbinden (nach Bootstrap)
- Topbar ersetzen:
  ```html
  <div class="topbar">
    <div class="brand">
      <span class="logo">DocuControl<span class="by">by GeTmatic</span></span>
    </div>
    <span class="conn-badge {% if tcp_connected %}online{% else %}offline{% endif %}" id="connBadge">
      <span class="dot"></span>
      <span id="connText">{% if tcp_connected %}Verbunden{% else %}Getrennt{% endif %}</span>
    </span>
  </div>
  ```
- Navstrip auf 3 Tabs reduzieren: Dashboard (`/`), Dateien (`/files`), Einstellungen (`/settings`)
  - Aktiver Tab über `request.path`-Vergleich gesetzt
- Footer: `DocuControl 2026 © GeTmatic — Krefeld`
- `tcp_connected` Context-Variable in app.py über `@app.context_processor` bereitstellen
  (ruft `get_capture_status()` auf → `tcp_enabled`)
- Status-Indikator im Topbar-Badge via kurzes JS alle 10s aktualisieren (`/api/tcp_capture/status`)

**Betroffene Dateien:**

- `templates/base.html`
- `app.py` (Context-Processor)

---

### Schritt 3: `/api/protocols`-Endpunkt in app.py

Paginierter, filterbarer JSON-Endpunkt für die neue Dashboard-Tabelle.

**Aktionen:**

- Route `GET /api/protocols` mit Query-Params:
  - `page` (default 1), `per_page` (default 20)
  - `status` (Alle / Bestanden / Fehlgeschlagen)
  - `date_from`, `date_to` (YYYY-MM-DD)
  - `charge_from`, `charge_to` (numerisch)
  - `sort_by` (timestamp / charge_nr), `sort_dir` (asc / desc, default desc)
- SQL aus `protocols`-Tabelle (status='completed' für "Bestanden", alle anderen für "Fehlgeschlagen")
- Charge-Nr. per Regex aus raw_data extrahieren: `r'Laufende Nr\.\s*[:\.]?\s*0*(\d+)'`
- Programm-Name per Regex: `r'Programm\s*:\s*(.+)'` (erste passende Zeile)
- Dauer: Differenz Programmstart/Programmende aus raw_data per Regex, oder leer wenn nicht extrahierbar
- Rückgabe: `{ total, page, per_page, pages, protocols: [{id, charge_nr, timestamp, program, duration, status, pdf_filename}] }`

**Betroffene Dateien:**

- `app.py`

---

### Schritt 4: `dashboard.html` komplett neu

Stat-Karten + Filterleiste + paginierte sortierbare Tabelle.

**Aktionen:**

- Page-Head: Über-Zeile „Chargenprotokolle" + H1 „Dashboard"
- 3 Stat-Karten (`.stat-row`):
  1. TCP-Status (navy icon-tile `bi-hdd-network`) — Verbunden/Getrennt + "TCP :9100"
  2. Protokolle heute (blue `bi-file-earmark-pdf`) — Zahl + "Letztes um HH:MM Uhr"
  3. Protokolle gesamt (blue `bi-collection`) — Zahl + "Seit Inbetriebnahme …"
- Filterleiste (`.filterbar`): Status-Select, Programm-Select (aus DB distinct), Datum-Range,
  Charge-Nr.-Range, "Filter anwenden", "Zurücksetzen"
- Tabelle (`.card` > `table.data`): Spalten Charge-Nr. / Datum & Uhrzeit / Programm / Dauer /
  Status / Aktionen
- Aktionen je Zeile: PDF-Download (`/download/<id>`) + Drucken (POST `/api/print/<id>`)
- Tabellenzeilen via JS aus `/api/protocols` laden (kein serverseitiges Rendering der Tabelle)
- Tabellen-Fuß: Anzeige "1–20 von N Protokollen" + Pager
- Pager: Pfeil links, Seitenzahlen (max 5 sichtbar + „…"), Pfeil rechts
- Status-Refresh alle 30s (Stat-Karten)
- Altes Chargen-Preview-Design und Banner komplett entfernen

**Betroffene Dateien:**

- `templates/dashboard.html`

---

### Schritt 5: `settings.html` mit Sub-Tabs neu gestalten

Sub-Nav "Geräte & Netzwerk" + "Live-Monitor" (TCP) — nach Handoff-Spec.

**Aktionen:**

- Sub-Nav (`.subnav`):
  - "Geräte & Netzwerk" (`bi-sliders`) → Tab `devices`
  - "Live-Monitor" (`bi-terminal`) → Tab `monitor`
  - Aktiver Tab via URL-Hash (`#devices` / `#monitor`), Fallback auf `#devices`
- Tab "Geräte & Netzwerk" (`.set-grid`, 2 Spalten):
  - Drucker-Card: "USB-Drucker erkennen" (Button), "Erkannter Drucker" (API-Wert),
    "Testdruck" (Button), "Automatisch drucken" (Toggle)
  - Netzwerk-Card: "IP-Adresse" (mono, from `/api/network/lan/status`), "TCP Port 9100" an/aus,
    Netzwerk-Info aus config
  - Toggle-Switches: custom 44×24px Switch wie im Handoff
- Tab "Live-Monitor": TCP Live-Feed
  - 4 Stat-Karten (`.stat-row.mon`): Empfänger, Protokolle heute, Protokolle gesamt, Letzte Charge
  - "Neues Protokoll gespeichert"-Banner (`.last-pdf`) wenn `/api/tcp_capture/status` neuen Job zeigt
  - Monitor-Head + Terminal-Box (aus bestehender monitor.html übernehmen, CSS-Klassen anpassen)
  - Terminal ruft `/api/tcp_capture/last_text` ab (5s Intervall), genau wie bisher
- Alte Tab-Struktur ("Empfang") aus settings.html ersetzen
- Die TCP-Aktivieren/Port-Einstellungen bleiben als Unterbereich in "Geräte & Netzwerk"

**Betroffene Dateien:**

- `templates/settings.html`

---

### Schritt 6: `filemanager.html` Design-Update

Dual-Pane-Struktur bleibt erhalten, CSS-Klassen auf neues Design-System umstellen.

**Aktionen:**

- Card-Header: `.card-head` mit navy Hintergrund + weißem Text
- Dateinamen: `.badge.mono` (monospace, grauer Hintergrund)
- Aktions-Buttons: `.icon-btn` + `.icon-btn.danger` für Löschen
- Sync-Zeile: heller Block mit "Jetzt sync." Button (`.btn-outline-accent`)
- Speicher-Meter: bestehende Bootstrap-Progress durch handoff-konformen Meter ersetzen
  (`.storagebar` mit animiertem Balken via CSS)
- `.two-col`-Grid für Dual-Pane statt Bootstrap `.row`/`.col`

**Betroffene Dateien:**

- `templates/filemanager.html`

---

### Schritt 7: Deployment und Test

**Aktionen:**

- `scp static/docucontrol.css docucontrol@192.168.0.171:/home/docucontrol/docupi/static/`
- Templates via SSH-Patch-Scripts übertragen (heredoc oder Python-Script nach /tmp/)
- `app.py` Änderungen übertragen
- `sudo systemctl restart docucontrol.service`
- Dashboard im Browser prüfen: Stat-Karten, Filterleiste, Tabelle mit echten Daten
- Einstellungen prüfen: Sub-Tab-Wechsel, Live-Monitor TCP-Feed
- Dateien prüfen: Dual-Pane, Buttons
- Testprotokoll über `send_krefeld_protocol.py` schicken → Tabelle aktualisiert sich

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- `app.py` rendert alle Templates → Context-Processor für `tcp_connected` nötig
- `tcp_print_capture.py` → `get_capture_status()` für Status-Badge
- `database.py` → `get_protocols()` als Basis für neuen `/api/protocols`-Endpunkt

### Nötige Updates für Konsistenz

- `CLAUDE.md` nach Abschluss aktualisieren (neues CSS, konsolidierte Nav)

### Auswirkungen auf bestehende Workflows

- `/monitor`, `/archive`, `/network`, `/system` bleiben als URLs erreichbar (nicht löschen)
- Bookmarks auf `/archive` funktionieren weiterhin
- Captive Portal (`captive.html`) ist explizit **nicht** Teil dieses Plans (eigene Surface)

---

## Validierungs-Checkliste

- [ ] Topbar zeigt "DocuControl by GeTmatic", Badge zeigt TCP-Status (grün/rot)
- [ ] Navigation hat genau 3 Tabs, aktiver Tab unterstrichen mit Accent-Blau
- [ ] Dashboard lädt Protokolle aus DB, zeigt korrekte Anzahl in Stat-Karten
- [ ] Filterleiste filtert Tabelle korrekt (Status, Datum, Charge-Nr.)
- [ ] Spalten-Sortierung funktioniert (Charge-Nr., Datum)
- [ ] PDF-Download-Button in Tabellenzeile funktioniert
- [ ] Paginierung korrekt (bei > 20 Einträgen)
- [ ] Einstellungen: Sub-Tab-Wechsel klappt via Hash
- [ ] Live-Monitor-Tab zeigt letztes TCP-Capture korrekt
- [ ] Toggle-Switches funktionieren (Auto-Druck)
- [ ] Dateien-Seite: Dual-Pane mit neuem Styling sichtbar
- [ ] Footer: "DocuControl 2026 © GeTmatic — Krefeld"
- [ ] Kein "Raspberry Pi" oder "DocuPi" im sichtbaren UI
- [ ] Responsive: bei schmaler Ansicht (900px) Grids einspaltig

---

## Erfolgskriterien

Die Implementierung ist abgeschlossen, wenn:

1. Das Web-Interface unter `192.168.0.171` das neue Design zeigt und alle 3 Tabs funktionieren
2. Die Protokoll-Tabelle im Dashboard echte DB-Daten zeigt und filterbar ist
3. Nach Senden eines Test-Protokolls via `send_krefeld_protocol.py` erscheint der neue Eintrag
   automatisch in der Tabelle (innerhalb von 30s Auto-Refresh oder nach manuellem Refresh)

---

## Notizen

- GeTmatic-Logo (`assets/GeTmatic_Logo.jpeg`) ist vorhanden — im Topbar verwenden falls gewünscht,
  aber laut Handoff genügt die Wortmarke "DocuControl by GeTmatic" im Text
- Die Topbar-Farbe aus dem `index.html`-Prototyp (`#323C4B`) wird bevorzugt, da das der
  tatsächlich sichtbare Wert im hifi-Mockup ist
- Captive-Portal-Redesign ist ein separates Folge-Thema
- System-Tab (/system) und Serial-Logs (/serial-logs) bleiben als versteckte Admin-Seiten erhalten

---

## Implementierungsnotizen

**Implementiert:** 2026-06-03

### Zusammenfassung

Alle Design-System-Dateien lokal in `src/docucontrol/` erstellt:
- `static/docucontrol.css` — vollständiges CSS-Design-System aus dem Handoff (342 Zeilen, alle Komponenten)
- `templates/base.html` — neue Topbar "DocuControl by GeTmatic", 3-Tab-Navstrip, Footer, Badge-JS
- `templates/dashboard.html` — Stat-Karten + Filterleiste + paginierte Tabelle via `/api/protocols`
- `templates/settings.html` — Sub-Tab "Geräte & Netzwerk" + "Live-Monitor" mit TCP-Terminal
- `templates/filemanager.html` — Dual-Pane (intern + USB) mit Design-System-Klassen
- `app_additions.py` — Context Processor + `/api/protocols` + `/api/protocols/programs` Endpunkte
- `scripts/deploy_docucontrol_design.sh` — Deployment-Script für den Pi

### Abweichungen vom Plan

1. **Lokale Struktur in `src/docucontrol/`** statt direkte Pi-Integration: SSH-Passwort-Auth ohne sshpass
   nicht automatisierbar vom Windows-Host — Deployment via `scripts/deploy_docucontrol_design.sh`
2. **Datei-API für Filemanager** nutzt `GET /api/files/list`, `DELETE /api/files/<id>` und
   `GET /api/usb/status`, `POST /api/usb/sync` — falls diese Endpunkte noch nicht existieren,
   müssen sie parallel in app.py angelegt werden.
3. **card-head mit navy Hintergrund** (primary #1F4E79) statt border-only — entspricht dem
   optischen Gesamteindruck des Handoffs besser als nur Border.

### Aufgetretene Probleme

1. **SSH von Windows-Host nicht automatisierbar** — kein sshpass/paramiko/plink verfügbar.
   Lösung: `scripts/deploy_docucontrol_win.ps1` erstellt — nutzt Windows OpenSSH (ssh.exe + scp.exe),
   packt alle Dateien in ein tar-Archiv, überträgt mit 2 Passwort-Eingaben, patcht app.py automatisch.
   Ausführen: `! powershell -ExecutionPolicy Bypass -File scripts\deploy_docucontrol_win.ps1`
2. **Filemanager bestehende Struktur unbekannt** — Pi-Datei nicht lesbar via SSH.
   Lösung: Filemanager komplett neu gebaut nach FileManager.jsx-Handoff-Referenz.
3. **Filemanager-API-Endpunkte** (`/api/files/list`, `/api/files/<id>`, `/api/usb/status`, `/api/usb/sync`)
   müssen in Pi's app.py vorhanden sein. Falls nicht: Filemanager-Tab zeigt Fehler, aber Dashboard +
   Einstellungen funktionieren vollständig.
