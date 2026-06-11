import sqlite3
import os
from datetime import datetime
import re as _re

_CHARGE_RE = _re.compile(r'Laufende\s+Nr\.?\s*:\s*0*(\d+)', _re.IGNORECASE)
_PROG_RE   = _re.compile(r'Programm\s*[:\.]?\s*(.+)',       _re.IGNORECASE)

DB_PATH = "/home/docucontrol/docupi/data/docupi.db"

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS protocols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            device_name TEXT DEFAULT '',
            raw_data TEXT NOT NULL,
            pdf_path TEXT DEFAULT '',
            pdf_filename TEXT DEFAULT '',
            file_size INTEGER DEFAULT 0,
            status TEXT DEFAULT 'received',
            charge_nr_int INTEGER DEFAULT NULL,
            program TEXT DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS system_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_protocols_timestamp ON protocols(timestamp);
        CREATE INDEX IF NOT EXISTS idx_protocols_status ON protocols(status);
        CREATE INDEX IF NOT EXISTS idx_charge_nr_int ON protocols(charge_nr_int);
        CREATE INDEX IF NOT EXISTS idx_program ON protocols(program);
    """)
    conn.commit()
    conn.close()

def log_event(level, message):
    conn = get_db()
    conn.execute("INSERT INTO system_log (timestamp, level, message) VALUES (?, ?, ?)",
        (datetime.now().isoformat(), level, message))
    conn.commit()
    conn.close()

def save_protocol(raw_data, device_name=""):
    cm = _CHARGE_RE.search(raw_data or '')
    charge_nr_int = int(cm.group(1)) if cm else None
    pm = _PROG_RE.search(raw_data or '')
    program_val = pm.group(1).strip()[:60] if pm else None
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO protocols (timestamp, device_name, raw_data, status, charge_nr_int, program) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), device_name, raw_data, "received", charge_nr_int, program_val))
    protocol_id = cur.lastrowid
    conn.commit()
    conn.close()
    return protocol_id

def update_protocol_pdf(protocol_id, pdf_path, pdf_filename, file_size):
    conn = get_db()
    conn.execute("UPDATE protocols SET pdf_path=?, pdf_filename=?, file_size=?, status=? WHERE id=?",
        (pdf_path, pdf_filename, file_size, "completed", protocol_id))
    conn.commit()
    conn.close()

def get_protocols(limit=50, offset=0, date_filter=None):
    conn = get_db()
    query = "SELECT * FROM protocols WHERE status='completed'"
    params = []
    if date_filter:
        query += " AND timestamp LIKE ?"
        params.append(f"{date_filter}%")
    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_protocol_count(date_filter=None):
    conn = get_db()
    query = "SELECT COUNT(*) FROM protocols WHERE status='completed'"
    params = []
    if date_filter:
        query += " AND timestamp LIKE ?"
        params.append(f"{date_filter}%")
    count = conn.execute(query, params).fetchone()[0]
    conn.close()
    return count

def get_today_count():
    today = datetime.now().strftime("%Y-%m-%d")
    return get_protocol_count(today)

def get_system_logs(limit=100):
    conn = get_db()
    rows = conn.execute("SELECT * FROM system_log ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

init_db()
