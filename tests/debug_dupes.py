#!/usr/bin/env python3
"""Debug: find what causes 4x duplicate phases."""
import sys, re
sys.path.insert(0, "/home/belimed/docupi")

with open("/home/belimed/docupi/serial_logs/serial_2026-03-19.log", "r", errors="replace") as f:
    raw = f.read()

# Check if data appears multiple times in the file
count_vorvak = raw.count("0:02 1. Vorvakuum")
print(f"'0:02 1. Vorvakuum' appears {count_vorvak} times in raw log")

# Check log markers
markers = re.findall(r"=== PROTOKOLL .+? ===", raw)
print(f"Protocol markers: {len(markers)}")
for m in markers:
    print(f"  {m}")

# Check if stripping markers helps
cleaned = re.sub(r"=+\n=== .+? ===\n=+\n?", "", raw)
count_clean = cleaned.count("0:02 1. Vorvakuum")
print(f"\nAfter cleaning markers: '0:02 1. Vorvakuum' appears {count_clean} times")

# The serial log has protocol start/end markers AND the raw data
# The data appears in between markers. Let's check structure.
lines = raw.split("\n")
print(f"\nTotal lines in log: {len(lines)}")

# Count BELIMED headers
belimed_count = sum(1 for l in lines if "BELIMED CHARGEN" in l)
print(f"'BELIMED CHARGEN' headers: {belimed_count}")
