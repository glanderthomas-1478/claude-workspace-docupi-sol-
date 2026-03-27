# DocuPi 3000 v2 - Wissensbasis & Erkenntnisse

Stand: 25.03.2026

---

## 1. Projektbeschreibung

Der DocuPi 3000 ist ein Raspberry Pi-basiertes System, das Daten von einem Sterilisator (Belimed MST-H10) empfaengt und daraus KRINKO-konforme Chargenprotokolle erzeugt. Die SPS im Sterilisator ist eine **SAIA PCD2.M5540** mit Step-7-Programmierung.

Ziel von v2: Direkte S7-Kommunikation ueber LAN statt serieller Schnittstelle, um alle Prozessdaten in Echtzeit zu lesen und Chargenprotokolle automatisch zu generieren.

---

## 2. Hardware-Setup

### 2.1 SPS (Steuerung)

- **Typ:** SAIA PCD2.M5540
- **USB-Seriennummer:** PCD2M5540 C3E17CA0000
- **USB VID/PID:** 5007 (0x138F) / 2 (0x0002)
- **Hersteller:** Saia-Burgess Controls
- **Programmierung:** Step 7 (S7-kompatibel)
- **SPS-Projekt:** MST-H10_TS16_Hupfer.zip (Step 7 Projekt im Ordner "SPS Projekt")
- **Firmware-Version (aus Chargenprotokoll):** PR: 07.03.2018 SW: 103

### 2.2 Sterilisator

- **Typ:** Belimed MST 9-6-18 HS2 (Dampfsterilisator)
- **Maschinen-Nr:** 27163
- **Betreiber (Testumgebung):** Helios Krefeld, AEMP

### 2.3 Kommunikations-Interfaces

| Interface | Ergebnis | Details |
|-----------|----------|---------|
| **USB** | Nicht geeignet | USB-Port ist proprietaer (Vendor-Specific Device, SubClass=255, Protocol=255). Nur fuer PG5-Programmierung. Erscheint NICHT als serieller Port (/dev/tty.usb*). Kein Standard-USB-Serial-Chip (kein FTDI, CH340, CP210x). |
| **Ethernet/LAN** | Funktioniert! | S7-Protokoll ueber TCP/IP. Getestet am 25.03.2026 mit python-snap7. Rack=0, Slot=2. |
| **RS-232/RS-485** | Nicht getestet | PGU-Anschluss vorhanden, waere Alternative mit USB-RS485-Adapter |

### 2.4 Netzwerk-Konfiguration (Test vom 25.03.2026)

- **SPS IP-Adresse:** 10.230.11.212
- **Mac/Pi IP-Adresse:** 10.230.11.100 (statisch konfiguriert)
- **Subnetzmaske:** 255.255.255.0
- **Interface auf Mac:** en0 (Ethernet, 100baseTX)
- **Ping-Latenz:** ~1.8 - 13 ms (Durchschnitt 6.2 ms)

---

## 3. S7-Verbindung - Testergebnisse (25.03.2026)

### 3.1 Verbindungsparameter

- **Protokoll:** S7 (ISO on TCP, RFC 1006)
- **Bibliothek:** python-snap7 2.0.2 (snap7 1.4.2)
- **Rack:** 0
- **Slot:** 2
- **CPU Status:** S7CpuStatusRun (CPU laeuft)
- **CPU Info Detail:** Nicht verfuegbar ("Item not available" - SAIA gibt keine S7-typischen CPU-Infos)

### 3.2 Was funktioniert

| Bereich | Status | Details |
|---------|--------|---------|
| DB8 (Aktives Programm) | Gelesen (150 Bytes) | Programmname, Sollwerte, Rezeptparameter |
| DB7 (Stoerungen) | Gelesen (100 Bytes) | Aktive Stoerung, Anzahl Stoerungen |
| DB9 (Rezepturen) | Gelesen (50 Bytes) | Programmrezepturen |
| DB4 (Prozessdaten) | FEHLER | "Address out of range" bei 200 Bytes. DB4-Groesse muss angepasst werden. |
| Analoge Eingaenge (PIW) | Alle 8 gelesen | Rohwerte von Druck- und Temperatursensoren |
| Merker (MK) | Alle 6 gelesen | Prozessstatus, Stoerungen, Phasen |

### 3.3 DB4 - Bekanntes Problem

DB4 konnte nicht gelesen werden (200 Bytes angefordert, "Address out of range"). Die tatsaechliche DB4-Groesse auf dieser SPS ist kleiner als erwartet. Der Live-Monitor liest nur 30 Bytes aus DB4 und das funktioniert. Loesung: Schrittweise testen welche Groesse funktioniert (30, 50, 100 Bytes).

### 3.4 DB8 - String-Encoding Problem

Der Programmname wird als Unicode/UTF-16-BE gespeichert statt als S7-Standard ASCII:

```
Raw: 2828004100750066006800650069007a0065006e00200026002000560050005200200020...
Dekodiert: (( A u f h e i z e n   &   V P R
Erwartet: "Aufheizen & VPR"
```

Die ersten 2 Bytes (0x28, 0x28 = 40, 40) sind der S7-String-Header (max_len=40, actual_len=40), aber die Nutzdaten sind UTF-16-BE kodiert (jedes Zeichen 2 Bytes mit fuehrendem 0x00). Die `read_s7_string`-Funktion muss fuer UTF-16 angepasst werden:

```python
def read_s7_string_utf16(data, offset, max_len=40):
    """Liest S7 STRING der als UTF-16-BE gespeichert ist (SAIA-spezifisch)."""
    if offset + 2 > len(data):
        return ""
    declared_len = data[offset]
    actual_len = data[offset + 1]
    raw = data[offset + 2:offset + 2 + actual_len]
    # Pruefen ob UTF-16 (jedes zweite Byte ist 0x00)
    if len(raw) >= 4 and raw[0] == 0x00 and raw[2] == 0x00:
        try:
            return raw.decode('utf-16-be').strip('\x00').strip()
        except:
            pass
    # Fallback auf Latin-1
    return raw.decode('latin1', errors='replace').strip()
```

---

## 4. SPS-Adressliste (MST-H10)

### 4.1 Datenbausteine (DB)

| DB | Name | Beschreibung | Getestet |
|----|------|-------------|----------|
| DB4 | Status/Prozessdaten | Live-Daten: Chargennr, Phase, Temperaturen, Zeiten, F0-Wert, Leckrate | Fehler (Groesse anpassen) |
| DB7 | Stoerungen | Aktive Stoerungen und Historie | OK |
| DB8 | Aktives Programm | Programmname (STRING[40]) + UDT9 Programmparameter | OK |
| DB9 | Rezepturen | Array[1..20] von UDT9 - alle 20 Sterilisationsprogramme | OK (Anfang) |
| DB10 | Batch-Daten | Chargenprotokoll-Rohdaten | Noch nicht getestet |
| DB11 | Kurvenspeicher | Temperatur-/Druckverlauf fuer Grafik | Noch nicht getestet |

### 4.2 DB4 - Status/Prozessdaten (fuer Live-Monitoring)

| Offset | Typ | Variable | Beschreibung | Einheit |
|--------|-----|----------|-------------|---------|
| 0 | DINT | Lfd_Nr | Laufende Chargennummer | - |
| 4 | INT | Akt_Phas_Nr | Aktuelle Phasennummer | - |
| 6 | INT | SterZeitT1 | Sterilisationszeit Sensor T1 | Sek |
| 8 | INT | SterZeitT3 | Sterilisationszeit Sensor T3 | Sek |
| 10 | INT | SterZeitT4 | Sterilisationszeit Sensor T4 | Sek |
| 12 | INT | SterZeitT5 | Sterilisationszeit Sensor T5 | Sek |
| 14 | INT | Fo_Wert_T1 | F0-Wert Sensor T1 | x0.1 Min |
| 16 | INT | Fo_Wert_T3 | F0-Wert Sensor T3 | x0.1 Min |
| 18 | INT | Fo_Wert_T4 | F0-Wert Sensor T4 | x0.1 Min |
| 20 | INT | Fo_Wert_T5 | F0-Wert Sensor T5 | x0.1 Min |
| 22 | INT | MinSterTemp | Min. Sterilisiertemperatur | x0.1 C |
| 24 | INT | MaxSterTemp | Max. Sterilisiertemperatur | x0.1 C |
| 26 | INT | LkRateVPR | Leckrate Vakuumpruefung | x0.1 mbar/Min |

### 4.3 DB8 - Aktives Programm (UDT9 Programmparameter)

| Offset | Typ | Variable | Beschreibung | Faktor | Einheit |
|--------|-----|----------|-------------|--------|---------|
| 0 | STRING[40] | Programmname | Name des Programms (UTF-16-BE!) | - | - |
| 42 | INT | ProgNr | Programmnummer | 1 | - |
| 44 | INT | MantelVorBe | Manteltemp Vorbehandlung | 0.1 | C |
| 46 | INT | AnzEvakVorBe | Anz. Evakuierungen Vorbehandlung | 1 | - |
| 48 | INT | VorVa_1 | 1. Vorvakuum | 1 | mbar |
| 50 | INT | VorVa_2 | 2. Vorvakuum | 1 | mbar |
| 52 | INT | VorVa_3 | 3. Vorvakuum | 1 | mbar |
| 54 | INT | VorVa_4 | 4. Vorvakuum | 1 | mbar |
| 56 | INT | DruBegr_1 | 1. Druckbegrenzung | 1 | mbar |
| 68 | INT | BegSteri | SOLL Beginn Sterilisation | 0.1 | C |
| 70 | INT | MantelSteri | SOLL Manteltemp Sterilisation | 0.1 | C |
| 72 | INT | Einwirkzeit | SOLL Haltezeit | 0.1 | Min |
| 74 | INT | ArbTempEinw | SOLL Arbeitstemp Einwirken | 0.1 | C |
| 76 | INT | AlaTempMini | Alarmtemperatur Minimum | 0.1 | C |
| 78 | INT | AlaTempMaxi | Alarmtemperatur Maximum | 0.1 | C |

### 4.4 DB7 - Stoerungen

| Offset | Typ | Variable | Beschreibung |
|--------|-----|----------|-------------|
| 0 | INT | AktStoerung | Aktive Stoerungsnummer |
| 2 | INT | AnzStoerungen | Anzahl Stoerungen gesamt |

### 4.5 Analoge Eingaenge (Peripherie-Eingaenge PIW)

| Name | PIW-Adresse | Beschreibung | Einheit | Rohwert (Test) |
|------|-------------|-------------|---------|----------------|
| AE_P1 | 128 | Drucksensor P1 (Kammer) | mbar | 10971 |
| AE_P3 | 130 | Drucksensor P3 | mbar | 15974 |
| AE_P4 | 132 | Drucksensor P4 | mbar | 19789 |
| AE_T1 | 136 | Temperatursensor T1 (Kammer) | C | 3117 |
| AE_T3 | 138 | Temperatursensor T3 | C | 3080 |
| AE_T4 | 140 | Temperatursensor T4 | C | 2860 |
| AE_T5 | 142 | Temperatursensor T5 | C | 3024 |
| AE_T6 | 172 | Temperatursensor T6 | C | 0 |

Skalierung der Rohwerte: S7-Analogwerte sind typisch 0-27648 fuer 4-20mA.
Formel: `physikalischer_wert = (rohwert / 27648) * messbereich`
Genaue Skalierung muss pro Sensor aus der HW-Konfig ermittelt werden.

### 4.6 Merker & Trigger (fuer Prozesssteuerung DocuPi)

| Merker | Bit | Variable | Beschreibung | Wert (Test) |
|--------|-----|----------|-------------|-------------|
| M76.1 | 1 | PROZ_Sta_Ende | Prozess Start/Ende | AN |
| M76.2 | 2 | Programm_laeuft | Programm laeuft gerade | AUS |
| M51.0 | 0 | Stoerung_aktiv | Stoerung aktiv | AN |
| M132.2 | 2 | Steri_Phase | Sterilisationsphase aktiv | AUS |
| M133.0 | 0 | Phasenwechsel | Phasenwechsel erkannt | AUS |
| M211.0 | 0 | Prozessabbruch | Prozessabbruch erkannt | AUS |

---

## 5. Chargenprotokoll-Format (Referenz)

Aus dem bestehenden seriellen Chargenprotokoll (BD Test, Charge 021693):

```
BELIMED CHARGEN-DOKUMENTATION
Betreiber     : Helios Krefeld
Abteilung     : AEMP
Maschinen-Typ : 9-6-18 HS2    Nr:27163
Laufende Nr.  : 021693
Benutzer      : User
Programm      :  5: Bowie Dick Test
Version       : PR: 07.03.2018 SW: 103

Sollwerte     : Anz. Fraktionen         9
                Sterilisierzeit    3.5min
                Sterilisiertemp.  134.2 C
                Trocknungszeit     3.0min

Programmstart : 23.03.2026 / 07:34

 Zeit  Phase    Kammer       mbara  T2 C
  m:s           Luftnachweisg.      T3 C
-----------------------------------------
  0:01 1. Vorvakuum           1011   38.2
                                     31.1
  ...
 33:29 Programm Ende           966   48.5
                                     84.7

Min. Sterilisiertemp.             134.8 C
Max. Sterilisiertemp.             135.6 C
Zeit ueber Sollwert Kammer        3:30m:s
F0-Wert                          116.0min

PROGRAMM KORREKT BEENDET
```

Dieses Format muss der DocuPi v2 aus den S7-Daten nachbilden.

---

## 6. Software-Abhaengigkeiten

### 6.1 Auf dem Raspberry Pi

```
python3 >= 3.9
python-snap7 >= 2.0.2
libsnap7-dev (apt install)
```

### 6.2 Auf macOS (Entwicklung/Test)

```
python3 >= 3.9
python-snap7 >= 2.0.2
snap7 (brew install)
pyserial >= 3.5 (fuer USB-Tests)
```

---

## 7. Offene Punkte fuer v2

### 7.1 Kritisch (muss geloest werden)

1. **DB4 Groesse ermitteln**: Schrittweise testen (30, 50, 100 Bytes) welche Lesegroesse auf dieser SPS funktioniert. Der Live-Monitor liest erfolgreich 30 Bytes.

2. **Analog-Skalierung**: Rohwerte (0-27648) muessen in physikalische Werte umgerechnet werden. Skalierungsfaktoren aus Step-7 HW-Konfig oder durch Vergleich mit bekannten Werten ermitteln.

3. **String-Dekodierung**: SAIA speichert Strings als UTF-16-BE statt S7-Standard ASCII. Die Lesefunktion muss angepasst werden.

4. **Chargenprotokoll-Generierung**: Logik implementieren die aus den S7-Daten ein Chargenprotokoll im Belimed-Format erzeugt (siehe Abschnitt 5).

### 7.2 Wichtig

5. **Phasenerkennung**: Merker M133.0 (Phasenwechsel) als Trigger nutzen um Phasenwechsel zu protokollieren. Bei jedem Wechsel: Zeitstempel, Phase, Temperatur, Druck speichern.

6. **Charge Start/Ende**: Merker M76.1 (PROZ_Sta_Ende) und M76.2 (Programm_laeuft) als Trigger fuer Chargenstart und -ende verwenden.

7. **DB10 und DB11 testen**: Batch-Daten und Kurvenspeicher lesen um zu pruefen ob das Chargenprotokoll komplett aus der SPS gelesen werden kann.

8. **Stoerungsbehandlung**: Bei Stoerung (M51.0) die Stoerungsnummer aus DB7 lesen und im Protokoll dokumentieren.

9. **Netzwerk-Konfiguration auf Pi**: Statische IP auf dem Raspberry Pi konfigurieren (eth0 = 10.230.11.100/24). Per dhcpcd.conf oder netplan.

### 7.3 Nice-to-have

10. **Reconnect-Logik**: Bei Verbindungsabbruch automatisch neu verbinden (ist im Live-Monitor bereits rudimentaer implementiert).

11. **PDF-Export**: Chargenprotokoll als PDF mit Belimed-Layout exportieren.

12. **SmartHub-Integration**: Daten an SmartHub Orbit senden (siehe SPS-Adressliste Sheet "SmartHub Mapping").

---

## 8. Getestete Tools & Scripts

Alle im Ordner `saia_test_toolkit/`:

| Script | Zweck | Status |
|--------|-------|--------|
| 01_usb_detect.py | USB-Device erkennen | Funktioniert, aber USB ist nicht der richtige Weg |
| 02_sbus_test.py | S-Bus ueber USB testen | Nicht relevant (USB ist proprietaer) |
| 03_s7_lan_test.py | S7 ueber LAN testen | Funktioniert! Hauptweg fuer v2 |
| 04_live_monitor.py | Echtzeit-Anzeige im Terminal | Funktioniert (liest DB4 mit 30 Bytes) |
| run_all_tests.py | Alle Tests ausfuehren | Vorhanden |

---

## 9. Wichtige Erkenntnisse

1. **USB ist eine Sackgasse**: Der USB-Port der SAIA PCD2.M5 ist ein proprietaeres Vendor-Specific Device (VID 5007, PID 2). Er erscheint NICHT als serieller Port und ist nur fuer PG5/Step-7-Programmierung gedacht. Kein Treiber (FTDI, CH340, etc.) hilft hier.

2. **S7 ueber LAN funktioniert perfekt**: python-snap7 kann sich problemlos mit der SAIA verbinden und alle relevanten Datenbereiche lesen (DBs, Merker, Peripherie-Eingaenge).

3. **SAIA ist kein Siemens**: Obwohl S7-kompatibel, gibt es Unterschiede:
   - CPU-Info ist nicht verfuegbar ("Item not available")
   - Strings werden als UTF-16-BE gespeichert statt ASCII
   - DB-Groessen weichen moeglicherweise vom Step-7-Projekt ab

4. **Nur-Lesen ist sicher**: Alle Tests arbeiten ausschliesslich lesend. Es wird nie auf die SPS geschrieben.

5. **Verbindungsparameter fuer diese SPS**: IP=10.230.11.212, Rack=0, Slot=2. Diese koennen bei anderen MST-Installationen abweichen.
