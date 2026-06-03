"""
Diesen Code in app.py einfügen.

1. Context Processor: inject_tcp_status() — nach den bestehenden @app.context_processor-Definitionen
2. API-Endpunkte: /api/protocols und /api/protocols/programs — vor if __name__ == '__main__'

Voraussetzungen:
- get_capture_status() aus tcp_print_capture.py muss importiert sein
- get_db() muss wie im restlichen app.py verfügbar sein (Flask g, sqlite3, oder anderes Muster)
- jsonify, request müssen importiert sein (sind sie bereits)
"""

import re as _re

# ─────────────────────────────────────────────────────────────
# 1. Context Processor — tcp_connected für alle Templates
# ─────────────────────────────────────────────────────────────

@app.context_processor
def inject_tcp_status():
    try:
        status = get_capture_status()
        return {'tcp_connected': bool(status.get('enabled', False))}
    except Exception:
        return {'tcp_connected': False}


# ─────────────────────────────────────────────────────────────
# 2. GET /api/protocols
#    Query-Params:
#      page (default 1), per_page (default 20, max 100)
#      status: 'Bestanden' | 'Fehlgeschlagen' | '' (alle)
#      date_from, date_to: YYYY-MM-DD
#      charge_from, charge_to: int (Laufende Nr.)
#      sort_by: 'timestamp' | 'charge_nr'  (default timestamp)
#      sort_dir: 'asc' | 'desc'            (default desc)
#    Response:
#      { total, page, per_page, pages, protocols: [...] }
# ─────────────────────────────────────────────────────────────

_CHARGE_RE = _re.compile(r'Laufende\s+Nr[\.:]?\s*0*(\d+)', _re.IGNORECASE)
_PROG_RE   = _re.compile(r'Programm\s*[:\.]?\s*(.+)',       _re.IGNORECASE)
_START_RE  = _re.compile(r'Beginn\s*[:\.]?\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', _re.IGNORECASE)
_END_RE    = _re.compile(r'Ende\s*[:\.]?\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})',   _re.IGNORECASE)


def _extract_protocol_fields(row):
    """Extrahiert Charge-Nr., Programm und Dauer aus raw_data per Regex."""
    raw = row['raw_data'] or ''

    cm = _CHARGE_RE.search(raw)
    charge_nr_num = int(cm.group(1)) if cm else None
    charge_nr = ('CH0' + cm.group(1)) if cm else ''

    pm = _PROG_RE.search(raw)
    prog = pm.group(1).strip()[:60] if pm else ''

    # Dauer: optional, aus Beginn/Ende berechnen
    duration = ''
    try:
        sm = _START_RE.search(raw)
        em = _END_RE.search(raw)
        if sm and em:
            from datetime import datetime
            start_dt = datetime.strptime(sm.group(1), '%Y-%m-%d %H:%M')
            end_dt   = datetime.strptime(em.group(1), '%Y-%m-%d %H:%M')
            delta = int((end_dt - start_dt).total_seconds())
            if delta > 0:
                duration = '{:02d}:{:02d}:{:02d}'.format(delta // 3600, (delta % 3600) // 60, delta % 60)
    except Exception:
        pass

    row_status = 'Bestanden' if row['status'] == 'completed' else 'Fehlgeschlagen'

    return {
        'id':           row['id'],
        'charge_nr':    charge_nr,
        'charge_nr_num': charge_nr_num or 0,
        'timestamp':    row['timestamp'],
        'program':      prog,
        'duration':     duration,
        'status':       row_status,
        'pdf_filename': row['pdf_filename'] or '',
    }


@app.route('/api/protocols')
def api_protocols():
    page     = max(1, int(request.args.get('page', 1)))
    per_page = min(max(1, int(request.args.get('per_page', 20))), 100)
    status_f = request.args.get('status', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to   = request.args.get('date_to', '').strip()
    charge_from = request.args.get('charge_from', '').strip()
    charge_to   = request.args.get('charge_to', '').strip()
    program_f   = request.args.get('program', '').strip()
    sort_by  = request.args.get('sort_by', 'timestamp').strip()
    sort_dir = request.args.get('sort_dir', 'desc').strip().lower()

    # DB-Abfrage mit einfachen Filtern
    where_clauses = []
    params = []

    if status_f == 'Bestanden':
        where_clauses.append("status = 'completed'")
    elif status_f == 'Fehlgeschlagen':
        where_clauses.append("(status IS NULL OR status != 'completed')")

    if date_from:
        where_clauses.append("date(timestamp) >= ?")
        params.append(date_from)
    if date_to:
        where_clauses.append("date(timestamp) <= ?")
        params.append(date_to)

    where = ('WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''
    sql = f"SELECT id, timestamp, device_name, raw_data, pdf_path, pdf_filename, file_size, status FROM protocols {where} ORDER BY timestamp DESC"

    db = get_db()
    rows = db.execute(sql, params).fetchall()

    # Felder extrahieren + Charge-Nummer-Filter in Python
    result = []
    cf_int = int(charge_from) if charge_from.isdigit() else None
    ct_int = int(charge_to)   if charge_to.isdigit()   else None

    for row in rows:
        rec = _extract_protocol_fields(row)
        if cf_int is not None and rec['charge_nr_num'] < cf_int:
            continue
        if ct_int is not None and rec['charge_nr_num'] > ct_int:
            continue
        if program_f and rec['program'] != program_f:
            continue
        result.append(rec)

    # Sortierung
    if sort_by == 'charge_nr':
        result.sort(key=lambda x: x['charge_nr_num'], reverse=(sort_dir == 'desc'))
    elif sort_dir == 'asc':
        result.reverse()  # war DESC aus DB, umkehren für ASC

    total = len(result)
    pages = max(1, (total + per_page - 1) // per_page)
    start = (page - 1) * per_page
    page_data = result[start:start + per_page]

    for p in page_data:
        del p['charge_nr_num']

    return jsonify({
        'total':     total,
        'page':      page,
        'per_page':  per_page,
        'pages':     pages,
        'protocols': page_data,
    })


# ─────────────────────────────────────────────────────────────
# 3. GET /api/protocols/programs
#    Gibt distinct Programmnamen aus raw_data zurück (für Filter-Select).
# ─────────────────────────────────────────────────────────────

@app.route('/api/protocols/programs')
def api_protocols_programs():
    db = get_db()
    rows = db.execute("SELECT raw_data FROM protocols WHERE raw_data IS NOT NULL").fetchall()
    programs = set()
    for row in rows:
        m = _PROG_RE.search(row['raw_data'] or '')
        if m:
            prog = m.group(1).strip()[:60]
            if prog:
                programs.add(prog)
    return jsonify(sorted(programs))
