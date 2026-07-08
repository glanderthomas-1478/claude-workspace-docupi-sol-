#!/usr/bin/env python3
"""
BLE-Diagnosewerkzeug fuer die Anbindung des BTMETER-Infrarot-Thermometers
(BT-1500APP oder aehnliches Modell, 30:1 Dual-Laser-Pyrometer, -50..1500C).

BTMETER veroeffentlicht kein SDK/Protokoll fuer die Bluetooth-Anbindung -
dieses Skript dient dazu, das GATT-Profil und das Datenformat empirisch zu
ermitteln, sobald das physische Geraet verfuegbar ist. Zwei Modi:

  Scan (ohne Argument):
      python3 ble_scan_thermometer.py
      Listet alle in Reichweite sichtbaren BLE-Geraete (Name, MAC, RSSI,
      Advertisement-Daten) - hilft, die MAC-Adresse des Thermometers zu
      identifizieren (Geraet dafuer einschalten und in Reichweite halten,
      ggf. Bluetooth-Pairing-Modus am Geraet aktivieren).

  Inspect (mit MAC-Adresse):
      python3 ble_scan_thermometer.py AA:BB:CC:DD:EE:FF
      Verbindet sich mit dem Geraet, listet alle GATT-Services/Characteristics
      (inkl. Eigenschaften read/write/notify/indicate), liest lesbare
      Characteristics einmalig aus und abonniert alle notify/indicate-fähigen
      Characteristics fuer 30 Sekunden - waehrenddessen am Geraet eine Messung
      ausloesen (Trigger druecken), um das Rohdatenformat einer Messung zu
      sehen (Hex-Dump jeder empfangenen Notification).

Voraussetzung: `python3-bleak` (bereits auf dem SOL-Pi installiert, 2026-07-08).
Laeuft auf dem Pi-Host (nicht im Docker-Container), da BLE direkten Zugriff
auf BlueZ/D-Bus braucht.
"""

import asyncio
import sys
from datetime import datetime

from bleak import BleakClient, BleakScanner


def hexdump(data: bytes) -> str:
    return " ".join(f"{b:02x}" for b in data)


async def scan(duration: float = 15.0):
    print(f"Scanne {duration:.0f}s nach BLE-Geraeten (Thermometer jetzt einschalten/in Reichweite halten)...\n")
    devices = await BleakScanner.discover(timeout=duration, return_adv=True)
    if not devices:
        print("Keine Geraete gefunden.")
        return
    for address, (device, adv) in devices.items():
        name = device.name or adv.local_name or "(kein Name)"
        print(f"{address}  RSSI={adv.rssi:>4}  Name={name!r}")
        if adv.manufacturer_data:
            for key, val in adv.manufacturer_data.items():
                print(f"    ManufacturerData[0x{key:04x}]: {hexdump(val)}")
        if adv.service_uuids:
            print(f"    Service-UUIDs: {adv.service_uuids}")
    print("\nGeraet identifiziert? Dann Skript mit der MAC-Adresse erneut aufrufen:")
    print("  python3 ble_scan_thermometer.py <MAC-ADRESSE>")


def notify_handler(characteristic, data: bytes):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{ts}] Notify von {characteristic.uuid}: {hexdump(data)}  (len={len(data)})")


async def inspect(address: str, notify_seconds: float = 30.0):
    print(f"Verbinde zu {address} ...")
    async with BleakClient(address) as client:
        print(f"Verbunden: {client.is_connected}\n")

        notify_chars = []
        for service in client.services:
            print(f"Service {service.uuid}  ({service.description})")
            for char in service.characteristics:
                props = ",".join(char.properties)
                print(f"  Characteristic {char.uuid}  [{props}]  ({char.description})")
                for desc in char.descriptors:
                    print(f"    Descriptor {desc.uuid}")

                if "read" in char.properties:
                    try:
                        val = await client.read_gatt_char(char.uuid)
                        print(f"    -> read: {hexdump(val)}  (len={len(val)})")
                    except Exception as e:
                        print(f"    -> read fehlgeschlagen: {e}")

                if "notify" in char.properties or "indicate" in char.properties:
                    notify_chars.append(char.uuid)

        if notify_chars:
            print(f"\nAbonniere {len(notify_chars)} notify/indicate-Characteristic(s) fuer {notify_seconds:.0f}s ...")
            print("Jetzt am Geraet eine Messung ausloesen (Trigger druecken)!\n")
            for uuid in notify_chars:
                try:
                    await client.start_notify(uuid, notify_handler)
                except Exception as e:
                    print(f"start_notify({uuid}) fehlgeschlagen: {e}")

            await asyncio.sleep(notify_seconds)

            for uuid in notify_chars:
                try:
                    await client.stop_notify(uuid)
                except Exception:
                    pass
        else:
            print("\nKeine notify/indicate-faehigen Characteristics gefunden.")

    print("\nFertig. Naechster Schritt: Rohdaten-Format oben analysieren und in ein neues")
    print("Modul (z.B. src/docucontrol/ble_thermometer.py) fuer die echte Anbindung giessen.")


def main():
    if len(sys.argv) > 1:
        asyncio.run(inspect(sys.argv[1]))
    else:
        asyncio.run(scan())


if __name__ == "__main__":
    main()
