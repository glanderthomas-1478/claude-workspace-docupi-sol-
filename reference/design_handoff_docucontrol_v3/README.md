# Handoff: DocuControl 2026 — Dashboard (v3)

## Overview
**DocuControl 2026 by GeTmatic** is a documentation appliance (internal name *DocuPi-3000*, a Raspberry-Pi-based device) that reads sterilization batch protocols from **one specific autoclave — a Belimed PST 14-8-12 HS1** — over its serial data interface (6050/6060 FIS, VAFI/KOST protocol). It stores each completed batch as a PDF and lets hospital/clinic technicians **view, filter, print and manage** those protocols in a laptop browser.

This handoff covers the **v3 web dashboard**: a single-page app with three top-level tabs (**Chargen** / Dateien / Einstellungen) and a settings area with six sub-tabs. Language is **German throughout**.

## About the Design Files
The files in this bundle are **design references created in HTML/CSS/JS** — a working prototype that shows the intended look, layout and behavior. They are **not** meant to be shipped verbatim. The task is to **recreate these designs in the target codebase's environment** (React, Vue, Svelte, etc.) using its established components, state patterns and conventions. If no frontend environment exists yet, pick the most appropriate framework for an embedded-device admin UI (a lightweight React or Svelte SPA served by the device is a natural fit) and implement there.

The prototype's data and most actions are **simulated** (in-memory file lists, a fake serial stream, demo toggles). In production these bind to the device's real filesystem, serial reader and network/printer services.

## Fidelity
**High-fidelity (hifi).** Final colors, typography, spacing, radii, shadows and interactions are all defined. Recreate the UI pixel-faithfully using the codebase's libraries. Exact values are in **Design Tokens** below and in `colors_and_type.css` (the single source of truth for tokens) + `app/docucontrol.css` (component styling). `styles.css` is the entry point that `@import`s both.

The signature visual treatment is **"liquid glass"**: translucent fills, `backdrop-filter: blur(10px) saturate(1.4)`, a top inset highlight (`inset 0 1px 0 rgba(255,255,255,0.85)`), soft colored shadows, and a subtle lift on hover. It is applied with restraint — this is trustworthy medical software, not a flashy consumer app.

---

## Global Chrome (present on every view)

### Topbar (height 58px, sticky)
- Background: vertical gradient `#3a4658 → #323C4B`, white text.
- **Left — brand lockup:** `DocuControl` (19px, weight 700) followed by `by **GeTmatic**`. The word **GeTmatic** is rendered in the brand display font **'Square'** (`--font-brand`); everything else is Segoe UI. "Square" is reserved exclusively for this wordmark — never use it for headings or body.
- **Right cluster (`.topbar-right`, gap 16px):**
  - **Live clock** (`.topbar-clock`): calendar icon + date `DD.MM.YYYY` + `·` + time `HH:MM:SS` (monospace, weight 700, white). Updates every second via `setInterval`. Hidden below 640px.
  - **Status badge** (`.conn-badge.online`): pill, translucent white fill, green dot + text **"Aktiv"**. The green dot **pulses** (`pulse-ready`, 1.3s ease-in-out infinite — a scaling ring + glow). This is the ONE place pulsing is allowed; disabled under `prefers-reduced-motion`.

### Nav strip (sticky under topbar, top:58px)
- Translucent white bar (`rgba(255,255,255,0.75)` + glass blur), bottom border.
- Three tabs, each icon + label: **Chargen** (`bi-collection`), **Dateien** (`bi-folder2-open`), **Einstellungen** (`bi-gear`).
- Active tab: primary navy text (`#1f4e79`), weight 600, 2px bottom border in accent blue (`#2e75b6`). Inactive: muted gray, navy on hover.

### Footer
- Dark bar (`#323C4B`), centered 12px muted text: `DocuControl 2026 © **GeTmatic** — Krefeld` ("GeTmatic" in the Square font).

### Page shell
- `.page` max-width **1340px**, centered, padding `26px 28px 30px`.
- Each tab is a `.view`; only `.view.active` is shown (`display:block` with a 0.25s fade-up entrance).
- Page header: tiny uppercase overline (muted) + `<h1>` (23px/700) + optional muted lede line.

---

## Screens / Views

### 1. Chargen (Dashboard — default active)
Purpose: the technician's home — browse/filter/print stored batches.

**a) Machine identity bar** (`.machine-bar`, full width, above stat cards)
- Layout: flex row, gap 16px. Card with translucent white + faint blue gradient fill, 1px border, radius 14px, padding `14px 18px`, small shadow. **No** left accent stripe.
- Contents left→right:
  - Icon tile (48px, radius 12px, navy tint fill, glass highlight) with `bi-safe2`.
  - Machine name: **"Belimed PST 14-8-12 HS1"** (18px, weight 700). No label above it.
  - Chips (`.chip`, pill, translucent white, 12px/600): `bi-diagram-3` **6050 / 6060 FIS** · `bi-file-earmark-code` **VAFI / KOST**.
  - Right: status plaque (`.mb-status`) — **solid** green pill (`--success-soft` fill, success-green border), `bi-hdd-network-fill` icon + **"Maschine verbunden"**. Static, NO animation (intentional — pulsing lives only in the topbar).

**b) Stat cards** (`.stat-row`, 3-column grid, gap 18px)
Each `.stat`: white + translucent gradient, 1px border, radius 14px, padding `18px 20px`, hover lifts -2px with bigger shadow. Top-right 44px glass icon tile. Big value 34px/700 tabular-nums.
1. **Chargen gesamt** — `bi-hash` (navy tile) — value **21.667** — sub "Höchster Chargenzähler der Maschine".
2. **Chargen heute** — `bi-calendar-day` (blue tile) — value **18** — sub "Letzte um 14:52 Uhr".
3. **Chargen diesen Monat** — `bi-calendar3` (green tile) — value **342** — sub: green up-trend "↑ 6,2 %" + "ggü. Vormonat".

**c) Filter bar** (`.filterbar`, flex-wrap, light grey-blue gradient panel, radius 12px, padding `14px 16px`)
Fields (each `.fld` = uppercase 11px label + `.ctrl`): **Status** select (Alle/Bestanden/Fehlgeschlagen) · **Programm** select (Alle/Instrumente 134 °C/Bowie-Dick-Test/Vakuumtest (VPR)/Textilien 121 °C) · **Datum** date-range (von … bis) · **Charge-Nr.** number-range (von … bis). Flex spacer, then **"Filter anwenden"** (primary glass button, `bi-funnel`) + **"Zurücksetzen"** (clear glass button, `bi-arrow-counterclockwise`; clears the bar's selects/inputs).

**d) Protocol table** (the hero — `.card` > `.table-wrap` > `table.data`)
- Header row: th background `#E6EBF0`, 11px uppercase muted, sortable (cursor pointer, sort chevron icons). First column **"Charge-Nr."** is the active sort (`.sorted`, down-arrow) — descending by default.
- Columns: **Charge-Nr.** | **Datum & Uhrzeit** | **Programm** | **Dauer** | **Status** | **Aktionen** (right-aligned).
- Charge cell: bold navy id (e.g. `CH021667`). Datum: main date + muted sub time. Programm: small accent icon + name. Dauer: tabular `HH:MM:SS`.
- Status: pill badge — `.badge.ok` (green-soft fill, dot + **"Bestanden"**) or `.badge.fail` (red-soft fill, dot + **"Fehlgeschlagen"**).
- Aktionen: two 34px glass icon-buttons — `bi-file-earmark-pdf` (download) + `bi-printer` (print). Hover tints accent blue.
- Rows: alternating white / `#FAFBFC`, hover light-blue `#eef4fb`.
- 8 sample rows: CH021667→CH021660, mostly Bestanden, **CH021663 is Fehlgeschlagen**, programs vary across the four types.
- Footer (`.table-foot`): left "1–20 von **21.667** Protokollen", right pager (`«` disabled, **1** active, 2, 3, …, 1084, `»`).

### 2. Dateien (file manager — TotalCommander style)
Purpose: move/copy/delete protocol PDFs between internal storage and a USB stick.

**Toolbar** (`.fm-toolbar`): **Kopieren nach [USB/Intern]** (`#btnCopy`) · **Verschieben** (`#btnMove`) · **Löschen** (`#btnDelete`, outline-danger) · **Aktualisieren** (`#btnRefresh`, small; spins its icon 360° on click). Right hint: "Klick markiert · Strg/⌘+Klick für Mehrfachauswahl". The copy/move buttons' arrow icon flips direction depending on which pane is focused; disabled when nothing selected or target USB is disconnected.

**Two panes** (`.fm-grid`, 2-column grid). Each `.pane` (white card, radius 12px); the **focused** pane gets an accent ring (`box-shadow 0 0 0 3px rgba(46,117,182,0.14)`).
- **Left — Interner Speicher** (`#pane-internal`, `bi-hdd`): storage meter "12,4 GB / 32 GB", then a sticky-header file table (Dateiname / Datum / Größe / Aktionen). 10 sample PDFs (mono filenames like `CH021667_Instrumente_134C_2026-04-13.pdf`). Focused by default.
- **Right — USB / Externer Speicher** (`#pane-usb`, `bi-usb-drive`): a connection status pill in the head (`.usb-status` green dot "Verbunden" / grey "Getrennt") + a **"USB trennen (Demo)"** toggle button. Storage "3,1 GB / 16 GB". 3 sample files. When disconnected, the list is replaced by an empty state (`bi-usb-drive` + "Kein USB-Speicher verbunden…").
- File rows: `bi-file-earmark-pdf-fill` (red) + mono filename, date (muted), size in KB (right), and per-row download + delete (`bi-trash`, danger) icon-buttons. Selected rows get `.sel` (light-blue `#d8e8fb`).
- Pane footer: left file count, right selection summary ("N markiert · X KB").

**Selection model:** plain click selects single (click again deselects); Ctrl/⌘-click toggles within a multi-selection. Clicking a pane sets it as focused.

**Delete confirmation modal** (`#modalDelete`): danger icon, title "Protokolle löschen?", body naming the count + source location, a scrollable mono mini-list of the affected filenames, and "Abbrechen" / "**N löschen**" (danger) buttons. **Every delete — row icon or toolbar — routes through this confirmation.** Copy/Move happen immediately (no modal).

### 3. Einstellungen (settings — sub-tab layout)
Layout `.set-layout`: a 232px sticky left **sub-nav** (`.subnav`) + content. Active sub-button uses the navy glass gradient with white text. Six sub-tabs:

**a) Live Monitor** (`#sub-monitor`, default) — the integrated serial monitor (replaces the old standalone app).
- Card head: title + a static green "Verbunden" pill.
- Monitor head row: port `/dev/ttyUSB0`, `9600 Baud · 8N1`, an **Auto-Scroll** switch, **Pause** (`#monPause`), **Leeren** (`#monClear`).
- Terminal (`.term`): dark `#1e1e1e` body, mac-style window bar (3 lights + title "sterilisator — RX-Stream" + blinking green "LIVE"). Monospace log lines, color-coded by class: `.l-rx` green, `.l-info` blue, `.l-ok` green-bright, `.l-warn` amber, `.l-err` red, `.l-feed` orange, timestamps grey. Lines stream in every 1.6s from a sample script; capped at 200; auto-scrolls when enabled. Starts/stops when the sub-tab is shown/hidden.
- Below: a blue info banner explaining new completed batches auto-save and appear under Chargen.

**b) Maschine** (`#sub-machine`) — machine info (mirrors the dashboard's machine bar).
- Repeats the `.machine-bar` at top, then a **Maschineninformationen** card with a 2-column definition list: Hersteller **Belimed** · Maschinentyp **PST 14-8-12 HS1** · Datenschnittstelle **6050 / 6060 FIS** · Protokollformat **VAFI / KOST** · Maschinentyp-Klasse "Dampf-Großsterilisator" · Verbindung `/dev/ttyUSB0 · 9600 8N1` · Status (green "Aktiv" plaque). Blue info banner: device is fixed-configured for this machine.

**c) Netzwerkverbindungen** (`#sub-network`)
- **IP-Konfiguration**: a segmented control (`#ipModeSeg`) **DHCP** / **Statisch**. DHCP shows a blue note with the current auto address `192.168.178.83` and the four static fields (IP / Subnetzmaske / Gateway / DNS) are **disabled**; switching to Statisch enables them and hides the note.
- An **amber warning banner** (always visible): changing IP config drops connections; device may only be reachable at the new address — note it before saving.
- **"IP-Konfiguration speichern"** opens a warning modal (`#modalNetwork`) summarizing the chosen mode + new address; confirming shows a transient "Gespeichert" check.
- **WLAN** section: Hotspot-Modus switch + SSID `DocuControl-AP` / Passwort; WLAN-Client SSID/Passwort + "Verbinden"; "Netzwerk neu starten" (outline-danger).

**d) USB-Drucker** (`#sub-printer`)
- Rows: Druckerstatus (green "Bereit" pill) · Erkannter Drucker "Brother QL-820NWB" + "Erneut suchen" · "Drucker aktiviert" switch · "Automatisch drucken bei neuem Protokoll" switch (on) · "Testseite drucken" button.

**e) Protokolleinstellungen** (`#sub-protocol`)
- **Kopfdaten**: Einrichtung "Klinikum Krefeld — ZSVA", Standort "Aufbereitung OP 2", "Klinik-Logo drucken" switch.
- **PDF & Dateiname**: Papierformat (A4/A5/Endlos) · Sprache (Deutsch/English) · Aufbewahrung (10/15 Jahre/Unbegrenzt); "Chargennummer im Dateinamen" switch (on, with example) · "Bediener-Kürzel abfragen" switch · Speichern.

**f) Uhrzeit** (`#sub-clock`)
- Two clock cards: **DocuControl-Systemzeit** (live, `#sysTime`/`#sysDate`) and **Echtzeituhr (RTC, Hardware)** (`#rtcTime`/`#rtcDate`, intentionally 4s behind to show drift, with a green "Abweichung +4 s · im Toleranzbereich" pill). Both monospace, update every second.
- **RTC stellen**: NTP switch + Datum/Uhrzeit/Zeitzone fields + "RTC stellen" (transient "RTC gestellt" check) + "Von Systemzeit übernehmen".

**g) Systeminfo** (`#sub-system`)
- 2-column definition list: **Angeschlossene Maschine** Belimed PST 14-8-12 HS1 · Gerät DocuControl 2026 · Modell DocuPi-3000 · Seriennummer `DCP-3000-26-00418` · Software v3.4.1 · Firmware fw-2.18 (RPi) · OS DocuOS 12 · MAC `B8:27:EB:4A:1C:90` · IP `192.168.178.83` · Inbetriebnahme 24.01.2026 · Betriebszeit "71 Tage, 04:18 h" · Höchster Chargenzähler 21.667 · Interner Speicher 12,4/32 GB. Actions: "Nach Updates suchen" · "Diagnosebericht exportieren" · "Gerät neu starten" (outline-danger).

---

## Interactions & Behavior
- **Tab switching:** clicking a `.navstrip .tab` toggles `.active` on the tab and the matching `#view-*`; scrolls to top.
- **Sub-tab switching:** clicking a `.subnav .sub` toggles the matching `#sub-*`. Selecting **Live Monitor** starts the stream; leaving it stops the interval.
- **File selection / move / copy / delete:** see Dateien above. Deletes always confirm via modal; moves/copies are immediate and de-dupe by filename.
- **Network mode toggle:** enables/disables static fields and the DHCP note. Saving requires modal confirmation.
- **Clocks:** one shared `setInterval(…, 1000)` drives the topbar clock, the two settings clocks (RTC −4s).
- **Live monitor:** `setInterval(…, 1600)` appends sample lines; Pause halts, Leeren clears, Auto-Scroll toggles follow.
- **Modals:** open by adding `.show`; close on the Abbrechen button, the backdrop click, or the confirm action.
- **Animations:** view fade-up 0.25s; hover lifts `translateY(-1/-2px)` ~0.14–0.18s; button press `translateY(1px) scale(.995)`; topbar dot `pulse-ready` 1.3s; terminal LIVE dot `blink` 1.4s. All decorative motion should respect `prefers-reduced-motion`.

## State Management
- `activeTab` ('dashboard' | 'dateien' | 'einstellungen').
- `activeSubTab` (monitor | machine | network | printer | protocol | system).
- **File manager:** `internal[]`, `usb[]` (each `{name, date, size}`), `usbConnected`, `focusedPane`, and a `Set` of selected indices per pane. Derived: per-pane used space, selection summary, toolbar enabled/direction.
- **Network:** `ipMode` ('dhcp'|'static'), static address fields, pending-save for the confirmation modal.
- **Live monitor:** running/paused flags, auto-scroll flag, line buffer (cap 200), sample cursor.
- **Pending delete:** which pane + selection the confirmation modal will act on.
- Production: replace simulated data with real device services (filesystem, serial reader, network config, printer, RTC). The protocol list should be **server-paginated** (21.667 rows) and **server-sorted/filtered**.

## Design Tokens
All defined in `colors_and_type.css` (`:root`). Key values:

**Brand / primary:** navy `#1f4e79` (`--docupi-blue`) · accent blue `#2e75b6` (`--docupi-light`) · app bg `#f4f6f9`.
**Status:** success `#28a745` / strong `#198754` · danger `#dc3545` · warning `#ffc107`/`#fd7e14` · info `#00bcd4`.
**Component-layer colors** (in `app/docucontrol.css`): topbar `#323C4B` · table header `#E6EBF0` · border `#DCE2E8` / strong `#C8C8C8` · text `#1D273B` · muted `#6C757D` · row-alt `#FAFBFC` · selected row `#d8e8fb` · success-soft `#e7f1ec` · danger-soft `#fbe9eb` · warn banner bg `#fff7e6` / border `#ffe1a8` / fg `#8a5a00`.
**Terminal:** bg `#1e1e1e` · head `#2d2d2d` · green `#00ff41` · text `#d4d4d4` · orange `#ff6600`.
**Liquid-glass primitives:** `--glass-fill rgba(255,255,255,0.55)`, `--glass-bd rgba(255,255,255,0.65)`, `--glass-hi inset 0 1px 0 rgba(255,255,255,0.85)`, `--glass-blur blur(10px) saturate(1.4)`.
**Typography:** sans = `'Segoe UI', system-ui, -apple-system, 'Helvetica Neue', Arial, sans-serif` · mono = `'Courier New', ui-monospace, …` · brand = `'Square'` (wordmark only). Sizes used in v3: h1 23px, stat value 34px, body 14px, labels 11px uppercase, table 13.5px, mono terminal 13px.
**Radii:** buttons 10px (sm 8px), cards 12px, stat/machine cards 14px, modal 16px, pills/badges 50px.
**Shadows:** sm `0 1px 3px rgba(24,39,59,.07)` · md `0 4px 16px rgba(24,39,59,.10)` · lg `0 18px 50px rgba(24,39,59,.22)`, plus colored button shadows.
**Spacing:** Bootstrap-like 4/8/16/24/48px scale; layout gaps 14–22px.
**Motion:** default 0.14–0.2s ease; hover lift −2px.

## Assets
- **`fonts/Square.ttf`** — GeTmatic brand wordmark font (self-hosted `@font-face` 'Square'). Used ONLY for the word "GeTmatic" in topbar + footer. Bundled here.
- **Bootstrap Icons 1.11.2** — loaded from jsDelivr CDN in the prototype (`bi-*` classes). In production use your icon system; the README names the specific glyph per control.
- No raster images; the autoclave is represented by the `bi-safe2` glyph in an icon tile (no custom illustration).

## Files
- `DocuControl Dashboard v3.html` — full markup for all three tabs, six settings sub-tabs, and both modals.
- `styles.css` — entry point; `@import`s the two CSS files below in order.
- `colors_and_type.css` — design-token foundation (`:root` variables + element defaults). **Source of truth for tokens.**
- `app/docucontrol.css` — component + liquid-glass styling layer.
- `app/docucontrol.js` — all interactivity (tabs, sub-tabs, file manager, modals, network mode, clocks, live monitor). Vanilla JS, IIFE, no dependencies.
- `fonts/Square.ttf` — brand wordmark font.

To preview the reference as-is: open `DocuControl Dashboard v3.html` in a browser (needs internet for the Bootstrap-Icons CDN). Note the HTML links `colors_and_type.css` + `app/docucontrol.css` directly; `styles.css` is provided as the single-link entry point for your build.
