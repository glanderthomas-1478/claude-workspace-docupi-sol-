#!/usr/bin/env python3
"""
Schlankes BLE-Diagnosewerkzeug fuer Geraete mit sehr kurzem Connection-Timeout
(z.B. BTMETER-Thermometer, das die Verbindung offenbar innerhalb weniger
Sekunden wieder trennt, vermutlich aggressives Power-Saving). Im Unterschied
zu ble_scan_thermometer.py NICHT alle Services der Reihe nach lesen/ausgeben,
sondern SOFORT nach dem Connect auf alle bekannten notify-Characteristics
abonnieren (harte UUIDs aus dem vorherigen Scan) und dann warten. Retried den
Connect-Versuch mehrfach, da das Zeitfenster fuer einen erfolgreichen Connect+
Service-Discovery offenbar knapp ist (Race gegen den Idle-Timeout des Geraets).

Usage: python3 ble_quick_notify.py <MAC> [versuche]
"""
import asyncio
import sys
from datetime import datetime

from bleak import BleakClient

NOTIFY_UUIDS = [
    "0000ffe2-0000-1000-8000-00805f9b34fb",
    "0000ffe3-0000-1000-8000-00805f9b34fb",
    "0000fee2-0000-1000-8000-00805f9b34fb",
    "0000fee3-0000-1000-8000-00805f9b34fb",
]


def hexdump(data: bytes) -> str:
    return " ".join(f"{b:02x}" for b in data)


def handler(characteristic, data: bytes):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{ts}] {characteristic.uuid}: {hexdump(data)}  (len={len(data)})  ascii={data!r}")


async def try_once(address: str, seconds: float) -> bool:
    async with BleakClient(address, timeout=5.0) as client:
        print(f"  Verbunden: {client.is_connected}")
        subscribed = []
        for uuid in NOTIFY_UUIDS:
            try:
                await client.start_notify(uuid, handler)
                subscribed.append(uuid)
                print(f"  abonniert: {uuid}")
            except Exception as e:
                print(f"  fehlgeschlagen: {uuid}: {e}")
        if not subscribed:
            return False
        print(f"  Warte {seconds:.0f}s auf Daten (jetzt Messung/Trigger am Geraet ausloesen) ...")
        for i in range(int(seconds)):
            if not client.is_connected:
                print(f"  Verbindung verloren nach {i}s.")
                return False
            await asyncio.sleep(1)
        return True


async def main(address: str, attempts: int, seconds: float = 20.0):
    for i in range(1, attempts + 1):
        print(f"--- Versuch {i}/{attempts} ---")
        try:
            ok = await try_once(address, seconds)
            if ok:
                print("Erfolgreich abgeschlossen.")
                return
        except Exception as e:
            print(f"  Fehler: {e}")
        await asyncio.sleep(1)
    print("Alle Versuche fehlgeschlagen.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 ble_quick_notify.py <MAC> [versuche]")
        sys.exit(1)
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    asyncio.run(main(sys.argv[1], n))
