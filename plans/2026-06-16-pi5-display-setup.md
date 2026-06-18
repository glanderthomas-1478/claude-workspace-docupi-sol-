# Pi5_Display — Projekt-Setup

**Erstellt:** 2026-06-16  
**Status:** In Betrieb — App läuft, Kiosk aktiv

---

## Was ist Pi5_Display

Ein zweiter, vollständig unabhängiger DocuControl-Pi (Raspberry Pi 5) mit:
- **Eigener TCP/9100-Pipeline** → eigene DB → eigene PDFs
- **Docker-Betrieb** (saubere Kapselung, einfachere Updates)
- **HDMI-Display im Kiosk-Modus** (Chromium → Dashboard, kein Tastatur/Maus nötig)

Zweck: Zweiter Einsatzort unabhängig von dem Pi bei getmatic (.171/.181).

---

## Hardware

| | |
|---|---|
| **Modell** | Raspberry Pi 5 (8 GB RAM) |
| **OS** | Debian GNU/Linux 13 (Trixie), Kernel 6.12.75 aarch64 |
| **IP** | 192.168.0.218 (DHCP, eth0) |
| **Speicher** | 53 GB SD-Karte, ~47 GB frei |
| **Display** | HDMI + USB (Touchscreen oder Monitor) |
| **SSH** | `ssh docucontrol2` (Alias in `~/.ssh/config`) |
| **SSH User** | `docucontrol` |
| **sudo Passwort** | `Xtend1478` |

---

## Architektur

```
Host (Pi 192.168.0.218)
├── Docker
│   └── docupi-docucontrol-1 (network_mode: host)
│       ├── Flask Web :5000
│       ├── TCP-Receiver :9100
│       ├── PDF-Generator
│       └── SQLite DB
├── CUPS (host, Port 631)
├── nftables (Port 80 → 5000, extern)
└── kiosk.service
    └── cage + Chromium → http://localhost:5000
```

**Volume-Mounts im Container:**
- `.:/app` — App-Code live (kein Rebuild nötig bei Dateiänderungen)
- `/home/docucontrol/docupi/logs:/home/docucontrol/docupi/logs`
- `/sys:/sys:ro` — USB-Drucker-Erkennung via sysfs
- `/dev:/dev` — USB-Gerätezugriff
- `/var/run/cups:/var/run/cups` — Host-CUPS-Socket
- `/media:/media`, `/mnt:/mnt` — USB-Stick / Netzwerk-Mount

---

## Verzeichnisstruktur auf dem Pi

```
/home/docucontrol/docupi/
├── app.py, config.py, database.py, ...   # App-Code (alle .py von .181 kopiert)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── data/                                  # Persistent: DB, PDFs, Configs
├── logs/                                  # docupi.log
└── templates/, static/
```

---

## Systemd-Services

| Service | Beschreibung | Status |
|---|---|---|
| `docucontrol.service` | Docker-Compose Up/Down | `active (running)`, enabled |
| `kiosk.service` | cage + Chromium Kiosk | `active (running)`, enabled |
| `docker.service` | Docker Engine | `active`, enabled |
| `cups.service` | Druckserver | `active`, enabled |
| `seatd.service` | Wayland Seat-Manager | `active`, enabled |

---

## SSH-Config (`~/.ssh/config`)

```
Host docucontrol2
    HostName 192.168.0.218
    User docucontrol
    IdentityFile ~/.ssh/docucontrol_id
    StrictHostKeyChecking no
```

---

## Docker-Befehle

```bash
# Logs anzeigen
ssh docucontrol2 "cd /home/docucontrol/docupi && sudo docker-compose logs -f"

# Neu starten
ssh docucontrol2 "cd /home/docucontrol/docupi && sudo docker-compose restart"

# App-Code aktualisieren (kein Rebuild nötig, Volume-Mount)
scp -i ~/.ssh/docucontrol_id src/docucontrol/app.py docucontrol@192.168.0.218:/home/docucontrol/docupi/
ssh docucontrol2 "cd /home/docucontrol/docupi && sudo docker-compose restart"

# Image neu bauen (nach requirements.txt-Änderung)
ssh docucontrol2 "cd /home/docucontrol/docupi && sudo docker-compose build --no-cache && sudo docker-compose up -d"
```

---

## Kiosk-Display

- **Compositor:** `cage` (minimaler Wayland-Kiosk, Pi 5 kompatibel)
- **Browser:** Chromium `--kiosk --ozone-platform=wayland`
- **URL:** `http://localhost:5000` (Dashboard-Seite)
- **Autostart:** `kiosk.service` (enabled, startet nach `docucontrol.service`)
- **Xwrapper:** `/etc/X11/Xwrapper.config` → `allowed_users=anybody`
- **Cursor ausgeblendet:** udev-Regel `/etc/udev/rules.d/99-vc4-hdmi-noinput.rules` setzt `LIBINPUT_IGNORE_DEVICE=1` auf den HDMI-CEC-Virtualgeräten (`platform-107c701400.hdmi` + `platform-107c706400.hdmi`) — diese wurden von cage als Pointer erkannt und haben den Cursor verursacht
- **Touchscreen:** QDTECH MPI7002 USB (Vendor 0484, Product 5750) via `/etc/udev/rules.d/99-qdtech-touch.rules` als Touch-Only klassifiziert

---

## Was noch offen ist

- [ ] **Maschinennummer + Name** in Settings eintragen (Einstellungen → Anlage)
- [x] **Netzwerk-Speicherort** konfiguriert — SMB zu `\\192.168.0.86\temp` (Konto `docucontrol`), `mounted:true`, Sofort-Sync verifiziert (2026-06-18, siehe CLAUDE.md "Netzwerk-Speicherort SMB-Mount im Docker-Container gefixt")
- [ ] **Drucker** anschließen und `USB einrichten` in Settings klicken
- [x] **nftables autostart** konfiguriert — `/etc/nftables-docucontrol.conf` + `nftables-docucontrol.service` (2026-06-16)
- [ ] **eth0 statisch** konfigurieren (aktuell DHCP → IP kann nach Reboot wechseln)
- [x] **Cursor ausgeblendet** — udev `LIBINPUT_IGNORE_DEVICE=1` auf vc4-hdmi Geräten (2026-06-16)
- [ ] **Kiosk testen** nach Reboot (Display zeigt Dashboard?)
- [ ] **Deploy-Script** erweitern (`deploy_docucontrol_win.ps1`) für .218

---

## Unterschiede zu DocuControl (.171)

| | .171 (getmatic) | .218 (Pi5_Display) |
|---|---|---|
| **Betrieb** | systemd direkt | Docker + systemd |
| **Display** | keines | HDMI Kiosk |
| **Netzwerk** | eth0 + eth1 (USB-Ethernet) | eth0 DHCP (.218) + eth1 statisch (.107) |
| **RTC** | DS3231 | (noch nicht geprüft) |
| **WLAN** | hardware-deaktiviert | Status unbekannt |
| **SMB-Sync** | 192.168.0.99 (gland) | 192.168.0.86 (Thomas' PC), produktiv seit 2026-06-18 |
