#!/usr/bin/env python3
"""Add handwritten emergency documentation fields to PDF + config toggle."""

# ===== 1. CONFIG =====
with open("/home/belimed/docupi/config.py", "r") as f:
    cfg = f.read()

if "handwritten_fields" not in cfg:
    cfg = cfg.replace(
        '"filename_separator": "_",',
        '"filename_separator": "_",\n        "handwritten_fields": false,'
    )
    with open("/home/belimed/docupi/config.py", "w") as f:
        f.write(cfg)
    print("OK: config.py updated")
else:
    print("SKIP: config already has handwritten_fields")


# ===== 2. PDF GENERATOR =====
with open("/home/belimed/docupi/pdf_generator.py", "r") as f:
    pdf = f.read()

if "draw_handwritten_page" not in pdf:
    # Add the handwritten fields method to the class
    handwritten_method = '''
    # ---------------------------------------------------------------
    # PAGE: Handschriftliche Dokumentation (Notfallkonzept)
    # ---------------------------------------------------------------
    def draw_handwritten_page(self):
        """Seite mit leeren Feldern fuer handschriftliche Container/Sieb-Dokumentation."""
        self.add_page()
        self.draw_header()

        y = 32
        # Section title
        self.set_fill_color(31, 78, 121)
        self.rect(10, y, 277, 7, "F")
        self.set_xy(12, y + 1)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(255, 255, 255)
        self.cell(200, 5, "HANDSCHRIFTLICHE DOKUMENTATION (NOTFALLKONZEPT)")
        y += 10

        # Subtitle
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(120, 120, 120)
        self.set_xy(10, y)
        self.cell(277, 4, "Bitte leserlich ausfuellen. Dieses Blatt dient als Backup-Dokumentation bei Ausfall des Hauptsystems.")
        y += 8

        # --- Container / Siebe Tabelle ---
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(31, 78, 121)
        self.set_xy(10, y)
        self.cell(130, 5, "STERILISIERTE CONTAINER / SIEBE / INSTRUMENTE")
        y += 6

        # Table header
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

        # 12 empty rows for handwriting
        self.set_font("Helvetica", "", 7)
        self.set_text_color(200, 200, 200)
        for row in range(12):
            self.set_xy(10, y)
            self.set_text_color(180, 180, 180)
            self.cell(col_w[0], 7, str(row + 1), border=1, align="C")
            for i in range(1, len(col_w)):
                self.cell(col_w[i], 7, "", border=1)
            y += 7

        y += 4

        # --- Beladungsmuster ---
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(31, 78, 121)
        self.set_xy(10, y)
        self.cell(80, 5, "BELADUNGSMUSTER")
        self.set_font("Helvetica", "I", 6)
        self.set_text_color(150, 150, 150)
        self.cell(100, 5, "(Skizze der Beladungspositionen im Sterilisator)")
        y += 6

        # Empty box for sketch
        self.set_draw_color(180, 180, 180)
        self.rect(10, y, 135, 30)
        # Grid lines inside (light)
        self.set_draw_color(230, 230, 230)
        for gx in range(1, 5):
            self.line(10 + gx * 27, y, 10 + gx * 27, y + 30)
        for gy in range(1, 3):
            self.line(10, y + gy * 10, 145, y + gy * 10)

        # --- Verpackungsart (right side) ---
        rx = 155
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(31, 78, 121)
        self.set_xy(rx, y - 6)
        self.cell(80, 5, "VERPACKUNGSART")
        # Checkboxes
        self.set_draw_color(100, 100, 100)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(0, 0, 0)
        options = [
            "Sterilcontainer (starr)",
            "Einmal-Sterilisierverpackung",
            "Doppelt verpackt (Klarsicht)",
            "Klarsicht-Sterilisierverp.",
            "Unverpackt / Einzelinstrument",
            "Sonstiges: ________________",
        ]
        for i, opt in enumerate(options):
            oy = y + i * 5
            self.rect(rx, oy + 0.5, 3.5, 3.5)
            self.set_xy(rx + 5, oy)
            self.cell(80, 4.5, opt)

        y += 35

        # --- Freigabe (erweitert) ---
        self.set_draw_color(180, 180, 180)
        self.line(10, y, 287, y)
        y += 3

        self.set_font("Helvetica", "B", 8)
        self.set_text_color(31, 78, 121)
        self.set_xy(10, y)
        self.cell(130, 5, "STERILGUT-FREIGABE")
        y += 7

        # Freigabe table
        self.set_draw_color(180, 180, 180)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(0, 0, 0)

        # Row 1: Freigabe-Entscheidung
        self.set_xy(10, y)
        self.set_font("Helvetica", "", 6.5)
        self.set_text_color(100, 100, 100)
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

        # Row 2: Bemerkungen zur bedingten Freigabe
        self.set_font("Helvetica", "", 6.5)
        self.set_text_color(100, 100, 100)
        self.set_xy(10, y)
        self.cell(80, 4, "BEMERKUNGEN ZUR BEDINGTEN FREIGABE")
        y += 4
        self.set_draw_color(180, 180, 180)
        self.line(10, y + 5, 200, y + 5)
        self.line(10, y + 11, 200, y + 11)

        # Row 3: Signatures
        y += 15
        sig_fields = [
            ("BELADEN DURCH", 10, 55),
            ("ENTLADEN DURCH", 70, 55),
            ("FREIGABE DURCH", 135, 55),
            ("DATUM / UHRZEIT", 200, 45),
            ("UNTERSCHRIFT", 250, 37),
        ]
        self.set_font("Helvetica", "", 6)
        self.set_text_color(100, 100, 100)
        for label, x, w in sig_fields:
            self.set_xy(x, y)
            self.cell(w, 3, label)
            self.set_draw_color(150, 150, 150)
            self.line(x, y + 9, x + w, y + 9)

        self.draw_footer(2)

'''

    # Insert before draw_page2
    pdf = pdf.replace(
        "    # ---------------------------------------------------------------\n    # PAGE 2: Data Table",
        handwritten_method + "\n    # ---------------------------------------------------------------\n    # PAGE 2: Data Table"
    )

    # Update generate() to conditionally include handwritten page
    old_generate = '''    def generate(self, output_path):
        self.draw_page1()
        self.draw_page2()
        self.draw_page3()
        self.output(output_path)'''

    new_generate = '''    def generate(self, output_path):
        # Dynamische Seitenzahl
        has_handwritten = self.config.get("pdf", {}).get("handwritten_fields", False)
        has_chart = len(self.data.get("phases", [])) >= 2
        self.page_count_total = 2 + (1 if has_handwritten else 0) + (1 if has_chart else 0)

        self.draw_page1()
        if has_handwritten:
            self.draw_handwritten_page()
        self.draw_page2()
        self.draw_page3()
        self.output(output_path)'''

    pdf = pdf.replace(old_generate, new_generate)

    # Fix footer page numbering for page2 and page3 to be dynamic
    # Page 2 footer should show correct page number
    old_p2_footer = "        self.draw_footer(2)"
    new_p2_footer = "        self.draw_footer(3 if self.config.get('pdf', {}).get('handwritten_fields', False) else 2)"
    # Only replace the one in draw_page2 (not in draw_handwritten_page)
    # Find the second occurrence
    idx1 = pdf.find(old_p2_footer)
    if idx1 >= 0:
        idx2 = pdf.find(old_p2_footer, idx1 + 1)
        if idx2 >= 0:
            pdf = pdf[:idx2] + new_p2_footer + pdf[idx2 + len(old_p2_footer):]

    old_p3_footer = "        self.draw_footer(3)"
    new_p3_footer = "        self.draw_footer(4 if self.config.get('pdf', {}).get('handwritten_fields', False) else 3)"
    pdf = pdf.replace(old_p3_footer, new_p3_footer)

    with open("/home/belimed/docupi/pdf_generator.py", "w") as f:
        f.write(pdf)
    print("OK: pdf_generator.py updated with handwritten fields")
else:
    print("SKIP: handwritten page already exists")


# ===== 3. SETTINGS HTML =====
with open("/home/belimed/docupi/templates/settings.html", "r") as f:
    html = f.read()

if "handwritten_fields" not in html:
    # Add toggle before the filename section
    old_hr = '<hr class="my-3">\n<h6><i class="bi bi-tag"'
    new_toggle = '''<hr class="my-3">
<h6><i class="bi bi-pencil-square" style="color:var(--docupi-blue)"></i> Notfallkonzept</h6>
<div class="form-check form-switch mb-2">
<input class="form-check-input" type="checkbox" name="handwritten_fields" id="handwrittenFields" value="true"
  {{ 'checked' if config.pdf.handwritten_fields|default(false) }}>
<label class="form-check-label" for="handwrittenFields"><strong>Handschriftliche Felder anzeigen</strong></label>
</div>
<small class="text-muted d-block mb-3"><i class="bi bi-info-circle"></i> Fuegt eine Seite mit leeren Feldern fuer Container/Siebe, Beladungsmuster, Verpackungsart und Freigabe hinzu. Nuetzlich als Backup-Dokumentation bei Systemausfaellen (Notfallkonzept gem. DIN EN ISO 17665).</small>

<hr class="my-3">
<h6><i class="bi bi-tag"'''

    html = html.replace(old_hr, new_toggle)

    with open("/home/belimed/docupi/templates/settings.html", "w") as f:
        f.write(html)
    print("OK: settings.html updated with toggle")
else:
    print("SKIP: settings already has handwritten toggle")


# ===== 4. APP.PY - Save the toggle =====
with open("/home/belimed/docupi/app.py", "r") as f:
    app = f.read()

if "handwritten_fields" not in app:
    app = app.replace(
        '        config["pdf"]["filename_pattern"]',
        '        config["pdf"]["handwritten_fields"] = request.form.get("handwritten_fields") == "true"\n        config["pdf"]["filename_pattern"]'
    )
    with open("/home/belimed/docupi/app.py", "w") as f:
        f.write(app)
    print("OK: app.py saves handwritten_fields")
else:
    print("SKIP: app.py already has handwritten_fields")

print("\n=== ALL DONE ===")
