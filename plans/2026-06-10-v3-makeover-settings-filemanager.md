# Plan: v3 Makeover — Einstellungen & Datei-Manager

**Erstellt:** 2026-06-10
**Status:** Implementiert
**Anforderung:** Einstellungen und Datei-Manager erhalten ein visuelles Makeover im Stil des v3-Dashboards — gleiche CSS-Klassen, gleiche Button-Hierarchie, gleiche Page-Header-Struktur. Keine funktionalen Änderungen, keine Umstrukturierung.

---

## Überblick

### Was dieser Plan erreicht

Settings und Datei-Manager sehen aus wie das bereits fertige v3-Dashboard: konsequente Button-Hierarchie (primär navy-glass / sekundär frosted-clear), korrekte `.segmented`-Klasse für den Modus-Toggle, und `.lede`-Untertitel im Page-Header. Alle bestehenden Funktionen, Buttons und Anordnungen bleiben exakt wo sie sind — nur die CSS-Klassen werden angepasst.

### Warum das wichtig ist

Für den Kundentermin nächste Woche soll das gesamte Interface konsistent wirken. Das Dashboard ist bereits v3; Settings und Datei-Manager fallen optisch etwas ab, weil primäre Aktionen (`btn-outline`, flach-grau) sich nicht von sekundären abheben und der Modus-Toggle im Datei-Manager mit Inline-Styles statt der vorhandenen `.segmented`-Klasse gebaut wurde.

---

## Aktueller Zustand

### Probleme die adressiert werden

**1. Button-Hierarchie fehlt in settings.html**

Alle Aktions-Buttons (primäre Speichern-Buttons und sekundäre Test-Buttons) sind gleich: `btn-outline` (weißer Hintergrund, grauer Rahmen). Im v3-Design gibt es drei Stufen:
- Primäre Aktion (`btn-primary`) → navy glass, Schatten, sichtbar herausgehoben
- Sekundäre Aktion (`btn-glass`) → frosted-clear, dezenter Schatten
- Gefährliche Aktion (`btn-danger` / `btn-outline-danger`) → bereits korrekt

Betroffene Buttons in settings.html:
| Zeile | Label | Klasse aktuell | Klasse neu |
|---|---|---|---|
| 38, 48 | Setzen (Maschinenname, IP) | `btn-outline` | `btn-primary` |
| 58 | Ping | `btn-outline` | `btn-glass` |
| 80 | Testdruck | `btn-outline` | `btn-glass` |
| 293 | Setzen (Hostname) | `btn-outline` | `btn-primary` |
| 320 | Setzen (Uhrzeit) | `btn-outline` | `btn-primary` |
| 343 | Setzen (NTP) | `btn-outline` | `btn-primary` |
| 380 | Jetzt sync. | `btn-outline` | `btn-glass` |
| 484 | Neu starten | `btn-outline` + inline-danger-style | `btn-outline-danger` |

Bereits korrekt (keine Änderung): Netzwerk-Speichern-Buttons (171, 202, 243, 273) → `btn-primary` ✓; Formatieren (404) → `btn-danger` ✓; Clear-Terminal (544) → `btn-outline-danger` ✓

**2. Modus-Toggle in filemanager.html nutzt Inline-Styles statt `.segmented`**

Der globale Ansicht-Toggle ("PDF-Protokolle" / "Rohdaten") wurde mit Inline `style=""` auf zwei `<button>` gebaut. Die CSS hat dafür die fertige `.segmented`-Klasse (pill-shaped button group, aktiver Button navy-glass). Muss auf `.segmented` umgebaut werden.

**3. "Auf USB kopieren" und Sync-Button in filemanager.html**

| Zeile | Label | Klasse aktuell | Klasse neu |
|---|---|---|---|
| 47 | Auf USB kopieren | `btn-sm btn-outline` | `btn-sm btn-primary` |
| 124 | Jetzt sync. | `btn-outline` | `btn-glass` |

**4. Page-Head Lede-Zeilen fehlen**

Dashboard hat `<div class="lede">Gespeicherte Sterilisations-Chargen ansehen, filtern und drucken.</div>` unter dem `<h1>`. Settings und Datei-Manager haben keinen Lede-Text.

---

## Vorgeschlagene Änderungen

### Zusammenfassung

- `settings.html`: 8 Button-Klassen anpassen + 1 `.lede` Zeile im Page-Head
- `filemanager.html`: `.segmented` Toggle + 2 Button-Klassen + 1 `.lede` Zeile + `switchMode()` JS an neue HTML-Struktur anpassen

### Neue Dateien erstellen

Keine.

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|---|---|
| Pi: `templates/settings.html` | 8× Buttonklasse + Page-Head lede |
| Pi: `templates/filemanager.html` | `.segmented`-Toggle (HTML + CSS + JS) + 2× Buttonklasse + Page-Head lede |

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **`btn-primary` nur für Speichern-Aktionen**: Buttons die Daten persistent verändern (Setzen, Speichern) → `btn-primary`. Buttons die Daten lesen oder testen (Ping, Testdruck, Sync) → `btn-glass`.

2. **`btn-outline-danger` für "Neu starten"**: Aktuell hat der Reboot-Button eine Inline-Style-Übersteuerung (`style="color:var(--danger);border-color:var(--danger)"`). `btn-outline-danger` ist die korrekte CSS-Klasse und macht Inline-Style obsolet.

3. **`.segmented` für Mode-Toggle**: Die CSS definiert `.segmented > button` mit `padding: 7px 16px`, aktivem Button in navy glass. Das ersetzt die zwei Inline-styled Buttons vollständig. JS `switchMode()` muss an die neue Struktur angepasst werden (keine `id="-Abfragen` mehr nötig, da `.segmented button.active` die Hervorhebung per CSS steuert — oder alternativ: active-Klasse per JS setzen statt style).

4. **Lede-Texte kurz und sachlich**: Kein Marketing-Speak. Je ein knapper Satz der erklärt was auf der Seite passiert.

### Betrachtete Alternativen

- **Nichts tun**: Die Seiten funktionieren, aber wirken optisch inkonsistent zum Dashboard.
- **Alle `btn-outline` ersetzen**: Zu aggressiv — manche sekundären Buttons (z.B. "Testdruck") sollen absichtlich dezenter wirken als die primären Speichern-Buttons.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: settings.html — Button-Hierarchie

Alle Änderungen via SSH-Python-Patch:

**Primäre Aktionen → `btn-primary`:**
```
"btn btn-outline" onclick="saveMachineConfig()"   → "btn btn-primary" (2× Vorkommen)
"btn btn-outline" onclick="saveHostname()"         → "btn btn-primary"
"btn btn-outline" onclick="saveManualTime()"        → "btn btn-primary"
"btn btn-outline" onclick="saveNtp()"               → "btn btn-primary"
```

**Sekundäre Aktionen → `btn-glass`:**
```
"btn btn-outline" onclick="testMachinePing()"  → "btn btn-glass"
"btn btn-outline" onclick="testPrint()"         → "btn btn-glass"
id="btnSyncNow" class="btn btn-outline"         → class="btn btn-glass"
```

**Neu starten → `btn-outline-danger` (Inline-Style entfernen):**
```
class="btn btn-outline" ... style="color:var(--danger);border-color:var(--danger)"
→ class="btn btn-outline-danger" (kein style-Attribut mehr)
```

**Aktionen:**
- Python-Patch via SSH
- Verifizieren: `grep -c 'btn-primary\|btn-glass\|btn-outline-danger' /home/docucontrol/docupi/templates/settings.html`

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/templates/settings.html`

---

### Schritt 2: settings.html — Page-Head Lede

Aktueller Page-Head:
```html
<div class="page-head">
    <div class="over">Konfiguration</div>
    <h1>Einstellungen</h1>
</div>
```

Neu:
```html
<div class="page-head">
    <div>
        <div class="over">Konfiguration</div>
        <h1>Einstellungen</h1>
        <div class="lede">Geräte, Netzwerk, Drucker und System konfigurieren.</div>
    </div>
</div>
```

**Aktionen:**
- Patch via SSH

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/templates/settings.html`

---

### Schritt 3: filemanager.html — `.segmented` Toggle

**HTML-Änderung** — Inline-styled Buttons durch `.segmented`-Block ersetzen:

Aktuell:
```html
<div style="display:inline-flex;border:1px solid var(--border);border-radius:8px;overflow:hidden">
    <button id="btnModePdf" onclick="switchMode('pdf')"
      style="padding:5px 16px;...;background:var(--accent);color:#fff">
      <i class="bi bi-file-earmark-pdf"></i> PDF-Protokolle
    </button>
    <button id="btnModeCaptures" onclick="switchMode('captures')"
      style="padding:5px 16px;...;background:var(--surface);color:var(--text)">
      <i class="bi bi-file-earmark-text"></i> Rohdaten
    </button>
</div>
```

Neu (`.segmented` CSS-Klasse, aktiver Button bekommt `.active`-Klasse):
```html
<div class="segmented" id="modeSegmented">
    <button id="btnModePdf" class="active" onclick="switchMode('pdf')">
        <i class="bi bi-file-earmark-pdf"></i> PDF-Protokolle
    </button>
    <button id="btnModeCaptures" onclick="switchMode('captures')">
        <i class="bi bi-file-earmark-text"></i> Rohdaten
    </button>
</div>
```

**JS-Änderung** in `switchMode()` — Inline-Styles durch `.active`-Klassen-Toggle ersetzen:

Aktuell (Lines ca. 229–238):
```javascript
var btnPdf = document.getElementById('btnModePdf');
var btnCap = document.getElementById('btnModeCaptures');
if (btnPdf) {
    btnPdf.style.background = isPdf ? 'var(--accent)' : 'var(--surface)';
    btnPdf.style.color = isPdf ? '#fff' : 'var(--text)';
}
if (btnCap) {
    btnCap.style.background = !isPdf ? 'var(--accent)' : 'var(--surface)';
    btnCap.style.color = !isPdf ? '#fff' : 'var(--text)';
}
```

Neu:
```javascript
var btnPdf = document.getElementById('btnModePdf');
var btnCap = document.getElementById('btnModeCaptures');
if (btnPdf) { btnPdf.classList.toggle('active', isPdf); }
if (btnCap) { btnCap.classList.toggle('active', !isPdf); }
```

**Aktionen:**
- HTML + JS-Block per Python-Patch ersetzen

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/templates/filemanager.html`

---

### Schritt 4: filemanager.html — Button-Hierarchie + Lede

**Button-Klassen:**
```
"btn btn-sm btn-outline" id="btnBulkCopyUsb"  → "btn btn-sm btn-primary"
"btn btn-outline" id="btnSync"                  → "btn btn-glass"
```

**Page-Head Lede:**

Aktuell:
```html
<div class="page-head">
    <div class="over">Speicher</div>
    <h1>Dateien</h1>
</div>
```

Neu:
```html
<div class="page-head">
    <div>
        <div class="over">Speicher</div>
        <h1>Dateien</h1>
        <div class="lede">PDFs und Rohdaten verwalten und auf USB-Stick synchronisieren.</div>
    </div>
</div>
```

**Aktionen:**
- Patch via SSH

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/templates/filemanager.html`

---

### Schritt 5: Service-Restart + Verifikation

**Aktionen:**
- `sudo systemctl restart docucontrol.service`
- `systemctl is-active docucontrol.service`
- Browser `http://192.168.0.171/settings` → "Setzen"-Buttons sind navy-glass, "Ping"/"Testdruck" sind frosted
- Browser `http://192.168.0.171/files` → Toggle ist `.segmented`, "Auf USB kopieren" ist navy-glass

---

## Verbindungen & Abhängigkeiten

### Dateien, die dieser Bereich betrifft

- `static/docucontrol.css`: keine Änderungen — alle benötigten Klassen sind bereits definiert
- `templates/base.html`: keine Änderungen
- `templates/dashboard.html`: keine Änderungen (bereits v3)

### Nötige Updates für Konsistenz

- `CLAUDE.md`: keine Änderungen nötig (kein neuer Endpunkt, keine neue Funktionalität)

---

## Validierungs-Checkliste

- [ ] `settings.html`: `btn-primary` für alle Setzen/Speichern-Buttons
- [ ] `settings.html`: `btn-glass` für Ping, Testdruck, Jetzt-sync.-Button
- [ ] `settings.html`: `btn-outline-danger` für Neustart (kein Inline-Style mehr)
- [ ] `settings.html`: `.lede` Zeile im Page-Head sichtbar
- [ ] `filemanager.html`: `.segmented`-Klasse für Mode-Toggle (keine Inline-Styles)
- [ ] `filemanager.html`: Toggle-Wechsel setzt `.active`-Klasse korrekt (JS-Test)
- [ ] `filemanager.html`: "Auf USB kopieren" → navy-glass
- [ ] `filemanager.html`: Sync-Button → frosted-glass
- [ ] `filemanager.html`: `.lede` Zeile im Page-Head sichtbar
- [ ] Service nach Restart `active`, keine 500er im Log

---

## Erfolgskriterien

1. Settings-Seite: primäre Aktionen (Setzen, Speichern) sind visuell von sekundären (Ping, Test, Sync) unterscheidbar
2. Datei-Manager: Mode-Toggle nutzt die `.segmented` CSS-Klasse, kein Inline-Style
3. Beide Seiten haben einen `.lede` Untertitel im Page-Header wie das Dashboard

---

## Notizen

- `btn-glass` gibt es im CSS (`.btn-glass`: frosted-clear, dezenter Schatten). Es wurde bisher in Settings/Filemanager noch gar nicht genutzt — diese Änderung ist der erste Einsatz auf diesen Seiten.
- Die Inline-Style-Bereinigung beim Neustart-Button (484) entfernt auch die Style-Redundanz — `btn-outline-danger` definiert genau dieselben Farben via CSS.
- `switchMode()` wird durch die `.active`-Klassen-Methode kürzer und korrekter — das Styling liegt im CSS, nicht im JS.

---

## Implementierungsnotizen

**Implementiert:** 2026-06-10

### Zusammenfassung

- `settings.html`: 5× `btn-primary` (saveMachineConfig ×2, saveHostname, saveManualTime, saveNtp), 3× `btn-glass` (testMachinePing, testPrint, btnSyncNow), 1× `btn-outline-danger` (rebootBtn, Inline-Style entfernt), `.lede` im Page-Head hinzugefügt
- `filemanager.html`: Modus-Toggle von Inline-styled-Buttons auf `.segmented` CSS-Klasse umgebaut; `switchMode()` JS nutzt `classList.toggle('active')` statt Inline-Style-Overrides; "Auf USB kopieren" → `btn-primary`; Sync-Button → `btn-glass`; `.lede` im Page-Head hinzugefügt

### Abweichungen vom Plan

Assertion-Fix nötig: Die erste Assertion `'style="color:var(--danger)' not in content` traf auch den USB-Verwaltungs-Beschreibungstext (`.desc`-Div mit inline danger color). Assertion auf `'id="rebootBtn" onclick="rebootSystem()" style='` präzisiert — keine inhaltliche Abweichung.

### Aufgetretene Probleme

Erster Patch-Lauf fehlgeschlagen wegen zu breiter Assertion (siehe Abweichungen). Zweiter Lauf erfolgreich. Filemanager-Datei ist nach dem Patch 395 Bytes kleiner (28.818 → 28.423) — korrekt, da `.segmented` kompakter als die Inline-Styles ist.
