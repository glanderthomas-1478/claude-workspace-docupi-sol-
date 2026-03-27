#!/usr/bin/env python3
"""
Major patch: Adapt DocuPi to real Belimed sterilizer data format.

Fixes:
1. Protocol detection: add "smart" mode that detects end by "Unterschrift:" or trailing blank lines
2. Parser: handle real header format (Betreiber, Maschinen-Typ, Laufende Nr., etc.)
3. Parser: handle empty phase names, ">" prefix, wide-char artifacts
4. Serial receiver: add smart delimiter detection
"""

# ===================================================================
# 1. FIX SERIAL RECEIVER - Add smart protocol end detection
# ===================================================================
with open("/home/belimed/docupi/serial_receiver.py", "r") as f:
    sr = f.read()

# Add smart end detection in the receive loop
# The sterilizer sends "Unterschrift:" near the end, followed by blank lines.
# We detect the protocol end by:
# a) Seeing "Unterschrift:" and then a few seconds of silence, OR
# b) Timeout after last data

# First, fix the check_timeout to also work in formfeed mode as a fallback
old_check = '''    def check_timeout(self):
        cfg = self.config["protocol"]
        if self.last_data_time and self.buffer.strip() and cfg["delimiter"] == "timeout":
            if time.time() - self.last_data_time >= cfg["timeout_seconds"]:
                return True
        return False'''

new_check = '''    def check_timeout(self):
        """Check if protocol is complete by timeout or smart end detection."""
        cfg = self.config["protocol"]
        if not self.last_data_time or not self.buffer.strip():
            return False

        elapsed = time.time() - self.last_data_time

        # Smart detection: if buffer contains "Unterschrift:" we know protocol is nearly done
        # Wait just a few seconds for trailing blank lines
        if "Unterschrift:" in self.buffer and elapsed >= 3:
            logger.info("Smart protocol end: 'Unterschrift:' + 3s silence")
            return True

        # Also detect "PROGRAMM KORREKT BEENDET" or "NICHT BESTANDEN" as near-end markers
        for marker in ["PROGRAMM KORREKT BEENDET", "NICHT BESTANDEN", "PROGRAMM ABGEBROCHEN"]:
            if marker in self.buffer.upper() and elapsed >= 5:
                logger.info(f"Smart protocol end: '{marker}' + 5s silence")
                return True

        # Standard timeout mode
        if cfg["delimiter"] == "timeout":
            if elapsed >= cfg["timeout_seconds"]:
                return True

        # Fallback timeout even in formfeed mode (sterilizer may not send FF)
        if elapsed >= max(cfg["timeout_seconds"], 15):
            if len(self.buffer.strip()) > 100:  # Only if we have substantial data
                logger.info(f"Fallback timeout ({elapsed:.0f}s) with {len(self.buffer)} chars in buffer")
                return True

        return False'''

sr = sr.replace(old_check, new_check)

with open("/home/belimed/docupi/serial_receiver.py", "w") as f:
    f.write(sr)
print("OK: serial_receiver.py smart end detection")


# ===================================================================
# 2. FIX PROTOCOL PARSER - Complete rewrite for real Belimed format
# ===================================================================

PARSER_CODE = r'''#!/usr/bin/env python3
"""
DocuPi-3000 - Protocol Parser v3
Parst echte Belimed-Sterilisator-Protokolldaten.

Echtes Format:
  BELIMED CHARGEN-DOKUMENTATION
  Betreiber     : Helios Krefeld
  Maschinen-Typ : 9-6-18 HS2    Nr:27163
  Laufende Nr.  : 021667
  Programm      :  1: Instrumente 134°C
  ...
  Programmstart : 19.03.2026 / 07:49
  ...
   Zeit  Phase    Kammer       mbara  T2 °C
    m:s           Luftnachweisg.      T3 °C
  -----------------------------------------
    0:02 1. Vorvakuum           1022   62.3
                                       56.1
   27:28                        3106  135.1
                                      135.1
  ...
  PROGRAMM KORREKT BEENDET
  Freigabe: J / N         Datum:
  Unterschrift:
"""

import re
from datetime import datetime, timedelta


def _clean_wide_chars(text):
    """Remove wide-char artifacts (every other char is a space in some fields)."""
    # Detect pattern: "H e l i o s" -> "Helios"
    # Only clean if most chars are single-char-then-space
    if not text:
        return text
    if len(text) > 6:
        # Check if it looks like wide chars (char, space, char, space...)
        wide_count = sum(1 for i in range(1, len(text), 2) if text[i] == ' ')
        non_space = sum(1 for c in text if c != ' ')
        if wide_count > non_space * 0.6 and non_space > 2:
            return text[::2].strip()  # Take every other char
    return text


def _parse_header_value(line, key):
    """Extract value after 'Key : Value' pattern."""
    m = re.search(rf'{key}\s*:\s*(.+)', line, re.IGNORECASE)
    if m:
        return _clean_wide_chars(m.group(1).strip())
    return ""


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

    lines = raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    result["raw_lines"] = [l for l in lines if l.strip()]

    # --- Parse Header ---
    for line in lines:
        stripped = line.strip()

        # Betreiber
        if stripped.startswith("Betreiber"):
            result["betreiber"] = _parse_header_value(stripped, "Betreiber")

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
                # Extract program number
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
                result["cycle_start"] = m.group(1).strip()

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
    for line in lines:
        upper = line.upper().strip()
        if "PROGRAMM KORREKT BEENDET" in upper:
            result["result"] = "ZYKLUS BESTANDEN"
            result["result_detail"] = "PROGRAMM KORREKT BEENDET"
        elif "NICHT BESTANDEN" in upper or "ABGEBROCHEN" in upper:
            result["result"] = "ZYKLUS NICHT BESTANDEN"
            result["result_detail"] = upper.strip()

    # --- Parse Footer Values ---
    for line in lines:
        # Min. Sterilisiertemp.
        m = re.search(r'Min\.\s*Sterilisiertemp\.\s+(\d+[\.,]\d+)', line)
        if m:
            result["temp_min"] = float(m.group(1).replace(",", "."))

        # Max. Sterilisiertemp.
        m = re.search(r'Max\.\s*Sterilisiertemp\.\s+(\d+[\.,]\d+)', line)
        if m:
            result["temp_max"] = float(m.group(1).replace(",", "."))

        # F0-Wert
        m = re.search(r'F0-Wert\s+(\d+[\.,]\d+)', line)
        if m:
            result["f0_value"] = float(m.group(1).replace(",", "."))

        # Zeit ueber Sollwert Kammer
        m = re.search(r'Zeit\s+(?:ueber|ueb\.?)\s+Soll\w*\s+Kammer\s+(\d+:\d+)', line)
        if m:
            result["sterilization_duration"] = m.group(1)

    # --- Parse Phase Data Lines ---
    # Format: " mm:ss Phase           pressure   temp"
    # T3 follows on next line: "                                    temp"
    phase_pattern = re.compile(
        r'^\s*(\d{1,3}:\d{2})\s+'     # time m:ss or mm:ss
        r'(.*?)\s+'                     # phase name (can be empty for continuation)
        r'(\d{1,5})\s+'                # pressure (mbara)
        r'(\d{1,3}[\.,]\d)'           # T2 temperature
    )

    # T3 standalone: just a number with lots of leading spaces
    standalone_t3 = re.compile(r'^\s{20,}(\d{1,3}[\.,]\d)\s*$')

    phase_lines = []
    pending_t3 = None
    last_phase_name = ""

    for i, line in enumerate(lines):
        # Check for standalone T3 (appears AFTER the data line in real format)
        t3m = standalone_t3.match(line)
        if t3m:
            t3_val = float(t3m.group(1).replace(",", "."))
            # Assign to the LAST phase entry (T3 comes after the main line)
            if phase_lines:
                phase_lines[-1]["t3_c"] = t3_val
            continue

        # Check for phase data line
        m = phase_pattern.match(line)
        if m:
            time_str = m.group(1)
            phase_name = m.group(2).strip()
            p2 = int(m.group(3))
            t2 = float(m.group(4).replace(",", "."))

            # Handle continuation lines (empty phase name = same phase as before)
            if not phase_name:
                phase_name = last_phase_name
            else:
                # Clean up ">" prefix (continuation marker)
                if phase_name.startswith(">"):
                    phase_name = phase_name.lstrip("> ").strip()
                    if not phase_name:
                        phase_name = last_phase_name
                last_phase_name = phase_name

            # RTC timestamp
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
                "t3_c": None,  # Will be filled by next standalone T3 line
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
    if not result["cycle_end"]:
        result["cycle_end"] = now.strftime("%d.%m.%Y %H:%M:%S")

    return result
'''

with open("/home/belimed/docupi/protocol_parser.py", "w") as f:
    f.write(PARSER_CODE)
print("OK: protocol_parser.py v3 for real Belimed format")


# ===================================================================
# 3. FIX PDF GENERATOR - Use new header fields from parser
# ===================================================================
with open("/home/belimed/docupi/pdf_generator.py", "r") as f:
    pdf = f.read()

# Update header to use parsed device_name from protocol (fallback to config)
old_device_header = '''        device = self.config.get("pdf", {}).get("device_name", "STERI01")
        self.cell(60, 12, device, ln=False)'''
new_device_header = '''        device = self.data.get("maschinen_typ") or self.config.get("pdf", {}).get("device_name", "STERI01")
        self.cell(60, 12, device, ln=False)'''
pdf = pdf.replace(old_device_header, new_device_header)

# Update charge_nr display to use Laufende Nr.
# The header already uses d.get("charge_nr") which now comes from "Laufende Nr."

# Update customer name to show Betreiber + Abteilung
old_customer = '''        customer = self.config.get("pdf", {}).get("header_text", "")
        self.cell(35, 10, customer, align="R")'''
new_customer = '''        customer = self.data.get("betreiber") or self.config.get("pdf", {}).get("header_text", "")
        if self.data.get("abteilung"):
            customer = customer + " / " + self.data["abteilung"] if customer else self.data["abteilung"]
        self.cell(35, 10, customer[:30], align="R")'''
pdf = pdf.replace(old_customer, new_customer)

with open("/home/belimed/docupi/pdf_generator.py", "w") as f:
    f.write(pdf)
print("OK: pdf_generator.py uses real header data")


# ===================================================================
# 4. TEST with the real protocol data
# ===================================================================
print("\n--- Running test with real protocol data ---")

import subprocess
r = subprocess.run(
    ["python3", "-c", '''
import sys
sys.path.insert(0, "/home/belimed/docupi")
from protocol_parser import parse_serial_protocol

# Read the actual serial log
with open("/home/belimed/docupi/serial_logs/serial_2026-03-19.log", "r", errors="replace") as f:
    raw = f.read()

# Strip the log markers
import re
raw = re.sub(r"={60}\n=== .+ ===\n={60}\n?", "", raw)

d = parse_serial_protocol(raw)
print(f"Betreiber: {d['betreiber']}")
print(f"Maschinen-Typ: {d['maschinen_typ']}")
print(f"Maschinen-Nr: {d['maschinen_nr']}")
print(f"Charge (Laufende Nr): {d['charge_nr']}")
print(f"Programm: {d['program_name']}")
print(f"Cycle Start: {d['cycle_start']}")
print(f"Duration: {d['cycle_duration']}")
print(f"Phases: {len(d['phases'])}")
print(f"Result: {d['result']}")
print(f"Temp Min/Max: {d['temp_min']} / {d['temp_max']}")
print(f"F0: {d['f0_value']}")
print()
for p in d["phases"][:5]:
    t3 = f"{p['t3_c']:.1f}" if p.get('t3_c') else '-'
    print(f"  {p['time_offset']:>5s} {p['phase']:<22s} P2={p['p2_mbar']:>5d} T2={p['t2_c']:>6.1f} T3={t3:>6s}")
print("  ...")
for p in d["phases"][-3:]:
    t3 = f"{p['t3_c']:.1f}" if p.get('t3_c') else '-'
    print(f"  {p['time_offset']:>5s} {p['phase']:<22s} P2={p['p2_mbar']:>5d} T2={p['t2_c']:>6.1f} T3={t3:>6s}")

# Generate PDF
from pdf_generator import generate_pdf
from datetime import datetime
config = {
    "pdf": {
        "device_name": "MST 9-6-18",
        "header_text": "",
        "font_size": 8,
        "folder_structure": "flat",
        "output_dir": "/media/usbstick",
        "fallback_dir": "/home/belimed/docupi/data/pdfs",
        "filename_pattern": "{datum}_{zeit}_{geraet}_{charge}",
        "filename_separator": "_",
        "handwritten_fields": True,
    }
}
pdf_path, pdf_name, pdf_size = generate_pdf(raw, 21667, datetime.now(), config)
print(f"\\nPDF: {pdf_name} ({pdf_size} bytes)")
print(f"Path: {pdf_path}")
'''],
    capture_output=True, text=True, timeout=30
)
print(r.stdout)
if r.stderr:
    print("ERRORS:", r.stderr[-500:])

print("\n=== ALL DONE ===")
