#!/usr/bin/env python3
"""
Major upgrade: Protocol parser for multi-value blocks + RTC timestamps + trend chart in PDF.

The sterilizer sends data blocks during the process:
  0:02 1. Vorvakuum    1034  46.0
                              50.8
Each block: time, step, P2(mbar), T2(°C), T3(°C on next line or same line)

Changes:
1. protocol_parser.py: Extract P2, T2, T3 + add RTC timestamp per step
2. pdf_generator.py: Add trend chart page with matplotlib
3. serial_receiver.py: Attach RTC timestamp to each incoming block
"""

# ===================================================================
# 1. PROTOCOL PARSER - Complete rewrite with multi-value support
# ===================================================================

PROTOCOL_PARSER_CODE = r'''#!/usr/bin/env python3
"""
DocuPi-3000 - Protocol Parser v2
Parst serielle Textdaten vom Sterilisator-Thermodrucker.

Eingabeformat (Thermodrucker, Zeile fuer Zeile):
  Zeile 1:                          50.8    (T3 Luftnachweis)
  Zeile 2: 0:02 1. Vorvakuum  1034 46.0     (Zeit, Phase, P2, T2)

  Oder auf einer Zeile:
  0:02 1. Vorvakuum    1034  46.0  50.8

Kopfbereich: Ergebnis, FO-Wert, Temperaturen, etc.
"""

import re
from datetime import datetime, timedelta


def parse_serial_protocol(raw_text, rtc_timestamps=None):
    """
    Parst den seriellen Protokolltext und gibt ein strukturiertes Dict zurueck.
    rtc_timestamps: optionale Liste von (line_index, datetime) Tupeln fuer RTC-Zeiten
    """
    result = {
        "device_name": "",
        "charge_nr": "",
        "program_name": "",
        "result": "",
        "result_detail": "",
        "cycle_start": "",
        "cycle_end": "",
        "cycle_duration": "",
        "sterilization_duration": "",
        "temp_min": 0.0,
        "temp_max": 0.0,
        "f0_value": 0.0,
        "air_detection_temp": 0.0,
        "phases": [],
        "raw_lines": [],
    }

    lines = raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = [l.rstrip() for l in lines]
    result["raw_lines"] = [l for l in lines if l.strip()]

    # --- Detect result line ---
    for line in lines:
        upper = line.upper().strip()
        if "BESTANDEN" in upper and ("BOWIE" in upper or "TEST" in upper):
            result["result"] = "ZYKLUS BESTANDEN"
            result["program_name"] = "Bowie-Dick-Test"
            result["result_detail"] = "OHNE ALARM"
        elif "BESTANDEN" in upper:
            result["result"] = "ZYKLUS BESTANDEN"
            result["result_detail"] = "OHNE ALARM"
        elif "NICHT BESTANDEN" in upper or "FEHLGESCHLAGEN" in upper:
            result["result"] = "ZYKLUS NICHT BESTANDEN"
            result["result_detail"] = "MIT ALARM"
        if "KORREKT BEENDET" in upper:
            result["result_detail"] = "OHNE ALARM"
            if not result["result"]:
                result["result"] = "ZYKLUS BESTANDEN"

    # --- Parse header values ---
    for line in lines:
        fo_match = re.search(r"FO[- ]?(?:Wert|wert)?\s+(\d+[\.,]\d+)", line, re.IGNORECASE)
        if fo_match:
            result["f0_value"] = float(fo_match.group(1).replace(",", "."))

        max_match = re.search(r"Max[\.\s]+Sterilisiertemp[\.\s]+(\d+[\.,]\d+)", line, re.IGNORECASE)
        if max_match:
            result["temp_max"] = float(max_match.group(1).replace(",", "."))

        min_match = re.search(r"Min[\.\s]+Sterilisiertemp[\.\s]+(\d+[\.,]\d+)", line, re.IGNORECASE)
        if min_match:
            result["temp_min"] = float(min_match.group(1).replace(",", "."))

        luft_match = re.search(r"Luftnachw[\w]*[\.\s]+(\d+[\.,]?\d*)", line, re.IGNORECASE)
        if luft_match:
            result["air_detection_temp"] = float(luft_match.group(1).replace(",", "."))

        zeit_soll = re.search(r"Zeit\s+ueb[\.\s]+Soll[\w\.\s]+(\d+[\.:]\d+)", line, re.IGNORECASE)
        if zeit_soll:
            val = zeit_soll.group(1).replace(".", ":")
            result["sterilization_duration"] = val

        # Charge number
        charge_match = re.search(r"Charge[\s:]+(\d+)", line, re.IGNORECASE)
        if charge_match:
            result["charge_nr"] = charge_match.group(1)

        # Program name/number
        prog_match = re.search(r"Programm[\s:]+(.+)", line, re.IGNORECASE)
        if prog_match and "Ende" not in line and "BEENDET" not in line.upper():
            result["program_name"] = prog_match.group(1).strip()

    # --- Parse phase data lines ---
    # Pattern: time phase pressure temp [temp2]
    # e.g.: "0:02 1. Vorvakuum    1034  46.0"
    # T3 may be on the PREVIOUS line (just a number) or as 5th column
    phase_pattern = re.compile(
        r"^\s*(\d{1,3}:\d{2})\s+"       # time m:ss or mm:ss
        r"([\w\.\s/>-]+?)\s{2,}"         # phase name (at least 2 spaces after)
        r"(\d{1,5})\s+"                   # P2 pressure
        r"(\d{1,3}[\.,]\d)"              # T2 temperature
        r"(?:\s+(\d{1,3}[\.,]\d))?"      # T3 optional on same line
    )

    # Also detect standalone number lines (T3 on its own line above)
    standalone_num = re.compile(r"^\s+(\d{1,3}[\.,]\d)\s*$")

    phase_lines = []
    pending_t3 = None

    for i, line in enumerate(lines):
        # Check for standalone T3 value (appears before the phase line)
        sm = standalone_num.match(line)
        if sm:
            pending_t3 = float(sm.group(1).replace(",", "."))
            continue

        m = phase_pattern.match(line)
        if m:
            time_str = m.group(1)
            phase_name = m.group(2).strip()
            p2 = int(m.group(3))
            t2 = float(m.group(4).replace(",", "."))
            t3 = None

            # T3 from same line (5th group)
            if m.group(5):
                t3 = float(m.group(5).replace(",", "."))
            # T3 from pending standalone line
            elif pending_t3 is not None:
                t3 = pending_t3

            # RTC timestamp for this data point
            rtc_time = None
            if rtc_timestamps:
                # Find closest timestamp for this line
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
                "t3_c": t3,
                "pressure_mbar": p2,  # backwards compat
                "temp_c": t2,         # backwards compat
            }
            if rtc_time:
                entry["rtc_time"] = rtc_time.strftime("%H:%M:%S")

            phase_lines.append(entry)
            pending_t3 = None
        else:
            # Non-matching line resets pending T3
            if not sm:
                pending_t3 = None

    # Thermoprinter prints bottom-to-top -> reverse if needed
    if len(phase_lines) >= 2:
        first_mins = int(phase_lines[0]["time_offset"].split(":")[0])
        last_mins = int(phase_lines[-1]["time_offset"].split(":")[0])
        if first_mins > last_mins:
            phase_lines.reverse()

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

    # --- Min/Max from sterilization phase ---
    if result["temp_min"] == 0 and result["temp_max"] == 0:
        steri_temps = [p["t2_c"] for p in phase_lines
                       if "sterilisation" in p["phase"].lower()]
        if steri_temps:
            result["temp_min"] = min(steri_temps)
            result["temp_max"] = max(steri_temps)

    # --- Cycle start/end times ---
    now = datetime.now()
    if not result["cycle_end"]:
        result["cycle_end"] = now.strftime("%d.%m.%Y %H:%M:%S")
    if not result["cycle_start"] and result["cycle_duration"]:
        parts = result["cycle_duration"].split(":")
        delta = timedelta(hours=int(parts[0]), minutes=int(parts[1]), seconds=int(parts[2]))
        start = now - delta
        result["cycle_start"] = start.strftime("%d.%m.%Y %H:%M:%S")

    return result
'''

with open("/home/belimed/docupi/protocol_parser.py", "w") as f:
    f.write(PROTOCOL_PARSER_CODE)
print("OK: protocol_parser.py updated")


# ===================================================================
# 2. CHART GENERATOR - matplotlib trend chart
# ===================================================================

CHART_CODE = r'''#!/usr/bin/env python3
"""
DocuPi-3000 - Chart Generator
Creates trend charts from sterilization process data using matplotlib.
"""

import os
import logging
import tempfile

logger = logging.getLogger("docupi.chart")


def generate_trend_chart(phases, output_path=None, width=10, height=3.5):
    """
    Generate a trend chart PNG showing P2, T2, T3 over process time.
    Returns path to PNG file.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
    except ImportError:
        logger.warning("matplotlib nicht installiert - kein Chart moeglich")
        return None

    if not phases or len(phases) < 2:
        return None

    # Extract data
    times = []
    p2_vals = []
    t2_vals = []
    t3_vals = []
    labels = []

    for p in phases:
        parts = p["time_offset"].split(":")
        t_min = int(parts[0]) + int(parts[1]) / 60.0
        times.append(t_min)
        p2_vals.append(p.get("p2_mbar", p.get("pressure_mbar", 0)))
        t2_vals.append(p.get("t2_c", p.get("temp_c", 0)))
        t3_vals.append(p.get("t3_c") or 0)
        labels.append(p.get("phase", ""))

    has_t3 = any(v > 0 for v in t3_vals)

    # Create figure with dual Y-axis
    fig, ax1 = plt.subplots(1, 1, figsize=(width, height), dpi=150)
    fig.patch.set_facecolor("white")

    # Pressure (left axis)
    color_p2 = "#1f4e79"
    ax1.set_xlabel("Prozesszeit (min)", fontsize=8, color="#666")
    ax1.set_ylabel("Druck P2 (mbar)", fontsize=8, color=color_p2)
    line_p2, = ax1.plot(times, p2_vals, color=color_p2, linewidth=1.5, label="P2 Kammerdruck", alpha=0.9)
    ax1.tick_params(axis="y", labelcolor=color_p2, labelsize=7)
    ax1.tick_params(axis="x", labelsize=7)
    ax1.set_xlim(min(times), max(times))
    ax1.grid(True, alpha=0.2)

    # Temperature (right axis)
    ax2 = ax1.twinx()
    color_t2 = "#dc3545"
    color_t3 = "#fd7e14"
    ax2.set_ylabel("Temperatur (°C)", fontsize=8, color=color_t2)
    line_t2, = ax2.plot(times, t2_vals, color=color_t2, linewidth=1.5, label="T2 Kammer", alpha=0.9)
    if has_t3:
        line_t3, = ax2.plot(times, t3_vals, color=color_t3, linewidth=1.2,
                            linestyle="--", label="T3 Luftnachweis", alpha=0.8)
    ax2.tick_params(axis="y", labelcolor=color_t2, labelsize=7)

    # Phase annotations (show phase changes)
    last_label = ""
    for i, lbl in enumerate(labels):
        if lbl != last_label and lbl:
            ax1.axvline(x=times[i], color="#ccc", linewidth=0.5, linestyle=":")
            # Only show label if there's enough space
            if i == 0 or (times[i] - times[max(0, i-1)]) > 0.5:
                ax1.text(times[i], ax1.get_ylim()[1] * 0.98, lbl,
                         fontsize=4.5, rotation=45, ha="left", va="top",
                         color="#888", alpha=0.7)
            last_label = lbl

    # Legend
    handles = [line_p2, line_t2]
    if has_t3:
        handles.append(line_t3)
    ax1.legend(handles=handles, loc="upper left", fontsize=6, framealpha=0.9)

    # Title
    fig.suptitle("Prozessverlauf", fontsize=10, fontweight="bold", color="#1f4e79", y=0.98)

    plt.tight_layout()

    if not output_path:
        output_path = tempfile.mktemp(suffix=".png", prefix="docupi_chart_")

    fig.savefig(output_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    logger.info(f"Chart erzeugt: {output_path}")
    return output_path
'''

with open("/home/belimed/docupi/chart_generator.py", "w") as f:
    f.write(CHART_CODE)
print("OK: chart_generator.py created")


# ===================================================================
# 3. UPDATE PDF GENERATOR - Add chart page + T3 column + RTC time
# ===================================================================
with open("/home/belimed/docupi/pdf_generator.py", "r") as f:
    pdf_code = f.read()

# 3a. Add chart import
if "chart_generator" not in pdf_code:
    pdf_code = pdf_code.replace(
        "from protocol_parser import parse_serial_protocol",
        "from protocol_parser import parse_serial_protocol\nfrom chart_generator import generate_trend_chart"
    )

# 3b. Update page count to 3
pdf_code = pdf_code.replace(
    "self.page_count_total = 2",
    "self.page_count_total = 3"
)

# 3c. Update Page 2 table headers to include RTC time, T3
old_page2_headers = '''        headers = ["Zeit", "Meld. Nr.", "Meldung", "Phase",
                    "T1 C", "T2 C", "P1 bar a", "P2 bar a", "P3 bar a", "P4 bar a"]'''
new_page2_headers = '''        headers = ["Uhrzeit", "Prozess", "Phase",
                    "T2 \\u00b0C", "T3 \\u00b0C", "P2 mbar"]'''
pdf_code = pdf_code.replace(old_page2_headers, new_page2_headers)

# Update column widths for page 2
old_page2_cols = '''        col_widths = [22, 22, 45, 65, 22, 22, 22, 22, 22, 22]'''
new_page2_cols = '''        col_widths = [28, 22, 70, 25, 25, 25]'''
# Only replace the one in draw_page2
pdf_code = pdf_code.replace(old_page2_cols, new_page2_cols, 1)

# Replace page 2 data rows
old_page2_rows = '''        for idx, p in enumerate(phases):
            y_row = y_table + 6 + idx * 5.5
            if y_row > 185:
                break

            if idx % 2 == 0:
                self.set_fill_color(250, 250, 252)
            else:
                self.set_fill_color(*WHITE)

            self.set_xy(5, y_row)
            self.cell(col_widths[0], 5.5, p.get("time_offset", ""), fill=True)
            self.cell(col_widths[1], 5.5, "", fill=True)
            self.cell(col_widths[2], 5.5, "", fill=True)
            self.cell(col_widths[3], 5.5, p.get("phase", ""), fill=True)
            self.cell(col_widths[4], 5.5, f"{p.get('temp_c', 0):.2f}", fill=True, align="R")
            self.cell(col_widths[5], 5.5, f"{p.get('temp_c', 0):.2f}", fill=True, align="R")
            self.cell(col_widths[6], 5.5, str(p.get("pressure_mbar", 0)), fill=True, align="R")
            self.cell(col_widths[7], 5.5, str(p.get("pressure_mbar", 0)), fill=True, align="R")
            self.cell(col_widths[8], 5.5, "", fill=True, align="R")
            self.cell(col_widths[9], 5.5, "", fill=True, align="R")

            self.set_draw_color(*TABLE_BORDER)
            self.line(5, y_row + 5.5, 292, y_row + 5.5)'''

new_page2_rows = '''        for idx, p in enumerate(phases):
            y_row = y_table + 6 + idx * 5.5
            if y_row > 185:
                break

            if idx % 2 == 0:
                self.set_fill_color(250, 250, 252)
            else:
                self.set_fill_color(*WHITE)

            rtc = p.get("rtc_time", "")
            t3_str = f"{p['t3_c']:.1f}" if p.get("t3_c") else "-"

            self.set_xy(10, y_row)
            self.cell(col_widths[0], 5.5, f"{rtc}  ({p.get('time_offset', '')})", fill=True)
            self.cell(col_widths[1], 5.5, p.get("time_offset", ""), fill=True)
            self.cell(col_widths[2], 5.5, p.get("phase", ""), fill=True)
            self.cell(col_widths[3], 5.5, f"{p.get('t2_c', p.get('temp_c', 0)):.1f}", fill=True, align="R")
            self.cell(col_widths[4], 5.5, t3_str, fill=True, align="R")
            self.cell(col_widths[5], 5.5, str(p.get("p2_mbar", p.get("pressure_mbar", 0))), fill=True, align="R")

            self.set_draw_color(*TABLE_BORDER)
            self.line(10, y_row + 5.5, 205, y_row + 5.5)'''

pdf_code = pdf_code.replace(old_page2_rows, new_page2_rows)

# 3d. Update page 2 header alignment
old_header_align = '''        for i, h in enumerate(headers):
            a = "R" if i >= 4 else "L"
            self.cell(col_widths[i], 6, h, border="B", fill=True, align=a)'''
new_header_align = '''        for i, h in enumerate(headers):
            a = "R" if i >= 3 else "L"
            self.cell(col_widths[i], 6, h, border="B", fill=True, align=a)'''
pdf_code = pdf_code.replace(old_header_align, new_header_align)

# 3e. Add draw_page3 for chart
old_generate = '''    def generate(self, output_path):
        self.draw_page1()
        self.draw_page2()
        self.output(output_path)'''

new_generate = '''    def draw_page3(self):
        """Seite 3: Verlaufskurve (Trend Chart)."""
        phases = self.data.get("phases", [])
        if len(phases) < 2:
            self.page_count_total = 2
            return

        chart_path = generate_trend_chart(phases)
        if not chart_path:
            self.page_count_total = 2
            return

        self.add_page()
        self.draw_header()

        # Title
        self.set_xy(10, 32)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*DARK_BLUE)
        self.cell(200, 6, "Prozessverlauf - Messwerte")

        # Chart image
        try:
            self.image(chart_path, x=10, y=40, w=277, h=0)
        except Exception as e:
            self.set_xy(10, 50)
            self.set_font("Helvetica", "", 8)
            self.cell(200, 5, f"Chart-Fehler: {e}")

        # Cleanup temp file
        try:
            import os
            os.remove(chart_path)
        except:
            pass

        self.draw_footer(3)

    def generate(self, output_path):
        self.draw_page1()
        self.draw_page2()
        self.draw_page3()
        self.output(output_path)'''

pdf_code = pdf_code.replace(old_generate, new_generate)

# Also update page 1 summary table to show T3
old_p1_headers = '''        headers = ["Zeit", "Phase", "T1 C", "T2 C", "P1 mbar", "P2 mbar"]'''
new_p1_headers = '''        headers = ["Zeit", "Phase", "T2 \\u00b0C", "T3 \\u00b0C", "P2 mbar"]'''
pdf_code = pdf_code.replace(old_p1_headers, new_p1_headers)

old_p1_cols = '''        col_widths = [20, 45, 20, 20, 20, 20]'''
new_p1_cols = '''        col_widths = [20, 50, 20, 20, 25]'''
pdf_code = pdf_code.replace(old_p1_cols, new_p1_cols)

# Update page 1 data cells
old_p1_cells = '''            self.set_xy(10, y_row)
            self.cell(col_widths[0], 4.5, p.get("time_offset", ""), border=0, fill=True)
            self.cell(col_widths[1], 4.5, p.get("phase", ""), border=0, fill=True)
            self.cell(col_widths[2], 4.5, f"{p.get('temp_c', 0):.1f}", border=0, fill=True, align="R")
            self.cell(col_widths[3], 4.5, f"{p.get('temp_c', 0):.1f}", border=0, fill=True, align="R")
            self.cell(col_widths[4], 4.5, str(p.get("pressure_mbar", 0)), border=0, fill=True, align="R")
            self.cell(col_widths[5], 4.5, "", border=0, fill=True, align="R")

            self.set_draw_color(*TABLE_BORDER)
            self.line(10, y_row + 4.5, 155, y_row + 4.5)'''

new_p1_cells = '''            t3_str = f"{p['t3_c']:.1f}" if p.get("t3_c") else "-"
            self.set_xy(10, y_row)
            self.cell(col_widths[0], 4.5, p.get("time_offset", ""), border=0, fill=True)
            self.cell(col_widths[1], 4.5, p.get("phase", ""), border=0, fill=True)
            self.cell(col_widths[2], 4.5, f"{p.get('t2_c', p.get('temp_c', 0)):.1f}", border=0, fill=True, align="R")
            self.cell(col_widths[3], 4.5, t3_str, border=0, fill=True, align="R")
            self.cell(col_widths[4], 4.5, str(p.get("p2_mbar", p.get("pressure_mbar", 0))), border=0, fill=True, align="R")

            self.set_draw_color(*TABLE_BORDER)
            self.line(10, y_row + 4.5, 145, y_row + 4.5)'''

pdf_code = pdf_code.replace(old_p1_cells, new_p1_cells)

with open("/home/belimed/docupi/pdf_generator.py", "w") as f:
    f.write(pdf_code)
print("OK: pdf_generator.py updated with chart + T3 + RTC")


# ===================================================================
# 4. UPDATE SERIAL RECEIVER - Attach RTC timestamps to blocks
# ===================================================================
with open("/home/belimed/docupi/serial_receiver.py", "r") as f:
    sr_code = f.read()

# Add timestamp tracking
if "rtc_timestamps" not in sr_code:
    # Add rtc_timestamps list to __init__
    sr_code = sr_code.replace(
        "self.bytes_received = 0",
        "self.bytes_received = 0\n        self.rtc_timestamps = []  # (char_offset, datetime) for RTC time per block"
    )

    # Record timestamp when new data arrives
    sr_code = sr_code.replace(
        "                    self.last_data_time = time.time()",
        "                    self.last_data_time = time.time()\n                    self.rtc_timestamps.append((len(self.buffer), datetime.now()))"
    )

    # Pass timestamps to process_complete_protocol
    sr_code = sr_code.replace(
        "                                self.process_complete_protocol(self.buffer)\n                                self.buffer = \"\"",
        "                                self.process_complete_protocol(self.buffer, self.rtc_timestamps)\n                                self.buffer = \"\"\n                                self.rtc_timestamps = []"
    )

    # Also for timeout
    sr_code = sr_code.replace(
        "                    self.process_complete_protocol(self.buffer)\n                    self.buffer = \"\"\n                    protocol_active = False",
        "                    self.process_complete_protocol(self.buffer, self.rtc_timestamps)\n                    self.buffer = \"\"\n                    self.rtc_timestamps = []\n                    protocol_active = False"
    )

    # Update method signature
    sr_code = sr_code.replace(
        "    def process_complete_protocol(self, data):",
        "    def process_complete_protocol(self, data, rtc_timestamps=None):"
    )

    # Pass rtc_timestamps through generate_pdf (we need to update the call too)
    # Actually, the timestamps need to go through the parser, not the PDF generator
    # We'll store them temporarily in a module-level variable that the parser can access
    sr_code = sr_code.replace(
        "            pdf_path, pdf_filename, file_size = generate_pdf(data, protocol_id, timestamp, self.config)",
        "            pdf_path, pdf_filename, file_size = generate_pdf(data, protocol_id, timestamp, self.config, rtc_timestamps=rtc_timestamps)"
    )

    # Also handle the stop() buffer flush
    sr_code = sr_code.replace(
        "        if self.buffer.strip():\n            self.process_complete_protocol(self.buffer)\n            self.buffer = \"\"",
        "        if self.buffer.strip():\n            self.process_complete_protocol(self.buffer, self.rtc_timestamps)\n            self.buffer = \"\"\n            self.rtc_timestamps = []"
    )

with open("/home/belimed/docupi/serial_receiver.py", "w") as f:
    f.write(sr_code)
print("OK: serial_receiver.py updated with RTC timestamps")


# ===================================================================
# 5. UPDATE generate_pdf to pass rtc_timestamps to parser
# ===================================================================
with open("/home/belimed/docupi/pdf_generator.py", "r") as f:
    pdf_code2 = f.read()

# Update generate_pdf signature
pdf_code2 = pdf_code2.replace(
    "def generate_pdf(raw_data, protocol_id, timestamp, config):",
    "def generate_pdf(raw_data, protocol_id, timestamp, config, rtc_timestamps=None):"
)

# Pass rtc_timestamps to parser
# Convert char offsets to line indices for the parser
pdf_code2 = pdf_code2.replace(
    "    protocol_data = parse_serial_protocol(raw_data)",
    """    # Convert char-offset timestamps to line-index timestamps
    line_ts = None
    if rtc_timestamps:
        line_ts = []
        char_to_line = {}
        char_pos = 0
        for line_idx, line in enumerate(raw_data.split("\\n")):
            char_to_line[char_pos] = line_idx
            char_pos += len(line) + 1
        for char_off, dt in rtc_timestamps:
            # Find closest line
            best_line = 0
            for cp, li in char_to_line.items():
                if cp <= char_off:
                    best_line = li
            line_ts.append((best_line, dt))

    protocol_data = parse_serial_protocol(raw_data, rtc_timestamps=line_ts)"""
)

with open("/home/belimed/docupi/pdf_generator.py", "w") as f:
    f.write(pdf_code2)
print("OK: generate_pdf passes rtc_timestamps to parser")


# ===================================================================
# 6. Install matplotlib
# ===================================================================
import subprocess
r = subprocess.run(["pip3", "install", "matplotlib", "--break-system-packages"],
                   capture_output=True, text=True, timeout=120)
if r.returncode == 0:
    print("OK: matplotlib installed")
else:
    print(f"matplotlib install: {r.stderr[-200:]}")

print("\n=== ALL DONE ===")
