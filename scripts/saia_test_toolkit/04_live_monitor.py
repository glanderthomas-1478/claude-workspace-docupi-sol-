#!/usr/bin/env python3
"""
DocuPi 3000 - Live-Monitor für SAIA PCD2.M5 über S7/LAN
=========================================================
Zeigt Live-Prozessdaten der Sterilisator-SPS im Terminal an.
Aktualisiert sich jede Sekunde.

Nur LESEN - es wird NICHTS geschrieben!

Voraussetzung: pip install python-snap7
"""

import argparse
import struct
import sys
import time
from datetime import datetime

try:
    import snap7
    SNAP7_AVAILABLE = True
except ImportError:
    SNAP7_AVAILABLE = False
    print("❌ python-snap7 nicht installiert!")
    sys.exit(1)

def clear_screen():
    print("\033[2J\033[H", end="")

def color(text, code):
    return f"\033[{code}m{text}\033[0m"

def read_s7_string(data, offset):
    if offset + 2 > len(data):
        return ""
    actual_len = data[offset + 1]
    try:
        return data[offset + 2:offset + 2 + actual_len].decode('latin1')
    except:
        return ""

def main():
    parser = argparse.ArgumentParser(description='DocuPi 3000 - Live-Monitor')
    parser.add_argument('--ip', '-i', required=True, help='IP-Adresse der SPS')
    parser.add_argument('--rack', '-r', type=int, default=0)
    parser.add_argument('--slot', '-s', type=int, default=2)
    parser.add_argument('--interval', '-t', type=float, default=1.0, help='Update-Intervall in Sekunden')
    args = parser.parse_args()

    client = snap7.client.Client()

    print(f"🔗 Verbinde mit {args.ip}...")
    try:
        client.connect(args.ip, args.rack, args.slot)
    except Exception as e:
        print(f"❌ Verbindung fehlgeschlagen: {e}")
        sys.exit(1)

    print("✅ Verbunden! Starte Live-Monitor (Ctrl+C zum Beenden)\n")
    time.sleep(1)

    cycle = 0
    try:
        while True:
            cycle += 1
            now = datetime.now().strftime("%H:%M:%S")

            # Daten lesen
            try:
                db4 = client.db_read(4, 0, 30)
                db8 = client.db_read(8, 0, 100)

                # Merker lesen
                m76 = client.read_area(snap7.type.Areas.MK, 0, 76, 1)
                m51 = client.read_area(snap7.type.Areas.MK, 0, 51, 1)
                m132 = client.read_area(snap7.type.Areas.MK, 0, 132, 1)
                m211 = client.read_area(snap7.type.Areas.MK, 0, 211, 1)

                # Analoge Eingänge
                ai_t1 = struct.unpack('>h', client.read_area(snap7.type.Areas.PE, 0, 136, 2))[0]
                ai_p1 = struct.unpack('>h', client.read_area(snap7.type.Areas.PE, 0, 128, 2))[0]
            except Exception as e:
                print(f"\r❌ Lesefehler: {e} - versuche Reconnect...")
                try:
                    client.disconnect()
                    time.sleep(2)
                    client.connect(args.ip, args.rack, args.slot)
                except:
                    pass
                continue

            # DB4 parsen
            lfd_nr = struct.unpack_from('>i', db4, 0)[0]
            phase = struct.unpack_from('>h', db4, 4)[0]
            steri_zeit = struct.unpack_from('>h', db4, 6)[0]
            f0_wert = struct.unpack_from('>h', db4, 14)[0] * 0.1
            min_temp = struct.unpack_from('>h', db4, 22)[0] * 0.1
            max_temp = struct.unpack_from('>h', db4, 24)[0] * 0.1
            leckrate = struct.unpack_from('>h', db4, 26)[0] * 0.1

            # DB8 parsen
            prog_name = read_s7_string(db8, 0)
            prog_nr = struct.unpack_from('>h', db8, 42)[0]
            soll_temp = struct.unpack_from('>h', db8, 68)[0] * 0.1
            soll_zeit = struct.unpack_from('>h', db8, 72)[0] * 0.1

            # Merker
            prg_laeuft = bool(m76[0] & (1 << 2))
            proz_ende = bool(m76[0] & (1 << 1))
            stoerung = bool(m51[0] & (1 << 0))
            steri_phase = bool(m132[0] & (1 << 2))
            abbruch = bool(m211[0] & (1 << 0))

            # Display
            clear_screen()
            print(color("═" * 60, "1;36"))
            print(color("  DocuPi 3000 - SAIA Live-Monitor", "1;36"))
            print(color(f"  {now}  |  Zyklus #{cycle}  |  Intervall: {args.interval}s", "36"))
            print(color("═" * 60, "1;36"))

            # Status-Zeile
            status_parts = []
            if prg_laeuft:
                status_parts.append(color("▶ LÄUFT", "1;32"))
            elif proz_ende:
                status_parts.append(color("✓ FERTIG", "1;34"))
            else:
                status_parts.append(color("■ STANDBY", "37"))

            if stoerung:
                status_parts.append(color("⚠ STÖRUNG", "1;31"))
            if steri_phase:
                status_parts.append(color("★ STERILISATION", "1;33"))
            if abbruch:
                status_parts.append(color("✗ ABBRUCH", "1;31"))

            print(f"\n  Status: {' | '.join(status_parts)}")

            # Charge & Programm
            print(f"\n  {'─' * 56}")
            print(f"  Charge:       #{lfd_nr}")
            print(f"  Programm:     {prog_name} (Nr. {prog_nr})")
            print(f"  Phase:        {phase}")

            # Temperaturen
            print(f"\n  {'─' * 56}")
            print(color("  TEMPERATUREN", "1;33"))
            print(f"  T1 (Kammer):  {ai_t1:>6d} (roh)")
            print(f"  Min Steri:    {min_temp:>6.1f} °C")
            print(f"  Max Steri:    {max_temp:>6.1f} °C")
            print(f"  SOLL:         {soll_temp:>6.1f} °C")

            # Druck
            print(f"\n  {'─' * 56}")
            print(color("  DRUCK", "1;34"))
            print(f"  P1 (Kammer):  {ai_p1:>6d} (roh)")
            print(f"  Leckrate:     {leckrate:>6.1f} mbar/Min")

            # Zeiten
            print(f"\n  {'─' * 56}")
            print(color("  ZEITEN", "1;35"))
            print(f"  Steri-Zeit:   {steri_zeit:>6d} Sek")
            print(f"  F0-Wert:      {f0_wert:>6.1f} Min")
            print(f"  SOLL-Zeit:    {soll_zeit:>6.1f} Min")

            print(f"\n  {'─' * 56}")
            print(f"  {color('Ctrl+C', '1')} zum Beenden")
            print(color("═" * 60, "1;36"))

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print(f"\n\n  Monitor beendet.")
    finally:
        try:
            client.disconnect()
            print("  🔌 Verbindung getrennt")
        except:
            pass

if __name__ == "__main__":
    main()
