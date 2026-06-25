"""
DocuPi-3000 Storage Manager
- USB auto-detection & mount/unmount
- Auto-sync last N days of PDFs from SD to USB
- USB formatting (FAT32)
- File browser (dual-pane: SD + USB)
"""

import os
import subprocess
import shutil
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("docupi.storage")

# Paths
SD_PDF_DIR = "/home/docucontrol/docupi/data/pdfs"
USB_MOUNT_POINT = "/media/usbstick"
USB_PDF_SUBDIR = "DocuControl"  # Subfolder on USB for PDFs
USB_CAPTURE_SUBDIR = "docucontrol/captures"  # Subfolder on USB for raw captures
SYNC_CONFIG_FILE = "/home/docucontrol/docupi/data/sync_config.json"

DEFAULT_SYNC_CONFIG = {
    "auto_sync_enabled": True,
    "sync_days": 7,
    "sync_interval_minutes": 15,
    "last_sync": None,
    "last_sync_count": 0
}


def _run(cmd, timeout=30):
    """Run shell command, return (success, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "timeout"
    except Exception as e:
        return False, "", str(e)


# --- Sync Config ---

def load_sync_config():
    if os.path.exists(SYNC_CONFIG_FILE):
        try:
            with open(SYNC_CONFIG_FILE, "r") as f:
                saved = json.load(f)
                config = dict(DEFAULT_SYNC_CONFIG)
                config.update(saved)
                return config
        except:
            pass
    return dict(DEFAULT_SYNC_CONFIG)


def save_sync_config(config):
    os.makedirs(os.path.dirname(SYNC_CONFIG_FILE), exist_ok=True)
    with open(SYNC_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


# --- USB Detection & Mount ---

def _mountpoint_source(mountpoint):
    """Liefert das tatsaechlich an `mountpoint` angehaengte Geraet (z.B. /dev/sda1),
    oder None falls nichts dort gemountet ist. Im Gegensatz zu os.path.ismount()
    prueft das nicht nur "ist da irgendein Mount", sondern welches Geraet dahinter
    steckt — wichtig nach USB-Re-Enumeration (Stick wird nach Abziehen/Einstecken
    oft unter einem neuen Geraetenamen registriert, z.B. sda1 -> sdb1), wo sonst ein
    verwaister Mount des alten, nicht mehr existierenden Geraetenamens faelschlich
    als "USB ist da" durchgeht."""
    try:
        with open("/proc/mounts") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == mountpoint:
                    return parts[0]
    except Exception:
        pass
    return None


def detect_usb_device():
    """Find USB block device (not mmcblk = SD card)."""
    ok, out, _ = _run("lsblk -rno NAME,TYPE,RM,MOUNTPOINT | grep 'part 1'")
    if not ok:
        return None
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            name = parts[0]
            if not name.startswith("mmcblk") and not name.startswith("zram") and not name.startswith("loop"):
                return f"/dev/{name}"
    return None


def get_usb_info():
    """Get USB device info."""
    dev = detect_usb_device()
    if not dev:
        # Kein Geraet (mehr) da — falls noch ein verwaister Mount eines bereits
        # abgezogenen Sticks haengt, jetzt aushaengen statt ihn liegen zu lassen
        if _mountpoint_source(USB_MOUNT_POINT):
            logger.warning(f"Verwaister USB-Mount an {USB_MOUNT_POINT} ohne Geraet - haenge aus")
            _run(f"sudo /usr/bin/umount -l {USB_MOUNT_POINT}")
        return {"detected": False}

    info = {"detected": True, "device": dev, "fstype": "", "label": "", "size": "", "mounted": False, "mount_point": ""}

    # blkid for filesystem info
    ok, out, _ = _run(f"sudo /usr/sbin/blkid {dev}")
    if ok:
        import re
        m = re.search(r'TYPE="([^"]*)"', out)
        if m: info["fstype"] = "FAT32" if m.group(1) == "vfat" else m.group(1).upper()
        m = re.search(r'LABEL="([^"]*)"', out)
        if m: info["label"] = m.group(1)

    # Size
    ok, out, _ = _run(f"lsblk -rno SIZE {dev}")
    if ok: info["size"] = out.strip()

    # Mount status
    ok, out, _ = _run(f"findmnt -rno TARGET {dev}")
    if ok and out.strip():
        info["mounted"] = True
        info["mount_point"] = out.strip().splitlines()[0]
    else:
        mounted_src = _mountpoint_source(USB_MOUNT_POINT)
        if mounted_src and os.path.realpath(mounted_src) == os.path.realpath(dev):
            info["mounted"] = True
            info["mount_point"] = USB_MOUNT_POINT
        elif mounted_src:
            # Mountpoint zeigt noch auf ein altes Geraet (z.B. sda1 nach Abziehen),
            # das aktuell erkannte ist aber ein anderes (z.B. sdb1 nach Neueinstecken)
            logger.warning(f"Verwaister USB-Mount an {USB_MOUNT_POINT} ({mounted_src} statt {dev}) - haenge aus")
            _run(f"sudo /usr/bin/umount -l {USB_MOUNT_POINT}")

    # Usage if mounted
    if info["mounted"] and info["mount_point"]:
        try:
            s = shutil.disk_usage(info["mount_point"])
            info["total_gb"] = round(s.total / (1024**3), 1)
            info["free_gb"] = round(s.free / (1024**3), 1)
            info["used_percent"] = round(s.used / s.total * 100) if s.total else 0
        except:
            pass

    return info


def mount_usb():
    """Mount USB device to USB_MOUNT_POINT."""
    dev = detect_usb_device()
    if not dev:
        return False, "Kein USB-Geraet gefunden"

    mounted_src = _mountpoint_source(USB_MOUNT_POINT)
    if mounted_src and os.path.realpath(mounted_src) == os.path.realpath(dev):
        return True, "USB bereits gemountet"
    if mounted_src:
        # Verwaister Mount eines alten/entfernten Geraets (Re-Enumeration) - erst aushaengen
        logger.warning(f"Verwaister USB-Mount erkannt ({mounted_src} statt {dev}) - haenge aus")
        _run(f"sudo /usr/bin/umount -l {USB_MOUNT_POINT}")
        time.sleep(1)

    _run("sudo /usr/bin/mkdir -p " + USB_MOUNT_POINT)

    # fsck vor Mount (repariert FAT-Fehler nach Stromausfall)
    fsck_ok, fsck_out, fsck_err = _run(f"sudo /usr/sbin/dosfsck -a -w {dev}")
    if fsck_ok:
        logger.info(f"USB fsck OK: {dev}")
    else:
        logger.warning(f"USB fsck Warnung: {fsck_err or fsck_out}")

    # Mount mit sync-Option (Daten sofort auf Stick schreiben, sicherer bei Stromausfall)
    ok, out, err = _run(f"sudo /usr/bin/mount -o uid=1000,gid=1000,umask=022,sync,flush {dev} {USB_MOUNT_POINT}")
    if not ok:
        ok, out, err = _run(f"sudo /usr/bin/mount {dev} {USB_MOUNT_POINT}")

    if ok:
        pdf_dir = os.path.join(USB_MOUNT_POINT, USB_PDF_SUBDIR)
        os.makedirs(pdf_dir, exist_ok=True)
        logger.info(f"USB gemountet: {dev} -> {USB_MOUNT_POINT}")
        return True, f"USB gemountet ({dev})"
    else:
        return False, f"Mount fehlgeschlagen: {err}"


def try_mount_usb_on_boot():
    """USB-Stick beim Boot mounten (nach Stromausfall/Reboot).
    udev-Rules feuern nur bei physischem Einstecken, nicht beim Boot."""
    dev = detect_usb_device()
    if dev:
        logger.info(f"USB-Geraet {dev} gefunden beim Boot - versuche Mount")
        ok, msg = mount_usb()
        if ok:
            logger.info(f"USB Boot-Mount erfolgreich: {msg}")
        else:
            logger.warning(f"USB Boot-Mount fehlgeschlagen: {msg}")
        return ok
    else:
        logger.info("Kein USB-Geraet beim Boot erkannt")
        return False


def unmount_usb():
    """Safely unmount USB."""
    if not os.path.ismount(USB_MOUNT_POINT):
        return True, "USB nicht gemountet"

    _run("sync")
    ok, _, err = _run(f"sudo /usr/bin/umount {USB_MOUNT_POINT}")
    if ok:
        logger.info("USB sicher ausgeworfen")
        return True, "USB sicher ausgeworfen"
    else:
        ok2, _, err2 = _run(f"sudo /usr/bin/umount -l {USB_MOUNT_POINT}")
        if ok2:
            return True, "USB ausgeworfen (lazy unmount)"
        return False, f"Unmount fehlgeschlagen: {err}"


# --- USB Formatting ---

def format_usb_fat32(label="DOCUCTRL"):
    """Format USB device as FAT32. DESTRUCTIVE!"""
    dev = detect_usb_device()
    if not dev:
        return False, "Kein USB-Geraet gefunden"

    if os.path.ismount(USB_MOUNT_POINT):
        ok, msg = unmount_usb()
        if not ok:
            return False, f"Konnte USB nicht unmounten: {msg}"

    _run(f"sudo /usr/bin/umount {dev} 2>/dev/null")

    label = label[:11].upper().replace(" ", "_")
    ok, out, err = _run(f"sudo /usr/sbin/mkfs.vfat -F 32 -n {label} {dev}", timeout=120)
    if ok:
        logger.info(f"USB formatiert als FAT32: {dev} Label={label}")
        # Wait for kernel to re-detect partition after format
        time.sleep(3)
        # Retry mount up to 3 times
        mount_msg = "Mount ausstehend"
        for attempt in range(3):
            mount_ok, mount_msg = mount_usb()
            if mount_ok:
                break
            time.sleep(2)
        return True, f"USB als FAT32 formatiert (Label: {label}). {mount_msg}"
    else:
        return False, f"Formatierung fehlgeschlagen: {err}"


# --- File Browser ---

def list_files(base_path, rel_path=""):
    """List files and directories for file browser."""
    full_path = os.path.join(base_path, rel_path) if rel_path else base_path

    real_base = os.path.realpath(base_path)
    real_path = os.path.realpath(full_path)
    if not real_path.startswith(real_base):
        return {"error": "Zugriff verweigert", "files": [], "dirs": []}

    if not os.path.isdir(real_path):
        return {"error": "Verzeichnis nicht gefunden", "files": [], "dirs": []}

    items = {"path": rel_path, "base": base_path, "files": [], "dirs": [], "error": None}

    try:
        entries = sorted(os.listdir(real_path))
        for name in entries:
            if name.startswith("."):
                continue
            fp = os.path.join(real_path, name)
            try:
                stat = os.stat(fp)
            except:
                continue
            entry = {
                "name": name,
                "path": os.path.join(rel_path, name) if rel_path else name,
                "size": stat.st_size,
                "size_human": _human_size(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M"),
                "modified_ts": stat.st_mtime
            }
            if os.path.isdir(fp):
                try:
                    entry["count"] = len([x for x in os.listdir(fp) if not x.startswith(".")])
                except:
                    entry["count"] = 0
                items["dirs"].append(entry)
            else:
                entry["ext"] = os.path.splitext(name)[1].lower()
                items["files"].append(entry)
    except PermissionError:
        items["error"] = "Keine Berechtigung"

    return items


def _human_size(nbytes):
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(nbytes) < 1024:
            return f"{nbytes:.1f} {unit}" if unit != "B" else f"{nbytes} B"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"


def get_storage_stats():
    """Get storage statistics for SD and USB."""
    stats = {"sd": {}, "usb": {}}

    try:
        s = shutil.disk_usage(SD_PDF_DIR)
        stats["sd"]["total_gb"] = round(s.total / (1024**3), 1)
        stats["sd"]["free_gb"] = round(s.free / (1024**3), 1)
        stats["sd"]["used_percent"] = round(s.used / s.total * 100)
    except:
        stats["sd"]["total_gb"] = 0
        stats["sd"]["free_gb"] = 0
        stats["sd"]["used_percent"] = 0

    pdf_count = 0
    pdf_size = 0
    for root, dirs, files in os.walk(SD_PDF_DIR):
        for f in files:
            if f.lower().endswith(".pdf"):
                pdf_count += 1
                pdf_size += os.path.getsize(os.path.join(root, f))
    stats["sd"]["pdf_count"] = pdf_count
    stats["sd"]["pdf_size_human"] = _human_size(pdf_size)

    usb_info = get_usb_info()
    stats["usb"] = usb_info

    if usb_info.get("mounted") and usb_info.get("mount_point"):
        usb_pdf_dir = os.path.join(usb_info["mount_point"], USB_PDF_SUBDIR)
        usb_pdf_count = 0
        usb_pdf_size = 0
        if os.path.isdir(usb_pdf_dir):
            for root, dirs, files in os.walk(usb_pdf_dir):
                for f in files:
                    if f.lower().endswith(".pdf"):
                        usb_pdf_count += 1
                        usb_pdf_size += os.path.getsize(os.path.join(root, f))
        stats["usb"]["pdf_count"] = usb_pdf_count
        stats["usb"]["pdf_size_human"] = _human_size(usb_pdf_size)

    return stats


# --- Sync Engine ---

def sync_pdfs_to_usb(days=None):
    """Sync PDFs from last N days from SD to USB stick."""
    config = load_sync_config()
    if days is None:
        days = config.get("sync_days", 7)

    if not get_usb_info().get("mounted"):
        ok, msg = mount_usb()
        if not ok:
            return False, msg, 0

    usb_pdf_dir = os.path.join(USB_MOUNT_POINT, USB_PDF_SUBDIR)
    os.makedirs(usb_pdf_dir, exist_ok=True)

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
                dst = os.path.join(usb_pdf_dir, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.exists(dst):
                    if os.path.getsize(src) == os.path.getsize(dst) and \
                       os.path.getmtime(src) <= os.path.getmtime(dst):
                        continue
                shutil.copy2(src, dst)
                synced += 1
            except Exception as e:
                logger.error(f"Sync-Fehler {fname}: {e}")
                errors += 1

    _run("sync")

    config["last_sync"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    config["last_sync_count"] = synced
    save_sync_config(config)

    msg = f"{synced} PDFs synchronisiert (letzte {days} Tage)"
    if errors:
        msg += f", {errors} Fehler"
    logger.info(msg)
    return True, msg, synced



def sync_captures_to_usb(days=None):
    """Sync raw capture files from last N days from SD to USB stick."""
    config = load_sync_config()
    if days is None:
        days = config.get("sync_days", 7)

    if not get_usb_info().get("mounted"):
        ok, msg = mount_usb()
        if not ok:
            return False, msg, 0

    capture_dir = "/home/docucontrol/docupi/data/raw_captures"
    usb_capture_dir = os.path.join(USB_MOUNT_POINT, USB_CAPTURE_SUBDIR)
    os.makedirs(usb_capture_dir, exist_ok=True)

    cutoff = datetime.now() - timedelta(days=days)
    synced = 0
    errors = 0

    if os.path.isdir(capture_dir):
        for fname in sorted(os.listdir(capture_dir)):
            src = os.path.join(capture_dir, fname)
            if not os.path.isfile(src):
                continue
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(src))
                if mtime < cutoff:
                    continue
                dst = os.path.join(usb_capture_dir, fname)
                if os.path.exists(dst) and os.path.getsize(src) == os.path.getsize(dst):
                    continue
                shutil.copy2(src, dst)
                synced += 1
            except Exception as e:
                logger.error(f"Captures-Sync Fehler {fname}: {e}")
                errors += 1

    msg = f"{synced} Capture-Dateien synchronisiert (letzte {days} Tage)"
    if errors:
        msg += f", {errors} Fehler"
    logger.info(msg)
    return True, msg, synced


# --- Auto-Sync Background Thread ---

USB_TRIGGER_FILE = "/var/lib/docucontrol/usb.trigger"

_sync_thread = None
_sync_running = False


def start_auto_sync():
    """Start background auto-sync thread."""
    global _sync_thread, _sync_running
    if _sync_running:
        return
    _sync_running = True
    _sync_thread = threading.Thread(target=_auto_sync_loop, daemon=True)
    _sync_thread.start()
    logger.info("Auto-Sync gestartet")


def stop_auto_sync():
    """Stop background auto-sync."""
    global _sync_running
    _sync_running = False
    logger.info("Auto-Sync gestoppt")


def _auto_sync_loop():
    """Background loop: erkennt USB-Einstecken via Trigger-Datei (sofort)
    und laeuft regelmaessigen Sync auf konfiguriertem Intervall."""
    global _sync_running
    last_sync_time = 0.0
    was_mounted = get_usb_info().get("mounted", False)

    while _sync_running:
        config = load_sync_config()
        auto_enabled = config.get("auto_sync_enabled", True)
        interval_secs = config.get("sync_interval_minutes", 15) * 60

        # Trigger-Datei: udev schreibt sie beim Einstecken
        trigger_fired = False
        if os.path.exists(USB_TRIGGER_FILE):
            try:
                content = open(USB_TRIGGER_FILE).read().strip()
                os.remove(USB_TRIGGER_FILE)
                if content != "removed":
                    trigger_fired = True
                    logger.info(f"USB-Trigger empfangen: {content} - warte auf Settle")
                    time.sleep(3)  # Geraet einpendeln lassen
            except Exception:
                pass

        usb = get_usb_info()
        now_mounted = usb.get("mounted", False)

        # Neu eingesteckt (Trigger oder Zustandsaenderung)
        newly_inserted = trigger_fired or (usb.get("detected") and not was_mounted)

        if usb.get("detected") and not now_mounted:
            ok, msg = mount_usb()
            if ok:
                now_mounted = True
                newly_inserted = True
                logger.info(f"USB auto-gemountet: {msg}")
            else:
                logger.warning(f"USB Auto-Mount fehlgeschlagen: {msg}")

        if now_mounted and auto_enabled:
            should_sync = newly_inserted or ((time.time() - last_sync_time) >= interval_secs)
            if should_sync:
                try:
                    ok, msg, count = sync_pdfs_to_usb()
                    try:
                        sync_captures_to_usb()
                    except Exception as e:
                        logger.error(f"Captures Auto-Sync Fehler: {e}")
                    last_sync_time = time.time()
                    if newly_inserted:
                        logger.info(f"USB Sofort-Sync nach Einstecken: {msg}")
                    else:
                        logger.info(f"USB Intervall-Sync: {msg}")
                except OSError as e:
                    if e.errno == 5:
                        logger.warning(f"USB I/O-Fehler, remounte: {e}")
                        _run(f"sudo /usr/bin/umount -l {USB_MOUNT_POINT}")
                        now_mounted = False
                        was_mounted = False
                        time.sleep(10)  # Kernel nach Lazy-Unmount einpendeln lassen
                    else:
                        logger.error(f"Auto-Sync Fehler: {e}")
                except Exception as e:
                    logger.error(f"Auto-Sync Fehler: {e}")

        was_mounted = now_mounted
        time.sleep(5)


def delete_file(base_path, rel_path):
    """Delete a file with security check."""
    full_path = os.path.join(base_path, rel_path)
    real_base = os.path.realpath(base_path)
    real_path = os.path.realpath(full_path)
    if not real_path.startswith(real_base):
        return False, "Zugriff verweigert"
    if not os.path.isfile(real_path):
        return False, "Datei nicht gefunden"
    try:
        os.remove(real_path)
        return True, "Datei geloescht"
    except Exception as e:
        return False, str(e)


def delete_directory(base_path, rel_path):
    """Delete a directory with security check."""
    full_path = os.path.join(base_path, rel_path)
    real_base = os.path.realpath(base_path)
    real_path = os.path.realpath(full_path)
    if not real_path.startswith(real_base):
        return False, "Zugriff verweigert"
    if not os.path.isdir(real_path):
        return False, "Verzeichnis nicht gefunden"
    try:
        shutil.rmtree(real_path)
        return True, "Verzeichnis geloescht"
    except Exception as e:
        return False, str(e)


def copy_file(src_base, src_rel, dst_base, dst_rel=""):
    """Copy file between SD and USB."""
    src = os.path.join(src_base, src_rel)
    if dst_rel:
        dst = os.path.join(dst_base, dst_rel)
    else:
        dst = os.path.join(dst_base, os.path.basename(src_rel))
    for base, path in [(src_base, src), (dst_base, dst)]:
        if not os.path.realpath(path).startswith(os.path.realpath(base)):
            return False, "Zugriff verweigert"
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        return True, f"Kopiert: {os.path.basename(src)}"
    except Exception as e:
        return False, str(e)



def copy_pdf_to_usb_instant(pdf_path, pdf_filename):
    """Kopiert ein frisch erzeugtes PDF sofort auf den USB-Stick.
    Wird nach jeder neuen Charge aufgerufen, damit der Kunde
    den Stick direkt nach der Charge ziehen kann."""
    if not get_usb_info().get("mounted"):
        dev = detect_usb_device()
        if not dev:
            return  # Kein Stick eingesteckt
        ok, msg = mount_usb()
        if not ok:
            logger.warning(f"USB Sofortkopie: Mount fehlgeschlagen: {msg}")
            return

    usb_pdf_dir = os.path.join(USB_MOUNT_POINT, USB_PDF_SUBDIR)
    os.makedirs(usb_pdf_dir, exist_ok=True)

    # Unterordner-Struktur beibehalten (relativ zum SD-PDF-Dir)
    if SD_PDF_DIR in pdf_path:
        rel = os.path.relpath(pdf_path, SD_PDF_DIR)
        dst = os.path.join(usb_pdf_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
    else:
        dst = os.path.join(usb_pdf_dir, pdf_filename)

    shutil.copy2(pdf_path, dst)
    _run("sync")
    logger.info(f"USB Sofortkopie: {pdf_filename}")


# Init
os.makedirs(SD_PDF_DIR, exist_ok=True)
