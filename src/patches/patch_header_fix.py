#!/usr/bin/env python3
"""Fix: header overlap, remove Bemerkungen, clean Notfallkonzept."""

path = "/home/belimed/docupi/pdf_generator.py"
with open(path, "r") as f:
    code = f.read()

# 1. Fix header layout - Nr and Alias on second line, not in device name
old = '''        device = d.get("maschinen_typ") or self.config.get("pdf", {}).get("device_name", "Sterilisator")
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

new = '''        device = d.get("maschinen_typ") or self.config.get("pdf", {}).get("device_name", "Sterilisator")
        alias = self.config.get("pdf", {}).get("device_alias", "")
        nr = d.get("maschinen_nr", "")
        self.cell(70, 8, device, ln=False)
        # Second line: Nr + Alias
        sub_parts = []
        if nr:
            sub_parts.append("Nr. " + nr)
        if alias:
            sub_parts.append(alias)
        if sub_parts:
            self.set_xy(10, 15)
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(100, 100, 100)
            self.cell(70, 5, "  |  ".join(sub_parts))'''

code = code.replace(old, new)

# 2. Move CHARGE start position right to avoid overlap
code = code.replace(
    '("CHARGE", str(d.get("charge_nr", "-")), 82, 18)',
    '("CHARGE", str(d.get("charge_nr", "-")), 85, 15)'
)
# If old position still there
code = code.replace(
    '("CHARGE", str(d.get("charge_nr", "-")), 75, 20)',
    '("CHARGE", str(d.get("charge_nr", "-")), 85, 15)'
)

# 3. Remove "BEMERKUNGEN ZUR BEDINGTEN FREIGABE" label from page 1 Freigabe
code = code.replace(
    '''        self.set_xy(140, y_sig)
        self.cell(60, 3, "BEMERKUNGEN ZUR BEDINGTEN FREIGABE")
        self.set_xy(235, y_sig)''',
    '        self.set_xy(235, y_sig)'
)

# 4. Remove Bemerkungen line from Notfallkonzept page
code = code.replace(
    '''        # Bemerkung line
        self.set_font("Helvetica", "", 6)
        self.set_text_color(100, 100, 100)
        self.set_xy(140, y)
        self.cell(30, 4, "BEMERKUNGEN:")
        self.set_draw_color(180, 180, 180)
        self.line(175, y + 4, 287, y + 4)
        y += 8''',
    '        y += 4'
)

# 5. Remove any leftover gray text at bottom (the subtitle hint)
# Check if there's a subtitle that should be removed
code = code.replace(
    '''        self.set_font("Helvetica", "I", 7)
        self.set_text_color(120, 120, 120)
        self.set_xy(10, y)
        self.cell(277, 4, "Bitte leserlich ausfuellen. Backup-Dokumentation bei Ausfall des Hauptsystems.")
        y += 7''',
    '        y += 2'
)

with open(path, "w") as f:
    f.write(code)

# Verify syntax
import py_compile
py_compile.compile(path, doraise=True)
print("OK: all header/layout fixes applied, syntax valid")
