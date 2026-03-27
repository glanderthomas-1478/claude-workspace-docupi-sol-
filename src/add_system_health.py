#!/usr/bin/env python3
"""Add /api/system/health endpoint to app.py"""

# Read current app.py
with open("/home/belimed/docupi/app.py", "r") as f:
    code = f.read()

# Add the new health endpoint BEFORE the reboot endpoint
health_route = '''
@app.route("/api/system/health")
def api_system_health():
    """Comprehensive system health data for the System tab."""
    import platform
    data = {}

    # --- CPU ---
    try:
        cpu_temp = round(int(open("/sys/class/thermal/thermal_zone0/temp").read().strip()) / 1000, 1)
    except:
        cpu_temp = 0

    try:
        with open("/proc/loadavg") as f:
            parts = f.read().split()
            load_1, load_5, load_15 = float(parts[0]), float(parts[1]), float(parts[2])
    except:
        load_1 = load_5 = load_15 = 0

    try:
        with open("/proc/cpuinfo") as f:
            cpuinfo = f.read()
        cpu_model = ""
        cpu_cores = 0
        for line in cpuinfo.splitlines():
            if line.startswith("model name") and not cpu_model:
                cpu_model = line.split(":")[1].strip()
            if line.startswith("processor"):
                cpu_cores += 1
    except:
        cpu_model = "Unknown"
        cpu_cores = 0

    # CPU usage from /proc/stat snapshot
    try:
        with open("/proc/stat") as f:
            cpu_line = f.readline()
        vals = list(map(int, cpu_line.split()[1:]))
        idle = vals[3]
        total = sum(vals)
        # Store for next call
        if not hasattr(api_system_health, '_prev'):
            api_system_health._prev = (idle, total)
        prev_idle, prev_total = api_system_health._prev
        diff_idle = idle - prev_idle
        diff_total = total - prev_total
        cpu_usage = round((1 - diff_idle / max(diff_total, 1)) * 100, 1) if diff_total > 0 else 0
        api_system_health._prev = (idle, total)
    except:
        cpu_usage = 0

    data["cpu"] = {
        "temp": cpu_temp,
        "temp_status": "ok" if cpu_temp < 60 else "warm" if cpu_temp < 70 else "hot" if cpu_temp < 80 else "critical",
        "model": cpu_model,
        "cores": cpu_cores,
        "usage": cpu_usage,
        "load_1": load_1,
        "load_5": load_5,
        "load_15": load_15
    }

    # --- Memory ---
    try:
        with open("/proc/meminfo") as f:
            mi = {}
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    mi[parts[0].strip()] = int(parts[1].strip().split()[0])
        mem_total = mi.get("MemTotal", 0) / 1024  # MB
        mem_free = mi.get("MemAvailable", mi.get("MemFree", 0)) / 1024
        mem_used = mem_total - mem_free
        swap_total = mi.get("SwapTotal", 0) / 1024
        swap_free = mi.get("SwapFree", 0) / 1024
    except:
        mem_total = mem_used = mem_free = swap_total = swap_free = 0

    data["memory"] = {
        "total_mb": round(mem_total),
        "used_mb": round(mem_used),
        "free_mb": round(mem_free),
        "percent": round(mem_used / max(mem_total, 1) * 100, 1),
        "swap_total_mb": round(swap_total),
        "swap_free_mb": round(swap_free)
    }

    # --- SD Card / Disk ---
    import shutil
    try:
        s = shutil.disk_usage("/")
        sd_total = round(s.total / (1024**3), 1)
        sd_used = round(s.used / (1024**3), 1)
        sd_free = round(s.free / (1024**3), 1)
        sd_percent = round(s.used / s.total * 100, 1)
    except:
        sd_total = sd_used = sd_free = sd_percent = 0

    # SD card health via sector errors
    sd_health = "good"
    sd_errors = 0
    try:
        r = subprocess.run(["dmesg"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            ll = line.lower()
            if "mmcblk0" in ll and ("error" in ll or "i/o" in ll or "failed" in ll):
                sd_errors += 1
        if sd_errors > 10:
            sd_health = "warning"
        if sd_errors > 50:
            sd_health = "critical"
    except:
        pass

    # SD write cycles estimation (lifetime writes)
    sd_lifetime_writes_gb = 0
    try:
        r = subprocess.run(["cat", "/sys/block/mmcblk0/stat"], capture_output=True, text=True, timeout=5)
        parts = r.stdout.split()
        if len(parts) >= 10:
            write_sectors = int(parts[6])
            sd_lifetime_writes_gb = round(write_sectors * 512 / (1024**3), 1)
    except:
        pass

    data["sd_card"] = {
        "total_gb": sd_total,
        "used_gb": sd_used,
        "free_gb": sd_free,
        "percent": sd_percent,
        "health": sd_health,
        "io_errors": sd_errors,
        "lifetime_writes_gb": sd_lifetime_writes_gb
    }

    # --- Uptime ---
    try:
        with open("/proc/uptime") as f:
            uptime_sec = float(f.read().split()[0])
        days = int(uptime_sec // 86400)
        hours = int((uptime_sec % 86400) // 3600)
        minutes = int((uptime_sec % 3600) // 60)
        uptime_str = f"{days}d {hours}h {minutes}m"
    except:
        uptime_sec = 0
        uptime_str = "?"

    data["uptime"] = {
        "seconds": int(uptime_sec),
        "text": uptime_str
    }

    # --- Network ---
    net_info = {}
    try:
        for iface in ["eth0", "wlan0"]:
            r = subprocess.run(["ip", "-j", "addr", "show", iface], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                import json as j
                idata = j.loads(r.stdout)
                if idata:
                    addrs = [a["local"] for a in idata[0].get("addr_info", []) if a.get("family") == "inet"]
                    state = idata[0].get("operstate", "UNKNOWN")
                    net_info[iface] = {"ip": addrs[0] if addrs else "-", "state": state}
    except:
        pass

    # Connected WiFi clients
    wifi_clients = 0
    try:
        r = subprocess.run(["sudo", "iw", "dev", "wlan0", "station", "dump"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            wifi_clients = r.stdout.count("Station ")
    except:
        pass

    data["network"] = {
        "interfaces": net_info,
        "wifi_clients": wifi_clients
    }

    # --- OS Info ---
    data["os"] = {
        "hostname": platform.node(),
        "kernel": platform.release(),
        "arch": platform.machine(),
        "distro": "",
        "python": platform.python_version()
    }
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    data["os"]["distro"] = line.split("=")[1].strip().strip('"')
                    break
    except:
        pass

    # --- DocuPi Service ---
    svc_status = "unknown"
    svc_uptime = ""
    try:
        r = subprocess.run(["systemctl", "is-active", "docupi.service"], capture_output=True, text=True, timeout=5)
        svc_status = r.stdout.strip()
    except:
        pass
    try:
        r = subprocess.run(["systemctl", "show", "docupi.service", "--property=ActiveEnterTimestamp"], capture_output=True, text=True, timeout=5)
        ts = r.stdout.strip().split("=")[1] if "=" in r.stdout else ""
        if ts:
            svc_uptime = ts
    except:
        pass

    serial_status = receiver.get_status()

    data["service"] = {
        "status": svc_status,
        "started": svc_uptime,
        "serial": serial_status,
        "today_count": get_today_count(),
        "total_count": get_protocol_count()
    }

    return jsonify(data)

'''

# Insert before the reboot route
marker = '@app.route("/api/system/reboot", methods=["POST"])'
if marker in code:
    code = code.replace(marker, health_route + marker)
    with open("/home/belimed/docupi/app.py", "w") as f:
        f.write(code)
    print("OK: /api/system/health added")
else:
    print("ERROR: marker not found")
