#!/usr/bin/env python3
"""Overhaul PDF settings: add all configurable customer/machine fields,
update defaults to match real data, clean up obsolete fields."""

# ===== 1. CONFIG: Add new fields with current real values =====
import json

path_cfg = "/home/belimed/docupi/config.py"
with open(path_cfg, "r") as f:
    cfg = f.read()

# Replace entire pdf section with comprehensive fields
old_pdf = '''        "folder_structure": "date",
        "filename_pattern": "{datum}_{zeit}_{geraet}_{charge}",
        "filename_separator": "_",
        "handwritten_fields": false,
        "device_alias": "",
        "notfall_rows": 18,
        "header_text": "DocuPi-3000 Protokoll",
        "device_name": "",
        "font_size": 8,
        "page_format": "A4"'''

# Note: Python needs False not false
new_pdf = '''        "folder_structure": "date",
        "filename_pattern": "{datum}_{zeit}_{geraet}_{charge}",
        "filename_separator": "_",
        "handwritten_fields": False,
        "notfall_rows": 18,
        "font_size": 8,
        "page_format": "A4",
        "kundenname": "Helios Krefeld",
        "abteilung": "AEMP",
        "maschinen_typ": "",
        "maschinen_nr": "",
        "device_alias": "Steri 1",
        "device_name": "",
        "header_text": "",
        "name_corrections": {}'''

cfg = cfg.replace(old_pdf, new_pdf)

with open(path_cfg, "w") as f:
    f.write(cfg)
print("OK: config.py updated with customer fields")


# ===== 2. SETTINGS HTML: Rebuild PDF tab =====
path_html = "/home/belimed/docupi/templates/settings.html"
with open(path_html, "r") as f:
    html = f.read()

# Find and replace the entire PDF tab content
old_tab_start = '<!-- ============ TAB: PDF ============ -->'
old_tab_end = '<!-- ============ TAB: HOTSPOT ============ -->'

idx_start = html.find(old_tab_start)
idx_end = html.find(old_tab_end)

if idx_start >= 0 and idx_end >= 0:
    new_pdf_tab = '''<!-- ============ TAB: PDF ============ -->
<div class="tab-pane fade" id="tabPdf">
<form method="POST" action="/settings">
<!-- Hidden fields for serial/protocol -->
<input type="hidden" name="serial_port" value="{{ config.serial.port }}">
<input type="hidden" name="baudrate" value="{{ config.serial.baudrate }}">
<input type="hidden" name="bytesize" value="{{ config.serial.bytesize }}">
<input type="hidden" name="parity" value="{{ config.serial.parity }}">
<input type="hidden" name="stopbits" value="{{ config.serial.stopbits }}">
<input type="hidden" name="delimiter" value="{{ config.protocol.delimiter }}">
<input type="hidden" name="timeout_seconds" value="{{ config.protocol.timeout_seconds }}">
<input type="hidden" name="custom_delimiter" value="{{ config.protocol.custom_delimiter }}">

<div class="row g-4">
<!-- Linke Spalte: Kunde & Maschine -->
<div class="col-md-6"><div class="config-section">
<h5><i class="bi bi-building" style="color:var(--docupi-blue)"></i> Kunde &amp; Maschine</h5>

<div class="mb-3">
  <label class="form-label fw-bold">Kundenname</label>
  <input type="text" name="kundenname" class="form-control" value="{{ config.pdf.kundenname|default('') }}" placeholder="z.B. Helios Krefeld">
  <small class="text-muted">Wird oben rechts im PDF angezeigt. Ueberschreibt den Wert vom Sterilisator falls gesetzt.</small>
</div>

<div class="mb-3">
  <label class="form-label fw-bold">Abteilung</label>
  <input type="text" name="abteilung" class="form-control" value="{{ config.pdf.abteilung|default('') }}" placeholder="z.B. AEMP, ZSVA">
  <small class="text-muted">Wird neben dem Kundennamen angezeigt.</small>
</div>

<div class="row">
  <div class="col-8 mb-3">
    <label class="form-label fw-bold">Maschinentyp</label>
    <input type="text" name="maschinen_typ" class="form-control" value="{{ config.pdf.maschinen_typ|default('') }}" placeholder="z.B. 9-6-18 HS2 (leer = aus Protokoll)">
    <small class="text-muted">Leer lassen = wird automatisch aus dem Protokoll gelesen.</small>
  </div>
  <div class="col-4 mb-3">
    <label class="form-label fw-bold">Maschinen-Nr.</label>
    <input type="text" name="maschinen_nr" class="form-control" value="{{ config.pdf.maschinen_nr|default('') }}" placeholder="z.B. 27163">
  </div>
</div>

<div class="mb-3">
  <label class="form-label fw-bold">Anzeigename</label>
  <input type="text" name="device_alias" class="form-control" value="{{ config.pdf.device_alias|default('') }}" placeholder="z.B. Steri 1, Autoklav A">
  <small class="text-muted">Frei waehlbarer Name, wird unter dem Maschinentyp im PDF angezeigt.</small>
</div>

</div></div>

<!-- Rechte Spalte: PDF-Ausgabe -->
<div class="col-md-6"><div class="config-section">
<h5><i class="bi bi-file-earmark-pdf" style="color:var(--docupi-blue)"></i> PDF-Ausgabe</h5>

<div class="row">
  <div class="col-6 mb-3">
    <label class="form-label fw-bold">Schriftgroesse</label>
    <select name="font_size" class="form-select">
      {% for s in [6,7,8,9,10] %}<option value="{{ s }}" {% if s == config.pdf.font_size %}selected{% endif %}>{{ s }} pt</option>{% endfor %}
    </select>
  </div>
  <div class="col-6 mb-3">
    <label class="form-label fw-bold">Ordnerstruktur</label>
    <select name="folder_structure" class="form-select">
      <option value="date" {% if config.pdf.folder_structure == 'date' %}selected{% endif %}>Nach Datum (YYYY/MM)</option>
      <option value="device" {% if config.pdf.folder_structure == 'device' %}selected{% endif %}>Nach Geraet</option>
      <option value="flat" {% if config.pdf.folder_structure == 'flat' %}selected{% endif %}>Flach (ein Ordner)</option>
    </select>
  </div>
</div>

<hr class="my-2">
<h6><i class="bi bi-pencil-square" style="color:var(--docupi-blue)"></i> Notfallkonzept</h6>
<div class="form-check form-switch mb-2">
  <input class="form-check-input" type="checkbox" name="handwritten_fields" id="handwrittenFields" value="true"
    {{ 'checked' if config.pdf.handwritten_fields|default(false) }}>
  <label class="form-check-label" for="handwrittenFields"><strong>Handschriftliche Felder anzeigen</strong></label>
</div>
<small class="text-muted d-block mb-2">Zusaetzliche Seite mit leeren Feldern fuer Container/Siebe und Freigabe.</small>
<div class="mb-3">
  <label class="form-label">Anzahl Zeilen</label>
  <input type="number" name="notfall_rows" class="form-control form-control-sm" value="{{ config.pdf.notfall_rows|default(18) }}" min="6" max="30" style="max-width:80px">
  <small class="text-muted">Standard: 18 (passend fuer 18 STE)</small>
</div>

<hr class="my-2">
<h6><i class="bi bi-tag" style="color:var(--docupi-blue)"></i> Dateiname</h6>
<div class="mb-2">
  <label class="form-label">Dateiname-Muster</label>
  <input type="text" name="filename_pattern" id="fnPattern" class="form-control font-monospace"
    value="{{ config.pdf.filename_pattern|default('{datum}_{zeit}_{geraet}_{charge}') }}">
  <small class="text-muted">Bausteine (klicken zum Einfuegen):</small>
  <div class="mt-1 d-flex flex-wrap gap-1" id="fnTokens">
    <span class="badge token-badge" data-token="{datum}" style="cursor:pointer" onclick="insertToken('{datum}')" title="2026-03-19">{datum}</span>
    <span class="badge token-badge" data-token="{zeit}" style="cursor:pointer" onclick="insertToken('{zeit}')" title="143025">{zeit}</span>
    <span class="badge token-badge" data-token="{geraet}" style="cursor:pointer" onclick="insertToken('{geraet}')" title="MST_9-6-18">{geraet}</span>
    <span class="badge token-badge" data-token="{charge}" style="cursor:pointer" onclick="insertToken('{charge}')" title="CH021667">{charge}</span>
    <span class="badge token-badge" data-token="{jahr}" style="cursor:pointer" onclick="insertToken('{jahr}')" title="2026">{jahr}</span>
    <span class="badge token-badge" data-token="{monat}" style="cursor:pointer" onclick="insertToken('{monat}')" title="03">{monat}</span>
    <span class="badge token-badge" data-token="{tag}" style="cursor:pointer" onclick="insertToken('{tag}')" title="19">{tag}</span>
    <span class="badge token-badge" data-token="{stunde}" style="cursor:pointer" onclick="insertToken('{stunde}')" title="14">{stunde}</span>
    <span class="badge token-badge" data-token="{minute}" style="cursor:pointer" onclick="insertToken('{minute}')" title="30">{minute}</span>
  </div>
</div>
<div class="mb-3">
  <label class="form-label">Trennzeichen</label>
  <select name="filename_separator" class="form-select form-select-sm" style="max-width:180px">
    <option value="_" {{ 'selected' if config.pdf.filename_separator|default('_') == '_' }}>Unterstrich ( _ )</option>
    <option value="-" {{ 'selected' if config.pdf.filename_separator|default('_') == '-' }}>Bindestrich ( - )</option>
  </select>
</div>
<div class="info-panel">
  <small><i class="bi bi-eye"></i> <strong>Vorschau:</strong> <span id="fnPreview" class="font-monospace">---</span></small>
</div>

</div></div>
</div><!-- row -->

<div class="info-panel mt-3">
  <small class="text-muted"><i class="bi bi-info-circle"></i> PDFs werden auf der SD-Karte gespeichert und automatisch auf den USB-Stick synchronisiert. Werte die leer gelassen werden, werden automatisch aus dem Sterilisator-Protokoll gelesen.</small>
</div>
<button type="submit" class="btn btn-primary mt-3"><i class="bi bi-check-lg"></i> Speichern &amp; Neustart</button>
</form>
</div>

'''
    html = html[:idx_start] + new_pdf_tab + html[idx_end:]

    with open(path_html, "w") as f:
        f.write(html)
    print("OK: settings.html PDF tab rebuilt")
else:
    print("ERROR: could not find PDF tab markers")


# ===== 3. APP.PY: Update POST handler to save all new fields =====
path_app = "/home/belimed/docupi/app.py"
with open(path_app, "r") as f:
    app = f.read()

# Find and replace the pdf config save block
# Look for where pdf settings are saved
old_save_start = '        config["pdf"]["header_text"]'
old_save_end = '        config["pdf"]["filename_separator"]'

# Find the full block
idx1 = app.find(old_save_start)
idx2 = app.find(old_save_end)
if idx1 >= 0 and idx2 >= 0:
    # Find end of the filename_separator line
    idx2_end = app.find("\n", idx2) + 1

    new_save_block = '''        config["pdf"]["kundenname"] = request.form.get("kundenname", "")
        config["pdf"]["abteilung"] = request.form.get("abteilung", "")
        config["pdf"]["maschinen_typ"] = request.form.get("maschinen_typ", "")
        config["pdf"]["maschinen_nr"] = request.form.get("maschinen_nr", "")
        config["pdf"]["device_alias"] = request.form.get("device_alias", "")
        config["pdf"]["device_name"] = request.form.get("maschinen_typ", "")
        config["pdf"]["header_text"] = request.form.get("kundenname", "")
        config["pdf"]["handwritten_fields"] = request.form.get("handwritten_fields") == "true"
        config["pdf"]["notfall_rows"] = int(request.form.get("notfall_rows", 18))
        config["pdf"]["font_size"] = int(request.form.get("font_size", 8))
        config["pdf"]["folder_structure"] = request.form.get("folder_structure", "date")
        config["pdf"]["filename_pattern"] = request.form.get("filename_pattern", "{datum}_{zeit}_{geraet}_{charge}")
        config["pdf"]["filename_separator"] = request.form.get("filename_separator", "_")
'''
    app = app[:idx1] + new_save_block + app[idx2_end:]

    with open(path_app, "w") as f:
        f.write(app)
    print("OK: app.py save block updated")
else:
    print("WARN: could not find save block, trying alternate")


# ===== 4. PDF GENERATOR + PARSER: Use config overrides =====
path_parser = "/home/belimed/docupi/protocol_parser.py"
with open(path_parser, "r") as f:
    parser = f.read()

# Add config override support at the end of parse_serial_protocol
# After all parsing, allow config to override values
old_return = '    return result'
new_return = '''    return result


def apply_config_overrides(protocol_data, config):
    """Override parsed values with config settings (if set by user)."""
    pdf_cfg = config.get("pdf", {})

    # Kundenname overrides Betreiber
    if pdf_cfg.get("kundenname"):
        protocol_data["betreiber"] = pdf_cfg["kundenname"]

    # Abteilung override
    if pdf_cfg.get("abteilung"):
        protocol_data["abteilung"] = pdf_cfg["abteilung"]

    # Maschinentyp override
    if pdf_cfg.get("maschinen_typ"):
        protocol_data["maschinen_typ"] = pdf_cfg["maschinen_typ"]
        protocol_data["device_name"] = pdf_cfg["maschinen_typ"]

    # Maschinen-Nr override
    if pdf_cfg.get("maschinen_nr"):
        protocol_data["maschinen_nr"] = pdf_cfg["maschinen_nr"]

    return protocol_data'''

parser = parser.replace(old_return, new_return, 1)  # Only replace first occurrence

with open(path_parser, "w") as f:
    f.write(parser)
print("OK: protocol_parser.py - apply_config_overrides added")

# Update pdf_generator to call apply_config_overrides
path_pdf = "/home/belimed/docupi/pdf_generator.py"
with open(path_pdf, "r") as f:
    pdf = f.read()

# Add import
if "apply_config_overrides" not in pdf:
    pdf = pdf.replace(
        "from protocol_parser import parse_serial_protocol",
        "from protocol_parser import parse_serial_protocol, apply_config_overrides"
    )

    # Call it after parsing
    pdf = pdf.replace(
        "    protocol_data = parse_serial_protocol(raw_data, rtc_timestamps=line_ts)",
        "    protocol_data = parse_serial_protocol(raw_data, rtc_timestamps=line_ts)\n    protocol_data = apply_config_overrides(protocol_data, config)"
    )

    with open(path_pdf, "w") as f:
        f.write(pdf)
    print("OK: pdf_generator.py - uses config overrides")

# ===== 5. Verify syntax =====
import py_compile
for f in [path_cfg, path_html, path_app, path_parser, path_pdf]:
    try:
        if f.endswith(".py"):
            py_compile.compile(f, doraise=True)
    except Exception as e:
        print(f"SYNTAX ERROR in {f}: {e}")
        import sys; sys.exit(1)
print("OK: all syntax valid")

print("\n=== ALL DONE ===")
