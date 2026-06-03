"""
DocuPi-3000 Print Manager
CUPS-basierter USB-Drucker-Support mit IPP Everywhere (driverless).
- Drucker erkennen und verwalten
- PDFs drucken (manuell + Auto-Print)
- Druckstatus abfragen
"""

import logging
import os
import threading
import time

logger = logging.getLogger("docupi.print")

# State
_cups_available = False
_conn = None
_auto_print_enabled = False
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
}


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

        for name, attrs in printers.items():
            state = attrs.get("printer-state", 0)
            state_map = {3: "bereit", 4: "druckt", 5: "gestoppt"}
            state_text = state_map.get(state, f"unbekannt ({state})")

            result.append({
                "name": name,
                "info": attrs.get("printer-info", name),
                "location": attrs.get("printer-location", ""),
                "uri": attrs.get("device-uri", ""),
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
