"""
DocuPi-3000 Print Manager
CUPS-basierter USB-Drucker-Support mit IPP Everywhere (driverless).
- Drucker erkennen und verwalten
- PDFs drucken (manuell + Auto-Print)
- Druckstatus abfragen
"""

import logging
import os
import re
import subprocess
import threading
import time

logger = logging.getLogger("docupi.print")

# State
_cups_available = False
_conn = None
_auto_print_enabled = False
_model_cache = {}  # {device_uri: (model_str, fetched_at_ts)}
_MODEL_CACHE_TTL = 300  # 5 Minuten
_default_printer = ""
_print_copies = 1
_print_all_pages = True

PRINT_CONFIG_FILE = "/home/docucontrol/docupi/data/print_config.json"

DEFAULT_PRINT_CONFIG = {
    "auto_print": False,
    "default_printer": "",
    "copies": 1,
    "all_pages": True,  # True = all, False = page 1 only
    "color_mode": "auto",  # auto, color, grayscale
    "connection_type": "usb",  # usb oder network
    "network_host": "",  # IP/Hostname des Netzwerkdruckers
}

_HOST_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9.\-]*$')


def _get_conn():
    """Get or create CUPS connection."""
    global _conn, _cups_available
    try:
        import cups
        if _conn is None:
            _conn = cups.Connection()
        _cups_available = True
        return _conn
    except ImportError:
        logger.warning("pycups nicht installiert")
        _cups_available = False
        return None
    except Exception as e:
        logger.warning(f"CUPS Verbindung fehlgeschlagen: {e}")
        _cups_available = False
        _conn = None
        return None


def load_print_config():
    """Load print configuration."""
    import json
    if os.path.exists(PRINT_CONFIG_FILE):
        try:
            with open(PRINT_CONFIG_FILE, "r") as f:
                saved = json.load(f)
                config = dict(DEFAULT_PRINT_CONFIG)
                config.update(saved)
                return config
        except:
            pass
    return dict(DEFAULT_PRINT_CONFIG)


def save_print_config(config):
    """Save print configuration."""
    import json
    os.makedirs(os.path.dirname(PRINT_CONFIG_FILE), exist_ok=True)
    with open(PRINT_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def is_cups_available():
    """Check if CUPS is available."""
    conn = _get_conn()
    return conn is not None


def get_printers():
    """Get list of available printers with details."""
    conn = _get_conn()
    if not conn:
        return []

    try:
        printers = conn.getPrinters()
        result = []
        default = conn.getDefault()

        config = load_print_config()
        is_network = config.get("connection_type") == "network"

        usb_connected = is_usb_printer_present()
        usb_model = get_usb_printer_model() if usb_connected else ""

        for name, attrs in printers.items():
            state = attrs.get("printer-state", 0)
            state_map = {3: "bereit", 4: "druckt", 5: "gestoppt"}
            state_text = state_map.get(state, f"unbekannt ({state})")

            device_uri = attrs.get("device-uri", "")
            # USB-Anschluss: physische Praesenz (sysfs) entscheidet, da CUPS
            # einen einmal eingerichteten USB-Drucker auch nach dem Ausstecken
            # noch als "bereit" melden kann. Netzwerkdrucker haben keine
            # sysfs-Praesenz - dort ist ein nicht gestoppter CUPS-Status
            # (state != 5) das einzig verfuegbare Signal.
            connected = usb_connected if not is_network else state != 5
            model = (usb_model or attrs.get("printer-info", name)) if connected else ""

            result.append({
                "name": name,
                "info": attrs.get("printer-info", name),
                "model": model,
                "connected": connected,
                "location": attrs.get("printer-location", ""),
                "uri": device_uri,
                "state": state,
                "state_text": state_text,
                "is_default": name == default,
                "accepting": attrs.get("printer-is-accepting-jobs", False),
                "color": attrs.get("color-supported", False),
            })

        return result
    except Exception as e:
        logger.error(f"Drucker-Abfrage fehlgeschlagen: {e}")
        return []


def get_real_printer_model(device_uri):
    """Query the real printer model name directly via ipptool (cached, TTL 5 min)."""
    now = time.time()
    if device_uri in _model_cache:
        model, ts = _model_cache[device_uri]
        if now - ts < _MODEL_CACHE_TTL:
            return model
    try:
        result = subprocess.run(
            ['ipptool', '-tv', device_uri,
             '/usr/share/cups/ipptool/get-printer-attributes.test'],
            capture_output=True, text=True, timeout=4
        )
        match = re.search(r'printer-make-and-model \([^)]+\) = (.+)', result.stdout)
        model = match.group(1).strip() if match else ''
    except Exception:
        model = ''
    _model_cache[device_uri] = (model, now)
    return model



def is_usb_printer_present():
    """Return True if any USB device with printer interface class (0x07) is physically connected."""
    try:
        base = '/sys/bus/usb/devices'
        for dev in os.listdir(base):
            dev_path = os.path.join(base, dev)
            if not os.path.isdir(dev_path):
                continue
            for entry in os.listdir(dev_path):
                iface_cls = os.path.join(dev_path, entry, 'bInterfaceClass')
                if os.path.exists(iface_cls):
                    with open(iface_cls) as f:
                        if f.read().strip() == '07':
                            return True
        return False
    except Exception:
        return False


def get_usb_printer_model():
    """Read manufacturer + product name of first USB printer from sysfs device descriptors."""
    try:
        base = '/sys/bus/usb/devices'
        for dev in sorted(os.listdir(base)):
            dev_path = os.path.join(base, dev)
            if not os.path.isdir(dev_path):
                continue
            for entry in os.listdir(dev_path):
                iface_cls = os.path.join(dev_path, entry, 'bInterfaceClass')
                if os.path.exists(iface_cls):
                    with open(iface_cls) as f:
                        if f.read().strip() == '07':
                            mfr_f = os.path.join(dev_path, 'manufacturer')
                            prod_f = os.path.join(dev_path, 'product')
                            mfr = open(mfr_f).read().strip() if os.path.exists(mfr_f) else ''
                            prod = open(prod_f).read().strip() if os.path.exists(prod_f) else ''
                            return f'{mfr} {prod}'.strip() or 'USB Drucker'
        return ''
    except Exception:
        return ''


def get_default_printer():
    """Get default printer name."""
    conn = _get_conn()
    if not conn:
        return None
    try:
        return conn.getDefault()
    except:
        return None


def print_pdf(pdf_path, printer_name=None, copies=1, all_pages=True, color_mode="auto"):
    """Print a PDF file.

    Returns: (success, message, job_id)
    """
    conn = _get_conn()
    if not conn:
        return False, "CUPS nicht verfuegbar", None

    if not os.path.isfile(pdf_path):
        return False, f"Datei nicht gefunden: {pdf_path}", None

    # Determine printer
    if not printer_name:
        config = load_print_config()
        printer_name = config.get("default_printer", "")

    if not printer_name:
        printer_name = get_default_printer()

    if not printer_name:
        printers = get_printers()
        if printers:
            printer_name = printers[0]["name"]
        else:
            return False, "Kein Drucker verfuegbar", None

    # Check printer exists
    try:
        printers = conn.getPrinters()
        if printer_name not in printers:
            return False, f"Drucker '{printer_name}' nicht gefunden", None
    except:
        return False, "Drucker-Abfrage fehlgeschlagen", None

    # Build options
    options = {
        "copies": str(copies),
        "orientation-requested": "4",  # landscape
        "media": "A4",
        "fit-to-page": "true",
    }

    if not all_pages:
        options["page-ranges"] = "1"

    if color_mode == "grayscale":
        options["print-color-mode"] = "monochrome"
    elif color_mode == "color":
        options["print-color-mode"] = "color"

    # Print
    try:
        title = os.path.basename(pdf_path)
        job_id = conn.printFile(printer_name, pdf_path, title, options)
        logger.info(f"Druckauftrag gesendet: {title} -> {printer_name} (Job #{job_id})")
        return True, f"Druckauftrag #{job_id} an {printer_name}", job_id
    except Exception as e:
        logger.error(f"Druck fehlgeschlagen: {e}")
        return False, f"Druck fehlgeschlagen: {e}", None


def get_job_status(job_id):
    """Get print job status."""
    conn = _get_conn()
    if not conn:
        return {"status": "unknown", "message": "CUPS nicht verfuegbar"}

    try:
        import cups
        attrs = conn.getJobAttributes(job_id)
        state = attrs.get("job-state", 0)
        state_map = {
            3: "wartend",
            4: "gehalten",
            5: "druckt",
            6: "gestoppt",
            7: "abgebrochen",
            8: "fehler",
            9: "fertig",
        }
        return {
            "job_id": job_id,
            "status": state_map.get(state, f"unbekannt ({state})"),
            "printer": attrs.get("printer-uri", ""),
            "title": attrs.get("job-name", ""),
        }
    except Exception as e:
        return {"status": "fehler", "message": str(e)}


def get_print_queue():
    """Get all active print jobs."""
    conn = _get_conn()
    if not conn:
        return []

    try:
        jobs = conn.getJobs()
        result = []
        for job_id, attrs in jobs.items():
            state = attrs.get("job-state", 0)
            state_map = {3: "wartend", 4: "gehalten", 5: "druckt", 6: "gestoppt", 7: "abgebrochen", 8: "fehler", 9: "fertig"}
            result.append({
                "job_id": job_id,
                "title": attrs.get("job-name", ""),
                "printer": attrs.get("job-printer-uri", "").split("/")[-1],
                "status": state_map.get(state, str(state)),
                "created": attrs.get("time-at-creation", 0),
            })
        return result
    except:
        return []


def cancel_job(job_id):
    """Cancel a print job."""
    conn = _get_conn()
    if not conn:
        return False, "CUPS nicht verfuegbar"
    try:
        conn.cancelJob(job_id)
        return True, f"Job #{job_id} abgebrochen"
    except Exception as e:
        return False, str(e)


def test_print(printer_name=None):
    """Print a CUPS test page."""
    conn = _get_conn()
    if not conn:
        return False, "CUPS nicht verfuegbar", None

    if not printer_name:
        printer_name = get_default_printer()
        if not printer_name:
            printers = get_printers()
            if printers:
                printer_name = printers[0]["name"]

    if not printer_name:
        return False, "Kein Drucker verfuegbar", None

    try:
        job_id = conn.printTestPage(printer_name)
        return True, f"Testseite an {printer_name} (Job #{job_id})", job_id
    except Exception as e:
        return False, f"Testdruck fehlgeschlagen: {e}", None


def auto_print_pdf(pdf_path):
    """Auto-print a PDF if auto-print is enabled and printer available.
    Called after each new protocol PDF is generated.
    """
    config = load_print_config()
    if not config.get("auto_print", False):
        return

    if not is_cups_available():
        logger.debug("Auto-Print: CUPS nicht verfuegbar")
        return

    printers = get_printers()
    if not printers:
        logger.debug("Auto-Print: Kein Drucker angeschlossen")
        return

    printer_name = config.get("default_printer", "") or (printers[0]["name"] if printers else "")
    copies = config.get("copies", 1)
    all_pages = config.get("all_pages", True)
    color_mode = config.get("color_mode", "auto")

    # Print in background thread to not block serial receiver
    def _do_print():
        ok, msg, job_id = print_pdf(pdf_path, printer_name, copies, all_pages, color_mode)
        if ok:
            logger.info(f"Auto-Print OK: {os.path.basename(pdf_path)} -> {printer_name}")
        else:
            logger.warning(f"Auto-Print fehlgeschlagen: {msg}")

    t = threading.Thread(target=_do_print, daemon=True)
    t.start()


def setup_usb_printer(printer_name="DocuPrinter"):
    """Legt DocuPrinter als USB-Drucker in CUPS an (loescht alten Eintrag falls vorhanden).

    Ablauf:
    1. USB-URI per lpinfo -v ermitteln
    2. Alten CUPS-Eintrag entfernen (sudo lpadmin -x)
    3. Neu anlegen mit USB-URI (sudo lpadmin -p ... -v usb://... -m everywhere -E)
    4. Als Standard-Drucker setzen

    Voraussetzung: docucontrol darf lpadmin ohne Passwort ausfuehren:
      echo 'docucontrol ALL=(ALL) NOPASSWD: /usr/sbin/lpadmin' \
        | sudo tee /etc/sudoers.d/docucontrol-cups

    Returns: (success: bool, message: str)
    """
    # 1. USB-URI ermitteln (klassisch usb:// oder IPP-over-USB via ipp-usb)
    try:
        result = subprocess.run(
            ['sudo', '/usr/sbin/lpinfo', '-v'],
            capture_output=True, text=True, timeout=10
        )
        usb_uri = None
        ipp_usb_uri = None
        for line in result.stdout.splitlines():
            line = line.strip()
            # Klassisches CUPS USB-Backend
            if line.startswith('direct usb://'):
                usb_uri = line.split(' ', 1)[1].strip()
                break
            # IPP-over-USB (ipp-usb Dienst, modernes Debian/Pi OS)
            if 'USB' in line and '_ipp._tcp.local' in line:
                ipp_usb_uri = line.split(' ', 1)[1].strip()
        if not usb_uri:
            usb_uri = ipp_usb_uri
    except Exception as e:
        return False, f"lpinfo fehlgeschlagen: {e}"

    if not usb_uri:
        return False, "Kein USB-Drucker gefunden (lpinfo -v liefert keine USB-URI)"

    # 2. Alten Eintrag entfernen (Fehler ignorieren — existiert vielleicht nicht)
    subprocess.run(
        ['sudo', 'lpadmin', '-x', printer_name],
        capture_output=True, timeout=10
    )

    # 3. Neu anlegen mit USB-URI
    # IPP-over-USB (ipp-usb) braucht "-m everywhere", klassisches usb:// braucht PCL-PPD
    if usb_uri.startswith('usb://'):
        ppd_model = 'drv:///sample.drv/generpcl.ppd'
    else:
        ppd_model = 'everywhere'
    try:
        r = subprocess.run(
            ['sudo', 'lpadmin', '-p', printer_name,
             '-v', usb_uri,
             '-m', ppd_model,
             '-E',
             '-o', 'printer-is-shared=false',
             '-o', 'media=iso_a4_210x297mm'],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode != 0:
            return False, f"lpadmin fehlgeschlagen: {r.stderr.strip() or r.stdout.strip()}"
    except Exception as e:
        return False, f"lpadmin Fehler: {e}"

    # 4. Als Standard-Drucker setzen
    subprocess.run(
        ['sudo', 'lpadmin', '-d', printer_name],
        capture_output=True, timeout=10
    )

    logger.info(f"USB-Drucker eingerichtet: {printer_name} -> {usb_uri}")
    return True, f"Drucker als USB eingerichtet ({usb_uri})"


def setup_network_printer(host, printer_name="DocuPrinter"):
    """Legt DocuPrinter als Netzwerkdrucker in CUPS an (driverless via IPP Everywhere).

    Funktioniert geraeteunabhaengig fuer alle IPP-Everywhere/AirPrint/Mopria-
    zertifizierten Drucker (de facto Standard seit ca. 2014) - kein
    modellspezifischer Treiber noetig, analog zum IPP-over-USB-Fall in
    setup_usb_printer(). Aeltere, nicht zertifizierte Netzwerkdrucker
    unterstuetzen das nicht und bräuchten weiterhin einen eigenen PPD/Treiber.

    Returns: (success: bool, message: str)
    """
    host = (host or "").strip()
    if not host or not _HOST_RE.match(host):
        return False, "Ungueltige IP/Hostname fuer Netzwerkdrucker"

    # Alten Eintrag entfernen (Fehler ignorieren — existiert vielleicht nicht)
    subprocess.run(
        ['sudo', 'lpadmin', '-x', printer_name],
        capture_output=True, timeout=10
    )

    uri = f"ipp://{host}/ipp/print"
    try:
        r = subprocess.run(
            ['sudo', 'lpadmin', '-p', printer_name,
             '-v', uri,
             '-m', 'everywhere',
             '-E',
             '-o', 'printer-is-shared=false',
             '-o', 'media=iso_a4_210x297mm'],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode != 0:
            return False, f"lpadmin fehlgeschlagen ({uri}): {r.stderr.strip() or r.stdout.strip()}"
    except Exception as e:
        return False, f"lpadmin Fehler: {e}"

    subprocess.run(
        ['sudo', 'lpadmin', '-d', printer_name],
        capture_output=True, timeout=10
    )

    logger.info(f"Netzwerkdrucker eingerichtet: {printer_name} -> {uri}")
    return True, f"Drucker als Netzwerkdrucker eingerichtet ({uri})"


def get_status():
    """Get printer subsystem status for API."""
    config = load_print_config()
    printers = get_printers() if is_cups_available() else []
    return {
        "cups_available": _cups_available,
        "printer_count": len(printers),
        "printers": printers,
        "auto_print": config.get("auto_print", False),
        "default_printer": config.get("default_printer", ""),
        "copies": config.get("copies", 1),
        "all_pages": config.get("all_pages", True),
        "color_mode": config.get("color_mode", "auto"),
    }
