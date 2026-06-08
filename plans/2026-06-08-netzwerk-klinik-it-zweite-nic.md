# Plan: Netzwerk-Einstellungen DocuControl — IP-Fix + Klinik-IT-Settings + zweite NIC

**Erstellt:** 2026-06-08
**Status:** Implementiert
**Anforderung:** Statische IP setzen funktioniert nicht (sudo nmcli fehlt in sudoers); Netzwerk-Tab um Klinik-IT-relevante Felder erweitern (Hostname, DNS2, NTP, VLAN); zweite Netzwerkschnittstelle mit Interface-Dropdown vorbereiten.

---

## Überblick

### Was dieser Plan erreicht

Der Netzwerk-Tab in den Einstellungen wird zu einem vollständigen Konfigurationswerkzeug für Krankenhausnetzwerke ausgebaut: statische IP funktioniert zuverlässig, ein zweites Interface ist konfigurierbar (z.B. eth1 für Maschinennetz), und alle für die Universitätsklinikum-IT relevanten Parameter (Hostname, DNS, NTP, VLAN-ID) sind über die UI einstellbar.

### Warum das wichtig ist

DocuControl wird im Tierlabor Uni Essen eingesetzt — ein reguliertes Krankenhausnetz mit festen IP-Vergaben, internen DNS/NTP-Servern und potenzieller VLAN-Segmentierung. Der aktuell defekte IP-Fix blockiert die Vor-Ort-Installation. Die erweiterten Einstellungen ermöglichen dem Klinik-IT-Administrator eine saubere Integration ohne SSH.

---

## Aktueller Zustand

### Root-Cause: Statische IP funktioniert nicht

`set_lan_static()` in `network_manager.py` ruft `sudo nmcli con mod ...` auf. Der User `docucontrol` hat **keinen Sudoers-Eintrag für nmcli** — nur für Storage-Befehle (`mount`, `umount`, `blkid`, `dosfsck`). Die `_run()`-Funktion fängt den Fehler still ab. Der Config-JSON (`network_config.json`) wird geschrieben, aber die tatsächliche Interface-Konfiguration ändert sich nie. Die aktive Verbindung `netplan-eth0` bleibt auf `ipv4.method: auto`.

### Relevante bestehende Struktur

| Datei | Inhalt |
|---|---|
| `/home/docucontrol/docupi/network_manager.py` | `get_lan_status()`, `set_lan_static()`, `set_lan_dhcp()`, `_get_eth_connection()` — alles via nmcli |
| `/home/docucontrol/docupi/app.py` | `GET/POST /api/network/lan/status`, `/api/network/lan/static`, `/api/network/lan/dhcp` |
| `src/docucontrol/templates/settings.html` | "Netzwerk & TCP"-Card: IP-Modus, static form (IP/Prefix, GW, DNS), TCP-Toggle |
| `/etc/sudoers.d/docucontrol-storage` | Nur: mount, umount, blkid, dosfsck |

### Lücken oder Probleme

1. **nmcli fehlt in sudoers** → statische IP nie wirksam
2. Fehler werden nicht ans Frontend propagiert (immer HTTP 200 egal ob nmcli fehlschlägt)
3. Nur ein Interface (eth0 hardcoded als `LAN_INTERFACE`)
4. Kein Hostname-Management
5. Kein NTP-Server konfigurierbar
6. Kein VLAN-ID-Feld
7. Kein zweites Interface

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

- Sudoers-Datei `/etc/sudoers.d/docucontrol-network` auf Pi anlegen (nmcli, ip, hostnamectl, timedatectl)
- `network_manager.py` erweitern: Multi-Interface, Hostname, NTP, VLAN, bessere Fehlerprpagierung
- `app.py` — neue API-Endpunkte: `/api/network/interfaces`, `/api/network/iface/<dev>/...`, `/api/system/hostname`, `/api/system/ntp`
- `settings.html` — "Netzwerk & TCP"-Card komplett neu strukturiert: 2 Interface-Sektionen, Hostname-Card, Zeit/NTP-Card

### Neue Dateien erstellen

| Dateipfad | Zweck |
|---|---|
| `plans/2026-06-08-netzwerk-klinik-it-zweite-nic.md` | Dieser Plan |

Keine neuen Python-Dateien — alles in bestehenden Dateien.

### Zu ändernde Dateien

| Dateipfad | Änderungen |
|---|---|
| `/etc/sudoers.d/docucontrol-network` (Pi) | Neu: nmcli, ip, hostnamectl, timedatectl ohne Passwort |
| `/home/docucontrol/docupi/network_manager.py` (Pi) | Multi-Interface-Support, Hostname, NTP, VLAN, Fehler-Propagierung |
| `/home/docucontrol/docupi/app.py` (Pi) | Neue API-Endpunkte für Interfaces, Hostname, NTP |
| `src/docucontrol/templates/settings.html` | Netzwerk-Tab neu strukturiert mit allen Klinik-IT-Feldern |

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

1. **nmcli bleibt das Backend** (nicht wechseln zu netplan-YAML direkt): nmcli ist der korrekte Weg auf Debian mit NetworkManager — Netplan generiert nmcli-Profile beim `netplan apply`, direktes YAML-Editing würde bei `netplan apply` überschrieben.

2. **VLAN als Sub-Interface** (`eth0.100`): VLAN-Tagging via `nmcli con add type vlan` erstellt ein virtuelles Interface. Einfacher als 802.1Q im Kernel direkt — und von nmcli verwaltbar.

3. **Zweites Interface gleichwertig zu erstem**: Beide Interfaces bekommen dieselbe Konfigurations-UI (DHCP/Statisch, IP, GW, DNS1, DNS2, VLAN). Das zweite Interface wird aktiviert/deaktiviert per Toggle.

4. **Interface-Dropdown aus `ip link show`**: Zeigt alle verfügbaren Ethernet-Interfaces außer `lo`. Beim Pi 5 mit nur eth0 erscheint kein USB-Ethernet-Adapter → Dropdown bleibt deaktiviert bis ein zweites Interface erkannt wird.

5. **Hostname via `hostnamectl set-hostname`**: Sauberste Methode auf systemd-Systemen, ändert `/etc/hostname` und informiert systemd gleichzeitig.

6. **NTP via `timedatectl`**: `timedatectl set-ntp true` und Änderung von `/etc/systemd/timesyncd.conf` ist einfacher und robuster als chrony/ntpd manuell zu verwalten.

7. **Fehler-Propagierung**: `_run()` gibt jetzt immer `(ok, stdout, stderr)` zurück — `set_lan_static()` sammelt alle Fehler und gibt sie als Liste zurück. API antwortet mit HTTP 207 oder 500 wenn nmcli fehlschlug.

8. **Kein 802.1X**: Zu komplex für diese Phase. VLAN reicht für Klinik-Netzsegmentierung.

9. **Kein HTTP-Proxy** in der UI: Proxy-Einstellungen betreffen nur System-Updates, nicht den DocuControl-Betrieb selbst — konfigurierbar via SSH wenn nötig.

### Betrachtete Alternativen

- **Netplan-YAML direkt editieren**: Fragil — `netplan apply` läuft asynchron, und bei Fehler ist das Gerät offline.
- **systemd-networkd statt nmcli**: Würde funktionieren, aber nmcli ist bereits installiert und der bestehende Code baut darauf.
- **VLAN weglassen**: Risiko — wenn die Klinik-IT VLAN-Tagging voraussetzt (häufig), schlägt die Installation fehl.

### Offene Fragen — GEKLÄRT

1. **Zweites Interface** → USB-Ethernet-Adapter. Erkennung muss `eth1`, `usb0` und `enx<mac>` (Debian USB-Naming) abdecken. ✓
2. **NTP** → **RTC DS3231 ist primäre Zeitquelle** (`/dev/rtc1`, produktiv). NTP ist optionaler Toggle. Wenn NTP aus: Zeit aus RTC + manuelle Zeitstellung möglich. Wenn NTP an: NTP-Server konfigurierbar, synchronisiert auch die RTC. Default NTP = aus. ✓
3. **VLAN** → Als Option im UI verfügbar (Feld VLAN-ID, default 0 = aus), nicht erzwungen. ✓

---

## Schritt-für-Schritt-Aufgaben

### Schritt 1: Sudoers-Fix auf Pi deployen

Root-Cause beheben: nmcli und netzwerk-relevante Befehle ohne Passwort erlauben.

**Aktionen:**

- Auf Pi via SSH als `docucontrol` einloggen
- Sudoers-Datei erstellen (mit `sudo tee` über eine temporäre Eskalation oder als root):

```
# /etc/sudoers.d/docucontrol-network
docucontrol ALL=(ALL) NOPASSWD: /usr/bin/nmcli
docucontrol ALL=(ALL) NOPASSWD: /usr/sbin/ip
docucontrol ALL=(ALL) NOPASSWD: /usr/bin/hostnamectl
docucontrol ALL=(ALL) NOPASSWD: /usr/bin/timedatectl
docucontrol ALL=(ALL) NOPASSWD: /usr/sbin/modprobe
```

- Syntax prüfen: `sudo visudo -c -f /etc/sudoers.d/docucontrol-network`
- Test: `sudo nmcli con show` als docucontrol ausführen → muss ohne Passwort funktionieren

**Hinweis:** Für die initiale Anlage ist einmalig das Sudo-Passwort `Xtend1478` erforderlich (interaktiv via SSH).

**Betroffene Dateien:**
- `/etc/sudoers.d/docucontrol-network` (Pi, neu)

---

### Schritt 2: network_manager.py — Multi-Interface + Hostname + NTP + VLAN

Die bestehende Datei auf dem Pi direkt editieren (oder lokal in `src/docucontrol/` spiegeln und deployen).

**Neue Konstanten:**

```python
LAN_INTERFACE_DEFAULT = "eth0"  # bisheriges LAN_INTERFACE

def get_available_interfaces():
    """Gibt alle Ethernet-Interfaces zurück außer lo."""
    ok, out, _ = _run("ip -o link show | awk -F': ' '{print $2}' | grep -v lo")
    ifaces = []
    for line in out.splitlines():
        name = line.strip().split('@')[0]  # VLAN-sub: eth0@eth0 → eth0
        if name and not name.startswith('lo'):
            ifaces.append(name)
    return ifaces
```

**Erweiterte `get_lan_status()` → `get_interface_status(iface='eth0')`:**

```python
def get_interface_status(iface='eth0'):
    result = {
        "iface": iface,
        "mode": "dhcp",   # aus config
        "config_ip": "", "config_netmask": "24",
        "config_gateway": "", "config_dns": "", "config_dns2": "",
        "config_vlan": 0,
        "current_ip": "", "current_gateway": "", "current_dns": "",
        "mac": "", "speed": "", "connected": False,
    }
    # Aus network_config.json für dieses Interface lesen
    cfg = load_network_config()
    iface_cfg = cfg.get("interfaces", {}).get(iface, cfg.get("lan", {}))
    result.update({
        "mode": iface_cfg.get("mode", "dhcp"),
        "config_ip": iface_cfg.get("ip", ""),
        "config_netmask": iface_cfg.get("netmask", "24"),
        "config_gateway": iface_cfg.get("gateway", ""),
        "config_dns": iface_cfg.get("dns", ""),
        "config_dns2": iface_cfg.get("dns2", ""),
        "config_vlan": iface_cfg.get("vlan", 0),
        "enabled": iface_cfg.get("enabled", True),
    })
    # Aktuelle Werte von System lesen (wie bisher)
    # ... ip addr show, ip route, resolv.conf ...
    return result
```

**`set_interface_static(iface, ip, netmask, gateway, dns, dns2='', vlan=0)`:**

```python
def set_interface_static(iface, ip, netmask="24", gateway="", dns="", dns2="", vlan=0):
    errors = []
    conn_name = _get_eth_connection(iface)
    if not conn_name:
        return False, f"Keine nmcli-Verbindung für {iface} gefunden"
    
    ok, _, err = _run(f'sudo nmcli con mod "{conn_name}" ipv4.method manual')
    if not ok: errors.append(f"method: {err}")
    
    ok, _, err = _run(f'sudo nmcli con mod "{conn_name}" ipv4.addresses {ip}/{netmask}')
    if not ok: errors.append(f"address: {err}")
    
    if gateway:
        ok, _, err = _run(f'sudo nmcli con mod "{conn_name}" ipv4.gateway {gateway}')
        if not ok: errors.append(f"gw: {err}")
    
    dns_str = dns + (" " + dns2 if dns2 else "")
    if dns_str.strip():
        ok, _, err = _run(f'sudo nmcli con mod "{conn_name}" ipv4.dns "{dns_str.strip()}"')
        if not ok: errors.append(f"dns: {err}")
    
    ok, _, err = _run(f'sudo nmcli con down "{conn_name}" && sudo nmcli con up "{conn_name}"')
    if not ok: errors.append(f"reconnect: {err}")
    
    # Config speichern
    cfg = load_network_config()
    if "interfaces" not in cfg: cfg["interfaces"] = {}
    cfg["interfaces"][iface] = {
        "mode": "static", "ip": ip, "netmask": netmask,
        "gateway": gateway, "dns": dns, "dns2": dns2, "vlan": vlan, "enabled": True
    }
    cfg["lan"] = cfg["interfaces"][iface]  # Backward-compat
    save_network_config(cfg)
    
    if errors:
        return False, "Teilweise Fehler: " + "; ".join(errors)
    return True, f"Statisch gesetzt: {ip}/{netmask}"
```

**Hostname:**

```python
def get_hostname():
    ok, out, _ = _run("hostname")
    return out.strip() if ok else ""

def set_hostname(name):
    if not re.match(r'^[a-zA-Z0-9\-]{1,63}$', name):
        return False, "Ungültiger Hostname"
    ok, _, err = _run(f'sudo hostnamectl set-hostname "{name}"')
    return ok, "Hostname gesetzt" if ok else err
```

**NTP:**

```python
def get_ntp_config():
    ok, out, _ = _run("timedatectl show --property=NTP,NTPSynchronized,Timesyncd")
    result = {"ntp_enabled": False, "ntp_synced": False, "ntp_server": "pool.ntp.org"}
    for line in out.splitlines():
        if "NTP=yes" in line: result["ntp_enabled"] = True
        if "NTPSynchronized=yes" in line: result["ntp_synced"] = True
    # NTP-Server aus timesyncd.conf lesen
    try:
        with open("/etc/systemd/timesyncd.conf") as f:
            for line in f:
                if line.startswith("NTP="):
                    result["ntp_server"] = line.split("=", 1)[1].strip()
    except Exception:
        pass
    return result

def set_ntp(server, enabled=True):
    errors = []
    # timesyncd.conf schreiben
    conf_line = f"[Time]\nNTP={server}\n"
    try:
        with open("/tmp/timesyncd_custom.conf", "w") as f:
            f.write(conf_line)
        ok, _, err = _run("sudo cp /tmp/timesyncd_custom.conf /etc/systemd/timesyncd.conf")
        if not ok: errors.append(err)
    except Exception as e:
        errors.append(str(e))
    
    ok, _, err = _run(f"sudo timedatectl set-ntp {'true' if enabled else 'false'}")
    if not ok: errors.append(err)
    
    if not errors:
        _run("sudo systemctl restart systemd-timesyncd")
    return not bool(errors), "; ".join(errors) if errors else "NTP gesetzt"
```

**Betroffene Dateien:**
- `/home/docucontrol/docupi/network_manager.py` (Pi)

---

### Schritt 3: app.py — neue API-Endpunkte

Ergänzungen **vor** `if __name__ == '__main__'`:

```python
# Neue Imports
from network_manager import (
    get_available_interfaces, get_interface_status,
    set_interface_static, set_interface_dhcp,
    get_hostname, set_hostname,
    get_ntp_config, set_ntp,
)

# GET /api/network/interfaces — Liste aller verfügbaren NICs
@app.route('/api/network/interfaces')
def api_network_interfaces():
    ifaces = get_available_interfaces()
    result = []
    for iface in ifaces:
        st = get_interface_status(iface)
        result.append(st)
    return jsonify(result)

# GET /api/network/iface/<dev>/status
@app.route('/api/network/iface/<dev>/status')
def api_iface_status(dev):
    return jsonify(get_interface_status(dev))

# POST /api/network/iface/<dev>/static
@app.route('/api/network/iface/<dev>/static', methods=['POST'])
def api_iface_static(dev):
    d = request.get_json(silent=True) or {}
    ip = d.get('ip', '').strip()
    netmask = str(d.get('netmask', '24')).strip()
    gw = d.get('gateway', '').strip()
    dns = d.get('dns', '').strip()
    dns2 = d.get('dns2', '').strip()
    vlan = int(d.get('vlan', 0))
    if not ip:
        return jsonify({'success': False, 'message': 'IP fehlt'}), 400
    ok, msg = set_interface_static(dev, ip, netmask, gw, dns, dns2, vlan)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 500)

# POST /api/network/iface/<dev>/dhcp
@app.route('/api/network/iface/<dev>/dhcp', methods=['POST'])
def api_iface_dhcp(dev):
    ok, msg = set_interface_dhcp(dev)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 500)

# GET /api/system/hostname
@app.route('/api/system/hostname')
def api_hostname_get():
    return jsonify({'hostname': get_hostname()})

# POST /api/system/hostname
@app.route('/api/system/hostname', methods=['POST'])
def api_hostname_set():
    d = request.get_json(silent=True) or {}
    name = d.get('hostname', '').strip()
    ok, msg = set_hostname(name)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 400)

# GET /api/system/ntp
@app.route('/api/system/ntp')
def api_ntp_get():
    return jsonify(get_ntp_config())

# POST /api/system/ntp
@app.route('/api/system/ntp', methods=['POST'])
def api_ntp_set():
    d = request.get_json(silent=True) or {}
    server = d.get('server', 'pool.ntp.org').strip()
    enabled = d.get('enabled', True)
    ok, msg = set_ntp(server, enabled)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 500)
```

**Bestehende Endpunkte beibehalten** (Backward-Compat):
- `GET /api/network/lan/status` → ruft intern `get_interface_status('eth0')` auf
- `POST /api/network/lan/static` → ruft intern `set_interface_static('eth0', ...)` auf
- `POST /api/network/lan/dhcp` → ruft intern `set_interface_dhcp('eth0')` auf

**Betroffene Dateien:**
- `/home/docucontrol/docupi/app.py` (Pi)

---

### Schritt 4: settings.html — Netzwerk-Tab neu strukturieren

Den Bereich "Netzwerk & TCP" in der `panelDevices`-Div vollständig ersetzen durch 4 neue Cards:

#### Card A: Schnittstelle 1 (Primär)

```html
<div class="card">
  <div class="card-head">
    <span><i class="bi bi-hdd-network"></i> Schnittstelle 1 — Primär</span>
    <span class="badge" id="iface1Status">—</span>
  </div>
  <div class="card-body">
    <!-- Interface Auswahl -->
    <div class="set-row">
      <div class="info"><div class="name">Schnittstelle</div><div class="desc">Ethernet-Adapter</div></div>
      <select class="ctrl" id="iface1Select" style="width:120px" onchange="loadIface(1)">
        <option value="eth0">eth0</option>
        <!-- dynamisch befüllt -->
      </select>
    </div>
    <!-- Aktuell -->
    <div class="set-row">
      <div class="info"><div class="name">Aktuelle IP</div><div class="desc">Zugewiesene Adresse</div></div>
      <span class="mono-ip" id="iface1CurrentIp">—</span>
    </div>
    <div class="set-row">
      <div class="info"><div class="name">MAC / Speed</div></div>
      <span class="value" id="iface1Mac" style="font-size:12px;color:var(--muted)">—</span>
    </div>
    <hr>
    <!-- IP-Modus -->
    <div class="set-row">
      <div class="info"><div class="name">IP-Modus</div><div class="desc">DHCP oder statisch</div></div>
      <select class="ctrl" id="iface1Mode" onchange="toggleIfaceForm(1, this.value)" style="width:120px">
        <option value="dhcp">DHCP</option>
        <option value="static">Statisch</option>
      </select>
    </div>
    <!-- Static Form -->
    <div id="iface1StaticForm" style="display:none;margin-top:8px">
      <div class="set-row" style="margin-bottom:6px">
        <div class="info"><div class="name">IP / Prefix</div></div>
        <input type="text" class="ctrl" id="iface1Ip" placeholder="192.168.0.180" style="width:160px">
        <span style="color:var(--muted);padding:0 4px">/</span>
        <input type="text" class="ctrl" id="iface1Prefix" placeholder="24" style="width:48px">
      </div>
      <div class="set-row" style="margin-bottom:6px">
        <div class="info"><div class="name">Gateway</div></div>
        <input type="text" class="ctrl" id="iface1Gw" placeholder="192.168.0.1" style="width:185px">
      </div>
      <div class="set-row" style="margin-bottom:6px">
        <div class="info"><div class="name">DNS 1</div></div>
        <input type="text" class="ctrl" id="iface1Dns" placeholder="192.168.0.1" style="width:185px">
      </div>
      <div class="set-row" style="margin-bottom:6px">
        <div class="info"><div class="name">DNS 2 (optional)</div></div>
        <input type="text" class="ctrl" id="iface1Dns2" placeholder="8.8.8.8" style="width:185px">
      </div>
      <div class="set-row" style="margin-bottom:6px">
        <div class="info"><div class="name">VLAN-ID</div><div class="desc">802.1Q Tagging (0 = aus)</div></div>
        <input type="number" class="ctrl" id="iface1Vlan" placeholder="0" min="0" max="4094" style="width:80px">
      </div>
      <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:10px">
        <button class="btn btn-outline" onclick="saveIfaceDhcp(1)">
          <i class="bi bi-arrow-counterclockwise"></i> DHCP
        </button>
        <button class="btn btn-primary" onclick="saveIfaceStatic(1)">
          <i class="bi bi-save"></i> Speichern
        </button>
      </div>
    </div>
  </div>
</div>
```

#### Card B: Schnittstelle 2 (Optional)

Identische Struktur wie Card A, mit:
- ID-Prefix `iface2` statt `iface1`
- Toggle "Schnittstelle aktivieren" oben in der Card
- Dropdown dynamisch aus `/api/network/interfaces` befüllt — nur NICs die **nicht** in Iface1 ausgewählt sind
- Bei `enabled: false` → grau dargestellt

#### Card C: Hostname

```html
<div class="card">
  <div class="card-head"><span><i class="bi bi-pc-display"></i> Gerätename im Netzwerk</span></div>
  <div class="card-body">
    <div class="set-row">
      <div class="info"><div class="name">Aktueller Hostname</div><div class="desc">DNS-Name im Klinumnetz</div></div>
      <span class="mono-ip" id="currentHostname">—</span>
    </div>
    <div class="set-row">
      <div class="info"><div class="name">Hostname ändern</div></div>
      <div style="display:flex;gap:6px;align-items:center">
        <input type="text" class="ctrl" id="newHostname" placeholder="docucontrol" style="width:160px">
        <button class="btn btn-outline" onclick="saveHostname()"><i class="bi bi-check-lg"></i> Setzen</button>
      </div>
    </div>
  </div>
</div>
```

#### Card D: Zeit & RTC/NTP

Primäre Zeitquelle ist die **DS3231 RTC** (`/dev/rtc1`). NTP ist optionaler Toggle.
Logik: NTP aus → Zeit kommt aus RTC beim Boot (`hwclock --hctosys`), manuelle Zeitstellung möglich.
NTP an → Zeitserver konfigurierbar, nach Sync wird RTC mit `hwclock --systohc` aktualisiert.

```html
<div class="card">
  <div class="card-head"><span><i class="bi bi-clock"></i> Zeit &amp; Uhr</span></div>
  <div class="card-body">
    <div class="set-row">
      <div class="info"><div class="name">Systemzeit</div><div class="desc">Aktuelle Uhrzeit (aus RTC DS3231)</div></div>
      <span class="value" id="sysTime" style="font-family:var(--mono)">—</span>
    </div>
    <div class="set-row">
      <div class="info"><div class="name">RTC-Zeit</div><div class="desc">Hardware-Uhr DS3231 (/dev/rtc1)</div></div>
      <span class="value" id="rtcTime" style="font-family:var(--mono);font-size:12.5px;color:var(--muted)">—</span>
    </div>
    <hr>
    <!-- Manuelle Zeitstellung (nur sichtbar wenn NTP aus) -->
    <div id="manualTimeRow" class="set-row">
      <div class="info">
        <div class="name">Zeit manuell setzen</div>
        <div class="desc">Datum und Uhrzeit direkt eingeben</div>
      </div>
      <div style="display:flex;gap:6px;align-items:center">
        <input type="datetime-local" class="ctrl" id="manualTime" style="width:185px">
        <button class="btn btn-outline" onclick="saveManualTime()"><i class="bi bi-check-lg"></i> Setzen</button>
      </div>
    </div>
    <hr>
    <div class="set-row">
      <div class="info">
        <div class="name">NTP-Synchronisation</div>
        <div class="desc">Automatische Zeitsynchronisation über Netzwerk (optional)</div>
      </div>
      <label class="switch">
        <input type="checkbox" id="ntpEnabled" onchange="toggleNtp(this.checked)">
        <span class="track"></span>
      </label>
    </div>
    <!-- NTP-Server-Feld: nur sichtbar wenn NTP aktiv -->
    <div id="ntpServerRow" style="display:none">
      <div class="set-row">
        <div class="info">
          <div class="name">NTP-Server</div>
          <div class="desc">Zeitserver des Kliniknetzes oder pool.ntp.org</div>
        </div>
        <div style="display:flex;gap:6px;align-items:center">
          <input type="text" class="ctrl" id="ntpServer" placeholder="pool.ntp.org" style="width:185px">
          <button class="btn btn-outline" onclick="saveNtp()"><i class="bi bi-check-lg"></i> Setzen</button>
        </div>
      </div>
      <div class="set-row">
        <div class="info"><div class="name">Sync-Status</div></div>
        <span class="value" id="ntpSyncStatus" style="font-size:12.5px;color:var(--muted)">—</span>
      </div>
    </div>
  </div>
</div>
```

**Toggle-Logik:** Wenn NTP-Toggle an → `ntpServerRow` einblenden, `manualTimeRow` ausblenden (und umgekehrt).

**Backend `get_ntp_config()` erweitern** um RTC-Zeit:
```python
def get_ntp_config():
    result = { "ntp_enabled": False, "ntp_synced": False, "ntp_server": "pool.ntp.org", "rtc_time": "" }
    ok, out, _ = _run("timedatectl show --property=NTP,NTPSynchronized 2>/dev/null")
    for line in out.splitlines():
        if line == "NTP=yes": result["ntp_enabled"] = True
        if line == "NTPSynchronized=yes": result["ntp_synced"] = True
    # RTC-Zeit
    ok, out, _ = _run("hwclock --get 2>/dev/null || hwclock -r 2>/dev/null")
    if ok: result["rtc_time"] = out.strip()
    # NTP-Server aus timesyncd.conf
    try:
        with open("/etc/systemd/timesyncd.conf") as f:
            for line in f:
                if line.startswith("NTP="):
                    result["ntp_server"] = line.split("=",1)[1].strip()
    except Exception:
        pass
    return result
```

**`set_manual_time(datetime_str)`:**
```python
def set_manual_time(datetime_str):
    # datetime_str: "2026-06-08 14:30:00"
    ok, _, err = _run(f'sudo timedatectl set-time "{datetime_str}"')
    if ok:
        _run("sudo hwclock --systohc")  # RTC aktualisieren
    return ok, "Zeit gesetzt" if ok else err
```

Neuer API-Endpunkt in app.py:
```python
@app.route('/api/system/time/manual', methods=['POST'])
def api_time_manual():
    d = request.get_json(silent=True) or {}
    t = d.get('datetime', '').strip()
    ok, msg = set_manual_time(t)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 400)
```

#### TCP-Empfang: aus "Netzwerk & TCP" herauslösen

Die TCP-Capture-Zeilen (Toggle, Statistik, letzter Empfang) bleiben im Tab, aber in einer separaten kleinen Card "TCP-Empfang" unterhalb der Interface-Cards.

#### JavaScript-Erweiterungen

```javascript
// Interfaces laden
function loadInterfaces() {
    fetch('/api/network/interfaces')
        .then(r => r.json())
        .then(ifaces => {
            fillIfaceDropdown(1, ifaces, 'eth0');
            fillIfaceDropdown(2, ifaces.filter(i => i.iface !== 'eth0'));
            if (ifaces[0]) applyIfaceStatus(1, ifaces[0]);
        }).catch(() => {});
}

function fillIfaceDropdown(num, ifaces, selected) {
    var sel = document.getElementById('iface' + num + 'Select');
    sel.innerHTML = '';
    if (ifaces.length === 0) {
        sel.innerHTML = '<option value="">— keine weiteren —</option>';
        sel.disabled = true;
        return;
    }
    ifaces.forEach(function(i) {
        var opt = document.createElement('option');
        opt.value = i.iface;
        opt.textContent = i.iface;
        if (i.iface === selected) opt.selected = true;
        sel.appendChild(opt);
    });
}

function loadIface(num) {
    var dev = document.getElementById('iface' + num + 'Select').value;
    if (!dev) return;
    fetch('/api/network/iface/' + dev + '/status')
        .then(r => r.json())
        .then(d => applyIfaceStatus(num, d))
        .catch(() => {});
}

function applyIfaceStatus(num, d) {
    document.getElementById('iface' + num + 'CurrentIp').textContent = d.current_ip || '—';
    document.getElementById('iface' + num + 'Mac').textContent =
        (d.mac || '—') + (d.speed ? ' · ' + d.speed : '');
    document.getElementById('iface' + num + 'Mode').value = d.mode || 'dhcp';
    toggleIfaceForm(num, d.mode || 'dhcp');
    if (d.mode === 'static') {
        document.getElementById('iface' + num + 'Ip').value = d.config_ip || '';
        document.getElementById('iface' + num + 'Prefix').value = d.config_netmask || '24';
        document.getElementById('iface' + num + 'Gw').value = d.config_gateway || '';
        document.getElementById('iface' + num + 'Dns').value = d.config_dns || '';
        document.getElementById('iface' + num + 'Dns2').value = d.config_dns2 || '';
        document.getElementById('iface' + num + 'Vlan').value = d.config_vlan || 0;
    }
    // Status-Badge
    var badge = document.getElementById('iface' + num + 'Status');
    if (badge) {
        badge.textContent = d.connected ? 'Verbunden' : 'Getrennt';
        badge.style.background = d.connected ? 'var(--success)' : 'var(--muted)';
    }
}

function toggleIfaceForm(num, mode) {
    document.getElementById('iface' + num + 'StaticForm').style.display =
        mode === 'static' ? '' : 'none';
}

function saveIfaceStatic(num) {
    var dev = document.getElementById('iface' + num + 'Select').value;
    var ip  = document.getElementById('iface' + num + 'Ip').value.trim();
    var pfx = document.getElementById('iface' + num + 'Prefix').value.trim() || '24';
    var gw  = document.getElementById('iface' + num + 'Gw').value.trim();
    var dns = document.getElementById('iface' + num + 'Dns').value.trim();
    var dns2= document.getElementById('iface' + num + 'Dns2').value.trim();
    var vlan= parseInt(document.getElementById('iface' + num + 'Vlan').value) || 0;
    if (!ip || !gw) { alert('IP und Gateway sind Pflichtfelder'); return; }
    if (!confirm('IP auf ' + ip + '/' + pfx + ' setzen?\nVerbindung trennt kurz.')) return;
    fetch('/api/network/iface/' + dev + '/static', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ip, netmask: pfx, gateway: gw, dns, dns2, vlan})
    }).then(r => r.json())
      .then(d => { alert(d.message || (d.success ? 'Gespeichert' : 'Fehler')); loadIface(num); })
      .catch(() => alert('Netzwerkfehler'));
}

function saveIfaceDhcp(num) {
    var dev = document.getElementById('iface' + num + 'Select').value;
    if (!confirm('Auf DHCP wechseln?')) return;
    fetch('/api/network/iface/' + dev + '/dhcp', {method: 'POST'})
        .then(r => r.json())
        .then(d => { alert(d.message); loadIface(num); })
        .catch(() => alert('Fehler'));
}

function loadHostname() {
    fetch('/api/system/hostname')
        .then(r => r.json())
        .then(d => {
            document.getElementById('currentHostname').textContent = d.hostname || '—';
            document.getElementById('newHostname').placeholder = d.hostname || 'docucontrol';
        }).catch(() => {});
}

function saveHostname() {
    var name = document.getElementById('newHostname').value.trim();
    if (!name) return;
    fetch('/api/system/hostname', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({hostname: name})
    }).then(r => r.json())
      .then(d => { alert(d.message); loadHostname(); })
      .catch(() => alert('Fehler'));
}

function loadNtp() {
    fetch('/api/system/ntp')
        .then(r => r.json())
        .then(d => {
            document.getElementById('ntpEnabled').checked = d.ntp_enabled || false;
            document.getElementById('ntpServer').value = d.ntp_server || 'pool.ntp.org';
            document.getElementById('ntpSyncStatus').textContent =
                d.ntp_synced ? 'Synchronisiert' : 'Nicht synchronisiert';
        }).catch(() => {});
}

function toggleNtp(checked) {
    var server = document.getElementById('ntpServer').value.trim() || 'pool.ntp.org';
    fetch('/api/system/ntp', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({server, enabled: checked})
    }).catch(() => {});
}

function saveNtp() {
    var server = document.getElementById('ntpServer').value.trim();
    var enabled = document.getElementById('ntpEnabled').checked;
    if (!server) return;
    fetch('/api/system/ntp', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({server, enabled})
    }).then(r => r.json())
      .then(d => { alert(d.message); loadNtp(); })
      .catch(() => alert('Fehler'));
}
```

**Init in `loadDeviceSettings()`** ergänzen:

```javascript
loadInterfaces();
loadHostname();
loadNtp();
// Systemzeit aktualisieren
function updateSysTime() {
    document.getElementById('sysTime').textContent = new Date().toLocaleTimeString('de-DE');
}
updateSysTime();
setInterval(updateSysTime, 1000);
```

**Betroffene Dateien:**
- `src/docucontrol/templates/settings.html`

---

### Schritt 5: Deployment auf Pi

```bash
# Von Workspace deployen
scp -i ~/.ssh/id_ed25519 \
    src/docucontrol/templates/settings.html \
    docucontrol@192.168.0.171:/home/docucontrol/docupi/templates/settings.html

# network_manager.py (als vollständige Datei deployen)
scp -i ~/.ssh/id_ed25519 \
    /tmp/network_manager_new.py \
    docucontrol@192.168.0.171:/home/docucontrol/docupi/network_manager.py

# app.py nur neue Endpunkte einfügen (via SSH-Edit)
# Service restart
ssh -i ~/.ssh/id_ed25519 docucontrol@192.168.0.171 \
    "cd /home/docucontrol/docupi && sudo systemctl restart docucontrol.service"
```

**Sudoers-Datei:**

```bash
# Einmalig mit Passwort (Xtend1478):
ssh -i ~/.ssh/id_ed25519 docucontrol@192.168.0.171 \
    "echo 'Xtend1478' | sudo -S tee /etc/sudoers.d/docucontrol-network << 'EOF'
docucontrol ALL=(ALL) NOPASSWD: /usr/bin/nmcli
docucontrol ALL=(ALL) NOPASSWD: /usr/sbin/ip
docucontrol ALL=(ALL) NOPASSWD: /usr/bin/hostnamectl
docucontrol ALL=(ALL) NOPASSWD: /usr/bin/timedatectl
EOF
sudo chmod 440 /etc/sudoers.d/docucontrol-network"
```

**Betroffene Dateien:**
- `/etc/sudoers.d/docucontrol-network` (Pi)
- Deployment-Skripte (optional, bestehende `deploy_docucontrol_design.sh` nutzen)

---

### Schritt 6: Testen

**IP-Fix validieren:**
1. Web-UI öffnen: `http://192.168.0.171/settings`
2. IP-Modus → "Statisch", IP `192.168.0.180/24`, GW `192.168.0.1`, DNS `192.168.0.1`
3. Speichern → Verbindung trennt kurz → neu verbinden auf `http://192.168.0.180/settings`
4. Dashboard zeigt neue IP in "Aktuelle IP"

**Hostname-Test:**
1. Hostname auf `docucontrol-essen` setzen
2. `ping docucontrol-essen.local` vom selben Netz (mDNS)

**NTP-Test:**
1. NTP-Server auf `pool.ntp.org` setzen → Sync-Status muss "Synchronisiert" zeigen

**Zweites Interface:**
- Mit USB-Ethernet-Adapter testen (erscheint als `eth1` oder `usb0`)
- Dropdown soll `eth1` anzeigen
- Statische IP `10.0.0.1/24` auf Interface 2 setzen

**Betroffene Dateien:**
- Keine Codeänderungen in diesem Schritt

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

- `app.py` importiert `network_manager.py` — bestehende Imports müssen erweitert werden
- `settings.html` referenziert `/api/network/lan/status` (bleibt kompatibel via Wrapper)
- `CLAUDE.md` — Abschnitt "DocuControl Web-Interface / Neue API-Endpunkte" muss aktualisiert werden

### Nötige Updates für Konsistenz

- `CLAUDE.md`: Neue API-Endpunkte dokumentieren
- `context/current-data.md`: Status "Netzwerk-Management vollständig" eintragen

---

## Validierungs-Checkliste

- [ ] `sudo nmcli con show` funktioniert ohne Passwort als `docucontrol`
- [ ] Statische IP `.180` setzt sich durch → Gerät unter neuer IP erreichbar
- [ ] `/api/network/interfaces` gibt JSON mit eth0-Status zurück
- [ ] Interface-Dropdown in Schnittstelle 2 zeigt "— keine weiteren —" (nur eth0 vorhanden)
- [ ] Hostname-Card zeigt aktuellen Hostname
- [ ] NTP-Server setzen → `timedatectl show` zeigt neuen Server
- [ ] Service-Restart < 1s (os._exit-Fix weiterhin aktiv)
- [ ] Backward-Compat: `/api/network/lan/status` antwortet noch korrekt

---

## Erfolgskriterien

1. Statische IP `.180` ist nach Klick auf "Speichern" tatsächlich aktiv (Gerät unter neuer IP erreichbar)
2. Alle 4 Klinik-IT-Felder (Hostname, DNS2, NTP, VLAN) sind über die UI konfigurierbar und werden persistent gespeichert
3. Zweites Interface erscheint im Dropdown sobald ein zweiter Adapter angeschlossen wird (dynamisch, kein Neustart nötig)

---

## Notizen

- **VLAN-Implementierung**: UI-Feld vorhanden (VLAN-ID, default 0 = aus). Wenn VLAN-ID > 0, wird ein Sub-Interface via `nmcli con add type vlan` erstellt — Implementierung in Schritt 2, aber erst aktiv wenn Wert > 0 eingegeben wird.
- **USB-Ethernet Naming auf Debian**: USB-Adapter erscheinen als `eth1`, `usb0` oder `enx<mac>` — `get_available_interfaces()` muss alle diese Muster erkennen. Filter: `ip link show` → alle Interfaces außer `lo`, `wlan*`, VLAN-Subinterfaces (`*.*`).
- **RTC DS3231 ist primäre Zeitquelle**: `hwclock --hctosys` beim Boot lädt RTC → System. `timedatectl set-ntp false` deaktiviert NTP, RTC bleibt maßgeblich. Bei manueller Zeitstellung: `timedatectl set-time` + `hwclock --systohc`.
- **NTP und RTC kombiniert**: Wenn NTP aktiv und synchronisiert, schreibt `systemd-timesyncd` automatisch die RTC zurück (via `SYNC_TO_HW=yes` in timesyncd.conf oder manuell via `hwclock --systohc` nach Sync).
- **IPv6**: Bewusst ignoriert — für industriellen Einsatz nicht relevant.
- **Firewall/nftables**: Wenn zweites Interface für TCP/9100 genutzt wird, muss die nftables-Port-Redirect-Regel auf das korrekte Interface angepasst werden — separater Schritt wenn benötigt.

---

## Implementierungsnotizen

**Implementiert:** 2026-06-08

### Zusammenfassung

- Sudoers-Fix `/etc/sudoers.d/docucontrol-network` auf Pi deployed (nmcli, ip, hostnamectl, timedatectl, hwclock)
- `network_manager.py` v3 geschrieben: Multi-Interface, Hostname, NTP/RTC, VLAN, korrekte Fehler-Propagierung
- `app.py` gepatcht: Import erweitert, `api_lan_static` auf `set_interface_static` umgestellt, 7 neue Routen hinzugefügt
- `settings.html` komplett neu: 4 neue Cards (Schnittstelle 1, Schnittstelle 2, Hostname, Zeit & Uhr), TCP in eigene Card
- IP erfolgreich auf 192.168.0.180 gesetzt und verifiziert

### Abweichungen vom Plan

1. **nmcli-Befehlsreihenfolge**: Plan hatte `method manual` und `addresses` als separate Befehle. nmcli validiert sofort und wirft Fehler wenn method=manual ohne Adresse gesetzt wird. Fix: alle Parameter in einem einzigen `nmcli con mod`-Befehl kombiniert.
2. **SSH-Key**: CLAUDE.md nannte `~/.ssh/docucontrol_id` — existiert nicht. Tatsächlicher Key: `~/.ssh/id_ed25519`. Kein Auswirkung auf Funktion.

### Aufgetretene Probleme

- **nmcli-Validierungsfehler** beim ersten Testlauf: `ipv4.method: method 'manual' requires at least an address or a route`. Gelöst durch Kombination aller Parameter in einem Befehl.
