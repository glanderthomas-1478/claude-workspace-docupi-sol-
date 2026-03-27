#!/usr/bin/env python3
"""
DocuPi 3000 - SAIA PCD2.M5 Test-Runner
========================================
Führt alle Tests der Reihe nach aus und erstellt einen Gesamtbericht.

Ablauf:
  1. USB-Device erkennen (01_usb_detect.py)
  2. S-Bus über USB testen (02_sbus_test.py)
  3. S7 über LAN testen (03_s7_lan_test.py)
  4. Optional: Live-Monitor starten (04_live_monitor.py)
"""

import json
import subprocess
import sys
import platform
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

def print_header(title):
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}\n")

def check_dependencies():
    """Prüft ob alle benötigten Python-Pakete installiert sind."""
    print_header("Abhängigkeiten prüfen")

    deps = {
        "serial": "pyserial",
        "snap7": "python-snap7",
    }

    missing = []
    for module, pip_name in deps.items():
        try:
            __import__(module)
            print(f"  ✅ {pip_name}")
        except ImportError:
            print(f"  ❌ {pip_name} - FEHLT")
            missing.append(pip_name)

    if missing:
        print(f"\n  Fehlende Pakete installieren:")
        print(f"    pip install {' '.join(missing)}")
        if platform.system() == "Darwin" and "python-snap7" in missing:
            print(f"    brew install snap7  (macOS: snap7 C-Library)")
        elif platform.system() == "Linux" and "python-snap7" in missing:
            print(f"    apt install libsnap7-dev  (Linux: snap7 C-Library)")
        return False

    print(f"\n  ✅ Alle Abhängigkeiten vorhanden!")
    return True

def run_script(script_name, args=None, interactive=False):
    """Führt ein Script aus und gibt das Ergebnis zurück."""
    script_path = SCRIPT_DIR / script_name
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)

    if interactive:
        # Interaktives Script direkt ausführen
        result = subprocess.run(cmd)
        return result.returncode == 0
    else:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        print(result.stdout)
        if result.stderr:
            print(f"  STDERR: {result.stderr}")
        return result.returncode == 0

def load_result(filename):
    """Lädt ein JSON-Ergebnis aus dem Log-Verzeichnis."""
    result_file = LOG_DIR / filename
    if result_file.exists():
        with open(result_file) as f:
            return json.load(f)
    return None

def main():
    print("=" * 60)
    print("  DocuPi 3000 - SAIA PCD2.M5 Komplett-Test")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  System: {platform.system()} {platform.machine()}")
    print("=" * 60)

    # 0. Abhängigkeiten prüfen
    if not check_dependencies():
        print("\n  ⚠️  Bitte erst die fehlenden Pakete installieren!")
        resp = input("\n  Trotzdem fortfahren? (j/n): ").strip().lower()
        if resp != 'j':
            sys.exit(1)

    # 1. USB Detection
    print_header("SCHRITT 1: USB-Device Erkennung")
    print("  Dieses Script erkennt das USB-Device der SAIA.\n")
    run_script("01_usb_detect.py", interactive=True)

    usb_result = load_result("usb_detect_result.json")
    usb_port = None
    if usb_result and usb_result.get("success"):
        usb_port = usb_result.get("recommended_port")
        print(f"\n  ✅ USB-Device erkannt: {usb_port}")
    else:
        print(f"\n  ❌ Kein USB-Device erkannt - S-Bus Test wird übersprungen")

    # 2. S-Bus Test (nur wenn USB-Device gefunden)
    if usb_port:
        print_header("SCHRITT 2: S-Bus Kommunikationstest über USB")
        run_script("02_sbus_test.py", args=["--port", usb_port], interactive=True)

        sbus_result = load_result("sbus_test_result.json")
        if sbus_result and sbus_result.get("success"):
            print(f"\n  ✅ S-Bus Kommunikation funktioniert!")
        else:
            print(f"\n  ❌ Keine S-Bus Kommunikation über USB")
    else:
        print_header("SCHRITT 2: S-Bus Test übersprungen (kein USB-Device)")

    # 3. S7 LAN Test
    print_header("SCHRITT 3: S7 Kommunikationstest über LAN")
    print("  Optionen:")
    print("    1) IP-Adresse direkt eingeben")
    print("    2) Subnetz scannen")
    print("    3) Überspringen")

    choice = input("\n  Auswahl (1/2/3): ").strip()

    s7_success = False
    if choice == "1":
        ip = input("  IP-Adresse der SPS: ").strip()
        if ip:
            run_script("03_s7_lan_test.py", args=["--ip", ip], interactive=True)
            s7_result = load_result("s7_lan_test_result.json")
            s7_success = s7_result and s7_result.get("connected", False)
    elif choice == "2":
        subnet = input("  Subnetz (z.B. 192.168.0): ").strip()
        if subnet:
            run_script("03_s7_lan_test.py", args=["--scan", subnet], interactive=True)

    # 4. Gesamtbericht
    print_header("GESAMTBERICHT")

    report = {
        "timestamp": datetime.now().isoformat(),
        "system": f"{platform.system()} {platform.machine()}",
        "usb_detected": bool(usb_port),
        "usb_device": usb_port,
        "sbus_works": False,
        "s7_lan_works": s7_success,
    }

    sbus_result = load_result("sbus_test_result.json")
    if sbus_result:
        report["sbus_works"] = sbus_result.get("success", False)

    print(f"  USB-Device erkannt:     {'✅ ' + (usb_port or '') if usb_port else '❌'}")
    print(f"  S-Bus über USB:         {'✅' if report['sbus_works'] else '❌'}")
    print(f"  S7 über LAN:            {'✅' if report['s7_lan_works'] else '❌'}")

    print(f"\n  {'─' * 50}")

    if report["s7_lan_works"]:
        print(f"\n  🎯 EMPFEHLUNG: S7 über LAN nutzen!")
        print(f"     python-snap7 funktioniert und liefert alle Daten.")
        if report["sbus_works"]:
            print(f"     S-Bus über USB funktioniert auch als Alternative.")
    elif report["sbus_works"]:
        print(f"\n  🎯 EMPFEHLUNG: S-Bus über USB nutzen!")
        print(f"     Eigenen S-Bus Treiber für DocuPi entwickeln.")
    elif usb_port:
        print(f"\n  ⚠️  USB-Device erkannt aber kein Protokoll funktioniert.")
        print(f"     Möglichkeiten:")
        print(f"       • S7 über LAN als Hauptweg nutzen")
        print(f"       • USB-Protokoll weiter analysieren (Wireshark/Logic Analyzer)")
    else:
        print(f"\n  ⚠️  Weder USB noch LAN hat funktioniert.")
        print(f"     Nächste Schritte:")
        print(f"       • USB-Kabel prüfen (Daten, nicht nur Ladung)")
        print(f"       • SAIA USB-Port in PCD-Konfig aktiviert?")
        print(f"       • LAN: IP-Adresse in Step 7 HW-Config prüfen")

    # Optional: Live-Monitor starten?
    if report["s7_lan_works"]:
        print(f"\n  {'─' * 50}")
        resp = input("\n  Live-Monitor starten? (j/n): ").strip().lower()
        if resp == 'j':
            s7_result = load_result("s7_lan_test_result.json")
            ip = s7_result.get("ip", "")
            if ip:
                run_script("04_live_monitor.py", args=["--ip", ip], interactive=True)

    # Bericht speichern
    report_file = LOG_DIR / "test_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n  Gesamtbericht: {report_file}")
    print(f"  Alle Logs:     {LOG_DIR}/")
    print("=" * 60)

if __name__ == "__main__":
    main()
