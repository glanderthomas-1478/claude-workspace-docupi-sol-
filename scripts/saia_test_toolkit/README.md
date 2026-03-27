# DocuPi 3000 - SAIA PCD2.M5 Test-Toolkit

Testet die Kommunikation zwischen Mac/Raspberry Pi und der SAIA PCD2.M5 SPS im Sterilisator.

## Was du brauchst

- Mac oder Raspberry Pi
- USB-A zu USB-B Kabel (Druckerkabel) für USB-Test
- Ethernet-Kabel für LAN-Test
- Zugang zur SAIA PCD2.M5 im Sterilisator

## Setup

**macOS:**
```bash
chmod +x setup_mac.sh
./setup_mac.sh
```

**Raspberry Pi:**
```bash
chmod +x setup_pi.sh
./setup_pi.sh
```

## Schnellstart

Alles auf einmal testen:
```bash
python3 run_all_tests.py
```

## Einzelne Scripts

### 1. USB-Erkennung (`01_usb_detect.py`)
Erkennt ob die SAIA als USB-Device registriert wird.
```bash
python3 01_usb_detect.py
```
→ Zeigt das Device (z.B. `/dev/tty.usbserial-1420` oder `/dev/ttyUSB0`)

### 2. S-Bus Test (`02_sbus_test.py`)
Testet S-Bus Kommunikation über USB-Serial.
```bash
python3 02_sbus_test.py --port /dev/ttyUSB0
python3 02_sbus_test.py --port /dev/tty.usbserial-1420 --baudrate 9600
python3 02_sbus_test.py --port /dev/ttyUSB0 --listen-only
```

### 3. S7 LAN Test (`03_s7_lan_test.py`)
Testet S7-Kommunikation über Ethernet mit python-snap7.
```bash
# Direkt mit IP:
python3 03_s7_lan_test.py --ip 192.168.0.1

# Subnetz scannen:
python3 03_s7_lan_test.py --scan 192.168.0

# Andere Rack/Slot Kombination:
python3 03_s7_lan_test.py --ip 192.168.0.1 --rack 0 --slot 0
```

### 4. Live-Monitor (`04_live_monitor.py`)
Zeigt Live-Prozessdaten im Terminal (braucht funktionierende S7/LAN-Verbindung).
```bash
python3 04_live_monitor.py --ip 192.168.0.1
python3 04_live_monitor.py --ip 192.168.0.1 --interval 0.5
```

## Ablauf vor Ort

1. **Vorbereitung**: Setup-Script ausführen (einmalig)
2. **USB-Kabel** in freien SAIA USB-Port stecken
3. **`python3 run_all_tests.py`** starten
4. Script führt durch alle Tests
5. **Ergebnisse** liegen in `logs/`

## IP-Adresse der SPS finden

Die IP steht in der Step 7 Hardware-Konfiguration. Falls nicht bekannt:
- `--scan` Option nutzt Ping-Scan
- Typische IPs bei Belimed: 192.168.0.x oder 10.0.0.x

## Logs

Alle Ergebnisse werden als JSON in `logs/` gespeichert:
- `usb_detect_result.json`
- `sbus_test_result.json`
- `s7_lan_test_result.json`
- `test_report.json`

## Sicherheit

Alle Scripts arbeiten **NUR LESEND** - es wird NICHTS auf die SPS geschrieben!
