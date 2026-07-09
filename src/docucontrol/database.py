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
        CREATE TABLE IF NOT EXISTS sol_charges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            charge_nr TEXT NOT NULL,
            started_at TEXT NOT NULL,
            closed_at TEXT DEFAULT NULL,
            room_temp REAL DEFAULT NULL,
            sensor_names TEXT DEFAULT '',
            operator_name TEXT DEFAULT '',
            lqk_name TEXT DEFAULT '',
            lqk_initials TEXT DEFAULT '',
            status TEXT DEFAULT 'open',
            pdf_path TEXT DEFAULT '',
            pdf_filename TEXT DEFAULT '',
            file_size INTEGER DEFAULT 0,
            process_status TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS sol_bottles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            charge_id INTEGER NOT NULL,
            seq_nr INTEGER NOT NULL,
            scan_code TEXT NOT NULL,
            scanned_at TEXT NOT NULL,
            ir_temp REAL DEFAULT NULL,
            visual_check_ok INTEGER DEFAULT NULL,
            residual_pressure_bar REAL DEFAULT NULL,
            residual_pressure_ok INTEGER DEFAULT NULL,
            is_nok INTEGER DEFAULT 0,
            FOREIGN KEY (charge_id) REFERENCES sol_charges(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_sol_charges_status ON sol_charges(status);
        CREATE INDEX IF NOT EXISTS idx_sol_charges_started ON sol_charges(started_at);
        CREATE INDEX IF NOT EXISTS idx_sol_bottles_charge ON sol_bottles(charge_id);
    """)
    # Idempotente Mini-Migration: neue Spalte fuer bereits existierende sol_charges-Tabellen
    # (CREATE TABLE IF NOT EXISTS greift nicht mehr, sobald die Tabelle einmal angelegt wurde).
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(sol_charges)").fetchall()}
    if "confirmed_signature" not in existing_cols:
        conn.execute("ALTER TABLE sol_charges ADD COLUMN confirmed_signature TEXT DEFAULT ''")
    if "process_status" not in existing_cols:
        conn.execute("ALTER TABLE sol_charges ADD COLUMN process_status TEXT DEFAULT ''")
    existing_bottle_cols = {row[1] for row in conn.execute("PRAGMA table_info(sol_bottles)").fetchall()}
    if "visual_check_ok" not in existing_bottle_cols:
        conn.execute("ALTER TABLE sol_bottles ADD COLUMN visual_check_ok INTEGER DEFAULT NULL")
    if "residual_pressure_bar" not in existing_bottle_cols:
        conn.execute("ALTER TABLE sol_bottles ADD COLUMN residual_pressure_bar REAL DEFAULT NULL")
    if "residual_pressure_ok" not in existing_bottle_cols:
        conn.execute("ALTER TABLE sol_bottles ADD COLUMN residual_pressure_ok INTEGER DEFAULT NULL")
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


# ─────────────────────────────────────────────────────────────
# SOL CHARGEN-WORKFLOW — Flaschen-Scan (Druckgasflaschen-Abfuellung)
# ─────────────────────────────────────────────────────────────

def create_sol_charge(charge_nr, room_temp, sensor_names, operator_name):
    """Startet eine neue offene Charge. Aufrufer muss vorher sicherstellen,
    dass keine andere Charge offen ist (get_open_sol_charge())."""
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO sol_charges (charge_nr, started_at, room_temp, sensor_names, operator_name, status) "
        "VALUES (?, ?, ?, ?, ?, 'open')",
        (charge_nr, datetime.now().isoformat(), room_temp, sensor_names, operator_name)
    )
    charge_id = cur.lastrowid
    conn.commit()
    conn.close()
    return charge_id


def update_sol_charge_start_fields(charge_id, room_temp, operator_name, sensor_names):
    """Traegt Referenztemperatur/Abfueller/Fuehler nachtraeglich in eine bereits offene Charge ein
    (2026-07-09, User-Vorgabe: Chargen-Barcode-Scan oeffnet die Charge sofort ohne diese Felder,
    sie werden danach ergaenzt). Nur uebergebene (nicht-None) Werte werden aktualisiert."""
    fields = []
    params = []
    if room_temp is not None:
        fields.append("room_temp=?"); params.append(room_temp)
    if operator_name is not None:
        fields.append("operator_name=?"); params.append(operator_name)
    if sensor_names is not None:
        fields.append("sensor_names=?"); params.append(sensor_names)
    if not fields:
        return
    conn = get_db()
    params.append(charge_id)
    conn.execute(f"UPDATE sol_charges SET {', '.join(fields)} WHERE id=?", params)
    conn.commit()
    conn.close()


def get_open_sol_charge():
    """Die aktuell offene Charge (es darf immer nur eine geben), oder None."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM sol_charges WHERE status='open' ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_sol_charge(charge_id):
    """Eine Charge (egal welcher Status) samt aller gescannten Flaschen."""
    conn = get_db()
    charge_row = conn.execute("SELECT * FROM sol_charges WHERE id=?", (charge_id,)).fetchone()
    if not charge_row:
        conn.close()
        return None
    charge = dict(charge_row)
    bottle_rows = conn.execute(
        "SELECT * FROM sol_bottles WHERE charge_id=? ORDER BY seq_nr ASC", (charge_id,)
    ).fetchall()
    conn.close()
    charge["bottles"] = [dict(r) for r in bottle_rows]
    return charge


def add_sol_bottle(charge_id, scan_code, ir_temp, visual_check_ok, residual_pressure_bar, is_nok):
    """Fuegt eine Flaschen-Messung hinzu. seq_nr wird automatisch fortlaufend vergeben."""
    conn = get_db()
    next_seq = conn.execute(
        "SELECT COALESCE(MAX(seq_nr), 0) + 1 FROM sol_bottles WHERE charge_id=?", (charge_id,)
    ).fetchone()[0]
    # visual_check_ok bleibt NULL (nicht 0!) solange es noch nicht gesetzt wurde - sonst wuerde
    # eine noch gar nicht durchgefuehrte Sichtpruefung faelschlich als "n.i.O." angezeigt, bevor
    # die Sammel-Sichtpruefung beim Chargen-Abschluss ueberhaupt erfasst wurde (2026-07-09-Bug).
    visual_val = None if visual_check_ok is None else (1 if visual_check_ok else 0)
    cur = conn.execute(
        "INSERT INTO sol_bottles (charge_id, seq_nr, scan_code, scanned_at, ir_temp, "
        "visual_check_ok, residual_pressure_bar, is_nok) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (charge_id, next_seq, scan_code, datetime.now().isoformat(), ir_temp,
         visual_val, residual_pressure_bar, 1 if is_nok else 0)
    )
    bottle_id = cur.lastrowid
    conn.commit()
    conn.close()
    return bottle_id, next_seq


def update_bottle_final_checks(bottle_id, visual_check_ok, residual_pressure_ok, is_nok):
    """Setzt die (Sammel-)Sichtpruefung + (Sammel-)Restdruck-Pruefung + neu berechneten NOK-Status
    einer Flasche - wird beim Chargen-Abschluss fuer jede Flasche der Charge aufgerufen
    (2026-07-09, User-Vorgabe: beide Pruefungen werden am Ende einmal fuer alle Flaschen erfasst,
    nicht mehr einzeln beim Scannen - echte Einzelmesswerte je Flasche folgen erst, sobald die
    jeweilige Datenquelle geklaert ist)."""
    conn = get_db()
    conn.execute("UPDATE sol_bottles SET visual_check_ok=?, residual_pressure_ok=?, is_nok=? WHERE id=?",
                 (1 if visual_check_ok else 0, 1 if residual_pressure_ok else 0, 1 if is_nok else 0, bottle_id))
    conn.commit()
    conn.close()


def bottle_code_exists_in_charge(charge_id, scan_code):
    """True wenn dieser Barcode/QR-Code in dieser Charge bereits gescannt wurde (fuer Duplikat-Warnung)."""
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) FROM sol_bottles WHERE charge_id=? AND scan_code=?", (charge_id, scan_code)
    ).fetchone()
    conn.close()
    return bool(row[0])


def delete_sol_bottle(bottle_id):
    """Loescht eine fehlerhafte Scan-Zeile (Korrektur). seq_nr der uebrigen Zeilen
    wird bewusst NICHT neu durchnummeriert, damit die Protokoll-Nr. nachvollziehbar bleibt."""
    conn = get_db()
    conn.execute("DELETE FROM sol_bottles WHERE id=?", (bottle_id,))
    conn.commit()
    conn.close()


def close_sol_charge(charge_id, confirmed_signature, process_status, pdf_path, pdf_filename, file_size):
    """Schliesst eine Charge ab. Bestaetigt wird ausschliesslich durch den Bediener/Abfueller
    (dessen Name schon bei create_sol_charge() erfasst wurde) per digitaler Unterschrift -
    kein separater LQK-Schritt (User-Entscheidung 2026-07-08). process_status haelt fest, ob der
    Bediener den Ablauf als ordnungsgemaess oder gestoert eingestuft hat (User-Vorgabe 2026-07-08)."""
    conn = get_db()
    conn.execute(
        "UPDATE sol_charges SET status='completed', closed_at=?, confirmed_signature=?, "
        "process_status=?, pdf_path=?, pdf_filename=?, file_size=? WHERE id=?",
        (datetime.now().isoformat(), confirmed_signature, process_status, pdf_path, pdf_filename, file_size, charge_id)
    )
    conn.commit()
    conn.close()


def get_sol_charge_pdf_path(charge_id):
    conn = get_db()
    row = conn.execute("SELECT pdf_path FROM sol_charges WHERE id=?", (charge_id,)).fetchone()
    conn.close()
    return row["pdf_path"] if row else None


def delete_sol_charge(charge_id):
    """Loescht eine Charge samt aller Flaschen. `PRAGMA foreign_keys` ist in dieser
    App nicht aktiviert, daher ON DELETE CASCADE wirkungslos - sol_bottles wird explizit
    zuerst geloescht. Die PDF-Datei auf der Platte muss der Aufrufer separat entfernen
    (pdf_path vorher per get_sol_charge_pdf_path() abfragen)."""
    conn = get_db()
    conn.execute("DELETE FROM sol_bottles WHERE charge_id=?", (charge_id,))
    conn.execute("DELETE FROM sol_charges WHERE id=?", (charge_id,))
    conn.commit()
    conn.close()


def _sol_charges_where(status_filter, date_from, date_to, charge_nr_search):
    where = []
    params = []
    if status_filter:
        where.append("status = ?")
        params.append(status_filter)
    if date_from:
        where.append("date(started_at) >= ?")
        params.append(date_from)
    if date_to:
        where.append("date(started_at) <= ?")
        params.append(date_to)
    if charge_nr_search:
        where.append("charge_nr LIKE ?")
        params.append(f"%{charge_nr_search}%")
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    return where_sql, params


def list_sol_charges(limit=20, offset=0, status_filter=None, date_from=None, date_to=None, charge_nr_search=None):
    conn = get_db()
    where_sql, params = _sol_charges_where(status_filter, date_from, date_to, charge_nr_search)
    rows = conn.execute(
        f"SELECT c.*, (SELECT COUNT(*) FROM sol_bottles b WHERE b.charge_id = c.id) AS bottle_count, "
        f"(SELECT COUNT(*) FROM sol_bottles b WHERE b.charge_id = c.id AND b.is_nok = 1) AS nok_count "
        f"FROM sol_charges c {where_sql} ORDER BY c.started_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset]
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_sol_charges(status_filter=None, date_from=None, date_to=None, charge_nr_search=None):
    conn = get_db()
    where_sql, params = _sol_charges_where(status_filter, date_from, date_to, charge_nr_search)
    count = conn.execute(f"SELECT COUNT(*) FROM sol_charges {where_sql}", params).fetchone()[0]
    conn.close()
    return count


def get_sol_charges_stats():
    """Kennzahlen fuer die Dashboard-Stat-Karten."""
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    total = conn.execute("SELECT COUNT(*) FROM sol_charges").fetchone()[0]
    today_count = conn.execute(
        "SELECT COUNT(*) FROM sol_charges WHERE date(started_at) = ?", (today,)
    ).fetchone()[0]
    month_count = conn.execute(
        "SELECT COUNT(*) FROM sol_charges WHERE started_at >= ?", (month_start,)
    ).fetchone()[0]
    total_bottles = conn.execute("SELECT COUNT(*) FROM sol_bottles").fetchone()[0]
    today_bottles = conn.execute(
        "SELECT COUNT(*) FROM sol_bottles WHERE date(scanned_at) = ?", (today,)
    ).fetchone()[0]
    conn.close()
    return {
        "total_charges": total,
        "today_charges": today_count,
        "month_charges": month_count,
        "total_bottles": total_bottles,
        "today_bottles": today_bottles,
    }


try:
    init_db()
except Exception:
    pass
