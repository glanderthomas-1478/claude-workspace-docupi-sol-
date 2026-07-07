import os, sys, logging, shutil, subprocess, signal, atexit, time as _time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, redirect, make_response, url_for, Response, session
from flask_socketio import SocketIO
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Machine identity kommt aus config.json (machine.name / machine.protocol)

from config import load_config, save_config
from database import (get_protocols, get_protocol_count, get_today_count, get_system_logs, log_event, get_db,
    get_pending_protocols, get_pending_protocol, save_form_draft, confirm_form, discard_pending,
    set_pdf_failed, get_form_confirmed_protocols)
from serial_receiver import SerialReceiver
from network_manager import (load_network_config, save_network_config,
    start_hotspot, stop_hotspot, update_hotspot_config, get_hotspot_status,
    get_lan_status, set_lan_dhcp, set_lan_static, init_hotspot_on_boot, start_hotspot_monitor,
    get_available_interfaces, get_interface_status, set_interface_static, set_interface_dhcp,
    get_hostname, set_hostname, get_ntp_config, set_ntp, set_manual_time)
from print_manager import (
    get_printers, print_pdf, test_print as printer_test_print,
    get_print_queue, cancel_job, get_status as get_printer_status,
    load_print_config, save_print_config, auto_print_pdf, is_cups_available,
    setup_usb_printer, is_usb_printer_present, setup_network_printer
)
from watchdog_manager import start_watchdog_thread, get_status as get_watchdog_status, stop_watchdog_thread
from tcp_print_capture import (start_capture_server, get_capture_status, load_capture_config, save_capture_config,
    set_pending_charge_callback, _finalize_charge_pdf)
from health_check import run_health_check, backup_config_on_save
from storage_manager import (
    get_usb_info, mount_usb, unmount_usb, format_usb_fat32,
    list_files, get_storage_stats, sync_pdfs_to_usb,
    load_sync_config, save_sync_config, start_auto_sync,
    delete_file, delete_directory, copy_file,
    try_mount_usb_on_boot, dongle_present,
    SD_PDF_DIR, USB_MOUNT_POINT, USB_PDF_SUBDIR, USB_CAPTURE_SUBDIR)
from network_storage_manager import (
    load_network_config, save_network_config, get_network_storage_status,
    test_network_connection, sync_pdfs_to_network, sync_captures_to_network,
    start_network_sync)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler("/home/docucontrol/docupi/logs/docupi.log"), logging.StreamHandler()])
logger = logging.getLogger("docupi.app")

# --- Boot Health Check ---
run_health_check()


def _load_or_create_auth_secrets():
    """Flask-SECRET_KEY und Service-Passwort werden NICHT im Quellcode
    hinterlegt, sondern beim ersten Start generiert/persistiert (analog zu
    network_share.cred). Datei liegt ausserhalb des Git-Repos, chmod 600."""
    import json as _json_secrets
    import secrets as _secrets_mod
    secrets_file = "/home/docucontrol/docupi/data/auth_secrets.json"
    if os.path.exists(secrets_file):
        try:
            with open(secrets_file) as f:
                d = _json_secrets.load(f)
            if d.get("secret_key") and d.get("service_password"):
                return d["secret_key"], d["service_password"]
        except Exception:
            pass
    key = _secrets_mod.token_hex(32)
    pw = "Xtend1478"  # Anfangswert - danach in data/auth_secrets.json aenderbar
    os.makedirs(os.path.dirname(secrets_file), exist_ok=True)
    with open(secrets_file, "w") as f:
        _json_secrets.dump({"secret_key": key, "service_password": pw}, f)
    os.chmod(secrets_file, 0o600)
    return key, pw


def _ensure_self_signed_cert():
    """Erzeugt beim ersten Start ein selbstsigniertes TLS-Zertifikat fuer den
    parallelen HTTPS-Listener (Port 5443). Liegt ausserhalb des Git-Repos in
    data/tls/, analog zu auth_secrets.json. Laeuft ZUSAETZLICH zu Port 5000
    (HTTP), damit der bestehende Kiosk (http://localhost:5000) unveraendert
    weiterlaeuft und nicht durch Zertifikatswarnungen gestoert wird."""
    tls_dir = "/home/docucontrol/docupi/data/tls"
    cert_file = os.path.join(tls_dir, "cert.pem")
    key_file = os.path.join(tls_dir, "key.pem")
    if os.path.exists(cert_file) and os.path.exists(key_file):
        return cert_file, key_file
    os.makedirs(tls_dir, exist_ok=True)
    import subprocess as _subprocess_tls
    try:
        _subprocess_tls.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", key_file, "-out", cert_file, "-days", "3650",
            "-subj", "/CN=docucontrol.local",
        ], check=True, capture_output=True)
        os.chmod(key_file, 0o600)
        return cert_file, key_file
    except Exception as e:
        logger.warning(f"TLS-Zertifikat konnte nicht erzeugt werden: {e}")
        return None, None


app = Flask(__name__)
app.config["SECRET_KEY"], SERVICE_PASSWORD = _load_or_create_auth_secrets()
# CSRF-Haertung: Session-Cookie wird nicht bei Cross-Site-Requests mitgesendet
# (kein HTTPS hier, daher SESSION_COOKIE_SECURE bewusst nicht gesetzt - sonst
# wuerde der Browser das Cookie ueber http:// gar nicht mehr senden).
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# Kein "*" mehr: ohne explizite cors_allowed_origins erlaubt Flask-SocketIO
# nur Same-Origin-Verbindungen (das Web-UI laeuft immer auf demselben Host/Port
# wie die Socket.IO-Verbindung) - kein geraetespezifischer IP-Allowlist-Pflegeaufwand noetig.
socketio = SocketIO(app, async_mode="threading")
receiver = SerialReceiver(socketio=socketio)

# --- Service-Anmeldung (Einstellungen-Sperre) ---
SERVICE_SESSION_TIMEOUT_S = 300
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_S = 300
_login_failures = []  # Liste von Timestamps fehlgeschlagener Versuche (in-memory)


def _login_locked_out():
    now = _time.time()
    while _login_failures and (now - _login_failures[0]) > LOGIN_LOCKOUT_S:
        _login_failures.pop(0)
    return len(_login_failures) >= LOGIN_MAX_ATTEMPTS


def _service_logged_in():
    # Der Service-Dongle allein schaltet den Service-Modus frei - kein
    # Passwort-Login noetig, solange er physisch steckt.
    if dongle_present():
        return True
    if session.get("role") != "service":
        return False
    if (_time.time() - session.get("last_seen", 0)) > SERVICE_SESSION_TIMEOUT_S:
        session.pop("role", None)
        session.pop("last_seen", None)
        return False
    return True


def _require_service():
    if not _service_logged_in():
        return jsonify({"ok": False, "success": False, "message": "Service-Anmeldung erforderlich"}), 403
    if not dongle_present():
        return jsonify({"ok": False, "success": False, "message": "Service-Dongle erforderlich"}), 403
    return None


@app.route("/api/auth/status")
def api_auth_status():
    if _service_logged_in():
        remaining = max(0, SERVICE_SESSION_TIMEOUT_S - (_time.time() - session.get("last_seen", 0)))
        return jsonify({"role": "service", "remaining_seconds": int(remaining), "dongle": dongle_present()})
    return jsonify({"role": "user", "remaining_seconds": 0, "dongle": dongle_present()})


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    if _login_locked_out():
        wait_s = int(LOGIN_LOCKOUT_S - (_time.time() - _login_failures[0]))
        log_event("WARN", f"Service-Anmeldung gesperrt (zu viele Fehlversuche, noch {wait_s}s)")
        return jsonify({"ok": False, "message": f"Zu viele Fehlversuche. Bitte {wait_s}s warten."}), 429
    d = request.get_json(silent=True) or {}
    pw = (d.get("password") or "").strip()
    # Optionales zweites Testpasswort - nur fuer Testzwecke, wird ueber ein
    # zusaetzliches Feld in auth_secrets.json gesetzt/entfernt, kein Redeploy
    # noetig zum Entfernen (Feld einfach wieder loeschen).
    test_pw = None
    try:
        import json as _json_test
        with open("/home/docucontrol/docupi/data/auth_secrets.json") as f:
            test_pw = _json_test.load(f).get("service_password_test")
    except Exception:
        pass
    if pw == SERVICE_PASSWORD or (test_pw and pw == test_pw):
        _login_failures.clear()
        session["role"] = "service"
        session["last_seen"] = _time.time()
        log_event("INFO", "Service-Anmeldung erfolgreich")
        return jsonify({"ok": True, "role": "service", "remaining_seconds": SERVICE_SESSION_TIMEOUT_S,
                         "dongle": dongle_present()})
    _login_failures.append(_time.time())
    log_event("WARN", "Service-Anmeldung fehlgeschlagen (falsches Passwort)")
    return jsonify({"ok": False, "message": "Falsches Passwort"}), 401


@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    session.pop("role", None)
    session.pop("last_seen", None)
    return jsonify({"ok": True})


@app.route("/api/auth/touch", methods=["POST"])
def api_auth_touch():
    if _service_logged_in():
        session["last_seen"] = _time.time()
        return jsonify({"ok": True, "remaining_seconds": SERVICE_SESSION_TIMEOUT_S, "dongle": dongle_present()})
    return jsonify({"ok": False}), 401


def _on_pending_charge(protocol_id, metadata):
    """Callback aus tcp_print_capture._process_job (Daemon-Thread)."""
    try:
        socketio.emit('new_pending_charge', metadata)
    except Exception as e:
        logger.warning("SocketIO emit new_pending_charge fehlgeschlagen: %s", e)

set_pending_charge_callback(_on_pending_charge)

@app.after_request
def add_no_cache_headers(response):
    is_page = request.path in ('/', '/settings', '/files') and 'text/html' in response.content_type
    is_api = request.path.startswith('/api/')
    if is_page or is_api:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
    return response


@app.route("/")
def dashboard():
    config = load_config(); status = receiver.get_status()
    try:
        cpu_temp = round(int(open("/sys/class/thermal/thermal_zone0/temp").read().strip()) / 1000, 1)
    except: cpu_temp = 0
    try:
        mem = {}
        for line in open("/proc/meminfo"):
            parts = line.split()
            if parts[0] in ("MemTotal:", "MemAvailable:"): mem[parts[0].rstrip(":")] = int(parts[1])
        mem_total = mem.get("MemTotal", 0) // 1024; mem_available = mem.get("MemAvailable", 0) // 1024
        mem_used = mem_total - mem_available; mem_percent = round(mem_used / mem_total * 100) if mem_total else 0
    except: mem_total = mem_used = mem_percent = 0
    usb_info = get_usb_info()
    usb_mounted = usb_info.get("mounted", False)
    usb_total = usb_info.get("total_gb", 0)
    usb_free = usb_info.get("free_gb", 0)
    usb_percent = usb_info.get("used_percent", 0)
    try:
        sec = float(open("/proc/uptime").read().split()[0])
        uptime = f"{int(sec//86400)}d {int(sec%86400//3600)}h {int(sec%3600//60)}m"
    except: uptime = "?"
    return render_template("dashboard.html", config=config, status=status, cpu_temp=cpu_temp,
        mem_total=mem_total, mem_used=mem_used, mem_percent=mem_percent, usb_mounted=usb_mounted,
        usb_total=usb_total, usb_free=usb_free, usb_percent=usb_percent, uptime=uptime,
        today_count=get_today_count(), total_count=get_protocol_count())

@app.route("/monitor")
def monitor():
    return render_template("monitor.html", config=load_config(), status=receiver.get_status())

@app.route("/archive")
def archive():
    page = request.args.get("page", 1, type=int); date_filter = request.args.get("date", "")
    per_page = 25; offset = (page-1)*per_page
    protocols = get_protocols(limit=per_page, offset=offset, date_filter=date_filter)
    total = get_protocol_count(date_filter if date_filter else None)
    return render_template("archive.html", protocols=protocols, page=page,
        total_pages=max(1,(total+per_page-1)//per_page), total=total, date_filter=date_filter)

@app.route("/download/<int:pid>")
def download_pdf(pid):
    conn = get_db(); row = conn.execute("SELECT * FROM protocols WHERE id=?", (pid,)).fetchone(); conn.close()
    if row and row["pdf_path"] and os.path.exists(row["pdf_path"]):
        return send_file(row["pdf_path"], as_attachment=True, download_name=row["pdf_filename"])
    return "PDF nicht gefunden", 404

@app.route("/view/<int:pid>")
def view_pdf(pid):
    conn = get_db(); row = conn.execute("SELECT * FROM protocols WHERE id=?", (pid,)).fetchone(); conn.close()
    if row and row["pdf_path"] and os.path.exists(row["pdf_path"]):
        return send_file(row["pdf_path"], mimetype="application/pdf")
    return "PDF nicht gefunden", 404

@app.route("/settings", methods=["GET", "POST"])
def settings():
    config = load_config()
    if request.method == "POST":
        config["serial"]["port"] = request.form.get("serial_port", "/dev/ttyUSB0")
        config["serial"]["baudrate"] = int(request.form.get("baudrate", 9600))
        config["serial"]["bytesize"] = int(request.form.get("bytesize", 8))
        config["serial"]["parity"] = request.form.get("parity", "N")
        config["serial"]["stopbits"] = int(request.form.get("stopbits", 1))
        config["protocol"]["delimiter"] = request.form.get("delimiter", "formfeed")
        config["protocol"]["timeout_seconds"] = int(request.form.get("timeout_seconds", 10))
        config["protocol"]["custom_delimiter"] = request.form.get("custom_delimiter", "")
        config["pdf"]["kundenname"] = request.form.get("kundenname", "")
        config["pdf"]["abteilung"] = request.form.get("abteilung", "")
        config["pdf"]["maschinen_typ"] = request.form.get("maschinen_typ", "")
        config["pdf"]["maschinen_nr"] = request.form.get("maschinen_nr", "")
        config["pdf"]["device_alias"] = request.form.get("device_alias", "")
        config["pdf"]["device_name"] = request.form.get("maschinen_typ", "")
        config["pdf"]["header_text"] = request.form.get("kundenname", "")
        config["pdf"]["handwritten_fields"] = request.form.get("handwritten_fields") == "true"
        config["pdf"]["notfall_rows"] = int(request.form.get("notfall_rows", 18))
        config["pdf"]["font_size"] = int(request.form.get("font_size", 8))
        config["pdf"]["folder_structure"] = request.form.get("folder_structure", "date")
        config["pdf"]["filename_pattern"] = request.form.get("filename_pattern", "{datum}_{zeit}_{geraet}_{charge}")
        config["pdf"]["filename_separator"] = request.form.get("filename_separator", "_")
        config["pdf"]["font_size"] = int(request.form.get("font_size", 8))
        config["pdf"]["folder_structure"] = request.form.get("folder_structure", "date")
        save_config(config); log_event("INFO", "Konfiguration gespeichert"); receiver.restart()
        return redirect(url_for("settings", saved=1))
    serial_ports = [p for p in ["/dev/ttyUSB0","/dev/ttyUSB1","/dev/ttyUSB2","/dev/ttyACM0","/dev/ttyAMA10"] if os.path.exists(p)]
    return render_template("settings.html", config=config, serial_ports=serial_ports, saved=request.args.get("saved",0,type=int),
        status=receiver.get_status(), hotspot=get_hotspot_status(), lan=get_lan_status())

@app.route("/system")
def system():
    return render_template("system.html", logs=get_system_logs(200))

# ---------------------------------------------------------------
# Serial Log Viewer
# ---------------------------------------------------------------
@app.route("/serial-logs")
def serial_logs():
    log_files = receiver.serial_logger.get_log_files()
    selected_date = request.args.get("date", "")
    content = None
    if selected_date:
        tail = request.args.get("lines", 500, type=int)
        content = receiver.serial_logger.get_log_content(selected_date, tail_lines=tail)
    return render_template("serial_logs.html", status=receiver.get_status(), log_files=log_files,
        selected_date=selected_date, content=content)

@app.route("/serial-logs/download/<date_str>")
def download_serial_log(date_str):
    import re
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return "Ungueltig", 400
    path = os.path.join("/home/docucontrol/docupi/serial_logs", f"serial_{date_str}.log")
    if os.path.isfile(path):
        return send_file(path, as_attachment=True, download_name=f"serial_{date_str}.log")
    return "Log nicht gefunden", 404

@app.route("/api/serial-logs")
def api_serial_logs():
    return jsonify({"logs": receiver.serial_logger.get_log_files()})

@app.route("/api/serial-logs/<date_str>")
def api_serial_log_content(date_str):
    tail = request.args.get("lines", 200, type=int)
    content = receiver.serial_logger.get_log_content(date_str, tail_lines=tail)
    if content is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"date": date_str, "content": content, "lines": content.count("\n")})

# ---------------------------------------------------------------
# Network Management
# ---------------------------------------------------------------
@app.route("/network")
def network():
    return render_template("network.html", status=receiver.get_status(),
        hotspot=get_hotspot_status(), lan=get_lan_status())

@app.route("/api/network/hotspot/start", methods=["POST"])
def api_hotspot_start():
    ok, msg = start_hotspot()
    log_event("INFO" if ok else "ERROR", f"Hotspot Start: {msg}")
    return jsonify({"success": ok, "message": msg})

@app.route("/api/network/hotspot/stop", methods=["POST"])
def api_hotspot_stop():
    ok, msg = stop_hotspot()
    log_event("INFO" if ok else "ERROR", f"Hotspot Stop: {msg}")
    return jsonify({"success": ok, "message": msg})

@app.route("/api/network/hotspot/config", methods=["POST"])
def api_hotspot_config():
    guard = _require_service()
    if guard: return guard
    data = request.get_json()
    ok, msg = update_hotspot_config(
        ssid=data.get("ssid"), password=data.get("password"),
        hidden=data.get("hidden"), channel=data.get("channel"))
    log_event("INFO", f"Hotspot Config: {msg}")
    return jsonify({"success": ok, "message": msg})

@app.route("/api/network/hotspot/status")
def api_hotspot_status():
    return jsonify(get_hotspot_status())

@app.route("/api/network/lan/dhcp", methods=["POST"])
def api_lan_dhcp():
    ok, msg = set_lan_dhcp()
    log_event("INFO" if ok else "ERROR", f"LAN DHCP: {msg}")
    return jsonify({"success": ok, "message": msg})

@app.route("/api/network/lan/static", methods=["POST"])
def api_lan_static():
    data = request.get_json(silent=True) or {}
    ok, msg = set_interface_static(
        "eth0",
        ip=data.get("ip", ""), netmask=data.get("netmask", "24"),
        gateway=data.get("gateway", ""), dns=data.get("dns", ""),
        dns2=data.get("dns2", ""), vlan=int(data.get("vlan", 0)))
    log_event("INFO" if ok else "ERROR", f"LAN Static: {msg}")
    return jsonify({"success": ok, "message": msg}), (200 if ok else 500)

@app.route("/api/network/lan/status")
def api_lan_status():
    return jsonify(get_lan_status())

# ---------------------------------------------------------------
# Multi-Interface / Klinik-IT Netzwerk

@app.route("/api/network/interfaces")
def api_network_interfaces():
    ifaces = get_available_interfaces()
    return jsonify([get_interface_status(i) for i in ifaces])

@app.route("/api/network/iface/<dev>/status")
def api_iface_status(dev):
    return jsonify(get_interface_status(dev))

@app.route("/api/network/iface/<dev>/static", methods=["POST"])
def api_iface_static(dev):
    guard = _require_service()
    if guard: return guard
    d = request.get_json(silent=True) or {}
    ip = d.get("ip", "").strip()
    if not ip:
        return jsonify({"success": False, "message": "IP fehlt"}), 400
    ok, msg = set_interface_static(
        dev, ip,
        netmask=str(d.get("netmask", "24")).strip(),
        gateway=d.get("gateway", "").strip(),
        dns=d.get("dns", "").strip(),
        dns2=d.get("dns2", "").strip(),
        vlan=int(d.get("vlan", 0)))
    log_event("INFO" if ok else "ERROR", f"Iface {dev} static: {msg}")
    return jsonify({"success": ok, "message": msg}), (200 if ok else 500)

@app.route("/api/network/iface/<dev>/dhcp", methods=["POST"])
def api_iface_dhcp(dev):
    guard = _require_service()
    if guard: return guard
    ok, msg = set_interface_dhcp(dev)
    log_event("INFO" if ok else "ERROR", f"Iface {dev} DHCP: {msg}")
    return jsonify({"success": ok, "message": msg}), (200 if ok else 500)

@app.route("/api/system/hostname")
def api_hostname_get():
    return jsonify({"hostname": get_hostname()})

@app.route("/api/system/hostname", methods=["POST"])
def api_hostname_set():
    guard = _require_service()
    if guard: return guard
    d = request.get_json(silent=True) or {}
    name = d.get("hostname", "").strip()
    ok, msg = set_hostname(name)
    log_event("INFO" if ok else "ERROR", f"Hostname: {msg}")
    return jsonify({"success": ok, "message": msg}), (200 if ok else 400)

@app.route("/api/system/ntp")
def api_ntp_get():
    return jsonify(get_ntp_config())

@app.route("/api/system/ntp", methods=["POST"])
def api_ntp_set():
    d = request.get_json(silent=True) or {}
    server = d.get("server", "pool.ntp.org").strip()
    enabled = bool(d.get("enabled", True))
    ok, msg = set_ntp(server, enabled)
    log_event("INFO" if ok else "ERROR", f"NTP: {msg}")
    return jsonify({"success": ok, "message": msg}), (200 if ok else 500)

@app.route("/api/system/time/manual", methods=["POST"])
def api_time_manual():
    d = request.get_json(silent=True) or {}
    t = d.get("datetime", "").strip()
    ok, msg = set_manual_time(t)
    log_event("INFO" if ok else "ERROR", f"Zeit manuell: {msg}")
    return jsonify({"success": ok, "message": msg}), (200 if ok else 400)

# ---------------------------------------------------------------
# File Manager & Storage
# ---------------------------------------------------------------
@app.route("/files")
def filemanager():
    return render_template("filemanager.html", status=receiver.get_status())


@app.route("/api/storage/pdfs/<pane>")
def api_storage_pdfs(pane):
    import os as _os
    from datetime import datetime as _dt
    if pane == "usb":
        from storage_manager import get_usb_info, USB_PDF_SUBDIR
        usb = get_usb_info()
        if not usb.get("mounted"):
            return jsonify({"files": [], "error": "USB nicht gemountet"})
        base = _os.path.join(usb["mount_point"], USB_PDF_SUBDIR)
    elif pane == "sd":
        from storage_manager import SD_PDF_DIR
        base = SD_PDF_DIR
    else:
        return jsonify({"files": [], "error": "Unbekannt"})
    files = []
    if _os.path.isdir(base):
        for root, dirs, fnames in _os.walk(base):
            dirs.sort()
            for fname in sorted(fnames):
                if not fname.lower().endswith(".pdf"):
                    continue
                fp = _os.path.join(root, fname)
                try:
                    stat = _os.stat(fp)
                    rel = _os.path.relpath(fp, base)
                    sz = stat.st_size
                    if sz >= 1048576:
                        sh = str(round(sz/1048576, 1)) + " MB"
                    else:
                        sh = str(round(sz/1024, 1)) + " KB"
                    files.append({
                        "name": fname,
                        "path": rel,
                        "size": sz,
                        "size_human": sh,
                        "modified": _dt.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M"),
                        "ext": ".pdf"
                    })
                except Exception:
                    pass
    return jsonify({"files": files})

@app.route("/api/storage/stats")
def api_storage_stats():
    return jsonify(get_storage_stats())

@app.route("/api/storage/browse/<pane>")
def api_storage_browse(pane):
    path = request.args.get("path", "")
    if pane == "sd":
        return jsonify(list_files(SD_PDF_DIR, path))
    elif pane == "usb":
        usb = get_usb_info()
        if not usb.get("mounted"):
            return jsonify({"error": "USB nicht gemountet", "files": [], "dirs": []})
        base = os.path.join(usb["mount_point"], USB_PDF_SUBDIR)
        if not os.path.isdir(base):
            os.makedirs(base, exist_ok=True)
        return jsonify(list_files(base, path))
    return jsonify({"error": "Unbekannter Bereich"}), 400

@app.route("/api/storage/file/<pane>")
def api_storage_file(pane):
    path = request.args.get("path", "")
    download = request.args.get("download", "0") == "1"
    if not path:
        return "Kein Pfad", 400

    if pane == "sd":
        base = SD_PDF_DIR
    elif pane == "usb":
        usb = get_usb_info()
        if not usb.get("mounted"):
            return "USB nicht gemountet", 404
        base = os.path.join(usb["mount_point"], USB_PDF_SUBDIR)
    elif pane == "usb_captures":
        usb = get_usb_info()
        if not usb.get("mounted"):
            return "USB nicht gemountet", 404
        base = os.path.join(usb["mount_point"], USB_CAPTURE_SUBDIR)
    else:
        return "Unbekannt", 400

    full = os.path.join(base, path)
    real_base = os.path.realpath(base)
    real_path = os.path.realpath(full)
    if not real_path.startswith(real_base) or not os.path.isfile(real_path):
        return "Nicht gefunden", 404

    if download:
        return send_file(real_path, as_attachment=True, download_name=os.path.basename(path))
    else:
        mime = "application/pdf" if path.lower().endswith(".pdf") else "application/octet-stream"
        return send_file(real_path, mimetype=mime)

@app.route("/api/storage/usb/mount", methods=["POST"])
def api_usb_mount():
    ok, msg = mount_usb()
    log_event("INFO" if ok else "ERROR", f"USB Mount: {msg}")
    return jsonify({"success": ok, "message": msg})

@app.route("/api/storage/usb/eject", methods=["POST"])
def api_usb_eject():
    ok, msg = unmount_usb()
    log_event("INFO" if ok else "ERROR", f"USB Eject: {msg}")
    return jsonify({"success": ok, "message": msg})

@app.route("/api/storage/usb/format", methods=["POST"])
def api_usb_format():
    data = request.get_json(silent=True) or {}
    label = data.get("label", "DOCUCTRL")
    ok, msg = format_usb_fat32(label)
    log_event("WARN" if ok else "ERROR", f"USB Format: {msg}")
    return jsonify({"success": ok, "message": msg})

@app.route("/api/storage/sync/config", methods=["GET", "POST"])
def api_sync_config():
    if request.method == "POST":
        data = request.get_json()
        config = load_sync_config()
        if "auto_sync_enabled" in data:
            config["auto_sync_enabled"] = bool(data["auto_sync_enabled"])
        if "sync_days" in data:
            config["sync_days"] = int(data["sync_days"])
        if "sync_interval_minutes" in data:
            config["sync_interval_minutes"] = int(data["sync_interval_minutes"])
        save_sync_config(config)
        return jsonify({"success": True, "message": "Sync-Konfiguration gespeichert"})
    return jsonify(load_sync_config())

@app.route("/api/storage/sync/now", methods=["POST"])
def api_sync_now():
    ok, msg, count = sync_pdfs_to_usb()
    log_event("INFO" if ok else "ERROR", f"Manual Sync: {msg}")
    return jsonify({"success": ok, "message": msg, "count": count})

@app.route("/api/storage/network/config", methods=["GET", "POST"])
def api_network_storage_config():
    if request.method == "POST":
        guard = _require_service()
        if guard: return guard
        data = request.get_json(silent=True) or {}
        cfg = load_network_config()
        if "enabled" in data:
            cfg["enabled"] = bool(data["enabled"])
        for key in ("server", "share", "username", "domain"):
            if key in data:
                cfg[key] = str(data[key]).strip()
        if data.get("password"):
            cfg["password"] = data["password"]
        for key in ("sync_days", "sync_interval_minutes"):
            if key in data:
                cfg[key] = int(data[key])
        save_network_config(cfg)
        log_event("INFO", "Netzwerk-Speicherort-Konfiguration gespeichert")
        return jsonify({"success": True, "message": "Gespeichert"})

    cfg = dict(load_network_config())
    cfg["has_password"] = bool(cfg.pop("password", ""))
    return jsonify(cfg)

@app.route("/api/storage/network/status")
def api_network_storage_status():
    return jsonify(get_network_storage_status())

@app.route("/api/storage/network/test", methods=["POST"])
def api_network_storage_test():
    data = request.get_json(silent=True) or {}
    cfg = load_network_config()
    server = data.get("server", cfg["server"])
    share = data.get("share", cfg["share"])
    username = data.get("username", cfg["username"])
    password = data.get("password") or cfg["password"]
    domain = data.get("domain", cfg["domain"])
    ok, msg = test_network_connection(server, share, username, password, domain)
    log_event("INFO" if ok else "WARN", f"Netzwerk-Speicherort Test: {msg}")
    return jsonify({"success": ok, "message": msg})

@app.route("/api/storage/network/sync", methods=["POST"])
def api_network_storage_sync():
    ok1, msg1, n1 = sync_pdfs_to_network()
    ok2, msg2, n2 = sync_captures_to_network()
    ok = ok1 and ok2
    log_event("INFO" if ok else "ERROR", f"Netzwerk-Sync: {msg1} / {msg2}")
    return jsonify({"success": ok, "message": f"{msg1}; {msg2}", "count": n1 + n2})

@app.route("/api/storage/copy", methods=["POST"])
def api_storage_copy():
    data = request.get_json()
    from_pane = data.get("from")
    to_pane = data.get("to")
    path = data.get("path", "")
    to_path = data.get("to_path", "")

    usb = get_usb_info()
    usb_base = os.path.join(usb.get("mount_point", USB_MOUNT_POINT), USB_PDF_SUBDIR) if usb.get("mounted") else None

    if from_pane == "sd":
        src_base = SD_PDF_DIR
    elif from_pane == "usb" and usb_base:
        src_base = usb_base
    else:
        return jsonify({"success": False, "message": "Quell-Speicher nicht verfuegbar"})

    if to_pane == "sd":
        dst_base = SD_PDF_DIR
    elif to_pane == "usb" and usb_base:
        dst_base = usb_base
    else:
        return jsonify({"success": False, "message": "Ziel-Speicher nicht verfuegbar"})

    # Determine destination path
    dst_rel = os.path.join(to_path, os.path.basename(path)) if to_path else os.path.basename(path)
    src_full = os.path.join(src_base, path)

    if os.path.isdir(os.path.realpath(src_full)):
        # Copy directory recursively
        dst_full = os.path.join(dst_base, dst_rel)
        try:
            if os.path.exists(dst_full):
                return jsonify({"success": False, "message": "Ziel existiert bereits"})
            shutil.copytree(src_full, dst_full)
            return jsonify({"success": True, "message": f"Verzeichnis kopiert"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)})
    else:
        ok, msg = copy_file(src_base, path, dst_base, dst_rel)
        return jsonify({"success": ok, "message": msg})

@app.route("/api/storage/delete", methods=["POST"])
def api_storage_delete():
    guard = _require_service()
    if guard: return guard
    data = request.get_json()
    pane = data.get("pane")
    path = data.get("path", "")

    usb = get_usb_info()

    if pane == "sd":
        base = SD_PDF_DIR
    elif pane == "usb":
        if not usb.get("mounted"):
            return jsonify({"success": False, "message": "USB nicht gemountet"})
        base = os.path.join(usb["mount_point"], USB_PDF_SUBDIR)
    elif pane == "usb_captures":
        if not usb.get("mounted"):
            return jsonify({"success": False, "message": "USB nicht gemountet"})
        from storage_manager import USB_CAPTURE_SUBDIR as _USB_CAP_SUBDIR
        base = os.path.join(usb["mount_point"], _USB_CAP_SUBDIR)
    else:
        return jsonify({"success": False, "message": "Unbekannt"})

    full = os.path.join(base, path)
    if os.path.isdir(os.path.realpath(full)):
        ok, msg = delete_directory(base, path)
    else:
        ok, msg = delete_file(base, path)
    if ok:
        log_event("INFO", f"Geloescht: {pane}:/{path}")
    return jsonify({"success": ok, "message": msg})

# ---------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------
@app.route("/api/status")
def api_status():
    config = load_config()
    try: cpu_temp = round(int(open("/sys/class/thermal/thermal_zone0/temp").read().strip())/1000, 1)
    except: cpu_temp = 0
    return jsonify({"serial": receiver.get_status(), "today_count": get_today_count(),
        "total_count": get_protocol_count(), "cpu_temp": cpu_temp,
        "usb_mounted": os.path.ismount(config["pdf"]["output_dir"])})

@app.route("/api/receiver/start", methods=["POST"])
def api_start(): receiver.start(); return jsonify({"status": "started"})
@app.route("/api/receiver/stop", methods=["POST"])
def api_stop(): receiver.stop(); return jsonify({"status": "stopped"})
@app.route("/api/receiver/restart", methods=["POST"])
def api_restart(): receiver.restart(); return jsonify({"status": "restarted"})

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
        cpu_model = open("/proc/device-tree/model").read().strip().rstrip(chr(0)) if os.path.exists("/proc/device-tree/model") else "Unknown"
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

    if not cpu_model and os.path.exists("/proc/device-tree/model"):
        try: cpu_model = open("/proc/device-tree/model").read().strip().rstrip(chr(0))
        except: pass

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

    # --- DocuControl Service ---
    svc_status = "unknown"
    svc_uptime = ""
    try:
        r = subprocess.run(["systemctl", "is-active", "docucontrol.service"], capture_output=True, text=True, timeout=5)
        svc_status = r.stdout.strip()
    except:
        pass
    try:
        r = subprocess.run(["systemctl", "show", "docucontrol.service", "--property=ActiveEnterTimestamp"], capture_output=True, text=True, timeout=5)
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

    # Watchdog
    try:
        data["watchdog"] = get_watchdog_status()
    except:
        data["watchdog"] = {"available": False}

    return jsonify(data)


@app.route("/api/logs/serial")
def api_logs_serial():
    """Get serial communication logs."""
    lines = request.args.get("lines", 100, type=int)
    log_file = "/home/docucontrol/docupi/data/serial.log"
    try:
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                all_lines = f.readlines()
            return jsonify({"logs": "".join(all_lines[-lines:])})
        else:
            # Fallback: app log
            log_file2 = "/home/docucontrol/docupi/data/docupi.log"
            if os.path.exists(log_file2):
                with open(log_file2, "r") as f:
                    all_lines = f.readlines()
                serial_lines = [l for l in all_lines if "serial" in l.lower() or "receiver" in l.lower() or "protocol" in l.lower() or "pdf" in l.lower()]
                return jsonify({"logs": "".join(serial_lines[-lines:]) or "Keine seriellen Logs gefunden"})
            return jsonify({"logs": "Keine Log-Datei gefunden"})
    except Exception as e:
        return jsonify({"logs": f"Fehler: {e}"})


@app.route("/api/logs/service")
def api_logs_service():
    """Get DocuControl service logs from journalctl."""
    lines = request.args.get("lines", 80, type=int)
    try:
        r = subprocess.run(
            ["journalctl", "-u", "docucontrol.service", "--no-pager", "-n", str(lines)],
            capture_output=True, text=True, timeout=10
        )
        return jsonify({"logs": r.stdout or "Keine Logs"})
    except Exception as e:
        return jsonify({"logs": f"Fehler: {e}"})


@app.route("/api/logs/kernel")
def api_logs_kernel():
    """Get kernel/dmesg logs with optional filter."""
    lines = request.args.get("lines", 80, type=int)
    filt = request.args.get("filter", "all")
    try:
        r = subprocess.run(["dmesg", "--time-format=reltime"], capture_output=True, text=True, timeout=10)
        all_lines = r.stdout.splitlines()
        if filt == "usb":
            all_lines = [l for l in all_lines if "usb" in l.lower() or "sda" in l.lower()]
        elif filt == "mmc":
            all_lines = [l for l in all_lines if "mmc" in l.lower() or "mmcblk" in l.lower()]
        elif filt == "net":
            all_lines = [l for l in all_lines if any(k in l.lower() for k in ["eth0", "wlan", "wifi", "net", "link", "dhcp", "ip"])]
        elif filt == "error":
            all_lines = [l for l in all_lines if any(k in l.lower() for k in ["error", "fail", "warn", "critical", "timeout"])]
        return jsonify({"logs": "\n".join(all_lines[-lines:]) or "Keine passenden Logs"})
    except Exception as e:
        return jsonify({"logs": f"Fehler: {e}"})



@app.route("/api/system/time", methods=["GET"])
def api_get_time():
    """Get current system and RTC time."""
    import subprocess
    data = {"system_time": "", "rtc_time": "", "ntp_active": False, "timezone": ""}
    try:
        r = subprocess.run(["timedatectl", "show", "--no-pager"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            if line.startswith("Timezone="):
                data["timezone"] = line.split("=", 1)[1]
            elif line.startswith("NTP="):
                data["ntp_active"] = line.split("=")[1].strip().lower() == "yes"
            elif line.startswith("NTPSynchronized="):
                data["ntp_synced"] = line.split("=")[1].strip().lower() == "yes"
    except:
        pass
    from datetime import datetime
    data["system_time"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    data["system_time_display"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    # RTC time
    try:
        r = subprocess.run(["sudo", "/usr/sbin/hwclock", "-r", "--rtc", "/dev/rtc1"],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            data["rtc_time"] = r.stdout.strip()
            data["rtc_available"] = True
        else:
            data["rtc_available"] = False
    except:
        data["rtc_available"] = False
    return jsonify(data)


@app.route("/api/system/time", methods=["POST"])
def api_set_time():
    """Set system time manually and sync to RTC."""
    import subprocess
    d = request.get_json()
    if not d or "datetime" not in d:
        return jsonify({"success": False, "message": "Kein Datum/Zeit angegeben"})

    dt_str = d["datetime"]  # Expected: "2026-03-18T14:30:00"

    try:
        # Disable NTP first so manual time sticks
        subprocess.run(["sudo", "/usr/bin/timedatectl", "set-ntp", "false"],
                       capture_output=True, timeout=5)

        # Set system time
        r = subprocess.run(["sudo", "/usr/bin/date", "-s", dt_str],
                           capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return jsonify({"success": False, "message": f"date -s fehlgeschlagen: {r.stderr}"})

        # Sync to hardware RTC (DS3231)
        rtc_msg = ""
        try:
            r2 = subprocess.run(["sudo", "/usr/sbin/hwclock", "-w", "--rtc", "/dev/rtc1"],
                                capture_output=True, text=True, timeout=5)
            if r2.returncode == 0:
                rtc_msg = " und in RTC gespeichert"
            else:
                rtc_msg = " (RTC-Sync fehlgeschlagen)"
        except:
            rtc_msg = " (keine RTC verfuegbar)"

        from datetime import datetime
        now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        logger.info(f"Uhrzeit manuell gesetzt: {now}")
        log_event("INFO", f"Uhrzeit manuell gesetzt: {now}")

        return jsonify({
            "success": True,
            "message": f"Uhrzeit gesetzt: {now}{rtc_msg}",
            "current_time": now
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Fehler: {e}"})



@app.route("/api/system/timezone", methods=["POST"])
def api_set_timezone():
    """Set system timezone."""
    import subprocess
    d = request.get_json()
    tz = d.get("timezone", "") if d else ""
    if not tz:
        return jsonify({"success": False, "message": "Keine Zeitzone angegeben"})
    try:
        r = subprocess.run(["sudo", "/usr/bin/timedatectl", "set-timezone", tz],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            # Also sync to RTC
            subprocess.run(["sudo", "/usr/sbin/hwclock", "-w", "--rtc", "/dev/rtc1"],
                           capture_output=True, timeout=5)
            logger.info(f"Zeitzone gesetzt: {tz}")
            return jsonify({"success": True, "message": f"Zeitzone: {tz}"})
        else:
            return jsonify({"success": False, "message": r.stderr})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/system/ntp", methods=["POST"])
def api_toggle_ntp():
    """Enable or disable NTP."""
    import subprocess
    d = request.get_json()
    enable = d.get("enable", True) if d else True
    try:
        r = subprocess.run(
            ["sudo", "/usr/bin/timedatectl", "set-ntp", "true" if enable else "false"],
            capture_output=True, text=True, timeout=5
        )
        state = "aktiviert" if enable else "deaktiviert"
        if r.returncode == 0:
            return jsonify({"success": True, "message": f"NTP {state}"})
        else:
            return jsonify({"success": False, "message": r.stderr})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})



@app.route("/api/storage/download-zip", methods=["POST"])
def api_download_zip():
    """Download multiple files as a single ZIP archive."""
    import zipfile
    import io
    from storage_manager import SD_PDF_DIR, USB_MOUNT_POINT, USB_PDF_SUBDIR

    d = request.get_json(silent=True) or {}
    pane = d.get("pane", "sd")
    files = d.get("files", [])

    if not files:
        return jsonify({"success": False, "message": "Keine Dateien ausgewaehlt"}), 400

    if pane == "sd":
        base = SD_PDF_DIR
    else:
        base = os.path.join(USB_MOUNT_POINT, USB_PDF_SUBDIR)

    # Create ZIP in memory
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_path in files:
            full_path = os.path.join(base, rel_path)
            # Security check
            real_base = os.path.realpath(base)
            real_path = os.path.realpath(full_path)
            if not real_path.startswith(real_base):
                continue
            if os.path.isfile(real_path):
                zf.write(real_path, os.path.basename(rel_path))

    mem_zip.seek(0)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"DocuControl_Protokolle_{ts}.zip"

    return send_file(
        mem_zip,
        mimetype="application/zip",
        as_attachment=True,
        download_name=filename
    )

# --- Printer API ---



@app.route('/api/protocols/<int:pid>', methods=['DELETE'])
def api_protocol_delete(pid):
    guard = _require_service()
    if guard: return guard
    db = get_db()
    row = db.execute('SELECT pdf_path FROM protocols WHERE id=?', (pid,)).fetchone()
    if not row:
        return jsonify({'success': False, 'error': 'Protokoll nicht gefunden'}), 404
    pdf_path = row['pdf_path']
    db.execute('DELETE FROM protocols WHERE id=?', (pid,))
    db.commit()
    if pdf_path and os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except Exception as e:
            logger.warning('PDF-Datei konnte nicht geloescht werden: %s', e)
    return jsonify({'success': True})

@app.route('/api/printer/status')
def api_printer_status():
    status = get_printer_status()
    printers = status.get('printers', [])
    connected_printers = [p for p in printers if p.get('connected', False)]
    printer_model = (connected_printers[0].get('model') or '') if connected_printers else ''
    return jsonify({
        'printer': printer_model,
        'model': printer_model,
        'cups_available': status['cups_available'],
        'printer_count': len(connected_printers),
        'auto_print': status['auto_print'],
        'printers': printers,
    })


@app.route('/api/printer/detect', methods=['POST'])
def api_printer_detect():
    status = get_printer_status()
    printers = status.get('printers', [])
    printer_model = (printers[0].get('model') or printers[0]['info']) if printers else ''
    return jsonify({'success': True, 'printer': printer_model, 'model': printer_model, 'count': len(printers)})


@app.route('/api/printer/setup', methods=['POST'])
def api_printer_setup():
    """Legt DocuPrinter neu an - USB oder Netzwerk je nach Auswahl (driverless via IPP Everywhere)."""
    d = request.get_json(silent=True) or {}
    config = load_print_config()
    conn_type = (d.get('connection_type') or config.get('connection_type', 'usb')).strip()
    network_host = (d.get('network_host') if 'network_host' in d else config.get('network_host', '')) or ''
    network_host = network_host.strip()
    config['connection_type'] = conn_type
    config['network_host'] = network_host
    save_print_config(config)
    if conn_type == 'network':
        if not network_host:
            return jsonify({'success': False, 'message': 'Bitte IP/Hostname des Netzwerkdruckers angeben'})
        ok, msg = setup_network_printer(network_host)
    else:
        if not is_usb_printer_present():
            return jsonify({'success': False, 'message': 'Kein USB-Drucker angeschlossen'})
        ok, msg = setup_usb_printer()
    return jsonify({'success': ok, 'message': msg})


@app.route('/api/printer/config')
def api_printer_config():
    config = load_print_config()
    return jsonify({
        'connection_type': config.get('connection_type', 'usb'),
        'network_host': config.get('network_host', ''),
    })


@app.route('/api/printer/test', methods=['POST'])
def api_printer_test_alias():
    d = request.get_json(silent=True) or {}
    ok, msg, job_id = printer_test_print(d.get('printer', ''))
    return jsonify({'success': ok, 'message': msg, 'job_id': job_id})


@app.route('/api/printer/auto_print', methods=['POST'])
def api_printer_auto_print():
    d = request.get_json(silent=True) or {}
    config = load_print_config()
    config['auto_print'] = bool(d.get('enabled', False))
    save_print_config(config)
    return jsonify({'success': True, 'auto_print': config['auto_print']})

@app.route('/api/printer/ready')
def api_printer_ready():
    if not is_cups_available():
        return jsonify({'ready': False, 'printer': '', 'state': 'CUPS nicht verfuegbar'})
    printers = get_printers()
    if not printers:
        return jsonify({'ready': False, 'printer': '', 'state': 'Kein Drucker'})
    config = load_print_config()
    name = config.get('default_printer') or printers[0]['name']
    p = next((x for x in printers if x['name'] == name), printers[0])
    ready = p['state'] in (3, 4) and p.get('connected', False)
    state_text = p['state_text'] if p.get('connected', False) else 'Kein Drucker angeschlossen'
    return jsonify({'ready': ready, 'printer': p.get('model') or p.get('info') or p['name'], 'state': state_text})


@app.route('/api/machine/ping')
def api_machine_ping():
    cfg = load_config().get('machine', {})
    ip = cfg.get('ip', '').strip()
    if not ip:
        return jsonify({'reachable': False, 'configured': False, 'ip': '', 'latency_ms': None})
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', '2', ip],
            capture_output=True, text=True, timeout=5
        )
        reachable = result.returncode == 0
        latency = None
        if reachable:
            import re as _re2
            m = _re2.search(r'time=(\d+\.?\d*)', result.stdout)
            if m:
                latency = float(m.group(1))
        return jsonify({'reachable': reachable, 'configured': True, 'ip': ip, 'latency_ms': latency})
    except Exception as e:
        return jsonify({'reachable': False, 'configured': True, 'ip': ip, 'latency_ms': None, 'error': str(e)})


def _root_device_is_nvme():
    """True wenn / aktuell (auch durch LUKS/dm-mapper hindurch) von der NVMe-SSD
    gebootet ist. False bei Boot von der SD-Karte (Notfall-Fallback nach
    BOOT_ORDER, siehe SSD-Klon-Doku in CLAUDE.md).

    Laeuft die App in Docker, ist '/' im Container immer 'overlay' -- die reine
    findmnt-Abfrage auf '/' liefert dort nie etwas Brauchbares. Stattdessen wird
    das echte Host-Root ueber die (namespace-uebergreifende) mountinfo-Datei
    von PID 1 ermittelt und das Major:Minor rekursiv durch sysfs aufgeloest,
    damit auch ein LUKS-verschluesseltes Root (/dev/mapper/cryptroot) korrekt
    bis zur physischen NVMe-Partition zurueckverfolgt wird."""
    major_minor = None
    for mountinfo_path in ('/hostproc/1/mountinfo', '/proc/1/mountinfo'):
        try:
            with open(mountinfo_path) as f:
                for line in f:
                    fields = line.split(' - ', 1)[0].split()
                    if len(fields) >= 5 and fields[4] == '/':
                        major_minor = fields[2]
                        break
        except OSError:
            continue
        if major_minor:
            break

    if major_minor:
        try:
            real = os.path.realpath(f'/sys/dev/block/{major_minor}')
            name = os.path.basename(real)
            if name.startswith('nvme'):
                return True
            slaves_dir = os.path.join(real, 'slaves')
            if os.path.isdir(slaves_dir):
                return any(s.startswith('nvme') for s in os.listdir(slaves_dir))
            return False
        except OSError:
            pass

    try:
        r = subprocess.run(['findmnt', '-n', '-o', 'SOURCE', '/'], capture_output=True, text=True, timeout=5)
        return 'nvme' in r.stdout
    except Exception:
        return True  # bei Unsicherheit keinen Fehlalarm ausloesen


@app.route('/api/system/alerts')
def api_system_alerts():
    """Aktive Stoerungen fuer die rote Alarm-Anzeige in der Topbar."""
    alerts = []

    # Verbindung zur Maschine
    try:
        mcfg = load_config().get('machine', {})
        ip = mcfg.get('ip', '').strip()
        if ip:
            r = subprocess.run(['ping', '-c', '1', '-W', '2', ip], capture_output=True, text=True, timeout=5)
            if r.returncode != 0:
                alerts.append({'type': 'machine_offline', 'icon': 'bi-plug-fill',
                                'label': 'Verbindung Maschine inaktiv'})
    except Exception:
        pass

    # Drucker (nur relevant wenn Auto-Druck aktiv ist)
    try:
        pconfig = load_print_config()
        if pconfig.get('auto_print'):
            printers = get_printers()
            ready = False
            if printers:
                name = pconfig.get('default_printer') or printers[0]['name']
                p = next((x for x in printers if x['name'] == name), printers[0])
                ready = p['state'] in (3, 4) and p.get('connected', False)
            if not ready:
                alerts.append({'type': 'printer_offline', 'icon': 'bi-printer-fill',
                                'label': 'Drucker offline'})
    except Exception:
        pass

    # SSD-Ausfall (Notfallbetrieb von SD-Karte)
    try:
        if not _root_device_is_nvme():
            alerts.append({'type': 'ssd_failed', 'icon': 'bi-hdd-fill',
                            'label': 'SSD defekt — Notfallbetrieb von SD-Karte'})
    except Exception:
        pass

    # Netzwerk-Speicherort
    try:
        ns = get_network_storage_status()
        if ns.get('enabled') and not ns.get('mounted'):
            alerts.append({'type': 'network_storage_unreachable', 'icon': 'bi-hdd-network-fill',
                            'label': 'Verbindung Netzwerkspeicherort nicht erreichbar'})
    except Exception:
        pass

    # USB-Stick (nur relevant wenn USB-Auto-Sync aktiviert ist)
    try:
        sync_cfg = load_sync_config()
        if sync_cfg.get('auto_sync_enabled'):
            usb = get_usb_info()
            if not usb.get('detected') or not usb.get('mounted'):
                alerts.append({'type': 'usb_disconnected', 'icon': 'bi-usb-symbol',
                                'label': 'USB-Stick nicht angeschlossen'})
    except Exception:
        pass

    return jsonify({'alerts': alerts})


@app.route('/api/machine/config', methods=['GET', 'POST'])
def api_machine_config():
    if request.method == 'GET':
        cfg = load_config().get('machine', {})
        return jsonify({
            'name': cfg.get('name', ''),
            'machine_nr': cfg.get('machine_nr', ''),
            'ip': cfg.get('ip', ''),
            'protocol': cfg.get('protocol', ''),
            'location': cfg.get('location', '')
        })
    guard = _require_service()
    if guard: return guard
    d = request.get_json(silent=True) or {}
    config = load_config()
    if 'machine' not in config:
        config['machine'] = {}
    if 'name' in d:
        config['machine']['name'] = d['name'].strip()
    if 'machine_nr' in d:
        config['machine']['machine_nr'] = d['machine_nr'].strip()
    if 'ip' in d:
        config['machine']['ip'] = d['ip'].strip()
    if 'location' in d:
        config['machine']['location'] = d['location'].strip()
    save_config(config)
    return jsonify({'success': True})


@app.route('/api/print/<int:pid>', methods=['POST'])
def api_print_by_id(pid):
    db = get_db()
    row = db.execute('SELECT pdf_path, pdf_filename FROM protocols WHERE id=?', (pid,)).fetchone()
    if not row or not row['pdf_path']:
        return jsonify({'success': False, 'error': 'Kein PDF fuer dieses Protokoll'})
    if not os.path.exists(row['pdf_path']):
        return jsonify({'success': False, 'error': 'PDF-Datei nicht gefunden: ' + (row['pdf_filename'] or '')})
    ok, msg, job_id = print_pdf(row['pdf_path'])
    return jsonify({'success': ok, 'message': msg, 'job_id': job_id})

@app.route("/api/printers")
def api_printers():
    """List available printers."""
    return jsonify(get_printer_status())

@app.route("/api/print", methods=["POST"])
def api_print():
    """Print a PDF file."""
    d = request.get_json(silent=True) or {}
    pdf_path = d.get("file_path", "")
    printer = d.get("printer", "")
    copies = d.get("copies", 1)
    all_pages = d.get("all_pages", True)
    if not pdf_path:
        return jsonify({"success": False, "message": "Kein Dateipfad angegeben"})
    ok, msg, job_id = print_pdf(pdf_path, printer, copies, all_pages)
    return jsonify({"success": ok, "message": msg, "job_id": job_id})

@app.route("/api/print/test", methods=["POST"])
def api_print_test():
    """Print test page."""
    d = request.get_json(silent=True) or {}
    printer = d.get("printer", "")
    ok, msg, job_id = printer_test_print(printer)
    return jsonify({"success": ok, "message": msg, "job_id": job_id})

@app.route("/api/print/queue")
def api_print_queue():
    """Get print queue."""
    return jsonify({"jobs": get_print_queue()})

@app.route("/api/print/cancel", methods=["POST"])
def api_print_cancel():
    """Cancel print job."""
    d = request.get_json(silent=True) or {}
    job_id = d.get("job_id", 0)
    ok, msg = cancel_job(int(job_id))
    return jsonify({"success": ok, "message": msg})

@app.route("/api/print/config", methods=["GET"])
def api_print_config_get():
    """Get print configuration."""
    return jsonify(load_print_config())

@app.route("/api/print/config", methods=["POST"])
def api_print_config_set():
    """Update print configuration."""
    d = request.get_json(silent=True) or {}
    config = load_print_config()
    if "auto_print" in d: config["auto_print"] = bool(d["auto_print"])
    if "default_printer" in d: config["default_printer"] = d["default_printer"]
    if "copies" in d: config["copies"] = max(1, min(10, int(d["copies"])))
    if "all_pages" in d: config["all_pages"] = bool(d["all_pages"])
    if "color_mode" in d: config["color_mode"] = d["color_mode"]
    save_print_config(config)
    return jsonify({"success": True, "message": "Druckeinstellungen gespeichert", "config": config})

@app.route("/api/watchdog/status")
def api_watchdog_status():
    """Get watchdog status."""
    try:
        return jsonify(get_watchdog_status())
    except Exception as e:
        return jsonify({"available": False, "error": str(e)})

@app.route("/api/system/reboot", methods=["POST"])
def api_reboot():
    log_event("WARN","Reboot"); subprocess.Popen(["sudo","reboot"]); return jsonify({"status":"rebooting"})

@socketio.on("connect")
def on_connect(): logger.info("WS Client verbunden")
@socketio.on("disconnect")
def on_disconnect(): logger.info("WS Client getrennt")

# Captive Portal Routes - Cookie-based CNA dismiss flow
# ---------------------------------------------------------------
APPLE_SUCCESS = "<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>"

@app.route("/hotspot-detect.html")
@app.route("/library/test/success.html")
def captive_apple():
    if request.cookies.get("docupi_auth"):
        return APPLE_SUCCESS
    return render_template("captive.html")

@app.route("/generate_204")
@app.route("/gen_204")
def captive_android():
    if request.cookies.get("docupi_auth"):
        return "", 204
    return render_template("captive.html")

@app.route("/connecttest.txt")
@app.route("/ncsi.txt")
def captive_windows():
    if request.cookies.get("docupi_auth"):
        return "Microsoft Connect Test"
    return render_template("captive.html")

@app.route("/canonical.html")
@app.route("/captive")
def captive_generic():
    return render_template("captive.html")

@app.route("/captive-auth", methods=["POST"])
def captive_auth():
    resp = make_response(jsonify({"status": "ok", "message": "Authentifiziert - Browser oeffnen"}))
    resp.set_cookie("docupi_auth", "1", max_age=86400, path="/")
    return resp



# --- Graceful Shutdown ---
_shutdown_done = False
def graceful_shutdown(signum=None, frame=None):
    global _shutdown_done
    if _shutdown_done:
        return
    _shutdown_done = True
    sig_name = signal.Signals(signum).name if signum else "atexit"
    logger.info("Graceful shutdown (%s)...", sig_name)
    try:
        if hasattr(app, '_serial_receiver') and app._serial_receiver:
            app._serial_receiver.stop()
            logger.info("Serial Receiver gestoppt")
    except Exception as e:
        logger.error("Fehler beim Stoppen des Receivers: %s", e)
    try:
        stop_watchdog_thread()
    except Exception:
        pass
    log_event("INFO", "DocuControl heruntergefahren")
    logger.info("Shutdown abgeschlossen")
    if signum is not None:
        os._exit(0)

signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)
atexit.register(graceful_shutdown)


@app.route("/api/tcp_capture/status")
def api_tcp_capture_status():
    return jsonify(get_capture_status())


@app.route("/api/tcp_capture/config", methods=["GET"])
def api_tcp_capture_config_get():
    return jsonify(load_capture_config())


@app.route("/api/tcp_capture/config", methods=["POST"])
def api_tcp_capture_config_post():
    data = request.json or {}
    # tcp_enabled/port gehoeren zur Karte "TCP-Empfang" (Service-gesperrt),
    # auto_print gehoert zur Karte "Drucker" (immer bearbeitbar) - daher nur
    # bei tcp_enabled/port pruefen, nicht den ganzen Endpunkt sperren.
    if "tcp_enabled" in data or "port" in data:
        guard = _require_service()
        if guard: return guard
    cfg = load_capture_config()
    if "tcp_enabled" in data:
        cfg["tcp_enabled"] = bool(data["tcp_enabled"])
    if "auto_print" in data:
        cfg["auto_print"] = bool(data["auto_print"])
    if "port" in data:
        cfg["port"] = int(data["port"])
    save_capture_config(cfg)
    return jsonify({"ok": True, "config": cfg})


@app.route("/api/dashboard/chargen")
def api_dashboard_chargen():
    capture_dir = "/home/docucontrol/docupi/data/raw_captures"
    result = []
    if os.path.exists(capture_dir):
        bins = sorted(
            [f for f in os.listdir(capture_dir) if f.endswith(".bin")],
            reverse=True
        )[:20]
        for fname in bins:
            fpath = os.path.join(capture_dir, fname)
            txt_path = fpath.replace(".bin", ".txt")
            size = os.path.getsize(fpath)
            try:
                ts_raw = fname[:15]
                ts_fmt = f"{ts_raw[6:8]}.{ts_raw[4:6]}.{ts_raw[0:4]} {ts_raw[9:11]}:{ts_raw[11:13]}:{ts_raw[13:15]}"
            except Exception:
                ts_fmt = fname
            preview = ""
            if os.path.exists(txt_path):
                try:
                    with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
                        lines = [l.strip() for l in f.readlines() if l.strip()][:4]
                        preview = " | ".join(lines)[:150]
                except Exception:
                    pass
            result.append({
                "filename": fname,
                "timestamp": ts_fmt,
                "size": size,
                "has_text": os.path.exists(txt_path),
                "preview": preview,
            })
    return jsonify(result)


@app.route("/api/tcp_capture/last_text")
def api_tcp_last_text():
    capture_dir = "/home/docucontrol/docupi/data/raw_captures"
    txts = sorted(
        [f for f in os.listdir(capture_dir) if f.endswith(".txt")],
        reverse=True
    ) if os.path.exists(capture_dir) else []
    if not txts:
        return jsonify({"filename": None, "content": "", "timestamp": None})
    fname = txts[0]
    fpath = os.path.join(capture_dir, fname)
    try:
        ts_raw = fname[:15]
        ts_fmt = f"{ts_raw[6:8]}.{ts_raw[4:6]}.{ts_raw[0:4]} {ts_raw[9:11]}:{ts_raw[11:13]}:{ts_raw[13:15]}"
    except Exception:
        ts_fmt = fname
    try:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(50000)
    except Exception:
        content = ""
    return jsonify({"filename": fname, "content": content, "timestamp": ts_fmt})


@app.route("/api/tcp_capture/captures")
def api_tcp_capture_list():
    capture_dir = '/home/docucontrol/docupi/data/raw_captures'
    files = []
    if os.path.exists(capture_dir):
        for fn in sorted(os.listdir(capture_dir)):
            fp = os.path.join(capture_dir, fn)
            files.append({"name": fn, "size": os.path.getsize(fp)})
    return jsonify(files)


@app.route("/api/tcp_capture/captures/<fname>")
def api_tcp_capture_download(fname):
    capture_dir = '/home/docucontrol/docupi/data/raw_captures'
    fp = os.path.join(capture_dir, fname)
    if not os.path.exists(fp):
        return jsonify({"error": "not found"}), 404
    return send_file(fp, as_attachment=True)


@app.route("/api/tcp_capture/captures/delete", methods=["POST"])
def api_tcp_capture_delete_all():
    guard = _require_service()
    if guard: return guard
    import glob
    capture_dir = "/home/docucontrol/docupi/data/raw_captures"
    deleted = 0
    for f in glob.glob(os.path.join(capture_dir, "*")):
        try:
            os.remove(f)
            deleted += 1
        except Exception:
            pass
    log_event("INFO", f"Captures gelöscht: {deleted} Dateien")
    return jsonify({"ok": True, "deleted": deleted})



@app.route("/api/tcp_capture/captures/<fname>", methods=["DELETE"])
def api_tcp_capture_delete_one(fname):
    guard = _require_service()
    if guard: return guard
    import re as _re_cap
    if not _re_cap.match(r'^[A-Za-z0-9_\-.]+$', fname):
        return jsonify({"error": "invalid filename"}), 400
    capture_dir = "/home/docucontrol/docupi/data/raw_captures"
    base = fname.rsplit('.', 1)[0] if '.' in fname else fname
    deleted = []
    for ext in ('.txt', '.bin'):
        fp = os.path.join(capture_dir, base + ext)
        if os.path.exists(fp):
            try:
                os.remove(fp)
                deleted.append(base + ext)
            except Exception as e:
                return jsonify({"error": str(e)}), 500
    log_event("INFO", f"Capture gelöscht: {base} ({len(deleted)} Dateien)")
    return jsonify({"ok": True, "deleted": deleted})


@app.route("/api/tcp_capture/captures/bulk-delete", methods=["POST"])
def api_tcp_capture_bulk_delete():
    guard = _require_service()
    if guard: return guard
    import re as _re_cap_bulk
    data = request.get_json(silent=True) or {}
    basenames = data.get("basenames", [])
    if not basenames:
        return jsonify({"ok": False, "error": "keine Basenames"}), 400
    capture_dir = "/home/docucontrol/docupi/data/raw_captures"
    deleted = 0
    errors = 0
    for base in basenames:
        if not _re_cap_bulk.match(r'^[A-Za-z0-9_\-]+$', base):
            errors += 1
            continue
        for ext in ('.txt', '.bin'):
            fp = os.path.join(capture_dir, base + ext)
            if os.path.exists(fp):
                try:
                    os.remove(fp)
                    deleted += 1
                except Exception as e:
                    logger.error(f"Bulk-Delete Capture {base}{ext}: {e}")
                    errors += 1
    log_event("INFO", f"Captures bulk gelöscht: {len(basenames)} Basen, {deleted} Dateien")
    return jsonify({"ok": True, "deleted": deleted, "errors": errors})


@app.route("/api/storage/sync/captures", methods=["POST"])
def api_storage_sync_captures():
    import shutil as _shutil
    capture_dir = "/home/docucontrol/docupi/data/raw_captures"
    if not os.path.ismount(USB_MOUNT_POINT):
        ok, msg = mount_usb()
        if not ok:
            return jsonify({"ok": False, "error": msg}), 400
    usb_captures_dir = os.path.join(USB_MOUNT_POINT, "docucontrol", "captures")
    os.makedirs(usb_captures_dir, exist_ok=True)
    copied = 0
    errors = 0
    if os.path.exists(capture_dir):
        for fname in os.listdir(capture_dir):
            src = os.path.join(capture_dir, fname)
            dst = os.path.join(usb_captures_dir, fname)
            try:
                if os.path.exists(dst) and os.path.getsize(src) == os.path.getsize(dst):
                    continue
                _shutil.copy2(src, dst)
                copied += 1
            except Exception as e:
                logger.error(f"Captures-Sync Fehler {fname}: {e}")
                errors += 1
    import subprocess as _sp
    _sp.run(["sync"], check=False)
    log_event("INFO", f"Captures auf USB synchronisiert: {copied} Dateien")
    return jsonify({"ok": True, "copied": copied, "errors": errors})


@app.route("/api/storage/captures/usb")
def api_storage_captures_usb():
    import os as _os
    from datetime import datetime as _dt
    from storage_manager import get_usb_info, USB_MOUNT_POINT as _USB_MOUNT, USB_CAPTURE_SUBDIR as _USB_CAP_SUBDIR
    usb = get_usb_info()
    if not usb.get("mounted"):
        return jsonify({"files": [], "error": "USB nicht gemountet"})
    base = _os.path.join(_USB_MOUNT, _USB_CAP_SUBDIR)
    files = []
    if _os.path.isdir(base):
        for fname in sorted(_os.listdir(base)):
            if not fname.lower().endswith(".txt"):
                continue
            fp = _os.path.join(base, fname)
            try:
                stat = _os.stat(fp)
                sz = stat.st_size
                sh = str(round(sz/1024, 1)) + " KB" if sz < 1048576 else str(round(sz/1048576, 1)) + " MB"
                bin_path = _os.path.join(base, fname.replace(".txt", ".bin"))
                has_bin = _os.path.exists(bin_path)
                files.append({
                    "name": fname,
                    "path": fname,
                    "size": sz,
                    "size_human": sh,
                    "has_bin": has_bin,
                    "modified": _dt.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M")
                })
            except Exception:
                pass
    return jsonify({"files": files})



@app.route('/api/protocols/bulk-delete', methods=['POST'])
def api_protocols_bulk_delete():
    guard = _require_service()
    if guard: return guard
    data = request.get_json(silent=True) or {}
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'ok': False, 'error': 'keine IDs'}), 400
    db = get_db()
    deleted = 0
    errors = 0
    for pid in ids:
        try:
            row = db.execute('SELECT pdf_path FROM protocols WHERE id=?', (pid,)).fetchone()
            if not row:
                continue
            pdf_path = row[0]
            db.execute('DELETE FROM protocols WHERE id=?', (pid,))
            db.commit()
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
            deleted += 1
        except Exception as e:
            logger.error(f'Bulk-Delete Protokoll {pid}: {e}')
            errors += 1
    db.close()
    log_event('INFO', f'Bulk-Delete: {deleted} Protokolle geloescht')
    return jsonify({'ok': True, 'deleted': deleted, 'errors': errors})


@app.route('/api/protocols/bulk-copy-usb', methods=['POST'])
def api_protocols_bulk_copy_usb():
    import shutil as _shutil
    data = request.get_json(silent=True) or {}
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'ok': False, 'error': 'keine IDs'}), 400
    if not os.path.ismount(USB_MOUNT_POINT):
        ok, msg = mount_usb()
        if not ok:
            return jsonify({'ok': False, 'error': msg}), 400
    usb_pdf_dir = os.path.join(USB_MOUNT_POINT, USB_PDF_SUBDIR)
    os.makedirs(usb_pdf_dir, exist_ok=True)
    db = get_db()
    copied = 0
    errors = 0
    for pid in ids:
        try:
            row = db.execute('SELECT pdf_path, pdf_filename FROM protocols WHERE id=?', (pid,)).fetchone()
            if not row or not row[0]:
                continue
            src = row[0]
            if not os.path.exists(src):
                continue
            dst = os.path.join(usb_pdf_dir, row[1])
            if os.path.exists(dst) and os.path.getsize(src) == os.path.getsize(dst):
                copied += 1
                continue
            _shutil.copy2(src, dst)
            copied += 1
        except Exception as e:
            logger.error(f'Bulk-Copy PDF {pid}: {e}')
            errors += 1
    db.close()
    import subprocess as _sp2
    _sp2.run(['sync'], check=False)
    log_event('INFO', f'Bulk-Copy PDF auf USB: {copied} Dateien')
    return jsonify({'ok': True, 'copied': copied, 'errors': errors})


@app.route('/api/protocols/bulk-download-zip', methods=['POST'])
def api_protocols_bulk_download_zip():
    import zipfile
    import io
    data = request.get_json(silent=True) or {}
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'ok': False, 'error': 'keine IDs'}), 400
    db = get_db()
    mem_zip = io.BytesIO()
    added = 0
    with zipfile.ZipFile(mem_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for pid in ids:
            row = db.execute('SELECT pdf_path, pdf_filename FROM protocols WHERE id=?', (pid,)).fetchone()
            if not row or not row[0] or not os.path.exists(row[0]):
                continue
            zf.write(row[0], row[1] or os.path.basename(row[0]))
            added += 1
    db.close()
    if added == 0:
        return jsonify({'ok': False, 'error': 'Keine Dateien gefunden'}), 404
    mem_zip.seek(0)
    from datetime import datetime as _dt
    ts = _dt.now().strftime('%Y%m%d_%H%M%S')
    return send_file(mem_zip, mimetype='application/zip', as_attachment=True,
                      download_name=f'DocuControl_Protokolle_{ts}.zip')


@app.route('/api/tcp_capture/captures/bulk-copy-usb', methods=['POST'])
def api_captures_bulk_copy_usb():
    import shutil as _shutil
    data = request.get_json(silent=True) or {}
    basenames = data.get('basenames', [])
    if not basenames:
        return jsonify({'ok': False, 'error': 'keine Basenames'}), 400
    capture_dir = '/home/docucontrol/docupi/data/raw_captures'
    if not os.path.ismount(USB_MOUNT_POINT):
        ok, msg = mount_usb()
        if not ok:
            return jsonify({'ok': False, 'error': msg}), 400
    usb_cap_dir = os.path.join(USB_MOUNT_POINT, 'docucontrol', 'captures')
    os.makedirs(usb_cap_dir, exist_ok=True)
    copied = 0
    errors = 0
    for base in basenames:
        for ext in ('.txt', '.bin'):
            src = os.path.join(capture_dir, base + ext)
            if not os.path.exists(src):
                continue
            dst = os.path.join(usb_cap_dir, base + ext)
            try:
                if os.path.exists(dst) and os.path.getsize(src) == os.path.getsize(dst):
                    continue
                _shutil.copy2(src, dst)
                copied += 1
            except Exception as e:
                logger.error(f'Bulk-Copy Capture {base}{ext}: {e}')
                errors += 1
    import subprocess as _sp3
    _sp3.run(['sync'], check=False)
    log_event('INFO', f'Bulk-Copy Captures auf USB: {copied} Dateien')
    return jsonify({'ok': True, 'copied': copied, 'errors': errors})


import re as _re

# ─────────────────────────────────────────────────────────────
# 1. Context Processor — tcp_connected für alle Templates
# ─────────────────────────────────────────────────────────────

@app.context_processor
def inject_tcp_status():
    try:
        status = get_capture_status()
        _mcfg = load_config().get('machine', {})
        pending = len(get_pending_protocols())
        return {
            'tcp_connected': bool(status.get('enabled', False)),
            'machine_name': _mcfg.get('name', 'Anlage'),
            'machine_protocol': _mcfg.get('protocol', ''),
            'pending_count': pending,
        }
    except Exception:
        _mcfg = load_config().get('machine', {})
        return {
            'tcp_connected': False,
            'machine_name': _mcfg.get('name', 'Anlage'),
            'machine_protocol': _mcfg.get('protocol', ''),
            'pending_count': 0,
        }


# ─────────────────────────────────────────────────────────────
# 2. GET /api/protocols
#    Query-Params:
#      page (default 1), per_page (default 20, max 100)
#      status: 'Bestanden' | 'Fehlgeschlagen' | '' (alle)
#      date_from, date_to: YYYY-MM-DD
#      charge_from, charge_to: int (Laufende Nr.)
#      sort_by: 'timestamp' | 'charge_nr'  (default timestamp)
#      sort_dir: 'asc' | 'desc'            (default desc)
#    Response:
#      { total, page, per_page, pages, protocols: [...] }
# ─────────────────────────────────────────────────────────────

_CHARGE_RE     = _re.compile(r'Laufende\s+Nr\.?\s*:\s*0*(\d+)', _re.IGNORECASE)
_CHARGE_PST_RE = _re.compile(r'Lfd\.Nr\.\s+(\d+)',             _re.IGNORECASE)
_PROG_RE       = _re.compile(r'Programm\s*[:\.]?\s*(.+)',       _re.IGNORECASE)
_START_RE      = _re.compile(r'Beginn\s*[:\.]?\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', _re.IGNORECASE)
_END_RE        = _re.compile(r'Ende\s*[:\.]?\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})',   _re.IGNORECASE)
_PROG_ENDE_RE  = _re.compile(r'^\s*(\d+):(\d+)\s+Programm\s+Ende', _re.MULTILINE | _re.IGNORECASE)
_DAUER_PST_RE  = _re.compile(r'Chargendauer\s+([\d.,]+)\s+min', _re.IGNORECASE)


def _extract_protocol_fields(row):
    """Extrahiert Charge-Nr., Programm und Dauer aus raw_data per Regex."""
    raw = row['raw_data'] or ''

    cm = _CHARGE_RE.search(raw)
    if cm:
        charge_nr_num = int(cm.group(1))
        charge_nr = 'CH0' + cm.group(1)
    else:
        cm_pst = _CHARGE_PST_RE.search(raw)
        if cm_pst:
            charge_nr_num = int(cm_pst.group(1))
            charge_nr = 'CH' + cm_pst.group(1)
        else:
            charge_nr_num = None
            charge_nr = ''

    pm = _PROG_RE.search(raw)
    prog = pm.group(1).strip()[:60] if pm else ''

    # Dauer: PST "Chargendauer X.X min" → primaer; alt: "MM:SS Programm Ende"; Fallback ISO diff
    duration = ''
    try:
        dm_pst = _DAUER_PST_RE.search(raw)
        em_ende = _PROG_ENDE_RE.search(raw)
        if dm_pst:
            total_sec = int(round(float(dm_pst.group(1).replace(',', '.')) * 60))
            duration = '{:02d}:{:02d}:{:02d}'.format(
                total_sec // 3600,
                (total_sec % 3600) // 60,
                total_sec % 60
            )
        elif em_ende:
            total_sec = int(em_ende.group(1)) * 60 + int(em_ende.group(2))
            duration = '{:02d}:{:02d}:{:02d}'.format(
                total_sec // 3600,
                (total_sec % 3600) // 60,
                total_sec % 60
            )
        else:
            sm = _START_RE.search(raw)
            em = _END_RE.search(raw)
            if sm and em:
                from datetime import datetime
                start_dt = datetime.strptime(sm.group(1), '%Y-%m-%d %H:%M')
                end_dt   = datetime.strptime(em.group(1), '%Y-%m-%d %H:%M')
                delta = int((end_dt - start_dt).total_seconds())
                if delta > 0:
                    duration = '{:02d}:{:02d}:{:02d}'.format(
                        delta // 3600, (delta % 3600) // 60, delta % 60)
    except Exception:
        pass

    raw_upper = raw.upper()
    has_fault = bool(
        ('PROZESSRELEVANTE STÖRUNG AUFGETRETEN' in raw_upper and 'KEINE PROZESSRELEVANTE' not in raw_upper)
        or 'BEENDET NICHT STERIL' in raw_upper
        or 'ABGEBROCHEN' in raw_upper
    )

    if row['status'] == 'pending_form':
        row_status = 'Wartet auf Formular'
    elif row['status'] == 'completed' and has_fault:
        row_status = 'Störung'
    elif row['status'] == 'completed':
        row_status = 'Bestanden'
    else:
        row_status = 'Fehlgeschlagen'

    return {
        'id':           row['id'],
        'charge_nr':    charge_nr,
        'charge_nr_num': charge_nr_num or 0,
        'timestamp':    row['timestamp'],
        'program':      prog,
        'duration':     duration,
        'status':       row_status,
        'db_status':    row['status'],
        'has_fault':    has_fault,
        'pdf_filename': row['pdf_filename'] or '',
        'file_size':    row['file_size'] or 0,
    }


@app.route('/api/protocols')
def api_protocols():
    page     = max(1, int(request.args.get('page', 1)))
    per_page = min(max(1, int(request.args.get('per_page', 20))), 100)
    status_f    = request.args.get('status', '').strip()
    date_from   = request.args.get('date_from', '').strip()
    date_to     = request.args.get('date_to', '').strip()
    charge_from = request.args.get('charge_from', '').strip()
    charge_to   = request.args.get('charge_to', '').strip()
    program_f   = request.args.get('program', '').strip()
    sort_by  = request.args.get('sort_by', 'timestamp').strip()
    sort_dir = request.args.get('sort_dir', 'desc').strip().lower()

    where_clauses = []
    params = []

    if status_f == 'Bestanden':
        where_clauses.append("status = 'completed'")
    elif status_f == 'Wartet auf Formular':
        where_clauses.append("status = 'pending_form'")
    elif status_f == 'Fehlgeschlagen':
        where_clauses.append("(status IS NULL OR (status != 'completed' AND status != 'pending_form'))")

    if date_from:
        where_clauses.append("date(timestamp) >= ?")
        params.append(date_from)
    if date_to:
        where_clauses.append("date(timestamp) <= ?")
        params.append(date_to)

    if charge_from.isdigit():
        where_clauses.append("charge_nr_int >= ?")
        params.append(int(charge_from))
    if charge_to.isdigit():
        where_clauses.append("charge_nr_int <= ?")
        params.append(int(charge_to))
    if program_f:
        where_clauses.append("program = ?")
        params.append(program_f)

    where = ('WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''

    db = get_db()
    total = db.execute(f"SELECT COUNT(*) FROM protocols {where}", params).fetchone()[0]

    order_col = 'charge_nr_int' if sort_by == 'charge_nr' else 'timestamp'
    order_dir_sql = 'DESC' if sort_dir == 'desc' else 'ASC'
    offset = (page - 1) * per_page

    sql = (f"SELECT id, timestamp, device_name, raw_data, pdf_path, pdf_filename, file_size, status "
           f"FROM protocols {where} ORDER BY {order_col} {order_dir_sql} LIMIT ? OFFSET ?")
    rows = db.execute(sql, params + [per_page, offset]).fetchall()

    page_data = [_extract_protocol_fields(row) for row in rows]
    for p in page_data:
        del p['charge_nr_num']

    pages = max(1, (total + per_page - 1) // per_page)
    return jsonify({
        'total':     total,
        'page':      page,
        'per_page':  per_page,
        'pages':     pages,
        'protocols': page_data,
    })


# ─────────────────────────────────────────────────────────────
# 3. GET /api/protocols/programs
#    Gibt distinct Programmnamen aus raw_data zurück (für Filter-Select).
# ─────────────────────────────────────────────────────────────

@app.route('/api/protocols/programs')
def api_protocols_programs():
    db = get_db()
    rows = db.execute(
        "SELECT DISTINCT program FROM protocols WHERE program IS NOT NULL ORDER BY program"
    ).fetchall()
    return jsonify([row['program'] for row in rows])




# ─────────────────────────────────────────────────────────────
# 4. GET /api/dashboard/stats
# ─────────────────────────────────────────────────────────────

@app.route("/api/dashboard/stats")
def api_dashboard_stats():
    db = get_db()
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 1:
        prev_start = month_start.replace(year=month_start.year - 1, month=12)
    else:
        prev_start = month_start.replace(month=month_start.month - 1)
    month_start_s = month_start.strftime("%Y-%m-%d")
    prev_start_s  = prev_start.strftime("%Y-%m-%d")
    total = db.execute("SELECT COUNT(*) FROM protocols").fetchone()[0]
    max_charge_nr = db.execute("SELECT MAX(charge_nr_int) FROM protocols").fetchone()[0] or 0
    today_count = db.execute(
        "SELECT COUNT(*) FROM protocols WHERE date(timestamp) = ?",
        (today_str,)
    ).fetchone()[0]
    month_count = db.execute(
        "SELECT COUNT(*) FROM protocols WHERE timestamp >= ?",
        (month_start_s,)
    ).fetchone()[0]
    prev_count = db.execute(
        "SELECT COUNT(*) FROM protocols WHERE timestamp >= ? AND timestamp < ?",
        (prev_start_s, month_start_s)
    ).fetchone()[0]
    last_today = db.execute(
        "SELECT timestamp FROM protocols WHERE date(timestamp) = ? ORDER BY timestamp DESC LIMIT 1",
        (today_str,)
    ).fetchone()
    last_time = ""
    if last_today:
        ts = (last_today[0] or "").replace("T", " ").split(".")[0]
        last_time = ts.split(" ")[1][:5] if " " in ts else ""
    trend_pct = None
    if prev_count > 0:
        trend_pct = round((month_count - prev_count) / prev_count * 100, 1)
    db.close()
    return jsonify({
        "total": total,
        "max_charge_nr": max_charge_nr,
        "today": today_count,
        "today_last_time": last_time,
        "month": month_count,
        "prev_month": prev_count,
        "month_trend_pct": trend_pct,
    })


# ─────────────────────────────────────────────────────────────
# Datensammlermodus — GET/POST /api/capture/collector
# ─────────────────────────────────────────────────────────────

@app.route('/api/capture/collector', methods=['GET'])
def api_collector_get():
    cfg = load_capture_config()
    return jsonify({'collector_mode': cfg.get('collector_mode', False)})


@app.route('/api/capture/collector', methods=['POST'])
def api_collector_set():
    guard = _require_service()
    if guard: return guard
    data = request.get_json(silent=True) or {}
    enabled = bool(data.get('enabled', False))
    cfg = load_capture_config()
    cfg['collector_mode'] = enabled
    save_capture_config(cfg)
    return jsonify({'collector_mode': enabled, 'ok': True})


# ─────────────────────────────────────────────────────────────
# AUTOKLAVENBUCH WORKFLOW — Pending Charges API
# ─────────────────────────────────────────────────────────────

import json as _json


@app.route('/api/pending-charges')
def api_pending_charges():
    rows = get_pending_protocols()
    result = []
    for r in rows:
        form_json = r.get('form_data_json') or '{}'
        try:
            form = _json.loads(form_json)
        except Exception:
            form = {}
        result.append({
            'id': r['id'],
            'timestamp': r['timestamp'],
            'device_name': r.get('device_name', ''),
            'charge_nr_int': r.get('charge_nr_int'),
            'program': r.get('program', ''),
            'preselected_program': r.get('preselected_program', ''),
            'form_draft': form,
            'confirmed_at': r.get('confirmed_at'),
        })
    return jsonify({'pending': result, 'count': len(result)})


@app.route('/api/pending-charges/<int:pid>')
def api_pending_charge_detail(pid):
    row = get_pending_protocol(pid)
    if not row:
        return jsonify({'error': 'Nicht gefunden oder nicht mehr pending'}), 404
    form_json = row.get('form_data_json') or '{}'
    try:
        form = _json.loads(form_json)
    except Exception:
        form = {}
    presel = row.get('preselected_program', '')
    if not presel and row.get('program'):
        from protocol_parser import preselect_autoclave_program
        presel_data = preselect_autoclave_program(row['program'], row.get('raw_data', ''))
        presel = presel_data.get('program_key', '')
    raw = (row.get('raw_data') or '').upper()
    has_fault = bool(
        ('PROZESSRELEVANTE STÖRUNG AUFGETRETEN' in raw and 'KEINE PROZESSRELEVANTE' not in raw)
        or 'BEENDET NICHT STERIL' in raw
        or 'ABGEBROCHEN' in raw
    )
    return jsonify({
        'id': row['id'],
        'timestamp': row['timestamp'],
        'device_name': row.get('device_name', ''),
        'charge_nr_int': row.get('charge_nr_int'),
        'program': row.get('program', ''),
        'preselected_program': presel,
        'has_fault': has_fault,
        'form_draft': form,
        'confirmed_at': row.get('confirmed_at'),
        'raw_data_preview': (row.get('raw_data') or '')[:400],
    })


@app.route('/api/pending-charges/<int:pid>/form', methods=['POST'])
def api_pending_form_save(pid):
    data = request.get_json(silent=True) or {}
    form_json = _json.dumps(data, ensure_ascii=False)
    save_form_draft(pid, form_json)
    return jsonify({'ok': True})


@app.route('/api/pending-charges/<int:pid>/confirm', methods=['POST'])
def api_pending_form_confirm(pid):
    body = request.get_json(silent=True) or {}
    form_data = body.get('form_data', {})
    confirmed_by = (body.get('confirmed_by') or '').strip()
    confirmed_initials = (body.get('confirmed_initials') or '').strip()
    preselected_program = (body.get('preselected_program') or '').strip()
    selected_program = (form_data.get('autoclave_program') or '').strip()
    program_was_changed = 1 if selected_program and selected_program != preselected_program else 0

    if not confirmed_by or not confirmed_initials:
        return jsonify({'error': 'Name und Kürzel des Bedieners sind Pflichtfelder'}), 400
    if not (form_data.get('result') or '').strip():
        return jsonify({'error': 'Ergebnis (Ablauf OK / Störung) ist Pflichtfeld'}), 400

    row = get_pending_protocol(pid)
    if not row:
        return jsonify({'error': 'Charge nicht gefunden oder bereits abgeschlossen'}), 404

    confirmed_at = datetime.now().isoformat()
    form_data['confirmed_at'] = confirmed_at
    form_data['confirmed_by'] = confirmed_by
    form_data['confirmed_initials'] = confirmed_initials

    confirm_form(
        pid,
        _json.dumps(form_data, ensure_ascii=False),
        confirmed_by, confirmed_initials, confirmed_at,
        preselected_program, program_was_changed
    )

    import threading as _thr

    def _gen():
        ok, result = _finalize_charge_pdf(pid, form_data)
        if ok:
            log_event("INFO", f"Autoklavenbuch bestätigt + PDF erstellt: {result} (pid={pid})")
            socketio.emit('charge_completed', {'protocol_id': pid, 'pdf_filename': result})
        else:
            log_event("ERROR", f"PDF-Generierung fehlgeschlagen (pid={pid}): {result}")
            socketio.emit('charge_pdf_error', {'protocol_id': pid, 'error': result})

    _thr.Thread(target=_gen, daemon=True).start()
    log_event("INFO", f"Autoklavenbuch Formular bestätigt von {confirmed_by} ({confirmed_initials}), pid={pid}")
    return jsonify({'ok': True, 'confirmed_at': confirmed_at})


@app.route('/api/pending-charges/<int:pid>', methods=['DELETE'])
def api_pending_charge_discard(pid):
    guard = _require_service()
    if guard: return guard
    discard_pending(pid)
    log_event("WARN", f"Pending Charge pid={pid} verworfen (kein Formular ausgefüllt)")
    return jsonify({'ok': True})


@app.route('/api/charges/<int:pid>/retry-pdf', methods=['POST'])
def api_retry_pdf(pid):
    """PDF-Generierung für fehlgeschlagene Chargen (pdf_failed) nochmal versuchen."""
    rows = get_form_confirmed_protocols()
    row = next((r for r in rows if r['id'] == pid), None)
    if not row:
        return jsonify({'ok': False, 'error': 'Charge nicht gefunden oder Status nicht pdf_failed'}), 404

    form_data_json = row.get('form_data_json') or '{}'
    try:
        import json as _json
        form_data = _json.loads(form_data_json)
    except Exception:
        form_data = {}

    if row.get('confirmed_by'):
        form_data['confirmed_by'] = row['confirmed_by']
    if row.get('confirmed_at'):
        form_data['confirmed_at'] = row['confirmed_at']

    import threading as _thr
    def _gen():
        ok, result = _finalize_charge_pdf(pid, form_data)
        if ok:
            socketio.emit('pdf_ready', {'pid': pid, 'filename': result})
            log_event("INFO", f"PDF-Retry erfolgreich: pid={pid}, {result}")
        else:
            log_event("ERROR", f"PDF-Retry fehlgeschlagen: pid={pid}, {result}")

    _thr.Thread(target=_gen, daemon=True).start()
    log_event("INFO", f"PDF-Retry gestartet: pid={pid}")
    return jsonify({'ok': True, 'message': 'PDF-Generierung läuft'})


if __name__ == "__main__":
    config = load_config()
    log_event("INFO", "DocuControl gestartet")
    init_hotspot_on_boot()
    start_hotspot_monitor()
    # TCP/9100 Print-Capture (DocuControl)
    try:
        _cap_cfg = load_capture_config()
        if _cap_cfg.get("tcp_enabled", True):
            start_capture_server(auto_print=_cap_cfg.get("auto_print", False))
            logger.info(f"TCP/{_cap_cfg.get('port', 9100)} Capture-Server gestartet")
        else:
            logger.info("TCP-Capture deaktiviert (capture_config.json)")
    except Exception as e:
        logger.warning(f"TCP capture Init-Fehler: {e}")
    # USB beim Boot mounten (nach Stromausfall/Reboot)
    try:
        try_mount_usb_on_boot()
    except Exception as e:
        logger.warning(f"USB Boot-Mount Fehler: {e}")
    # Auto-Sync starten
    start_auto_sync()
    start_network_sync()
    # Drucker beim Start konfigurieren (USB oder Netzwerk je nach gespeicherter Auswahl)
    try:
        _print_cfg = load_print_config()
        if _print_cfg.get('connection_type') == 'network' and _print_cfg.get('network_host'):
            ok, msg = setup_network_printer(_print_cfg['network_host'])
            logger.info(f"Drucker-Setup beim Start (Netzwerk): {msg}")
        elif is_usb_printer_present():
            ok, msg = setup_usb_printer()
            logger.info(f"Drucker-Setup beim Start (USB): {msg}")
        else:
            logger.info("Drucker-Setup beim Start: kein Drucker konfiguriert/angeschlossen")
    except Exception as e:
        logger.warning(f"Drucker-Setup beim Start fehlgeschlagen: {e}")

    # Start hardware watchdog (Waveshare RTC Watchdog HAT B)
    try:
        if start_watchdog_thread(timeout=120):
            logger.info("Hardware-Watchdog aktiviert (120s Timeout)")
        else:
            logger.info("Kein Watchdog HAT erkannt - laeuft ohne Hardware-Watchdog")
    except Exception as e:
        logger.warning(f"Watchdog Init-Fehler: {e}")
    # receiver.start()  # DocuControl: kein RS232

    # Zusaetzlicher HTTPS-Listener (Port 5443, selbstsigniert) - laeuft parallel
    # zum bestehenden HTTP-Port 5000 in einem eigenen Thread, damit der Kiosk
    # (http://localhost:5000) unangetastet bleibt. Kein SocketIO auf diesem
    # Port noetig (Kiosk nutzt weiterhin HTTP), nur fuer externen Browserzugriff
    # per HTTPS gedacht.
    try:
        cert_file, key_file = _ensure_self_signed_cert()
        if cert_file and key_file:
            import threading as _threading_tls
            def _run_https():
                app.run(host=config["web"]["host"], port=5443,
                        ssl_context=(cert_file, key_file), debug=False,
                        use_reloader=False, threaded=True)
            _threading_tls.Thread(target=_run_https, daemon=True).start()
            logger.info("Web: https://0.0.0.0:5443 (selbstsigniertes Zertifikat)")
    except Exception as e:
        logger.warning(f"HTTPS-Listener konnte nicht gestartet werden: {e}")

    logger.info(f"Web: http://0.0.0.0:{config['web']['port']}")
    socketio.run(app, host=config["web"]["host"], port=config["web"]["port"], debug=False, allow_unsafe_werkzeug=True)

