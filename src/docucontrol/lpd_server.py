"""
LPD-Server (RFC 1179, Port 515)
Alternativer Empfangsweg fuer Maschinen, die per Line Printer Daemon-Protokoll
drucken statt per Raw-TCP/9100. Empfangene Datendateien werden ueber dieselbe
Pipeline wie der TCP/9100-Capture verarbeitet (Parse -> PDF -> DB / Sammelmodus).
"""

import logging
import socketserver
import threading
from datetime import datetime

from tcp_print_capture import (
    CAPTURE_DIR,
    detect_format,
    try_extract_text,
    load_capture_config,
    _process_job,
    _auto_print_text,
)
import os

logger = logging.getLogger("docupi.lpd")

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 515

CMD_PRINT_WAITING_JOBS = 0x01
CMD_RECEIVE_JOB = 0x02
CMD_SEND_QUEUE_STATE_SHORT = 0x03
CMD_SEND_QUEUE_STATE_LONG = 0x04
CMD_REMOVE_JOBS = 0x05

SUBCMD_ABORT_JOB = 0x01
SUBCMD_RECEIVE_CONTROL_FILE = 0x02
SUBCMD_RECEIVE_DATA_FILE = 0x03


def _read_line(rfile):
    """Liest eine LPD-Kommandozeile bis LF (ohne das LF zurueckzugeben)."""
    line = rfile.readline()
    if not line:
        return None
    return line.rstrip(b"\n")


class _Stats:
    def __init__(self):
        self.job_count = 0
        self.last_job_ts = None
        self.last_job_size = 0
        self.last_job_format = ""

    def as_dict(self, running):
        return {
            "running": running,
            "port": LISTEN_PORT,
            "job_count": self.job_count,
            "last_job_ts": self.last_job_ts.isoformat() if self.last_job_ts else None,
            "last_job_size": self.last_job_size,
            "last_job_format": self.last_job_format,
        }


_stats = _Stats()
_server = None


class _LPDHandler(socketserver.StreamRequestHandler):
    timeout = 30

    def handle(self):
        peer = self.client_address
        try:
            cmd_line = _read_line(self.rfile)
        except Exception as e:
            logger.error(f"LPD Lesefehler von {peer}: {e}")
            return
        if not cmd_line:
            return

        cmd = cmd_line[0]
        if cmd == CMD_RECEIVE_JOB:
            queue = cmd_line[1:].decode("utf-8", errors="replace")
            self.wfile.write(b"\x00")
            self._receive_job(peer, queue)
        elif cmd in (CMD_SEND_QUEUE_STATE_SHORT, CMD_SEND_QUEUE_STATE_LONG):
            self.wfile.write(b"keine Auftraege\n")
        elif cmd == CMD_PRINT_WAITING_JOBS:
            self.wfile.write(b"\x00")
        else:
            logger.warning(f"LPD: unbekanntes Kommando 0x{cmd:02x} von {peer}")
            self.wfile.write(b"\x00")

    def _receive_job(self, peer, queue):
        logger.info(f"LPD-Druckauftrag von {peer} fuer Queue '{queue}'")
        data_chunks = []
        while True:
            sub_line = _read_line(self.rfile)
            if sub_line is None or len(sub_line) == 0:
                break
            sub = sub_line[0]
            try:
                count_str, _, _name = sub_line[1:].decode(
                    "utf-8", errors="replace"
                ).partition(" ")
                count = int(count_str)
            except Exception:
                self.wfile.write(b"\x01")
                break

            if sub in (SUBCMD_RECEIVE_CONTROL_FILE, SUBCMD_RECEIVE_DATA_FILE):
                self.wfile.write(b"\x00")
                payload = self.rfile.read(count)
                ack = self.rfile.read(1)  # abschliessendes 0x00
                self.wfile.write(b"\x00")
                if sub == SUBCMD_RECEIVE_DATA_FILE:
                    data_chunks.append(payload)
            elif sub == SUBCMD_ABORT_JOB:
                logger.info(f"LPD-Auftrag von {peer} abgebrochen")
                self.wfile.write(b"\x00")
                return
            else:
                self.wfile.write(b"\x01")
                break

        if not data_chunks:
            logger.warning(f"LPD-Auftrag von {peer} ohne Daten, verworfen")
            return

        raw = b"".join(data_chunks)
        _stats.job_count += 1
        _stats.last_job_ts = datetime.now()
        _stats.last_job_size = len(raw)
        _stats.last_job_format = detect_format(raw)

        os.makedirs(CAPTURE_DIR, exist_ok=True)
        ts = _stats.last_job_ts.strftime("%Y%m%d_%H%M%S")
        basename = f"{ts}_lpd{_stats.job_count:04d}"
        bin_path = os.path.join(CAPTURE_DIR, basename + ".bin")
        with open(bin_path, "wb") as f:
            f.write(raw)

        text = try_extract_text(raw)
        if not text:
            logger.warning(f"LPD-Auftrag {basename}: kein Text extrahierbar")
            return

        txt_path = os.path.join(CAPTURE_DIR, basename + ".txt")
        with open(txt_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(text)

        logger.info(
            f"LPD-Charge #{_stats.job_count} erfasst: {len(raw)} Bytes, "
            f"Format={_stats.last_job_format}, Datei={basename}.bin"
        )

        cfg = load_capture_config()
        if cfg.get("collector_mode", False):
            threading.Thread(
                target=_auto_print_text, args=(txt_path,), daemon=True
            ).start()
        else:
            threading.Thread(
                target=_process_job, args=(txt_path, text), daemon=True
            ).start()


class _ThreadingLPDServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_lpd_server():
    global _server

    def _run():
        global _server
        try:
            _server = _ThreadingLPDServer((LISTEN_HOST, LISTEN_PORT), _LPDHandler)
        except Exception as e:
            logger.error(f"LPD-Server konnte Port {LISTEN_PORT} nicht binden: {e}")
            return
        logger.info(f"LPD-Server lauscht auf {LISTEN_HOST}:{LISTEN_PORT}")
        _server.serve_forever()

    t = threading.Thread(target=_run, daemon=True, name="lpd-server")
    t.start()


def get_lpd_status():
    return _stats.as_dict(running=_server is not None)
