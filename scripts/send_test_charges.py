#!/usr/bin/env python3
"""
send_test_charges.py — Simuliert Belimed-Chargenprotokolle via TCP/9100

Sendet N Chargen im angegebenen Intervall an den DocuControl-Pi.
Encoding: UTF-16LE mit BOM (identisch zum Originalgeraet).

Verwendung:
    python3 scripts/send_test_charges.py
    python3 scripts/send_test_charges.py --count 1
    python3 scripts/send_test_charges.py --host 192.168.0.171 --count 10 --interval 30
    python3 scripts/send_test_charges.py --dry-run
    python3 scripts/send_test_charges.py --interval 7200   # produktionsnahe Simulation
"""

import argparse
import socket
import time
from datetime import datetime

DEFAULT_HOST = "192.168.0.171"
DEFAULT_PORT = 9100
START_CHARGE = 21720

# Programm-Rotation fuer 10 Chargen: 4x Instr134, 3x BowieDick, 3x Instr121
ROTATION = [0, 1, 0, 2, 0, 1, 2, 0, 1, 0]

# Laufzeit-Offsets (Minuten) pro Charge-Index — deterministisch variiert
DURATION_OFFSETS = [0, 0, +2, 0, -1, +2, -3, +3, -2, +1]


# ---------------------------------------------------------------------------
# Template 1: Instrumente 134°C  (Basislaufzeit: 33 min, Varianz: ±3 min)
# ---------------------------------------------------------------------------

def prog_instrumente_134(charge_nr, start_dt, ende_mm, ende_ss):
    return (
        "BELIMED CHARGEN-DOKUMENTATION\n"
        "============================================================\n"
        f"Betreiber     : Uniklinik Essen Tierlabor\n"
        f"Abteilung     : AEMP\n"
        f"Maschinen-Typ : PST 14-8-12 HS1    Nr:10980\n"
        f"Laufende Nr.  : {charge_nr:06d}\n"
        f"Benutzer      : User\n"
        f"Programm      :  1: Instrumente 134°C\n"
        f"Version       : PR: 07.03.2018 SW: 103\n"
        f"\n"
        f"Sollwerte     : Anz. Fraktionen         9\n"
        f"                Sterilisierzeit    5.0min\n"
        f"                Sterilisiertemp.  134.2°C\n"
        f"                Trocknungszeit    17.0min\n"
        f"\n"
        f"Programmstart : {start_dt.strftime('%d.%m.%Y / %H:%M')}\n"
        f"\n"
        f" Zeit  Phase    Kammer       mbara  T2 °C\n"
        f"  m:s           Luftnachweisg.      T3 °C\n"
        f"-----------------------------------------\n"
        f"  0:01 1. Vorvakuum           1011   38.2\n"
        f"                                     31.1\n"
        f"  2:31 1. Druck                 82   69.1\n"
        f"                                     31.0\n"
        f"  3:35 2. Vorvakuum            871   52.1\n"
        f"                                     31.5\n"
        f"  4:27 2. Druck                102   72.3\n"
        f"                                     31.1\n"
        f"  5:24 3. Vorvakuum            803   82.1\n"
        f"                                     31.5\n"
        f"  6:13 3. Druck                100   54.5\n"
        f"                                     31.2\n"
        f"  7:14 4. Vorvakuum            856   92.1\n"
        f"                                     31.5\n"
        f"  8:04 4. Druck                 99   66.7\n"
        f"                                     31.3\n"
        f"  9:20 Luftdruck erreicht     1016   97.8\n"
        f"                                     98.7\n"
        f" 10:34 5. Vorvakuum           1823  116.2\n"
        f"                                    116.2\n"
        f" 11:20 5. Druck               1080  107.4\n"
        f"                                    103.1\n"
        f" 12:18 6. Vorvakuum           1810  116.4\n"
        f"                                    116.6\n"
        f" 13:04 6. Druck               1085  105.1\n"
        f"                                    104.1\n"
        f" 14:07 7. Vorvakuum           1869  117.1\n"
        f"                                    117.1\n"
        f" 14:51 7. Druck               1111  109.0\n"
        f"                                    104.8\n"
        f" 15:50 > Vorvakuum            1817  116.7\n"
        f"                                    116.7\n"
        f" 16:35 > Druck                1086  110.3\n"
        f"                                    104.9\n"
        f" 17:38 > Vorvakuum            1853  117.4\n"
        f"                                    116.9\n"
        f" 18:24 Aufheizen              1080  110.2\n"
        f"                                    105.2\n"
        f" 21:54 Sterilisation          3101  134.5\n"
        f"                                    134.4\n"
        f" 22:53                        3094  135.2\n"
        f"                                    134.9\n"
        f" 23:53                        3101  135.1\n"
        f"                                    135.1\n"
        f" 24:53                        3111  135.1\n"
        f"                                    135.2\n"
        f" 25:24 Nachvakuum             3110  135.1\n"
        f"                                    135.1\n"
        f" {ende_mm - 5}:41 Trocknung               100   81.6\n"
        f"                                     94.7\n"
        f" {ende_mm - 2}:42 Belüften                 44   33.1\n"
        f"                                     91.7\n"
        f" {ende_mm}:{ende_ss:02d} Programm Ende           966   48.5\n"
        f"                                     84.7\n"
        f"\n"
        f"Min. Sterilisiertemp.             134.8°C\n"
        f"Max. Sterilisiertemp.             135.6°C\n"
        f"Zeit ueber Sollwert Kammer        {ende_mm - 30}:30m:s\n"
        f"Zeit ueb. Sollt. Luftnachweisg.   {ende_mm - 30}:30m:s\n"
        f"F0-Wert                          116.0min\n"
        f"\n"
        f"PROGRAMM KORREKT BEENDET\n"
        f"\n"
        f"Freigabe: J / N         Datum:\n"
        f"\n"
        f"Unterschrift:\n"
    )


# ---------------------------------------------------------------------------
# Template 2: Bowie Dick  (Basislaufzeit: 20 min, Varianz: ±2 min)
# ---------------------------------------------------------------------------

def prog_bowie_dick(charge_nr, start_dt, ende_mm, ende_ss):
    return (
        "BELIMED CHARGEN-DOKUMENTATION\n"
        "============================================================\n"
        f"Betreiber     : Uniklinik Essen Tierlabor\n"
        f"Abteilung     : AEMP\n"
        f"Maschinen-Typ : PST 14-8-12 HS1    Nr:10980\n"
        f"Laufende Nr.  : {charge_nr:06d}\n"
        f"Benutzer      : User\n"
        f"Programm      :  3: Bowie Dick\n"
        f"Version       : PR: 07.03.2018 SW: 103\n"
        f"\n"
        f"Sollwerte     : Sterilisierzeit    3.5min\n"
        f"                Sterilisiertemp.  134.2°C\n"
        f"                Trocknungszeit     5.0min\n"
        f"\n"
        f"Programmstart : {start_dt.strftime('%d.%m.%Y / %H:%M')}\n"
        f"\n"
        f" Zeit  Phase    Kammer       mbara  T2 °C\n"
        f"  m:s           Luftnachweisg.      T3 °C\n"
        f"-----------------------------------------\n"
        f"  0:01 1. Vorvakuum           1011   37.4\n"
        f"                                     30.8\n"
        f"  2:15 1. Druck                 84   65.3\n"
        f"                                     30.9\n"
        f"  3:10 2. Vorvakuum            883   48.7\n"
        f"                                     31.2\n"
        f"  3:58 2. Druck                 98   69.8\n"
        f"                                     31.0\n"
        f"  4:44 3. Vorvakuum            812   79.5\n"
        f"                                     31.3\n"
        f"  5:29 3. Druck                101   52.1\n"
        f"                                     31.1\n"
        f"  6:18 Luftdruck erreicht     1012   94.2\n"
        f"                                     95.0\n"
        f"  7:45 Aufheizen              1076  108.4\n"
        f"                                    104.1\n"
        f" 10:52 Sterilisation          3098  134.3\n"
        f"                                    134.2\n"
        f" 11:51                        3092  134.8\n"
        f"                                    134.6\n"
        f" 12:51                        3105  134.9\n"
        f"                                    134.7\n"
        f" 14:22 Nachvakuum             3108  134.8\n"
        f"                                    134.9\n"
        f" {ende_mm - 5}:03 Trocknung               103   79.2\n"
        f"                                     88.4\n"
        f" {ende_mm - 1}:38 Belüften                 46   31.4\n"
        f"                                     82.1\n"
        f" {ende_mm}:{ende_ss:02d} Programm Ende           971   44.3\n"
        f"                                     76.5\n"
        f"\n"
        f"Min. Sterilisiertemp.             134.3°C\n"
        f"Max. Sterilisiertemp.             135.1°C\n"
        f"Zeit ueber Sollwert Kammer        3:30m:s\n"
        f"Zeit ueb. Sollt. Luftnachweisg.   3:30m:s\n"
        f"F0-Wert                           82.4min\n"
        f"\n"
        f"PROGRAMM KORREKT BEENDET\n"
        f"\n"
        f"Freigabe: J / N         Datum:\n"
        f"\n"
        f"Unterschrift:\n"
    )


# ---------------------------------------------------------------------------
# Template 3: Instrumente 121°C  (Basislaufzeit: 42 min, Varianz: ±4 min)
# ---------------------------------------------------------------------------

def prog_instrumente_121(charge_nr, start_dt, ende_mm, ende_ss):
    return (
        "BELIMED CHARGEN-DOKUMENTATION\n"
        "============================================================\n"
        f"Betreiber     : Uniklinik Essen Tierlabor\n"
        f"Abteilung     : AEMP\n"
        f"Maschinen-Typ : PST 14-8-12 HS1    Nr:10980\n"
        f"Laufende Nr.  : {charge_nr:06d}\n"
        f"Benutzer      : User\n"
        f"Programm      :  2: Instrumente 121°C\n"
        f"Version       : PR: 07.03.2018 SW: 103\n"
        f"\n"
        f"Sollwerte     : Anz. Fraktionen         3\n"
        f"                Sterilisierzeit   15.0min\n"
        f"                Sterilisiertemp.  121.0°C\n"
        f"                Trocknungszeit    20.0min\n"
        f"\n"
        f"Programmstart : {start_dt.strftime('%d.%m.%Y / %H:%M')}\n"
        f"\n"
        f" Zeit  Phase    Kammer       mbara  T2 °C\n"
        f"  m:s           Luftnachweisg.      T3 °C\n"
        f"-----------------------------------------\n"
        f"  0:01 1. Vorvakuum           1013   37.8\n"
        f"                                     30.9\n"
        f"  2:08 1. Druck                 79   62.4\n"
        f"                                     30.7\n"
        f"  3:12 2. Vorvakuum            868   49.3\n"
        f"                                     31.1\n"
        f"  4:01 2. Druck                 95   67.9\n"
        f"                                     30.8\n"
        f"  4:58 3. Vorvakuum            821   78.2\n"
        f"                                     31.2\n"
        f"  5:44 3. Druck                 97   51.8\n"
        f"                                     30.9\n"
        f"  6:51 Luftdruck erreicht     1009   92.5\n"
        f"                                     93.1\n"
        f"  8:04 Aufheizen              2006  103.7\n"
        f"                                    101.2\n"
        f" 11:22 Sterilisation          2105  121.2\n"
        f"                                    121.0\n"
        f" 12:22                        2098  121.4\n"
        f"                                    121.1\n"
        f" 13:22                        2107  121.3\n"
        f"                                    121.2\n"
        f" 14:22                        2101  121.5\n"
        f"                                    121.3\n"
        f" 15:22                        2109  121.4\n"
        f"                                    121.2\n"
        f" 16:22                        2103  121.3\n"
        f"                                    121.1\n"
        f" 17:22                        2098  121.4\n"
        f"                                    121.2\n"
        f" 18:22                        2104  121.5\n"
        f"                                    121.3\n"
        f" 19:22                        2107  121.3\n"
        f"                                    121.2\n"
        f" 20:22                        2101  121.4\n"
        f"                                    121.1\n"
        f" 21:22                        2098  121.3\n"
        f"                                    121.0\n"
        f" 22:22                        2104  121.5\n"
        f"                                    121.2\n"
        f" 26:22 Nachvakuum             2106  121.3\n"
        f"                                    121.1\n"
        f" {ende_mm - 14}:08 Trocknung                98   74.3\n"
        f"                                     89.6\n"
        f" {ende_mm - 2}:51 Belüften                 41   30.8\n"
        f"                                     85.2\n"
        f" {ende_mm}:{ende_ss:02d} Programm Ende           972   42.1\n"
        f"                                     79.8\n"
        f"\n"
        f"Min. Sterilisiertemp.             121.0°C\n"
        f"Max. Sterilisiertemp.             121.6°C\n"
        f"Zeit ueber Sollwert Kammer       15:00m:s\n"
        f"Zeit ueb. Sollt. Luftnachweisg.  15:00m:s\n"
        f"F0-Wert                           48.2min\n"
        f"\n"
        f"PROGRAMM KORREKT BEENDET\n"
        f"\n"
        f"Freigabe: J / N         Datum:\n"
        f"\n"
        f"Unterschrift:\n"
    )


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

PROGRAMS = [
    ("Instrumente 134°C", prog_instrumente_134, 33, 3),
    ("Bowie Dick",        prog_bowie_dick,      20, 2),
    ("Instrumente 121°C", prog_instrumente_121, 42, 4),
]


def build_protocol(i, start_charge=START_CHARGE, sequence=None):
    prog_idx = sequence[i] if sequence is not None else ROTATION[i % len(ROTATION)]
    name, func, base_min, _variance = PROGRAMS[prog_idx]
    offset = DURATION_OFFSETS[i % len(DURATION_OFFSETS)]
    ende_mm = base_min + offset
    ende_ss = 29
    charge_nr = start_charge + i
    start_dt = datetime.now()
    text = func(charge_nr, start_dt, ende_mm, ende_ss)
    return charge_nr, name, ende_mm, ende_ss, text


def encode_protocol(text):
    return b'\xff\xfe' + text.encode('utf-16-le')


def send_protocol(host, port, raw_bytes, timeout=10):
    sock = socket.create_connection((host, port), timeout=timeout)
    try:
        sock.sendall(raw_bytes)
    finally:
        sock.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Sendet simulierte Belimed-Protokolle an DocuControl Pi")
    parser.add_argument("--host",     default=DEFAULT_HOST,  help=f"Ziel-IP (default: {DEFAULT_HOST})")
    parser.add_argument("--port",     type=int, default=DEFAULT_PORT, help=f"TCP-Port (default: {DEFAULT_PORT})")
    parser.add_argument("--count",    type=int, default=10,  help="Anzahl Chargen (default: 10)")
    parser.add_argument("--interval", type=int, default=30,  help="Pause zwischen Chargen in Sekunden (default: 30)")
    parser.add_argument("--start-charge", type=int, default=START_CHARGE,
                        help=f"Erste Chargennummer (default: {START_CHARGE})")
    parser.add_argument("--sequence", default=None,
                        help="Komma-Liste Programm-Indizes (0=Instr134, 1=BowieDick, 2=Instr121), "
                             "ueberschreibt --count und Standard-Rotation, z.B. '1,0,0,0,0,0'")
    parser.add_argument("--dry-run",  action="store_true",   help="Protokolle auf stdout ausgeben, nicht senden")
    args = parser.parse_args()

    sequence = None
    if args.sequence:
        sequence = [int(x) for x in args.sequence.split(",")]
        args.count = len(sequence)

    print(f"DocuControl Test-Chargen-Sender")
    print(f"Ziel: {args.host}:{args.port}  |  Chargen: {args.count}  |  Interval: {args.interval}s")
    if args.dry_run:
        print("MODUS: Dry-Run (kein TCP-Send)\n")
    print("-" * 60)

    for i in range(args.count):
        charge_nr, prog_name, ende_mm, ende_ss, text = build_protocol(i, args.start_charge, sequence)
        raw = encode_protocol(text)
        duration_str = f"{ende_mm}:{ende_ss:02d}"

        if args.dry_run:
            print(f"\n{'='*60}")
            print(f"CH{charge_nr:06d}  |  {prog_name}  |  Laufzeit {duration_str} min")
            print(f"{'='*60}")
            print(text)
        else:
            try:
                send_protocol(args.host, args.port, raw)
                lines = text.count('\n')
                print(f"[{i+1:02d}/{args.count}]  CH{charge_nr:06d}  |  {prog_name:25s}  |  "
                      f"Laufzeit {duration_str:5s}  |  {len(raw):5d} Bytes  |  OK")
            except Exception as e:
                print(f"[{i+1:02d}/{args.count}]  CH{charge_nr:06d}  FEHLER: {e}")

        if not args.dry_run and i < args.count - 1:
            print(f"         Warte {args.interval}s ...")
            time.sleep(args.interval)

    print("-" * 60)
    if not args.dry_run:
        print(f"Fertig. {args.count} Chargen gesendet (CH{args.start_charge:06d}–CH{args.start_charge + args.count - 1:06d})")
    else:
        print(f"Dry-Run abgeschlossen. Mit --count {args.count} --host {args.host} senden.")


if __name__ == "__main__":
    main()
