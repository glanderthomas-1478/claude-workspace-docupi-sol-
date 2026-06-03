# Handoff: DocuControl Web-Interface (DocuPi-3000)

> Entwickler-Übergabepaket für die Implementierung in einer echten Codebasis (z. B. mit Claude Code).
> **Sprache der Oberfläche: Deutsch.** Alle Labels, Buttons, Hinweise und Toasts bleiben deutsch.

---

## Überblick

DocuControl ist die lokale Web-Oberfläche des **DocuPi-3000** — ein Raspberry-Pi-Gerät, das
Sterilisator-/Autoklav-Chargenprotokolle über RS232 / S-Bus ausliest, ein **Echtzeit-Dashboard**
im Browser anzeigt (lokales WLAN / Hotspot) und archivierbare **PDF-Chargenprotokolle** erzeugt.
Techniker erreichen das Gerät über einen Laptop-Browser oder ein Smartphone im geräteeigenen Hotspot.

- **Anbieter / Marke:** GeTmatic — Thomas Glander, Krefeld (*Steuerung · Antriebe · Visualisierung*)
- **Produkt-Stack im Original:** Flask + Jinja2 + Bootstrap 5 + Socket.IO, ausgeliefert vom Pi
- **Erste Kunden:** Uniklinik Essen; Feldtest Helios Krefeld (Belimed 9-6-18 HS2)
- **Charakter:** klar, vertrauenswürdig, **klinisch** — wie eine Medizingeräte-UI. Keine Verläufe,
  keine dekorativen Spielereien, dicht aber gut lesbar.

Das Web-Interface hat **drei Hauptbereiche**: Dashboard (Chargenprotokoll-Tabelle + Statuskarten),
Dateien (Dual-Pane SD ↔ USB), Einstellungen (Geräte & Netzwerk + serieller Live-Monitor).

---

## Über die Design-Dateien

Die Dateien in diesem Bundle sind **Design-Referenzen, erstellt in HTML/React** — Prototypen, die
das beabsichtigte Aussehen und Verhalten zeigen, **kein Produktionscode zum 1:1-Kopieren**.

Aufgabe: Diese HTML-Designs in der **bestehenden Umgebung der Zielcodebasis** nachbauen (React, Vue,
Jinja2-Templates, native usw.) mit deren etablierten Mustern und Bibliotheken. Das Original-Produkt
ist eine **Flask-/Jinja2-/Bootstrap-5-App** — wenn ihr in diese Codebasis zurückspielt, übersetzt die
React-Komponenten in Jinja2-Partials + Bootstrap-Klassen. Falls noch keine Umgebung existiert, das
geeignetste Framework wählen und die Designs dort umsetzen.

Die Prototypen sind in **React (Babel-im-Browser)** geschrieben, weil das die schnellste Form für ein
klickbares Mockup war — **nicht** weil das Zielprodukt React ist. Das Original läuft serverseitig
gerendert.

---

## Fidelity: **High-Fidelity (hifi)**

Pixelgenaue Mockups mit finalen Farben, Typografie, Abständen und Interaktionen. Die exakten
Werte stehen unten unter „Design-Tokens" und sind in `colors_and_type.css` hinterlegt. UI bitte
pixelgenau mit den Bibliotheken/Mustern der Zielcodebasis nachbauen.

> **Wichtiger Hinweis zu zwei Token-Quellen:** Das Prototyp-`index.html` definiert seine eigenen
> CSS-Variablen inline (etwas andere Werte, z. B. ein dunkleres Topbar-Grau `#323C4B`). Die
> **kanonische** Token-Quelle des Design-Systems ist `colors_and_type.css` (Navbar-Navy `#1f4e79`).
> Wo sich beide unterscheiden, sind beide Werte unten dokumentiert — im Zweifel
> `colors_and_type.css` als verbindlich nehmen, das ist aus dem echten Produkt rückentwickelt.

---

## Screens / Views

Gemeinsamer Rahmen für alle drei Views:

- **Topbar** (dunkel, Höhe 58px): links Wortmarke „DocuControl" + „by GeTmatic"; rechts ein
  Verbindungs-Badge (Pille mit farbigem Punkt — grün „Verbunden" / rot „Getrennt"). Klick auf die
  Marke springt zum Dashboard; Klick auf das Badge schaltet den Verbindungsstatus um.
- **Nav-Strip** (weiß, untere Hairline): Tabs „Dashboard / Dateien / Einstellungen" mit
  Bootstrap-Icon. Aktiver Tab: navy Text, 2px accent-blaue Unterstreichung, 600er Schrift.
- **Page-Shell:** `max-width: 1320px`, zentriert, Padding `26px 28px 40px`. Seitenkopf = kleine
  uppercase „Über-Zeile" (muted) + große H1 (22px / 700).
- **Footer:** dunkel, zentriert, „DocuControl 2026 © GeTmatic — Krefeld", 12px.

### 1. Dashboard (`Dashboard.jsx`)
- **Zweck:** Überblick über erzeugte Chargenprotokolle; Schnellzugriff auf PDF/Druck pro Charge.
- **Layout:**
  - **Statuskarten-Reihe** — Grid `repeat(3, 1fr)`, gap 18px, margin-bottom 20px.
    1. *Verbindungsstatus* (navy Icon-Tile `bi-plug`) — großer farbiger Status mit Punkt
       („Verbunden"/„Getrennt"), Subtext `/dev/ttyUSB0 · 9600 Baud · 8N1`.
    2. *Protokolle heute* (blaues Tile `bi-file-earmark-pdf`) — große Zahl „18", Subtext „Letztes um 14:52 Uhr".
    3. *Protokolle gesamt* (blaues Tile `bi-collection`) — „327", Subtext „Seit Inbetriebnahme 24.01.2026".
  - **Filterleiste** — heller Block (`#eef1f5`), border + radius 9px. Felder (flex, align-end, gap 14px):
    Status-Select, Programm-Select, Datum-Range (zwei `input[type=date]` mit „bis"), Charge-Nr.-Range
    (zwei `input[type=number]`), Spacer, dann Primär-Button „Filter anwenden" (`bi-funnel`) + Outline-Button
    „Zurücksetzen" (`bi-arrow-counterclockwise`, setzt Felder zurück).
  - **Protokoll-Tabelle** in einer Card: Spalten *Charge-Nr.* (fett, navy, mit Sortier-Icon — aktive
    Spalte zeigt `bi-arrow-down`, inaktive `bi-chevron-expand`), *Datum & Uhrzeit* (zweizeilig:
    fett + muted), *Programm*, *Dauer* (tabular-nums), *Status* (Badge), *Aktionen* (rechtsbündig:
    Icon-Buttons PDF + Drucken).
  - **Status-Badges:** Pille mit 7px-Punkt. „Bestanden" = grün-soft Hintergrund / grüner Punkt;
    „Fehlgeschlagen" = rot-soft / roter Punkt.
  - **Tabellen-Fuß:** „1–20 von **327** Protokollen" links; Pager rechts (Pfeil, 1·2·3·…·17, Pfeil;
    aktive Seite navy gefüllt).
- **Beispieldaten:** 8 Chargen `CH021660`–`CH021667`, Programme „Instrumente 134 °C",
  „Bowie-Dick-Test", „Vakuumtest (VPR)", „Textilien 121 °C", eine fehlgeschlagene Charge (`CH021663`).

### 2. Dateien (`FileManager.jsx`)
- **Zweck:** PDF-Protokolle vom internen Speicher auf USB sichern; Übersicht über beide Speicher.
- **Layout:** zwei Karten nebeneinander (`grid 1fr 1fr`, gap 18px, align-start).
  - **Interner Speicher** (Card-Head `bi-hdd`): Speicherbalken („Belegt — 12,4 GB / 32 GB",
    Meter 39%), darunter Dateitabelle (Spalten Dateiname / Datum / Größe / Aktionen).
  - **USB / Externer Speicher** (Card-Head `bi-usb-drive` + rechts USB-Status „Verbunden" mit
    grünem Punkt): Speicherbalken („3,1 GB / 16 GB", 19%), Dateitabelle, darunter **Sync-Zeile**
    (heller Block): „Synchronisation" + grünes „Aktuell" (`bi-check-circle-fill`) + Spacer +
    Outline-Button „Jetzt sync." (`bi-arrow-repeat`).
  - **Dateinamen** monospace, mit rotem `bi-file-earmark-pdf-fill`. Aktionen pro Zeile:
    Download (Icon-Button) + Löschen (roter Icon-Button).
  - Dateinamen-Muster: `CH021667_Instrumente_134C_2026-04-13.pdf`. Größen mit Dezimalkomma (`48,2 KB`).

### 3. Einstellungen (`Settings.jsx`)
- **Zweck:** Drucker/Netzwerk konfigurieren + laufenden Serienverkehr live beobachten.
- **Sub-Nav:** Pill-Tabs in hellem Container (`#eef1f5`, radius 9px, padding 4px). Aktiver Pill: navy
  gefüllt, weißer Text, leichter Schatten. Tabs: „Geräte & Netzwerk" (`bi-sliders`) und „Live-Monitor"
  (`bi-terminal`).
- **Geräte & Netzwerk** — Grid `1fr 1fr`:
  - *Drucker*-Card: Settings-Zeilen (Name + Beschreibung links, Wert/Control rechts, Hairline-Trenner):
    „USB-Drucker erkennen" (Button Suchen), „Erkannter Drucker" (Wert „Brother QL-820NWB"), „Testdruck"
    (Button), „Automatisch drucken bei neuem Protokoll" (**Toggle-Switch**, default an).
  - *Netzwerk*-Card: „IP-Adresse" (mono, navy `192.168.178.83`), „Hotspot-Modus" (Toggle an) +
    Felder SSID `DocuControl-AP` / Passwort, „WLAN-Client" (Status-Pille „Getrennt") + leere SSID/Passwort-Felder,
    Buttons „Verbinden" (primary, `bi-wifi`) + „Netzwerk neu starten" (outline-danger).
- **Live-Monitor** — die **Signatur-Komponente**:
  - 4 Statuskarten (`repeat(4,1fr)`): Empfänger (Status), Protokolle heute (live hochzählend),
    Protokolle gesamt (`toLocaleString('de-DE')` → Tausenderpunkt), Letzte Charge (mono).
  - Optionales grünes „Neues Protokoll gespeichert"-Banner (`last-pdf`, erscheint nach Chargenende).
  - Monitor-Kopf: „Serieller Live-Monitor" (`bi-terminal`), rechts Byte-Zähler-Badge (mono),
    Auto-Scroll-Checkbox, „Leeren"-Button (outline-danger sm).
  - **Terminal:** Titelleiste `#2d2d2d` mit Port-Info + blinkendem grünem RX-Punkt; Body `#1e1e1e`,
    grüner Monospace-Text `#00ff41`, Höhe 42vh, Auto-Scroll. Chargenende-Zeile fett grün;
    PDF-Zeile (`>>> PDF erzeugt:`) fett cyan `#00bcd4`. Bei Trennung: „— Empfänger getrennt —".
  - **Synthetischer Datenstrom** (alle 1100 ms eine Zeile aus `SAMPLE_LINES`): simuliert RS232.
    Bei „ERGEBNIS … FREIGEGEBEN" werden Zähler erhöht, eine PDF-Zeile + Banner erzeugt.

---

## Interaktionen & Verhalten

- **Navigation:** Tab-Klick wechselt View (`useState('dashboard')`); bei View-Wechsel `scrollTo top`.
- **Verbindung umschalten:** Klick aufs Topbar-Badge kippt `connected`. Wirkt sich aus auf:
  Badge-Farbe, Dashboard-Statuskarte, und stoppt/startet den Live-Monitor-Stream.
- **Filter zurücksetzen:** setzt Selects auf Index 0 und Number-Inputs leer (rein clientseitig im Mock).
- **Datei-Auswahl (im Original):** Row-Checkboxen + „Alle auswählen" markieren Zeilen blau
  (`--row-selected #cce5ff`) und aktivieren Download/Kopieren/Löschen. *(Im Mock vereinfacht.)*
- **Live-Monitor:** Intervall-Timer streamt Zeilen; RX-Punkt blinkt 220 ms pro empfangener Zeile;
  Auto-Scroll hält ans Ende gescrollt; „Leeren" leert Puffer + Byte-Zähler. Puffer auf 80 Zeilen begrenzt.
- **Toggle-Switches:** custom 44×24px Switch, grün wenn aktiv, Knopf 18px schiebt 20px.

### Animation (sparsam & schnell — klinisch)
- Statuskarten heben sich beim Hover `translateY(-2px)` über `0.2s`.
- RX-/Live-Punkt: 1s `blink`-Opacity-Loop (`@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }`).
- Meter-Balken animieren Breite über `0.5s`. Keine Bounces, kein Parallax, keine Slide-ins.
- Hover = hellerer/dunklerer Tint; Press = subtil. Selektierte Datei-Zeilen `#cce5ff`.

### Responsives Verhalten
- `max-width: 1040px` → Monitor-Statusreihe auf `repeat(2,1fr)`.
- `max-width: 900px` → alle Grids (Statusreihe, Dateien-Dual-Pane, Settings) einspaltig.

---

## State Management

Im Prototyp (React) genutzt — in der Zielarchitektur entsprechend abbilden (im Original via
Socket.IO/Server-State):

| State | Wo | Beschreibung |
|-------|-----|------|
| `view` | App | aktiver Tab (`dashboard` / `files` / `settings`) |
| `connected` | App | Empfänger-Verbindungsstatus (treibt Badge, Statuskarte, Monitor) |
| `tab` | Settings | Sub-Tab (`devices` / `monitor`) |
| `lines`, `bytes` | LiveMonitor | Terminal-Zeilenpuffer (max 80) + Byte-Zähler |
| `today`, `total`, `lastPdf`, `lastCharge` | LiveMonitor | Zähler, die bei Chargenende hochlaufen |
| `rx`, `autoScroll` | LiveMonitor | RX-Blink-Flag, Auto-Scroll-Schalter |

**Datenanbindung im echten Produkt:** Serielle Daten kommen per WebSocket/Socket.IO vom Pi;
Protokolle/Dateien aus dem Dateisystem; PDF-Erzeugung serverseitig. Im Mock alles synthetisch.

---

## Design-Tokens

Vollständig in `colors_and_type.css` (kanonisch). Auszug:

### Farben — Marke
| Token | Hex | Verwendung |
|-------|-----|------|
| `--docupi-blue` | `#1f4e79` | Primär-Navy: Navbar, Card-Header, Überschriften, Primär-Button |
| `--docupi-light` | `#2e75b6` | Accent-Blau: Links, Sekundär-Icons, Focus-Ring |
| `--docupi-bg` | `#f4f6f9` | App-Hintergrund (kühles Off-White) |

> Prototyp-`index.html` weicht ab: Topbar `#323C4B`, Accent `#2E75B6`, Text `#1D273B`,
> Border `#DCE2E8`. Kanonisch ist `colors_and_type.css`.

### Farben — semantisch / Status
| Token | Hex | Verwendung |
|-------|-----|------|
| `--success` | `#28a745` | Online-Punkt, OK, Meter |
| `--success-strong` | `#198754` | solider Erfolg (Badges/Buttons) |
| `--danger` | `#dc3545` | Offline, Fehler, destruktiv |
| `--warning` | `#ffc107` | USB-Warnungen, Hinweise |
| `--warning-icon` | `#e6a800` | Warn-Icon auf hellem Grund |
| `--info` | `#00bcd4` | Neues-Protokoll-Notiz (Terminal, cyan) |
| Health-Badges | `#d4edda`/`#155724`, `#fff3cd`/`#856404`, `#f8d7da`/`#721c24` | gut / warnung / kritisch (bg/fg) |
| Tints | je Farbe @ 10% Opacity | Hintergrund der Statuskarten-Icon-Tiles |

### Farben — Neutrals (Bootstrap-5-Skala)
`--white #fff` · `--gray-100 #f8f9fa` · `--gray-200 #e9ecef` (Meter-Track, Trenner) ·
`--gray-300 #dee2e6` · `--gray-400 #ced4da` (Input-Border) · `--gray-500 #adb5bd` ·
`--gray-600 #6c757d` (muted) · `--gray-700 #495057` · `--gray-900 #212529` (Body) ·
`--row-selected #cce5ff`.

### Terminal (serieller Monitor + Logs)
`--term-bg #1e1e1e` · `--term-head #2d2d2d` · `--term-border #333` · `--term-green #00ff41` (RX-Text) ·
`--term-orange #ff6600` (Seitenvorschub) · `--term-text #d4d4d4` · Log-Severity:
`--log-warn #ffc107` · `--log-err #ff6b6b` · `--log-info #69c0ff` · `--log-ok #52c41a`.

### Typografie
- **Sans:** `'Segoe UI', system-ui, -apple-system, 'Helvetica Neue', Arial, sans-serif`
  (bewusst der native Windows/Laptop-Look der Techniker).
- **Mono:** `'Courier New', ui-monospace, 'SF Mono', Menlo, monospace` (Terminal, Dateinamen, IP).
- **Skala:** Display 2rem/32px · H1 1.7rem/27px · Stat 1.4rem/22px · H5 1rem/16px · Body 0.95rem/15px ·
  Small 0.85rem/14px · Label 0.75rem/12px (uppercase) · Mono 13px.
- **Gewichte:** 400 Body · 500 medium Labels · 600 Überschriften/Card-Header · 700 Stat-Werte +
  Navbar-Marke (`letter-spacing: 1px`).

> **Segoe UI ist proprietär (Microsoft) und darf nicht gebündelt werden.** Auf Windows-Laptops
> (echtes Ziel) nativ; sonst Fallback `system-ui`/`-apple-system`. Für pixelgenaues Rendering auf
> Nicht-Windows ggf. Lizenz besorgen oder Substitut (z. B. *Source Sans 3*) freigeben.

### Radien
`--radius-sm 8px` (Nav-Pills, Inner-Boxen, Terminal) · `--radius 10px` (Cards, Icon-Boxen) ·
`--radius-lg 12px` (Health-Badges) · `--radius-xl 20px` (Captive-Glass-Card) · `--radius-pill 50%` (Punkte).

### Elevation / Schatten
`--shadow-card 0 2px 8px rgba(0,0,0,.08)` (jede Card) · `--shadow-pill 0 2px 6px rgba(31,78,121,.35)`
(aktiver Settings-Pill) · `--shadow-glass 0 8px 32px rgba(0,0,0,.3)` (Captive) ·
`--shadow-btn 0 4px 15px rgba(0,0,0,.2)` (Captive-Button). **Keine Inset-Schatten.**

### Spacing (Bootstrap-Skala, 0.25rem-Basis)
`--space-1 4px` · `--space-2 8px` · `--space-3 16px` · `--space-4 24px` · `--space-5 48px`.
Grids nutzen `g-3`/`g-4`-Gutter; Cards padden 16–20px.

### Cards & Flächen
Weiß, **kein Border** (im DS) bzw. 1px Hairline (im Prototyp), `border-radius 10px`,
`box-shadow 0 2px 8px rgba(0,0,0,.08)`. Viele Cards haben einen **soliden Navy-Header**
(weißer 600er Text, obere Ecken gerundet). **Hintergründe flach — keine Verläufe, Bilder, Muster.**

> **Einzige Ausnahme: mobiles Captive-Portal** (nicht in diesem Mock) — `135deg` Navy→Hellblau-Verlauf
> + Frosted-Glass-Card (`backdrop-filter: blur(10px)`). Glas/Verlauf **nie** ins Dashboard bringen.

---

## Iconografie

- **Einziges Icon-System: Bootstrap Icons 1.11.2** (Webfont via CDN
  `https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.2/font/bootstrap-icons.css`), inline `<i class="bi bi-…">`.
- **Verwendete Glyphen:** `bi-speedometer2` (Dashboard), `bi-folder2-open` (Dateien), `bi-gear`
  (Einstellungen), `bi-plug` (seriell), `bi-file-earmark-pdf(-fill)`, `bi-collection`, `bi-printer`,
  `bi-hdd`, `bi-usb-drive`, `bi-terminal`, `bi-hdd-network`, `bi-wifi`, `bi-sliders`, `bi-funnel`,
  `bi-arrow-counterclockwise`, `bi-arrow-repeat`, `bi-download`, `bi-trash`, `bi-check-circle-fill`,
  `bi-check2-circle`, `bi-search`, `bi-chevron-expand`, `bi-arrow-down`.
- **Farbe:** Icons erben Textfarbe oder nehmen semantische Farbe; in Statuskarten sitzt das Icon
  auf einer 10%-Tint-Box seiner eigenen Farbe.
- **Kein eigenes SVG-Set, kein PNG-Sprite.** Icons nicht selbst zeichnen — Bootstrap Icons laden.
- **Emoji: im Desktop-UI nicht verwenden.** (Nur im mobilen Captive-Portal: 🖨 ⚠️ ✅ 📋; 📁 als Ordner.)

---

## Assets

| Datei | Beschreibung |
|-------|------|
| `assets/GeTmatic_Logo.jpeg` | GeTmatic-Wortmarke mit farbigem Capability-Balken. Raster-JPEG auf weißem Feld — auf weiße Plates setzen; auf Navy hell behandeln. **Es gibt keine separate DocuControl-Logomarke** — das Produkt wird über die Navbar-Wortmarke („DocuControl" / „DocuPi-3000") + die GeTmatic-Anbietermarke gebrandet. |

Bootstrap Icons + Bootstrap 5.3.2 werden im Original per CDN geladen (Offline-Build müsste die
Font-Dateien lokal vendoren).

---

## Dateien in diesem Bundle

| Pfad | Inhalt |
|------|------|
| `README.md` | Dieses Dokument |
| `colors_and_type.css` | Kanonische Design-Tokens (Farben, Typo, Radien, Schatten, Spacing, Motion) |
| `ui_kit/index.html` | Lauffähiges hifi-Mockup (Shell + eigene CSS-Tokens, lädt die JSX-Komponenten) |
| `ui_kit/Navbar.jsx` | Topbar + Tab-Strip + Verbindungs-Badge |
| `ui_kit/Dashboard.jsx` | Statuskarten + Filterleiste + sortierbare Protokoll-Tabelle |
| `ui_kit/FileManager.jsx` | Dual-Pane Interner Speicher ↔ USB + Sync |
| `ui_kit/Settings.jsx` | Sub-Nav, Geräte/Netzwerk-Formular, serieller Live-Monitor |
| `assets/GeTmatic_Logo.jpeg` | Anbieter-Logo |

**Mockup öffnen:** `ui_kit/index.html` im Browser öffnen (lädt React + Babel + Bootstrap Icons per CDN).

### Nicht nachgebaut (im echten Produkt vorhanden)
Captive-Portal (mobil, das einzige Surface mit Verlauf + Glas), das tatsächlich erzeugte PDF-Protokoll,
sowie Hotspot/USB-Wartung/Logs-Settings-Tabs und die echte WebSocket-/Serien-Anbindung.
