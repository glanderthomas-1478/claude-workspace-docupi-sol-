#!/usr/bin/env python3
"""Add hotspot health monitoring thread to network_manager.py"""

with open("/home/belimed/docupi/network_manager.py", "r") as f:
    code = f.read()

# Add health monitor after init_hotspot_on_boot
health_monitor = '''

# --- Hotspot Health Monitor ---
_hotspot_monitor_running = False

def start_hotspot_monitor():
    """Background thread that monitors hostapd and restarts if needed."""
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

            # Check if hostapd is running
            if not _is_hostapd_running():
                consecutive_fails += 1
                logger.warning(f"hostapd nicht aktiv (Versuch {consecutive_fails})")
                if consecutive_fails <= 5:
                    # Try to restart
                    logger.info("Starte hostapd neu...")
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

            # Also check wlan0 IP
            ok, out, _ = _run(f"ip addr show {HOTSPOT_INTERFACE} | grep 'inet '")
            if ok and HOTSPOT_IP not in out:
                logger.warning(f"wlan0 IP fehlt, setze neu: {HOTSPOT_IP}")
                _run(f"sudo ip addr add {HOTSPOT_IP}/24 dev {HOTSPOT_INTERFACE}")

    t = threading.Thread(target=_monitor_loop, daemon=True)
    t.start()


def stop_hotspot_monitor():
    global _hotspot_monitor_running
    _hotspot_monitor_running = False

'''

# Insert after init_hotspot_on_boot function
if "start_hotspot_monitor" not in code:
    # Find the end of init_hotspot_on_boot
    idx = code.find("def init_hotspot_on_boot():")
    if idx > 0:
        # Find the next function definition after init_hotspot_on_boot
        next_def = code.find("\ndef ", idx + 10)
        if next_def > 0:
            code = code[:next_def] + health_monitor + code[next_def:]
        else:
            code += health_monitor

    with open("/home/belimed/docupi/network_manager.py", "w") as f:
        f.write(code)
    print("OK: hotspot health monitor added to network_manager.py")
else:
    print("SKIP: health monitor already exists")

# Update app.py to start the monitor
with open("/home/belimed/docupi/app.py", "r") as f:
    app = f.read()

if "start_hotspot_monitor" not in app:
    # Add import
    app = app.replace(
        "    get_lan_status, set_lan_dhcp, set_lan_static, init_hotspot_on_boot)",
        "    get_lan_status, set_lan_dhcp, set_lan_static, init_hotspot_on_boot, start_hotspot_monitor)"
    )
    # Add call after init_hotspot_on_boot
    app = app.replace(
        "    init_hotspot_on_boot()",
        "    init_hotspot_on_boot()\n    start_hotspot_monitor()"
    )
    with open("/home/belimed/docupi/app.py", "w") as f:
        f.write(app)
    print("OK: app.py starts hotspot monitor")
else:
    print("SKIP: app.py already starts monitor")

print("=== DONE ===")
