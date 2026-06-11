#!/usr/bin/env python3
"""
Einmalige Migration: Fügt charge_nr_int + program Spalten zur protocols-Tabelle hinzu
und befüllt sie aus bestehenden raw_data-Einträgen.
Idempotent — kann mehrfach ausgeführt werden.
"""
import sqlite3
import re
import sys

DB_PATH = "/home/docucontrol/docupi/data/docupi.db"

_CHARGE_RE = re.compile(r'Laufende\s+Nr\.?\s*:\s*0*(\d+)', re.IGNORECASE)
_PROG_RE   = re.compile(r'Programm\s*[:\.]?\s*(.+)',       re.IGNORECASE)

def main():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # Vorhandene Spalten prüfen
    cols = {r['name'] for r in conn.execute("PRAGMA table_info(protocols)").fetchall()}
    added = []

    if 'charge_nr_int' not in cols:
        conn.execute("ALTER TABLE protocols ADD COLUMN charge_nr_int INTEGER")
        added.append('charge_nr_int')
        print("Spalte charge_nr_int hinzugefügt.")
    else:
        print("Spalte charge_nr_int existiert bereits.")

    if 'program' not in cols:
        conn.execute("ALTER TABLE protocols ADD COLUMN program TEXT")
        added.append('program')
        print("Spalte program hinzugefügt.")
    else:
        print("Spalte program existiert bereits.")

    conn.commit()

    # Indizes anlegen
    conn.execute("CREATE INDEX IF NOT EXISTS idx_charge_nr_int ON protocols(charge_nr_int)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_program ON protocols(program)")
    conn.commit()
    print("Indizes sichergestellt.")

    # Alle Zeilen befüllen (auch bereits vorhandene, falls NULL)
    rows = conn.execute("SELECT id, raw_data FROM protocols WHERE charge_nr_int IS NULL OR program IS NULL").fetchall()
    print(f"{len(rows)} Zeilen zum Aktualisieren gefunden.")

    updated = 0
    no_charge = 0
    no_prog = 0

    for row in rows:
        raw = row['raw_data'] or ''
        cm = _CHARGE_RE.search(raw)
        charge_nr_int = int(cm.group(1)) if cm else None
        if not cm:
            no_charge += 1

        pm = _PROG_RE.search(raw)
        program_val = pm.group(1).strip()[:60] if pm else None
        if not pm:
            no_prog += 1

        conn.execute(
            "UPDATE protocols SET charge_nr_int=?, program=? WHERE id=?",
            (charge_nr_int, program_val, row['id'])
        )
        updated += 1

    conn.commit()
    conn.close()

    print(f"\nErgebnis:")
    print(f"  {updated} Zeilen aktualisiert")
    print(f"  {no_charge} ohne Charge-Nr. (NULL)")
    print(f"  {no_prog} ohne Programm (NULL)")
    print("Migration abgeschlossen.")

if __name__ == '__main__':
    main()
