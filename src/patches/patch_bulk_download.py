#!/usr/bin/env python3
"""Add checkboxes + bulk download to file manager."""

# ===== 1. APP.PY - Add bulk download ZIP endpoint =====
with open("/home/belimed/docupi/app.py", "r") as f:
    app = f.read()

if "/api/storage/download-zip" not in app:
    zip_route = '''
@app.route("/api/storage/download-zip", methods=["POST"])
def api_download_zip():
    """Download multiple files as a single ZIP archive."""
    import zipfile
    import io
    from storage_manager import SD_PDF_DIR, USB_MOUNT_POINT, USB_PDF_SUBDIR

    d = request.get_json() or {}
    pane = d.get("pane", "sd")
    files = d.get("files", [])

    if not files:
        return jsonify({"success": False, "message": "Keine Dateien ausgewaehlt"}), 400

    if pane == "sd":
        base = SD_PDF_DIR
    else:
        base = os.path.join(USB_MOUNT_POINT, USB_PDF_SUBDIR)

    # Create ZIP in memory
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_path in files:
            full_path = os.path.join(base, rel_path)
            # Security check
            real_base = os.path.realpath(base)
            real_path = os.path.realpath(full_path)
            if not real_path.startswith(real_base):
                continue
            if os.path.isfile(real_path):
                zf.write(real_path, os.path.basename(rel_path))

    mem_zip.seek(0)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"DocuPi_Protokolle_{ts}.zip"

    return send_file(
        mem_zip,
        mimetype="application/zip",
        as_attachment=True,
        download_name=filename
    )

'''
    # Insert before the watchdog endpoint
    marker = '# --- Printer API ---'
    if marker in app:
        app = app.replace(marker, zip_route + marker)
    else:
        marker = '@app.route("/api/watchdog/status")'
        app = app.replace(marker, zip_route + marker)

    # Add send_file import if missing
    if "send_file" not in app:
        app = app.replace(
            "from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response",
            "from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response, send_file"
        )

    with open("/home/belimed/docupi/app.py", "w") as f:
        f.write(app)
    print("OK: app.py bulk download ZIP endpoint added")
else:
    print("SKIP: ZIP endpoint already exists")


# ===== 2. FILEMANAGER.HTML - Add checkboxes + bulk download =====
with open("/home/belimed/docupi/templates/filemanager.html", "r") as f:
    html = f.read()

if "selectAll" not in html:
    # 2a. Add checkbox column to table header
    old_header = """var html = '<table><thead><tr>' +
    '<th style="width:30px"></th>' +
    '<th class="' + sc('name')"""
    new_header = """var html = '<table><thead><tr>' +
    '<th style="width:28px"><input type="checkbox" class="form-check-input" onchange="selectAll(\\'' + pane + '\\',this.checked)" title="Alle auswaehlen"></th>' +
    '<th style="width:30px"></th>' +
    '<th class="' + sc('name')"""
    html = html.replace(old_header, new_header)

    # 2b. Add checkbox to file rows
    old_file_row = """html += '<tr data-path="' + esc(file.path) + '" data-type="file" onclick="toggleSelect(this,\\'' + pane + '\\')">' +
      '<td class="fm-icon">' + icon + '</td>'"""
    new_file_row = """html += '<tr data-path="' + esc(file.path) + '" data-type="file">' +
      '<td onclick="event.stopPropagation()"><input type="checkbox" class="form-check-input file-cb" data-pane="' + pane + '" data-path="' + esc(file.path) + '" onchange="toggleCheckbox(this)" title="Auswaehlen"></td>' +
      '<td class="fm-icon" onclick="toggleSelect(this.parentElement,\\'' + pane + '\\')">' + icon + '</td>'"""
    html = html.replace(old_file_row, new_file_row)

    # 2c. Add checkbox to dir rows
    old_dir_row = """html += '<tr data-path="' + esc(dir.path) + '" data-type="dir" onclick="toggleSelect(this,\\'' + pane + '\\')">' +
      '<td class="fm-icon">&#x1F4C1;</td>'"""
    new_dir_row = """html += '<tr data-path="' + esc(dir.path) + '" data-type="dir">' +
      '<td onclick="event.stopPropagation()"><input type="checkbox" class="form-check-input file-cb" data-pane="' + pane + '" data-path="' + esc(dir.path) + '" onchange="toggleCheckbox(this)"></td>' +
      '<td class="fm-icon" onclick="toggleSelect(this.parentElement,\\'' + pane + '\\')">&#x1F4C1;</td>'"""
    html = html.replace(old_dir_row, new_dir_row)

    # 2d. Add download button to both toolbars
    old_sd_toolbar = """<button class="btn btn-outline-primary" onclick="copySelected('sd','usb')" title="Auf USB kopieren"><i class="bi bi-arrow-right"></i> USB</button>
        <button class="btn btn-outline-danger" onclick="deleteSelected('sd')"><i class="bi bi-trash"></i></button>"""
    new_sd_toolbar = """<button class="btn btn-outline-success" onclick="downloadSelected('sd')" title="Ausgewaehlte herunterladen"><i class="bi bi-download"></i> Download</button>
        <button class="btn btn-outline-primary" onclick="copySelected('sd','usb')" title="Auf USB kopieren"><i class="bi bi-arrow-right"></i> USB</button>
        <button class="btn btn-outline-danger" onclick="deleteSelected('sd')"><i class="bi bi-trash"></i></button>"""
    html = html.replace(old_sd_toolbar, new_sd_toolbar)

    old_usb_toolbar = """<button class="btn btn-outline-primary" onclick="copySelected('usb','sd')" title="Auf SD kopieren"><i class="bi bi-arrow-left"></i> SD</button>
        <button class="btn btn-outline-danger" onclick="deleteSelected('usb')"><i class="bi bi-trash"></i></button>"""
    new_usb_toolbar = """<button class="btn btn-outline-success" onclick="downloadSelected('usb')" title="Ausgewaehlte herunterladen"><i class="bi bi-download"></i> Download</button>
        <button class="btn btn-outline-primary" onclick="copySelected('usb','sd')" title="Auf SD kopieren"><i class="bi bi-arrow-left"></i> SD</button>
        <button class="btn btn-outline-danger" onclick="deleteSelected('usb')"><i class="bi bi-trash"></i></button>"""
    html = html.replace(old_usb_toolbar, new_usb_toolbar)

    # 2e. Add JS functions for checkboxes and bulk download
    # Find a good place to insert - before the sortBy function
    old_sort = "function sortBy(pane, col) {"
    new_js = """function selectAll(pane, checked) {
  document.querySelectorAll('.file-cb[data-pane="' + pane + '"]').forEach(function(cb) {
    cb.checked = checked;
    var tr = cb.closest('tr');
    var path = cb.getAttribute('data-path');
    if (checked) {
      state[pane].selected.add(path);
      tr.classList.add('selected');
    } else {
      state[pane].selected.delete(path);
      tr.classList.remove('selected');
    }
  });
  updateSelCount(pane);
}

function toggleCheckbox(cb) {
  var pane = cb.getAttribute('data-pane');
  var path = cb.getAttribute('data-path');
  var tr = cb.closest('tr');
  if (cb.checked) {
    state[pane].selected.add(path);
    tr.classList.add('selected');
  } else {
    state[pane].selected.delete(path);
    tr.classList.remove('selected');
  }
  updateSelCount(pane);
}

function updateSelCount(pane) {
  var count = state[pane].selected.size;
  var badge = document.getElementById(pane + 'SelCount');
  if (badge) {
    badge.textContent = count > 0 ? count + ' ausgewaehlt' : '';
    badge.style.display = count > 0 ? 'inline' : 'none';
  }
}

function downloadSelected(pane) {
  var files = Array.from(state[pane].selected).filter(function(p) {
    // Only files, not directories
    return p.endsWith('.pdf') || p.endsWith('.log') || p.endsWith('.txt');
  });
  if (files.length === 0) {
    alert('Keine Dateien ausgewaehlt. Bitte Checkboxen markieren.');
    return;
  }
  if (files.length === 1) {
    // Single file: direct download
    window.location.href = '/api/storage/file/' + pane + '?path=' + encodeURIComponent(files[0]) + '&download=1';
    return;
  }
  // Multiple files: ZIP download
  fetch('/api/storage/download-zip', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({pane: pane, files: files})
  }).then(function(r) {
    if (!r.ok) throw new Error('Download fehlgeschlagen');
    return r.blob();
  }).then(function(blob) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'DocuPi_Protokolle.zip';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }).catch(function(e) { alert('Download-Fehler: ' + e.message); });
}

function sortBy(pane, col) {"""

    html = html.replace(old_sort, new_js)

    # 2f. Add selection count badge to toolbars
    html = html.replace(
        """<button class="btn btn-outline-success" onclick="downloadSelected('sd')" """,
        """<span class="badge bg-primary ms-auto" id="sdSelCount" style="display:none"></span>
        <button class="btn btn-outline-success" onclick="downloadSelected('sd')" """
    )
    html = html.replace(
        """<button class="btn btn-outline-success" onclick="downloadSelected('usb')" """,
        """<span class="badge bg-primary ms-auto" id="usbSelCount" style="display:none"></span>
        <button class="btn btn-outline-success" onclick="downloadSelected('usb')" """
    )

    # 2g. Add CSS for checkboxes
    old_css = ".fm-list tr.selected{background:#cce5ff}"
    new_css = """.fm-list tr.selected{background:#cce5ff}
.fm-list .form-check-input{margin:0;cursor:pointer}
.fm-list thead .form-check-input{margin-top:2px}"""
    html = html.replace(old_css, new_css)

    with open("/home/belimed/docupi/templates/filemanager.html", "w") as f:
        f.write(html)
    print("OK: filemanager.html checkboxes + bulk download added")
else:
    print("SKIP: filemanager already has selectAll")

print("\n=== ALL DONE ===")
