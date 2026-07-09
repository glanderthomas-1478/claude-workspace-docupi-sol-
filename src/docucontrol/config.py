import os
import json

CONFIG_FILE = "/home/docucontrol/docupi/data/config.json"

DEFAULT_CONFIG = {
    "serial": {
        "port": "/dev/ttyUSB0",
        "baudrate": 9600,
        "bytesize": 8,
        "parity": "E",
        "stopbits": 1,
        "timeout": 1
    },
    "protocol": {
        "delimiter": "formfeed",
        "timeout_seconds": 10,
        "custom_delimiter": ""
    },
    "pdf": {
        "output_dir": "/media/usbstick",
        "fallback_dir": "/home/docucontrol/docupi/data/pdfs",
        "folder_structure": "date",
        "filename_pattern": "{datum}_{zeit}_{geraet}_{charge}",
        "filename_separator": "_",
        "handwritten_fields": False,
        "device_alias": "",
        "notfall_rows": 18,
        "header_text": "DocuControl Protokoll",
        "device_name": "Sterilisator / RDG",
        "font_size": 8,
        "page_format": "A4",
        "abteilung": "ZTL"
    },
    "web": {
        "host": "0.0.0.0",
        "port": 5000
    },
    "system": {
        "hostname": "DocuControl",
        "log_level": "INFO"
    },
    "machine": {
        "name": "Belimed PST 14-8-12 HS1",
        "ip": "",
        "protocol": "6050 / 6060 FIS"
    },
    "sol": {
        "sensor_names": "Testo 835-T1 / Testo 608-H1",
        "temp_tolerance_c": 5.0,
        "bottle_warn_count": 160,
        "standort_kuerzel": "",
        "rows_per_page": 18,
        "scanner_bt_mac": "",
        "scanner_enabled": True,
        "temp_sensor_enabled": True,
        "temp_sensor_bt_mac": "01:B6:EC:FC:DA:E1"
    }
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            saved = json.load(f)
            config = {}
            for section in DEFAULT_CONFIG:
                config[section] = dict(DEFAULT_CONFIG[section])
                if section in saved:
                    config[section].update(saved[section])
            return config
    return {k: dict(v) for k, v in DEFAULT_CONFIG.items()}

def save_config(config):
    """Atomic write: schreibt in temp-Datei und benennt um, damit
    ein Stromausfall die config.json nicht zerstoert."""
    import tempfile
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    dir_name = os.path.dirname(CONFIG_FILE)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp", prefix="config_")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(config, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, CONFIG_FILE)
        # Backup erstellen
        import shutil
        try:
            shutil.copy2(CONFIG_FILE, CONFIG_FILE + '.backup')
        except Exception:
            pass
    except Exception:
        # Cleanup temp file on error
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

config = load_config()
