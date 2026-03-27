#!/usr/bin/env python3
"""
DocuPi-3000 - PDF Generator v4
Erzeugt professionelle Chargenprotokolle aus Belimed-Sterilisator-Daten.

Seitenaufbau:
  Seite 1: Kopf, KPI-Boxen, vollstaendige Datentabelle (Uhrzeit + Prozesszeit), Freigabe
  Seite 2: Kopf, Verlaufskurve (Uhrzeit auf X-Achse)
  Seite 3 (optional): Handschriftliche Felder (Notfallkonzept)
"""

import os
import logging
from datetime import datetime, timedelta
from fpdf import FPDF
from database import update_protocol_pdf
from protocol_parser import parse_serial_protocol
from chart_generator import generate_trend_chart

logger = logging.getLogger("docupi.pdf")

# Farben
DARK_BLUE = (31, 78, 121)
MID_BLUE = (46, 117, 182)
LIGHT_GRAY = (240, 240, 240)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN_BG = (39, 124, 72)
RED_BG = (192, 57, 43)
TABLE_HEADER_BG = (230, 235, 240)
TABLE_BORDER = (200, 200, 200)
FOOTER_BG = (50, 60, 75)


class SterilizationPDF(FPDF):
    """PDF im SmartHub Connect Report Stil."""

    def __init__(self, protocol_data, config):
        super().__init__(orientation="L", format="A4")
        self.data = protocol_data
        self.config = config
        self.page_count_total = 2
        self.set_auto_page_break(auto=False)

    # ---------------------------------------------------------------
    # HEADER
    # ---------------------------------------------------------------
    def draw_header(self):
        d = self.data
        self.set_fill_color(*WHITE)
        self.rect(0, 0, 297, 28, "F")
        self.set_draw_color(200, 200, 200)
        self.line(0, 28, 297, 28)

        # Geraetename
        self.set_xy(10, 6)
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(*DARK_BLUE)
        device = d.get("maschinen_typ") or self.config.get("pdf", {}).get("device_name", "Sterilisator")
        self.cell(60, 12, device, ln=False)

        # Header-Felder
        fields = [
            ("CHARGE", str(d.get("charge_nr", "-")), 75, 20),
            ("ZYKLUS START", d.get("cycle_start", "-"), 100, 35),
            ("ZYKLUS ENDE", d.get("cycle_end", "-"), 135, 35),
            ("ZYKLUSZEIT", d.get("cycle_duration", "-"), 170, 25),
        ]
        for label, value, x, w in fields:
            self.set_xy(x, 4)
            self.set_font("Helvetica", "", 6)
            self.set_text_color(120, 120, 120)
            self.cell(w, 4, label)
            self.set_xy(x, 8)
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(*BLACK)
            parts = value.split(" ", 1) if " " in value and len(value) > 12 else [value]
            self.cell(w, 5, parts[0])
            if len(parts) > 1:
                self.set_xy(x, 13)
                self.set_font("Helvetica", "", 8)
                self.cell(w, 5, parts[1])

        # Ergebnis Box
        result = d.get("result", "")
        is_passed = "BESTANDEN" in result.upper() and "NICHT" not in result.upper()
        bg = GREEN_BG if is_passed else RED_BG
        self.set_fill_color(*bg)
        self.set_xy(200, 6)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*WHITE)
        result_text = result if result else "-"
        self.cell(50, 7, result_text, fill=True, align="C")
        # Detail
        self.set_xy(200, 14)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(100, 100, 100)
        self.cell(50, 4, d.get("result_detail", ""))

        # Betreiber / Abteilung (rechts oben)
        self.set_xy(255, 6)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*DARK_BLUE)
        betreiber = d.get("betreiber", "") or self.config.get("pdf", {}).get("header_text", "")
        abt = d.get("abteilung", "")
        label = f"{betreiber} / {abt}" if betreiber and abt else betreiber or abt
        self.cell(35, 5, label[:25], align="R")
        # Maschinen-Nr darunter
        if d.get("maschinen_nr"):
            self.set_xy(255, 12)
            self.set_font("Helvetica", "", 6)
            self.set_text_color(120, 120, 120)
            self.cell(35, 4, f"Nr: {d['maschinen_nr']}", align="R")

    # ---------------------------------------------------------------
    # FOOTER
    # ---------------------------------------------------------------
    def draw_footer(self, page_nr):
        y = 195
        self.set_fill_color(*FOOTER_BG)
        self.rect(0, y, 297, 15, "F")
        self.set_font("Helvetica", "", 6)
        self.set_text_color(*WHITE)

        self.set_xy(10, y + 2)
        self.cell(60, 4, "MACHINE / SERIENNUMMER")
        self.set_xy(10, y + 6)
        self.set_font("Helvetica", "B", 7)
        device = self.data.get("maschinen_typ", "")
        nr = self.data.get("maschinen_nr", "")
        self.cell(60, 4, f"{device} Nr:{nr} / DocuPi-3000")

        self.set_font("Helvetica", "", 6)
        self.set_xy(120, y + 2)
        self.cell(50, 4, "PROGRAMM")
        self.set_xy(120, y + 6)
        self.set_font("Helvetica", "B", 7)
        self.cell(50, 4, self.data.get("program_name", "-"))

        self.set_font("Helvetica", "", 6)
        self.set_xy(190, y + 2)
        self.cell(40, 4, "REPORT ERSTELLT")
        self.set_xy(190, y + 6)
        self.set_font("Helvetica", "B", 7)
        self.cell(40, 4, datetime.now().strftime("%d.%m.%Y %H:%M:%S"))

        self.set_font("Helvetica", "", 9)
        self.set_xy(235, y + 3)
        self.cell(25, 6, f"Seite {page_nr}/{self.page_count_total}", align="C")

        self.set_font("Helvetica", "B", 14)
        self.set_text_color(200, 200, 200)
        self.set_xy(263, y + 2)
        self.cell(28, 10, "DocuPi", align="R")

    # ---------------------------------------------------------------
    # PAGE 1: KPI + Full Data Table + Freigabe
    # ---------------------------------------------------------------
    def draw_page1(self):
        self.add_page()
        self.draw_header()
        d = self.data

        # --- KPI Boxen ---
        y_kpi = 32
        box_h = 25
        kpi_boxes = [
            ("ZYKLUSZEIT", d.get("cycle_duration", "-"), "H : MIN : SEK", 10, 55),
            ("STERILISATIONSDAUER", d.get("sterilization_duration", "-"), "", 68, 55),
            ("STERILISATION TEMP.", f"{d.get('temp_min', 0):.1f}  /  {d.get('temp_max', 0):.1f}", "MIN  /  MAX  \u00b0C", 126, 55),
            ("PROGRAMM", d.get("program_name", "-"), f"Nr. {d.get('program_nr', '-')} / {d.get('version', '-')}", 184, 55),
            ("BENUTZER", d.get("benutzer", "-"), "", 242, 45),
        ]
        for label, value, unit, x, w in kpi_boxes:
            self.set_fill_color(*DARK_BLUE)
            self.rect(x, y_kpi, w, 6, "F")
            self.set_xy(x + 2, y_kpi + 1)
            self.set_font("Helvetica", "B", 6)
            self.set_text_color(*WHITE)
            self.cell(w - 4, 4, label)
            self.set_fill_color(*LIGHT_GRAY)
            self.rect(x, y_kpi + 6, w, box_h - 6, "F")
            self.set_xy(x + 2, y_kpi + 8)
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(*BLACK)
            self.cell(w - 4, 8, str(value)[:20], align="C")
            if unit:
                self.set_xy(x + 2, y_kpi + 17)
                self.set_font("Helvetica", "", 5.5)
                self.set_text_color(120, 120, 120)
                self.cell(w - 4, 4, unit, align="C")

        # --- Vollstaendige Datentabelle ---
        y_table = y_kpi + box_h + 4
        phases = d.get("phases", [])

        # Calculate RTC times from cycle_start + time_offset
        start_time = None
        try:
            cs = d.get("cycle_start", "")
            if "/" in cs:
                start_time = datetime.strptime(cs.strip(), "%d.%m.%Y / %H:%M")
            elif "." in cs:
                start_time = datetime.strptime(cs.strip(), "%d.%m.%Y %H:%M:%S")
        except:
            start_time = None

        # Enrich phases with calculated RTC time
        for p in phases:
            if not p.get("rtc_time") and start_time:
                parts = p["time_offset"].split(":")
                offset_sec = int(parts[0]) * 60 + int(parts[1])
                rtc = start_time + timedelta(seconds=offset_sec)
                p["rtc_time"] = rtc.strftime("%H:%M:%S")

        # Table header
        self.set_font("Helvetica", "", 6)
        self.set_text_color(100, 100, 100)
        self.set_xy(10, y_table)
        self.cell(277, 4, "PROZESSDATEN", ln=True)
        y_table += 5

        # Determine if we need 2 columns (more than ~20 rows)
        total_phases = len(phases)
        use_two_cols = total_phases > 18
        col_width = 133 if use_two_cols else 277
        max_rows_per_col = 26 if use_two_cols else 30

        # Column headers
        col_w = [18, 14, 38, 14, 14, 16] if use_two_cols else [22, 18, 60, 20, 20, 22]
        headers = ["Uhrzeit", "Prozess", "Phase", "T2 \u00b0C", "T3 \u00b0C", "P2 mbar"]

        def draw_table_header(x_off, y):
            self.set_fill_color(*TABLE_HEADER_BG)
            self.set_font("Helvetica", "B", 5.5 if use_two_cols else 6.5)
            self.set_text_color(80, 80, 80)
            self.set_xy(x_off, y)
            for i, h in enumerate(headers):
                a = "R" if i >= 3 else "L"
                self.cell(col_w[i], 5, h, border="B", fill=True, align=a)
            return y + 5

        def draw_data_row(x_off, y, p, idx):
            if idx % 2 == 0:
                self.set_fill_color(250, 250, 252)
            else:
                self.set_fill_color(*WHITE)
            self.set_font("Helvetica", "", 5.5 if use_two_cols else 7)
            self.set_text_color(*BLACK)
            t3_str = f"{p['t3_c']:.1f}" if p.get("t3_c") else "-"
            rtc = p.get("rtc_time", "")
            self.set_xy(x_off, y)
            self.cell(col_w[0], 4.5 if use_two_cols else 5.5, rtc, fill=True)
            self.cell(col_w[1], 4.5 if use_two_cols else 5.5, p.get("time_offset", ""), fill=True)
            self.cell(col_w[2], 4.5 if use_two_cols else 5.5, p.get("phase", ""), fill=True)
            self.cell(col_w[3], 4.5 if use_two_cols else 5.5, f"{p.get('t2_c', 0):.1f}", fill=True, align="R")
            self.cell(col_w[4], 4.5 if use_two_cols else 5.5, t3_str, fill=True, align="R")
            self.cell(col_w[5], 4.5 if use_two_cols else 5.5, str(p.get("p2_mbar", 0)), fill=True, align="R")
            self.set_draw_color(*TABLE_BORDER)
            rh = 4.5 if use_two_cols else 5.5
            self.line(x_off, y + rh, x_off + sum(col_w), y + rh)

        # Draw left column
        x1 = 10
        y1 = draw_table_header(x1, y_table)
        rh = 4.5 if use_two_cols else 5.5
        for i, p in enumerate(phases[:max_rows_per_col]):
            yr = y1 + i * rh
            if yr > 172:
                break
            draw_data_row(x1, yr, p, i)

        # Draw right column if needed
        if use_two_cols and total_phases > max_rows_per_col:
            x2 = 152
            y2 = draw_table_header(x2, y_table)
            remaining = phases[max_rows_per_col:]
            for i, p in enumerate(remaining):
                yr = y2 + i * rh
                if yr > 172:
                    break
                draw_data_row(x2, yr, p, i)

        # --- Freigabebereich ---
        y_sig = 178
        self.set_draw_color(180, 180, 180)
        self.line(10, y_sig - 2, 287, y_sig - 2)

        self.set_font("Helvetica", "", 6)
        self.set_text_color(100, 100, 100)
        self.set_xy(10, y_sig)
        self.cell(30, 3, "OPERATOR")
        self.set_xy(60, y_sig)
        self.cell(30, 3, "CHARGE")
        self.set_xy(140, y_sig)
        self.cell(60, 3, "BEMERKUNGEN ZUR BEDINGTEN FREIGABE")
        self.set_xy(235, y_sig)
        self.cell(30, 3, "SIGNATURE")

        y_cb = y_sig + 5
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*BLACK)
        self.set_xy(10, y_cb)
        self.cell(30, 5, d.get("benutzer", "User"))
        self.set_xy(60, y_cb)
        self.cell(20, 5, "freigegeben")

        for label, x_pos in [("ja", 92), ("nein", 110), ("bedingte Freigabe", 130)]:
            self.set_draw_color(100, 100, 100)
            self.rect(x_pos, y_cb + 0.5, 4, 4)
            self.set_xy(x_pos + 5, y_cb)
            self.set_font("Helvetica", "", 7)
            self.cell(20, 5, label)

        self.set_draw_color(150, 150, 150)
        self.line(170, y_cb + 5, 230, y_cb + 5)
        self.line(240, y_cb + 5, 287, y_cb + 5)

        self.draw_footer(1)

    # ---------------------------------------------------------------
    # PAGE 2: Trend Chart with RTC time on X-axis
    # ---------------------------------------------------------------
    def draw_page2(self):
        phases = self.data.get("phases", [])
        if len(phases) < 2:
            return

        # Calculate RTC times for chart
        start_time = None
        try:
            cs = self.data.get("cycle_start", "")
            if "/" in cs:
                start_time = datetime.strptime(cs.strip(), "%d.%m.%Y / %H:%M")
            elif "." in cs:
                start_time = datetime.strptime(cs.strip(), "%d.%m.%Y %H:%M:%S")
        except:
            pass

        chart_path = generate_trend_chart(phases, start_time=start_time)
        if not chart_path:
            return

        self.add_page()
        self.draw_header()

        self.set_xy(10, 32)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*DARK_BLUE)
        self.cell(200, 6, "Prozessverlauf - Messwerte")

        try:
            self.image(chart_path, x=8, y=40, w=281, h=0)
        except Exception as e:
            self.set_xy(10, 50)
            self.set_font("Helvetica", "", 8)
            self.cell(200, 5, f"Chart-Fehler: {e}")

        try:
            os.remove(chart_path)
        except:
            pass

        self.draw_footer(2)

    # ---------------------------------------------------------------
    # PAGE 3 (optional): Handschriftliche Dokumentation
    # ---------------------------------------------------------------
    def draw_handwritten_page(self):
        """Seite mit leeren Feldern fuer handschriftliche Container/Sieb-Dokumentation."""
        self.add_page()
        self.draw_header()

        y = 32
        self.set_fill_color(31, 78, 121)
        self.rect(10, y, 277, 7, "F")
        self.set_xy(12, y + 1)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(255, 255, 255)
        self.cell(200, 5, "HANDSCHRIFTLICHE DOKUMENTATION (NOTFALLKONZEPT)")
        y += 10

        self.set_font("Helvetica", "I", 7)
        self.set_text_color(120, 120, 120)
        self.set_xy(10, y)
        self.cell(277, 4, "Bitte leserlich ausfuellen. Dieses Blatt dient als Backup-Dokumentation bei Ausfall des Hauptsystems.")
        y += 8

        # Container/Siebe Tabelle
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(31, 78, 121)
        self.set_xy(10, y)
        self.cell(130, 5, "STERILISIERTE CONTAINER / SIEBE / INSTRUMENTE")
        y += 6

        col_w = [8, 70, 35, 35, 45, 45, 40]
        headers = ["Nr.", "Container / Sieb / Instrument", "Menge", "SIE-Nr.", "Verpackungsart", "Indikator OK", "Bemerkung"]
        self.set_fill_color(230, 235, 240)
        self.set_font("Helvetica", "B", 6.5)
        self.set_text_color(80, 80, 80)
        self.set_draw_color(180, 180, 180)
        self.set_xy(10, y)
        for i, h in enumerate(headers):
            self.cell(col_w[i], 6, h, border=1, fill=True, align="C")
        y += 6

        self.set_font("Helvetica", "", 7)
        for row in range(12):
            self.set_xy(10, y)
            self.set_text_color(180, 180, 180)
            self.cell(col_w[0], 7, str(row + 1), border=1, align="C")
            for i in range(1, len(col_w)):
                self.cell(col_w[i], 7, "", border=1)
            y += 7
        y += 4

        # Beladungsmuster
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(31, 78, 121)
        self.set_xy(10, y)
        self.cell(80, 5, "BELADUNGSMUSTER")
        self.set_font("Helvetica", "I", 6)
        self.set_text_color(150, 150, 150)
        self.cell(100, 5, "(Skizze der Beladungspositionen im Sterilisator)")
        y += 6
        self.set_draw_color(180, 180, 180)
        self.rect(10, y, 135, 30)
        self.set_draw_color(230, 230, 230)
        for gx in range(1, 5):
            self.line(10 + gx * 27, y, 10 + gx * 27, y + 30)
        for gy in range(1, 3):
            self.line(10, y + gy * 10, 145, y + gy * 10)

        # Verpackungsart
        rx = 155
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(31, 78, 121)
        self.set_xy(rx, y - 6)
        self.cell(80, 5, "VERPACKUNGSART")
        self.set_draw_color(100, 100, 100)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(0, 0, 0)
        options = ["Sterilcontainer (starr)", "Einmal-Sterilisierverpackung",
                   "Doppelt verpackt (Klarsicht)", "Klarsicht-Sterilisierverp.",
                   "Unverpackt / Einzelinstrument", "Sonstiges: ________________"]
        for i, opt in enumerate(options):
            oy = y + i * 5
            self.rect(rx, oy + 0.5, 3.5, 3.5)
            self.set_xy(rx + 5, oy)
            self.cell(80, 4.5, opt)
        y += 35

        # Freigabe
        self.set_draw_color(180, 180, 180)
        self.line(10, y, 287, y)
        y += 3
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(31, 78, 121)
        self.set_xy(10, y)
        self.cell(130, 5, "STERILGUT-FREIGABE")
        y += 7
        self.set_font("Helvetica", "", 6.5)
        self.set_text_color(100, 100, 100)
        self.set_xy(10, y)
        self.cell(40, 4, "FREIGABE-ENTSCHEIDUNG")
        y += 5
        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "", 8)
        for label, xp in [("Freigegeben", 10), ("Nicht freigegeben", 55), ("Bedingt freigegeben", 115)]:
            self.set_draw_color(80, 80, 80)
            self.rect(xp, y + 0.5, 4, 4)
            self.set_xy(xp + 6, y)
            self.cell(40, 5, label)
        y += 8
        self.set_font("Helvetica", "", 6.5)
        self.set_text_color(100, 100, 100)
        self.set_xy(10, y)
        self.cell(80, 4, "BEMERKUNGEN ZUR BEDINGTEN FREIGABE")
        y += 4
        self.set_draw_color(180, 180, 180)
        self.line(10, y + 5, 200, y + 5)
        self.line(10, y + 11, 200, y + 11)
        y += 15
        sig_fields = [("BELADEN DURCH", 10, 55), ("ENTLADEN DURCH", 70, 55),
                      ("FREIGABE DURCH", 135, 55), ("DATUM / UHRZEIT", 200, 45),
                      ("UNTERSCHRIFT", 250, 37)]
        self.set_font("Helvetica", "", 6)
        self.set_text_color(100, 100, 100)
        for label, x, w in sig_fields:
            self.set_xy(x, y)
            self.cell(w, 3, label)
            self.set_draw_color(150, 150, 150)
            self.line(x, y + 9, x + w, y + 9)

        self.draw_footer(self.page_count_total)

    # ---------------------------------------------------------------
    # Generate
    # ---------------------------------------------------------------
    def generate(self, output_path):
        has_handwritten = self.config.get("pdf", {}).get("handwritten_fields", False)
        has_chart = len(self.data.get("phases", [])) >= 2
        self.page_count_total = 1 + (1 if has_chart else 0) + (1 if has_handwritten else 0)

        self.draw_page1()
        if has_chart:
            self.draw_page2()
        if has_handwritten:
            self.draw_handwritten_page()
        self.output(output_path)


# ===================================================================
# Public API (unchanged)
# ===================================================================

def get_output_dir(config):
    sd_dir = config["pdf"]["fallback_dir"]
    os.makedirs(sd_dir, exist_ok=True)
    return sd_dir, False


def build_filename(protocol_id, timestamp, config, charge_nr=""):
    device = config["pdf"]["device_name"].replace(" ", "_").replace("/", "-")
    if charge_nr and charge_nr != str(protocol_id):
        charge_tag = f"CH{charge_nr}"
    else:
        charge_tag = f"CH{protocol_id:05d}"
    tokens = {
        "datum": timestamp.strftime("%Y-%m-%d"),
        "zeit": timestamp.strftime("%H%M%S"),
        "geraet": device,
        "charge": charge_tag,
        "jahr": timestamp.strftime("%Y"),
        "monat": timestamp.strftime("%m"),
        "tag": timestamp.strftime("%d"),
        "stunde": timestamp.strftime("%H"),
        "minute": timestamp.strftime("%M"),
    }
    pattern = config["pdf"].get("filename_pattern", "{datum}_{zeit}_{geraet}_{charge}")
    sep = config["pdf"].get("filename_separator", "_")
    name = pattern
    for key, val in tokens.items():
        name = name.replace("{" + key + "}", val)
    name = name.replace(" ", sep)
    while sep + sep in name:
        name = name.replace(sep + sep, sep)
    name = name.strip(sep)
    return f"{name}.pdf"


def build_subfolder(timestamp, config):
    structure = config["pdf"]["folder_structure"]
    if structure == "date":
        return timestamp.strftime("%Y/%Y-%m")
    elif structure == "device":
        return config["pdf"]["device_name"].replace(" ", "_").replace("/", "-")
    elif structure == "flat":
        return ""
    return timestamp.strftime("%Y/%Y-%m")


def generate_pdf(raw_data, protocol_id, timestamp, config, rtc_timestamps=None):
    line_ts = None
    if rtc_timestamps:
        line_ts = []
        char_to_line = {}
        char_pos = 0
        for line_idx, line in enumerate(raw_data.split("\n")):
            char_to_line[char_pos] = line_idx
            char_pos += len(line) + 1
        for char_off, dt in rtc_timestamps:
            best_line = 0
            for cp, li in char_to_line.items():
                if cp <= char_off:
                    best_line = li
            line_ts.append((best_line, dt))

    protocol_data = parse_serial_protocol(raw_data, rtc_timestamps=line_ts)
    parsed_charge = protocol_data.get("charge_nr", "").strip()
    if not parsed_charge:
        parsed_charge = str(protocol_id)
        protocol_data["charge_nr"] = parsed_charge

    output_base, on_usb = get_output_dir(config)
    subfolder = build_subfolder(timestamp, config)
    output_dir = os.path.join(output_base, subfolder)
    os.makedirs(output_dir, exist_ok=True)

    filename = build_filename(protocol_id, timestamp, config, charge_nr=parsed_charge)
    pdf_path = os.path.join(output_dir, filename)

    pdf = SterilizationPDF(protocol_data, config)
    pdf.generate(pdf_path)

    file_size = os.path.getsize(pdf_path)
    update_protocol_pdf(protocol_id, pdf_path, filename, file_size)
    logger.info(f"PDF: {pdf_path} ({file_size}B)")
    return pdf_path, filename, file_size
