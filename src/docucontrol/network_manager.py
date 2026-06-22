#!/usr/bin/env python3
"""
DocuPi-3000 - Network Manager v3
Verwaltet WiFi Hotspot, LAN-Konfiguration, Multi-Interface, Hostname, NTP/RTC.
"""

import subprocess
import os
import re
import json
import logging
import time

logger = logging.getLogger("docupi.network")

HOSTAPD_CONF = "/etc/hostapd/hostapd.conf"
DNSMASQ_CONF = "/etc/dnsmasq.d/docupi-hotspot.conf"
NETWORK_CONFIG = "/home/docucontrol/docupi/network_config.json"
HOSTAPD_PID = "/run/docupi-hostapd.pid"
DNSMASQ_PID = "/run/docupi-dnsmasq.pid"
HOTSPOT_INTERFACE = "wlan0"
LAN_INTERFACE = "eth0"
HOTSPOT_IP = "10.3.141.1"
HOTSPOT_DHCP_START = "10.3.141.50"
HOTSPOT_DHCP_END = "10.3.141.150"
CAPTIVE_PORT = 5000

DEFAULT_NETWORK_CONFIG = {
    "hotspot": {
        "enabled": False,
        "ssid": "DocuControl",
        "password": "DocuCtrl2026",
        "hidden": False,
        "channel": 6,
    },
    "lan": {
        "mode": "dhcp",
        "ip": "192.168.178.83",
        "netmask": "24",
        "gateway": "192.168.178.1",
        "dns": "192.168.178.1",
        "dns2": "",
        "vlan": 0,
    },
    "interfaces": {},
}


def _run(cmd, timeout=15):
    logger.debug(f"CMD: {cmd}")
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True,
                           text=True, timeout=timeout)
        if r.returncode != 0 and r.stderr.strip():
            logger.warning(f"CMD err: {cmd[:60]} -> {r.stderr.strip()[:150]}")
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        logger.error(f"CMD timeout: {cmd[:60]}")
        return False, "", "timeout"
    except Exception as e:
        logger.error(f"CMD error: {cmd[:60]} -> {e}")
        return False, "", str(e)


def load_network_config():
    if os.path.isfile(NETWORK_CONFIG):
        try:
            with open(NETWORK_CONFIG, "r") as f:
                cfg = json.load(f)
            for section in DEFAULT_NETWORK_CONFIG:
                if section not in cfg:
                    cfg[section] = DEFAULT_NETWORK_CONFIG[section]
                else:
                    for k, v in DEFAULT_NETWORK_CONFIG[section].items():
                        if k not in cfg[section]:
                            cfg[section][k] = v
            return cfg
        except Exception as e:
            logger.error(f"Config load: {e}")
    return json.loads(json.dumps(DEFAULT_NETWORK_CONFIG))


def save_network_config(cfg):
    os.makedirs(os.path.dirname(NETWORK_CONFIG), exist_ok=True)
    with open(NETWORK_CONFIG, "w") as f:
        json.dump(cfg, f, indent=2)


# ===================================================================
# HOTSPOT
# ===================================================================

def _write_hostapd_conf(cfg):
    hotspot = cfg["hotspot"]
    conf = (
        f"interface={HOTSPOT_INTERFACE}\n"
        f"driver=nl80211\n"
        f"ssid={hotspot['ssid']}\n"
        f"hw_mode=g\n"
        f"channel={hotspot['channel']}\n"
        f"wmm_enabled=0\n"
        f"macaddr_acl=0\n"
        f"auth_algs=1\n"
        f"ignore_broadcast_ssid={'1' if hotspot['hidden'] else '0'}\n"
        f"wpa=2\n"
        f"wpa_passphrase={hotspot['password']}\n"
        f"wpa_key_mgmt=WPA-PSK\n"
        f"rsn_pairwise=CCMP\n"
    )
    try:
        with open("/tmp/docupi_hostapd.conf", "w") as f:
            f.write(conf)
        _run(f"sudo cp /tmp/docupi_hostapd.conf {HOSTAPD_CONF}")
        return True
    except Exception as e:
        logger.error(f"hostapd conf: {e}")
        return False


def _write_dnsmasq_conf():
    conf = (
        f"interface={HOTSPOT_INTERFACE}\n"
        f"bind-interfaces\n"
        f"dhcp-range={HOTSPOT_DHCP_START},{HOTSPOT_DHCP_END},255.255.255.0,24h\n"
        f"address=/#/{HOTSPOT_IP}\n"
    )
    try:
        with open("/tmp/docupi_dnsmasq.conf", "w") as f:
            f.write(conf)
        _run(f"sudo cp /tmp/docupi_dnsmasq.conf {DNSMASQ_CONF}")
        return True
    except Exception as e:
        logger.error(f"dnsmasq conf: {e}")
        return False


def _is_hostapd_running():
    ok, out, _ = _run("pgrep -x hostapd 2>/dev/null")
    return ok and out.strip() != ""


def _kill_hotspot_processes():
    _run("sudo killall hostapd 2>/dev/null")
    _run(f"sudo kill $(cat {DNSMASQ_PID} 2>/dev/null) 2>/dev/null")
    _run(f"sudo pkill -f 'dnsmasq.*docupi-hotspot' 2>/dev/null")
    time.sleep(0.5)


def _setup_captive_nft():
    _cleanup_captive_nft()
    try:
        _run(f"sudo /usr/sbin/iptables -t nat -A PREROUTING -i {HOTSPOT_INTERFACE} -p tcp --dport 80 -j DNAT --to-destination {HOTSPOT_IP}:{CAPTIVE_PORT}")
        _run(f"sudo /usr/sbin/iptables -t nat -A PREROUTING -i {HOTSPOT_INTERFACE} -p tcp --dport 443 -j DNAT --to-destination {HOTSPOT_IP}:{CAPTIVE_PORT}")
        logger.info("iptables captive portal active")
    except Exception as e:
        logger.error(f"captive portal setup: {e}")


def _cleanup_captive_nft():
    _run("sudo /usr/sbin/iptables -t nat -F PREROUTING 2>/dev/null")
    _run("sudo /usr/sbin/nft delete table ip docupi_captive 2>/dev/null")


def start_hotspot():
    cfg = load_network_config()
    logger.info(f"Starting hotspot: SSID={cfg['hotspot']['ssid']}")
    _kill_hotspot_processes()
    _cleanup_captive_nft()
    _run("sudo /usr/sbin/rfkill unblock wifi")
    time.sleep(0.5)
    _run(f"sudo nmcli device set {HOTSPOT_INTERFACE} managed no")
    _run(f"sudo nmcli device disconnect {HOTSPOT_INTERFACE} 2>/dev/null")
    time.sleep(1)
    _run(f"sudo ip link set {HOTSPOT_INTERFACE} down")
    _run(f"sudo ip addr flush dev {HOTSPOT_INTERFACE}")
    _run(f"sudo ip addr add {HOTSPOT_IP}/24 dev {HOTSPOT_INTERFACE}")
    _run(f"sudo ip link set {HOTSPOT_INTERFACE} up")
    time.sleep(1)
    _write_hostapd_conf(cfg)
    _write_dnsmasq_conf()
    ok, out, err = _run(f"sudo /usr/sbin/hostapd -B -P {HOSTAPD_PID} {HOSTAPD_CONF}")
    if not ok:
        logger.error(f"hostapd failed: {err}")
        return False, f"hostapd Fehler: {err[:100]}"
    time.sleep(2)
    if not _is_hostapd_running():
        return False, "hostapd konnte nicht gestartet werden"
    _run(f"sudo /usr/sbin/dnsmasq --conf-file={DNSMASQ_CONF} "
         f"--pid-file={DNSMASQ_PID} --listen-address={HOTSPOT_IP} "
         f"--except-interface=lo --bind-interfaces")
    _setup_captive_nft()
    cfg["hotspot"]["enabled"] = True
    save_network_config(cfg)
    logger.info("Hotspot gestartet")
    return True, "Hotspot gestartet"


def stop_hotspot():
    logger.info("Stopping hotspot")
    _kill_hotspot_processes()
    _cleanup_captive_nft()
    _run(f"sudo ip addr flush dev {HOTSPOT_INTERFACE}")
    _run(f"sudo ip link set {HOTSPOT_INTERFACE} down")
    _run(f"sudo nmcli device set {HOTSPOT_INTERFACE} managed yes")
    cfg = load_network_config()
    cfg["hotspot"]["enabled"] = False
    save_network_config(cfg)
    logger.info("Hotspot gestoppt")
    return True, "Hotspot gestoppt"


def update_hotspot_config(ssid=None, password=None, hidden=None, channel=None):
    cfg = load_network_config()
    changed = False
    if ssid is not None and len(ssid) >= 1:
        cfg["hotspot"]["ssid"] = ssid; changed = True
    if password is not None and len(password) >= 8:
        cfg["hotspot"]["password"] = password; changed = True
    if hidden is not None:
        cfg["hotspot"]["hidden"] = bool(hidden); changed = True
    if channel is not None and 1 <= int(channel) <= 13:
        cfg["hotspot"]["channel"] = int(channel); changed = True
    if changed:
        save_network_config(cfg)
        if cfg["hotspot"]["enabled"] and _is_hostapd_running():
            stop_hotspot()
            return start_hotspot()
    return True, "Konfiguration gespeichert"


def get_hotspot_status():
    cfg = load_network_config()
    running = _is_hostapd_running()
    clients = 0
    if running:
        ok, out, _ = _run(f"sudo iw dev {HOTSPOT_INTERFACE} station dump 2>/dev/null | grep -c Station")
        try: clients = int(out)
        except: pass
    return {
        "enabled": cfg["hotspot"]["enabled"],
        "running": running,
        "ssid": cfg["hotspot"]["ssid"],
        "password": cfg["hotspot"]["password"],
        "hidden": cfg["hotspot"]["hidden"],
        "channel": cfg["hotspot"]["channel"],
        "clients": clients,
        "ip": HOTSPOT_IP,
    }


# ===================================================================
# MULTI-INTERFACE MANAGEMENT
# ===================================================================

def get_available_interfaces():
    """Gibt alle Ethernet-Interfaces zurück (außer lo, wlan*, VLAN-Subs)."""
    ok, out, _ = _run("ip -o link show 2>/dev/null")
    ifaces = []
    for line in out.splitlines():
        m = re.match(r'^\d+:\s+(\S+):', line)
        if not m:
            continue
        name = m.group(1).split('@')[0]
        if name == 'lo':
            continue
        if name.startswith('wlan'):
            continue
        if '.' in name:  # VLAN-Sub-Interface
            continue
        ifaces.append(name)
    return ifaces


def _get_eth_connection(iface=None):
    """Findet den nmcli-Verbindungsnamen für ein Interface."""
    target = iface or LAN_INTERFACE
    ok, out, _ = _run("nmcli -t -f NAME,DEVICE con show --active 2>/dev/null")
    for line in out.split("\n"):
        parts = line.split(":")
        if len(parts) >= 2 and parts[1] == target:
            return parts[0]
    # Fallback: ersten Ethernet-Eintrag nehmen (für eth0 ohne aktive Verbindung)
    ok, out, _ = _run("nmcli -t -f NAME,TYPE,DEVICE con show 2>/dev/null")
    for line in out.split("\n"):
        parts = line.split(":")
        if len(parts) >= 3 and "ethernet" in parts[1].lower():
            if parts[2] == target or (target == LAN_INTERFACE and parts[2] in ('', target)):
                return parts[0]
    return None


def get_interface_status(iface='eth0'):
    """Liefert Konfiguration und aktuellen Status eines Interfaces."""
    cfg = load_network_config()
    iface_cfg = cfg.get("interfaces", {}).get(iface) or cfg.get("lan", {})

    result = {
        "iface": iface,
        "mode": iface_cfg.get("mode", "dhcp"),
        "config_ip": iface_cfg.get("ip", ""),
        "config_netmask": iface_cfg.get("netmask", "24"),
        "config_gateway": iface_cfg.get("gateway", ""),
        "config_dns": iface_cfg.get("dns", ""),
        "config_dns2": iface_cfg.get("dns2", ""),
        "config_vlan": iface_cfg.get("vlan", 0),
        "enabled": iface_cfg.get("enabled", True),
        "connected": False,
        "current_ip": "",
        "current_gateway": "",
        "current_dns": "",
        "mac": "",
        "speed": "",
    }

    ok, out, _ = _run(f"cat /sys/class/net/{iface}/carrier 2>/dev/null")
    result["connected"] = ok and out.strip() == "1"

    ok, out, _ = _run(f"ip -4 addr show {iface} 2>/dev/null")
    ip_match = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)", out)
    if ip_match:
        result["current_ip"] = ip_match.group(1)

    ok, out, _ = _run("ip route show default 2>/dev/null")
    gw_match = re.search(r"default via (\d+\.\d+\.\d+\.\d+)", out)
    if gw_match:
        result["current_gateway"] = gw_match.group(1)

    ok, out, _ = _run("grep nameserver /etc/resolv.conf 2>/dev/null | head -1")
    dns_match = re.search(r"nameserver\s+(\d+\.\d+\.\d+\.\d+)", out)
    if dns_match:
        result["current_dns"] = dns_match.group(1)

    ok, out, _ = _run(f"cat /sys/class/net/{iface}/address 2>/dev/null")
    if ok and out.strip():
        result["mac"] = out.strip()

    ok, out, _ = _run(f"cat /sys/class/net/{iface}/speed 2>/dev/null")
    if ok and out.strip().isdigit():
        result["speed"] = f"{out.strip()} Mbit/s"

    return result


NM_CONN_DIR = "/etc/NetworkManager/system-connections"
NFTABLES_CONF = "/etc/nftables-docucontrol.conf"


def _run_stdin(cmd, data):
    """Führt Befehl mit stdin-Daten aus (für sudo tee)."""
    try:
        r = subprocess.run(cmd, shell=True, input=data.encode(),
                           capture_output=True, timeout=15)
        return r.returncode == 0, r.stdout.decode().strip(), r.stderr.decode().strip()
    except Exception as e:
        return False, "", str(e)


def _write_nm_keyfile(iface, ip, netmask, gateway, dns, dns2):
    """Schreibt persistente NM-Verbindungsdatei in /etc/ via sudo tee."""
    conn_id = f"docucontrol-{iface}"
    dns_line = ";".join(filter(None, [dns, dns2]))
    if dns_line:
        dns_line += ";"
    content = f"""[connection]
id={conn_id}
type=ethernet
interface-name={iface}
autoconnect=true
autoconnect-priority=10

[ethernet]
wake-on-lan=0

[ipv4]
method=manual
address1={ip}/{netmask},{gateway}
dns={dns_line}

[ipv6]
method=disabled

[proxy]
"""
    path = f"{NM_CONN_DIR}/{conn_id}.nmconnection"
    ok, _, err = _run_stdin(f"sudo tee {path}", content)
    if ok:
        _run(f"sudo chmod 600 {path}")
    return ok, err


def _write_nftables_conf(static_ip=None):
    """Aktualisiert nftables-Config -- interface-basierte Regeln fuer eth0 + eth1."""
    conf = """table ip docucontrol_nat {
    chain prerouting {
        type nat hook prerouting priority dstnat; policy accept;
        iif eth0 tcp dport 80 redirect to :5000
        iif eth1 tcp dport 80 redirect to :5000
        iif eth0 tcp dport 443 redirect to :5443
        iif eth1 tcp dport 443 redirect to :5443
        tcp dport 9100 accept
    }
    chain output {
        type nat hook output priority -100; policy accept;
        ip daddr 127.0.0.1 tcp dport 80 redirect to :5000
        ip daddr 127.0.0.1 tcp dport 443 redirect to :5443
    }
}
"""
    ok, _, err = _run_stdin(f"sudo tee {NFTABLES_CONF}", conf)
    if ok:
        _run("sudo nft flush table ip docucontrol_nat 2>/dev/null; sudo nft -f " + NFTABLES_CONF)
    return ok, err


def set_interface_static(iface, ip, netmask="24", gateway="", dns="", dns2="", vlan=0):
    """Setzt statische IP — persistent via NM-Keyfile in /etc/ + nftables-Update."""
    if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
        return False, "Ungültige IP-Adresse"

    errors = []
    logger.info(f"set_interface_static: {iface} -> {ip}/{netmask}")

    # 1. Persistente NM-Keyfile schreiben
    ok, err = _write_nm_keyfile(iface, ip, netmask, gateway, dns, dns2)
    if not ok:
        errors.append(f"keyfile: {err}")

    # 2. NM neu laden + Connection neu aktivieren
    conn_id = f"docucontrol-{iface}"
    _run("sudo nmcli con reload")
    # Alle anderen aktiven Connections für dieses Interface deaktivieren
    ok, out, _ = _run("nmcli -t -f NAME,DEVICE con show --active 2>/dev/null")
    for line in out.splitlines():
        parts = line.split(":")
        if len(parts) >= 2 and parts[1] == iface and parts[0] != conn_id:
            _run(f'sudo nmcli con down "{parts[0]}" 2>/dev/null')
    # Down+Up in einem Shell-Befehl — verhindert NM-Autoconnect von netplan-eth0 dazwischen
    ok, _, err = _run(f'sudo nmcli con down "{conn_id}" 2>/dev/null; sudo nmcli con up "{conn_id}"')
    if not ok:
        errors.append(f"nmcli up: {err}")

    # 3. nftables mit neuer IP aktualisieren
    ok, err = _write_nftables_conf(ip)
    if not ok:
        errors.append(f"nftables: {err}")

    # 4. Persistent config speichern
    cfg = load_network_config()
    if "interfaces" not in cfg:
        cfg["interfaces"] = {}
    iface_data = {
        "mode": "static", "ip": ip, "netmask": netmask,
        "gateway": gateway, "dns": dns, "dns2": dns2,
        "vlan": vlan, "enabled": True,
    }
    cfg["interfaces"][iface] = iface_data
    if iface == LAN_INTERFACE:
        cfg["lan"] = iface_data
    save_network_config(cfg)

    if errors:
        return False, "Fehler: " + "; ".join(errors)
    return True, f"Statisch gesetzt: {ip}/{netmask}"


def set_interface_dhcp(iface=None):
    """Setzt Interface auf DHCP — schreibt NM-Keyfile mit method=auto."""
    target = iface or LAN_INTERFACE
    errors = []

    logger.info(f"set_interface_dhcp: {target}")

    # Persistente NM-Keyfile für DHCP schreiben (via sudo tee)
    conn_id = f"docucontrol-{target}"
    content = f"""[connection]
id={conn_id}
type=ethernet
interface-name={target}
autoconnect=true
autoconnect-priority=10

[ethernet]
wake-on-lan=0

[ipv4]
method=auto

[ipv6]
method=disabled

[proxy]
"""
    path = f"{NM_CONN_DIR}/{conn_id}.nmconnection"
    ok, _, err = _run_stdin(f"sudo tee {path}", content)
    if ok:
        _run(f"sudo chmod 600 {path}")
    else:
        errors.append(f"keyfile: {err}")

    # nftables VOR nmcli down/up aktualisieren — nmcli trennt kurz die Verbindung
    # und der HTTP-Request würde sonst abgebrochen bevor nftables aktualisiert wird
    ok, err = _write_nftables_conf(None)
    if not ok:
        errors.append(f"nftables: {err}")

    _run("sudo nmcli con reload")
    ok, _, err = _run(f'sudo nmcli con down "{conn_id}" 2>/dev/null; sudo nmcli con up "{conn_id}"')
    if not ok:
        errors.append(f"nmcli up: {err}")

    cfg = load_network_config()
    if "interfaces" not in cfg:
        cfg["interfaces"] = {}
    iface_data = {"mode": "dhcp", "ip": "", "netmask": "24", "gateway": "", "dns": "", "dns2": "", "vlan": 0, "enabled": True}
    cfg["interfaces"][target] = iface_data
    if target == LAN_INTERFACE:
        cfg["lan"]["mode"] = "dhcp"
    save_network_config(cfg)

    if errors:
        return False, "Teilweise Fehler: " + "; ".join(errors)
    return True, f"{target} auf DHCP umgestellt"


# ===================================================================
# BACKWARD-COMPAT WRAPPERS (für bestehende app.py-Aufrufe)
# ===================================================================

def get_lan_status():
    return get_interface_status(LAN_INTERFACE)


def set_lan_dhcp():
    return set_interface_dhcp(LAN_INTERFACE)


def set_lan_static(ip, netmask="24", gateway="", dns=""):
    return set_interface_static(LAN_INTERFACE, ip, netmask, gateway, dns)


# ===================================================================
# HOSTNAME
# ===================================================================

def get_hostname():
    ok, out, _ = _run("hostname")
    return out.strip() if ok else ""


def set_hostname(name):
    if not re.match(r'^[a-zA-Z0-9\-]{1,63}$', name):
        return False, "Ungültiger Hostname (nur A-Z, 0-9, Bindestrich, max. 63 Zeichen)"
    ok, _, err = _run(f'sudo hostnamectl set-hostname "{name}"')
    if ok:
        logger.info(f"Hostname gesetzt: {name}")
    return ok, "Hostname gesetzt" if ok else err


# ===================================================================
# ZEIT / RTC / NTP
# ===================================================================

def get_time_status():
    """Liefert Systemzeit, RTC-Zeit und NTP-Konfiguration."""
    result = {
        "ntp_enabled": False,
        "ntp_synced": False,
        "ntp_server": "pool.ntp.org",
        "rtc_time": "",
        "system_time": "",
    }

    ok, out, _ = _run("timedatectl show --property=NTP,NTPSynchronized 2>/dev/null")
    for line in out.splitlines():
        if line.strip() == "NTP=yes":
            result["ntp_enabled"] = True
        if line.strip() == "NTPSynchronized=yes":
            result["ntp_synced"] = True

    ok, out, _ = _run("sudo hwclock --get 2>/dev/null")
    if ok and out:
        result["rtc_time"] = out.strip()

    ok, out, _ = _run("date '+%Y-%m-%d %H:%M:%S' 2>/dev/null")
    if ok:
        result["system_time"] = out.strip()

    try:
        with open("/etc/systemd/timesyncd.conf") as f:
            for line in f:
                line = line.strip()
                if line.startswith("NTP=") and not line.startswith("#"):
                    val = line.split("=", 1)[1].strip()
                    if val:
                        result["ntp_server"] = val
    except Exception:
        pass

    return result


# Alias für API-Konsistenz
def get_ntp_config():
    return get_time_status()


def set_ntp(server, enabled=True):
    """Konfiguriert NTP-Server und aktiviert/deaktiviert NTP."""
    errors = []

    conf_content = f"[Time]\nNTP={server}\n"
    try:
        with open("/tmp/timesyncd_new.conf", "w") as f:
            f.write(conf_content)
        ok, _, err = _run("sudo cp /tmp/timesyncd_new.conf /etc/systemd/timesyncd.conf")
        if not ok:
            errors.append(f"timesyncd.conf: {err}")
    except Exception as e:
        errors.append(str(e))

    ok, _, err = _run(f"sudo timedatectl set-ntp {'true' if enabled else 'false'}")
    if not ok:
        errors.append(f"timedatectl: {err}")

    if not errors:
        _run("sudo systemctl restart systemd-timesyncd 2>/dev/null")
        if enabled:
            logger.info(f"NTP aktiviert: {server}")

    return not bool(errors), "; ".join(errors) if errors else f"NTP {'aktiviert' if enabled else 'deaktiviert'}: {server}"


def set_manual_time(datetime_str):
    """Setzt Systemzeit manuell. Aktualisiert auch RTC.

    Nutzt 'date -s' statt 'timedatectl set-time', da timedatectl in einer
    Docker-Container-Umgebung (PID 1 ist nicht systemd) generell fehlschlaegt.
    """
    if not re.match(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?$', datetime_str):
        return False, "Ungültiges Datumsformat (erwartet: YYYY-MM-DD HH:MM)"
    # Normalisieren: T -> Leerzeichen
    dt_clean = datetime_str.replace('T', ' ')
    if len(dt_clean) == 16:  # ohne Sekunden
        dt_clean += ':00'
    ok, _, err = _run(f'sudo date -s "{dt_clean}"')
    if ok:
        ok2, _, err2 = _run("sudo hwclock --systohc")
        if ok2:
            logger.info(f"Zeit manuell gesetzt: {dt_clean}, RTC aktualisiert")
            return True, "Zeit gesetzt und RTC aktualisiert"
        logger.warning(f"Zeit gesetzt, aber RTC-Sync fehlgeschlagen: {err2}")
        return True, "Zeit gesetzt (RTC-Sync fehlgeschlagen)"
    return False, err


# ===================================================================
# HOTSPOT BOOT + MONITOR (unverändert)
# ===================================================================

def init_hotspot_on_boot():
    import threading
    cfg = load_network_config()
    if cfg["hotspot"]["enabled"]:
        def _boot_hotspot():
            logger.info("Auto-starting hotspot on boot (waiting 8s)")
            time.sleep(8)
            for attempt in range(3):
                ok, msg = start_hotspot()
                if ok:
                    logger.info(f"Hotspot Boot-Start OK (Versuch {attempt+1})")
                    return
                logger.warning(f"Hotspot Versuch {attempt+1} fehlgeschlagen: {msg}")
                time.sleep(5)
            logger.error("Hotspot konnte nach 3 Versuchen nicht gestartet werden")
        t = threading.Thread(target=_boot_hotspot, daemon=True)
        t.start()


_hotspot_monitor_running = False


def start_hotspot_monitor():
    import threading
    global _hotspot_monitor_running
    if _hotspot_monitor_running:
        return
    _hotspot_monitor_running = True

    def _monitor_loop():
        global _hotspot_monitor_running
        logger.info("Hotspot Health Monitor gestartet")
        consecutive_fails = 0
        while _hotspot_monitor_running:
            time.sleep(30)
            cfg = load_network_config()
            if not cfg["hotspot"]["enabled"]:
                consecutive_fails = 0
                continue
            if not _is_hostapd_running():
                consecutive_fails += 1
                logger.warning(f"hostapd nicht aktiv (Versuch {consecutive_fails})")
                if consecutive_fails <= 5:
                    _run("sudo /usr/sbin/rfkill unblock wifi")
                    time.sleep(1)
                    ok, msg = start_hotspot()
                    if ok:
                        logger.info(f"hostapd Recovery OK: {msg}")
                        consecutive_fails = 0
                    else:
                        logger.error(f"hostapd Recovery fehlgeschlagen: {msg}")
                else:
                    logger.error("hostapd nach 5 Versuchen nicht wiederherstellbar")
                    _hotspot_monitor_running = False
            else:
                if consecutive_fails > 0:
                    logger.info("hostapd laeuft wieder stabil")
                consecutive_fails = 0
            ok, out, _ = _run(f"ip addr show {HOTSPOT_INTERFACE} | grep 'inet '")
            if ok and HOTSPOT_IP not in out:
                logger.warning(f"wlan0 IP fehlt, setze neu: {HOTSPOT_IP}")
                _run(f"sudo ip addr add {HOTSPOT_IP}/24 dev {HOTSPOT_INTERFACE}")

    t = threading.Thread(target=_monitor_loop, daemon=True)
    t.start()


def stop_hotspot_monitor():
    global _hotspot_monitor_running
    _hotspot_monitor_running = False
