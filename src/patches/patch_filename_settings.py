#!/usr/bin/env python3
"""Add configurable filename pattern to PDF settings tab + backend."""

# ===================================================================
# 1. Update config.py - add filename_pattern default
# ===================================================================
with open("/home/belimed/docupi/config.py", "r") as f:
    cfg = f.read()

if "filename_pattern" not in cfg:
    cfg = cfg.replace(
        '"folder_structure": "date",',
        '"folder_structure": "date",\n        "filename_pattern": "{datum}_{zeit}_{geraet}_{charge}",\n        "filename_separator": "_",'
    )
    with open("/home/belimed/docupi/config.py", "w") as f:
        f.write(cfg)
    print("OK: config.py updated")
else:
    print("SKIP: config already has filename_pattern")


# ===================================================================
# 2. Update pdf_generator.py - use configurable pattern
# ===================================================================
with open("/home/belimed/docupi/pdf_generator.py", "r") as f:
    pdf = f.read()

old_build = '''def build_filename(protocol_id, timestamp, config, charge_nr=""):
    date_str = timestamp.strftime("%Y-%m-%d")
    time_str = timestamp.strftime("%H%M%S")
    device = config["pdf"]["device_name"].replace(" ", "_").replace("/", "-")
    # Chargennummer im Dateinamen: CH00042 oder Fallback auf Protocol-ID
    if charge_nr and charge_nr != str(protocol_id):
        charge_tag = f"CH{charge_nr}"
    else:
        charge_tag = f"CH{protocol_id:05d}"
    return f"{date_str}_{time_str}_{device}_{charge_tag}.pdf"'''

new_build = '''def build_filename(protocol_id, timestamp, config, charge_nr=""):
    """Build PDF filename from configurable pattern.

    Available tokens:
      {datum}    -> 2026-03-18
      {zeit}     -> 143025
      {geraet}   -> MST_9-6-6
      {charge}   -> CH00042
      {jahr}     -> 2026
      {monat}    -> 03
      {tag}      -> 18
      {stunde}   -> 14
      {minute}   -> 30
      {id}       -> 00042 (protocol ID)
    """
    device = config["pdf"]["device_name"].replace(" ", "_").replace("/", "-")

    if charge_nr and charge_nr != str(protocol_id):
        charge_tag = f"CH{charge_nr}"
    else:
        charge_tag = f"CH{protocol_id:05d}"

    # Token mapping
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
        "id": f"{protocol_id:05d}",
    }

    pattern = config["pdf"].get("filename_pattern", "{datum}_{zeit}_{geraet}_{charge}")
    sep = config["pdf"].get("filename_separator", "_")

    # Replace tokens
    name = pattern
    for key, val in tokens.items():
        name = name.replace("{" + key + "}", val)

    # Clean up: replace spaces, ensure no double separators
    name = name.replace(" ", sep)
    while sep + sep in name:
        name = name.replace(sep + sep, sep)
    name = name.strip(sep)

    return f"{name}.pdf"'''

pdf = pdf.replace(old_build, new_build)

with open("/home/belimed/docupi/pdf_generator.py", "w") as f:
    f.write(pdf)
print("OK: pdf_generator.py build_filename updated")


# ===================================================================
# 3. Update settings.html - add filename pattern config to PDF tab
# ===================================================================
with open("/home/belimed/docupi/templates/settings.html", "r") as f:
    html = f.read()

# Add filename pattern section before the info-panel in PDF tab
old_info = '''<div class="info-panel mt-3">
<small class="text-muted"><i class="bi bi-info-circle"></i> PDFs werden auf der SD-Karte gespeichert und automatisch auf den USB-Stick synchronisiert (konfigurierbar im Datei-Manager).</small>
</div>
<button type="submit" class="btn btn-primary mt-3"><i class="bi bi-check-lg"></i> Speichern &amp; Neustart</button>'''

new_section = '''<hr class="my-3">
<h6><i class="bi bi-tag" style="color:var(--docupi-blue)"></i> Dateiname</h6>
<div class="mb-2"><label class="form-label">Dateiname-Muster</label>
<div class="input-group">
<input type="text" name="filename_pattern" id="fnPattern" class="form-control font-monospace"
  value="{{ config.pdf.filename_pattern | default('{datum}_{zeit}_{geraet}_{charge}') }}">
</div>
<small class="text-muted">Verfuegbare Bausteine (klicken zum Einfuegen):</small>
<div class="mt-1 d-flex flex-wrap gap-1" id="fnTokens">
<span class="badge bg-primary" style="cursor:pointer" onclick="insertToken('{datum}')" title="2026-03-18">{datum}</span>
<span class="badge bg-primary" style="cursor:pointer" onclick="insertToken('{zeit}')" title="143025">{zeit}</span>
<span class="badge bg-primary" style="cursor:pointer" onclick="insertToken('{geraet}')" title="MST_9-6-6">{geraet}</span>
<span class="badge bg-primary" style="cursor:pointer" onclick="insertToken('{charge}')" title="CH00042">{charge}</span>
<span class="badge bg-secondary" style="cursor:pointer" onclick="insertToken('{jahr}')" title="2026">{jahr}</span>
<span class="badge bg-secondary" style="cursor:pointer" onclick="insertToken('{monat}')" title="03">{monat}</span>
<span class="badge bg-secondary" style="cursor:pointer" onclick="insertToken('{tag}')" title="18">{tag}</span>
<span class="badge bg-secondary" style="cursor:pointer" onclick="insertToken('{stunde}')" title="14">{stunde}</span>
<span class="badge bg-secondary" style="cursor:pointer" onclick="insertToken('{minute}')" title="30">{minute}</span>
<span class="badge bg-secondary" style="cursor:pointer" onclick="insertToken('{id}')" title="00042">{id}</span>
</div></div>
<div class="mb-3"><label class="form-label">Trennzeichen</label>
<select name="filename_separator" class="form-select" style="max-width:200px">
<option value="_" {{ 'selected' if config.pdf.filename_separator|default('_') == '_' }}>Unterstrich ( _ )</option>
<option value="-" {{ 'selected' if config.pdf.filename_separator|default('_') == '-' }}>Bindestrich ( - )</option>
</select></div>
<div class="info-panel">
<small><i class="bi bi-eye"></i> <strong>Vorschau:</strong> <span id="fnPreview" class="font-monospace">---</span></small>
</div>

<div class="info-panel mt-3">
<small class="text-muted"><i class="bi bi-info-circle"></i> PDFs werden auf der SD-Karte gespeichert und automatisch auf den USB-Stick synchronisiert (konfigurierbar im Datei-Manager).</small>
</div>
<button type="submit" class="btn btn-primary mt-3"><i class="bi bi-check-lg"></i> Speichern &amp; Neustart</button>'''

html = html.replace(old_info, new_section)

# Add JS for token insertion and preview (before the closing script or loadUsbStatus)
old_usb_js = "// --- USB Format ---"
fn_js = """// --- Filename Pattern ---
function insertToken(token) {
  var inp = document.getElementById('fnPattern');
  var pos = inp.selectionStart || inp.value.length;
  var val = inp.value;
  var sep = document.querySelector('select[name="filename_separator"]').value;
  // Add separator if needed
  if (pos > 0 && val[pos-1] !== sep && val[pos-1] !== '{') {
    token = sep + token;
  }
  inp.value = val.substring(0, pos) + token + val.substring(pos);
  inp.focus();
  updateFnPreview();
}

function updateFnPreview() {
  var pattern = document.getElementById('fnPattern').value;
  var sep = document.querySelector('select[name="filename_separator"]').value;
  var now = new Date();
  var pad = function(n) { return n < 10 ? '0' + n : '' + n; };
  var tokens = {
    '{datum}': now.getFullYear() + '-' + pad(now.getMonth()+1) + '-' + pad(now.getDate()),
    '{zeit}': pad(now.getHours()) + pad(now.getMinutes()) + pad(now.getSeconds()),
    '{geraet}': (document.querySelector('input[name="device_name"]').value || 'Geraet').replace(/ /g, sep).replace(/\\//g, '-'),
    '{charge}': 'CH00042',
    '{jahr}': '' + now.getFullYear(),
    '{monat}': pad(now.getMonth()+1),
    '{tag}': pad(now.getDate()),
    '{stunde}': pad(now.getHours()),
    '{minute}': pad(now.getMinutes()),
    '{id}': '00042'
  };
  var name = pattern;
  for (var k in tokens) { name = name.split(k).join(tokens[k]); }
  name = name.replace(/ /g, sep);
  document.getElementById('fnPreview').textContent = name + '.pdf';
}

// Update preview on any change
document.getElementById('fnPattern').addEventListener('input', updateFnPreview);
document.querySelector('select[name="filename_separator"]').addEventListener('change', updateFnPreview);
document.querySelector('input[name="device_name"]').addEventListener('input', updateFnPreview);
setTimeout(updateFnPreview, 500);

// --- USB Format ---"""

html = html.replace(old_usb_js, fn_js)

with open("/home/belimed/docupi/templates/settings.html", "w") as f:
    f.write(html)
print("OK: settings.html filename pattern UI added")


# ===================================================================
# 4. Update app.py POST /settings to save filename_pattern
# ===================================================================
with open("/home/belimed/docupi/app.py", "r") as f:
    app = f.read()

# Find where settings POST saves pdf config and add the new fields
if "filename_pattern" not in app:
    # The settings POST handler saves config - find where pdf config is set
    # Look for where device_name is saved
    old_save = 'config["pdf"]["device_name"] = request.form.get("device_name"'
    if old_save in app:
        new_save = old_save
        # Add after the next line that saves a pdf setting
        idx = app.find(old_save)
        # Find end of that line
        end_idx = app.find("\n", idx)
        # Insert after
        insert = '\n    config["pdf"]["filename_pattern"] = request.form.get("filename_pattern", "{datum}_{zeit}_{geraet}_{charge}")\n    config["pdf"]["filename_separator"] = request.form.get("filename_separator", "_")'
        app = app[:end_idx] + insert + app[end_idx:]
        with open("/home/belimed/docupi/app.py", "w") as f:
            f.write(app)
        print("OK: app.py saves filename_pattern")
    else:
        # Try alternate approach - find settings POST
        print("INFO: Could not find device_name save line, checking POST handler")
        # Search for where form data is saved to config
        import re
        m = re.search(r'config\["pdf"\]\["folder_structure"\]\s*=', app)
        if m:
            idx = app.find("\n", m.end())
            insert = '\n    config["pdf"]["filename_pattern"] = request.form.get("filename_pattern", "{datum}_{zeit}_{geraet}_{charge}")\n    config["pdf"]["filename_separator"] = request.form.get("filename_separator", "_")'
            app = app[:idx] + insert + app[idx:]
            with open("/home/belimed/docupi/app.py", "w") as f:
                f.write(app)
            print("OK: app.py saves filename_pattern (via folder_structure)")
        else:
            print("WARN: Could not find where to inject filename_pattern save")
else:
    print("SKIP: app.py already has filename_pattern")

print("\n=== ALL DONE ===")
