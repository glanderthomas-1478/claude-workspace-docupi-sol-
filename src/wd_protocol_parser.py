#!/usr/bin/env python3
"""
DocuPi-3000 — WD/RDG Chargenprotokoll-Parser

Parst Chargenprotokolle von Belimed Waschdesinfektoren (WD290, WD390, etc.)
aus HyperTerminal-Aufzeichnungen (.ht, UTF-16LE) oder Klartext (RS232-Stream).

Datenmodell: siehe plans/2026-03-27-wd390-parser-und-pdf.md
"""

import re
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("docupi.wd_parser")

# --- Regex-Patterns fuer Kopfdaten ---
RE_OPERATOR = re.compile(r"operation company\s*:(.+?)(?=machine type)", re.IGNORECASE | re.DOTALL)
RE_MACHINE_TYPE = re.compile(r"machine type\s*:(\S+)", re.IGNORECASE)
RE_USER = re.compile(r"(?<!\w)user\s*:(\S+)", re.IGNORECASE)
RE_MACHINE_NR = re.compile(r"machine no\s*\.\s*:(\d+)", re.IGNORECASE)
RE_CHARGE = re.compile(r"charge no\.\s*:(\d+)", re.IGNORECASE)
RE_PROGRAM = re.compile(r"program name\s*:(.+?)(?=program start)", re.IGNORECASE | re.DOTALL)
RE_START = re.compile(r"program start\s*:(\d{2}:\d{2}:\d{2})\s+(\d{2}\.\d{2}\.\d{2})", re.IGNORECASE)
RE_END = re.compile(r"program end\s*:(\d{2}:\d{2}:\d{2})\s+(\d{2}\.\d{2}\.\d{2})", re.IGNORECASE)
RE_VERSION = re.compile(r"progr\.no\./version\s*:(\d+)/([\d.]+)", re.IGNORECASE)
RE_RACK = re.compile(r"rack\s*:(\w+)", re.IGNORECASE)
RE_RESULT = re.compile(r"program cycle\s*:(.+?)(?=\d+\.\d+\s+\d{2}:)", re.IGNORECASE | re.DOTALL)

# --- Regex-Patterns fuer Prozessschritte ---
RE_STEP_HEADER = re.compile(r"(\d+\.\d+)\s+(\d{2}:\d{2}:\d{2})\s+([\w\s]+?)(?=\d+\.\d+\s|$)")
RE_STEP_TIME = re.compile(r"step time\s+nom\.\s*(\d+)\s*sec\s+act\.\s*(\d+)\s*sec", re.IGNORECASE)
RE_TEMP_NOM = re.compile(r"temperature nominal\s+min\.\s*([\d.]+)\s*.{1,2}C\s+max\.\s*([\d.]+)\s*.{1,2}C", re.IGNORECASE)
RE_TEMP_ACT = re.compile(r"temperature actual\s+min\.\s*([\d.]+)\s*.{1,2}C\s+max\.\s*([\d.]+)\s*.{1,2}C", re.IGNORECASE)
RE_DOSING = re.compile(r"nom\.\s*(\d+)\s*ml\s+act\.\s*(\d+)\s*ml", re.IGNORECASE)
RE_CONDUCT = re.compile(r"max\.\s*([\d.]+)\s*.{1,3}S/cm\s*act\.\s*([\d.]+)\s*.{1,3}S/cm", re.IGNORECASE)
RE_A0 = re.compile(r"A0\s*Value\s+nom\.\s*(\d+)\s+act\.\s*(\d+)", re.IGNORECASE)


def decode_ht_file(path: str) -> str:
    """Liest HyperTerminal .ht-Datei und extrahiert den UTF-16LE-Klartext.

    Der .ht-Header (COM-Port-Config etc.) wird uebersprungen.
    Die Suche beginnt beim UTF-16LE-kodierten Marker 'belimed'.
    """
    path = Path(path)
    raw = path.read_bytes()

    marker = "belimed".encode("utf-16-le")
    offset = raw.find(marker)
    if offset == -1:
        logger.error("Marker 'belimed' nicht gefunden in %s", path)
        raise ValueError(f"Kein WD-Protokoll in {path} gefunden (Marker 'belimed' fehlt)")

    chunk = raw[offset:]
    text = chunk.decode("utf-16-le", errors="replace")

    # Steuerzeichen und Binaer-Muell am Ende abschneiden
    text = _normalize_text(text)
    logger.info("HT-Datei dekodiert: %d Zeichen aus %s", len(text), path.name)
    return text


def parse_wd_protocol(text: str) -> dict:
    """Parst WD/RDG-Chargenprotokoll aus Klartext.

    Akzeptiert sowohl den Output von decode_ht_file() als auch
    direkt gelesenen RS232-Text.
    """
    text = _normalize_text(text)
    header = _parse_header(text)
    steps = _parse_steps(text)
    kpis = _calculate_kpis(steps, header)

    result = {
        "machine_type": "wd",
        **header,
        "steps": steps,
        "kpi": kpis,
    }

    logger.info(
        "WD-Protokoll geparst: %s Charge %s, %d Schritte, Ergebnis: %s",
        result.get("machine_model", "?"),
        result.get("charge_nr", "?"),
        len(steps),
        result.get("result", "?"),
    )
    return result


def parse_ht_file(path: str) -> dict:
    """Convenience: Liest .ht-Datei und parst das Protokoll in einem Schritt."""
    text = decode_ht_file(path)
    return parse_wd_protocol(text)


# ---------------------------------------------------------------------------
# Interne Hilfsfunktionen
# ---------------------------------------------------------------------------

def _normalize_text(text: str) -> str:
    """Entfernt Steuerzeichen und normalisiert Whitespace."""
    # CR als Zeilenumbruch behandeln (\r -> \n)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Steuerzeichen entfernen (ausser Newline, Tab, Space)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    # Alles ab "signature" + etwas Puffer abschneiden (Ende des Protokolls)
    sig_match = re.search(r"signature", text, re.IGNORECASE)
    if sig_match:
        # Noch die Freigabe-Zeile mitnehmen
        end = text.find("\n", sig_match.end() + 50)
        if end == -1:
            end = min(sig_match.end() + 200, len(text))
        text = text[:end]
    # Unicode-Replacement-Zeichen entfernen
    text = text.replace("\ufffd", "")
    return text


def _parse_datetime(time_str: str, date_str: str) -> str:
    """Konvertiert '11:08:39' + '27.03.26' zu ISO-Format '2026-03-27T11:08:39'."""
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%y %H:%M:%S")
        return dt.isoformat()
    except ValueError:
        logger.warning("Datum/Zeit nicht parsbar: %s %s", time_str, date_str)
        return f"{date_str} {time_str}"


def _parse_header(text: str) -> dict:
    """Extrahiert Kopfdaten aus dem Protokolltext."""
    header = {}

    m = RE_OPERATOR.search(text)
    if m:
        header["operator"] = m.group(1).strip()

    m = RE_MACHINE_TYPE.search(text)
    if m:
        header["machine_model"] = m.group(1).strip()

    m = RE_USER.search(text)
    if m:
        header["user"] = m.group(1).strip()

    m = RE_MACHINE_NR.search(text)
    if m:
        header["machine_nr"] = m.group(1).strip()

    m = RE_CHARGE.search(text)
    if m:
        header["charge_nr"] = m.group(1).strip()

    m = RE_PROGRAM.search(text)
    if m:
        header["program_name"] = m.group(1).strip()

    m = RE_START.search(text)
    if m:
        header["cycle_start"] = _parse_datetime(m.group(1), m.group(2))
        header["cycle_start_time"] = m.group(1)
        header["cycle_start_date"] = m.group(2)

    m = RE_END.search(text)
    if m:
        header["cycle_end"] = _parse_datetime(m.group(1), m.group(2))
        header["cycle_end_time"] = m.group(1)
        header["cycle_end_date"] = m.group(2)

    m = RE_VERSION.search(text)
    if m:
        header["program_nr"] = m.group(1).strip()
        header["program_version"] = m.group(2).strip()

    m = RE_RACK.search(text)
    if m:
        header["rack"] = m.group(1).strip()

    m = RE_RESULT.search(text)
    if m:
        result_text = m.group(1).strip()
        header["result_detail"] = result_text
        if "without failure" in result_text.lower() or "korrekt" in result_text.lower():
            header["result"] = "BESTANDEN"
        elif "failure" in result_text.lower() or "fehler" in result_text.lower():
            header["result"] = "NICHT BESTANDEN"
        else:
            header["result"] = result_text.upper()

    # Laufzeit berechnen
    if "cycle_start" in header and "cycle_end" in header:
        try:
            t_start = datetime.fromisoformat(header["cycle_start"])
            t_end = datetime.fromisoformat(header["cycle_end"])
            delta = t_end - t_start
            header["cycle_duration_sec"] = int(delta.total_seconds())
            mins, secs = divmod(header["cycle_duration_sec"], 60)
            header["cycle_duration_display"] = f"{mins} min {secs} sec"
        except (ValueError, TypeError):
            pass

    return header


def _parse_steps(text: str) -> list:
    """Parst die Prozessschritte aus dem Protokolltext.

    Strategie: Zeilen nach Step-ID gruppieren. Jede Zeile beginnt mit einer
    Step-ID (z.B. '1.1'). Header-Zeilen haben zusaetzlich eine Uhrzeit.
    Parameter-Zeilen haben nur die Step-ID gefolgt von Leerzeichen.
    """
    lines = text.split("\n")
    step_header_re = re.compile(r"^(\d+\.\d+)\s+(\d{2}:\d{2}:\d{2})\s+(.+)$")
    step_line_re = re.compile(r"^(\d+\.\d+)\s{2,}(.+)$")

    # Schritt-Bloecke sammeln: {(id, time): [zugehoerige Zeilen]}
    blocks = []
    current_block = None

    for line in lines:
        line = line.rstrip()
        if not line:
            continue

        header_match = step_header_re.match(line)
        if header_match:
            step_id = header_match.group(1)
            step_time = header_match.group(2)
            step_name = header_match.group(3).strip()

            # Neuen Block starten
            current_block = {
                "id": step_id,
                "time": step_time,
                "name_raw": step_name,
                "param_lines": [],
            }
            blocks.append(current_block)
            continue

        line_match = step_line_re.match(line)
        if line_match and current_block and line_match.group(1) == current_block["id"]:
            current_block["param_lines"].append(line_match.group(2))

    # Bloecke mit gleicher ID + ohne eigene Parameter in den vorherigen Block mergen
    # (z.B. "1.2 11:13:43 cleaning 1" gefolgt von "1.2 11:13:55 cleaning 1" —
    #  der erste ist eine Vorankuendigung, der zweite hat die Daten)
    merged = []
    for block in blocks:
        if merged and merged[-1]["id"] == block["id"] and not merged[-1]["param_lines"]:
            # Vorheriger Block gleiche ID aber leer — ersetzen
            merged[-1] = block
        elif merged and merged[-1]["id"] == block["id"]:
            # Gleiche ID, vorheriger hat schon Daten — als separaten Durchlauf behalten
            # aber nur wenn der neue auch Daten hat oder einen anderen Namen
            if block["param_lines"] or block["name_raw"] != merged[-1]["name_raw"]:
                merged.append(block)
        else:
            merged.append(block)

    # Bloecke in Step-Dicts umwandeln
    steps = []
    for block in merged:
        param_text = "\n".join(block["param_lines"])
        params = _parse_step_params(param_text)

        name_raw = block["name_raw"]
        step = {
            "id": block["id"],
            "time": block["time"],
            "name": re.sub(r"[^a-z0-9]+", "_", name_raw.lower()).strip("_"),
            "name_display": name_raw.title() if name_raw == name_raw.lower() else name_raw,
            "params": params,
        }
        steps.append(step)

    logger.debug("  %d Schritte erkannt", len(steps))
    return steps


def _parse_step_params(block: str) -> dict:
    """Parst Parameter (step time, temperature, dosierung, etc.) aus einem Schritt-Block."""
    params = {}

    m = RE_STEP_TIME.search(block)
    if m:
        params["step_time"] = {"nom": int(m.group(1)), "act": int(m.group(2)), "unit": "sec"}

    m = RE_TEMP_NOM.search(block)
    if m:
        params["temp_nominal"] = {"min": float(m.group(1)), "max": float(m.group(2)), "unit": "C"}

    m = RE_TEMP_ACT.search(block)
    if m:
        params["temp_actual"] = {"min": float(m.group(1)), "max": float(m.group(2)), "unit": "C"}

    m = RE_DOSING.search(block)
    if m:
        params["dosing"] = {"nom": int(m.group(1)), "act": int(m.group(2)), "unit": "ml"}

    m = RE_CONDUCT.search(block)
    if m:
        params["conductivity"] = {"max": float(m.group(1)), "act": float(m.group(2)), "unit": "uS/cm"}

    m = RE_A0.search(block)
    if m:
        params["a0_value"] = {"nom": int(m.group(1)), "act": int(m.group(2)), "unit": ""}

    return params


def _calculate_kpis(steps: list, header: dict) -> dict:
    """Berechnet KPIs aus den geparsten Schritten."""
    kpis = {}

    # Gesamtlaufzeit aus Header
    if "cycle_duration_sec" in header:
        kpis["total_duration_sec"] = header["cycle_duration_sec"]

    # A0-Wert und Thermodesinfektion finden
    for step in steps:
        params = step.get("params", {})

        if "a0_value" in params:
            a0 = params["a0_value"]
            kpis["a0_value"] = {
                "nom": a0["nom"],
                "act": a0["act"],
                "passed": a0["act"] >= a0["nom"],
            }

        if "conductivity" in params:
            cond = params["conductivity"]
            kpis["conductivity"] = {
                "max_allowed": cond["max"],
                "act": cond["act"],
                "passed": cond["act"] <= cond["max"],
            }

        # Thermodesinfektion-Temperaturen (Schritt mit A0 oder 'thermal' im Namen)
        if "a0_value" in params or "thermal" in step.get("name", ""):
            if "temp_actual" in params and "temp_nominal" in params:
                t_act = params["temp_actual"]
                t_nom = params["temp_nominal"]
                kpis["thermal_disinfection_temp"] = {
                    "min": t_act["min"],
                    "max": t_act["max"],
                    "nom_min": t_nom["min"],
                    "nom_max": t_nom["max"],
                    "passed": t_act["min"] >= t_nom["min"] and t_act["max"] <= t_nom["max"],
                }

    # Dosiermengen sammeln
    dosing_steps = []
    for step in steps:
        if "dosing" in step.get("params", {}):
            d = step["params"]["dosing"]
            dosing_steps.append({
                "step": step["name_display"],
                "nom": d["nom"],
                "act": d["act"],
                "passed": d["act"] >= d["nom"],
            })
    if dosing_steps:
        kpis["dosing"] = dosing_steps

    return kpis


# --- CLI fuer Schnelltests ---
if __name__ == "__main__":
    import sys
    import json

    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) < 2:
        print("Verwendung: python wd_protocol_parser.py <datei.ht>")
        sys.exit(1)

    path = sys.argv[1]
    if path.endswith(".ht"):
        result = parse_ht_file(path)
    else:
        text = Path(path).read_text(encoding="utf-8")
        result = parse_wd_protocol(text)

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
