#!/usr/bin/env python3
"""
Patcht app.py auf dem Pi:
- api_protocols: echte SQL-Paginierung mit LIMIT/OFFSET
- api_protocols_programs: SELECT DISTINCT program statt raw_data-Scan
"""
import sys

APP_PATH = '/home/docucontrol/docupi/app.py'

with open(APP_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# ── Schritt 3: api_protocols ersetzen ────────────────────────────────────────

OLD_PROTOCOLS = """@app.route('/api/protocols')
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
    })"""

NEW_PROTOCOLS = """@app.route('/api/protocols')
def api_protocols():
    page     = max(1, int(request.args.get('page', 1)))
    per_page = min(max(1, int(request.args.get('per_page', 20))), 100)
    status_f    = request.args.get('status', '').strip()
    date_from   = request.args.get('date_from', '').strip()
    date_to     = request.args.get('date_to', '').strip()
    charge_from = request.args.get('charge_from', '').strip()
    charge_to   = request.args.get('charge_to', '').strip()
    program_f   = request.args.get('program', '').strip()
    sort_by  = request.args.get('sort_by', 'timestamp').strip()
    sort_dir = request.args.get('sort_dir', 'desc').strip().lower()

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

    if charge_from.isdigit():
        where_clauses.append("charge_nr_int >= ?")
        params.append(int(charge_from))
    if charge_to.isdigit():
        where_clauses.append("charge_nr_int <= ?")
        params.append(int(charge_to))
    if program_f:
        where_clauses.append("program = ?")
        params.append(program_f)

    where = ('WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''

    db = get_db()
    total = db.execute(f"SELECT COUNT(*) FROM protocols {where}", params).fetchone()[0]

    order_col = 'charge_nr_int' if sort_by == 'charge_nr' else 'timestamp'
    order_dir_sql = 'DESC' if sort_dir == 'desc' else 'ASC'
    offset = (page - 1) * per_page

    sql = (f"SELECT id, timestamp, device_name, raw_data, pdf_path, pdf_filename, file_size, status "
           f"FROM protocols {where} ORDER BY {order_col} {order_dir_sql} LIMIT ? OFFSET ?")
    rows = db.execute(sql, params + [per_page, offset]).fetchall()

    page_data = [_extract_protocol_fields(row) for row in rows]
    for p in page_data:
        del p['charge_nr_num']

    pages = max(1, (total + per_page - 1) // per_page)
    return jsonify({
        'total':     total,
        'page':      page,
        'per_page':  per_page,
        'pages':     pages,
        'protocols': page_data,
    })"""

if OLD_PROTOCOLS not in content:
    print("FEHLER: api_protocols-Block nicht gefunden. Abbruch.")
    sys.exit(1)

content = content.replace(OLD_PROTOCOLS, NEW_PROTOCOLS, 1)
print("api_protocols: ersetzt.")

# ── Schritt 4: api_protocols_programs ersetzen ───────────────────────────────

OLD_PROGRAMS = """@app.route('/api/protocols/programs')
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
    return jsonify(sorted(programs))"""

NEW_PROGRAMS = """@app.route('/api/protocols/programs')
def api_protocols_programs():
    db = get_db()
    rows = db.execute(
        "SELECT DISTINCT program FROM protocols WHERE program IS NOT NULL ORDER BY program"
    ).fetchall()
    return jsonify([row['program'] for row in rows])"""

if OLD_PROGRAMS not in content:
    print("FEHLER: api_protocols_programs-Block nicht gefunden. Abbruch.")
    sys.exit(1)

content = content.replace(OLD_PROGRAMS, NEW_PROGRAMS, 1)
print("api_protocols_programs: ersetzt.")

with open(APP_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print("app.py erfolgreich gepatcht.")
