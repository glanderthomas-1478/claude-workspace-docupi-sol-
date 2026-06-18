"""
DocuPi-3000 Network Storage Manager
- SMB/CIFS-Netzwerkfreigabe mounten/unmounten
- Verbindungstest mit verstaendlichen Fehlermeldungen
- Auto-Sync von PDFs und Rohdaten-Captures auf die Freigabe (Hintergrund-Thread)
"""

import os
import re
import json
import shutil
import logging
import threading
import time
import subprocess
from datetime import datetime, timedelta

logger = logging.getLogger("docupi.netstorage")

# Paths
SD_PDF_DIR = "/home/docucontrol/docupi/data/pdfs"
CAPTURE_DIR = "/home/docucontrol/docupi/data/raw_captures"
NETWORK_MOUNT_POINT = "/mnt/docucontrol_share"
NETWORK_PDF_SUBDIR = "DocuControl"
NETWORK_CAPTURE_SUBDIR = "docucontrol/captures"
CRED_FILE = "/home/docucontrol/docupi/data/network_share.cred"
NETWORK_CONFIG_FILE = "/home/docucontrol/docupi/data/network_storage_config.json"

SERVER_RE = re.compile(r"^[A-Za-z0-9._-]+$")
SHARE_RE = re.compile(r"^[A-Za-z0-9._\- ]+$")

DEFAULT_NETWORK_CONFIG = {
    "enabled": False,
    "server": "",
    "share": "",
    "username": "",
    "password": "",
    "domain": "",
    "sync_days": 7,
    "sync_interval_minutes": 15,
    "last_sync": None,
    "last_sync_count": 0,
    "last_error": "",
}


def _run(args, timeout=30):
    """Run command from argument list (no shell), return (success, stdout, stderr)."""
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "timeout"
    except Exception as e:
        return False, "", str(e)


# --- Config ---

def load_network_config():
    if os.path.exists(NETWORK_CONFIG_FILE):
        try:
            with open(NETWORK_CONFIG_FILE, "r") as f:
                saved = json.load(f)
                config = dict(DEFAULT_NETWORK_CONFIG)
                config.update(saved)
                return config
        except Exception:
            pass
    return dict(DEFAULT_NETWORK_CONFIG)


def save_network_config(config):
    os.makedirs(os.path.dirname(NETWORK_CONFIG_FILE), exist_ok=True)
    with open(NETWORK_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


# --- Validation & error translation ---

def _validate_server_share(server, share):
    if not server or not share:
        return False, "Server und Freigabename sind erforderlich"
    if not SERVER_RE.match(server):
        return False, "Server: nur Buchstaben, Ziffern, Punkt und Bindestrich erlaubt"
    if not SHARE_RE.match(share):
        return False, "Freigabename: nur Buchstaben, Ziffern, Leerzeichen, Punkt, Bindestrich und Unterstrich erlaubt"
    return True, ""


def _translate_mount_error(stderr):
    s = (stderr or "").lower()
    if "permission denied" in s or "error(13)" in s:
        return "Zugriff verweigert - Benutzername/Passwort pruefen"
    if "no such file or directory" in s or "error(2)" in s:
        return "Freigabe nicht gefunden - Freigabename pruefen"
    if ("host is down" in s or "unreachable" in s or "error(112)" in s or "error(101)" in s
            or "error(113)" in s or "no route to host" in s or "could not connect" in s):
        return "Server nicht erreichbar - IP/Hostname pruefen"
    return stderr or "Unbekannter Fehler beim Verbinden"


# --- Credentials file ---

def _write_credentials_file(username, password, domain, path=CRED_FILE):
    lines = [f"username={username}", f"password={password}"]
    if domain:
        lines.append(f"domain={domain}")
    content = "\n".join(lines) + "\n"
    with open(path, "w") as f:
        f.write(content)
    os.chmod(path, 0o600)


# --- Mount / Unmount ---

def is_mounted():
    return os.path.ismount(NETWORK_MOUNT_POINT)


def mount_network_share(cfg=None):
    cfg = cfg or load_network_config()

    if not cfg.get("enabled"):
        return False, "Netzwerk-Speicherort ist deaktiviert"

    ok, msg = _validate_server_share(cfg.get("server", ""), cfg.get("share", ""))
    if not ok:
        return False, msg

    if is_mounted():
        return True, "Bereits gemountet"

    _write_credentials_file(cfg.get("username", ""), cfg.get("password", ""), cfg.get("domain", ""))

    _run(["sudo", "/usr/bin/mkdir", "-p", NETWORK_MOUNT_POINT])

    unc = f"//{cfg['server']}/{cfg['share']}"
    options = f"credentials={CRED_FILE},uid=1000,gid=1000,iocharset=utf8,_netdev,file_mode=0644,dir_mode=0755,vers=3.0"
    ok, out, err = _run(["sudo", "/usr/bin/mount", "-t", "cifs", unc, NETWORK_MOUNT_POINT, "-o", options], timeout=30)

    if ok:
        pdf_dir = os.path.join(NETWORK_MOUNT_POINT, NETWORK_PDF_SUBDIR)
        capture_dir = os.path.join(NETWORK_MOUNT_POINT, NETWORK_CAPTURE_SUBDIR)
        os.makedirs(pdf_dir, exist_ok=True)
        os.makedirs(capture_dir, exist_ok=True)
        cfg["last_error"] = ""
        save_network_config(cfg)
        logger.info(f"Netzwerk-Freigabe gemountet: {unc} -> {NETWORK_MOUNT_POINT}")
        return True, f"Verbunden mit {unc}"
    else:
        msg = _translate_mount_error(err)
        cfg["last_error"] = msg
        save_network_config(cfg)
        logger.warning(f"Netzwerk-Freigabe Mount fehlgeschlagen: {err}")
        return False, msg


def unmount_network_share():
    if not is_mounted():
        return True, "Nicht gemountet"

    ok, _, err = _run(["sudo", "/usr/bin/umount", NETWORK_MOUNT_POINT])
    if ok:
        logger.info("Netzwerk-Freigabe ausgehaengt")
        return True, "Ausgehaengt"
    else:
        ok2, _, err2 = _run(["sudo", "/usr/bin/umount", "-l", NETWORK_MOUNT_POINT])
        if ok2:
            return True, "Ausgehaengt (lazy)"
        return False, f"Aushaengen fehlgeschlagen: {err}"


# --- Connection test ---

def test_network_connection(server, share, username, password, domain):
    ok, msg = _validate_server_share(server, share)
    if not ok:
        return False, msg

    unc = f"//{server}/{share}"

    cfg = load_network_config()
    if is_mounted() and cfg.get("server") == server and cfg.get("share") == share:
        return True, f"Verbindung OK (bereits verbunden mit {unc})"

    test_cred = CRED_FILE + ".test"
    _write_credentials_file(username, password, domain, path=test_cred)

    try:
        _run(["sudo", "/usr/bin/mkdir", "-p", NETWORK_MOUNT_POINT])
        options = f"credentials={test_cred},uid=1000,gid=1000,iocharset=utf8,vers=3.0"
        ok, out, err = _run(["sudo", "/usr/bin/mount", "-t", "cifs", unc, NETWORK_MOUNT_POINT, "-o", options], timeout=15)
        if ok:
            _run(["sudo", "/usr/bin/umount", NETWORK_MOUNT_POINT])
            return True, f"Verbindung erfolgreich ({unc})"
        else:
            return False, _translate_mount_error(err)
    finally:
        try:
            os.remove(test_cred)
        except OSError:
            pass


# --- Status ---

def get_network_storage_status():
    cfg = load_network_config()
    status = {
        "enabled": cfg.get("enabled", False),
        "mounted": is_mounted(),
        "server": cfg.get("server", ""),
        "share": cfg.get("share", ""),
        "username": cfg.get("username", ""),
        "has_password": bool(cfg.get("password", "")),
        "domain": cfg.get("domain", ""),
        "sync_days": cfg.get("sync_days", 7),
        "sync_interval_minutes": cfg.get("sync_interval_minutes", 15),
        "last_sync": cfg.get("last_sync"),
        "last_sync_count": cfg.get("last_sync_count", 0),
        "last_error": cfg.get("last_error", ""),
    }

    if status["mounted"]:
        try:
            s = shutil.disk_usage(NETWORK_MOUNT_POINT)
            status["total_gb"] = round(s.total / (1024**3), 1)
            status["free_gb"] = round(s.free / (1024**3), 1)
            status["used_percent"] = round(s.used / s.total * 100) if s.total else 0
        except Exception:
            pass

    return status


# --- Sync Engine ---

def sync_pdfs_to_network(days=None):
    """Sync PDFs from last N days from SD to network share."""
    cfg = load_network_config()
    if not cfg.get("enabled"):
        return False, "Netzwerk-Speicherort ist deaktiviert", 0

    if days is None:
        days = cfg.get("sync_days", 7)

    if not is_mounted():
        ok, msg = mount_network_share(cfg)
        if not ok:
            return False, msg, 0

    net_pdf_dir = os.path.join(NETWORK_MOUNT_POINT, NETWORK_PDF_SUBDIR)
    os.makedirs(net_pdf_dir, exist_ok=True)

    cutoff = datetime.now() - timedelta(days=days)
    synced = 0
    errors = 0

    for root, dirs, files in os.walk(SD_PDF_DIR):
        for fname in files:
            if not fname.lower().endswith(".pdf"):
                continue
            src = os.path.join(root, fname)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(src))
                if mtime < cutoff:
                    continue
                rel = os.path.relpath(src, SD_PDF_DIR)
                dst = os.path.join(net_pdf_dir, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.exists(dst):
                    if os.path.getsize(src) == os.path.getsize(dst) and \
                       os.path.getmtime(src) <= os.path.getmtime(dst):
                        continue
                shutil.copy2(src, dst)
                synced += 1
            except Exception as e:
                logger.error(f"Netzwerk-PDF-Sync-Fehler {fname}: {e}")
                errors += 1

    cfg = load_network_config()
    cfg["last_sync"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    cfg["last_sync_count"] = synced
    save_network_config(cfg)

    msg = f"{synced} PDFs synchronisiert (letzte {days} Tage)"
    if errors:
        msg += f", {errors} Fehler"
    logger.info(msg)
    return True, msg, synced


def copy_pdf_to_network_instant(pdf_path, pdf_filename):
    """Kopiert ein frisch erzeugtes PDF sofort auf den Netzwerk-Speicherort.
    Wird nach jeder neuen Charge aufgerufen."""
    cfg = load_network_config()
    if not cfg.get("enabled"):
        return

    if not is_mounted():
        ok, msg = mount_network_share(cfg)
        if not ok:
            logger.warning(f"Netzwerk Sofortkopie: Mount fehlgeschlagen: {msg}")
            return

    net_pdf_dir = os.path.join(NETWORK_MOUNT_POINT, NETWORK_PDF_SUBDIR)
    os.makedirs(net_pdf_dir, exist_ok=True)

    if SD_PDF_DIR in pdf_path:
        rel = os.path.relpath(pdf_path, SD_PDF_DIR)
        dst = os.path.join(net_pdf_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
    else:
        dst = os.path.join(net_pdf_dir, pdf_filename)

    try:
        shutil.copy2(pdf_path, dst)
        logger.info(f"Netzwerk Sofortkopie: {pdf_filename}")
    except Exception as e:
        logger.warning(f"Netzwerk Sofortkopie fehlgeschlagen: {e}")


def sync_captures_to_network(days=None):
    """Sync raw capture files from last N days from SD to network share."""
    cfg = load_network_config()
    if not cfg.get("enabled"):
        return False, "Netzwerk-Speicherort ist deaktiviert", 0

    if days is None:
        days = cfg.get("sync_days", 7)

    if not is_mounted():
        ok, msg = mount_network_share(cfg)
        if not ok:
            return False, msg, 0

    net_capture_dir = os.path.join(NETWORK_MOUNT_POINT, NETWORK_CAPTURE_SUBDIR)
    os.makedirs(net_capture_dir, exist_ok=True)

    cutoff = datetime.now() - timedelta(days=days)
    synced = 0
    errors = 0

    if os.path.isdir(CAPTURE_DIR):
        for fname in sorted(os.listdir(CAPTURE_DIR)):
            src = os.path.join(CAPTURE_DIR, fname)
            if not os.path.isfile(src):
                continue
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(src))
                if mtime < cutoff:
                    continue
                dst = os.path.join(net_capture_dir, fname)
                if os.path.exists(dst) and os.path.getsize(src) == os.path.getsize(dst):
                    continue
                shutil.copy2(src, dst)
                synced += 1
            except Exception as e:
                logger.error(f"Netzwerk-Capture-Sync-Fehler {fname}: {e}")
                errors += 1

    msg = f"{synced} Capture-Dateien synchronisiert (letzte {days} Tage)"
    if errors:
        msg += f", {errors} Fehler"
    logger.info(msg)
    return True, msg, synced


# --- Auto-Sync Background Thread ---

_sync_thread = None
_sync_running = False


def start_network_sync():
    """Start background network-share sync thread."""
    global _sync_thread, _sync_running
    if _sync_running:
        return
    _sync_running = True
    _sync_thread = threading.Thread(target=_network_sync_loop, daemon=True)
    _sync_thread.start()
    logger.info("Netzwerk-Sync gestartet")


def stop_network_sync():
    global _sync_running
    _sync_running = False
    logger.info("Netzwerk-Sync gestoppt")


def _network_sync_loop():
    """Background loop: mountet die Freigabe bei Bedarf (mit Backoff) und
    synchronisiert PDFs + Captures im konfigurierten Intervall."""
    global _sync_running
    last_sync_time = 0.0
    last_mount_attempt = 0.0

    while _sync_running:
        cfg = load_network_config()

        if not cfg.get("enabled"):
            if is_mounted():
                unmount_network_share()
            time.sleep(30)
            continue

        if not is_mounted():
            if time.time() - last_mount_attempt >= 60:
                mount_network_share(cfg)
                last_mount_attempt = time.time()
            if not is_mounted():
                time.sleep(30)
                continue

        interval_secs = cfg.get("sync_interval_minutes", 15) * 60
        if time.time() - last_sync_time >= interval_secs:
            try:
                sync_pdfs_to_network()
                sync_captures_to_network()
            except OSError as e:
                logger.error(f"Netzwerk-Sync I/O-Fehler: {e}")
                _run(["sudo", "/usr/bin/umount", "-l", NETWORK_MOUNT_POINT])
            except Exception as e:
                logger.error(f"Netzwerk-Sync Fehler: {e}")
            last_sync_time = time.time()

        time.sleep(30)
