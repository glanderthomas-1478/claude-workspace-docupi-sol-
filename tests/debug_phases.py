#!/usr/bin/env python3
"""Debug: check phase count and wide-char cleaning."""
import sys, re
sys.path.insert(0, "/home/belimed/docupi")
from protocol_parser import parse_serial_protocol

with open("/home/belimed/docupi/serial_logs/serial_2026-03-19.log", "r", errors="replace") as f:
    raw = f.read()
raw = re.sub(r"=+\n=== .+? ===\n=+\n?", "", raw)

d = parse_serial_protocol(raw)

# Show all unique phase entries
seen = set()
for p in d["phases"]:
    key = p["time_offset"] + " " + p["phase"]
    if key not in seen:
        seen.add(key)
        t3 = f"{p['t3_c']:.1f}" if p.get("t3_c") else "-"
        print(f"  {p['time_offset']:>5s} {p['phase']:<25s} P2={p['p2_mbar']:>5d} T2={p['t2_c']:>6.1f} T3={t3:>6s}")

print(f"\nUnique entries: {len(seen)}")
print(f"Total phases array: {len(d['phases'])}")

# Check for duplicates
from collections import Counter
times = [p["time_offset"] for p in d["phases"]]
dupes = [(t, c) for t, c in Counter(times).items() if c > 1]
if dupes:
    print(f"\nDuplicate timestamps: {dupes[:10]}")
