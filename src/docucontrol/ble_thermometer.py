"""
BLE-Anbindung fuer das BTMETER-Infrarot-Thermometer (Bluetooth-Modul "AiLink_DAE1").

Kein offizielles SDK/Protokoll vom Hersteller - Format per Reverse-Engineering ermittelt
(siehe CLAUDE.md, 2026-07-09). Kurzfassung:

- Das Geraet streamt kontinuierlich (~alle 350ms) Notify-Pakete auf GATT-Characteristic
  0000ffe2, sobald verbunden - kein Trigger am Geraet noetig.
- 17-Byte-Pakete enthalten die Zieltemperatur: Byte 9/10 (little-endian) ergeben einen
  Rohwert, der linear mit der angezeigten Temperatur korreliert.
- Das Geraet trennt die Verbindung von sich aus nach ca. 3-5s (vermutlich Power-Saving) -
  jeder Verbindungsversuch ist ein Race dagegen, daher der Retry-Mechanismus hier.
- Formel bislang nur an 2 sauberen Kalibrierpunkten (28.6C, 33.8C) + 1 Plausibilitaets-
  check ermittelt - fuer den vollen Einsatzbereich noch nicht fein kalibriert.

WICHTIG: Das Display des Geraets zeigt den zuletzt GETRIGGERTEN Messwert eingefroren an,
waehrend der BLE-Stream die aktuell LIVE anvisierte Temperatur sendet. Fuer den Techniker
bedeutet das: den Mess-Trigger am Geraet gedrueckt halten, waehrend die Pi-Messung laeuft,
damit Display und uebertragener Wert uebereinstimmen.
"""
import asyncio
import logging

from bleak import BleakClient

logger = logging.getLogger("docupi.ble_thermometer")

NOTIFY_UUID = "0000ffe2-0000-1000-8000-00805f9b34fb"

# Kalibrierung (2026-07-09, siehe CLAUDE.md) - vorlaeufig, bis mehr Referenzpunkte vorliegen.
_CAL_OFFSET = 57353.0
_CAL_SCALE = 10.77

# Plausibilitaetsgrenzen fuer die Zieltemperatur (Geraete-Spec: -50..1500C, hier bewusst
# enger gefasst, um korrupte/fehlinterpretierte Pakete zu verwerfen statt sie als Messwert
# durchzureichen).
_TEMP_MIN_C = -50.0
_TEMP_MAX_C = 300.0


def _parse_packet(data: bytes):
    """Extrahiert die Zieltemperatur aus einem 17-Byte-Notify-Paket, oder None wenn das
    Paket nicht dem bekannten Format entspricht bzw. der Wert unplausibel ist."""
    if len(data) != 17 or data[0] != 0xA7 or data[2] != 0x20 or data[3] != 0x0B or data[-1] != 0x7A:
        return None
    raw16 = data[9] | (data[10] << 8)
    temp_c = (raw16 - _CAL_OFFSET) / _CAL_SCALE
    if not (_TEMP_MIN_C <= temp_c <= _TEMP_MAX_C):
        return None
    return round(temp_c, 1)


async def _read_once(mac: str, connect_timeout: float, notify_timeout: float):
    result = {"temp": None}
    done = asyncio.Event()

    def handler(_characteristic, data: bytes):
        if result["temp"] is None:
            parsed = _parse_packet(bytes(data))
            if parsed is not None:
                result["temp"] = parsed
                done.set()

    async with BleakClient(mac, timeout=connect_timeout) as client:
        await client.start_notify(NOTIFY_UUID, handler)
        try:
            await asyncio.wait_for(done.wait(), timeout=notify_timeout)
        except asyncio.TimeoutError:
            pass
    return result["temp"]


async def _read_with_retries(mac: str, attempts: int, connect_timeout: float, notify_timeout: float):
    last_error = "Kein Verbindungsversuch moeglich"
    for i in range(1, attempts + 1):
        try:
            temp = await _read_once(mac, connect_timeout, notify_timeout)
            if temp is not None:
                return temp, None
            last_error = "Verbunden, aber keine gueltige Messung empfangen"
        except Exception as e:
            last_error = str(e) or type(e).__name__
            logger.info("BLE-Thermometer Versuch %d/%d fehlgeschlagen: %s", i, attempts, last_error)
    return None, last_error


def read_temperature(mac: str, attempts: int = 5, connect_timeout: float = 2.5, notify_timeout: float = 2.0):
    """Synchroner Einstiegspunkt fuer Flask-Routen. Liefert (temp_c, error) - genau eines
    von beiden ist None. Blockiert bis zu ca. attempts * (connect_timeout + notify_timeout)
    Sekunden (Default: ~22s worst case, typischer Erfolgsfall deutlich schneller)."""
    if not mac:
        return None, "Keine Bluetooth-MAC fuer den Temperatursensor konfiguriert"
    return asyncio.run(_read_with_retries(mac, attempts, connect_timeout, notify_timeout))
