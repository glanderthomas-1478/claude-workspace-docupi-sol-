#!/usr/bin/env python3
"""
USB-Diagnosewerkzeug fuer die Anbindung des Testo 835-T1 Infrarot-Thermometers.

Wichtiger Unterschied zum BTMETER (siehe scripts/ble_scan_thermometer.py): der
Testo 835-T1 hat KEIN Bluetooth, nur USB. Testo bietet fuer Live-Werte-Abfrage
offiziell nur ein **Windows-only .NET-SDK** ("Toolbox", Teil von EasyClimate)
an - kein dokumentiertes offenes Protokoll gefunden (Stand 2026-07-08, Websuche
inkl. offiziellem Testo-GitHub-Beispielrepo). Es ist daher VORAB NICHT klar, ob
sich das Geraet ueberhaupt ohne Windows-Zwischenschritt oder aufwendiges
USB-Reverse-Engineering am Linux-Pi ansprechen laesst.

Dieses Skript sammelt die Fakten, die zur Einschaetzung noetig sind, sobald das
physische Geraet verfuegbar ist:

  Scan (ohne Argument):
      python3 usb_scan_thermometer.py
      Listet alle angeschlossenen USB-Geraete (lsusb) - hilft, das Testo-Geraet
      per Vendor/Product-Namen zu identifizieren (Geraet vorher per USB-Kabel
      anschliessen).

  Inspect (mit Vendor:Product-ID, Format wie in lsusb z.B. "1a86:7523"):
      python3 usb_scan_thermometer.py 1a86:7523
      Zeigt die vollstaendigen USB-Deskriptoren (Interfaces, Endpoints, Klasse)
      per pyusb. Die USB-Geraeteklasse verraet den moeglichen Integrationsweg:
        - CDC-ACM / "Communications" -> erscheint als /dev/ttyACM* oder
          /dev/ttyUSB* virtueller COM-Port, direkt per pyserial lesbar, OHNE
          Windows-SDK - guter Fall.
        - HID -> ueber Standard-HID-Reports lesbar (aehnlich USB-Tastatur/-Maus),
          Protokoll muss aber trotzdem empirisch ermittelt werden (Rohdaten
          mitschneiden waehrend am Geraet gemessen wird).
        - Vendor-spezifische Klasse (0xFF) -> vermutlich nur mit dem
          Windows-SDK oder per USB-Paketmitschnitt (Wireshark+usbmon, im
          Idealfall auf einem Windows-Rechner mit installierter EasyClimate-
          Software waehrend einer Messung) entschluesselbar - schwierigster Fall.

Voraussetzung: `python3-serial` + `python3-usb` (bereits auf dem SOL-Pi
installiert, 2026-07-08). Fuer den Inspect-Modus ggf. root/sudo noetig, falls
keine passende udev-Regel fuer das Geraet existiert.
"""

import subprocess
import sys


def scan():
    print("=== lsusb (alle angeschlossenen USB-Geraete) ===\n")
    try:
        out = subprocess.run(["lsusb"], capture_output=True, text=True, check=True)
        print(out.stdout)
    except Exception as e:
        print(f"lsusb fehlgeschlagen: {e}")
        return
    print("Testo-Geraet identifiziert (Vendor/Product-Name)? Dann Skript mit der")
    print("Vendor:Product-ID erneut aufrufen, z.B.:")
    print("  python3 usb_scan_thermometer.py 1a86:7523")


def inspect(vid_pid: str):
    try:
        vid_str, pid_str = vid_pid.split(":")
        vid, pid = int(vid_str, 16), int(pid_str, 16)
    except ValueError:
        print(f"Ungueltiges Format '{vid_pid}', erwartet z.B. '1a86:7523' (wie in lsusb).")
        sys.exit(1)

    try:
        import usb.core
        import usb.util
    except ImportError:
        print("pyusb nicht installiert (python3-usb fehlt).")
        sys.exit(1)

    dev = usb.core.find(idVendor=vid, idProduct=pid)
    if dev is None:
        print(f"Kein Geraet mit {vid_pid} gefunden (angeschlossen? sudo noetig?).")
        sys.exit(1)

    print(f"Geraet gefunden: {vid_pid}")
    try:
        print(f"  Hersteller: {usb.util.get_string(dev, dev.iManufacturer)}")
        print(f"  Produkt:    {usb.util.get_string(dev, dev.iProduct)}")
    except Exception:
        pass

    print(f"  bDeviceClass: 0x{dev.bDeviceClass:02x}")
    print(f"  bcdUSB: 0x{dev.bcdUSB:04x}")
    print()

    for cfg in dev:
        print(f"Configuration {cfg.bConfigurationValue}")
        for intf in cfg:
            cls = intf.bInterfaceClass
            cls_name = {
                0x02: "CDC (virtueller COM-Port) -> per pyserial lesbar!",
                0x03: "HID -> Standard-HID-Reports, Protokoll empirisch ermitteln",
                0x08: "Mass Storage",
                0xFF: "Vendor-spezifisch -> vermutlich nur mit Windows-SDK oder USB-Mitschnitt loesbar",
            }.get(cls, f"unbekannt (0x{cls:02x})")
            print(f"  Interface {intf.bInterfaceNumber} Alt {intf.bAlternateSetting}: "
                  f"Klasse 0x{cls:02x} = {cls_name}")
            for ep in intf:
                direction = "IN " if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN else "OUT"
                ep_type = usb.util.endpoint_type(ep.bmAttributes)
                print(f"    Endpoint 0x{ep.bEndpointAddress:02x} {direction}  "
                      f"Type={ep_type}  MaxPacketSize={ep.wMaxPacketSize}")

    print("\nFalls CDC-Interface gefunden: pruefen, ob /dev/ttyACM* oder /dev/ttyUSB*")
    print("auftaucht (dmesg | tail nach dem Anschliessen), dann einfach mit")
    print("pyserial verbinden (Baudrate variiert, haeufig 9600 oder 115200) und")
    print("waehrend einer Messung am Geraet die Rohbytes mitschneiden.")


def main():
    if len(sys.argv) > 1:
        inspect(sys.argv[1])
    else:
        scan()


if __name__ == "__main__":
    main()
