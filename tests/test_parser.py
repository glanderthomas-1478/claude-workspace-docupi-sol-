#!/usr/bin/env python3
"""Test the protocol parser + chart generator with simulated sterilizer data."""

import sys
sys.path.insert(0, "/home/belimed/docupi")

from protocol_parser import parse_serial_protocol
from chart_generator import generate_trend_chart

test_data = """
                              50.8
0:02 1. Vorvakuum    1034  46.0
                              52.1
0:30 1. Vorvakuum     680  48.3
                              55.0
1:15 1. Vorvakuum     320  52.1
                              58.2
2:00 2. Dampfeinlass   47  65.4
                              72.1
3:30 2. Dampfeinlass  1200  95.2
                              98.5
5:00 3. Vorvakuum     120  88.3
                              90.1
7:00 4. Dampfeinlass  1050 110.5
                             115.2
9:00 5. Sterilisation 2100 134.2
                             134.8
15:00 5. Sterilisation 2100 134.5
                             134.9
20:00 5. Sterilisation 2100 134.3
                             134.7
25:00 6. Entlueftung   950  98.2
                             100.1
28:00 7. Trocknung     200  72.5
                              75.3
32:00 Programm Ende    984  55.1
"""

d = parse_serial_protocol(test_data)
print(f"Phases found: {len(d['phases'])}")
print(f"Duration: {d['cycle_duration']}")
print()

for p in d["phases"]:
    t3 = f"{p['t3_c']:.1f}" if p.get("t3_c") else "-"
    print(f"  {p['time_offset']:>5s}  {p['phase']:<22s}  P2={p['p2_mbar']:>5d}  T2={p['t2_c']:>6.1f}  T3={t3:>6s}")

print()

# Test chart generation
chart_path = generate_trend_chart(d["phases"], "/tmp/test_chart.png")
if chart_path:
    import os
    print(f"Chart: {chart_path} ({os.path.getsize(chart_path)} bytes)")
else:
    print("Chart: FAILED")

# Test PDF generation
from pdf_generator import generate_pdf
from datetime import datetime

class FakeConfig:
    pass

config = {
    "pdf": {
        "device_name": "MST 9-6-6",
        "header_text": "DocuPi Test",
        "font_size": 8,
        "folder_structure": "flat",
        "output_dir": "/media/usbstick",
        "fallback_dir": "/home/belimed/docupi/data/pdfs",
    }
}

pdf_path, pdf_name, pdf_size = generate_pdf(test_data, 99999, datetime.now(), config)
print(f"PDF: {pdf_name} ({pdf_size} bytes)")
print(f"Path: {pdf_path}")
