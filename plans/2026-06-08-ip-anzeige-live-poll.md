# Plan: Aktuelle IP live anzeigen — periodischer System-Poll

**Erstellt:** 2026-06-08
**Status:** Implementiert
**Anforderung:** "Aktuelle IP" in der Netzwerk-Card soll die echte System-IP live anzeigen und sich automatisch aktualisieren — nicht nur einmalig beim Seitenaufruf.

---

## Überblick

### Was dieser Plan erreicht

`iface1CurrentIp` (und iface2) werden alle 5 Sekunden neu aus dem System gelesen (`ip addr show eth0` via `/api/network/iface/<dev>/status`) und sofort angezeigt. Nach einem DHCP-Wechsel erscheint die neue IP automatisch, sobald nmcli die DHCP-Lease vom Router bekommen hat — ohne manuellen Reload.

### Warum das wichtig ist

DocuControl wird im Kliniknetz auf eine fest vergabene IP eingestellt. Wenn der Techniker von Statisch auf DHCP wechselt, muss er sofort sehen, welche IP der Router vergeben hat — nicht erst nach einem Browser-Reload. Die aktuelle Implementierung zeigt nach dem DHCP-Wechsel 4 Sekunden lang neu, dann friert die Anzeige ein. Vor-Ort-Installation beim Tierlabor Uni Essen: ohne diese Funktion ist das Netzwerk-Setup blind.

---

## Aktueller Zustand

### Relevante bestehende Struktur

| Datei | Relevanter Inhalt |
|---|---|
| `src/docucontrol/templates/settings.html` | JS-Funktionen `loadInterfaces()`, `loadIface(num)`, `applyIfaceStatus(num, d)` |
| `src/docucontrol/network_manager.py` | `get_interface_status(iface)` — liest `current_ip` live via `ip -4 addr show` |
| Pi `app.py` | `GET /api/network/iface/<dev>/status` → ruft `get_interface_status()` auf |

### Lücken oder Probleme, die adressiert werden

1. **`loadStaticSettings()`** wird einmalig beim Seitenaufruf aufgerufen → danach kein Poll.
2. **`saveIfaceDhcp()`** löst `loadIface(num)` nach 4 Sekunden aus — aber nmcli braucht je nach Router-Antwort 5–15 Sekunden für die DHCP-Lease. Danach: nichts mehr.
3. **Kein `ipPollInterval`** vorhanden — die `clockInterval`/`monitorInterval`/`systemInterval`-Pattern (alle schon implementiert) werden für IP-Poll noch nicht genutzt.
4. Backend ist korrekt: `get_interface_status()` liest bereits `current_ip` live von `ip addr show` — kein Backend-Fix nötig.

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

- Neue JS-Funktion `pollCurrentIPs()` in `settings.html`: holt von `/api/network/interfaces` nur `current_ip`, `connected`, `mac`, `speed` und aktualisiert ausschließlich diese DOM-Elemente (NICHT die Config-Felder mode/ip-inputs — würde laufende User-Eingaben überschreiben).
- `pollCurrentIPs()` wird als `ipPollInterval` alle 5 Sekunden ausgeführt, solange `panelDevices` aktiv ist.
- `switchTab()` startet/stoppt `ipPollInterval` analog zu `monitorInterval` und `systemInterval`.
- `saveIfaceDhcp()`: timeout von 4s auf 2s reduzieren (erster Aufruf), danach übernimmt der Poll automatisch.

### Neue Dateien erstellen

Keine.

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|---|---|
| `src/docucontrol/templates/settings.html` | Neue Variable `ipPollInterval`, neue Funktion `pollCurrentIPs()`, Anpassung `switchTab()`, Anpassung `saveIfaceDhcp()` |

### Zu löschende Dateien

Keine.

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **Nur `current_ip`/`connected`/`mac`/`speed` pollen — NICHT `mode` oder Config-Felder**: Der User könnte gerade den IP-Modus-Dropdown auf "Statisch" umgeschaltet haben und tippt die neue IP ein. Ein vollständiger `applyIfaceStatus()`-Call würde das Formular resetten. Die Poll-Funktion darf nur die reinen Ist-Werte aktualisieren, nie Eingabefelder.

2. **5-Sekunden-Interval**: Kurz genug damit nach DHCP-Lease (<15s typisch) die neue IP erscheint; lang genug um nicht den Pi zu belasten (ein `ip addr show`-Befehl pro 5s ist trivial).

3. **Poll nur wenn Tab `devices` aktiv**: Analog zum bestehenden Pattern mit `monitorInterval` und `systemInterval` — Interval wird in `switchTab()` gestartet/gestoppt. Kein unnötiger Traffic auf inaktiven Tabs.

4. **`ipPollInterval` separat von `clockInterval`**: `clockInterval` läuft immer (Systemuhr), `ipPollInterval` nur auf dem Devices-Tab. Klar getrennte Verantwortlichkeiten.

5. **Kein Backend-Change**: `GET /api/network/interfaces` gibt bereits `current_ip` aus `ip addr show` zurück — das ist genau was wir wollen. Keine neue Route nötig.

### Betrachtete Alternativen

- **Server-Sent Events (SSE)**: Würde echte Push-Updates liefern, aber deutlich komplexer (neuer Endpoint, Verbindungsmanagement, Fallback). Overkill für ein 5s-Interval.
- **WebSocket**: Noch komplexer, kein Mehrwert gegenüber polling für diesen Use Case.
- **`loadIface()` timeout verlängern**: 4s → 15s würde den Einzel-Reload verbessern, aber keine echte Live-Anzeige liefern.

### Offene Fragen

Keine — der Fix ist technisch eindeutig.

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: Variable `ipPollInterval` deklarieren

Im JS-Block von `settings.html` sind bereits alle Interval-Variablen am Anfang des IIFE deklariert:
```js
var monitorInterval = null;
var systemInterval = null;
var clockInterval = null;
```

Hier `var ipPollInterval = null;` ergänzen.

**Aktionen:**
- In `settings.html` im `(function() {` Block die neue Variable ergänzen, direkt nach `var clockInterval = null;`

**Betroffene Dateien:**
- `src/docucontrol/templates/settings.html` (Zeile ~501)

---

### Schritt 2: Funktion `pollCurrentIPs()` implementieren

Neue Funktion die `/api/network/interfaces` fetcht und ausschließlich `current_ip`, `connected`, `mac`, `speed` aktualisiert:

```javascript
function pollCurrentIPs() {
    fetch('/api/network/interfaces')
        .then(function(r) { return r.json(); })
        .then(function(ifaces) {
            ifaces.forEach(function(d) {
                var num = document.getElementById('iface1Select').value === d.iface ? 1 :
                          document.getElementById('iface2Select').value === d.iface ? 2 : 0;
                if (!num) return;
                var ipEl = document.getElementById('iface' + num + 'CurrentIp');
                if (ipEl) ipEl.textContent = d.current_ip || '—';
                var macEl = document.getElementById('iface' + num + 'Mac');
                if (macEl) macEl.textContent = (d.mac || '—') + (d.speed ? ' · ' + d.speed : '');
                var badge = document.getElementById('iface' + num + 'StatusBadge');
                if (badge) {
                    badge.textContent = d.connected ? 'Verbunden' : 'Getrennt';
                    badge.style.background = d.connected ? 'var(--success)' : 'var(--muted)';
                }
            });
        }).catch(function() {});
}
```

**Aktionen:**
- Funktion in `settings.html` nach `loadInterfaces()` einfügen (ca. Zeile 621, nach dem `}).catch(function() {}); }` Block von `loadInterfaces`)

**Betroffene Dateien:**
- `src/docucontrol/templates/settings.html`

---

### Schritt 3: `switchTab()` — `ipPollInterval` starten/stoppen

Analog zu `monitorInterval` und `systemInterval` den Poll im Tab-Wechsel verwalten.

**Aktuell** (vereinfacht):
```js
window.switchTab = function(tab) {
    ...
    if (tab === 'monitor') {
        ...
        if (!monitorInterval) monitorInterval = setInterval(tickMonitor, 5000);
    } else {
        if (monitorInterval) { clearInterval(monitorInterval); monitorInterval = null; }
    }
    if (tab === 'system') {
        ...
        if (!systemInterval) systemInterval = setInterval(loadSystemStatus, 10000);
    } else {
        if (systemInterval) { clearInterval(systemInterval); systemInterval = null; }
    }
};
```

**Nach dem Fix** — ergänzen:
```js
    if (tab === 'devices') {
        if (!ipPollInterval) ipPollInterval = setInterval(pollCurrentIPs, 5000);
    } else {
        if (ipPollInterval) { clearInterval(ipPollInterval); ipPollInterval = null; }
    }
```

**Aktionen:**
- Im `switchTab()`-Block den `devices`-Branch für `ipPollInterval` ergänzen, direkt nach dem `system`-Branch

**Betroffene Dateien:**
- `src/docucontrol/templates/settings.html` (Zeile ~513–527)

---

### Schritt 4: `saveIfaceDhcp()` — timeout auf 2s kürzen

Aktuell: 4 Sekunden nach DHCP-Bestätigung einmaliger `loadIface(num)`. Das bleibt, aber der Timeout wird auf 2s verkürzt (erster schneller Check), danach übernimmt `ipPollInterval` alle 5 Sekunden.

**Aktuell:**
```js
setTimeout(function() { loadIface(num); }, 4000);
```

**Nach dem Fix:**
```js
setTimeout(function() { loadIface(num); }, 2000);
```

**Aktionen:**
- In `saveIfaceDhcp()` den timeout von 4000 auf 2000 ms setzen

**Betroffene Dateien:**
- `src/docucontrol/templates/settings.html` (Zeile ~737)

---

### Schritt 5: `devices`-Tab initial poll starten

Der `devices`-Tab ist beim Seitenaufruf bereits aktiv — `switchTab('devices')` wird aber nie explizit aufgerufen. Daher muss `ipPollInterval` auch im initialen `loadDeviceSettings()`/`loadStaticSettings()`-Aufruf gestartet werden.

**Aktuell** (am Ende des IIFE, nach allen Funktionsdefinitionen):
```js
loadDeviceSettings();
loadStaticSettings();
```

**Nach dem Fix:**
```js
loadDeviceSettings();
loadStaticSettings();
if (!ipPollInterval) ipPollInterval = setInterval(pollCurrentIPs, 5000);
```

**Aktionen:**
- Im Initialisierungsblock am Ende des IIFE `ipPollInterval` starten

**Betroffene Dateien:**
- `src/docucontrol/templates/settings.html` (letzter Abschnitt des JS-Blocks)

---

### Schritt 6: Deployment auf Pi

```bash
scp src/docucontrol/templates/settings.html \
    docucontrol@192.168.0.180:/home/docucontrol/docupi/templates/settings.html
ssh docucontrol "sudo systemctl restart docucontrol.service"
```

(SSH-Key: `~/.ssh/id_ed25519`, sudo pw: `Xtend1478`)

**Aktionen:**
- `settings.html` deployen
- Service neustarten
- Seite im Browser öffnen: `http://192.168.0.180/settings`
- Prüfen: IP-Anzeige aktualisiert sich alle 5 Sekunden

**Betroffene Dateien:**
- Pi: `/home/docucontrol/docupi/templates/settings.html`

---

### Schritt 7: Testen

1. Seite `http://192.168.0.180/settings` öffnen → Tab "Geräte & Netzwerk" aktiv
2. Im Browser-DevTools Network-Tab: alle 5s kommt ein Request auf `/api/network/interfaces` → ✓
3. Interface auf DHCP umstellen, "DHCP übernehmen" klicken
4. Warten ohne Reload — nach <15s erscheint die neue DHCP-IP automatisch in "Aktuelle IP"
5. Auf Tab "System" wechseln → kein mehr `/api/network/interfaces`-Request (Poll gestoppt) → ✓
6. Zurück zu "Geräte & Netzwerk" → Poll startet wieder → ✓

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- Pi `app.py` → `GET /api/network/interfaces` (bereits vorhanden, kein Change)
- Pi `network_manager.py` → `get_interface_status()` (bereits korrekt, kein Change)

### Nötige Updates für Konsistenz

- `CLAUDE.md` — kein Update nötig (kein neuer Endpunkt, kein strukturelles Feature)
- `context/current-data.md` — kein Update nötig

### Auswirkungen auf bestehende Workflows

- Keine funktionale Änderung an bestehenden Save-Funktionen
- DHCP/Static-Speichern funktioniert unverändert
- Nur die passive Anzeige wird live gemacht

---

## Validierungs-Checkliste

- [ ] `var ipPollInterval = null;` im IIFE-Kopf deklariert
- [ ] `pollCurrentIPs()` aktualisiert nur `current_ip`, `mac`, `speed`, `badge` — KEINE input-Felder
- [ ] DevTools zeigen `/api/network/interfaces` alle 5s auf Tab "Geräte & Netzwerk"
- [ ] Auf anderem Tab stoppt der Poll (kein Traffic)
- [ ] Nach DHCP-Wechsel: neue IP erscheint ohne Browser-Reload innerhalb von 15s
- [ ] Statische Formular-Eingaben werden beim Tippen NICHT vom Poll überschrieben
- [ ] Deployment erfolgreich: `docucontrol.service` läuft, Seite erreichbar

---

## Erfolgskriterien

1. Die "Aktuelle IP"-Anzeige zeigt nach einem DHCP-Wechsel automatisch die neue DHCP-IP, ohne dass der User die Seite neu laden muss.
2. Der IP-Poll läuft nur wenn der Tab "Geräte & Netzwerk" aktiv ist — kein unnötiger Hintergrund-Traffic.
3. Laufende Eingaben in den Formularfeldern (IP, Gateway etc.) werden durch den Poll nicht überschrieben.

---

## Implementierungsnotizen

**Implementiert:** 2026-06-08

### Zusammenfassung

- `var ipPollInterval = null;` im IIFE-Kopf ergänzt
- Neue Funktion `pollCurrentIPs()` nach `loadIface()` eingefügt — liest `current_ip`, `mac`, `speed`, `connected` aus `/api/network/interfaces`, schreibt NUR diese Anzeigeelemente (keine Input-Felder)
- `switchTab()` erweitert: `ipPollInterval` startet bei Tab `devices`, stoppt bei allen anderen Tabs
- `saveIfaceDhcp()`: timeout 4000 → 2000 ms
- Init-Block: `ipPollInterval` beim Seitenaufruf sofort starten
- Deployment konnte nicht automatisch erfolgen (Pi bei getmatic, nicht vom Heimnetz erreichbar)

### Abweichungen vom Plan

Keine inhaltlichen — Deploy-Schritt muss manuell ausgeführt werden (siehe Notizen).

### Aufgetretene Probleme

- SSH-Verbindung zu 192.168.0.180 timed out (Pi im getmatic-Netz, kein Fernzugriff von Heimnetz). Deploy-Befehl für manuelle Ausführung:
  ```bash
  scp src/docucontrol/templates/settings.html docucontrol@192.168.0.180:/home/docucontrol/docupi/templates/settings.html
  ssh docucontrol "echo 'Xtend1478' | sudo -S systemctl restart docucontrol.service"
  ```

---

## Notizen

- Der `/api/network/interfaces`-Endpunkt ruft `get_interface_status()` für jedes Interface auf — auf dem Pi mit nur einem Interface (`eth0`) ist das ein einzelner `ip addr show`-Aufruf, trivial schnell.
- Wenn der Pi die DHCP-Lease vom Router in <5s bekommt, sieht der User die neue IP noch bevor der erste Poll-Tick ausgelöst wird (wegen des 2s-Timeouts in `saveIfaceDhcp`).
- Falls das Interface beim DHCP-Wechsel kurz `connected: false` ist (keine IP), zeigt die Badge "Getrennt" — das ist korrekt und gibt dem User Feedback, dass der Wechsel läuft.
