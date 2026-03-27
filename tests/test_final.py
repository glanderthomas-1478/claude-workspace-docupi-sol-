#!/usr/bin/env python3
import sys
sys.path.insert(0, "/home/belimed/docupi")
from protocol_parser import parse_serial_protocol
from pdf_generator import generate_pdf
from datetime import datetime

with open("/home/belimed/docupi/serial_logs/serial_2026-03-19.log", "r", errors="replace") as f:
    raw = f.read()

d = parse_serial_protocol(raw)
print(f"Start: {d['cycle_start']}  Ende: {d['cycle_end']}  Dauer: {d['cycle_duration']}")
print(f"Betreiber: {d['betreiber']} / {d['abteilung']}")
print(f"Maschine: {d['maschinen_typ']} Nr:{d['maschinen_nr']}")
print(f"Phases: {len(d['phases'])}")

config = {
    "pdf": {
        "device_name": "MST 9-6-18",
        "device_alias": "Steri 1",
        "header_text": "",
        "font_size": 8,
        "folder_structure": "flat",
        "output_dir": "/media/usbstick",
        "fallback_dir": "/home/belimed/docupi/data/pdfs",
        "filename_pattern": "{datum}_{zeit}_{geraet}_{charge}",
        "filename_separator": "_",
        "handwritten_fields": True,
        "notfall_rows": 18,
    }
}

pdf_path, pdf_name, pdf_size = generate_pdf(raw, 21667, datetime.now(), config)
print(f"\nPDF: {pdf_name} ({pdf_size} bytes)")
