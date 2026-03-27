#!/usr/bin/env python3
"""
DocuPi 3000 - SAIA PCD2.M5 USB Device Detection
=================================================
Dieses Script erkennt neue USB-Geräte wenn die SAIA angesteckt wird.

Ablauf:
1. Snapshot aller aktuellen USB/Serial-Devices
2. Warten bis SAIA angesteckt wird
3. Vergleich und Ausgabe des neuen Devices

Funktioniert auf macOS und Linux (Raspberry Pi).
"""

import subprocess
import sys
import time
import platform
import glob
import json
from datetime import datetime
from pathlib import Path

# Log-Datei
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"usb_detect_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

def log(msg, also_print=True):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{timestamp}] {msg}"
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    if also_print:
        print(line)

def get_serial_devices():
    """Findet alle seriellen Devices (macOS + Linux)."""
    devices = set()

    # Linux: /dev/ttyUSB*, /dev/ttyACM*, /dev/ttyS*
    for pattern in ['/dev/ttyUSB*', '/dev/ttyACM*', '/dev/ttyS*', '/dev/ttyAMA*']:
        devices.update(glob.glob(pattern))

    # macOS: /dev/tty.usb*, /dev/cu.usb*, /dev/tty.usbmodem*, /dev/tty.SLAB*
    for pattern in ['/dev/tty.usb*', '/dev/cu.usb*', '/dev/tty.SLAB*', '/dev/cu.SLAB*',
                    '/dev/tty.wch*', '/dev/cu.wch*']:
        devices.update(glob.glob(pattern))

    return devices

def get_usb_devices():
    """Listet USB-Geräte auf (system_profiler auf macOS, lsusb auf Linux)."""
    system = platform.system()
    devices = []

    if system == "Darwin":  # macOS
        try:
            result = subprocess.run(
                ['system_profiler', 'SPUSBDataType', '-json'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                devices = _parse_macos_usb(data)
        except Exception as e:
            log(f"  system_profiler Fehler: {e}")
            # Fallback ohne JSON
            try:
                result = subprocess.run(
                    ['system_profiler', 'SPUSBDataType'],
                    capture_output=True, text=True, timeout=10
                )
                devices = [result.stdout]
            except:
                pass
    else:  # Linux
        try:
            result = subprocess.run(
                ['lsusb'], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                devices = result.stdout.strip().split('\n')
        except FileNotFoundError:
            log("  lsusb nicht installiert - versuche /sys/bus/usb/devices/")
            try:
                for d in Path('/sys/bus/usb/devices/').iterdir():
                    product_file = d / 'product'
                    if product_file.exists():
                        product = product_file.read_text().strip()
                        vendor_file = d / 'manufacturer'
                        vendor = vendor_file.read_text().strip() if vendor_file.exists() else "?"
                        devices.append(f"{vendor}: {product}")
            except:
                pass

    return devices

def _parse_macos_usb(data, depth=0):
    """Rekursiv USB-Geräte aus system_profiler JSON extrahieren."""
    devices = []
    if isinstance(data, dict):
        for key, val in data.items():
            if key == '_items':
                for item in val:
                    name = item.get('_name', 'Unknown')
                    vendor_id = item.get('vendor_id', '')
                    product_id = item.get('product_id', '')
                    serial = item.get('serial_num', '')
                    manufacturer = item.get('manufacturer', '')
                    info = f"{name} (Vendor: {vendor_id}, Product: {product_id}"
                    if manufacturer:
                        info += f", Hersteller: {manufacturer}"
                    if serial:
                        info += f", Serial: {serial}"
                    info += ")"
                    devices.append(info)
                    # Rekursiv nach Sub-Devices suchen
                    devices.extend(_parse_macos_usb(item, depth+1))
            elif isinstance(val, (dict, list)):
                devices.extend(_parse_macos_usb(val, depth+1))
    elif isinstance(data, list):
        for item in data:
            devices.extend(_parse_macos_usb(item, depth+1))
    return devices

def get_device_details(device_path):
    """Holt Details zu einem seriellen Device."""
    details = {"path": device_path}
    system = platform.system()

    if system == "Linux":
        # udevadm Infos holen
        try:
            result = subprocess.run(
                ['udevadm', 'info', '--query=all', '--name=' + device_path],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'ID_VENDOR=' in line:
                        details['vendor'] = line.split('=', 1)[1]
                    elif 'ID_MODEL=' in line:
                        details['model'] = line.split('=', 1)[1]
                    elif 'ID_SERIAL=' in line:
                        details['serial'] = line.split('=', 1)[1]
                    elif 'ID_USB_DRIVER=' in line:
                        details['driver'] = line.split('=', 1)[1]
        except:
            pass

    elif system == "Darwin":
        # Auf macOS den Device-Namen parsen
        # tty.usbserial-XXXX oder tty.usbmodemXXXX
        details['type'] = 'USB-Serial' if 'serial' in device_path else 'USB-Modem'

    return details

def check_dmesg_for_usb():
    """Prüft dmesg auf USB-bezogene Meldungen (nur Linux)."""
    if platform.system() != "Linux":
        return []
    try:
        result = subprocess.run(
            ['dmesg', '--time-format=reltime'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            # Letzte 20 USB-bezogene Meldungen
            usb_lines = [l for l in lines if 'usb' in l.lower() or 'tty' in l.lower()]
            return usb_lines[-20:]
    except:
        pass
    return []

def main():
    print("=" * 60)
    print("  DocuPi 3000 - SAIA PCD2.M5 USB-Erkennung")
    print("=" * 60)
    print(f"  System: {platform.system()} {platform.machine()}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Log:    {LOG_FILE}")
    print("=" * 60)

    log(f"System: {platform.system()} {platform.machine()}")

    # Phase 1: Snapshot VORHER
    print("\n📸 Phase 1: Aktuellen Zustand aufnehmen...")
    print("   (SAIA sollte NICHT angeschlossen sein)\n")

    input("   → Enter drücken wenn bereit...")

    serial_before = get_serial_devices()
    usb_before = get_usb_devices()

    log(f"Serielle Devices vorher: {serial_before}")
    log(f"USB Devices vorher: {len(usb_before)} Geräte")

    print(f"\n   Serielle Devices gefunden: {len(serial_before)}")
    for d in sorted(serial_before):
        print(f"     • {d}")

    print(f"\n   USB-Geräte gefunden: {len(usb_before)}")
    for d in usb_before:
        print(f"     • {d}")

    # Phase 2: SAIA anstecken
    print("\n" + "=" * 60)
    print("🔌 Phase 2: Jetzt die SAIA per USB anschließen!")
    print("=" * 60)

    input("\n   → USB-Kabel einstecken und Enter drücken...")

    # Kurz warten damit das System das Device registriert
    print("\n   Warte 3 Sekunden auf Device-Registrierung...")
    time.sleep(3)

    # Phase 3: Snapshot NACHHER
    print("\n🔍 Phase 3: Neue Devices suchen...\n")

    serial_after = get_serial_devices()
    usb_after = get_usb_devices()

    log(f"Serielle Devices nachher: {serial_after}")
    log(f"USB Devices nachher: {len(usb_after)} Geräte")

    # Vergleich: Serielle Devices
    new_serial = serial_after - serial_before

    print("   SERIELLE SCHNITTSTELLEN:")
    if new_serial:
        print(f"   ✅ {len(new_serial)} neue(s) Device(s) gefunden!")
        for dev in sorted(new_serial):
            print(f"\n   🎯 NEUES DEVICE: {dev}")
            details = get_device_details(dev)
            for key, val in details.items():
                if key != 'path':
                    print(f"      {key}: {val}")
            log(f"NEUES SERIELLES DEVICE: {dev} - Details: {details}")
    else:
        print("   ❌ Kein neues serielles Device erkannt")
        log("KEIN neues serielles Device gefunden")

    # Vergleich: USB Devices
    new_usb = set(usb_after) - set(usb_before)

    print(f"\n   USB-GERÄTE:")
    if new_usb:
        print(f"   ✅ {len(new_usb)} neue(s) USB-Gerät(e)!")
        for dev in new_usb:
            print(f"   🎯 NEU: {dev}")
            log(f"NEUES USB DEVICE: {dev}")
    else:
        print("   ❌ Kein neues USB-Gerät erkannt")

    # Linux: dmesg prüfen
    if platform.system() == "Linux":
        print(f"\n   KERNEL-MELDUNGEN (dmesg):")
        dmesg_lines = check_dmesg_for_usb()
        if dmesg_lines:
            for line in dmesg_lines[-10:]:
                print(f"     {line}")
                log(f"dmesg: {line}")

    # Zusammenfassung
    print("\n" + "=" * 60)
    print("📋 ZUSAMMENFASSUNG")
    print("=" * 60)

    result = {
        "system": platform.system(),
        "machine": platform.machine(),
        "serial_before": list(serial_before),
        "serial_after": list(serial_after),
        "new_serial_devices": list(new_serial),
        "usb_before_count": len(usb_before),
        "usb_after_count": len(usb_after),
        "new_usb_devices": list(new_usb),
        "timestamp": datetime.now().isoformat()
    }

    if new_serial:
        device = sorted(new_serial)[0]
        print(f"\n   ✅ SAIA erkannt als: {device}")
        print(f"\n   → Nächster Schritt: Script 02_sbus_test.py ausführen mit:")
        print(f"     python3 02_sbus_test.py --port {device}")
        result["recommended_port"] = device
        result["success"] = True
    else:
        print(f"\n   ❌ Kein serielles Device erkannt.")
        print(f"\n   Mögliche Ursachen:")
        print(f"     • USB-Kabel ist nur ein Ladekabel (kein Datenkabel)")
        print(f"     • SAIA USB-Port ist nicht aktiviert")
        print(f"     • Treiber fehlt (SAIA nutzt oft FTDI oder CH340)")
        if platform.system() == "Darwin":
            print(f"\n   macOS Treiber-Tipp:")
            print(f"     • FTDI: brew install --cask ftdi-vcp-driver")
            print(f"     • CH340: brew install --cask wch-ch34x-usb-serial-driver")
        result["success"] = False

    # Ergebnis als JSON speichern
    result_file = LOG_DIR / "usb_detect_result.json"
    with open(result_file, "w") as f:
        json.dump(result, f, indent=2, default=str)
    log(f"Ergebnis gespeichert: {result_file}")

    print(f"\n   Log gespeichert: {LOG_FILE}")
    print(f"   Ergebnis JSON:   {result_file}")
    print("=" * 60)

    return result

if __name__ == "__main__":
    main()
