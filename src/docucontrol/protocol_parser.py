#!/usr/bin/env python3
"""
DocuPi-3000 - Protocol Parser v4
Parst Belimed-Sterilisator-Protokolldaten in zwei Formaten:

Format 1 (BELIMED / altes Format):
  BELIMED CHARGEN-DOKUMENTATION
  Betreiber     : Helios Krefeld
  Maschinen-Typ : 9-6-18 HS2    Nr:27163
  Laufende Nr.  : 021667
  Programm      :  1: Instrumente 134°C
  ...
  Programmstart : 19.03.2026 / 07:49
   Zeit  Phase    Kammer       mbara  T2 °C
    m:s           Luftnachweisg.      T3 °C
  -----------------------------------------
    0:02 1. Vorvakuum           1022   62.3
                                       56.1
  PROGRAMM KORREKT BEENDET
  Freigabe: J / N         Datum:

Format 2 (PST / UNIKLINIK_ESSEN):
  Chargen Protokoll                    UNIKLINIK_ESSEN_10980        Seite 1/1
  Steri-Nr.    10980                   Chargendauer         65.6 min
  Benutzer     ALLGEMEIN               Sterilisierdauer      5.0 min
  Lfd.Nr.      12085
  Programm     7   Futter 134C
  Datum/Zeit   12 . 06 . 2026   09 h07 min
  Zeit         Phase          P2      T1    T2    T3    T4    T5    T6
  09 . 07 . 12  1. Druckanstieg       989   52.4   41.8   46.1   47.9   34.5   35.5
  Keine prozessrelevante Störung aufgetreten
  Freigabe : Ja    Nein
"""

import re
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# PST-Format Regex (Modul-Ebene, kompiliert einmalig)
# ---------------------------------------------------------------------------

# 6-Temperaturspalten: HH.MM.SS Phase P2 T1 T2 T3 T4 T5 T6
# Zeit-Trennzeichen: Punkt oder Doppelpunkt, mit optionalen Leerzeichen
_PST_ROW_6 = re.compile(
    r'^\s*(\d{1,2})\s*[.:]\s*(\d{2})\s*[.:]\s*(\d{2})\s+'
    r'(.+?)\s{2,}'
    r'(\d{1,5})\s+'
    r'([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$'
)

# 2-Spalten (Vakuumtest): HH.MM.SS Phase P2 T1
_PST_ROW_2 = re.compile(
    r'^\s*(\d{1,2})\s*[.:]\s*(\d{2})\s*[.:]\s*(\d{2})\s+'
    r'(.+?)\s{2,}'
    r'(\d{1,5})\s+'
    r'([\d.]+)\s*$'
)


def _clean_wide_chars(text):
    """Remove wide-char artifacts (every other char is a space in some fields)."""
    if not text:
        return text
    if len(text) > 6:
        stripped = text.strip()
        if len(stripped) > 4:
            pairs = 0
            for i in range(0, len(stripped) - 1, 2):
                if stripped[i] != ' ' and (stripped[i+1] == ' ' or i+1 == len(stripped)-1):
                    pairs += 1
            total_nonspace = sum(1 for c in stripped if c != ' ')
            if pairs >= total_nonspace * 0.7 and total_nonspace >= 3:
                result = stripped[::2].strip()
                if result:
                    return result
    return text


def apply_config_overrides(protocol_data, config):
    """Override parsed values with config settings (if set by user)."""
    pdf_cfg = config.get("pdf", {})

    if pdf_cfg.get("kundenname"):
        protocol_data["betreiber"] = pdf_cfg["kundenname"]

    if pdf_cfg.get("abteilung"):
        protocol_data["abteilung"] = pdf_cfg["abteilung"]

    if pdf_cfg.get("maschinen_typ"):
        protocol_data["maschinen_typ"] = pdf_cfg["maschinen_typ"]
        protocol_data["device_name"] = pdf_cfg["maschinen_typ"]

    if pdf_cfg.get("maschinen_nr"):
        protocol_data["maschinen_nr"] = pdf_cfg["maschinen_nr"]

    return protocol_data


def _parse_header_value(line, key):
    """Extract value after 'Key : Value' pattern."""
    m = re.search(rf'{key}\s*:\s*(.+)', line, re.IGNORECASE)
    if m:
        return _clean_wide_chars(m.group(1).strip())
    return ""


# ---------------------------------------------------------------------------
# PST-Format: Erkennung + Parser
# ---------------------------------------------------------------------------

def _detect_pst_format(raw_text):
    """True wenn Belimed PST-Format (Chargen Protokoll / UNIKLINIK_ESSEN)."""
    return "Chargen Protokoll" in raw_text or "UNIKLINIK_ESSEN" in raw_text


def _parse_pst_header(lines):
    """Parst den Header-Block eines PST-Protokolls. Gibt Partial-Dict zurück."""
    h = {
        "maschinen_nr": "", "benutzer": "", "charge_nr": "",
        "program_nr": "", "program_name": "", "cycle_start": "",
        "cycle_duration": "", "sterilization_duration": "",
        "temp_max": 0.0, "temp_min": 0.0, "f0_value": 0.0,
        "betreiber": "Uniklinik Essen Tierlabor",
        "abteilung": "", "maschinen_typ": "PST 14-8-12 HS1",
        "device_name": "PST 14-8-12 HS1",
    }
    for line in lines:
        s = line.strip()

        # Steri-Nr.    10980
        m = re.search(r'Steri-Nr\.\s+(\d+)', s)
        if m and not h["maschinen_nr"]:
            h["maschinen_nr"] = m.group(1)

        # Benutzer     ALLGEMEIN
        m = re.match(r'^Benutzer\s+(.+)', s)
        if m and not h["benutzer"]:
            # nur erstes Wort / Token (Benutzer-Zeile hat rechts manchmal Chargendauer)
            val = m.group(1).strip().split()[0] if m.group(1).strip() else ""
            h["benutzer"] = val

        # Lfd.Nr.      12085
        m = re.search(r'Lfd\.Nr\.\s+(\d+)', s)
        if m and not h["charge_nr"]:
            h["charge_nr"] = m.group(1)

        # Programm     7   Futter 134C
        m = re.match(r'^Programm\s+(\d+)\s+(.+)', s)
        if m and not h["program_nr"]:
            h["program_nr"] = m.group(1)
            # Rechte Seite kann "Endwert Fo T2  157.2 min" enthalten — kürzen
            prog_raw = m.group(2).strip()
            # Schneide bei doppeltem Leerzeichen ab (Beginn der rechten Spalte)
            prog_name = re.split(r'\s{3,}', prog_raw)[0].strip()
            h["program_name"] = prog_name

        # Datum/Zeit   12 . 06 . 2026   09 h07 min
        m = re.search(
            r'Datum/Zeit\s+(\d+)\s*[.]\s*(\d+)\s*[.]\s*(\d+)\s+(\d+)\s*h\s*(\d+)\s*min',
            s
        )
        if m and not h["cycle_start"]:
            dd, mm, yyyy, hh, mi = m.groups()
            h["cycle_start"] = f"{dd.zfill(2)}.{mm.zfill(2)}.{yyyy} {hh.zfill(2)}:{mi.zfill(2)}:00"

        # Chargendauer         65.6 min
        m = re.search(r'Chargendauer\s+([\d.,]+)\s*min', s)
        if m and not h["cycle_duration"]:
            h["cycle_duration"] = m.group(1).replace(",", ".") + " min"

        # Sterilisierdauer      5.0 min
        m = re.search(r'Sterilisierdauer\s+([\d.,]+)\s*min', s)
        if m and not h["sterilization_duration"]:
            h["sterilization_duration"] = m.group(1).replace(",", ".") + " min"

        # max. Sterilisiertemperatur  134.9 °C
        m = re.search(r'max\.\s*Sterilisiertemperatur\s+([\d.,]+)', s)
        if m and h["temp_max"] == 0.0:
            h["temp_max"] = float(m.group(1).replace(",", "."))

        # min. Sterilisiertemperatur  134.2 °C
        m = re.search(r'min\.\s*Sterilisiertemperatur\s+([\d.,]+)', s)
        if m and h["temp_min"] == 0.0:
            h["temp_min"] = float(m.group(1).replace(",", "."))

        # Endwert Fo T2   157.2 min  (auch T3 bei Passage)
        m = re.search(r'Endwert Fo T\d+\s+([\d.,]+)', s)
        if m and h["f0_value"] == 0.0:
            h["f0_value"] = float(m.group(1).replace(",", "."))

    return h


def _parse_pst_protocol(raw_text):
    """Parst Belimed PST-Format (UNIKLINIK_ESSEN) und gibt Standard-Dict zurück."""
    result = {
        "device_name": "PST 14-8-12 HS1",
        "charge_nr": "", "program_name": "", "program_nr": "",
        "result": "", "result_detail": "",
        "cycle_start": "", "cycle_end": "", "cycle_duration": "",
        "sterilization_duration": "", "drying_duration": "",
        "temp_min": 0.0, "temp_max": 0.0, "f0_value": 0.0,
        "air_detection_temp": 0.0,
        "betreiber": "Uniklinik Essen Tierlabor",
        "abteilung": "", "maschinen_typ": "PST 14-8-12 HS1",
        "maschinen_nr": "", "benutzer": "", "version": "",
        "sollwerte": {}, "phases": [], "raw_lines": [],
    }

    # Seitentrenner (Form Feed) und NUL-Bytes normalisieren
    raw_text = raw_text.replace("\x0c", "\n").replace(chr(0), "")
    lines = raw_text.replace("\r", "").split("\n")
    result["raw_lines"] = [l for l in lines if l.strip()]

    # Header parsen (beim ersten Auftreten jedes Feldes — Multi-Page-tolerant)
    header_data = _parse_pst_header(lines)
    result.update(header_data)

    # Datenzeilen extrahieren
    phase_lines = []
    for line in lines:
        # Zuerst 6-Spalten probieren (spezifischer)
        m6 = _PST_ROW_6.match(line)
        if m6:
            hh, mi, ss, phase_name, p2, t1, t2, t3, t4, t5, t6 = m6.groups()
            rtc = f"{hh.zfill(2)}:{mi.zfill(2)}:{ss.zfill(2)}"
            entry = {
                "rtc_time": rtc,
                "time_offset": rtc,
                "phase": phase_name.strip(),
                "p2_mbar": int(p2),
                "pressure_mbar": int(p2),
                "t1_c": float(t1),
                "t2_c": float(t2),
                "t3_c": float(t3),
                "t4_c": float(t4),
                "t5_c": float(t5),
                "t6_c": float(t6),
                "temp_c": float(t2),
            }
            phase_lines.append(entry)
            continue

        # Dann 2-Spalten (Vakuumtest)
        m2 = _PST_ROW_2.match(line)
        if m2:
            hh, mi, ss, phase_name, p2, t1 = m2.groups()
            rtc = f"{hh.zfill(2)}:{mi.zfill(2)}:{ss.zfill(2)}"
            entry = {
                "rtc_time": rtc,
                "time_offset": rtc,
                "phase": phase_name.strip(),
                "p2_mbar": int(p2),
                "pressure_mbar": int(p2),
                "t1_c": float(t1),
                "t2_c": None,
                "t3_c": None,
                "t4_c": None,
                "t5_c": None,
                "t6_c": None,
                "temp_c": float(t1),
            }
            phase_lines.append(entry)

    result["phases"] = phase_lines

    # PST: Störungsmeldung hat Vorrang vor "Freigabe : Ja  Nein" (beides steht immer als Formularzeile)
    for line in lines:
        upper = line.upper().strip()
        if 'PROZESSRELEVANTE STÖRUNG AUFGETRETEN' in upper and 'KEINE PROZESSRELEVANTE' not in upper:
            result["result"] = "ZYKLUS NICHT BESTANDEN"
            result["result_detail"] = line.strip()
            break

    # Ergebnis aus "Freigabe : Ja/Nein" (nur wenn noch kein Ergebnis durch Störungszeile)
    if not result["result"]:
        for line in lines:
            s = line.strip()
            m = re.search(r'Freigabe\s*:\s*(Ja|Nein)', s, re.IGNORECASE)
            if m:
                if m.group(1).lower() == "ja":
                    result["result"] = "ZYKLUS BESTANDEN"
                    result["result_detail"] = "Freigabe: Ja"
                else:
                    result["result"] = "ZYKLUS NICHT BESTANDEN"
                    result["result_detail"] = "Freigabe: Nein"
                break

    if not result["result"] and phase_lines:
        result["result"] = "UNVOLLSTAENDIG"
        result["result_detail"] = "Kein Ergebnis empfangen"

    # cycle_end aus letzter Datenzeile (RTC-Uhrzeit)
    if phase_lines:
        last_rtc = phase_lines[-1]["rtc_time"]
        if result["cycle_start"]:
            date_part = result["cycle_start"].split(" ")[0]
            result["cycle_end"] = f"{date_part} {last_rtc}"
        else:
            result["cycle_end"] = datetime.now().strftime("%d.%m.%Y") + " " + last_rtc

    result["rtc_end_time"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    return result


# ---------------------------------------------------------------------------
# Hauptfunktion (BELIMED-Format — unverändert, nur Dispatch am Anfang)
# ---------------------------------------------------------------------------

def parse_serial_protocol(raw_text, rtc_timestamps=None):
    """Parse Belimed sterilizer protocol and return structured data."""
    result = {
        "device_name": "",
        "charge_nr": "",
        "program_name": "",
        "program_nr": "",
        "result": "",
        "result_detail": "",
        "cycle_start": "",
        "cycle_end": "",
        "cycle_duration": "",
        "sterilization_duration": "",
        "drying_duration": "",
        "temp_min": 0.0,
        "temp_max": 0.0,
        "f0_value": 0.0,
        "air_detection_temp": 0.0,
        "betreiber": "",
        "abteilung": "",
        "maschinen_typ": "",
        "maschinen_nr": "",
        "benutzer": "",
        "version": "",
        "sollwerte": {},
        "phases": [],
        "raw_lines": [],
    }

    # Strip NUL bytes (sterilizer sends some fields in UTF-16LE with 0x00 padding)
    raw_text = raw_text.replace(chr(0), "")

    # --- Format-Dispatch: PST-Format hat eigenen Parser ---
    if _detect_pst_format(raw_text):
        return _parse_pst_protocol(raw_text)

    # If buffer contains multiple protocols, take only the last complete one
    import re as _re
    _parts = _re.split(r"(?=BELIMED CHARGEN-DOKUMENTATION)", raw_text)
    _parts = [p for p in _parts if p.strip() and len(p.strip()) > 200]
    if len(_parts) > 1:
        raw_text = _parts[-1]
    lines = raw_text.replace("\r", "").split("\n")
    result["raw_lines"] = [l for l in lines if l.strip()]

    # --- Parse Header ---
    for line in lines:
        stripped = line.strip()

        # Betreiber
        if stripped.startswith("Betreiber"):
            result["betreiber"] = _parse_header_value(stripped, "Betreiber")
            _name_fixes = {
                'Helios Krefe': 'Helios Krefeld',
                'Helios Kref': 'Helios Krefeld',
            }
            for short, full in _name_fixes.items():
                if result['betreiber'] and (result['betreiber'] == short or result['betreiber'].startswith(short)):
                    result['betreiber'] = full
                    break

        # Abteilung
        elif stripped.startswith("Abteilung"):
            result["abteilung"] = _parse_header_value(stripped, "Abteilung")

        # Maschinen-Typ + Nr
        elif "Maschinen-Typ" in stripped:
            m = re.search(r'Maschinen-Typ\s*:\s*(.+?)(?:\s+Nr\s*:\s*(\d+))?$', stripped)
            if m:
                result["maschinen_typ"] = m.group(1).strip()
                result["device_name"] = m.group(1).strip()
                if m.group(2):
                    result["maschinen_nr"] = m.group(2)

        # Laufende Nr. (= Chargennummer)
        elif "Laufende Nr" in stripped:
            m = re.search(r'Laufende Nr\.\s*:\s*(\d+)', stripped)
            if m:
                result["charge_nr"] = m.group(1)

        # Benutzer
        elif stripped.startswith("Benutzer"):
            result["benutzer"] = _parse_header_value(stripped, "Benutzer")

        # Programm
        elif stripped.startswith("Programm") and "Ende" not in stripped and "start" not in stripped.lower():
            m = re.search(r'Programm\s*:\s*(.+)', stripped)
            if m:
                prog = m.group(1).strip()
                result["program_name"] = prog
                nm = re.match(r'(\d+):\s*(.+)', prog)
                if nm:
                    result["program_nr"] = nm.group(1)
                    result["program_name"] = nm.group(2).strip()

        # Version
        elif stripped.startswith("Version"):
            result["version"] = _parse_header_value(stripped, "Version")

        # Programmstart
        elif "Programmstart" in stripped:
            m = re.search(r'Programmstart\s*:\s*(.+)', stripped)
            if m:
                raw_start = m.group(1).strip()
                raw_start = raw_start.replace(" / ", " ").replace("/ ", " ")
                if len(raw_start.split(" ")) == 2 and ":" in raw_start:
                    date_part, time_part = raw_start.split(" ", 1)
                    if len(time_part) <= 5:
                        time_part += ":00"
                    raw_start = date_part + " " + time_part
                result["cycle_start"] = raw_start

        # Sollwerte
        elif "Sterilisierzeit" in stripped:
            m = re.search(r'Sterilisierzeit\s+(\d+[\.,]\d+)\s*min', stripped)
            if m:
                result["sollwerte"]["sterilisierzeit"] = m.group(1)
                result["sterilization_duration"] = m.group(1) + " min"

        elif "Sterilisiertemp" in stripped and "Sollwert" not in stripped:
            m = re.search(r'Sterilisiertemp\.\s*(\d+[\.,]\d+)', stripped)
            if m:
                result["sollwerte"]["sterilisiertemp"] = float(m.group(1).replace(",", "."))

        elif "Trocknungszeit" in stripped:
            m = re.search(r'Trocknungszeit\s+(\d+[\.,]\d+)\s*min', stripped)
            if m:
                result["sollwerte"]["trocknungszeit"] = m.group(1)
                result["drying_duration"] = m.group(1) + " min"

        elif "Fraktionen" in stripped:
            m = re.search(r'Fraktionen\s+(\d+)', stripped)
            if m:
                result["sollwerte"]["fraktionen"] = m.group(1)

    # --- Parse Result ---
    result_found = False
    for line in lines:
        upper = line.upper().strip()
        if "ABGEBROCHEN" in upper:
            result["result"] = "ZYKLUS NICHT BESTANDEN"
            result["result_detail"] = "PROGRAMM ABGEBROCHEN"
            result_found = True
            break
        elif "PROGRAMM KORREKT BEENDET" in upper:
            result["result"] = "ZYKLUS BESTANDEN"
            result["result_detail"] = "PROGRAMM KORREKT BEENDET"
            result_found = True
        elif "BEENDET" in upper and "PROGRAMM" in upper and not result_found:
            result["result"] = "ZYKLUS BESTANDEN"
            result["result_detail"] = upper.strip()
            result_found = True

    # --- Parse Footer Values ---
    for line in lines:
        m = re.search(r'Min\.\s*Sterilisiertemp\.\s+(\d+[\.,]\d+)', line)
        if m:
            result["temp_min"] = float(m.group(1).replace(",", "."))

        m = re.search(r'Max\.\s*Sterilisiertemp\.\s+(\d+[\.,]\d+)', line)
        if m:
            result["temp_max"] = float(m.group(1).replace(",", "."))

        m = re.search(r'F0-Wert\s+(\d+[\.,]\d+)', line)
        if m:
            result["f0_value"] = float(m.group(1).replace(",", "."))

        m = re.search(r'Zeit\s+(?:ueber|ueb\.?)\s+Soll\w*\s+Kammer\s+(\d+:\d+)', line)
        if m:
            result["sterilization_duration"] = m.group(1)

    # --- Parse Phase Data Lines ---
    phase_pattern = re.compile(
        r'^\s*(\d{1,3}:\d{2})\s+'
        r'(.*?)\s+'
        r'(\d{1,5})\s+'
        r'(\d{1,3}[\.,]\d)'
    )

    standalone_t3 = re.compile(r'^\s{20,}(\d{1,3}[\.,]\d)\s*$')

    phase_lines = []
    last_phase_name = ""

    for i, line in enumerate(lines):
        t3m = standalone_t3.match(line)
        if t3m:
            t3_val = float(t3m.group(1).replace(",", "."))
            if phase_lines:
                phase_lines[-1]["t3_c"] = t3_val
            continue

        m = phase_pattern.match(line)
        if m:
            time_str = m.group(1)
            phase_name = m.group(2).strip()
            p2 = int(m.group(3))
            t2 = float(m.group(4).replace(",", "."))

            if not phase_name:
                phase_name = last_phase_name
            else:
                if phase_name.startswith(">"):
                    phase_name = phase_name.lstrip("> ").strip()
                    if not phase_name:
                        phase_name = last_phase_name
                last_phase_name = phase_name

            rtc_time = None
            if rtc_timestamps:
                for ts_idx, ts_dt in rtc_timestamps:
                    if ts_idx <= i:
                        rtc_time = ts_dt
                    else:
                        break

            entry = {
                "time_offset": time_str,
                "phase": phase_name,
                "p2_mbar": p2,
                "t2_c": t2,
                "t3_c": None,
                "pressure_mbar": p2,
                "temp_c": t2,
            }
            if rtc_time:
                entry["rtc_time"] = rtc_time.strftime("%H:%M:%S")

            phase_lines.append(entry)

    result["phases"] = phase_lines

    # --- Calculate cycle duration ---
    if phase_lines:
        first_t = phase_lines[0]["time_offset"]
        last_t = phase_lines[-1]["time_offset"]
        first_sec = int(first_t.split(":")[0]) * 60 + int(first_t.split(":")[1])
        last_sec = int(last_t.split(":")[0]) * 60 + int(last_t.split(":")[1])
        dur_sec = abs(last_sec - first_sec)
        dur_h = dur_sec // 3600
        dur_min = (dur_sec % 3600) // 60
        dur_s = dur_sec % 60
        result["cycle_duration"] = f"{dur_h:02d}:{dur_min:02d}:{dur_s:02d}"

    # --- Cycle end time ---
    now = datetime.now()
    if result["cycle_start"] and phase_lines:
        try:
            cs = result["cycle_start"]
            start_dt = datetime.strptime(cs.strip(), "%d.%m.%Y %H:%M:%S")
            last_offset = phase_lines[-1]["time_offset"]
            last_parts = last_offset.split(":")
            last_sec = int(last_parts[0]) * 60 + int(last_parts[1])
            end_dt = start_dt + timedelta(seconds=last_sec)
            result["cycle_end"] = end_dt.strftime("%d.%m.%Y %H:%M:%S")
        except Exception:
            result["cycle_end"] = now.strftime("%d.%m.%Y %H:%M:%S")
    elif not result["cycle_end"]:
        result["cycle_end"] = now.strftime("%d.%m.%Y %H:%M:%S")
    result["rtc_end_time"] = now.strftime("%d.%m.%Y %H:%M:%S")

    if not result_found and len(result["phases"]) > 0:
        result["result"] = "UNVOLLSTAENDIG"
        result["result_detail"] = "Kein Ergebnis empfangen"

    return result


# ---------------------------------------------------------------------------
# Autoklavenbuch Programm-Vorauswahl
# ---------------------------------------------------------------------------

_PROGRAM_KEYS = [
    # (key, kategorie, temp_label, keywords, steril_temp_min, steril_temp_max)
    ("futter_75",          "Futter",            "75 °C",          ["futter", "feed"],              70, 80),
    ("futter_121",         "Futter",            "121 °C",         ["futter", "feed"],             118, 124),
    ("futter_134",         "Futter",            "134 °C",         ["futter", "feed"],             131, 137),
    ("einstreu_75",        "Einstreu",          "75 °C",          ["einstreu", "bedding"],         70, 80),
    ("einstreu_121",       "Einstreu",          "121 °C",         ["einstreu", "bedding"],        118, 124),
    ("einstreu_134",       "Einstreu",          "134 °C",         ["einstreu", "bedding"],        131, 137),
    ("fluessigkeiten_121", "Flüssigkeiten",     "121 °C",         ["fl", "liquid", "aqua"],       118, 124),
    ("fluessigkeiten_134", "Flüssigkeiten",     "134 °C",         ["fl", "liquid", "aqua"],       131, 137),
    ("tierkoerper_121",    "Tierkörper",        "121 °C",         ["tier", "animal", "corp"],     118, 124),
    ("tierkoerper_134",    "Tierkörper",        "134 °C",         ["tier", "animal", "corp"],     131, 137),
    ("schleusen",          "Schleusenprogramm", "",               ["schleusen", "passage", "schleuse"], None, None),
    ("kaefige_134",        "Käfige",            "134 °C",         ["käfig", "kafig", "cage", "gestell"], 131, 137),
    ("kaefige_121",        "Käfige",            "121 °C",         ["käfig", "kafig", "cage", "gestell"], 118, 124),
    ("kaefige_normal",     "Käfige",            "Normalprogramm", ["käfig", "kafig", "cage", "normal"], None, None),
]

_STERIL_TEMP_RE = re.compile(
    r'(?:max\.?\s*Sterilisier(?:temperatur)?|Sterilisiertemperatur)\s+([\d.,]+)',
    re.IGNORECASE
)


def preselect_autoclave_program(program_str, raw_text=""):
    """
    Bestimmt den wahrscheinlichsten Autoklavenbuch-Programmschlüssel.

    Rückgabe:
        {
            "program_key": str,    z.B. "futter_134"
            "category": str,       z.B. "Futter"
            "temp_label": str,     z.B. "134 °C"
            "display": str,        z.B. "Futter — 134 °C"
            "confidence": float,   0.0-1.0
        }
    """
    prog_lower = (program_str or "").lower()
    raw_lower = (raw_text or "").lower()

    steril_temp = None
    m = _STERIL_TEMP_RE.search(raw_text or "")
    if m:
        try:
            steril_temp = float(m.group(1).replace(",", "."))
        except ValueError:
            pass

    # PST-Format: Sterilisiertemperatur aus "T1" Spitzenwert oder direkt aus Protokollzeilen
    if steril_temp is None:
        # Suche Zeilen mit Temperaturen nahe Sterilisationsbereich (>118°C)
        for line in (raw_text or "").splitlines():
            nums = re.findall(r'\b(1[12]\d\.\d|13[0-9]\.\d)\b', line)
            if nums:
                try:
                    candidate = float(nums[0])
                    if steril_temp is None or candidate > steril_temp:
                        steril_temp = candidate
                except ValueError:
                    pass

    best_key = None
    best_score = 0

    for key, cat, temp, keywords, t_min, t_max in _PROGRAM_KEYS:
        score = 0
        kw_hit = any(kw in prog_lower or kw in raw_lower for kw in keywords)
        if kw_hit:
            score += 2
        if steril_temp is not None and t_min is not None and t_max is not None:
            if t_min <= steril_temp <= t_max:
                score += 3
            else:
                score -= 1
        if score > best_score:
            best_score = score
            best_key = key

    if best_key is None:
        return {"program_key": "", "category": "", "temp_label": "", "display": "", "confidence": 0.0}

    matched = next((row for row in _PROGRAM_KEYS if row[0] == best_key), None)
    cat = matched[1]
    temp_label = matched[2]
    display = f"{cat} — {temp_label}" if temp_label else cat
    confidence = min(1.0, best_score / 5.0)
    return {
        "program_key": best_key,
        "category": cat,
        "temp_label": temp_label,
        "display": display,
        "confidence": confidence,
    }
