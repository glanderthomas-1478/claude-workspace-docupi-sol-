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

Hintergrundverbindung (2026-07-10): ein Verbindungsaufbau pro Messung (siehe read_temperature)
dauert mehrere Sekunden und war fuer den Scan-Ablauf (eine Messung pro Flasche) zu langsam.
start_background()/stop_background() halten stattdessen waehrend einer offenen Charge
kontinuierlich eine Verbindung zum Geraet aufrecht (reconnected sofort wieder, sobald es sich
von selbst trennt) und cachen die zuletzt empfangene Temperatur - eine einzelne Messanfrage
(measure_with_background) liest dann nur noch aus diesem Cache statt selbst neu zu verbinden.
"""
import asyncio
import logging
import threading
import time

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
    """Synchroner Einstiegspunkt fuer Flask-Routen (Einzelmessung ohne Hintergrundverbindung).
    Liefert (temp_c, error) - genau eines von beiden ist None. Blockiert bis zu ca.
    attempts * (connect_timeout + notify_timeout) Sekunden (Default: ~22s worst case). Wird nur
    noch als Fallback genutzt, wenn keine Hintergrundverbindung laeuft - siehe
    measure_with_background()."""
    if not mac:
        return None, "Keine Bluetooth-MAC fuer den Temperatursensor konfiguriert"
    return asyncio.run(_read_with_retries(mac, attempts, connect_timeout, notify_timeout))


# ── Hintergrundverbindung (haelt waehrend einer offenen Charge dauerhaft Verbindung) ──────────

_bg_lock = threading.RLock()
_bg_thread = None
_bg_stop_event = None
_bg_mac = None
_bg_cache_temp = None
_bg_cache_ts = 0.0


def _bg_set_cache(temp_c):
    global _bg_cache_temp, _bg_cache_ts
    _bg_cache_temp = temp_c
    _bg_cache_ts = time.time()


def get_cached_temperature(max_age: float = 1.5):
    """Letzte per Hintergrundverbindung empfangene Temperatur, oder None wenn keine
    vorhanden bzw. aelter als max_age Sekunden (Geraet sendet alle ~350ms, solange verbunden)."""
    if _bg_cache_temp is None:
        return None
    if time.time() - _bg_cache_ts > max_age:
        return None
    return _bg_cache_temp


async def _bg_loop(mac: str, stop_event: threading.Event):
    while not stop_event.is_set():
        try:
            async with BleakClient(mac, timeout=3.0) as client:
                def handler(_characteristic, data: bytes):
                    parsed = _parse_packet(bytes(data))
                    if parsed is not None:
                        _bg_set_cache(parsed)

                await client.start_notify(NOTIFY_UUID, handler)
                # Verbunden bleiben, bis das Geraet sich von selbst trennt (~3-5s, Power-Saving)
                # oder ein Stop angefordert wird - dann sofort neu verbinden.
                while client.is_connected and not stop_event.is_set():
                    await asyncio.sleep(0.2)
        except Exception as e:
            logger.info("BLE-Hintergrundverbindung (Thermometer) getrennt/fehlgeschlagen: %s: %s",
                        type(e).__name__, e or "(keine Fehlermeldung)")
        if not stop_event.is_set():
            await asyncio.sleep(0.1)


def _bg_run(mac: str, stop_event: threading.Event):
    asyncio.run(_bg_loop(mac, stop_event))


def start_background(mac: str):
    """Startet (idempotent) eine dauerhafte Hintergrund-Verbindung zum Thermometer. Ohne
    Wirkung, wenn fuer dieselbe MAC bereits eine laeuft. Gedacht fuer die Dauer einer offenen
    SOL-Charge (siehe app.py: charge start/close, Config-/Toggle-Aenderungen)."""
    global _bg_thread, _bg_stop_event, _bg_mac
    if not mac:
        return
    with _bg_lock:
        if _bg_thread is not None and _bg_thread.is_alive() and _bg_mac == mac:
            return
        stop_background()
        _bg_mac = mac
        _bg_stop_event = threading.Event()
        _bg_cache_temp_reset()
        _bg_thread = threading.Thread(target=_bg_run, args=(mac, _bg_stop_event), daemon=True)
        _bg_thread.start()
        logger.info("BLE-Hintergrundverbindung (Thermometer) gestartet fuer %s", mac)


def _bg_cache_temp_reset():
    global _bg_cache_temp, _bg_cache_ts
    _bg_cache_temp = None
    _bg_cache_ts = 0.0


def stop_background():
    """Stoppt eine laufende Hintergrundverbindung (falls vorhanden). Ohne Wirkung, wenn keine
    laeuft."""
    global _bg_thread, _bg_stop_event, _bg_mac
    with _bg_lock:
        if _bg_stop_event is not None:
            _bg_stop_event.set()
        if _bg_thread is not None:
            _bg_thread.join(timeout=5.0)
            logger.info("BLE-Hintergrundverbindung (Thermometer) gestoppt")
        _bg_thread = None
        _bg_stop_event = None
        _bg_mac = None
        _bg_cache_temp_reset()


def measure_with_background(mac: str, min_hold: float = 2.0, wait_max: float = 6.0, poll_interval: float = 0.1):
    """Liefert (temp_c, error) aus dem Hintergrund-Cache statt selbst neu zu verbinden.

    WICHTIG: ignoriert absichtlich einen bereits VOR diesem Aufruf im Cache liegenden Wert (der
    kann von vor dem Scan stammen, also bevor der Techniker das Thermometer ueberhaupt auf die
    Flasche gerichtet/den Trigger gedrueckt hat) und wartet mindestens min_hold Sekunden auf
    einen NEUEN, erst waehrend dieser Messzeit eingetroffenen Wert - das gibt dem Techniker Zeit
    zum Anvisieren+Trigger-Druecken (siehe Hinweistext "Trigger gedrueckt halten" in der UI).
    Danach bis zu wait_max Sekunden Sicherheitsmarge, falls die Hintergrundverbindung gerade neu
    aufbaut. Deutlich schneller als das alte read_temperature() (kein Verbindungsaufbau mehr pro
    Messung), aber nicht mehr sofort - der Mindest-Wartezeit ist bewusst so gewollt."""
    start_background(mac)
    call_start = time.time()
    deadline = call_start + wait_max
    hold_until = call_start + min_hold
    fresh_temp = None
    while time.time() < deadline:
        temp, ts = _bg_cache_temp, _bg_cache_ts
        if temp is not None and ts > call_start:
            fresh_temp = temp
        if time.time() >= hold_until and fresh_temp is not None:
            return fresh_temp, None
        time.sleep(poll_interval)
    if fresh_temp is not None:
        return fresh_temp, None
    return None, "Keine Messung waehrend der Messzeit empfangen (Thermometer nicht in Reichweite oder Trigger nicht gedrueckt)"
