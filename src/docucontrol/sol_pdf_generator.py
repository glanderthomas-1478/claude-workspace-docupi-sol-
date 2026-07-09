#!/usr/bin/env python3
"""
DocuControl-SOL - PDF Generator fuer das Temperaturprotokoll (Druckgasflaschen-Abfuellung)

Bildet die Struktur des echten SOL-Papierformulars "Temperaturprotokoll (IF.103A)"
nach: Kopf (Charge-Nr., Abfueller, Referenztemperatur, verwendete Fuehler), zweispaltige
Tabelle mit einer Zeile pro gescannter Flasche (Protokoll-Nr. / Datum-Uhrzeit / Code /
Sichtpruefung / Restdruck / IR-Temp), Fusszeile mit Min/Max ueber alle Messungen +
digitaler Unterschrift des Bedieners. Sichtpruefung + Restdruck am 2026-07-09 ergaenzt
(GMP-Vorpruefungen vor der Befuellung laut EU-GMP-Anhang 6 Ziffer 5.3.5/6).

Die Tabelle nutzt pro Seite zwei nebeneinander liegende Spaltenbloecke und packt so
deutlich mehr Flaschen-Zeilen auf jede Seite (bis zu 160 Flaschen passen dadurch meist
auf nur 1-2 Seiten statt auf 9). Die Seitenanzahl wird dynamisch anhand des tatsaechlich
verfuegbaren Platzes berechnet (Seite 1 hat wegen des Kopf-Blocks weniger Platz als
Folgeseiten, die letzte Seite reserviert zusaetzlich Platz fuer Zusammenfassung+Unterschrift).

Referenz: reference/screenshots/Bilder SOL Daten/ (Fotos des Original-Formulars).
"""

import os
import logging
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import AccessPermission

from pdf_generator import get_output_dir, build_subfolder

logger = logging.getLogger("docupi.sol_pdf")

# Farben (gleiche Palette wie pdf_generator.py, fuer visuelle Konsistenz)
DARK_BLUE = (31, 78, 121)
MID_BLUE = (46, 117, 182)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
TABLE_HEADER_BG = (230, 235, 240)
TABLE_BORDER = (200, 200, 200)
ROW_ALT_BG = (247, 249, 251)
NOK_BG = (248, 214, 214)
NOK_TEXT = (150, 30, 30)
FOOTER_BG = (50, 60, 75)

# Layout-Konstanten fuer die zweispaltige Flaschen-Tabelle (in mm, A4 Hochformat 210x297).
ROW_H = 5.0
TABLE_HEAD_H = 6.0
FOOTER_TOP = 285.0
LAST_PAGE_RESERVE = 47.0  # Platz fuer Min/Max-Zusammenfassung + Unterschriftsblock auf der letzten Seite
CONTENT_LEFT = 10.0
CONTENT_WIDTH = 190.0  # bis x=200, symmetrisch zu den 10mm links (A4=210mm breit)
COL_GAP = 6.0
COL_WIDTH = (CONTENT_WIDTH - COL_GAP) / 2  # 92mm
COL_X = [CONTENT_LEFT, CONTENT_LEFT + COL_WIDTH + COL_GAP]
# Sicht./Restdr. am 2026-07-09 ergaenzt (GMP-Vorpruefungen vor der Befuellung, EU-GMP-Anhang 6
# Ziffer 5.3.5/6); "dt" dafuer von vormals 41mm gekuerzt (Datum/Zeit passt weiterhin,
# Summe = COL_WIDTH (92mm) bleibt unveraendert).
SUBCOL = {"nr": 9.0, "dt": 27.0, "code": 20.0, "sicht": 11.0, "restdr": 14.0, "temp": 11.0}

# DejaVu Sans unterstuetzt volle Unicode (ä/ö/ü/ß, °, — usw.), Helvetica (Latin-1
# only) crasht dabei - gleiches Muster wie in pdf_generator.py._draw_autoklavenbuch_page().
_DEJAVU = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
_DEJAVU_B = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


class SolTemperaturProtokollPDF(FPDF):
    def __init__(self, charge, bottles, config):
        super().__init__(orientation="P", format="A4")
        self.charge = charge
        self.bottles = bottles
        self.config = config
        self.page_count_total = 1  # wird in build() vor dem Zeichnen final gesetzt
        self.set_auto_page_break(auto=False)

        self._font_name = "Helvetica"
        if os.path.exists(_DEJAVU):
            try:
                self.add_font("DVSans", "", _DEJAVU)
                self.add_font("DVSans", "B", _DEJAVU_B)
                self._font_name = "DVSans"
            except Exception:
                pass  # bereits registriert oder Ladefehler - Fallback auf Helvetica

    def _sf(self, style="", size=9):
        self.set_font(self._font_name, style, size)

    def _safe(self, text):
        """Sanitisiert Text nur, wenn DejaVu nicht verfuegbar ist (Helvetica-Fallback)."""
        if self._font_name == "Helvetica":
            return "".join(c if ord(c) < 256 else "-" for c in str(text or ""))
        return str(text if text is not None else "")

    # ---------------------------------------------------------------
    # HEADER (jede Seite)
    # ---------------------------------------------------------------
    def draw_header(self, page_nr):
        c = self.charge
        cfg_pdf = self.config.get("pdf", {})
        standort = (self.config.get("sol", {}) or {}).get("standort_kuerzel", "")

        self.set_fill_color(*WHITE)
        self.rect(0, 0, 210, 26, "F")
        self.set_draw_color(*TABLE_BORDER)
        self.line(0, 26, 210, 26)

        self.set_xy(10, 6)
        self._sf("B", 16)
        self.set_text_color(*DARK_BLUE)
        self.cell(140, 8, self._safe(cfg_pdf.get("header_text", "DocuControl") or "DocuControl"))

        self.set_xy(10, 15)
        self._sf("", 10)
        self.set_text_color(80, 80, 80)
        title = "Temperaturprotokoll - Druckgasflaschen-Abfüllung"
        if standort:
            title += f" ({standort})"
        self.cell(140, 6, self._safe(title))

        self.set_xy(150, 6)
        self._sf("", 7)
        self.set_text_color(120, 120, 120)
        self.cell(50, 4, "Charge", align="R")
        self.set_xy(150, 11)
        self._sf("B", 11)
        self.set_text_color(*DARK_BLUE)
        self.cell(50, 6, self._safe(c.get("charge_nr", "")), align="R")

        self.set_xy(150, 19)
        self._sf("", 7)
        self.set_text_color(120, 120, 120)
        self.cell(50, 4, f"Seite {page_nr}/{self.page_count_total}", align="R")

    # ---------------------------------------------------------------
    # META-BLOCK (nur Seite 1): Charge-Metadaten wie im Papierformular
    # ---------------------------------------------------------------
    def draw_meta_block(self):
        c = self.charge
        y = 32
        row_h = 7
        rows = [
            ("Abfüller", c.get("operator_name") or "-"),
            ("Charge", c.get("charge_nr") or "-"),
            ("Referenztemperatur", f"{c.get('room_temp'):.1f} °C" if c.get("room_temp") is not None else "-"),
            ("Verwendete Fühler", c.get("sensor_names") or "-"),
            ("Anzahl Messung Flaschen", str(len(self.bottles))),
        ]
        self.set_draw_color(*TABLE_BORDER)
        for label, value in rows:
            self.set_xy(10, y)
            self._sf("B", 8.5)
            self.set_text_color(60, 60, 60)
            self.cell(55, row_h, self._safe(label))
            self._sf("", 8.5)
            self.set_text_color(*BLACK)
            self.cell(120, row_h, self._safe(value))
            self.line(10, y + row_h, 200, y + row_h)
            y += row_h
        return y + 4

    # ---------------------------------------------------------------
    # SEITEN-KAPAZITAET (fuer die dynamische Paginierung in build())
    # ---------------------------------------------------------------
    @staticmethod
    def _page_top(is_first):
        # Seite 1: 32 (Kopf-Ende) + 5 Metazeilen * 7mm + 4mm Abstand = 71
        return 71.0 if is_first else 32.0

    @classmethod
    def _rows_per_column(cls, is_first, is_last):
        top = cls._page_top(is_first) + TABLE_HEAD_H
        bottom = (FOOTER_TOP - LAST_PAGE_RESERVE) if is_last else FOOTER_TOP
        avail = max(0.0, bottom - top)
        return max(1, int(avail // ROW_H))

    @classmethod
    def _page_capacity(cls, is_first, is_last):
        return cls._rows_per_column(is_first, is_last) * 2  # zwei Spalten pro Seite

    @classmethod
    def _paginate(cls, bottles):
        """Verteilt die Flaschen-Liste dynamisch auf so wenige Seiten wie moeglich.
        Greedy von vorne: jede Seite bekommt so viele Zeilen, wie passen, ausser der
        Rest wuerde bereits auf DIESE Seite passen, wenn sie als letzte Seite (mit
        Zusammenfassungs-/Unterschriftsblock) gerechnet wird - dann ist sie die letzte."""
        indexed = list(enumerate(bottles))
        pages = []
        page_nr = 1
        while indexed:
            is_first = (page_nr == 1)
            cap_last = cls._page_capacity(is_first, True)
            if len(indexed) <= cap_last:
                pages.append(indexed)
                indexed = []
            else:
                cap_not_last = cls._page_capacity(is_first, False)
                pages.append(indexed[:cap_not_last])
                indexed = indexed[cap_not_last:]
            page_nr += 1
        return pages or [[]]

    # ---------------------------------------------------------------
    # TABELLEN-KOPF (zweispaltig)
    # ---------------------------------------------------------------
    def draw_table_head(self, y):
        self._sf("B", 7)
        self.set_text_color(60, 60, 60)
        for x0 in COL_X:
            self.set_fill_color(*TABLE_HEADER_BG)
            self.rect(x0, y, COL_WIDTH, TABLE_HEAD_H, "F")
            cx = x0
            self.set_xy(cx, y + 0.5)
            self.cell(SUBCOL["nr"], TABLE_HEAD_H - 1, "Nr.", align="C")
            cx += SUBCOL["nr"]
            self.set_xy(cx, y + 0.5)
            self.cell(SUBCOL["dt"], TABLE_HEAD_H - 1, "Datum / Uhrzeit", align="C")
            cx += SUBCOL["dt"]
            self.set_xy(cx, y + 0.5)
            self.cell(SUBCOL["code"], TABLE_HEAD_H - 1, "Code", align="C")
            cx += SUBCOL["code"]
            self.set_xy(cx, y + 0.5)
            self.cell(SUBCOL["sicht"], TABLE_HEAD_H - 1, "Sicht.", align="C")
            cx += SUBCOL["sicht"]
            self.set_xy(cx, y + 0.5)
            self.cell(SUBCOL["restdr"], TABLE_HEAD_H - 1, "Restdr.", align="C")
            cx += SUBCOL["restdr"]
            self.set_xy(cx, y + 0.5)
            self.cell(SUBCOL["temp"], TABLE_HEAD_H - 1, "Temp [°C]", align="C")
        return y + TABLE_HEAD_H

    # ---------------------------------------------------------------
    # TABELLEN-ZEILEN (zweispaltig: linke Spalte zuerst voll, dann rechte)
    # ---------------------------------------------------------------
    def draw_table_rows(self, y_top, indexed_bottles):
        n = len(indexed_bottles)
        split = -(-n // 2)  # linke Spalte bekommt bei ungerader Anzahl die zusaetzliche Zeile
        self._draw_column(COL_X[0], y_top, indexed_bottles[:split])
        self._draw_column(COL_X[1], y_top, indexed_bottles[split:])

    def _draw_column(self, x0, y_top, indexed_bottles):
        y = y_top
        for global_idx, b in indexed_bottles:
            is_nok = bool(b.get("is_nok"))
            bg = NOK_BG if is_nok else (ROW_ALT_BG if global_idx % 2 else WHITE)
            self.set_fill_color(*bg)
            self.rect(x0, y, COL_WIDTH, ROW_H, "F")
            self.set_draw_color(*TABLE_BORDER)
            self.rect(x0, y, COL_WIDTH, ROW_H)

            # Absichtlich immer Regular-Gewicht (nicht Bold bei NOK): DejaVu-Bold ist breiter
            # und liess bei knapp bemessenen Spalten (insbesondere "dt") Text in die naechste
            # Spalte hineinlaufen (gefunden 2026-07-09 im Live-Test auf dem Pi). Rote Schrift +
            # roter Zeilenhintergrund reichen als NOK-Kennzeichnung aus.
            text_color = NOK_TEXT if is_nok else BLACK
            self._sf("", 7)
            self.set_text_color(*text_color)

            cx = x0
            self.set_xy(cx, y + 0.75)
            self.cell(SUBCOL["nr"], ROW_H - 1.5, str(b.get("seq_nr", "")), align="C")
            cx += SUBCOL["nr"]

            ts = (b.get("scanned_at") or "").replace("T", " ")
            ts_display = ts.split(".")[0] if "." in ts else ts
            self.set_xy(cx, y + 0.75)
            self.cell(SUBCOL["dt"], ROW_H - 1.5, ts_display, align="C")
            cx += SUBCOL["dt"]

            self.set_xy(cx, y + 0.75)
            self.cell(SUBCOL["code"], ROW_H - 1.5, self._safe(b.get("scan_code", "")), align="C")
            cx += SUBCOL["code"]

            visual_ok = b.get("visual_check_ok")
            visual_str = "i.O." if visual_ok else ("n.i.O." if visual_ok is not None else "-")
            self.set_xy(cx, y + 0.75)
            self.cell(SUBCOL["sicht"], ROW_H - 1.5, self._safe(visual_str), align="C")
            cx += SUBCOL["sicht"]

            pressure_ok = b.get("residual_pressure_ok")
            pressure_str = "i.O." if pressure_ok else ("n.i.O." if pressure_ok is not None else "-")
            self.set_xy(cx, y + 0.75)
            self.cell(SUBCOL["restdr"], ROW_H - 1.5, self._safe(pressure_str), align="C")
            cx += SUBCOL["restdr"]

            temp = b.get("ir_temp")
            temp_str = f"{temp:.1f}" if temp is not None else "-"
            self.set_xy(cx, y + 0.75)
            self.cell(SUBCOL["temp"], ROW_H - 1.5, temp_str, align="C")

            y += ROW_H

    # ---------------------------------------------------------------
    # FOOTER (jede Seite)
    # ---------------------------------------------------------------
    def draw_footer(self, page_nr, is_last_page):
        y = FOOTER_TOP
        if is_last_page:
            temps = [b["ir_temp"] for b in self.bottles if b.get("ir_temp") is not None]
            nok_count = sum(1 for b in self.bottles if b.get("is_nok"))
            summary_y = y - 14
            self._sf("B", 8)
            self.set_text_color(*BLACK)
            self.set_xy(10, summary_y)
            if temps:
                self.cell(90, 5, f"Min (gesamt): {min(temps):.1f} °C    Max (gesamt): {max(temps):.1f} °C")
            self.set_xy(100, summary_y)
            self.cell(100, 5, f"Flaschen gesamt: {len(self.bottles)}    Davon NOK: {nok_count}", align="R")

            c = self.charge
            process_status = c.get("process_status") or ""
            if process_status:
                label = "Ordnungsgemäßer Ablauf" if process_status == "ordnungsgemaess" else "Störung im Ablauf"
                self._sf("B", 8)
                self.set_text_color(176, 37, 49) if process_status == "stoerung" else self.set_text_color(*BLACK)
                self.set_xy(10, summary_y + 5)
                self.cell(190, 5, self._safe("Ablauf: " + label))
                self.set_text_color(*BLACK)
            sig_y = summary_y - 33
            self.set_draw_color(*TABLE_BORDER)
            self._sf("", 7)
            self.set_text_color(100, 100, 100)
            self.set_xy(10, sig_y)
            self.cell(90, 4, self._safe("Bestätigt korrekt gemessen von (Bediener/Abfüller):"))

            sig_data_url = c.get("confirmed_signature") or ""
            if sig_data_url.startswith("data:image/"):
                try:
                    import base64
                    import io
                    b64 = sig_data_url.split(",", 1)[1]
                    sig_stream = io.BytesIO(base64.b64decode(b64))
                    self.rect(10, sig_y + 5, 70, 20)
                    self.image(sig_stream, x=11, y=sig_y + 6, w=68, h=18)
                except Exception as e:
                    logger.warning("Unterschrift konnte nicht eingebettet werden: %s", e)
                    self.rect(10, sig_y + 5, 70, 20)
            else:
                self.rect(10, sig_y + 5, 70, 20)

            self.line(10, sig_y + 26, 90, sig_y + 26)
            self.set_xy(10, sig_y + 27)
            self._sf("B", 8)
            self.set_text_color(*BLACK)
            self.cell(90, 4, self._safe(c.get("operator_name") or ""))

        self.set_fill_color(*FOOTER_BG)
        self.rect(0, y, 210, 12, "F")
        self.set_xy(10, y + 2)
        self._sf("", 6)
        self.set_text_color(*WHITE)
        self.cell(100, 4, self._safe("DocuControl - Automatisch generiert"))
        self.set_xy(110, y + 2)
        self.cell(90, 4, datetime.now().strftime("%d.%m.%Y %H:%M:%S"), align="R")

    # ---------------------------------------------------------------
    # SEITENAUFBAU GESAMT
    # ---------------------------------------------------------------
    def build(self):
        pages = self._paginate(self.bottles)
        self.page_count_total = len(pages)

        for page_nr, page_items in enumerate(pages, start=1):
            self.add_page()
            self.draw_header(page_nr)
            if page_nr == 1:
                y = self.draw_meta_block()
            else:
                y = 32
            y = self.draw_table_head(y)
            self.draw_table_rows(y, page_items)
            self.draw_footer(page_nr, is_last_page=(page_nr == len(pages)))


def build_sol_filename(charge, timestamp, config):
    charge_nr = str(charge.get("charge_nr", "")).replace(" ", "_").replace("/", "-")
    sep = config["pdf"].get("filename_separator", "_")
    name = f"{timestamp.strftime('%Y-%m-%d')}{sep}{timestamp.strftime('%H%M%S')}{sep}SOL{sep}{charge_nr}"
    while sep + sep in name:
        name = name.replace(sep + sep, sep)
    return f"{name.strip(sep)}.pdf"


def generate_sol_pdf(charge, bottles, config):
    """Erzeugt das PDF-Temperaturprotokoll fuer eine abgeschlossene SOL-Charge.

    Rueckgabe: (pdf_path, pdf_filename, file_size_bytes)
    """
    timestamp = datetime.now()
    pdf = SolTemperaturProtokollPDF(charge, bottles, config)
    pdf.build()

    # Nicht beschreibbares PDF (User-Vorgabe 2026-07-08): Ansehen/Drucken/Kopieren bleibt erlaubt,
    # Bearbeiten/Kommentieren/Formularfelder/Neuzusammenstellen wird gesperrt. Das Owner-Passwort
    # dient nur der Durchsetzung dieser Berechtigungs-Flags (RC4/PDF-Standard-"Schreibschutz"),
    # nicht als echte Verschluesselung - kein Passwort zum Oeffnen/Ansehen noetig.
    pdf.set_encryption(
        owner_password="docucontrol-sol",
        permissions=AccessPermission.PRINT_LOW_RES | AccessPermission.PRINT_HIGH_RES
        | AccessPermission.COPY | AccessPermission.COPY_FOR_ACCESSIBILITY,
    )

    base_dir, _ = get_output_dir(config)
    subfolder = build_subfolder(timestamp, config)
    out_dir = os.path.join(base_dir, subfolder) if subfolder else base_dir
    os.makedirs(out_dir, exist_ok=True)

    filename = build_sol_filename(charge, timestamp, config)
    pdf_path = os.path.join(out_dir, filename)
    pdf.output(pdf_path)
    file_size = os.path.getsize(pdf_path)
    logger.info("SOL-PDF erzeugt: %s (%d Bytes)", pdf_path, file_size)
    return pdf_path, filename, file_size
