#!/usr/bin/env python3
"""Final fixes: cycle_start format, cycle_end from last phase, Unterschrift, remove gray labels."""

# ===== 1. PROTOCOL PARSER: Fix cycle_start format + cycle_end from last phase =====
path_parser = "/home/belimed/docupi/protocol_parser.py"
with open(path_parser, "r") as f:
    parser = f.read()

# Fix cycle_start: "19.03.2026 / 07:49" -> "19.03.2026 07:49:00" (with seconds, no slash)
old_start = '''        elif "Programmstart" in stripped:
            m = re.search(r'Programmstart\s*:\s*(.+)', stripped)
            if m:
                result["cycle_start"] = m.group(1).strip()'''

new_start = '''        elif "Programmstart" in stripped:
            m = re.search(r'Programmstart\s*:\s*(.+)', stripped)
            if m:
                raw_start = m.group(1).strip()
                # Clean format: "19.03.2026 / 07:49" -> "19.03.2026 07:49:00"
                raw_start = raw_start.replace(" / ", " ").replace("/ ", " ")
                if len(raw_start.split(" ")) == 2 and ":" in raw_start:
                    date_part, time_part = raw_start.split(" ", 1)
                    if len(time_part) <= 5:  # HH:MM without seconds
                        time_part += ":00"
                    raw_start = date_part + " " + time_part
                result["cycle_start"] = raw_start'''

parser = parser.replace(old_start, new_start)

# Fix cycle_end: calculate from start + LAST PHASE time offset (not duration)
old_end = '''    # --- Cycle end time (calculated from start + duration, NOT RTC) ---
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
        result["cycle_end"] = now.strftime("%d.%m.%Y %H:%M:%S")'''

new_end = '''    # --- Cycle end time (from start + last phase time offset) ---
    now = datetime.now()
    if result["cycle_start"] and phase_lines:
        try:
            cs = result["cycle_start"]
            # Parse start time (now always "dd.mm.yyyy HH:MM:SS")
            start_dt = datetime.strptime(cs.strip(), "%d.%m.%Y %H:%M:%S")
            # Use last phase offset for end time
            last_offset = phase_lines[-1]["time_offset"]
            last_parts = last_offset.split(":")
            last_sec = int(last_parts[0]) * 60 + int(last_parts[1])
            end_dt = start_dt + timedelta(seconds=last_sec)
            result["cycle_end"] = end_dt.strftime("%d.%m.%Y %H:%M:%S")
        except Exception:
            result["cycle_end"] = now.strftime("%d.%m.%Y %H:%M:%S")
    elif not result["cycle_end"]:
        result["cycle_end"] = now.strftime("%d.%m.%Y %H:%M:%S")'''

parser = parser.replace(old_end, new_end)

with open(path_parser, "w") as f:
    f.write(parser)
print("OK: protocol_parser.py - start format + end from last phase")

# ===== 2. PDF GENERATOR: Unterschrift fix + remove gray labels =====
path_pdf = "/home/belimed/docupi/pdf_generator.py"
with open(path_pdf, "r") as f:
    pdf = f.read()

# Fix Freigabe section on Page 1: rename SIGNATURE -> UNTERSCHRIFT, remove short line, remove gray labels
old_freigabe = '''        self.set_xy(235, y_sig)
        self.cell(30, 3, "SIGNATURE")

        y_cb = y_sig + 5
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*BLACK)
        self.set_xy(10, y_cb)
        self.cell(30, 5, d.get("benutzer", "User"))
        self.set_xy(60, y_cb)
        self.cell(20, 5, "freigegeben")

        for label, x_pos in [("ja", 92), ("nein", 115)]:
            self.set_draw_color(100, 100, 100)
            self.rect(x_pos, y_cb + 0.5, 4, 4)
            self.set_xy(x_pos + 5, y_cb)
            self.set_font("Helvetica", "", 7)
            self.cell(20, 5, label)

        self.set_draw_color(150, 150, 150)
        self.line(170, y_cb + 5, 230, y_cb + 5)
        self.line(240, y_cb + 5, 287, y_cb + 5)'''

new_freigabe = '''        self.set_xy(200, y_sig)
        self.cell(50, 3, "UNTERSCHRIFT")

        y_cb = y_sig + 5
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*BLACK)
        self.set_xy(10, y_cb)
        self.cell(30, 5, d.get("benutzer", "User"))
        self.set_xy(60, y_cb)
        self.cell(20, 5, "freigegeben")

        for label, x_pos in [("ja", 92), ("nein", 115)]:
            self.set_draw_color(100, 100, 100)
            self.rect(x_pos, y_cb + 0.5, 4, 4)
            self.set_xy(x_pos + 5, y_cb)
            self.set_font("Helvetica", "", 7)
            self.cell(20, 5, label)

        # Unterschriftslinie (durchgehend)
        self.set_draw_color(150, 150, 150)
        self.line(200, y_cb + 5, 287, y_cb + 5)'''

pdf = pdf.replace(old_freigabe, new_freigabe)

# Remove gray signature labels from Notfallkonzept page
old_sig = '''        # Signature fields
        sig_fields = [("BELADEN DURCH", 10, 60), ("ENTLADEN DURCH", 80, 60),
                      ("FREIGABE DURCH", 150, 55), ("DATUM", 210, 35),
                      ("UNTERSCHRIFT", 250, 37)]
        self.set_font("Helvetica", "", 6)
        self.set_text_color(100, 100, 100)
        for label, x, w in sig_fields:
            self.set_xy(x, y)
            self.cell(w, 3, label)
            self.set_draw_color(150, 150, 150)
            self.line(x, y + 9, x + w, y + 9)'''

new_sig = '''        # Unterschriftslinien (ohne Labels)
        self.set_draw_color(150, 150, 150)
        self.set_font("Helvetica", "", 6)
        self.set_text_color(100, 100, 100)
        self.set_xy(10, y)
        self.cell(30, 3, "DATUM:")
        self.line(35, y + 3, 100, y + 3)
        self.set_xy(110, y)
        self.cell(40, 3, "UNTERSCHRIFT:")
        self.line(155, y + 3, 287, y + 3)'''

pdf = pdf.replace(old_sig, new_sig)

with open(path_pdf, "w") as f:
    f.write(pdf)
print("OK: pdf_generator.py - Unterschrift + labels fix")

# ===== 3. Verify syntax =====
import py_compile
py_compile.compile(path_parser, doraise=True)
py_compile.compile(path_pdf, doraise=True)
print("OK: all syntax valid")
print("\n=== DONE ===")
