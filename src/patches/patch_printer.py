#!/usr/bin/env python3
"""Integrate printer support into DocuPi: API endpoints, settings tab, auto-print."""

# ===== 1. APP.PY - Add imports + API endpoints =====
with open("/home/belimed/docupi/app.py", "r") as f:
    app = f.read()

if "print_manager" not in app:
    # Add import
    app = app.replace(
        "from watchdog_manager import",
        "from print_manager import (\n    get_printers, print_pdf, test_print as printer_test_print,\n    get_print_queue, cancel_job, get_status as get_printer_status,\n    load_print_config, save_print_config, auto_print_pdf, is_cups_available\n)\nfrom watchdog_manager import"
    )

    # Add API endpoints before the watchdog endpoint
    printer_api = '''
# --- Printer API ---
@app.route("/api/printers")
def api_printers():
    """List available printers."""
    return jsonify(get_printer_status())

@app.route("/api/print", methods=["POST"])
def api_print():
    """Print a PDF file."""
    d = request.get_json() or {}
    pdf_path = d.get("file_path", "")
    printer = d.get("printer", "")
    copies = d.get("copies", 1)
    all_pages = d.get("all_pages", True)
    if not pdf_path:
        return jsonify({"success": False, "message": "Kein Dateipfad angegeben"})
    ok, msg, job_id = print_pdf(pdf_path, printer, copies, all_pages)
    return jsonify({"success": ok, "message": msg, "job_id": job_id})

@app.route("/api/print/test", methods=["POST"])
def api_print_test():
    """Print test page."""
    d = request.get_json() or {}
    printer = d.get("printer", "")
    ok, msg, job_id = printer_test_print(printer)
    return jsonify({"success": ok, "message": msg, "job_id": job_id})

@app.route("/api/print/queue")
def api_print_queue():
    """Get print queue."""
    return jsonify({"jobs": get_print_queue()})

@app.route("/api/print/cancel", methods=["POST"])
def api_print_cancel():
    """Cancel print job."""
    d = request.get_json() or {}
    job_id = d.get("job_id", 0)
    ok, msg = cancel_job(int(job_id))
    return jsonify({"success": ok, "message": msg})

@app.route("/api/print/config", methods=["GET"])
def api_print_config_get():
    """Get print configuration."""
    return jsonify(load_print_config())

@app.route("/api/print/config", methods=["POST"])
def api_print_config_set():
    """Update print configuration."""
    d = request.get_json() or {}
    config = load_print_config()
    if "auto_print" in d: config["auto_print"] = bool(d["auto_print"])
    if "default_printer" in d: config["default_printer"] = d["default_printer"]
    if "copies" in d: config["copies"] = max(1, min(10, int(d["copies"])))
    if "all_pages" in d: config["all_pages"] = bool(d["all_pages"])
    if "color_mode" in d: config["color_mode"] = d["color_mode"]
    save_print_config(config)
    return jsonify({"success": True, "message": "Druckeinstellungen gespeichert", "config": config})

'''
    marker = '@app.route("/api/watchdog/status")'
    app = app.replace(marker, printer_api + marker)

    with open("/home/belimed/docupi/app.py", "w") as f:
        f.write(app)
    print("OK: app.py printer API added")
else:
    print("SKIP: app.py already has print_manager")


# ===== 2. SERIAL RECEIVER - Add auto-print =====
with open("/home/belimed/docupi/serial_receiver.py", "r") as f:
    sr = f.read()

if "auto_print_pdf" not in sr:
    sr = sr.replace(
        "from storage_manager import copy_pdf_to_usb_instant",
        "from storage_manager import copy_pdf_to_usb_instant\nfrom print_manager import auto_print_pdf"
    )
    # Add auto-print after USB instant copy
    sr = sr.replace(
        """            # Sofort auf USB kopieren falls eingesteckt
            try:
                copy_pdf_to_usb_instant(pdf_path, pdf_filename)
            except Exception as ue:
                logger.debug(f"USB-Sofortkopie: {ue}")""",
        """            # Sofort auf USB kopieren falls eingesteckt
            try:
                copy_pdf_to_usb_instant(pdf_path, pdf_filename)
            except Exception as ue:
                logger.debug(f"USB-Sofortkopie: {ue}")
            # Auto-Print falls aktiviert
            try:
                auto_print_pdf(pdf_path)
            except Exception as pe:
                logger.debug(f"Auto-Print: {pe}")"""
    )
    with open("/home/belimed/docupi/serial_receiver.py", "w") as f:
        f.write(sr)
    print("OK: serial_receiver.py auto-print added")
else:
    print("SKIP: serial_receiver already has auto_print")


# ===== 3. SETTINGS.HTML - Add Drucker tab =====
with open("/home/belimed/docupi/templates/settings.html", "r") as f:
    html = f.read()

if "tabDrucker" not in html:
    # Add tab button
    old_logs_tab = '<li class="nav-item"><a class="nav-link" data-bs-toggle="pill" href="#tabLogs">'
    new_tabs = '<li class="nav-item"><a class="nav-link" data-bs-toggle="pill" href="#tabDrucker"><i class="bi bi-printer"></i> Drucker</a></li>\n  ' + old_logs_tab
    html = html.replace(old_logs_tab, new_tabs)

    # Add tab pane before Logs tab
    drucker_pane = '''
<!-- ============ TAB: DRUCKER ============ -->
<div class="tab-pane fade" id="tabDrucker">
<div class="row g-4">
  <div class="col-md-6">
    <div class="config-section">
      <h5><i class="bi bi-printer" style="color:var(--docupi-blue)"></i> Drucker-Status</h5>
      <div id="printerStatus" class="info-panel mb-3">Lade...</div>
      <div class="d-flex gap-2">
        <button class="btn btn-sm btn-outline-primary" onclick="loadPrinterStatus()"><i class="bi bi-arrow-clockwise"></i> Aktualisieren</button>
        <button class="btn btn-sm btn-outline-secondary" onclick="doPrinterTest()"><i class="bi bi-printer"></i> Testseite drucken</button>
      </div>
    </div>
  </div>
  <div class="col-md-6">
    <div class="config-section">
      <h5><i class="bi bi-gear" style="color:var(--docupi-blue)"></i> Druck-Einstellungen</h5>
      <div class="form-check form-switch mb-3">
        <input class="form-check-input" type="checkbox" id="autoPrint" onchange="savePrintConfig()">
        <label class="form-check-label" for="autoPrint"><strong>Auto-Print bei neuer Charge</strong></label>
        <br><small class="text-muted">Jedes neue Protokoll wird automatisch gedruckt</small>
      </div>
      <div class="mb-3">
        <label class="form-label">Standard-Drucker</label>
        <select class="form-select form-select-sm" id="defaultPrinter" onchange="savePrintConfig()">
          <option value="">Automatisch (erster verfuegbarer)</option>
        </select>
      </div>
      <div class="row">
        <div class="col-6 mb-3">
          <label class="form-label">Kopien</label>
          <input type="number" class="form-control form-control-sm" id="printCopies" value="1" min="1" max="10" onchange="savePrintConfig()">
        </div>
        <div class="col-6 mb-3">
          <label class="form-label">Seiten</label>
          <select class="form-select form-select-sm" id="printPages" onchange="savePrintConfig()">
            <option value="true">Alle Seiten</option>
            <option value="false">Nur Seite 1 (Uebersicht)</option>
          </select>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label">Farbmodus</label>
        <select class="form-select form-select-sm" id="printColor" onchange="savePrintConfig()">
          <option value="auto">Automatisch</option>
          <option value="color">Farbe</option>
          <option value="grayscale">Schwarzweiss</option>
        </select>
      </div>
    </div>
  </div>
  <div class="col-12">
    <div class="config-section">
      <h5><i class="bi bi-list-task" style="color:var(--docupi-blue)"></i> Druckwarteschlange</h5>
      <div id="printQueue">Keine aktiven Druckauftraege</div>
    </div>
  </div>
</div>
</div>

'''
    # Insert before Logs tab pane
    html = html.replace(
        '<!-- ============ TAB: LOGS ============ -->',
        drucker_pane + '<!-- ============ TAB: LOGS ============ -->'
    )

    # Add printer JS before the log functions
    printer_js = '''
// --- Printer ---
function loadPrinterStatus() {
  fetch('/api/printers').then(function(r){return r.json()}).then(function(d) {
    var el = document.getElementById('printerStatus');
    if (!d.cups_available) {
      el.innerHTML = '<span class="text-danger"><i class="bi bi-x-circle"></i> CUPS nicht verfuegbar</span>';
      return;
    }
    if (d.printer_count === 0) {
      el.innerHTML = '<span class="text-warning"><i class="bi bi-exclamation-triangle"></i> Kein Drucker angeschlossen</span><br><small class="text-muted">Schliessen Sie einen USB-Drucker an und klicken Sie auf Aktualisieren.</small>';
    } else {
      var html = '';
      d.printers.forEach(function(p) {
        var badge = p.state === 3 ? 'bg-success' : p.state === 5 ? 'bg-primary' : 'bg-secondary';
        html += '<div class="d-flex justify-content-between align-items-center mb-2">';
        html += '<div><strong>' + p.info + '</strong><br><small class="text-muted">' + p.uri + '</small></div>';
        html += '<span class="badge ' + badge + '">' + p.state_text + '</span>';
        html += '</div>';
      });
      el.innerHTML = html;
    }
    // Update printer dropdown
    var sel = document.getElementById('defaultPrinter');
    var currentVal = sel.value;
    sel.innerHTML = '<option value="">Automatisch (erster verfuegbarer)</option>';
    d.printers.forEach(function(p) {
      var opt = document.createElement('option');
      opt.value = p.name; opt.textContent = p.info;
      if (p.name === d.default_printer) opt.selected = true;
      sel.appendChild(opt);
    });
    // Load config
    document.getElementById('autoPrint').checked = d.auto_print;
    document.getElementById('printCopies').value = d.copies;
    document.getElementById('printPages').value = d.all_pages ? 'true' : 'false';
    document.getElementById('printColor').value = d.color_mode;
    if (d.default_printer) sel.value = d.default_printer;
  }).catch(function(){});
  // Load queue
  fetch('/api/print/queue').then(function(r){return r.json()}).then(function(d) {
    var el = document.getElementById('printQueue');
    if (!d.jobs || d.jobs.length === 0) {
      el.textContent = 'Keine aktiven Druckauftraege';
    } else {
      var html = '<table class="table table-sm table-borderless"><thead><tr><th>Job</th><th>Datei</th><th>Drucker</th><th>Status</th><th></th></tr></thead><tbody>';
      d.jobs.forEach(function(j) {
        html += '<tr><td>#' + j.job_id + '</td><td>' + j.title + '</td><td>' + j.printer + '</td><td>' + j.status + '</td>';
        html += '<td><button class="btn btn-sm btn-outline-danger" onclick="cancelPrintJob(' + j.job_id + ')"><i class="bi bi-x"></i></button></td></tr>';
      });
      html += '</tbody></table>';
      el.innerHTML = html;
    }
  }).catch(function(){});
}

function savePrintConfig() {
  fetch('/api/print/config', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      auto_print: document.getElementById('autoPrint').checked,
      default_printer: document.getElementById('defaultPrinter').value,
      copies: parseInt(document.getElementById('printCopies').value),
      all_pages: document.getElementById('printPages').value === 'true',
      color_mode: document.getElementById('printColor').value,
    })
  }).then(function(r){return r.json()}).then(function(d) {
    showToast('Drucker', d.message, d.success);
  }).catch(function(e) { showToast('Fehler', e.toString(), false); });
}

function doPrinterTest() {
  var printer = document.getElementById('defaultPrinter').value;
  fetch('/api/print/test', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({printer: printer})
  }).then(function(r){return r.json()}).then(function(d) {
    showToast('Testdruck', d.message, d.success);
    setTimeout(loadPrinterStatus, 2000);
  }).catch(function(e) { showToast('Fehler', e.toString(), false); });
}

function cancelPrintJob(jobId) {
  fetch('/api/print/cancel', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({job_id: jobId})
  }).then(function(r){return r.json()}).then(function(d) {
    showToast('Drucker', d.message, d.success);
    loadPrinterStatus();
  }).catch(function(){});
}

// Load printer status when tab shown
document.querySelector('a[href="#tabDrucker"]').addEventListener('shown.bs.tab', function() {
  loadPrinterStatus();
});

'''
    html = html.replace('// --- Logs ---', printer_js + '// --- Logs ---')

    with open("/home/belimed/docupi/templates/settings.html", "w") as f:
        f.write(html)
    print("OK: settings.html Drucker tab added")
else:
    print("SKIP: settings already has Drucker tab")


# ===== 4. SUDOERS - Add CUPS commands =====
import subprocess
result = subprocess.run(["sudo", "grep", "cups", "/etc/sudoers.d/docupi-network"],
                        capture_output=True, text=True)
if "cups" not in result.stdout.lower():
    subprocess.run(
        ["sudo", "bash", "-c",
         'echo "belimed ALL=(ALL) NOPASSWD: /usr/sbin/cupsd, /usr/sbin/cupsctl, /usr/bin/lpadmin" >> /etc/sudoers.d/docupi-network'],
        capture_output=True
    )
    print("OK: sudoers updated for CUPS")
else:
    print("SKIP: sudoers already has CUPS")

print("\n=== ALL DONE ===")
