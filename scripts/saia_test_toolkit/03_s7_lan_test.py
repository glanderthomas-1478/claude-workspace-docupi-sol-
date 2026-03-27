#!/usr/bin/env python3
"""
DocuPi 3000 - S7 Kommunikationstest über LAN (python-snap7)
============================================================
Testet die S7-Kommunikation mit der SAIA PCD2.M5 über Ethernet.
Liest gezielt die bekannten Datenbausteine aus dem MST-H10 Step 7 Projekt.

WICHTIG: Nur LESEN - es wird NICHTS auf die SPS geschrieben!

Voraussetzung: pip install python-snap7
Auf macOS: brew install snap7
Auf Linux: apt install libsnap7-dev
"""

import argparse
import json
import struct
import sys
import time
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"s7_lan_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

def log(msg, also_print=True):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{timestamp}] {msg}"
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    if also_print:
        print(line)

try:
    import snap7
    from snap7.util import get_int, get_dint, get_real, get_string, get_bool
    SNAP7_AVAILABLE = True
except ImportError:
    SNAP7_AVAILABLE = False
    print("⚠️  python-snap7 nicht installiert!")
    print("   Installation:")
    print("     macOS:  brew install snap7 && pip install python-snap7")
    print("     Linux:  apt install libsnap7-dev && pip install python-snap7")
    print("     Pi:     pip install python-snap7")

# ============================================================
# MST-H10 Datenbausteine (aus SPS-Adressliste)
# ============================================================
DB_DEFINITIONS = {
    4: {
        "name": "DB4 - Status/Prozessdaten",
        "description": "Live-Prozessdaten: Chargennummer, Phase, Temperaturen, Zeiten",
        "size": 200,  # Sicherheitsmarge
        "fields": [
            # (offset, typ, name, einheit, faktor)
            (0,  "DINT",  "Lfd_Nr",         "Chargennummer",     1),
            (4,  "INT",   "Akt_Phas_Nr",    "Aktuelle Phase",    1),
            (6,  "INT",   "SterZeitT1",     "Sterilisationszeit T1", 1, "Sek"),
            (8,  "INT",   "SterZeitT3",     "Sterilisationszeit T3", 1, "Sek"),
            (10, "INT",   "SterZeitT4",     "Sterilisationszeit T4", 1, "Sek"),
            (12, "INT",   "SterZeitT5",     "Sterilisationszeit T5", 1, "Sek"),
            (14, "INT",   "Fo_Wert_T11",    "F0-Wert T1",       0.1, "Min"),
            (16, "INT",   "Fo_Wert_T31",    "F0-Wert T3",       0.1, "Min"),
            (18, "INT",   "Fo_Wert_T41",    "F0-Wert T4",       0.1, "Min"),
            (20, "INT",   "Fo_Wert_T51",    "F0-Wert T5",       0.1, "Min"),
            (22, "INT",   "MinSterTemp",    "Min Steri-Temp",   0.1, "°C"),
            (24, "INT",   "MaxSterTemp",    "Max Steri-Temp",   0.1, "°C"),
            (26, "INT",   "LkRateVPR",      "Leckrate",         0.1, "mbar/Min"),
        ]
    },
    8: {
        "name": "DB8 - Aktives Programm",
        "description": "Aktuell geladene Programmparameter (UDT9)",
        "size": 150,
        "fields": [
            # String hat in S7 Format: max_len(1byte) + actual_len(1byte) + chars
            # Programmname: STRING[40] = Offset 0, Daten ab Offset 2, max 40 Zeichen
            (0,  "STRING[40]", "Programmname",    "Programmname",    1),
            # UDT9 beginnt nach dem String: Offset 0 + 2 + 40 = 42
            (42, "INT",  "ProgNr",          "Programmnummer",     1),
            (44, "INT",  "MantelVorBe",     "Manteltemp Vorbehandlung", 0.1, "°C"),
            (46, "INT",  "AnzEvakVorBe",    "Anz. Evakuierungen", 1),
            (48, "INT",  "VorVa_1",         "1. Vorvakuum",       1, "mbar"),
            (50, "INT",  "VorVa_2",         "2. Vorvakuum",       1, "mbar"),
            (52, "INT",  "VorVa_3",         "3. Vorvakuum",       1, "mbar"),
            (54, "INT",  "VorVa_4",         "4. Vorvakuum",       1, "mbar"),
            (56, "INT",  "DruBegr_1",       "1. Druckbegrenzung", 1, "mbar"),
            # ... weitere Felder nach Bedarf
            (68, "INT",  "BegSteri",        "SOLL Beginn Sterilisation", 0.1, "°C"),
            (70, "INT",  "MantelSteri",     "SOLL Manteltemp Steri", 0.1, "°C"),
            (72, "INT",  "Einwirkzeit",     "SOLL Haltezeit",    0.1, "Min"),
            (74, "INT",  "ArbTempEinw",     "SOLL Arbeitstemp Einwirken", 0.1, "°C"),
            (76, "INT",  "AlaTempMini",     "Alarmtemp Minimum",  0.1, "°C"),
            (78, "INT",  "AlaTempMaxi",     "Alarmtemp Maximum",  0.1, "°C"),
        ]
    },
    7: {
        "name": "DB7 - Störungen",
        "description": "Aktive Störungen und Störungshistorie",
        "size": 100,
        "fields": [
            (0,  "INT",  "AktStoerung",    "Aktive Störungsnr",  1),
            (2,  "INT",  "AnzStoerungen",  "Anzahl Störungen",   1),
        ]
    },
    9: {
        "name": "DB9 - Rezepturen",
        "description": "Alle 20 gespeicherten Sterilisationsprogramme (UDT9 Array)",
        "size": 50,  # Lesen nur Anfang zum Test
        "fields": [
            # Rezeptur[1] beginnt bei Offset 0
            (0,  "INT",  "Rezept1_ProgNr",    "Rezept 1 Programmnr", 1),
            (2,  "INT",  "Rezept1_MantelVB",  "Rezept 1 Manteltemp VB", 0.1, "°C"),
        ]
    },
}

# Analoge Eingänge (PIW = Peripheral Input Word)
ANALOG_INPUTS = {
    "AE_P1": {"address": 128, "description": "Drucksensor P1 (Kammer)", "unit": "mbar"},
    "AE_P3": {"address": 130, "description": "Drucksensor P3", "unit": "mbar"},
    "AE_P4": {"address": 132, "description": "Drucksensor P4", "unit": "mbar"},
    "AE_T1": {"address": 136, "description": "Temperatursensor T1 (Kammer)", "unit": "°C"},
    "AE_T3": {"address": 138, "description": "Temperatursensor T3", "unit": "°C"},
    "AE_T4": {"address": 140, "description": "Temperatursensor T4", "unit": "°C"},
    "AE_T5": {"address": 142, "description": "Temperatursensor T5", "unit": "°C"},
    "AE_T6": {"address": 172, "description": "Temperatursensor T6", "unit": "°C"},
}

# Merker / Trigger
MARKERS = {
    "PROZ_Sta_Ende":    {"byte": 76, "bit": 1, "description": "Prozess Start/Ende"},
    "Programm_laeuft":  {"byte": 76, "bit": 2, "description": "Programm läuft"},
    "Stoerung_aktiv":   {"byte": 51, "bit": 0, "description": "Störung aktiv"},
    "Steri_Phase":      {"byte": 132, "bit": 2, "description": "Sterilisationsphase aktiv"},
    "Phasenwechsel":    {"byte": 133, "bit": 0, "description": "Phasenwechsel erkannt"},
    "Prozessabbruch":   {"byte": 211, "bit": 0, "description": "Prozessabbruch"},
}

def read_s7_string(data, offset, max_len=40):
    """Liest einen S7 STRING aus Rohdaten."""
    if offset + 2 > len(data):
        return "(zu kurz)"
    declared_len = data[offset]
    actual_len = data[offset + 1]
    if actual_len > declared_len:
        actual_len = declared_len
    if offset + 2 + actual_len > len(data):
        return "(unvollständig)"
    try:
        return data[offset + 2:offset + 2 + actual_len].decode('latin1')
    except:
        return "(decode error)"

def read_value(data, offset, typename, factor=1):
    """Liest einen Wert aus Rohdaten basierend auf Typ."""
    try:
        if typename == "INT":
            val = struct.unpack_from('>h', data, offset)[0]
            return val * factor if factor != 1 else val
        elif typename == "DINT":
            val = struct.unpack_from('>i', data, offset)[0]
            return val * factor if factor != 1 else val
        elif typename == "REAL":
            return struct.unpack_from('>f', data, offset)[0]
        elif typename == "WORD":
            return struct.unpack_from('>H', data, offset)[0]
        elif typename == "DWORD":
            return struct.unpack_from('>I', data, offset)[0]
        elif typename == "BYTE":
            return data[offset]
        elif typename.startswith("STRING"):
            return read_s7_string(data, offset)
        else:
            return f"(unbekannter Typ: {typename})"
    except Exception as e:
        return f"(Fehler: {e})"

def find_plc_ip(subnet="192.168.0"):
    """Versucht die SPS im Netzwerk zu finden via Ping-Scan."""
    import subprocess
    import concurrent.futures

    log(f"  Scanne Subnetz {subnet}.0/24 nach erreichbaren Hosts...")
    found = []

    def ping(ip):
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '1', ip],
                capture_output=True, timeout=3
            )
            return ip if result.returncode == 0 else None
        except:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(ping, f"{subnet}.{i}"): i for i in range(1, 255)}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                found.append(result)
                log(f"  📡 Host erreichbar: {result}")

    return sorted(found, key=lambda x: int(x.split('.')[-1]))

def test_s7_connection(ip, rack=0, slot=2):
    """Versucht S7-Verbindung herzustellen und DBs zu lesen."""
    if not SNAP7_AVAILABLE:
        return None

    results = {
        "ip": ip,
        "rack": rack,
        "slot": slot,
        "connected": False,
        "cpu_info": None,
        "dbs": {},
        "analog_inputs": {},
        "markers": {},
    }

    client = snap7.client.Client()

    # Verbindungsversuch
    print(f"\n  🔗 Verbinde mit {ip} (Rack {rack}, Slot {slot})...")
    log(f"Verbindungsversuch: {ip}:{rack}:{slot}")

    try:
        client.connect(ip, rack, slot)
    except Exception as e:
        log(f"  ❌ Verbindung fehlgeschlagen: {e}")
        print(f"  ❌ Verbindung fehlgeschlagen: {e}")
        results["error"] = str(e)

        # Alternative Slots probieren
        for alt_slot in [0, 1, 3]:
            if alt_slot == slot:
                continue
            try:
                print(f"  🔄 Versuche Slot {alt_slot}...")
                client.connect(ip, rack, alt_slot)
                print(f"  ✅ Verbunden mit Slot {alt_slot}!")
                results["slot"] = alt_slot
                break
            except:
                continue
        else:
            return results

    results["connected"] = True
    print(f"  ✅ S7-Verbindung hergestellt!")
    log(f"S7-Verbindung erfolgreich: {ip}")

    # CPU Info
    try:
        cpu_state = client.get_cpu_state()
        results["cpu_info"] = {"state": cpu_state}
        print(f"  📊 CPU Status: {cpu_state}")
        log(f"CPU State: {cpu_state}")
    except Exception as e:
        log(f"  CPU Info Fehler: {e}")

    try:
        cpu_info = client.get_cpu_info()
        results["cpu_info"]["module_type"] = cpu_info.ModuleTypeName.decode().strip()
        results["cpu_info"]["serial"] = cpu_info.SerialNumber.decode().strip()
        results["cpu_info"]["module_name"] = cpu_info.ModuleName.decode().strip()
        print(f"  📊 CPU Typ:    {results['cpu_info']['module_type']}")
        print(f"  📊 CPU Name:   {results['cpu_info']['module_name']}")
        print(f"  📊 Seriennr:   {results['cpu_info']['serial']}")
        log(f"CPU Info: {results['cpu_info']}")
    except Exception as e:
        log(f"  CPU Info Detail Fehler: {e}")

    # Datenbausteine lesen
    print(f"\n  📖 Lese Datenbausteine...")
    for db_nr, db_def in DB_DEFINITIONS.items():
        try:
            data = client.db_read(db_nr, 0, db_def["size"])
            print(f"\n  ✅ {db_def['name']} ({len(data)} Bytes gelesen)")
            log(f"DB{db_nr} raw: {data.hex()}")

            db_result = {"raw_hex": data.hex(), "fields": {}}

            for field_def in db_def["fields"]:
                offset = field_def[0]
                typename = field_def[1]
                varname = field_def[2]
                description = field_def[3]
                factor = field_def[4] if len(field_def) > 4 else 1
                unit = field_def[5] if len(field_def) > 5 else ""

                value = read_value(data, offset, typename, factor)
                db_result["fields"][varname] = {
                    "value": value,
                    "description": description,
                    "unit": unit
                }

                if isinstance(value, float):
                    print(f"     {varname:25s} = {value:>10.1f} {unit:6s}  ({description})")
                else:
                    print(f"     {varname:25s} = {str(value):>10s} {unit:6s}  ({description})")

            results["dbs"][db_nr] = db_result

        except Exception as e:
            print(f"  ❌ {db_def['name']}: {e}")
            log(f"DB{db_nr} Fehler: {e}")
            results["dbs"][db_nr] = {"error": str(e)}

    # Analoge Eingänge (Peripherie-Eingänge)
    print(f"\n  📖 Lese Analoge Eingänge (PIW)...")
    for name, ai in ANALOG_INPUTS.items():
        try:
            # PE-Bereich lesen: area=0x81 (PE), start=address, size=2
            data = client.read_area(snap7.type.Areas.PE, 0, ai["address"], 2)
            raw_value = struct.unpack('>h', data)[0]
            # Rohwert: 0-27648 für 4-20mA / 0-100%
            # Skalierung noch unbekannt - Rohwert ausgeben
            print(f"     {name:10s} = {raw_value:>6d} (roh)    {ai['description']}")
            log(f"PIW {ai['address']}: {raw_value} ({name})")
            results["analog_inputs"][name] = {
                "address": ai["address"],
                "raw_value": raw_value,
                "description": ai["description"]
            }
        except Exception as e:
            print(f"     {name:10s} = ❌ {e}")
            log(f"PIW {ai['address']} Fehler: {e}")

    # Merker lesen
    print(f"\n  📖 Lese Merker/Trigger...")
    for name, mk in MARKERS.items():
        try:
            data = client.read_area(snap7.type.Areas.MK, 0, mk["byte"], 1)
            bit_value = bool(data[0] & (1 << mk["bit"]))
            status = "🟢 AN" if bit_value else "⚪ AUS"
            print(f"     {name:25s} = {status}  M{mk['byte']}.{mk['bit']}  ({mk['description']})")
            log(f"M{mk['byte']}.{mk['bit']}: {bit_value} ({name})")
            results["markers"][name] = {
                "byte": mk["byte"],
                "bit": mk["bit"],
                "value": bit_value,
                "description": mk["description"]
            }
        except Exception as e:
            print(f"     {name:25s} = ❌ {e}")
            log(f"Merker {name} Fehler: {e}")

    # Verbindung trennen
    client.disconnect()
    print(f"\n  🔌 Verbindung getrennt")
    log("Verbindung getrennt")

    return results

def main():
    parser = argparse.ArgumentParser(
        description='DocuPi 3000 - S7 LAN Kommunikationstest',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python3 03_s7_lan_test.py --ip 192.168.0.1
  python3 03_s7_lan_test.py --ip 192.168.0.1 --rack 0 --slot 2
  python3 03_s7_lan_test.py --scan 192.168.0
  python3 03_s7_lan_test.py --scan 10.0.0
        """
    )
    parser.add_argument('--ip', '-i', help='IP-Adresse der SAIA PLC')
    parser.add_argument('--rack', '-r', type=int, default=0, help='Rack-Nummer (Standard: 0)')
    parser.add_argument('--slot', '-s', type=int, default=2, help='Slot-Nummer (Standard: 2)')
    parser.add_argument('--scan', help='Subnetz scannen (z.B. 192.168.0)')

    args = parser.parse_args()

    print("=" * 60)
    print("  DocuPi 3000 - S7 LAN Kommunikationstest")
    print("=" * 60)
    print(f"  Log: {LOG_FILE}")

    if not SNAP7_AVAILABLE:
        print("\n  ❌ python-snap7 muss installiert sein!")
        print("     Bitte erst installieren (siehe oben)")
        sys.exit(1)

    print("=" * 60)

    # Netzwerk-Scan?
    if args.scan:
        print(f"\n  🔍 Scanne Subnetz {args.scan}.0/24...")
        hosts = find_plc_ip(args.scan)
        if hosts:
            print(f"\n  Erreichbare Hosts:")
            for h in hosts:
                print(f"     • {h}")

            print(f"\n  🔗 Versuche S7-Verbindung zu jedem Host...")
            all_results = {}
            for host in hosts:
                result = test_s7_connection(host, args.rack, args.slot)
                if result and result.get("connected"):
                    all_results[host] = result
                    print(f"\n  🎯 S7-Gerät gefunden: {host}")

            if not all_results:
                print(f"\n  ❌ Kein S7-Gerät im Subnetz gefunden")
                print(f"     Tipp: IP-Adresse in Step 7 HW-Konfig prüfen")
        else:
            print(f"\n  ❌ Keine Hosts im Subnetz erreichbar")
        return

    # Direkter Verbindungstest
    if not args.ip:
        print("\n  ❌ Bitte --ip oder --scan angeben!")
        parser.print_help()
        sys.exit(1)

    log(f"Start S7 Test: IP={args.ip}, Rack={args.rack}, Slot={args.slot}")

    results = test_s7_connection(args.ip, args.rack, args.slot)

    # Zusammenfassung
    print("\n" + "=" * 60)
    print("📋 ZUSAMMENFASSUNG S7 LAN Test")
    print("=" * 60)

    if results and results.get("connected"):
        print(f"\n  ✅ S7-Verbindung erfolgreich!")
        print(f"     IP:   {results['ip']}")
        print(f"     Rack: {results['rack']}, Slot: {results['slot']}")

        if results.get("cpu_info"):
            print(f"     CPU:  {results['cpu_info'].get('module_type', '?')}")

        n_dbs = sum(1 for v in results["dbs"].values() if "error" not in v)
        n_ai = len(results["analog_inputs"])
        n_mk = len(results["markers"])

        print(f"\n     Datenbausteine gelesen:  {n_dbs}/{len(DB_DEFINITIONS)}")
        print(f"     Analoge Eingänge:        {n_ai}/{len(ANALOG_INPUTS)}")
        print(f"     Merker:                  {n_mk}/{len(MARKERS)}")

        # KRINKO-relevante Werte hervorheben
        db8 = results["dbs"].get(8, {}).get("fields", {})
        if db8:
            print(f"\n  🎯 KRINKO-relevante Sollwerte (DB8):")
            for key in ["BegSteri", "Einwirkzeit", "AlaTempMini", "AlaTempMaxi"]:
                if key in db8:
                    v = db8[key]
                    print(f"     {key:25s} = {v['value']} {v['unit']}")

        print(f"\n  → Die S7-Kommunikation funktioniert!")
        print(f"  → DocuPi kann ALLE Daten direkt von der SPS lesen!")
    else:
        print(f"\n  ❌ Keine S7-Verbindung möglich")
        if results:
            print(f"     Fehler: {results.get('error', 'unbekannt')}")
        print(f"\n  Tipps:")
        print(f"     • IP-Adresse in Step 7 HW-Konfig prüfen")
        print(f"     • Rack/Slot Kombination variieren (--rack 0 --slot 0)")
        print(f"     • Firewall / Netzwerk-Switch prüfen")
        print(f"     • Ping testen: ping {args.ip or '192.168.0.1'}")

    # Ergebnis speichern
    result_file = LOG_DIR / "s7_lan_test_result.json"
    with open(result_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n  Log:      {LOG_FILE}")
    print(f"  Ergebnis: {result_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()
