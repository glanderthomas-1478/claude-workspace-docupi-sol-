#!/usr/bin/env python3
"""
DocuPi-3000 Boot Health Check
Wird beim App-Start aufgerufen und repariert was noetig ist.
"""

import os
import json
import shutil
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger("docupi.health")

DATA_DIR = "/home/docucontrol/docupi/data"
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
CONFIG_BACKUP = os.path.join(DATA_DIR, "config.json.backup")
DB_PATH = os.path.join(DATA_DIR, "docupi.db")

def run_health_check():
    """Fuehrt alle Checks beim Start durch. Gibt True zurueck wenn alles OK."""
    logger.info("=== Boot Health Check gestartet ===")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    ok = True
    ok = _check_config() and ok
    ok = _check_database() and ok
    ok = _check_directories() and ok
    
    if ok:
        logger.info("=== Health Check: ALLES OK ===")
    else:
        logger.warning("=== Health Check: Probleme behoben ===")
    return ok


def _check_config():
    """Prueft config.json - repariert aus Backup oder Default falls korrupt."""
    # Versuch 1: config.json lesen
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
            if "serial" in data and "pdf" in data:
                logger.info("config.json: OK")
                # Backup aktualisieren (nur wenn config valid ist)
                _backup_config()
                return True
            else:
                logger.warning("config.json: Unvollstaendig (fehlende Sektionen)")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"config.json: Korrupt ({e})")
    else:
        logger.warning("config.json: FEHLT")

    # Versuch 2: Backup laden
    if os.path.exists(CONFIG_BACKUP):
        try:
            with open(CONFIG_BACKUP, "r") as f:
                data = json.load(f)
            if "serial" in data:
                shutil.copy2(CONFIG_BACKUP, CONFIG_FILE)
                logger.info("config.json: Aus Backup wiederhergestellt")
                return True
        except Exception as e:
            logger.error(f"config.json Backup auch korrupt: {e}")

    # Versuch 3: Default-Config schreiben
    logger.warning("config.json: Schreibe DEFAULT-Konfiguration")
    from config import DEFAULT_CONFIG, save_config
    save_config({k: dict(v) for k, v in DEFAULT_CONFIG.items()})
    return False


def _backup_config():
    """Erstellt ein Backup der config.json (nur wenn sie valid ist)."""
    try:
        shutil.copy2(CONFIG_FILE, CONFIG_BACKUP)
    except Exception as e:
        logger.error(f"Config-Backup fehlgeschlagen: {e}")


def _check_database():
    """Prueft SQLite-Datenbank auf Integritaet."""
    if not os.path.exists(DB_PATH):
        logger.info("Datenbank existiert nicht - wird beim Start erstellt")
        return True

    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        # Integrity check
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            logger.error(f"Datenbank-Integritaet: {result}")
            # Versuche WAL-Checkpoint (repariert oft WAL-Probleme)
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            result2 = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if result2 == "ok":
                logger.info("Datenbank nach WAL-Checkpoint repariert")
            else:
                logger.error("Datenbank beschaedigt - Backup noetig!")
                # DB umbenennen und neu starten lassen
                backup_name = DB_PATH + f".broken.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(DB_PATH, backup_name)
                logger.warning(f"Beschaedigte DB gesichert als {backup_name}")
                conn.close()
                return False
        
        # WAL-Modus sicherstellen
        mode = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.close()
        logger.info(f"Datenbank: OK (journal={mode})")
        return True
    except Exception as e:
        logger.error(f"Datenbank-Check fehlgeschlagen: {e}")
        return False


def _check_directories():
    """Stellt sicher dass alle noetige Verzeichnisse existieren."""
    dirs = [
        "/home/docucontrol/docupi/data",
        "/home/docucontrol/docupi/data/pdfs",
        "/home/docucontrol/docupi/logs",
        "/home/docucontrol/docupi/serial_logs",
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    logger.info("Verzeichnisse: OK")
    return True


def backup_config_on_save():
    """Wird nach jedem save_config() aufgerufen."""
    _backup_config()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    run_health_check()
