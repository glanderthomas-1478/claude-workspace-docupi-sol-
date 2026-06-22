#!/usr/bin/env python3
"""
DocuPi-3000 - PDF Generator v4
Erzeugt professionelle Chargenprotokolle aus Belimed-Sterilisator-Daten.

Seitenaufbau:
  Seite 1: Kopf, KPI-Boxen, vollstaendige Datentabelle (Uhrzeit + Prozesszeit), Freigabe
  Seite 2: Kopf, Verlaufskurve (Uhrzeit auf X-Achse)
  Seite 3 (optional): Handschriftliche Felder (Notfallkonzept)

Formate:
  - BELIMED-Format: 6 Spalten [Uhrzeit, Prozess, Phase, T2, T3, P2]
  - PST-Format (UNIKLINIK_ESSEN): 9 Spalten [Zeit, Phase, P2, T1-T6]
  - Vakuumtest: 4 Spalten [Zeit, Phase, P2, T1]
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

    def __init__(self, protocol_data, config, form_data=None):
        super().__init__(orientation="L", format="A4")
        self.data = protocol_data
        self.config = config
        self.form_data = form_data or {}
        self.page_count_total = 2
        self.set_auto_page_break(auto=False)

    def _is_pst_format(self):
        """True wenn Phasendaten T1-T6 enthalten (PST-Format)."""
        phases = self.data.get("phases", [])
        return bool(phases and "t1_c" in phases[0])

    def _is_vakuumtest(self):
        """True wenn nur T1 vorhanden (Vakuumtest / Prog 1)."""
        phases = self.data.get("phases", [])
        return bool(phases and "t1_c" in phases[0] and phases[0].get("t2_c") is None)

    def _t3_label(self):
        """T3 ist je Maschinenformat unterschiedlich belegt: beim alten
        BELIMED-Format (6-Spalten, Helios Krefeld) ist T3 der Luftnachweis-
        Sensor; im PST-Format (UNIKLINIK_ESSEN) ist T3 der Produktfuehler."""
        return "T3 Produktfühler" if self._is_pst_format() else "T3 Luftnachweis"

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
        self.cell(60, 4, f"{device} Nr:{nr} / DocuControl")

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

        self.set_font("Helvetica", "B", 10)
        self.set_text_color(200, 200, 200)
        self.set_xy(263, y + 3)
        self.cell(28, 10, "DocuControl", align="R")

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
            ("STERILISATION TEMP.", f"{d.get('temp_min', 0):.1f}  /  {d.get('temp_max', 0):.1f}", "MIN  /  MAX  °C", 126, 55),
            ("PROGRAMM", d.get("program_name", "-"), f"Nr. {d.get('program_nr', '-')} / {d.get('version', '-')}", 184, 55),
            ("BENUTZER", d.get("benutzer", "-"), "", 242, 45),
        ]

        # Fo-Wert-Box fuer PST-Format (ersetzt BENUTZER wenn Fo > 0)
        if self._is_pst_format() and d.get("f0_value", 0) > 0:
            fo_val = f"{d['f0_value']:.1f}"
            kpi_boxes[4] = ("ENDWERT FO T2", fo_val, "min", 242, 45)

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

        # Fuer BELIMED-Format: RTC-Zeiten aus cycle_start + time_offset berechnen
        if not self._is_pst_format():
            start_time = None
            try:
                cs = d.get("cycle_start", "")
                if "/" in cs:
                    start_time = datetime.strptime(cs.strip(), "%d.%m.%Y / %H:%M")
                elif "." in cs:
                    start_time = datetime.strptime(cs.strip(), "%d.%m.%Y %H:%M:%S")
            except Exception:
                start_time = None

            for p in phases:
                if not p.get("rtc_time") and start_time:
                    parts = p["time_offset"].split(":")
                    offset_sec = int(parts[0]) * 60 + int(parts[1])
                    rtc = start_time + timedelta(seconds=offset_sec)
                    p["rtc_time"] = rtc.strftime("%H:%M:%S")

        # Tabellen-Label
        self.set_font("Helvetica", "", 6)
        self.set_text_color(100, 100, 100)
        self.set_xy(10, y_table)
        self.cell(277, 4, "PROZESSDATEN", ln=True)
        y_table += 5

        total_phases = len(phases)
        use_two_cols = total_phases > 18
        max_rows_per_col = 26 if use_two_cols else 30

        # Format-abhaengige Spaltenbreiten und -koepfe
        if self._is_vakuumtest():
            col_w = [22, 60, 20, 20] if not use_two_cols else [18, 44, 14, 14]
            headers = ["Zeit", "Phase", "P2 mbar", "T1 °C"]
        elif self._is_pst_format():
            col_w = [22, 38, 13, 13, 13, 13, 13, 13, 13] if not use_two_cols \
                 else [16, 30, 10, 10, 10, 10, 10, 10, 10]
            headers = ["Zeit", "Phase", "P2", "T1 °C", "T2 °C",
                       "T3 °C", "T4 °C", "T5 °C", "T6 °C"]
        else:
            # Altes BELIMED-Format
            col_w = [18, 14, 38, 14, 14, 16] if use_two_cols else [22, 18, 60, 20, 20, 22]
            headers = ["Uhrzeit", "Prozess", "Phase", "T2 °C", "T3 °C", "P2 mbar"]

        def draw_table_header(x_off, y):
            self.set_fill_color(*TABLE_HEADER_BG)
            self.set_font("Helvetica", "B", 5.5 if use_two_cols else 6.5)
            self.set_text_color(80, 80, 80)
            self.set_xy(x_off, y)
            for i, h in enumerate(headers):
                a = "R" if i >= (2 if self._is_pst_format() or self._is_vakuumtest() else 3) else "L"
                self.cell(col_w[i], 5, h, border="B", fill=True, align=a)
            return y + 5

        def fmt(val, digits=1):
            return f"{val:.{digits}f}" if val is not None else "-"

        def draw_data_row(x_off, y, p, idx):
            fill = (250, 250, 252) if idx % 2 == 0 else (255, 255, 255)
            self.set_fill_color(*fill)
            fs = 5.5 if use_two_cols else 7
            rh = 4.5 if use_two_cols else 5.5
            self.set_font("Helvetica", "", fs)
            self.set_text_color(*BLACK)
            self.set_xy(x_off, y)

            if self._is_vakuumtest():
                self.cell(col_w[0], rh, p.get("rtc_time", p.get("time_offset", "")), fill=True)
                self.cell(col_w[1], rh, p.get("phase", ""), fill=True)
                self.cell(col_w[2], rh, str(p.get("p2_mbar", 0)), fill=True, align="R")
                self.cell(col_w[3], rh, fmt(p.get("t1_c")), fill=True, align="R")
            elif self._is_pst_format():
                self.cell(col_w[0], rh, p.get("rtc_time", p.get("time_offset", "")), fill=True)
                self.cell(col_w[1], rh, p.get("phase", ""), fill=True)
                self.cell(col_w[2], rh, str(p.get("p2_mbar", 0)), fill=True, align="R")
                self.cell(col_w[3], rh, fmt(p.get("t1_c")), fill=True, align="R")
                self.cell(col_w[4], rh, fmt(p.get("t2_c")), fill=True, align="R")
                self.cell(col_w[5], rh, fmt(p.get("t3_c")), fill=True, align="R")
                self.cell(col_w[6], rh, fmt(p.get("t4_c")), fill=True, align="R")
                self.cell(col_w[7], rh, fmt(p.get("t5_c")), fill=True, align="R")
                self.cell(col_w[8], rh, fmt(p.get("t6_c")), fill=True, align="R")
            else:
                # Altes BELIMED-Format: [Uhrzeit, Prozess, Phase, T2, T3, P2]
                rtc = p.get("rtc_time", "")
                t3_str = fmt(p.get("t3_c"))
                self.cell(col_w[0], rh, rtc, fill=True)
                self.cell(col_w[1], rh, p.get("time_offset", ""), fill=True)
                self.cell(col_w[2], rh, p.get("phase", ""), fill=True)
                self.cell(col_w[3], rh, fmt(p.get("t2_c", 0)), fill=True, align="R")
                self.cell(col_w[4], rh, t3_str, fill=True, align="R")
                self.cell(col_w[5], rh, str(p.get("p2_mbar", 0)), fill=True, align="R")

            self.set_draw_color(*TABLE_BORDER)
            rh = 4.5 if use_two_cols else 5.5
            self.line(x_off, y + rh, x_off + sum(col_w), y + rh)

        # Linke Spalte zeichnen
        x1 = 10
        y1 = draw_table_header(x1, y_table)
        rh = 4.5 if use_two_cols else 5.5
        for i, p in enumerate(phases[:max_rows_per_col]):
            yr = y1 + i * rh
            if yr > 172:
                break
            draw_data_row(x1, yr, p, i)

        # Rechte Spalte (wenn mehr als max_rows_per_col Zeilen)
        if use_two_cols and total_phases > max_rows_per_col:
            # Startposition der rechten Spalte: nach der linken
            x2 = 10 + sum(col_w) + 6
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

        start_time = None
        try:
            cs = self.data.get("cycle_start", "")
            if "/" in cs:
                start_time = datetime.strptime(cs.strip(), "%d.%m.%Y / %H:%M")
            elif "." in cs:
                start_time = datetime.strptime(cs.strip(), "%d.%m.%Y %H:%M:%S")
        except Exception:
            pass

        chart_path = generate_trend_chart(phases, start_time=start_time, t3_label=self._t3_label())
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
        except Exception:
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
        has_autoklavenbuch = bool(self.form_data)
        self.page_count_total = (1 + (1 if has_chart else 0)
                                 + (1 if has_handwritten else 0)
                                 + (1 if has_autoklavenbuch else 0))

        self.draw_page1()
        if has_chart:
            self.draw_page2()
        if has_handwritten:
            self.draw_handwritten_page()
        if has_autoklavenbuch:
            self.add_page(orientation='P', format='A4')
            self._draw_autoklavenbuch_page()
        self.output(output_path)

    def _draw_autoklavenbuch_page(self):
        """Autoklavenbuch-Formularseite im Hochformat A4 (210×297mm)."""
        fd = self.form_data

        # DejaVu Sans laden — unterstützt volle Unicode (—, ä/ö/ü/ß, °C, etc.)
        # Helvetica (Latin-1 only) crasht bei em-dash und anderen Unicode-Zeichen.
        _font_name = 'Helvetica'
        _DEJAVU   = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
        _DEJAVU_B = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
        if os.path.exists(_DEJAVU):
            try:
                self.add_font('DVSans', '',  _DEJAVU)
                self.add_font('DVSans', 'B', _DEJAVU_B)
                _font_name = 'DVSans'
            except Exception:
                pass  # bereits registriert oder Ladefehler — Fallback auf Helvetica

        def _sf(style='', size=9):
            self.set_font(_font_name, style, size)

        def _safe(text):
            if _font_name == 'Helvetica':
                return ''.join(c if ord(c) < 256 else '-' for c in str(text or ''))
            return str(text or '')

        # Header
        self.set_fill_color(*DARK_BLUE)
        self.rect(0, 0, 210, 20, 'F')
        self.set_xy(10, 5)
        _sf('B', 13)
        self.set_text_color(*WHITE)
        self.cell(130, 10, 'Autoklavenbuch — Chargendokumentation')
        self.set_xy(150, 5)
        _sf('', 7)
        self.cell(55, 4, 'Formular-Nr. 268627  Rev. 004/01.2024', align='R')
        self.set_xy(150, 10)
        self.cell(55, 4, 'Letzte Wartung: 22.07.2025', align='R')
        self.set_xy(150, 15)
        self.cell(55, 4, 'Letzte Überprüfung: 19.03.2026', align='R')

        y = 26
        col1_x, col2_x = 10, 110
        col_w = 95

        def section_title(title):
            nonlocal y
            self.set_fill_color(*TABLE_HEADER_BG)
            self.rect(10, y, 190, 6, 'F')
            self.set_xy(12, y + 0.5)
            _sf('B', 8)
            self.set_text_color(*DARK_BLUE)
            self.cell(186, 5, title)
            y += 8

        def field_row(label1, val1, label2='', val2=''):
            nonlocal y
            _sf('', 7)
            self.set_text_color(100, 100, 100)
            self.set_xy(col1_x, y)
            self.cell(col_w, 4, label1)
            if label2:
                self.set_xy(col2_x, y)
                self.cell(col_w, 4, label2)
            y += 4
            _sf('B', 9)
            self.set_text_color(*BLACK)
            self.set_xy(col1_x, y)
            self.cell(col_w, 5, _safe(val1) or '-')
            if label2:
                self.set_xy(col2_x, y)
                self.cell(col_w, 5, _safe(val2) or '-')
            y += 6

        def checkbox_row(items_checked, all_items):
            nonlocal y
            _sf('', 9)
            self.set_text_color(*BLACK)
            x = col1_x
            for item in all_items:
                checked = item in items_checked
                mark = '[X]' if checked else '[ ]'
                w = max(40, self.get_string_width(item) + 18)
                if x + w > 198:
                    x = col1_x
                    y += 5
                self.set_xy(x, y)
                self.cell(w, 5, mark + ' ' + item)
                x += w
            y += 6

        # Kopfdaten
        section_title('Kopfdaten')
        field_row('Standort / Location', fd.get('standort', ''), 'Datum', fd.get('datum', ''))
        field_row('Zyklus / Charge-Nr.', fd.get('zyklus', ''), 'Maschinenprogramm',
                  self.data.get('program_name', '') or self.data.get('program', ''))
        field_row('Kürzel', fd.get('operator_initials', ''))

        # Abfall stammt aus
        section_title('Abfall stammt aus')
        checkbox_row(fd.get('waste_origin', []), ['Tierhaltung', 'Labor', 'Andere Anlage'])

        # Sicherheitsstufe
        section_title('Sicherheitsstufe (GVO-Klasse)')
        checkbox_row([fd.get('safety_level', '')], ['S1', 'S2', 'Keine GVO'])

        # Art des Autoklaviergutes
        section_title('Art des Autoklaviergutes')
        checkbox_row(fd.get('autoklaviergut', []),
                     ['Käfigmaterial / Käfiggestelle', 'Einstreu / Futter', 'Papier / Wäsche',
                      'Laborabfälle', 'Flüssigkeiten', 'Tierkörper', 'OP-/Sektions-Besteck',
                      'Leercharge / Testcharge'])

        # Autoklavenprogramm
        section_title('Verwendetes Autoklavenprogramm')
        prog_key = fd.get('autoclave_program', '')
        prog_display_map = {
            'kaefige_normal': 'Käfige — Normalprogramm',
            'kaefige_121':    'Käfige — 121 °C',
            'kaefige_134':    'Käfige — 134 °C',
            'einstreu_75':    'Einstreu — 75 °C',
            'einstreu_121':   'Einstreu — 121 °C',
            'einstreu_134':   'Einstreu — 134 °C',
            'futter_75':      'Futter — 75 °C',
            'futter_121':     'Futter — 121 °C',
            'futter_134':     'Futter — 134 °C',
            'fluessigkeiten_121':  'Flüssigkeiten — 121 °C',
            'fluessigkeiten_134':  'Flüssigkeiten — 134 °C',
            'tierkoerper_121':     'Tierkörper — 121 °C',
            'tierkoerper_134':     'Tierkörper — 134 °C',
            'schleusen':      'Schleusenprogramm',
        }
        prog_display = prog_display_map.get(prog_key, _safe(prog_key) or '-')
        _sf('B', 11)
        self.set_text_color(*DARK_BLUE)
        self.set_xy(col1_x, y)
        self.cell(190, 6, prog_display)
        y += 8

        # Ergebnis
        section_title('Ergebnis')
        result_ok = fd.get('result', '') == 'ok'
        result_color = GREEN_BG if result_ok else RED_BG
        result_text = 'Ablauf OK' if result_ok else ('Störung' if fd.get('result') == 'err' else '-')
        self.set_fill_color(*result_color)
        _sf('B', 10)
        self.set_text_color(*WHITE)
        self.rect(col1_x, y, 50, 7, 'F')
        self.set_xy(col1_x, y)
        self.cell(50, 7, result_text, align='C')
        if not result_ok and fd.get('result_comment'):
            _sf('', 8)
            self.set_text_color(*BLACK)
            self.set_xy(65, y + 1)
            self.cell(130, 5, 'Bemerkung: ' + _safe(fd.get('result_comment', '')))
        y += 10

        # Bemerkungen (freies Feld)
        remarks = fd.get('remarks', '')
        if remarks:
            section_title('Bemerkungen')
            _sf('', 9)
            self.set_text_color(*BLACK)
            self.set_xy(col1_x, y)
            self.multi_cell(190, 5, _safe(remarks))
            y = self.get_y() + 3

        # Bestätigung
        section_title('Bestätigung')
        _sf('', 8)
        self.set_text_color(60, 60, 60)
        self.set_xy(col1_x, y)
        self.cell(190, 5,
                  'Ich bestätige, dass die eingegebenen Daten korrekt und vollständig sind '
                  'und der Autoklaviervorgang ordnungsgemäß durchgeführt wurde.')
        y += 7
        confirmed_at = fd.get('confirmed_at', '')
        if confirmed_at:
            try:
                from datetime import datetime as _dt
                ct = _dt.fromisoformat(confirmed_at)
                confirmed_at = ct.strftime('%d.%m.%Y %H:%M:%S')
            except Exception:
                pass
        field_row('Bestätigt durch', fd.get('confirmed_by', ''), 'Bestätigt am', confirmed_at)
        field_row('Kürzel', fd.get('confirmed_initials', ''), '', '')

        # Unterschrift
        sig_data = fd.get('signature', '')
        if sig_data:
            try:
                import base64, io
                b64 = sig_data.split(',', 1)[1] if ',' in sig_data else sig_data
                sig_stream = io.BytesIO(base64.b64decode(b64))
                _sf('', 7)
                self.set_text_color(100, 100, 100)
                self.set_xy(col1_x, y)
                self.cell(col_w, 4, 'Unterschrift')
                y += 4
                sig_h = 16
                self.set_draw_color(180, 180, 180)
                self.rect(col1_x, y, 55, sig_h)
                self.image(sig_stream, x=col1_x + 1, y=y + 1, w=53, h=sig_h - 2)
                y += sig_h + 4
            except Exception as e:
                logger.warning(f"Unterschrift konnte nicht eingebettet werden: {e}")

        # Fußzeile
        self.set_fill_color(*FOOTER_BG)
        self.rect(0, 285, 210, 12, 'F')
        self.set_xy(10, 287)
        _sf('', 6)
        self.set_text_color(*WHITE)
        self.cell(100, 4, 'DocuControl by GeTmatic — Automatisch generiert')
        self.set_xy(110, 287)
        self.cell(90, 4, 'Maschinendaten automatisch · Formular manuell ausgefüllt', align='R')


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
        "masch_nr": ((config.get("machine", {}) or {}).get("machine_nr", "") or "").strip().replace(" ", "_"),
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


def generate_pdf(raw_data, protocol_id, timestamp, config, rtc_timestamps=None, form_data=None):
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

    machine_nr = ((config.get("machine", {}) or {}).get("machine_nr", "") or "").strip()
    if machine_nr:
        protocol_data["maschinen_nr"] = machine_nr

    output_base, on_usb = get_output_dir(config)
    subfolder = build_subfolder(timestamp, config)
    output_dir = os.path.join(output_base, subfolder)
    os.makedirs(output_dir, exist_ok=True)

    filename = build_filename(protocol_id, timestamp, config, charge_nr=parsed_charge)
    pdf_path = os.path.join(output_dir, filename)

    pdf = SterilizationPDF(protocol_data, config, form_data=form_data)
    pdf.generate(pdf_path)

    file_size = os.path.getsize(pdf_path)
    update_protocol_pdf(protocol_id, pdf_path, filename, file_size)
    logger.info(f"PDF: {pdf_path} ({file_size}B)")
    return pdf_path, filename, file_size
