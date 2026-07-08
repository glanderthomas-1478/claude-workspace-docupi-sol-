#!/usr/bin/env python3
"""
Simulation einer realistischen SOL-Charge gegen die laufende App auf dem Pi.

Testet den kompletten End-to-End-Ablauf bei realistischer Groessenordnung
(insbesondere PDF-Mehrseiten-Paginierung, die bei den bisherigen 1-4-Flaschen-
Tests nie ausgeloest wurde): Charge starten -> N Flaschen scannen (gemischt
OK/NOK) -> bestaetigen -> mit Unterschrift abschliessen -> PDF herunterladen.

Nutzung: python3 simulate_sol_charge.py [anzahl_flaschen] [--keep] [--all-ok] [--nok=N]
  --keep    Testdaten NICHT am Ende loeschen (Standard: wird aufgeraeumt)
  --all-ok  Alle Flaschen erzeugen einen OK-Wert, keine bewusste NOK-Streuung
  --nok=N   Exakt N zufaellig verteilte Flaschen erzeugen einen NOK-Wert (statt ~10% Zufallsstreuung)
"""

import base64
import io
import random
import sys
import time

import requests

BASE = "http://192.168.0.172:5000"


def make_charge_nr():
    """RAMSES-Chargennummer, 18-stellig (PR.128.07.9 Kap. 4.3): Standort-ID(3) +
    Abfuellnr./Tag(1) + Produktionsdatum TTMMJJ(6) + Produktcode Buchstabe+5 Ziffern(6) +
    Mitarbeiter-Nr. alphanumerisch(1) + Landeskennung(1)."""
    site_id = "075"
    fill_no = str(random.randint(0, 9))
    prod_date = time.strftime("%d%m%y")
    product_code = "X" + f"{random.randint(0, 99999):05d}"
    employee = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    country = "D"
    return f"{site_id}{fill_no}{prod_date}{product_code}{employee}{country}"


def make_bottle_code(i):
    """SOL-Flaschen-Barcode: 3 Buchstaben + 9 Ziffern (z. B. EFQ227010119)."""
    return f"BTL{i:09d}"


def make_signature_png():
    """Erzeugt eine simple, nicht-transparente Test-Unterschrift (Zickzack-Linie)."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        # Fallback: fixes 1x1-weisses PNG (falls Pillow lokal fehlt)
        return ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAA"
                "fFcSJAAAADUlEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
    img = Image.new("RGB", (300, 100), "white")
    d = ImageDraw.Draw(img)
    pts = [(20 + i * 40, 20 + (60 if i % 2 == 0 else 20)) for i in range(7)]
    d.line(pts, fill="black", width=4)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def main():
    n_bottles = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 45
    keep = "--keep" in sys.argv
    all_ok = "--all-ok" in sys.argv
    exact_nok = None
    for a in sys.argv:
        if a.startswith("--nok="):
            exact_nok = int(a.split("=", 1)[1])

    charge_nr = make_charge_nr()
    room_temp = 27.5
    print(f"=== Simulation: Charge {charge_nr}, {n_bottles} Flaschen ===\n")

    r = requests.post(f"{BASE}/api/sol/charges", json={
        "charge_nr": charge_nr, "room_temp": room_temp,
        "operator_name": "Simulierter Testbediener",
        "sensor_names": "Testo 835-T1 / Testo 608-H1",
    })
    r.raise_for_status()
    d = r.json()
    if not d.get("ok"):
        print("FEHLER beim Charge-Start:", d)
        sys.exit(1)
    charge_id = d["charge"]["id"]
    print(f"Charge gestartet (id={charge_id}), Referenztemp={room_temp}°C")

    nok_indices = set()
    if exact_nok is not None:
        nok_indices = set(random.sample(range(1, n_bottles + 1), min(exact_nok, n_bottles)))

    nok_count = 0
    for i in range(1, n_bottles + 1):
        # ~90% klar OK (Diff 6-16°C), ~10% bewusst NOK (Diff 1-4°C), ausser --all-ok/--nok= gesetzt
        is_nok = (i in nok_indices) if exact_nok is not None else (not all_ok and random.random() < 0.1)
        if is_nok:
            ir_temp = round(room_temp + random.uniform(1.0, 4.0), 1)
        else:
            ir_temp = round(room_temp + random.uniform(6.0, 16.0), 1)
        scan_code = make_bottle_code(i)
        r = requests.post(f"{BASE}/api/sol/charges/{charge_id}/bottles",
                           json={"scan_code": scan_code, "ir_temp": ir_temp})
        r.raise_for_status()
        bd = r.json()
        if not bd.get("ok"):
            print(f"  Flasche {i}: FEHLER {bd}")
            continue
        is_nok = bd["bottle"]["is_nok"]
        if is_nok:
            nok_count += 1
        tag = "NOK" if is_nok else "OK "
        if i % 10 == 0 or is_nok:
            print(f"  [{i:3d}/{n_bottles}] {scan_code}  {ir_temp:5.1f}°C  {tag}")

    print(f"\n{n_bottles} Flaschen erfasst, davon {nok_count} NOK.")

    signature = make_signature_png()
    r = requests.post(f"{BASE}/api/sol/charges/{charge_id}/close",
                       json={"confirmed": True, "signature": signature})
    r.raise_for_status()
    cd = r.json()
    if not cd.get("ok"):
        print("FEHLER beim Abschluss:", cd)
        sys.exit(1)
    pdf_filename = cd["pdf_filename"]
    print(f"Charge abgeschlossen. PDF: {pdf_filename}")

    pdf_resp = requests.get(f"{BASE}/sol/download/{charge_id}")
    pdf_resp.raise_for_status()
    out_path = f"./{pdf_filename}"
    with open(out_path, "wb") as f:
        f.write(pdf_resp.content)
    print(f"PDF heruntergeladen: {out_path} ({len(pdf_resp.content)} Bytes)")

    if not keep:
        stats_before = requests.get(f"{BASE}/api/sol/charges/stats").json()
        print(f"\nHinweis: Testdaten (charge_id={charge_id}) NICHT automatisch geloescht von diesem "
              f"Skript - Cleanup erfolgt separat auf dem Pi (DB + PDF-Datei + evtl. USB-Kopie).")
        print(f"Stats aktuell: {stats_before}")

    print(f"\n=== Fertig: charge_id={charge_id}, charge_nr={charge_nr}, pdf={pdf_filename} ===")


if __name__ == "__main__":
    main()
