#!/usr/bin/env python3
"""
DocuPi-3000 — WD/RDG PDF Generator

Erzeugt professionelle Chargenprotokolle fuer Waschdesinfektoren.
Layout konsistent mit dem MST SterilizationPDF (Corporate Design).

Seitenaufbau:
  Seite 1: Header, KPI-Boxen, Schritt-Tabelle, Freigabebereich
  Seite 2: Temperaturverlauf-Chart
"""

import os
import logging
from datetime import datetime
from fpdf import FPDF

logger = logging.getLogger("docupi.wd_pdf")

# Farben (identisch mit MST pdf_generator.py)
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
ORANGE_WARN = (230, 126, 34)


class WashDisinfectorPDF(FPDF):
    """PDF-Generator fuer WD/RDG-Chargenprotokolle."""

    def __init__(self, protocol_data, config=None):
        super().__init__(orientation="L", format="A4")
        self.data = protocol_data
        self.config = config or {}
        self.page_count_total = 2
        self.set_auto_page_break(auto=False)

    # ---------------------------------------------------------------
    # HEADER (identisches Layout wie MST)
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
        device = d.get("machine_model", "Waschdesinfektor")
        self.cell(60, 12, device, ln=False)

        # Header-Felder
        fields = [
            ("CHARGE", str(d.get("charge_nr", "-")), 75, 20),
            ("PROGRAMM START", d.get("cycle_start_time", "-"), 100, 30),
            ("PROGRAMM ENDE", d.get("cycle_end_time", "-"), 133, 30),
            ("LAUFZEIT", d.get("cycle_duration_display", "-"), 166, 28),
        ]
        for label, value, x, w in fields:
            self.set_xy(x, 4)
            self.set_font("Helvetica", "", 6)
            self.set_text_color(120, 120, 120)
            self.cell(w, 4, label)
            self.set_xy(x, 9)
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(*BLACK)
            self.cell(w, 5, str(value)[:20])

        # Ergebnis-Box
        result = d.get("result", "")
        is_passed = result == "BESTANDEN"
        bg = GREEN_BG if is_passed else RED_BG
        self.set_fill_color(*bg)
        self.set_xy(198, 4)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*WHITE)
        self.cell(48, 8, result or "-", fill=True, align="C")
        # Detail
        self.set_xy(198, 13)
        self.set_font("Helvetica", "", 6)
        self.set_text_color(100, 100, 100)
        detail = d.get("result_detail", "")
        self.cell(48, 4, detail[:35])

        # Betreiber (rechts oben)
        self.set_xy(250, 4)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*DARK_BLUE)
        operator = d.get("operator", "")
        self.cell(40, 5, operator[:28], align="R")
        # Maschinen-Nr
        if d.get("machine_nr"):
            self.set_xy(250, 10)
            self.set_font("Helvetica", "", 6)
            self.set_text_color(120, 120, 120)
            self.cell(40, 4, f"Nr: {d['machine_nr']}", align="R")
        # Datum
        self.set_xy(250, 15)
        self.set_font("Helvetica", "", 6)
        self.set_text_color(120, 120, 120)
        self.cell(40, 4, d.get("cycle_start_date", ""), align="R")

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
        self.cell(60, 4, "MASCHINE / SERIENNUMMER")
        self.set_xy(10, y + 6)
        self.set_font("Helvetica", "B", 7)
        device = self.data.get("machine_model", "")
        nr = self.data.get("machine_nr", "")
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
    # KPI-BOXEN
    # ---------------------------------------------------------------
    def draw_kpi_boxes(self, y_start):
        d = self.data
        kpi = d.get("kpi", {})
        box_h = 25

        # A0-Wert
        a0 = kpi.get("a0_value", {})
        a0_text = f"{a0.get('act', '-')}" if a0 else "-"
        a0_sub = f"Soll >= {a0.get('nom', '-')}" if a0 else ""
        a0_ok = a0.get("passed", True) if a0 else True

        # Thermodesinfektion
        td = kpi.get("thermal_disinfection_temp", {})
        td_text = f"{td.get('min', '-')} / {td.get('max', '-')}" if td else "-"
        td_sub = f"Soll {td.get('nom_min', '-')} - {td.get('nom_max', '-')} \u00b0C" if td else ""
        td_ok = td.get("passed", True) if td else True

        # Leitwert
        cond = kpi.get("conductivity", {})
        cond_text = f"{cond.get('act', '-')} \u00b5S/cm" if cond else "-"
        cond_sub = f"max. {cond.get('max_allowed', '-')} \u00b5S/cm" if cond else ""
        cond_ok = cond.get("passed", True) if cond else True

        # Laufzeit
        dur = kpi.get("total_duration_sec", 0)
        if dur:
            mins, secs = divmod(dur, 60)
            dur_text = f"{mins}:{secs:02d} min"
        else:
            dur_text = d.get("cycle_duration_display", "-")

        boxes = [
            ("A0-WERT", a0_text, a0_sub, a0_ok, 10, 66),
            ("THERMODESINFEKTION", td_text, td_sub, td_ok, 79, 66),
            ("LEITWERT", cond_text, cond_sub, cond_ok, 148, 66),
            ("GESAMTLAUFZEIT", dur_text, "", True, 217, 70),
        ]

        for label, value, sub, ok, x, w in boxes:
            # Kopfzeile
            self.set_fill_color(*DARK_BLUE)
            self.rect(x, y_start, w, 6, "F")
            self.set_xy(x + 2, y_start + 1)
            self.set_font("Helvetica", "B", 6)
            self.set_text_color(*WHITE)
            self.cell(w - 4, 4, label)

            # Wert-Box
            if ok:
                self.set_fill_color(*LIGHT_GRAY)
            else:
                self.set_fill_color(250, 220, 220)
            self.rect(x, y_start + 6, w, box_h - 6, "F")

            # Wert
            self.set_xy(x + 2, y_start + 8)
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(*BLACK if ok else RED_BG)
            self.cell(w - 4, 8, str(value)[:22], align="C")

            # Unterzeile
            if sub:
                self.set_xy(x + 2, y_start + 17)
                self.set_font("Helvetica", "", 5.5)
                self.set_text_color(120, 120, 120)
                self.cell(w - 4, 4, sub, align="C")

        return y_start + box_h + 3

    # ---------------------------------------------------------------
    # SCHRITT-TABELLE
    # ---------------------------------------------------------------
    def draw_step_table(self, y_start):
        steps = self.data.get("steps", [])
        if not steps:
            return y_start

        # Tabellenkopf-Label
        self.set_font("Helvetica", "", 6)
        self.set_text_color(100, 100, 100)
        self.set_xy(10, y_start)
        self.cell(277, 4, "PROZESSSCHRITTE", ln=True)
        y = y_start + 5

        # Spaltenbreiten
        col_w = [14, 16, 42, 26, 38, 38, 28, 30, 45]
        headers = [
            "Schritt", "Uhrzeit", "Name",
            "Zeit (sec)", "Temp. Soll (\u00b0C)", "Temp. Ist (\u00b0C)",
            "Dosierung", "Leitwert", "Sonstiges",
        ]

        # Header-Zeile
        self.set_fill_color(*TABLE_HEADER_BG)
        x = 10
        for i, (header, w) in enumerate(zip(headers, col_w)):
            self.set_xy(x, y)
            self.set_font("Helvetica", "B", 5.5)
            self.set_text_color(*DARK_BLUE)
            self.rect(x, y, w, 6, "F")
            self.cell(w, 6, header, align="C")
            x += w
        y += 7

        # Datenzeilen
        row_h = 8
        for idx, step in enumerate(steps):
            p = step.get("params", {})

            # Alternierend grau/weiss
            if idx % 2 == 0:
                self.set_fill_color(248, 248, 248)
            else:
                self.set_fill_color(*WHITE)

            x = 10
            cells = []

            # Schritt-ID
            cells.append(step["id"])

            # Uhrzeit
            cells.append(step["time"][:5])

            # Name
            cells.append(step.get("name_display", "")[:22])

            # Zeit nom/act
            st = p.get("step_time", {})
            if st:
                cells.append(f"{st.get('nom', '-')} / {st.get('act', '-')}")
            else:
                cells.append("-")

            # Temp Soll min-max
            tn = p.get("temp_nominal", {})
            if tn and (tn.get("min", 0) > 0 or tn.get("max", 0) > 0):
                cells.append(f"{tn['min']:.1f} - {tn['max']:.1f}")
            else:
                cells.append("-")

            # Temp Ist min-max
            ta = p.get("temp_actual", {})
            if ta:
                cells.append(f"{ta['min']:.1f} - {ta['max']:.1f}")
            else:
                cells.append("-")

            # Dosierung
            dos = p.get("dosing", {})
            if dos:
                cells.append(f"{dos['act']} ml")
            else:
                cells.append("-")

            # Leitwert
            cond = p.get("conductivity", {})
            if cond:
                cells.append(f"{cond['act']} \u00b5S/cm")
            else:
                cells.append("-")

            # Sonstiges (A0)
            a0 = p.get("a0_value", {})
            if a0:
                cells.append(f"A0: {a0['act']} (Soll {a0['nom']})")
            else:
                cells.append("")

            # Zeile zeichnen
            for i, (cell_text, w) in enumerate(zip(cells, col_w)):
                self.set_xy(x, y)
                self.rect(x, y, w, row_h, "F")
                self.set_draw_color(*TABLE_BORDER)
                self.rect(x, y, w, row_h, "D")

                # Farbkodierung fuer Temperatur-Abweichungen
                self.set_font("Helvetica", "", 6)
                self.set_text_color(*BLACK)

                # Temp Ist pruefen gegen Temp Soll
                if i == 5 and ta and tn:
                    if tn.get("min", 0) > 0 and ta.get("min", 0) < tn["min"]:
                        self.set_text_color(*RED_BG)
                    elif tn.get("max", 0) > 0 and ta.get("max", 0) > tn["max"]:
                        self.set_text_color(*RED_BG)

                self.cell(w, row_h, cell_text, align="C")
                x += w

            y += row_h

        return y + 3

    # ---------------------------------------------------------------
    # FREIGABE-BEREICH
    # ---------------------------------------------------------------
    def draw_signature(self, y_start):
        y = max(y_start, 160)

        self.set_draw_color(*TABLE_BORDER)
        self.rect(10, y, 277, 30, "D")

        self.set_xy(15, y + 2)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*DARK_BLUE)
        self.cell(60, 5, "FREIGABE")

        # Ja/Nein Checkboxen
        self.set_xy(15, y + 9)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*BLACK)
        self.cell(5, 5, "", border=1)
        self.cell(20, 5, "  Ja")
        self.cell(5, 5, "", border=1)
        self.cell(20, 5, "  Nein")

        # Unterschrift
        self.set_xy(100, y + 9)
        self.cell(30, 5, "Unterschrift:")
        self.line(135, y + 14, 200, y + 14)

        # Datum
        self.set_xy(210, y + 9)
        self.cell(20, 5, "Datum:")
        self.line(232, y + 14, 280, y + 14)

        # Bemerkung
        self.set_xy(15, y + 18)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(120, 120, 120)
        self.cell(60, 4, "Bemerkung:")
        self.line(15, y + 26, 280, y + 26)

    # ---------------------------------------------------------------
    # SEITE 1
    # ---------------------------------------------------------------
    def draw_page1(self):
        self.add_page()
        self.draw_header()
        y = self.draw_kpi_boxes(32)
        y = self.draw_step_table(y)
        self.draw_signature(y)
        self.draw_footer(1)

    # ---------------------------------------------------------------
    # SEITE 2: CHART
    # ---------------------------------------------------------------
    def draw_page2(self, chart_path=None):
        self.add_page()
        self.draw_header()

        if chart_path and os.path.exists(chart_path):
            # Chart einbetten
            self.set_xy(10, 32)
            self.set_font("Helvetica", "", 6)
            self.set_text_color(100, 100, 100)
            self.cell(277, 4, "TEMPERATURVERLAUF")

            self.image(chart_path, x=10, y=38, w=277)
        else:
            self.set_xy(10, 80)
            self.set_font("Helvetica", "", 12)
            self.set_text_color(180, 180, 180)
            self.cell(277, 10, "Kein Chart verfuegbar", align="C")

        self.draw_footer(2)

    # ---------------------------------------------------------------
    # GENERIERUNG
    # ---------------------------------------------------------------
    def generate(self, output_path, chart_path=None):
        """Erzeugt das vollstaendige PDF."""
        self.draw_page1()
        self.draw_page2(chart_path)
        self.output(output_path)
        logger.info("WD-PDF erzeugt: %s", output_path)
        return output_path


def generate_wd_pdf(protocol_data, config=None, output_path=None, chart_path=None):
    """Convenience-Funktion: Erzeugt WD-PDF aus Protokolldaten.

    Args:
        protocol_data: Dict aus parse_wd_protocol()
        config: Optionale Konfiguration
        output_path: Ziel-PDF-Pfad (None = automatisch generiert)
        chart_path: Pfad zum Chart-PNG (None = kein Chart)

    Returns:
        Pfad zur erzeugten PDF-Datei.
    """
    if not output_path:
        d = protocol_data
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        model = d.get("machine_model", "WD").replace(" ", "_")
        charge = d.get("charge_nr", "0")
        output_path = f"{model}_Charge_{charge}_{ts}.pdf"

    pdf = WashDisinfectorPDF(protocol_data, config)
    return pdf.generate(output_path, chart_path)
