# DocuPi-3000

**Digitale Chargendokumentation für Sterilisatoren — ohne Eingriff in die Maschinensteuerung**

Konzeptpapier für getmatic · Stand: April 2026

---

## Das Problem

Sterilisatoren in Kliniken und AEMP-Zentren dokumentieren ihre Chargen heute in der Regel über einen direkt angeschlossenen Drucker — oft einen klassischen Tintenstrahl- oder Nadeldrucker am HMI-Panel. Die Ausdrucke sind analog, schlecht archivierbar, nicht durchsuchbar und gehen im Stations-Alltag verloren. Eine nachträgliche digitale Auswertung ist faktisch nicht möglich.

Eine Nachrüstung mit geräteseitigen Softwareupdates ist meist nicht möglich: Die HMI-Steuerungen sind validierte Systeme, Änderungen darin sind regulatorisch und kommerziell nicht durchführbar.

---

## Die Lösung: DocuPi-3000

Der DocuPi-3000 ist ein kompaktes, industrietaugliches Dokumentationsgerät, das sich **passiv zwischen HMI und Drucker** einfügt. Es liest die Chargenprotokolle direkt vom Druckdatenstrom der Maschine, speichert sie in strukturierter Form und stellt sie als:

- durchsuchbare digitale Protokoll-Datenbank,
- moderne PDF-Chargendokumentation mit grafischer Kurvendarstellung (Druck- und Temperaturverlauf),
- Web-Dashboard mit Live-Übersicht aller laufenden und vergangenen Chargen,
- optionalen USB- und Netzwerk-Export

bereit.

**Der Kunde muss an der Maschine selbst nichts verändern.** Keine Softwareanpassung, keine Umkonfiguration der HMI, keine Validierungsfrage.

---

## Technisches Konzept

### Architektur beim Kunden

```
  HMI-Panel
     │
     │  Ethernet (Druckdaten, TCP/9100)
     ▼
  DocuPi-3000  ──── USB ────▶  vorhandener Drucker (optional)
     │
     ├──── USB-Ethernet ────▶  Klinik-Netzwerk (WebIF, Kunde)
     │
     └──── WLAN-Hotspot ────▶  Service-Zugang (Techniker)
```

Der DocuPi-3000 übernimmt die Rolle, die bisher ein passiver LAN-Printserver zwischen HMI und Drucker eingenommen hat. Er tritt im Maschinen-LAN unter der gewohnten IP-Adresse auf, nimmt die Druckaufträge entgegen, extrahiert die Chargendaten und reicht den Druck auf Wunsch transparent an den vorhandenen Drucker weiter — oder erstellt einen hochwertigen PDF-Ausdruck im neuen Design.

### Netzwerk-Trennung

Der DocuPi-3000 arbeitet mit **zwei physisch getrennten Netzwerkschnittstellen**:

- **Maschinen-Seite** — abgeschottet, nur Kommunikation mit der HMI
- **Klinik-Seite** — WebIF-Zugriff, optional per USB-Ethernet eingebunden

Zwischen den Seiten findet **kein IP-Routing** statt. Der DocuPi-3000 ist ein Endgerät, kein Router — ein kritisches Kriterium für die Freigabe durch Klinik-IT.

### Drei Betriebsmodi

Der Betreiber entscheidet pro Installation:

| Modus | Beschreibung | Typischer Einsatz |
|------|--------------|-------------------|
| **Integriert** | DocuPi hängt im Klinik-LAN, Zugriff vom PC am Arbeitsplatz | AEMP mit IT-Freigabe |
| **Hotspot** | DocuPi spannt eigenes WLAN auf, Zugriff per Tablet/Laptop | Werkstatt, Service |
| **USB-Export** | Chargen werden auf USB-Stick exportiert | IT-restriktive Umgebungen |

Alle drei Modi sind im Auslieferungsgerät verfügbar und per WebIF umschaltbar.

---

## Funktionsumfang

### Dokumentation

- Automatische Erfassung aller Chargenprotokolle in Echtzeit
- Strukturierte Speicherung in durchsuchbarer Datenbank
- Neu gestaltete PDF-Ausgabe mit Charts (Druck-/Temperaturkurven), Programmdaten, Chargennummer, Zeitstempel und Freigabestatus
- Unterscheidung und korrekte Kennzeichnung aller Programmtypen (Instrumente 134 °C, Bowie-Dick, VPR/Lecktest, Sonderprogramme)
- Robuste Behandlung unvollständiger Protokolle (Stromausfall, Abbruch)

### Ausgabe

- Web-Dashboard mit Live-Übersicht und Chargenhistorie
- Download aller PDFs einzeln oder gebündelt
- Direkter Druck auf den vorhandenen Drucker (optional, per USB)
- Automatischer USB-Stick-Export bei Gerät-Einstecken
- Langzeit-Archivierung lokal auf dem DocuPi (mehrere Jahre bei typischer Nutzung)

### Administration

- WebIF-gestützte Konfiguration, kein Kommandozeilen-Zugriff nötig
- Watchdog-Überwachung aller internen Dienste, automatischer Neustart bei Fehlfunktion
- Systemgesundheits-Anzeige (Temperatur, Speicher, Netzwerk, Dienste) im WebIF
- Remote-Wartungszugang für Service über verschlüsselten Tunnel (optional)

---

## Sicherheit & IT-Konformität

Alle Anforderungen, die typischerweise von Klinik-IT-Abteilungen gestellt werden, werden vom DocuPi-3000 erfüllt:

- **HTTPS-Verschlüsselung** für den gesamten WebIF-Zugriff; Zertifikatsverwaltung über eigene CA oder Kunden-PKI möglich
- **Benutzerauthentifizierung** mit Login und Rollentrennung (Administrator, Techniker, Betrachter)
- **LDAP-/Active-Directory-Anbindung** möglich für Integration in bestehende Kunden-Infrastruktur
- **Audit-Log** aller Zugriffe und Konfigurationsänderungen
- **Firewall** auf Klinik-Seite, nur explizit benötigte Ports offen
- **Keine ausgehenden Internetverbindungen** im Standardbetrieb — das Gerät funktioniert vollständig lokal
- **Keine personenbezogenen Daten** werden verarbeitet, ausschließlich Maschinendaten
- **DSGVO-konform** durch Lokalität der Datenverarbeitung
- **Updates** werden signiert und entweder per USB oder über getmatic-gesteuerten Update-Kanal ausgeliefert

---

## Referenzinstallation

Der DocuPi-3000 wurde im Frühjahr 2026 über **drei Wochen im Dauerbetrieb** an einem Sterilisator in einem großen deutschen Klinikum erprobt:

- **140 Chargen lückenlos erfasst**
- **327 Protokolle** in Datenbank
- Programme: Instrumente 134 °C, Bowie-Dick, VPR/Lecktest
- Mehrere reale Stör- und Abbruchfälle korrekt erkannt und dokumentiert
- Null Datenverluste, null ungeplante Neustarts im Produktivbetrieb

Die dort gewonnenen Erkenntnisse sind in die aktuelle Softwareversion eingeflossen.

---

## Liefer- und Leistungsumfang

### Von getmatic geliefert

- DocuPi-3000-Gerät (industrietauglich, lüfterlos, SD-Karten-basiert)
- USB-Ethernet-Adapter für Klinik-Anbindung
- Vorkonfiguriertes Betriebssystem mit DocuPi-Software
- Passendes Netzteil, Anschlusskabel
- Inbetriebnahme-Dokumentation (Kunden-Handbuch)
- Support-Vertrag nach Vereinbarung

### Kundenseitig erforderlich

- Netzwerk-Port am Sterilisator frei (der Port, an dem bisher der Drucker hing)
- Bei Modus „Integriert": IP-Adresse im Klinik-LAN + Freigabe der Klinik-IT
- Optional: Stellplatz für vorhandenen Drucker, falls dieser weiter genutzt werden soll

---

## Inbetriebnahme

1. DocuPi-3000 wird vorkonfiguriert ausgeliefert — inklusive Maschinen-IP und Protokoll-Profil
2. Vor-Ort-Installation: alten LAN-Printserver abklemmen, DocuPi an gleicher Stelle anschließen
3. Klinik-LAN-Seite optional einbinden (USB-Ethernet-Adapter in Switch/Dose)
4. Drucker per USB anschließen, falls weiter gewünscht
5. Funktionsprüfung über eine Testcharge

**Typische Installationszeit: unter 30 Minuten pro Gerät.**

---

## Nächste Schritte

Zur finalen Anpassung des Geräts an die Kunden-Umgebung benötigen wir einmalig:

1. Ein Sample eines aktuellen Chargenprotokoll-Ausdrucks (Papier oder PDF)
2. Die IP-Adresse, unter der der bisherige Drucker/Printserver im Maschinen-LAN erreichbar war
3. Bei Modus „Integriert": IP/DHCP-Konfiguration im Klinik-LAN, IT-Kontakt für Freigabe

Mit diesen Informationen ist eine Inbetriebnahme innerhalb weniger Tage möglich.

---

*Kontakt: Thomas Glander, getmatic*
