#!/usr/bin/env python3
"""Test parser with real serial log data."""
import sys, re
sys.path.insert(0, "/home/belimed/docupi")

from protocol_parser import parse_serial_protocol

# Read the actual serial log
with open("/home/belimed/docupi/serial_logs/serial_2026-03-19.log", "r", errors="replace") as f:
    raw = f.read()

# Strip the log markers
raw = re.sub(r"=+\n=== .+? ===\n=+\n?", "", raw)

d = parse_serial_protocol(raw)
print(f"Betreiber: {d['betreiber']}")
print(f"Maschinen-Typ: {d['maschinen_typ']}")
print(f"Maschinen-Nr: {d['maschinen_nr']}")
print(f"Charge (Laufende Nr): {d['charge_nr']}")
print(f"Programm: {d['program_name']}")
print(f"Cycle Start: {d['cycle_start']}")
print(f"Duration: {d['cycle_duration']}")
print(f"Phases: {len(d['phases'])}")
print(f"Result: {d['result']}")
print(f"Temp Min/Max: {d['temp_min']} / {d['temp_max']}")
print(f"F0: {d['f0_value']}")
print()
for p in d["phases"][:5]:
    t3 = f"{p['t3_c']:.1f}" if p.get('t3_c') else '-'
    print(f"  {p['time_offset']:>5s} {p['phase']:<22s} P2={p['p2_mbar']:>5d} T2={p['t2_c']:>6.1f} T3={t3:>6s}")
print("  ...")
for p in d["phases"][-3:]:
    t3 = f"{p['t3_c']:.1f}" if p.get('t3_c') else '-'
    print(f"  {p['time_offset']:>5s} {p['phase']:<22s} P2={p['p2_mbar']:>5d} T2={p['t2_c']:>6.1f} T3={t3:>6s}")

# Generate PDF
from pdf_generator import generate_pdf
from datetime import datetime
config = {
    "pdf": {
        "device_name": "MST 9-6-18",
        "header_text": "",
        "font_size": 8,
        "folder_structure": "flat",
        "output_dir": "/media/usbstick",
        "fallback_dir": "/home/belimed/docupi/data/pdfs",
        "filename_pattern": "{datum}_{zeit}_{geraet}_{charge}",
        "filename_separator": "_",
        "handwritten_fields": True,
    }
}
pdf_path, pdf_name, pdf_size = generate_pdf(raw, 21667, datetime.now(), config)
print(f"\nPDF: {pdf_name} ({pdf_size} bytes)")
print(f"Path: {pdf_path}")
