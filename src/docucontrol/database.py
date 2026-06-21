import sqlite3
import os
from datetime import datetime
import re as _re

_CHARGE_RE    = _re.compile(r'Laufende\s+Nr\.?\s*:\s*0*(\d+)', _re.IGNORECASE)
_LFD_NR_RE    = _re.compile(r'Lfd\.Nr\.\s+(\d+)',              _re.IGNORECASE)
_PROG_RE      = _re.compile(r'Programm\s*[:\.]?\s*(.+)',        _re.IGNORECASE)

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
        CREATE TABLE IF NOT EXISTS charge_forms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocol_id INTEGER NOT NULL UNIQUE,
            form_data_json TEXT DEFAULT '{}',
            confirmed_at TEXT DEFAULT NULL,
            confirmed_by TEXT DEFAULT '',
            confirmed_initials TEXT DEFAULT '',
            preselected_program TEXT DEFAULT '',
            program_was_changed INTEGER DEFAULT 0,
            FOREIGN KEY (protocol_id) REFERENCES protocols(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_charge_forms_protocol ON charge_forms(protocol_id);
    """)
    conn.commit()
    conn.close()

def log_event(level, message):
    conn = get_db()
    conn.execute("INSERT INTO system_log (timestamp, level, message) VALUES (?, ?, ?)",
        (datetime.now().isoformat(), level, message))
    conn.commit()
    conn.close()

def save_protocol(raw_data, device_name="", status="received"):
    raw = raw_data or ''
    cm = _CHARGE_RE.search(raw)
    charge_nr_int = int(cm.group(1)) if cm else None
    if charge_nr_int is None:
        cm2 = _LFD_NR_RE.search(raw)
        charge_nr_int = int(cm2.group(1)) if cm2 else None
    pm = _PROG_RE.search(raw)
    program_val = pm.group(1).strip()[:60] if pm else None
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO protocols (timestamp, device_name, raw_data, status, charge_nr_int, program) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), device_name, raw_data, status, charge_nr_int, program_val))
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


# ─────────────────────────────────────────────────────────────
# AUTOKLAVENBUCH WORKFLOW — Pending Charges
# ─────────────────────────────────────────────────────────────

def get_pending_protocols():
    """Alle Chargen mit status='pending_form', neueste zuerst."""
    conn = get_db()
    rows = conn.execute(
        "SELECT p.*, cf.form_data_json, cf.confirmed_at, cf.preselected_program "
        "FROM protocols p "
        "LEFT JOIN charge_forms cf ON cf.protocol_id = p.id "
        "WHERE p.status = 'pending_form' ORDER BY p.timestamp DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pending_protocol(protocol_id):
    """Eine Charge mit status='pending_form' samt Formulardaten."""
    conn = get_db()
    row = conn.execute(
        "SELECT p.*, cf.form_data_json, cf.confirmed_at, cf.preselected_program "
        "FROM protocols p "
        "LEFT JOIN charge_forms cf ON cf.protocol_id = p.id "
        "WHERE p.id = ?", (protocol_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def save_form_draft(protocol_id, form_data_json, preselected_program=""):
    """Zwischenspeichert Formulardaten (Autosave, kein Confirm)."""
    conn = get_db()
    conn.execute(
        "INSERT INTO charge_forms (protocol_id, form_data_json, preselected_program) "
        "VALUES (?, ?, ?) ON CONFLICT(protocol_id) DO UPDATE SET "
        "form_data_json=excluded.form_data_json, "
        "preselected_program=COALESCE(NULLIF(excluded.preselected_program,''), charge_forms.preselected_program)",
        (protocol_id, form_data_json, preselected_program)
    )
    conn.commit()
    conn.close()


def confirm_form(protocol_id, form_data_json, confirmed_by, confirmed_initials, confirmed_at,
                 preselected_program="", program_was_changed=0):
    """Bestätigt Formular — setzt status auf form_confirmed."""
    conn = get_db()
    conn.execute(
        "INSERT INTO charge_forms (protocol_id, form_data_json, confirmed_at, confirmed_by, "
        "confirmed_initials, preselected_program, program_was_changed) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(protocol_id) DO UPDATE SET "
        "form_data_json=excluded.form_data_json, "
        "confirmed_at=excluded.confirmed_at, "
        "confirmed_by=excluded.confirmed_by, "
        "confirmed_initials=excluded.confirmed_initials, "
        "preselected_program=excluded.preselected_program, "
        "program_was_changed=excluded.program_was_changed",
        (protocol_id, form_data_json, confirmed_at, confirmed_by,
         confirmed_initials, preselected_program, program_was_changed)
    )
    conn.execute(
        "UPDATE protocols SET status='form_confirmed' WHERE id=?", (protocol_id,)
    )
    conn.commit()
    conn.close()


def discard_pending(protocol_id):
    """Verwirft eine ausstehende Charge (status → skipped, kein PDF)."""
    conn = get_db()
    conn.execute("UPDATE protocols SET status='skipped' WHERE id=? AND status='pending_form'",
                 (protocol_id,))
    conn.commit()
    conn.close()


def set_pdf_failed(protocol_id):
    conn = get_db()
    conn.execute("UPDATE protocols SET status='pdf_failed' WHERE id=? AND status='form_confirmed'",
                 (protocol_id,))
    conn.commit()
    conn.close()


def get_form_confirmed_protocols():
    """Gibt alle Chargen zurück, bei denen das PDF noch erzeugt werden muss (inkl. Retry)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT p.*, cf.form_data_json, cf.confirmed_by, cf.confirmed_at, cf.preselected_program "
        "FROM protocols p LEFT JOIN charge_forms cf ON cf.protocol_id = p.id "
        "WHERE p.status IN ('form_confirmed', 'pdf_failed') ORDER BY p.timestamp DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


try:
    init_db()
except Exception:
    pass
