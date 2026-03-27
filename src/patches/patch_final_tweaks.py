#!/usr/bin/env python3
"""Final tweaks: fix cycle end, device alias, prominent Nr, remove bedingte Freigabe,
configurable Notfallkonzept rows, remove Verpackungsart/Beladungsmuster."""

# ===== 1. CONFIG: Add device_alias + notfall_rows =====
with open("/home/belimed/docupi/config.py", "r") as f:
    cfg = f.read()

if "device_alias" not in cfg:
    cfg = cfg.replace(
        '"handwritten_fields": False,',
        '"handwritten_fields": False,\n        "device_alias": "",\n        "notfall_rows": 18,'
    )
    with open("/home/belimed/docupi/config.py", "w") as f:
        f.write(cfg)
    print("OK: config.py - device_alias + notfall_rows added")

# ===== 2. APP.PY: Save new settings =====
with open("/home/belimed/docupi/app.py", "r") as f:
    app = f.read()

if "device_alias" not in app:
    app = app.replace(
        '        config["pdf"]["handwritten_fields"] = request.form.get("handwritten_fields") == "true"',
        '        config["pdf"]["handwritten_fields"] = request.form.get("handwritten_fields") == "true"\n        config["pdf"]["device_alias"] = request.form.get("device_alias", "")\n        config["pdf"]["notfall_rows"] = int(request.form.get("notfall_rows", 18))'
    )
    with open("/home/belimed/docupi/app.py", "w") as f:
        f.write(app)
    print("OK: app.py - saves device_alias + notfall_rows")

# ===== 3. SETTINGS.HTML: Add device alias field + notfall rows =====
with open("/home/belimed/docupi/templates/settings.html", "r") as f:
    html = f.read()

# Add device alias field after Geraetebezeichnung
if "device_alias" not in html:
    old_font = '<div class="row"><div class="col-6 mb-3"><label class="form-label">Schriftgroesse</label>'
    new_alias = '''<div class="mb-3"><label class="form-label">Anzeigename (z.B. "Steri 1")</label><input type="text" name="device_alias" class="form-control" value="{{ config.pdf.device_alias|default('') }}" placeholder="z.B. Steri 1, Autoklav A"></div>
<div class="row"><div class="col-6 mb-3"><label class="form-label">Schriftgroesse</label>'''
    html = html.replace(old_font, new_alias)

# Add notfall_rows setting after handwritten toggle
if "notfall_rows" not in html:
    old_notfall_hint = 'Nuetzlich als Backup-Dokumentation bei Systemausfaellen (Notfallkonzept gem. DIN EN ISO 17665).</small>'
    new_notfall = '''Nuetzlich als Backup-Dokumentation bei Systemausfaellen (Notfallkonzept gem. DIN EN ISO 17665).</small>
<div class="row mt-2"><div class="col-4">
<label class="form-label">Anzahl Zeilen (Container/Siebe)</label>
<input type="number" name="notfall_rows" class="form-control form-control-sm" value="{{ config.pdf.notfall_rows|default(18) }}" min="6" max="30" style="max-width:100px">
<small class="text-muted">Standard: 18 (passend fuer 18 STE)</small>
</div></div>'''
    html = html.replace(old_notfall_hint, new_notfall)

with open("/home/belimed/docupi/templates/settings.html", "w") as f:
    f.write(html)
print("OK: settings.html - device_alias + notfall_rows fields")

# ===== 4. PDF GENERATOR: All the fixes =====
with open("/home/belimed/docupi/pdf_generator.py", "r") as f:
    pdf = f.read()

# 4a. Fix Zyklus Ende: calculate from start + duration, not RTC
old_cycle_end = '''    if not result["cycle_end"]:
        result["cycle_end"] = now.strftime("%d.%m.%Y %H:%M:%S")'''
new_cycle_end = '''    # Calculate cycle_end from cycle_start + duration
    if result["cycle_start"] and result["cycle_duration"]:
        try:
            cs = result["cycle_start"]
            if "/" in cs:
                start_dt = datetime.strptime(cs.strip(), "%d.%m.%Y / %H:%M")
            else:
                start_dt = datetime.strptime(cs.strip(), "%d.%m.%Y %H:%M:%S")
            dur_parts = result["cycle_duration"].split(":")
            dur_sec = int(dur_parts[0]) * 3600 + int(dur_parts[1]) * 60 + int(dur_parts[2])
            end_dt = start_dt + timedelta(seconds=dur_sec)
            result["cycle_end"] = end_dt.strftime("%d.%m.%Y %H:%M:%S")
        except:
            if not result["cycle_end"]:
                result["cycle_end"] = now.strftime("%d.%m.%Y %H:%M:%S")
    elif not result["cycle_end"]:
        result["cycle_end"] = now.strftime("%d.%m.%Y %H:%M:%S")'''

# This is in protocol_parser.py, not pdf_generator.py - fix it there
print("NOTE: cycle_end fix goes into protocol_parser.py")

# 4b. Add device alias to header
old_device_header = '''        device = d.get("maschinen_typ") or self.config.get("pdf", {}).get("device_name", "Sterilisator")
        self.cell(60, 12, device, ln=False)'''
new_device_header = '''        device = d.get("maschinen_typ") or self.config.get("pdf", {}).get("device_name", "Sterilisator")
        alias = self.config.get("pdf", {}).get("device_alias", "")
        nr = d.get("maschinen_nr", "")
        # Device name with Nr prominent
        display = device
        if nr:
            display = f"{device}  |  Nr. {nr}"
        self.cell(65, 7, display, ln=False)
        # Alias underneath (e.g. "Steri 1")
        if alias:
            self.set_xy(10, 14)
            self.set_font("Helvetica", "I", 9)
            self.set_text_color(100, 100, 100)
            self.cell(65, 5, alias)'''
pdf = pdf.replace(old_device_header, new_device_header)

# 4c. Remove "bedingte Freigabe" from Seite 1
old_freigabe = '''        for label, x_pos in [("ja", 92), ("nein", 110), ("bedingte Freigabe", 130)]:'''
new_freigabe = '''        for label, x_pos in [("ja", 92), ("nein", 115)]:'''
pdf = pdf.replace(old_freigabe, new_freigabe)

# 4d. Rewrite Notfallkonzept page: configurable rows, no Verpackungsart/Beladungsmuster
old_handwritten = '''    def draw_handwritten_page(self):
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

        self.draw_footer(self.page_count_total)'''

new_handwritten = '''    def draw_handwritten_page(self):
        """Seite mit leeren Feldern fuer handschriftliche Container/Sieb-Dokumentation."""
        self.add_page()
        self.draw_header()

        num_rows = self.config.get("pdf", {}).get("notfall_rows", 18)
        y = 32

        # Title bar
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
        self.cell(277, 4, "Bitte leserlich ausfuellen. Backup-Dokumentation bei Ausfall des Hauptsystems.")
        y += 7

        # Container/Siebe Tabelle - full width, simple columns
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(31, 78, 121)
        self.set_xy(10, y)
        self.cell(200, 5, "STERILISIERTE CONTAINER / SIEBE / INSTRUMENTE")
        y += 6

        col_w = [10, 90, 30, 40, 40, 67]
        headers = ["Nr.", "Container / Sieb / Instrument", "Menge", "SIE-Nr.", "Indikator OK", "Bemerkung"]
        self.set_fill_color(230, 235, 240)
        self.set_font("Helvetica", "B", 6)
        self.set_text_color(80, 80, 80)
        self.set_draw_color(180, 180, 180)
        self.set_xy(10, y)
        for i, h in enumerate(headers):
            self.cell(col_w[i], 5, h, border=1, fill=True, align="C")
        y += 5

        # Dynamic row height based on count
        available_h = 140 - y + 32  # Space before Freigabe
        row_h = min(7, max(4.5, available_h / num_rows))

        self.set_font("Helvetica", "", 6)
        for row in range(num_rows):
            self.set_xy(10, y)
            self.set_text_color(180, 180, 180)
            self.cell(col_w[0], row_h, str(row + 1), border=1, align="C")
            for i in range(1, len(col_w)):
                self.cell(col_w[i], row_h, "", border=1)
            y += row_h

        y += 4

        # Freigabe - simplified (nur ja/nein)
        self.set_draw_color(180, 180, 180)
        self.line(10, y, 287, y)
        y += 3
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(31, 78, 121)
        self.set_xy(10, y)
        self.cell(130, 5, "STERILGUT-FREIGABE")
        y += 7

        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "", 8)
        for label, xp in [("Freigegeben", 10), ("Nicht freigegeben", 60)]:
            self.set_draw_color(80, 80, 80)
            self.rect(xp, y + 0.5, 4, 4)
            self.set_xy(xp + 6, y)
            self.cell(45, 5, label)

        # Bemerkung line
        self.set_font("Helvetica", "", 6)
        self.set_text_color(100, 100, 100)
        self.set_xy(140, y)
        self.cell(30, 4, "BEMERKUNGEN:")
        self.set_draw_color(180, 180, 180)
        self.line(175, y + 4, 287, y + 4)
        y += 8

        # Signature fields
        sig_fields = [("BELADEN DURCH", 10, 60), ("ENTLADEN DURCH", 80, 60),
                      ("FREIGABE DURCH", 150, 55), ("DATUM", 210, 35),
                      ("UNTERSCHRIFT", 250, 37)]
        self.set_font("Helvetica", "", 6)
        self.set_text_color(100, 100, 100)
        for label, x, w in sig_fields:
            self.set_xy(x, y)
            self.cell(w, 3, label)
            self.set_draw_color(150, 150, 150)
            self.line(x, y + 9, x + w, y + 9)

        self.draw_footer(self.page_count_total)'''

pdf = pdf.replace(old_handwritten, new_handwritten)

with open("/home/belimed/docupi/pdf_generator.py", "w") as f:
    f.write(pdf)
print("OK: pdf_generator.py - all display fixes applied")

# ===== 5. PROTOCOL_PARSER: Fix cycle_end calculation =====
with open("/home/belimed/docupi/protocol_parser.py", "r") as f:
    parser = f.read()

old_end = '''    # --- Cycle end time ---
    now = datetime.now()
    if not result["cycle_end"]:
        result["cycle_end"] = now.strftime("%d.%m.%Y %H:%M:%S")'''

new_end = '''    # --- Cycle end time (calculated from start + duration, NOT RTC) ---
    now = datetime.now()
    if result["cycle_start"] and result["cycle_duration"]:
        try:
            cs = result["cycle_start"]
            if "/" in cs:
                start_dt = datetime.strptime(cs.strip(), "%d.%m.%Y / %H:%M")
            else:
                start_dt = datetime.strptime(cs.strip(), "%d.%m.%Y %H:%M:%S")
            dur_parts = result["cycle_duration"].split(":")
            dur_sec = int(dur_parts[0]) * 3600 + int(dur_parts[1]) * 60 + int(dur_parts[2])
            end_dt = start_dt + timedelta(seconds=dur_sec)
            result["cycle_end"] = end_dt.strftime("%d.%m.%Y %H:%M:%S")
        except Exception:
            result["cycle_end"] = now.strftime("%d.%m.%Y %H:%M:%S")
    elif not result["cycle_end"]:
        result["cycle_end"] = now.strftime("%d.%m.%Y %H:%M:%S")
    # Store RTC time separately for internal logging
    result["rtc_end_time"] = now.strftime("%d.%m.%Y %H:%M:%S")'''

parser = parser.replace(old_end, new_end)

with open("/home/belimed/docupi/protocol_parser.py", "w") as f:
    f.write(parser)
print("OK: protocol_parser.py - cycle_end from start+duration, RTC logged separately")

print("\n=== ALL DONE ===")
