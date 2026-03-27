#!/usr/bin/env python3
"""
DocuPi 3000 - SAIA S-Bus Kommunikationstest über USB-Serial
============================================================
Testet verschiedene S-Bus Telegramm-Formate und Baudraten
um herauszufinden ob die SAIA über USB S-Bus spricht.

S-Bus Data Mode (S2) Protokoll:
- Request:  [Station][Cmd][Count][AddrHi][AddrLo]...CRC
- Response: [Station][Cmd][Data...]...CRC

Referenz: SAIA S-Bus Handbuch Kapitel 3 (Data Mode)
"""

import argparse
import json
import serial
import struct
import sys
import time
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"sbus_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

def log(msg, also_print=True):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{timestamp}] {msg}"
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    if also_print:
        print(line)

# ============================================================
# S-Bus CRC-16 Berechnung (CCITT mit Polynom 0x1021)
# ============================================================
def sbus_crc16(data):
    """CRC-16/CCITT für S-Bus Telegramme."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            crc &= 0xFFFF
    return crc

def build_sbus_request(station, command, data=b''):
    """Baut ein S-Bus Telegramm mit CRC."""
    telegram = bytes([station, command]) + data
    crc = sbus_crc16(telegram)
    telegram += struct.pack('>H', crc)  # CRC Big Endian
    return telegram

# ============================================================
# S-Bus Kommandos (Data Mode S2)
# ============================================================
SBUS_COMMANDS = {
    "Read Register": {
        "cmd": 0x00,
        "description": "Liest Register (32-bit Werte)",
        "data": struct.pack('>BH', 1, 0),  # Count=1, StartAddr=0
    },
    "Read Flag": {
        "cmd": 0x02,
        "description": "Liest Flags/Merker (Boolean)",
        "data": struct.pack('>BH', 8, 0),  # Count=8, StartAddr=0
    },
    "Read Timer": {
        "cmd": 0x04,
        "description": "Liest Timer-Werte",
        "data": struct.pack('>BH', 1, 0),  # Count=1, StartAddr=0
    },
    "Read Counter": {
        "cmd": 0x06,
        "description": "Liest Zähler-Werte",
        "data": struct.pack('>BH', 1, 0),  # Count=1, StartAddr=0
    },
    "Read Display Register": {
        "cmd": 0x14,
        "description": "Liest Display-Register",
        "data": struct.pack('>BH', 1, 0),
    },
    "Read PCD Status": {
        "cmd": 0x00,
        "description": "PCD Status abfragen (Station 255 = Broadcast)",
        "data": b'',
    },
    "Read Station Number": {
        "cmd": 0x1D,
        "description": "Station Number lesen",
        "data": b'',
    },
}

# Alternative: Einfache Byte-Sequenzen die bekannt funktionieren
RAW_PROBES = {
    "S-Bus Minimal (Station 0, Read Reg 0)": bytes([0x00, 0x00, 0x01, 0x00, 0x00]),
    "S-Bus Minimal (Station 1, Read Reg 0)": bytes([0x01, 0x00, 0x01, 0x00, 0x00]),
    "S-Bus Broadcast (Station 253)": bytes([0xFD, 0x00, 0x01, 0x00, 0x00]),
    "S7 TPKT Probe (RFC 1006)": bytes([0x03, 0x00, 0x00, 0x16]),  # S7 über TCP? Nicht seriell, aber testen
    "Modbus RTU (Station 1, Read Holding 0)": bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x01, 0x84, 0x0A]),
    "AT Command": b'AT\r\n',
    "Newline Probe": b'\r\n',
    "Null Probe": bytes([0x00]),
}

# Typische Baudraten für SAIA S-Bus
BAUDRATES = [9600, 19200, 38400, 57600, 115200]

def test_serial_port(port, baudrate, timeout=2):
    """Öffnet seriellen Port und gibt Serial-Objekt zurück."""
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_EVEN,  # S-Bus nutzt standardmäßig Even Parity
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
            write_timeout=timeout
        )
        return ser
    except serial.SerialException as e:
        log(f"  ❌ Port {port} @ {baudrate} baud: {e}")
        return None

def send_and_receive(ser, data, label="", wait=0.5):
    """Sendet Daten und wartet auf Antwort."""
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        log(f"  TX [{label}]: {data.hex(' ')}", also_print=False)
        ser.write(data)
        ser.flush()

        time.sleep(wait)

        response = ser.read(ser.in_waiting or 256)

        if response:
            log(f"  RX [{label}]: {response.hex(' ')} ({len(response)} bytes)")
            log(f"     ASCII: {response.decode('latin1', errors='replace')}", also_print=False)
            return response
        else:
            log(f"  RX [{label}]: (keine Antwort)", also_print=False)
            return None

    except Exception as e:
        log(f"  ❌ Fehler bei [{label}]: {e}")
        return None

def passive_listen(ser, duration=5):
    """Lauscht passiv ob die SPS von sich aus Daten sendet."""
    log(f"  Passives Lauschen für {duration} Sekunden...")
    print(f"     Lausche {duration}s auf spontane Daten...")

    start = time.time()
    all_data = b''

    while time.time() - start < duration:
        if ser.in_waiting:
            chunk = ser.read(ser.in_waiting)
            all_data += chunk
            log(f"  📡 Spontan empfangen: {chunk.hex(' ')} ({len(chunk)} bytes)")
        time.sleep(0.1)

    if all_data:
        log(f"  Gesamt spontan empfangen: {all_data.hex(' ')} ({len(all_data)} bytes)")
        return all_data
    else:
        log(f"  Keine spontanen Daten empfangen")
        return None

def analyze_response(data):
    """Versucht empfangene Daten zu interpretieren."""
    if not data:
        return "Keine Daten"

    analysis = []
    analysis.append(f"Länge: {len(data)} Bytes")
    analysis.append(f"Hex: {data.hex(' ')}")
    analysis.append(f"ASCII: {data.decode('latin1', errors='replace')}")

    # S-Bus Antwort?
    if len(data) >= 4:
        possible_crc = struct.unpack('>H', data[-2:])[0]
        calc_crc = sbus_crc16(data[:-2])
        if possible_crc == calc_crc:
            analysis.append("✅ CRC-16 CCITT stimmt überein → S-Bus Antwort!")

    # Modbus RTU Antwort?
    if len(data) >= 5:
        # Modbus CRC ist Little Endian CRC-16/Modbus
        try:
            # Einfache Modbus CRC Prüfung
            analysis.append(f"Erstes Byte (Station): {data[0]}")
            analysis.append(f"Zweites Byte (Function): {data[1]}")
        except:
            pass

    return "\n     ".join(analysis)

def run_baudrate_scan(port):
    """Testet alle Baudraten mit passivem Lauschen und S-Bus Probes."""
    results = {}

    for baudrate in BAUDRATES:
        print(f"\n{'─' * 50}")
        print(f"  🔧 Teste {baudrate} baud...")
        log(f"\n=== Baudrate: {baudrate} ===")

        # Erst mit Even Parity (S-Bus Standard)
        for parity_name, parity in [("Even", serial.PARITY_EVEN), ("None", serial.PARITY_NONE)]:
            try:
                ser = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=parity,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1,
                    write_timeout=1
                )
            except serial.SerialException as e:
                log(f"  ❌ Port {port} @ {baudrate}/{parity_name}: {e}")
                continue

            log(f"  Port geöffnet: {baudrate} baud, Parity={parity_name}")
            br_result = {"baudrate": baudrate, "parity": parity_name, "responses": []}

            # 1. Passiv lauschen (2 Sek)
            spontaneous = passive_listen(ser, duration=2)
            if spontaneous:
                br_result["spontaneous_data"] = spontaneous.hex()
                print(f"     ✅ Spontane Daten bei {baudrate}/{parity_name}!")

            # 2. S-Bus Kommandos testen
            for name, cmd_info in SBUS_COMMANDS.items():
                for station in [0, 1]:  # Station 0 und 1 probieren
                    telegram = build_sbus_request(station, cmd_info["cmd"], cmd_info["data"])
                    label = f"{name} (St.{station}) @ {baudrate}/{parity_name}"
                    response = send_and_receive(ser, telegram, label, wait=0.3)
                    if response:
                        br_result["responses"].append({
                            "command": name,
                            "station": station,
                            "tx": telegram.hex(),
                            "rx": response.hex(),
                            "rx_len": len(response)
                        })
                        print(f"     ✅ ANTWORT auf {name} (St.{station})!")
                        print(f"        → {response.hex(' ')}")

            # 3. Raw Probes
            for name, probe in RAW_PROBES.items():
                label = f"{name} @ {baudrate}/{parity_name}"
                response = send_and_receive(ser, probe, label, wait=0.3)
                if response:
                    br_result["responses"].append({
                        "command": name,
                        "tx": probe.hex(),
                        "rx": response.hex(),
                        "rx_len": len(response)
                    })
                    print(f"     ✅ ANTWORT auf {name}!")
                    print(f"        → {response.hex(' ')}")

            ser.close()

            if br_result["responses"] or br_result.get("spontaneous_data"):
                results[f"{baudrate}_{parity_name}"] = br_result

    return results

def main():
    parser = argparse.ArgumentParser(
        description='DocuPi 3000 - SAIA S-Bus USB Test',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python3 02_sbus_test.py --port /dev/tty.usbserial-1420
  python3 02_sbus_test.py --port /dev/ttyUSB0
  python3 02_sbus_test.py --port /dev/ttyUSB0 --baudrate 9600
  python3 02_sbus_test.py --port /dev/ttyUSB0 --listen-only
        """
    )
    parser.add_argument('--port', '-p', required=True, help='Serieller Port (z.B. /dev/ttyUSB0)')
    parser.add_argument('--baudrate', '-b', type=int, default=None, help='Nur diese Baudrate testen')
    parser.add_argument('--listen-only', '-l', action='store_true', help='Nur passiv lauschen (30 Sek)')
    parser.add_argument('--station', '-s', type=int, default=None, help='Nur diese Station testen')

    args = parser.parse_args()

    print("=" * 60)
    print("  DocuPi 3000 - SAIA S-Bus Kommunikationstest")
    print("=" * 60)
    print(f"  Port:     {args.port}")
    print(f"  Baudrate: {args.baudrate or 'Auto-Scan (' + ', '.join(map(str, BAUDRATES)) + ')'}")
    print(f"  Modus:    {'Nur Lauschen' if args.listen_only else 'Aktiver Test'}")
    print(f"  Log:      {LOG_FILE}")
    print("=" * 60)

    log(f"Start S-Bus Test: Port={args.port}, Baudrate={args.baudrate}")

    if args.listen_only:
        # Nur passiv lauschen
        baudrate = args.baudrate or 9600
        for parity_name, parity in [("Even", serial.PARITY_EVEN), ("None", serial.PARITY_NONE)]:
            print(f"\n  Lausche auf {args.port} @ {baudrate}/{parity_name}...")
            try:
                ser = serial.Serial(
                    port=args.port, baudrate=baudrate,
                    parity=parity, timeout=1
                )
                data = passive_listen(ser, duration=30)
                if data:
                    print(f"\n  📊 Analyse:")
                    print(f"     {analyze_response(data)}")
                ser.close()
            except Exception as e:
                print(f"  ❌ Fehler: {e}")
        return

    # Aktiver Scan
    if args.baudrate:
        baudrate_list = [args.baudrate]
    else:
        baudrate_list = list(BAUDRATES)

    saved = BAUDRATES[:]
    BAUDRATES.clear()
    BAUDRATES.extend(baudrate_list)
    results = run_baudrate_scan(args.port)
    BAUDRATES.clear()
    BAUDRATES.extend(saved)

    # Zusammenfassung
    print("\n" + "=" * 60)
    print("📋 ZUSAMMENFASSUNG S-Bus Test")
    print("=" * 60)

    if results:
        print(f"\n  ✅ Kommunikation erfolgreich bei:")
        for key, res in results.items():
            baud = res['baudrate']
            par = res['parity']
            n_resp = len(res['responses'])
            spont = "Ja" if res.get('spontaneous_data') else "Nein"
            print(f"\n     {baud} baud / Parity {par}:")
            print(f"       Antworten: {n_resp}")
            print(f"       Spontane Daten: {spont}")
            for r in res['responses']:
                print(f"       • {r['command']}: TX={r['tx']} → RX={r['rx']}")

        print(f"\n  → Nächster Schritt: Script 03_s7_lan_test.py für Vergleichstest über LAN")
    else:
        print(f"\n  ❌ Keine S-Bus Kommunikation über USB möglich.")
        print(f"\n  Mögliche Ursachen:")
        print(f"     • USB-Port der SAIA spricht kein S-Bus (evtl. nur PG5 Upload/Download)")
        print(f"     • Station-Adresse stimmt nicht (0-253)")
        print(f"     • Baudrate/Parity stimmt nicht")
        print(f"     • USB-Port ist deaktiviert in PCD-Konfiguration")
        print(f"\n  → Empfehlung: Teste über LAN mit Script 03_s7_lan_test.py")
        print(f"     Das ist der zuverlässigere Weg für S7-programmierte SAIAs!")

    # Ergebnis speichern
    result_file = LOG_DIR / "sbus_test_result.json"
    with open(result_file, "w") as f:
        json.dump({
            "port": args.port,
            "results": results,
            "success": bool(results),
            "timestamp": datetime.now().isoformat()
        }, f, indent=2, default=str)

    print(f"\n  Log:      {LOG_FILE}")
    print(f"  Ergebnis: {result_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()
