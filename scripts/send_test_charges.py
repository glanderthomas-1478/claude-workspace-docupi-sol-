#!/usr/bin/env python3
"""
send_test_charges.py — Simuliert Belimed-Chargenprotokolle via TCP/9100 oder LPD

Sendet N Chargen im angegebenen Intervall an den DocuControl-Pi.
Encoding: UTF-16LE mit BOM (identisch zum Originalgeraet).

Verwendung:
    python3 scripts/send_test_charges.py
    python3 scripts/send_test_charges.py --count 1
    python3 scripts/send_test_charges.py --host 192.168.0.171 --count 10 --interval 30
    python3 scripts/send_test_charges.py --dry-run
    python3 scripts/send_test_charges.py --interval 7200   # produktionsnahe Simulation
    python3 scripts/send_test_charges.py --format pst --count 1 --sequence 4
    python3 scripts/send_test_charges.py --format pst --via-lpd --count 1
"""

import argparse
import socket
import time
from datetime import datetime, timedelta

DEFAULT_HOST = "192.168.0.171"
DEFAULT_PORT = 9100
START_CHARGE = 21720
START_LFD_NR = 12086

# Programm-Rotation fuer 10 Chargen: 4x Instr134, 3x BowieDick, 3x Instr121
ROTATION = [0, 1, 0, 2, 0, 1, 2, 0, 1, 0]

# PST-Rotation: 0=Aufheiz, 1=Vakuumtest, 2=Kaefige, 3=Passage, 4=Futter
ROTATION_PST = [0, 4, 2, 4, 0, 1, 4, 3, 4, 0]

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
        f"Abteilung     : ZTL\n"
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
        f"Abteilung     : ZTL\n"
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
        f"Abteilung     : ZTL\n"
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
# Template 4: Aufheizen & VPR  (Basislaufzeit: 46 min, Varianz: ±3 min)
# ---------------------------------------------------------------------------

def prog_vpr(charge_nr, start_dt, ende_mm, ende_ss):
    lecktest_mm = ende_mm - 12
    belueften2_mm = ende_mm - 2
    return (
        "BELIMED CHARGEN-DOKUMENTATION\n"
        "============================================================\n"
        f"Betreiber     : Uniklinik Essen Tierlabor\n"
        f"Abteilung     : ZTL\n"
        f"Maschinen-Typ : PST 14-8-12 HS1    Nr:10980\n"
        f"Laufende Nr.  : {charge_nr:06d}\n"
        f"Benutzer      : User\n"
        f"Programm      :  4: Aufheizen & VPR\n"
        f"Version       : PR: 07.03.2018 SW: 103\n"
        f"\n"
        f"Sollwerte     : Leckrate        <   1.3 mbar/min\n"
        f"                Testzeit               10.0min\n"
        f"\n"
        f"Programmstart : {start_dt.strftime('%d.%m.%Y / %H:%M')}\n"
        f"\n"
        f" Zeit  Phase    Kammer       mbara  T2 °C\n"
        f"  m:s           Luftnachweisg.      T3 °C\n"
        f"-----------------------------------------\n"
        f"  0:02 1. Vorvakuum            991   32.2\n"
        f"                                     31.4\n"
        f"  2:33 Aufheizen                75   66.7\n"
        f"                                     52.3\n"
        f" 10:59 Sterilisation          3166  134.6\n"
        f"                                    134.4\n"
        f" 11:59                        3187  135.1\n"
        f"                                    134.9\n"
        f" 12:59                        3184  135.1\n"
        f"                                    135.0\n"
        f" 13:59                        3180  135.1\n"
        f"                                    135.1\n"
        f" 14:59                        3195  135.1\n"
        f"                                    135.2\n"
        f" 16:00 Nachvakuum             3169  135.0\n"
        f"                                    135.0\n"
        f" 19:22 Trocknung               100   76.7\n"
        f"                                     94.2\n"
        f" 25:22 Belüften                 41   32.3\n"
        f"                                     78.1\n"
        f" 27:14 Vakuum                  956   34.0\n"
        f"                                     42.6\n"
        f" 29:42 Stabilisierung           70   30.2\n"
        f"                                     36.1\n"
        f" {lecktest_mm}:43 Lecktest                 76   35.2\n"
        f"                                     35.8\n"
        f" {belueften2_mm}:44 Belüften                 80   38.4\n"
        f"                                     38.1\n"
        f" {ende_mm}:{ende_ss:02d} Programm Ende           956   39.6\n"
        f"                                     39.2\n"
        f"\n"
        f"Leckrate                     0.7 mbar/min\n"
        f"\n"
        f"PROGRAMM BEENDET NICHT STERIL\n"
        f"\n"
        f"Freigabe: J / N         Datum:\n"
        f"\n"
        f"Unterschrift:\n"
    )


# ---------------------------------------------------------------------------
# PST-Format Templates (Belimed PST 14-8-12 HS1 / UNIKLINIK_ESSEN_10980)
# Zeit: echte Uhrzeit HH.MM.SS, 6 Temperatursensoren T1–T6
# ---------------------------------------------------------------------------

def pst_prog0_aufheiz(lfd_nr, start_hh, start_mm):
    t0 = datetime.now().replace(hour=start_hh, minute=start_mm, second=0, microsecond=0)
    def ts(m, s): return (t0 + timedelta(minutes=m, seconds=s)).strftime("%H . %M . %S")
    return (
        f"Chargen Protokoll                    UNIKLINIK_ESSEN_10980        Seite 1/1\n"
        f"Steri-Nr.    10980                   Chargendauer         34.4 min\n"
        f"Benutzer     ALLGEMEIN               Sterilisierdauer      5.0 min\n"
        f"                                     max. Sterilisiertemperatur  123.0 C\n"
        f"Lfd.Nr.      {lfd_nr}\n"
        f"Programm     0   Aufheizprogramm 121 C    Endwert Fo T2         0.0 min\n"
        f"                                     min. Sterilisiertemperatur  122.0 C\n"
        f"Datum/Zeit   {t0.strftime('%d . %m . %Y')}   {start_hh:02d} h{start_mm:02d} min\n"
        f"Artikel-Bez.\n"
        f"Chargen-Bez.\n"
        f"\n"
        f"Zeit         Phase                    P2      T1    T2    T3    T4    T5    T6\n"
        f"                                    [mbar]  [C]   [C]   [C]   [C]   [C]   [C]\n"
        f"-------------------------------------------------------------------------------\n"
        f"{ts(0,2)}  1. Vorvakuum              987   47.2   27.7   49.7   49.3   23.5   25.7\n"
        f"{ts(5,27)}  Aufheizen                  68   41.8   42.9   43.6   43.8   24.2   25.9\n"
        f"{ts(15,27)}  Aufheizen                2057  120.1  118.7  119.4  119.2   25.1   26.5\n"
        f"{ts(16,43)}  Sterilisation (Zeit)     2151  122.0  120.5  121.4  121.3   25.3   26.7\n"
        f"{ts(17,43)}  Sterilisation (Zeit)     2202  122.7  121.8  122.4  122.3   25.4   26.8\n"
        f"{ts(18,43)}  Sterilisation (Zeit)     2202  122.7  121.6  122.3  122.3   25.5   27.2\n"
        f"{ts(19,43)}  Sterilisation (Zeit)     2206  122.7  122.2  122.5  122.6   25.7   27.3\n"
        f"{ts(20,43)}  Sterilisation (Zeit)     2208  122.6  122.4  122.6  122.7   25.9   27.5\n"
        f"{ts(21,43)}  Druckentlasten           2196  122.6  122.5  122.7  122.8   26.0   27.7\n"
        f"{ts(22,48)}  Nachvakuum               1125  107.2  104.6  106.1  108.4   26.2   28.0\n"
        f"{ts(24,33)}  Trocknung                 102   70.5   73.7   71.3   70.4   26.6   28.3\n"
        f"{ts(29,33)}  Belüften                   37   84.7   68.1   87.8   89.0   27.1   28.9\n"
        f"{ts(34,30)}  Programmende             1027  104.9   54.2  109.5  110.5   35.2   29.3\n"
        f"\n"
        f"Keine prozessrelevante Störung aufgetreten\n"
        f"Unterschrift :           Freigabe : Ja    Nein\n"
    )


def pst_prog1_vakuumtest(lfd_nr, start_hh, start_mm):
    # Exakt nach Foto 61a85d69: LFD 12074, 08.06.2026, 05h56 min
    # Erste Zeile 48s nach Start, 14 Zeilen gesamt
    t0 = datetime.now().replace(hour=start_hh, minute=start_mm, second=0, microsecond=0)
    def ts(m, s): return (t0 + timedelta(minutes=m, seconds=s)).strftime("%H . %M . %S")
    return (
        f"Chargen Protokoll                    UNIKLINIK_ESSEN_10980        Seite 1/1\n"
        f"Steri-Nr.    10980                   Chargendauer         22.3 min\n"
        f"Benutzer     ALLGEMEIN\n"
        f"\n"
        f"Lfd.Nr.      {lfd_nr}\n"
        f"Programm     1   Vakuumtest\n"
        f"Datum/Zeit   {t0.strftime('%d . %m . %Y')}   {start_hh:02d} h{start_mm:02d} min\n"
        f"Artikel-Bez.\n"
        f"Chargen-Bez.\n"
        f"\n"
        f"Zeit         Phase                    P2      T1\n"
        f"                                    [mbar]  [C]\n"
        f"--------------------------------------------------\n"
        f"{ts(0,48)}  Vakuum                    989   20.1\n"
        f"{ts(2,48)}  Vakuum                    307   13.5\n"
        f"{ts(4,48)}  Vakuum                    123   10.9\n"
        f"{ts(6,48)}  Vakuum                     69   11.5\n"
        f"{ts(6,53)}  Stabilisierung             68   11.6\n"
        f"{ts(8,53)}  Stabilisierung             69   12.9\n"
        f"{ts(10,53)}  Stabilisierung             69   14.1\n"
        f"{ts(11,53)}  Vakuumtest                 69   14.5\n"
        f"{ts(13,53)}  Vakuumtest                 69   15.4\n"
        f"{ts(15,53)}  Vakuumtest                 69   16.0\n"
        f"{ts(17,53)}  Vakuumtest                 69   16.5\n"
        f"{ts(19,53)}  Vakuumtest                 69   17.0\n"
        f"{ts(21,53)}  Belüften                   69   17.4\n"
        f"{ts(23,6)}  Programmende             1024   22.2\n"
        f"\n"
        f"Keine prozessrelevante Störung aufgetreten\n"
        f"Unterschrift :           Freigabe : Ja    Nein\n"
    )


def pst_prog2_kaefige(lfd_nr, start_hh, start_mm):
    # Seite 2 exakt nach Foto e6d8b176: LFD 12084, 12.06.2026, 07h16 min
    t0 = datetime.now().replace(hour=start_hh, minute=start_mm, second=0, microsecond=0)
    def ts(m, s): return (t0 + timedelta(minutes=m, seconds=s)).strftime("%H . %M . %S")
    page2_header = (
        f"Chargen Protokoll                    UNIKLINIK_ESSEN_10980        Seite 2/2\n"
        f"                                     Chargendauer         97.1 min\n"
        f"Lfd.Nr.      {lfd_nr}                Sterilisierdauer     20.0 min\n"
        f"Programm     2   Kaefige 121C         max. Sterilisiertemperatur  122.5 C\n"
        f"Datum/Zeit   {t0.strftime('%d . %m . %Y')}   {start_hh:02d} h{start_mm:02d} min   min. Sterilisiertemperatur  121.3 C\n"
        f"\n"
        f"Zeit         Phase                    P2      T1    T2    T3    T4    T5    T6\n"
        f"                                    [mbar]  [C]   [C]   [C]   [C]   [C]   [C]\n"
        f"-------------------------------------------------------------------------------\n"
    )
    return (
        f"Chargen Protokoll                    UNIKLINIK_ESSEN_10980        Seite 1/2\n"
        f"Steri-Nr.    10980                   Chargendauer         97.1 min\n"
        f"Benutzer     ALLGEMEIN               Sterilisierdauer     20.0 min\n"
        f"                                     max. Sterilisiertemperatur  122.5 C\n"
        f"Lfd.Nr.      {lfd_nr}\n"
        f"Programm     2   Kaefige 121C         Endwert Fo T2         58.4 min\n"
        f"                                     min. Sterilisiertemperatur  121.3 C\n"
        f"Datum/Zeit   {t0.strftime('%d . %m . %Y')}   {start_hh:02d} h{start_mm:02d} min\n"
        f"Artikel-Bez.\n"
        f"Chargen-Bez.\n"
        f"\n"
        f"Zeit         Phase                    P2      T1    T2    T3    T4    T5    T6\n"
        f"                                    [mbar]  [C]   [C]   [C]   [C]   [C]   [C]\n"
        f"-------------------------------------------------------------------------------\n"
        f"{ts(0,7)}   1. Vorvakuum             897   38.9   22.8   23.5   22.6   31.2   34.8\n"
        f"{ts(4,21)}  Aufheizen                  73   36.8   22.2   22.8   22.4   31.0   34.8\n"
        f"{ts(13,20)}  Aufheizen               1942  105.3   99.1  103.8  102.1   31.8   35.2\n"
        f"{ts(15,20)}  Sterilisation (Zeit)    2121  121.0  120.0  121.0  120.8   32.2   35.5\n"
        f"{ts(16,20)}  Sterilisation (Zeit)    2175  121.8  121.2  121.8  121.5   32.4   35.7\n"
        f"{ts(17,20)}  Sterilisation (Zeit)    2181  122.1  121.5  122.0  121.8   32.5   35.9\n"
        f"{ts(18,20)}  Sterilisation (Zeit)    2178  122.3  121.6  122.1  121.9   32.6   36.0\n"
        f"{ts(19,20)}  Sterilisation (Zeit)    2182  122.4  121.7  122.2  122.0   32.7   36.1\n"
        f"{ts(25,20)}  Sterilisation (Zeit)    2180  122.5  121.8  122.3  122.1   32.9   36.2\n"
        f"{ts(35,20)}  Druckentlasten          2165  122.4  121.7  122.2  122.0   33.1   36.3\n"
        f"{ts(36,25)}  Nachvakuum              1075  109.2  106.3  108.1  107.4   33.3   36.4\n"
        f"{ts(39,30)}  Belüften                  40   91.2   74.1   89.3   87.8   33.5   36.3\n"
        f"{ts(40,31)}  Haltezeit Belüften       401   93.5   62.4   91.2   89.5   33.8   36.2\n"
        f"{ts(41,32)}  Nachvakuum                79   95.8   78.2   93.4   91.7   34.1   36.1\n"
        f"{ts(42,33)}  Haltezeit Vakuum           50   96.4   74.5   94.1   92.3   33.9   36.0\n"
        f"{ts(43,34)}  Belüften                   50   97.0   76.2   94.8   93.0   33.7   36.0\n"
        + page2_header +
        # Seite 2 — exakte Werte aus Foto e6d8b176
        f"{ts(61,23)}  Trocknung                  81  102.8   79.8   91.4   94.1   32.6   36.3\n"
        f"{ts(71,23)}  Belüften                   38   96.4   72.5   89.3   92.2   32.6   36.5\n"
        f"{ts(72,18)}  Haltezeit Belüften        401   97.4   66.7   91.5   94.0   38.5   36.5\n"
        f"{ts(73,18)}  Nachvakuum                392   97.2   61.0   92.5   95.0   36.9   36.4\n"
        f"{ts(76,16)}  Haltezeit Vakuum           79   95.6   81.8   91.9   93.6   34.7   36.4\n"
        f"{ts(77,16)}  Belüften                   50   96.8   79.8   92.8   94.3   33.8   36.3\n"
        f"{ts(80,9)}  Haltezeit Belüften         398   98.0   72.0   94.2   95.7   37.2   36.2\n"
        f"{ts(81,9)}  Nachvakuum                 391   98.3   64.5   95.0   96.5   37.2   36.2\n"
        f"{ts(84,8)}  Haltezeit Vakuum            79   97.0   83.5   93.6   95.0   34.9   36.1\n"
        f"{ts(87,8)}  Belüften                    50   98.8   80.1   94.3   95.5   34.0   36.0\n"
        f"{ts(88,1)}  Haltezeit Belüften         398   99.5   71.9   96.2   97.0   38.8   36.0\n"
        f"{ts(89,1)}  Nachvakuum                 390  100.3   64.3   96.8   98.7   37.3   35.8\n"
        f"{ts(92,1)}  Haltezeit Vakuum            79   98.9   84.6   94.9   96.1   35.0   35.7\n"
        f"{ts(95,1)}  Belüften                    50  100.3   77.6   95.5   96.5   34.0   35.7\n"
        f"{ts(97,28)}  Programmende             1026  101.3   56.6   99.7  101.0   43.7   35.5\n"
        f"\n"
        f"Keine prozessrelevante Störung aufgetreten\n"
        f"Unterschrift :           Freigabe : Ja    Nein\n"
    )


def pst_prog6_passage(lfd_nr, start_hh, start_mm):
    # Seite 1 nach Foto ca28da79/e6d8b176: LFD 12080, 10.06.2026, 09h00 min
    t0 = datetime.now().replace(hour=start_hh, minute=start_mm, second=0, microsecond=0)
    def ts(m, s): return (t0 + timedelta(minutes=m, seconds=s)).strftime("%H . %M . %S")
    page2_header = (
        f"Chargen Protokoll                    UNIKLINIK_ESSEN_10980        Seite 2/2\n"
        f"                                     Chargendauer         94.4 min\n"
        f"Lfd.Nr.      {lfd_nr}                Sterilisierdauer     20.0 min\n"
        f"Programm     6   Passage Gen-Technik VAR1-K  max. Sterilisiertemperatur  122.9 C\n"
        f"Datum/Zeit   {t0.strftime('%d . %m . %Y')}   {start_hh:02d} h{start_mm:02d} min   min. Sterilisiertemperatur  121.3 C\n"
        f"\n"
        f"Zeit         Phase                    P2      T1    T2    T3    T4    T5    T6\n"
        f"                                    [mbar]  [C]   [C]   [C]   [C]   [C]   [C]\n"
        f"-------------------------------------------------------------------------------\n"
    )
    return (
        f"Chargen Protokoll                    UNIKLINIK_ESSEN_10980        Seite 1/2\n"
        f"Steri-Nr.    10980                   Chargendauer         94.4 min\n"
        f"Benutzer     ALLGEMEIN               Sterilisierdauer     20.0 min\n"
        f"                                     max. Sterilisiertemperatur  122.9 C\n"
        f"Lfd.Nr.      {lfd_nr}\n"
        f"Programm     6   Passage Gen-Technik VAR1-K  Endwert Fo T4         40.7 min\n"
        f"                                     min. Sterilisiertemperatur  121.3 C\n"
        f"Datum/Zeit   {t0.strftime('%d . %m . %Y')}   {start_hh:02d} h{start_mm:02d} min\n"
        f"Artikel-Bez.\n"
        f"Chargen-Bez.\n"
        f"\n"
        f"Zeit         Phase                    P2      T1    T2    T3    T4    T5    T6\n"
        f"                                    [mbar]  [C]   [C]   [C]   [C]   [C]   [C]\n"
        f"-------------------------------------------------------------------------------\n"
        f"{ts(0,17)}  1. Vorvakuum              897   39.8   23.6   22.8   22.6   32.0   35.1\n"
        f"{ts(15,54)}  Aufheizen                  69   38.2   23.6   22.2   22.6   32.7   35.8\n"
        f"{ts(33,38)}  Aufheizen                1167  121.8  119.6  119.2  119.8   33.2   36.8\n"
        f"{ts(40,38)}  Aufheizen                2088  121.8  121.7  122.2  122.5   33.3   37.0\n"
        f"{ts(41,38)}  Sterilisation (Zeit)     2167  121.8  121.6  122.1  122.4   32.8   36.7\n"
        f"{ts(42,38)}  Sterilisation (Zeit)     2204  121.9  121.8  122.3  122.5   32.9   36.7\n"
        f"{ts(43,38)}  Sterilisation (Zeit)     2218  122.0  121.9  122.4  122.5   33.1   36.8\n"
        f"{ts(44,38)}  Sterilisation (Zeit)     2218  122.1  121.9  122.4  122.5   32.9   36.8\n"
        f"{ts(45,38)}  Sterilisation (Zeit)     2221  122.2  122.0  122.5  122.5   33.0   36.9\n"
        f"{ts(46,38)}  Sterilisation (Zeit)     2225  122.1  121.9  122.3  122.4   33.1   36.9\n"
        f"{ts(47,38)}  Sterilisation (Zeit)     2228  122.1  121.9  122.3  122.4   33.2   37.0\n"
        f"{ts(48,38)}  Sterilisation (Zeit)     2231  122.1  121.9  122.3  122.4   33.2   37.0\n"
        f"{ts(49,38)}  Sterilisation (Zeit)     2229  122.1  121.9  122.3  122.4   33.3   37.1\n"
        f"{ts(50,38)}  Sterilisation (Zeit)     2233  122.2  122.0  122.4  122.5   33.3   37.1\n"
        f"{ts(51,38)}  Sterilisation (Zeit)     2230  122.2  122.0  122.4  122.5   33.4   37.2\n"
        f"{ts(55,38)}  Sterilisation (Zeit)     2226  122.1  121.8  122.2  122.3   33.5   37.3\n"
        f"{ts(59,38)}  Sterilisation (Zeit)     2208  122.0  121.8  122.1  122.2   33.5   37.3\n"
        f"{ts(60,38)}  Druckentlasten           2000   44.2   34.6   72.0   44.3   32.2   35.4\n"
        f"{ts(65,32)}  Nachvakuum               1088   52.1   38.4   73.6   73.3   31.9   34.7\n"
        + page2_header +
        f"{ts(70,32)}  Druckentlasten            986   41.9   32.4   75.3   44.7   32.2   35.4\n"
        f"{ts(72,20)}  Belüften                   40   88.3   72.1   91.4   89.6   31.5   34.2\n"
        f"{ts(75,20)}  Haltezeit Belüften        399   94.1   65.3   92.8   90.2   31.2   34.0\n"
        f"{ts(78,30)}  Nachvakuum                 79   96.5   79.8   94.3   91.8   31.0   33.8\n"
        f"{ts(82,30)}  Haltezeit Vakuum           79   95.3   81.2   93.0   90.5   30.8   33.6\n"
        f"{ts(85,30)}  Belüften                   50   96.8   77.4   93.7   91.3   30.6   33.4\n"
        f"{ts(86,28)}  Haltezeit Belüften        397   97.2   70.1   94.5   92.4   30.5   33.3\n"
        f"{ts(87,28)}  Nachvakuum                391   96.8   63.5   95.3   92.9   30.4   33.2\n"
        f"{ts(90,28)}  Haltezeit Vakuum           79   96.5   83.1   94.0   91.8   30.3   33.1\n"
        f"{ts(91,28)}  Trocknung                  80   97.4   80.5   94.8   92.4   30.2   33.0\n"
        f"{ts(93,16)}  Belüften                   38   95.8   74.6   93.7   91.3   30.1   32.9\n"
        f"{ts(94,24)}  Programmende             1028  101.8   58.3   99.2   97.4   30.0   32.8\n"
        f"\n"
        f"Keine prozessrelevante Störung aufgetreten\n"
        f"Unterschrift :           Freigabe : Ja    Nein\n"
    )


def pst_prog7_futter(lfd_nr, start_hh, start_mm):
    # Exakt nach Foto 00190b45: LFD 12085, 12.06.2026, 09h07 min
    t0 = datetime.now().replace(hour=start_hh, minute=start_mm, second=0, microsecond=0)
    def ts(m, s): return (t0 + timedelta(minutes=m, seconds=s)).strftime("%H . %M . %S")
    return (
        f"Chargen Protokoll                    UNIKLINIK_ESSEN_10980        Seite 1/1\n"
        f"Steri-Nr.    10980                   Chargendauer         65.6 min\n"
        f"Benutzer     ALLGEMEIN               Sterilisierdauer      5.0 min\n"
        f"                                     max. Sterilisiertemperatur  134.9 C\n"
        f"Lfd.Nr.      {lfd_nr}\n"
        f"Programm     7   Futter 134C          Endwert Fo T2         157.2 min\n"
        f"                                     min. Sterilisiertemperatur  134.2 C\n"
        f"Datum/Zeit   {t0.strftime('%d . %m . %Y')}   {start_hh:02d} h{start_mm:02d} min\n"
        f"Artikel-Bez.\n"
        f"Chargen-Bez.\n"
        f"\n"
        f"Zeit         Phase                    P2      T1    T2    T3    T4    T5    T6\n"
        f"                                    [mbar]  [C]   [C]   [C]   [C]   [C]   [C]\n"
        f"-------------------------------------------------------------------------------\n"
        f"{ts(0,12)}  1. Druckanstieg           989   52.4   41.8   46.1   47.9   34.5   35.5\n"
        f"{ts(2,41)}  1. Vorvakuum             1500   90.8   78.3   93.2   92.4   34.1   35.5\n"
        f"{ts(3,20)}  1. Vorvakuum             1124   79.4   80.7   93.6   94.4   34.2   35.5\n"
        f"{ts(6,6)}   2. Druckanstieg            80   77.5   68.1   72.6   74.2   33.8   35.4\n"
        f"{ts(13,9)}  2. Vorvakuum             1502  111.0  111.4  110.7  110.3   33.1   35.2\n"
        f"{ts(13,48)}  2. Vorvakuum             1125  109.5  104.1  105.5  106.4   33.2   35.2\n"
        f"{ts(17,18)}  3. Druckanstieg           121  100.4   79.8   84.5   86.9   33.0   35.5\n"
        f"{ts(24,9)}  3. Vorvakuum             1501  111.9  111.5  111.1  110.5   32.9   35.8\n"
        f"{ts(24,50)}  3. Vorvakuum             1125  111.6  106.4  106.1  107.2   32.9   35.9\n"
        f"{ts(28,4)}  Aufheizen                  120  103.9   90.0   86.7   88.7   32.8   36.2\n"
        f"{ts(38,55)}  Aufheizen                2122  122.0  121.7  121.4  121.4   32.7   36.5\n"
        f"{ts(43,45)}  Sterilisation (Zeit)     3026  133.9  134.3  133.4  133.3   32.8   36.7\n"
        f"{ts(44,45)}  Sterilisation (Zeit)     3072  134.5  134.7  134.1  134.1   32.9   36.7\n"
        f"{ts(45,45)}  Sterilisation (Zeit)     3080  134.7  134.8  134.1  134.1   33.1   36.8\n"
        f"{ts(46,45)}  Sterilisation (Zeit)     3075  134.6  134.8  134.1  134.1   32.9   36.8\n"
        f"{ts(47,45)}  Sterilisation (Zeit)     3078  134.7  134.8  134.1  134.1   33.0   36.9\n"
        f"{ts(48,45)}  Druckentlasten           3054  134.4  134.6  134.0  133.9   33.1   36.9\n"
        f"{ts(52,37)}  Nachvakuum               1125  120.0  109.6  113.7  115.6   33.2   37.4\n"
        f"{ts(57,20)}  Trocknung                 100  101.2   92.8   93.7   93.5   33.5   38.5\n"
        f"{ts(63,20)}  Belüften                   40  113.7   99.1   90.2   91.2   33.4   39.2\n"
        f"{ts(65,49)}  Programmende             1028  114.3   81.8  101.2  101.9   44.3   39.2\n"
        f"\n"
        f"Keine prozessrelevante Störung aufgetreten\n"
        f"Unterschrift :           Freigabe : Ja    Nein\n"
    )


# ---------------------------------------------------------------------------
# Programm-Listen und Generatoren
# ---------------------------------------------------------------------------

PROGRAMS = [
    ("Instrumente 134°C", prog_instrumente_134, 33, 3),
    ("Bowie Dick",        prog_bowie_dick,      20, 2),
    ("Instrumente 121°C", prog_instrumente_121, 42, 4),
    ("Aufheizen & VPR",   prog_vpr,             46, 3),
]

PROGRAMS_PST = [
    ("Aufheizprogramm 121C", pst_prog0_aufheiz,   34, 0),
    ("Vakuumtest",           pst_prog1_vakuumtest, 22, 0),
    ("Kaefige 121C",         pst_prog2_kaefige,    97, 0),
    ("Passage VAR1-K",       pst_prog6_passage,    94, 0),
    ("Futter 134C",          pst_prog7_futter,     65, 0),
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


def build_protocol_pst(i, start_lfd=START_LFD_NR, sequence=None):
    prog_idx = sequence[i] if sequence is not None else ROTATION_PST[i % len(ROTATION_PST)]
    name, func, base_min, _ = PROGRAMS_PST[prog_idx]
    lfd_nr = start_lfd + i
    now = datetime.now()
    text = func(lfd_nr, now.hour, now.minute)
    return lfd_nr, name, base_min, 0, text


def encode_protocol(text):
    return b'\xff\xfe' + text.encode('utf-16-le')


def send_protocol(host, port, raw_bytes, timeout=10):
    sock = socket.create_connection((host, port), timeout=timeout)
    try:
        sock.sendall(raw_bytes)
    finally:
        sock.close()


def send_via_lpd(host, raw_bytes, queue="lp1", timeout=10):
    """Sendet Protokoll via RFC 1179 LPD-Handshake an Port 5150 (intern)."""
    port = 5150
    s = socket.create_connection((host, port), timeout=timeout)
    try:
        job_id = 1
        s.sendall(f"\x02{queue}\n".encode())
        s.recv(1)
        ctrl = f"Htest\nPdocucontrol\nJtest_pst\nldfA00{job_id}test\n"
        ctrl_bytes = ctrl.encode()
        s.sendall(f"\x02{len(ctrl_bytes)} cfA00{job_id}test\n".encode())
        s.recv(1)
        s.sendall(ctrl_bytes)
        s.sendall(b"\x00")
        s.recv(1)
        s.sendall(f"\x03{len(raw_bytes)} dfA00{job_id}test\n".encode())
        s.recv(1)
        s.sendall(raw_bytes)
        s.sendall(b"\x00")
        s.recv(1)
    finally:
        s.close()


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
                        help=f"Erste Chargennummer BELIMED (default: {START_CHARGE})")
    parser.add_argument("--start-lfd", type=int, default=START_LFD_NR,
                        help=f"Erste Lfd.Nr. PST (default: {START_LFD_NR})")
    parser.add_argument("--sequence", default=None,
                        help="Komma-Liste Programm-Indizes (BELIMED: 0=Instr134, 1=BowieDick, 2=Instr121, 3=VPR; "
                             "PST: 0=Aufheiz, 1=Vakuumtest, 2=Kaefige, 3=Passage, 4=Futter), "
                             "ueberschreibt --count und Standard-Rotation, z.B. '3,0,0,1'")
    parser.add_argument("--format", choices=["old", "pst"], default="old",
                        help="Protokollformat: 'old'=BELIMED, 'pst'=Chargen Protokoll UNIKLINIK_ESSEN (default: old)")
    parser.add_argument("--via-lpd", action="store_true",
                        help="Sende via LPD-Handshake (Port 5150) statt TCP/9100")
    parser.add_argument("--dry-run",  action="store_true",   help="Protokolle auf stdout ausgeben, nicht senden")
    args = parser.parse_args()

    sequence = None
    if args.sequence:
        sequence = [int(x) for x in args.sequence.split(",")]
        args.count = len(sequence)

    print(f"DocuControl Test-Chargen-Sender")
    print(f"Format: {args.format.upper()}  |  Ziel: {args.host}:{args.port}  |  "
          f"Chargen: {args.count}  |  Interval: {args.interval}s")
    if args.via_lpd:
        print(f"Modus: LPD-Handshake (Port 5150)")
    if args.dry_run:
        print("MODUS: Dry-Run (kein TCP-Send)\n")
    print("-" * 60)

    for i in range(args.count):
        if args.format == "pst":
            lfd_nr, prog_name, ende_mm, _, text = build_protocol_pst(
                i, args.start_lfd, sequence)
            charge_display = f"LFD{lfd_nr}"
        else:
            charge_nr, prog_name, ende_mm, ende_ss, text = build_protocol(
                i, args.start_charge, sequence)
            charge_display = f"CH{charge_nr:06d}"

        raw = encode_protocol(text)
        duration_str = f"{ende_mm} min"

        if args.dry_run:
            print(f"\n{'='*60}")
            print(f"{charge_display}  |  {prog_name}  |  Laufzeit {duration_str}")
            print(f"{'='*60}")
            print(text)
        else:
            try:
                if args.via_lpd:
                    send_via_lpd(args.host, raw)
                else:
                    send_protocol(args.host, args.port, raw)
                print(f"[{i+1:02d}/{args.count}]  {charge_display}  |  {prog_name:30s}  |  "
                      f"Laufzeit {duration_str:8s}  |  {len(raw):5d} Bytes  |  OK")
            except Exception as e:
                print(f"[{i+1:02d}/{args.count}]  {charge_display}  FEHLER: {e}")

        if not args.dry_run and i < args.count - 1:
            print(f"         Warte {args.interval}s ...")
            time.sleep(args.interval)

    print("-" * 60)
    if not args.dry_run:
        print(f"Fertig. {args.count} Chargen gesendet.")
    else:
        print(f"Dry-Run abgeschlossen.")


if __name__ == "__main__":
    main()
