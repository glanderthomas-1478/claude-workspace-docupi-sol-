import serial
import threading
import time
import os
import logging
from datetime import datetime
from config import load_config
from database import save_protocol, log_event
from pdf_generator import generate_pdf
from storage_manager import copy_pdf_to_usb_instant
from print_manager import auto_print_pdf

logger = logging.getLogger("docupi.serial")

SERIAL_LOG_DIR = "/home/docucontrol/docupi/serial_logs"


class SerialLogger:
    """Schreibt alle seriellen Rohdaten in tagesweise Log-Dateien."""

    def __init__(self, log_dir=SERIAL_LOG_DIR):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self._current_date = None
        self._file = None

    def _get_log_file(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._current_date:
            if self._file:
                self._file.close()
            path = os.path.join(self.log_dir, f"serial_{today}.log")
            self._file = open(path, "a", encoding="utf-8")
            self._current_date = today
        return self._file

    def log_raw(self, text):
        """Schreibt empfangene Zeichen sofort in die Log-Datei."""
        try:
            f = self._get_log_file()
            f.write(text)
            f.flush()
        except Exception as e:
            logger.error(f"SerialLogger write error: {e}")

    def log_protocol_start(self):
        """Markiert den Beginn eines neuen Protokolls."""
        try:
            f = self._get_log_file()
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n{'='*60}\n")
            f.write(f"=== PROTOKOLL EMPFANGEN: {ts} ===\n")
            f.write(f"{'='*60}\n")
            f.flush()
        except Exception as e:
            logger.error(f"SerialLogger marker error: {e}")

    def log_protocol_end(self, char_count):
        """Markiert das Ende eines Protokolls."""
        try:
            f = self._get_log_file()
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n{'='*60}\n")
            f.write(f"=== ENDE PROTOKOLL: {ts} ({char_count} Zeichen) ===\n")
            f.write(f"{'='*60}\n\n")
            f.flush()
        except Exception as e:
            logger.error(f"SerialLogger marker error: {e}")

    def close(self):
        if self._file:
            self._file.close()
            self._file = None

    def get_log_files(self):
        """Gibt Liste aller Log-Dateien zurueck, neueste zuerst."""
        if not os.path.isdir(self.log_dir):
            return []
        files = []
        for f in sorted(os.listdir(self.log_dir), reverse=True):
            if f.startswith("serial_") and f.endswith(".log"):
                path = os.path.join(self.log_dir, f)
                stat = os.stat(path)
                files.append({
                    "filename": f,
                    "date": f.replace("serial_", "").replace(".log", ""),
                    "size": stat.st_size,
                    "size_kb": round(stat.st_size / 1024, 1),
                    "path": path,
                })
        return files

    def get_log_content(self, date_str, tail_lines=200):
        """Liest die letzten N Zeilen einer Log-Datei."""
        path = os.path.join(self.log_dir, f"serial_{date_str}.log")
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            if tail_lines and len(lines) > tail_lines:
                return "".join(lines[-tail_lines:])
            return "".join(lines)
        except Exception as e:
            logger.error(f"Log read error: {e}")
            return None


class SerialReceiver:
    def __init__(self, socketio=None):
        self.config = load_config()
        self.socketio = socketio
        self.running = False
        self.thread = None
        self.serial_port = None
        self.buffer = ""
        self.last_data_time = None
        self.connected = False
        self.bytes_received = 0
        self.rtc_timestamps = []  # (char_offset, datetime) for RTC time per block
        self.serial_logger = SerialLogger()
        self._port_retry_count = 0
        self._port_retry_interval = 5

    def get_status(self):
        return {"connected": self.connected, "running": self.running,
            "port": self.config["serial"]["port"], "baudrate": self.config["serial"]["baudrate"],
            "bytes_received": self.bytes_received, "buffer_size": len(self.buffer)}

    def open_port(self):
        cfg = self.config["serial"]
        parity_map = {"N": serial.PARITY_NONE, "E": serial.PARITY_EVEN, "O": serial.PARITY_ODD}
        parity_val = parity_map.get(cfg["parity"], serial.PARITY_NONE)
        try:
            self.serial_port = serial.Serial(
                port=cfg["port"],
                baudrate=cfg["baudrate"],
                bytesize=cfg["bytesize"],
                parity=parity_val,
                stopbits=cfg["stopbits"],
                timeout=cfg["timeout"],
                dsrdtr=False,
                rtscts=False,
            )
            self.connected = True
            self._port_retry_count = 0
            self._port_retry_interval = 5
            parity_name = {serial.PARITY_NONE: "N", serial.PARITY_EVEN: "E", serial.PARITY_ODD: "O"}.get(parity_val, "?")
            msg = f"Port {cfg['port']} geoeffnet ({cfg['baudrate']} {cfg['bytesize']}{parity_name}{cfg['stopbits']}, dsrdtr=off, rtscts=off)"
            logger.info(msg); log_event("INFO", msg)
            return True
        except serial.SerialException as e:
            self.connected = False
            self._port_retry_count += 1
            msg = f"Fehler: {cfg['port']}: {e}"
            if self._port_retry_count <= 1:
                logger.error(msg); log_event("ERROR", msg)
            elif self._port_retry_count % 60 == 0:
                logger.warning(f"Port {cfg['port']} nicht verfuegbar seit {self._port_retry_count} Versuchen")
                log_event("WARNING", f"Port {cfg['port']} nicht verfuegbar seit {self._port_retry_count} Versuchen")
            else:
                logger.debug(msg)
            return False
        except Exception as e:
            self.connected = False
            self._port_retry_count += 1
            msg = f"Unerwarteter Fehler beim Oeffnen von {cfg['port']}: {type(e).__name__}: {e}"
            if self._port_retry_count <= 1:
                logger.error(msg); log_event("ERROR", msg)
            else:
                logger.debug(msg)
            return False

    def close_port(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.connected = False

    def process_complete_protocol(self, data, rtc_timestamps=None):
        if not data.strip(): return
        self.serial_logger.log_protocol_end(len(data))
        timestamp = datetime.now()
        device_name = self.config["pdf"]["device_name"]
        logger.info(f"Protokoll: {len(data)} Zeichen")
        log_event("INFO", f"Protokoll empfangen: {len(data)} Zeichen von {device_name}")
        protocol_id = save_protocol(data, device_name)
        try:
            pdf_path, pdf_filename, file_size = generate_pdf(data, protocol_id, timestamp, self.config, rtc_timestamps=rtc_timestamps)
            logger.info(f"PDF: {pdf_filename}")
            log_event("INFO", f"PDF erzeugt: {pdf_filename} ({file_size} Bytes)")
            # Sofort auf USB kopieren falls eingesteckt
            try:
                copy_pdf_to_usb_instant(pdf_path, pdf_filename)
            except Exception as ue:
                logger.debug(f"USB-Sofortkopie: {ue}")
            # Auto-Print falls aktiviert
            try:
                auto_print_pdf(pdf_path)
            except Exception as pe:
                logger.debug(f"Auto-Print: {pe}")
            if self.socketio:
                self.socketio.emit("new_protocol", {"id": protocol_id, "timestamp": timestamp.isoformat(),
                    "filename": pdf_filename, "size": file_size, "device": device_name})
        except Exception as e:
            logger.error(f"PDF fehlgeschlagen: {e}")
            log_event("ERROR", f"PDF-Erzeugung fehlgeschlagen: {e}")

    def check_timeout(self):
        """Check if protocol is complete by smart end detection or timeout.

        WICHTIG: Der Sterilisator uebertraegt das Protokoll waehrend des gesamten
        Zyklus (bis zu 60+ Minuten) in kleinen Bloecken mit langen Pausen dazwischen.
        Einzig sicherer End-Trigger ist 'Unterschrift:' am Ende des Protokolls.
        """
        if not self.last_data_time or not self.buffer.strip():
            return False

        elapsed = time.time() - self.last_data_time

        # Primaerer End-Trigger: "Unterschrift:" ist das allerletzte Feld im Protokoll
        if "Unterschrift:" in self.buffer and elapsed >= 3:
            logger.info("Protokoll-Ende erkannt: Unterschrift: + 3s Stille")
            return True

        # Sekundaerer End-Trigger: Abort-Protokoll ohne "Unterschrift:"
        if "ABGEBROCHEN" in self.buffer.upper() and elapsed >= 10 and len(self.buffer.strip()) > 200:
            logger.info("Protokoll-Ende erkannt: ABGEBROCHEN + 10s Stille")
            return True

        # Sicherheits-Fallback: Nach 15 Min Stille
        # Laengster realer Zyklus: ~64 Min, danach kommt "Unterschrift:" sofort
        if elapsed >= 900 and len(self.buffer.strip()) > 200:
            logger.warning(f"Sicherheits-Fallback ({elapsed:.0f}s) mit {len(self.buffer)} Zeichen")
            return True

        return False

    def _receive_loop(self):
        logger.info("Empfangsschleife gestartet")
        protocol_active = False
        while self.running:
            try:
                if not self.serial_port or not self.serial_port.is_open:
                    if not self.open_port():
                        time.sleep(min(30, self._port_retry_interval))
                        self._port_retry_interval = min(30, self._port_retry_interval * 2)
                        continue

                if self.serial_port.in_waiting > 0:
                    raw = self.serial_port.read(self.serial_port.in_waiting)
                    text = raw.decode("latin-1", errors="replace")
                    self.bytes_received += len(raw)
                    self.last_data_time = time.time()
                    self.rtc_timestamps.append((len(self.buffer), datetime.now()))

                    # Alles in Serial-Log schreiben
                    self.serial_logger.log_raw(text)

                    if self.socketio:
                        self.socketio.emit("serial_data", {"data": text})

                    for char in text:
                        if char == chr(12):
                            # Form-Feed: NICHT als Protokoll-Ende behandeln!
                            # Der Sterilisator sendet FF nach jedem Prozessschritt,
                            # aber wir wollen ein PDF pro GESAMTEM Zyklus.
                            self.buffer += chr(10)
                            if not protocol_active:
                                self.serial_logger.log_protocol_start()
                                protocol_active = True
                        else:
                            if not protocol_active and char.strip():
                                self.serial_logger.log_protocol_start()
                                protocol_active = True
                            self.buffer += char

                    # Neuen Zyklus-Start erkennen
                    if "BELIMED CHARGEN" in text and protocol_active:
                        split_pos = self.buffer.rfind("BELIMED CHARGEN")
                        before = self.buffer[:split_pos].strip() if split_pos > 0 else ""
                        if before and len(before) > 100:
                            # IMMER vorheriges Protokoll speichern, auch unvollstaendig
                            old_data = self.buffer[:split_pos]
                            new_data = self.buffer[split_pos:]
                            if "Unterschrift:" in before or "KORREKT BEENDET" in before.upper() or "ABGEBROCHEN" in before.upper():
                                logger.info(f"Neuer Zyklus erkannt - verarbeite vorherigen ({len(old_data)} Zeichen)")
                            else:
                                logger.warning(f"Neuer Zyklus erkannt - vorheriges Protokoll UNVOLLSTAENDIG ({len(old_data)} Zeichen)")
                            self.process_complete_protocol(old_data, self.rtc_timestamps)
                            self.buffer = new_data
                            self.rtc_timestamps = [(0, datetime.now())]

                if self.check_timeout():
                    self.process_complete_protocol(self.buffer, self.rtc_timestamps)
                    self.buffer = ""
                    self.rtc_timestamps = []
                    protocol_active = False

                time.sleep(0.05)

            except serial.SerialException as e:
                self.connected = False
                logger.error(f"Serial: {e}"); log_event("ERROR", f"Serial: {e}")
                self.close_port(); time.sleep(5)
            except Exception as e:
                logger.error(f"Error: {e}"); log_event("ERROR", f"Error: {e}")
                time.sleep(1)


    def start(self):
        if self.running: return
        self.config = load_config()
        self.running = True
        self.thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.thread.start()
        logger.info("Serial Receiver gestartet")

    def stop(self):
        self.running = False
        if self.buffer.strip():
            self.process_complete_protocol(self.buffer, self.rtc_timestamps)
            self.buffer = ""
            self.rtc_timestamps = []
        self.close_port()
        self.serial_logger.close()
        if self.thread: self.thread.join(timeout=5)
        logger.info("Serial Receiver gestoppt")

    def restart(self):
        self.stop(); time.sleep(1); self.start()
