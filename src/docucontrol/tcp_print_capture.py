"""
TCP/9100 Print Job Capture
Intercepts raw print jobs (port 9100). Saves raw data + extracts text.
Config persisted in capture_config.json. Optional USB auto-print via lpr.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import threading
from datetime import datetime

logger = logging.getLogger("docupi.tcp_capture")

# Callback für neue pending Chargen → von app.py registriert
_pending_charge_callback = None


def set_pending_charge_callback(callback):
    """Registriert Callback für neue pending Chargen → von app.py aufgerufen.
    callback(protocol_id: int, metadata: dict) — Thread-safe via SocketIO threading mode.
    """
    global _pending_charge_callback
    _pending_charge_callback = callback


CAPTURE_DIR = "/home/docucontrol/docupi/data/raw_captures"
CAPTURE_CONFIG_FILE = "/home/docucontrol/docupi/data/capture_config.json"
LISTEN_HOST = "0.0.0.0"
READ_TIMEOUT = 10.0

DEFAULT_CONFIG = {
    "tcp_enabled": True,
    "auto_print": False,
    "port": 9100,
    "collector_mode": False,
}


def load_capture_config():
    if os.path.exists(CAPTURE_CONFIG_FILE):
        try:
            with open(CAPTURE_CONFIG_FILE, "r") as f:
                cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
        except Exception as e:
            logger.error(f"capture_config.json lesen fehlgeschlagen: {e}")
    return dict(DEFAULT_CONFIG)


def save_capture_config(cfg):
    os.makedirs(os.path.dirname(CAPTURE_CONFIG_FILE), exist_ok=True)
    try:
        with open(CAPTURE_CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        logger.error(f"capture_config.json schreiben fehlgeschlagen: {e}")


def detect_format(data):
    if len(data) < 2:
        return "empty"
    if data[:9] == b"\x1b%-12345X":
        return "PJL"
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return "UTF-16"
    if data[:2] == b"\x1b@":
        return "ESC/P2"
    if data[:2] in (b"\x1bE", b"\x1b%"):
        return "PCL"
    if data[:2] == b"%!":
        return "PostScript"
    if data[:4] == b"%PDF":
        return "PDF"
    if len(data) >= 10 and all(data[i] == 0 for i in range(1, min(20, len(data)), 2)):
        return "UTF-16LE"
    try:
        data[:min(200, len(data))].decode("utf-8")
        return "UTF-8 text"
    except Exception:
        pass
    return f"unknown (0x{data[:4].hex()})"


def try_extract_text(data):
    if data[:2] == b"\xff\xfe":
        try:
            return data.decode("utf-16-le", errors="replace")
        except Exception:
            pass
    if data[:2] == b"\xfe\xff":
        try:
            return data.decode("utf-16-be", errors="replace")
        except Exception:
            pass
    if len(data) >= 10 and all(data[i] == 0 for i in range(1, min(20, len(data)), 2)):
        try:
            return data.decode("utf-16-le", errors="replace")
        except Exception:
            pass
    try:
        text = data.decode("utf-8", errors="replace")
        printable = sum(1 for c in text if c.isprintable() or c in "\r\n\t")
        if printable / max(len(text), 1) > 0.6:
            return text
    except Exception:
        pass
    chunks = re.findall(b"[\x20-\x7e\r\n\t]{8,}", data)
    if chunks:
        return "\n".join(c.decode("ascii", errors="replace") for c in chunks)
    return None


def _auto_print_text(txt_path):
    """Druckt .txt-Datei via CUPS /usr/bin/lp (Sammelmodus: Rohtext ohne PDF)."""
    import tempfile
    try:
        # BOM entfernen (Belimed sendet UTF-16 mit BOM, extrahiertes .txt hat utf-8-sig)
        txt = open(txt_path, encoding='utf-8-sig', errors='replace').read()

        # Druckernamen aus print_config.json lesen
        printer = 'DocuPrinter'
        try:
            import json as _json
            with open('/home/docucontrol/docupi/data/print_config.json') as _f:
                _pcfg = _json.load(_f)
            printer = _pcfg.get('default_printer', '') or 'DocuPrinter'
        except Exception:
            pass

        # BOM-bereinigten Text in temp-Datei schreiben, dann per lp drucken
        fd, tmp_path = tempfile.mkstemp(suffix='.txt', prefix='docupi_raw_')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as _f:
                _f.write(txt)
            result = subprocess.run(
                ['/usr/bin/lp', '-d', printer, tmp_path],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                logger.info(f"Sammelmodus-Druck OK: {os.path.basename(txt_path)} → {printer}")
            else:
                logger.warning(f"Sammelmodus-Druck fehlgeschlagen: {result.stderr.strip()}")
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Sammelmodus-Druck Fehler: {e}")




def _process_job(txt_path, raw_text):
    """Sofort: Rohdaten in DB (status=pending_form). PDF erst nach Formular-Bestätigung."""
    try:
        import sys as _sys
        _sys.path.insert(0, '/home/docucontrol/docupi')
        from protocol_parser import parse_serial_protocol, preselect_autoclave_program
        from database import save_protocol, save_form_draft
        import json as _json

        protocol = parse_serial_protocol(raw_text)
        device = protocol.get('device_name', '')
        program_str = protocol.get('program_name', '') or protocol.get('program', '')

        # Sofort in DB speichern — status=pending_form, NOCH KEIN PDF
        pid = save_protocol(raw_text, device, status='pending_form')

        # Programm-Vorauswahl berechnen
        preselection = preselect_autoclave_program(program_str, raw_text)

        # Formulardaten-Datensatz mit Vorauswahl anlegen
        save_form_draft(pid, '{}', preselected_program=preselection.get('program_key', ''))

        charge_nr = protocol.get('charge_nr', '') or str(pid)
        metadata = {
            'protocol_id': pid,
            'charge_nr': charge_nr,
            'device': device,
            'program': program_str,
            'preselection': preselection,
            'timestamp': datetime.now().isoformat(),
        }

        logger.info("Charge #%s gespeichert (pending_form, pid=%d) — warte auf Formular", charge_nr, pid)

        if _pending_charge_callback is not None:
            try:
                _pending_charge_callback(pid, metadata)
            except Exception as cb_err:
                logger.warning("pending_charge_callback Fehler: %s", cb_err)

    except Exception as e:
        logger.error("Job-Verarbeitung fehlgeschlagen: %s", e)


def _finalize_charge_pdf(protocol_id, form_data):
    """Nach Formular-Bestätigung aus app.py aufgerufen. Generiert finales PDF."""
    try:
        import sys as _sys
        _sys.path.insert(0, '/home/docucontrol/docupi')
        from database import get_db, update_protocol_pdf
        from pdf_generator import generate_pdf
        from config import load_config
        import os as _os

        conn = get_db()
        row = conn.execute("SELECT * FROM protocols WHERE id=?", (protocol_id,)).fetchone()
        conn.close()
        if not row:
            logger.error("_finalize_charge_pdf: Protokoll %d nicht gefunden", protocol_id)
            return False, "Protokoll nicht gefunden"

        raw_text = row['raw_data']
        config = load_config()
        config['pdf']['fallback_dir'] = '/home/docucontrol/docupi/data/pdfs'
        _os.makedirs('/home/docucontrol/docupi/data/pdfs', exist_ok=True)

        from datetime import datetime as _dt
        ts = _dt.fromisoformat(row['timestamp']) if row['timestamp'] else _dt.now()

        pdf_path, pdf_filename, size = generate_pdf(
            raw_text, protocol_id, ts, config, form_data=form_data
        )
        update_protocol_pdf(protocol_id, pdf_path, pdf_filename, size)

        try:
            from storage_manager import copy_pdf_to_usb_instant
            copy_pdf_to_usb_instant(pdf_path, pdf_filename)
        except Exception as e:
            logger.warning("USB-Copy fehlgeschlagen: %s", e)
        try:
            from network_storage_manager import copy_pdf_to_network_instant
            copy_pdf_to_network_instant(pdf_path, pdf_filename)
        except Exception as e:
            logger.warning("Netzwerk-Copy fehlgeschlagen: %s", e)
        try:
            from print_manager import auto_print_pdf
            auto_print_pdf(pdf_path)
        except Exception as e:
            logger.warning("Auto-Print fehlgeschlagen: %s", e)

        logger.info("PDF finalisiert: %s (%d Bytes), pid=%d", pdf_filename, size, protocol_id)
        return True, pdf_filename

    except Exception as e:
        logger.error("_finalize_charge_pdf fehlgeschlagen (pid=%d): %s", protocol_id, e)
        try:
            from database import set_pdf_failed
            set_pdf_failed(protocol_id)
        except Exception as db_err:
            logger.warning("set_pdf_failed fehlgeschlagen: %s", db_err)
        return False, str(e)

class PrintCaptureServer:
    def __init__(self, auto_print=False):
        self.auto_print = auto_print
        self._server = None
        self.job_count = 0
        self.last_job_ts = None
        self.last_job_size = 0
        self.last_job_format = ""
        os.makedirs(CAPTURE_DIR, exist_ok=True)

    async def _handle(self, reader, writer):
        peer = writer.get_extra_info("peername")
        logger.info(f"Druckauftrag von {peer}")
        chunks = []
        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(reader.read(8192), timeout=READ_TIMEOUT)
                except asyncio.TimeoutError:
                    break
                if not chunk:
                    break
                chunks.append(chunk)
                if len(chunks) == 1 and chunks[0].lstrip()[:4] == b"@PJL":
                    pjl_ready = (
                        b"\x1b%-12345X@PJL\r\n"
                        b"@PJL INFO STATUS\r\n"
                        b"CODE=10001\r\n"
                        b"DISPLAY=\"READY\"\r\n"
                        b"ONLINE=TRUE\r\n"
                        b"\x1b%-12345X"
                    )
                    try:
                        writer.write(pjl_ready)
                        await writer.drain()
                    except Exception:
                        pass
                    logger.info(f"PJL STATUS READY gesendet an {peer}")
        except Exception as e:
            logger.error(f"Lesefehler von {peer}: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

        if not chunks:
            logger.warning(f"Leerer Auftrag von {peer}, ignoriert")
            return

        raw = b"".join(chunks)
        self.job_count += 1
        self.last_job_ts = datetime.now()
        self.last_job_size = len(raw)
        self.last_job_format = detect_format(raw)

        ts = self.last_job_ts.strftime("%Y%m%d_%H%M%S")
        basename = f"{ts}_job{self.job_count:04d}"

        bin_path = os.path.join(CAPTURE_DIR, basename + ".bin")
        with open(bin_path, "wb") as f:
            f.write(raw)

        txt_path = None
        text = try_extract_text(raw)
        if text:
            txt_path = os.path.join(CAPTURE_DIR, basename + ".txt")
            with open(txt_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(text)

        logger.info(
            f"Charge #{self.job_count} erfasst: {len(raw)} Bytes, "
            f"Format={self.last_job_format}, Datei={basename}.bin"
        )

        cfg = load_capture_config()
        collector_mode = cfg.get("collector_mode", False)

        if collector_mode:
            # Sammelmodus: Rohtext 1:1 drucken, kein Parse, keine PDF, kein DB-Eintrag
            if txt_path:
                logger.info("Sammelmodus: Rohtext-Druck ohne PDF-Generierung")
                threading.Thread(
                    target=_auto_print_text, args=(txt_path,), daemon=True
                ).start()
        else:
            # Normalmodus: Parse → PDF → DB (+ Auto-Print via print_manager)
            if txt_path:
                with open(txt_path, "r", encoding="utf-8", errors="replace") as _f:
                    _raw_text = _f.read()
                threading.Thread(
                    target=_process_job, args=(txt_path, _raw_text), daemon=True
                ).start()

    async def serve(self):
        port = load_capture_config().get("port", 9100)
        self._server = await asyncio.start_server(self._handle, LISTEN_HOST, port)
        logger.info(f"TCP/{port} Capture lauscht auf {LISTEN_HOST}:{port}")
        async with self._server:
            await self._server.serve_forever()

    def get_status(self):
        captures = []
        if os.path.exists(CAPTURE_DIR):
            captures = sorted(
                f for f in os.listdir(CAPTURE_DIR) if f.endswith(".bin")
            )
        cfg = load_capture_config()
        return {
            "running": self._server is not None,
            "port": cfg.get("port", 9100),
            "tcp_enabled": cfg.get("tcp_enabled", True),
            "auto_print": self.auto_print,
            "collector_mode": cfg.get("collector_mode", False),
            "job_count": self.job_count,
            "last_job_ts": self.last_job_ts.isoformat() if self.last_job_ts else None,
            "last_job_size": self.last_job_size,
            "last_job_format": self.last_job_format,
            "captures": captures[-20:],
        }


_instance = None


def start_capture_server(auto_print=False):
    global _instance

    def _run():
        global _instance
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _instance = PrintCaptureServer(auto_print=auto_print)
        try:
            loop.run_until_complete(_instance.serve())
        except Exception as e:
            logger.error(f"Capture-Server gestoppt: {e}")

    t = threading.Thread(target=_run, daemon=True, name="tcp-capture")
    t.start()
    logger.info("TCP/9100 Capture-Server startet")


def get_capture_status():
    if _instance is None:
        cfg = load_capture_config()
        return {
            "running": False,
            "port": cfg.get("port", 9100),
            "tcp_enabled": cfg.get("tcp_enabled", True),
            "auto_print": cfg.get("auto_print", False),
            "collector_mode": cfg.get("collector_mode", False),
            "job_count": 0,
            "last_job_ts": None,
            "last_job_size": 0,
            "last_job_format": "",
            "captures": [],
        }
    return _instance.get_status()
