#!/usr/bin/env python3
"""Integrate watchdog_manager into DocuPi app.py"""

with open("/home/belimed/docupi/app.py", "r") as f:
    code = f.read()

# 1. Add import for watchdog_manager (after storage_manager import)
if "watchdog_manager" not in code:
    old_import = "from storage_manager import"
    new_import = """from watchdog_manager import start_watchdog_thread, get_status as get_watchdog_status, stop_watchdog_thread
from storage_manager import"""
    code = code.replace(old_import, new_import)

# 2. Add watchdog start in __main__ block
if "start_watchdog_thread" not in code:
    old_main = "start_auto_sync()"
    new_main = """start_auto_sync()

    # Start hardware watchdog (Waveshare RTC Watchdog HAT B)
    try:
        if start_watchdog_thread(timeout=120):
            logger.info("Hardware-Watchdog aktiviert (120s Timeout)")
        else:
            logger.info("Kein Watchdog HAT erkannt - laeuft ohne Hardware-Watchdog")
    except Exception as e:
        logger.warning(f"Watchdog Init-Fehler: {e}")"""
    code = code.replace(old_main, new_main)

# 3. Add watchdog status to /api/system/health response
if "watchdog" not in code or "get_watchdog_status" not in code:
    old_health_return = "    return jsonify(data)"
    # Find the one in api_system_health (there might be multiple return jsonify)
    # Add watchdog data before the return in system health
    idx = code.find("def api_system_health():")
    if idx > 0:
        # Find the return jsonify(data) after api_system_health
        ret_idx = code.find("    return jsonify(data)", idx)
        if ret_idx > 0:
            insert = """
    # --- Watchdog ---
    try:
        data["watchdog"] = get_watchdog_status()
    except:
        data["watchdog"] = {"available": False}

"""
            code = code[:ret_idx] + insert + code[ret_idx:]

# 4. Add /api/watchdog endpoint for control
if "/api/watchdog" not in code:
    reboot_marker = '@app.route("/api/system/reboot", methods=["POST"])'
    watchdog_api = '''
@app.route("/api/watchdog/status")
def api_watchdog_status():
    """Get watchdog status."""
    try:
        return jsonify(get_watchdog_status())
    except Exception as e:
        return jsonify({"available": False, "error": str(e)})

'''
    code = code.replace(reboot_marker, watchdog_api + reboot_marker)

with open("/home/belimed/docupi/app.py", "w") as f:
    f.write(code)

print("OK: watchdog integrated into app.py")
