# Plan: Netzwerk-Speicherort (SMB-Sync) fuer DocuControl

**Erstellt:** 2026-06-12
**Status:** Implementiert
**Anforderung:** Im Settings-Tab "Geraete & Netzwerk" soll ein Netzwerk-Speicherort (Windows-Freigabe/SMB) konfigurierbar sein, auf den PDF-Protokolle und Rohdaten-Captures automatisch im Intervall synchronisiert werden — analog zur bestehenden USB-Synchronisation.

---

## Ueberblick

### Was dieser Plan erreicht

DocuControl kann zusaetzlich zur USB-Synchronisation PDFs und Rohdaten-Captures automatisch auf eine
SMB/CIFS-Netzwerkfreigabe (z.B. einen Windows-PC im Kliniknetz) kopieren. Konfiguration (Server,
Freigabename, Zugangsdaten) erfolgt ueber eine neue Settings-Card. Ein Hintergrund-Thread mountet die
Freigabe bei aktivierter Konfiguration und synchronisiert im konfigurierten Intervall.

### Warum das wichtig ist

Im Tierlabor/Kliniknetz soll die Dokumentation nicht nur lokal (SD/USB) liegen, sondern automatisch auf
einen zentralen Rechner/Server im Netzwerk gespiegelt werden — fuer Backup, Archivierung und Zugriff
durch mehrere Arbeitsplaetze ohne manuelles Stick-Tauschen.

---

## Aktueller Zustand

### Relevante bestehende Struktur

- `src/docucontrol/storage_manager.py` — USB-Mount/Sync-Engine: `load_sync_config()`/`save_sync_config()`
  (Datei `data/sync_config.json`), `sync_pdfs_to_usb()`, `sync_captures_to_usb()`,
  `_auto_sync_loop()` (Hintergrund-Thread, `start_auto_sync()`/`stop_auto_sync()`)
- `src/docucontrol/app.py` — Routen `/api/storage/sync/config`, `/api/storage/sync/now`,
  `/api/storage/usb/*`; Imports aus `storage_manager`
- `src/docucontrol/templates/settings.html` — Tab "Geraete & Netzwerk", Card "USB-Synchronisation"
  (Zeilen ~361-401): Toggle, Letzter-Sync-Anzeige, "Jetzt sync."-Button, Format-Button
- `src/docucontrol/config.py` — `DEFAULT_CONFIG` mit Sektionen serial/protocol/pdf/web/system/machine,
  `load_config()`/`save_config()` (atomic write + Backup)
- Sudoers: `/etc/sudoers.d/docucontrol-storage` (mount/umount/blkid/dosfsck/mkfs.vfat/mkdir),
  `/etc/sudoers.d/docucontrol-network` (nmcli/ip/hostnamectl/timedatectl/hwclock/nft/tee)
- `cifs-utils` ist auf dem Pi bereits installiert, `/usr/sbin/mount.cifs` ist setuid-root vorhanden

### Luecken oder Probleme, die adressiert werden

- Es gibt aktuell keinen Weg, Protokolle automatisch auf ein Netzlaufwerk/anderen Rechner zu spiegeln —
  nur USB-Stick-Sync und manueller Download
- Sudoers erlaubt noch kein `mount -t cifs`

---

## Vorgeschlagene Aenderungen

### Zusammenfassung der Aenderungen

1. Neues Modul `network_storage_manager.py`: SMB-Mount (CIFS), Verbindungstest, PDF+Capture-Sync,
   Hintergrund-Sync-Thread, eigene Config-Datei `data/network_storage_config.json`
2. Sudoers-Erweiterung fuer `mount -t cifs` / `mount.cifs`
3. Neue API-Routen in `app.py`: Config lesen/speichern, Status, Verbindungstest, manueller Sync
4. Neue Settings-Card "Netzwerk-Speicherort" in `settings.html` (Tab Geraete & Netzwerk, nach
   USB-Synchronisation)
5. CLAUDE.md-Dokumentation aktualisieren
6. Deploy auf den Pi, Sudoers einspielen, Service neu starten, mit echter Freigabe testen

### Neue Dateien erstellen

| Dateipfad | Zweck |
| --- | --- |
| `src/docucontrol/network_storage_manager.py` | SMB-Mount/Unmount, Verbindungstest, Sync-Engine, Hintergrund-Thread, Config-Persistenz |

### Zu aendernde Dateien

| Dateipfad | Aenderungen |
| --- | --- |
| `src/docucontrol/app.py` | Import aus `network_storage_manager`; neue Routen `/api/storage/network/config` (GET/POST), `/api/storage/network/status`, `/api/storage/network/test`, `/api/storage/network/sync`; `start_network_sync()` beim Start aufrufen |
| `src/docucontrol/templates/settings.html` | Neue Card "Netzwerk-Speicherort" mit Formular + Status + Sync-Buttons; JS-Funktionen `loadNetworkStorageConfig()`, `saveNetworkStorageConfig()`, `testNetworkStorage()`, `syncNetworkNow()`, Status-Polling |
| `CLAUDE.md` | Neue API-Endpunkte + Feature-Beschreibung dokumentieren |

### Zu loeschende Dateien

Keine.

---

## Design-Entscheidungen

### Getroffene Schluesselentscheidungen

1. **Eigenes Modul statt Erweiterung von `storage_manager.py`**: Klare Trennung USB- vs.
   Netzwerk-Sync, eigener Hintergrund-Thread mit eigener Fehlerbehandlung (Netzwerkfreigabe kann
   zeitweise nicht erreichbar sein, ohne dass das den USB-Sync blockiert).
2. **Eigene Config-Datei `data/network_storage_config.json`** (statt neue Sektion in `config.json`):
   folgt exakt dem Muster von `sync_config.json` (USB), enthaelt sowohl Konfiguration
   (server/share/username/password/sync_days/interval/enabled) als auch Laufzeit-Status
   (last_sync, last_sync_count, last_error).
3. **Zugangsdaten in separater Credentials-Datei** (`data/network_share.cred`, chmod 600,
   `credentials=`-Option von `mount.cifs`): verhindert, dass das Passwort in `ps aux` (Prozessliste)
   auftaucht. Passwort wird zusaetzlich **nie** ueber `GET /api/storage/network/config`
   zurueckgegeben (nur `has_password: true/false`) — adressiert das gleiche Muster wie der
   bekannte Hotspot-Passwort-Leak-Befund, fuer dieses neue Feature von Anfang an korrekt.
4. **Validierung von Server/Freigabename per Regex** (`^[A-Za-z0-9._-]+$` fuer Server,
   `^[A-Za-z0-9._\- ]+$` fuer Freigabename) und **`subprocess.run([...], shell=False)`** (Listenform)
   fuer alle neuen `mount`/`umount`-Aufrufe: vermeidet die im Security-Review (2026-06-11) fuer
   bestehenden Code dokumentierten Shell-Injection-Risiken — fuer neuen Code von Anfang an sauber.
5. **Mount-Punkt `/mnt/docucontrol_share`**, Unterordner `DocuControl/` (PDFs) und
   `docucontrol/captures/` (Rohdaten) — identische Ordnerstruktur wie auf dem USB-Stick
   (`USB_PDF_SUBDIR`/`USB_CAPTURE_SUBDIR`), damit Nutzer beide Ziele gleich wiederfinden.
6. **SMB-Protokollversion**: kein festes `vers=`-Mount-Option — `mount.cifs` handelt automatisch
   die hoechste gemeinsame Version aus (SMB3 bei modernen Windows-Versionen). Bei Testverbindung
   wird die `mount.cifs`-Fehlermeldung in eine verstaendliche deutsche Meldung uebersetzt
   (z.B. "Zugriff verweigert", "Freigabe nicht gefunden", "Server nicht erreichbar").
7. **Hintergrund-Thread mit 60s-Grundtakt**: pruefit `enabled`, mountet bei Bedarf (mit Backoff bei
   Fehlern, kein Retry-Sturm), synchronisiert im konfigurierten Intervall (Default 15 Min, wie USB).
8. **Mount mit `uid=1000,gid=1000`** (wie USB-Mount), damit der `docucontrol`-User direkt schreiben
   kann ohne weitere sudo-Aufrufe fuer den Datei-Sync selbst.

### Betrachtete Alternativen

- **rsync/SSH statt SMB**: waere fuer Linux-Ziele eleganter, aber im Tierlabor/Klinik-Umfeld sind die
  Zielrechner i.d.R. Windows-PCs ohne SSH-Server — SMB ist dort die einzige praktikable Option ohne
  Zusatzinstallation auf dem Zielrechner. (User-Entscheidung: SMB/Windows-Freigabe)
- **Sektion in `config.json`**: wuerde Passwort in die bereits per `config.json.backup` gesicherte
  Haupt-Config mischen; separate Datei haelt das Feature isoliert und einfacher zu loeschen/zuruecksetzen.
- **Sync nur manuell per Button**: User wollte automatisches Intervall (wie USB), manueller
  "Jetzt synchronisieren"-Button wird zusaetzlich angeboten, da er bei USB-Sync ebenfalls existiert
  und kostenguenstig ist.

### Offene Fragen

Keine blockierenden offenen Fragen — Defaults (Mount-Punkt, Unterordner, Intervall 15 Min,
sync_days 7) folgen den bestehenden USB-Sync-Konventionen 1:1. Der Nutzer muss bei der ersten
Einrichtung lediglich Server/IP, Freigabename, Benutzername und Passwort der Windows-Freigabe im
UI eintragen.

---

## Schritt-fuer-Schritt-Aufgaben

### Schritt 1: `network_storage_manager.py` erstellen

Neues Modul nach dem Vorbild von `storage_manager.py`, aber fuer SMB/CIFS-Freigaben.

**Aktionen:**

- Konstanten definieren:
  - `NETWORK_MOUNT_POINT = "/mnt/docucontrol_share"`
  - `NETWORK_PDF_SUBDIR = "DocuControl"`
  - `NETWORK_CAPTURE_SUBDIR = "docucontrol/captures"`
  - `CRED_FILE = "/home/docucontrol/docupi/data/network_share.cred"`
  - `NETWORK_CONFIG_FILE = "/home/docucontrol/docupi/data/network_storage_config.json"`
  - `CAPTURE_DIR = "/home/docucontrol/docupi/data/raw_captures"` (wie in `storage_manager.py`)
  - `SERVER_RE = re.compile(r"^[A-Za-z0-9._-]+$")`, `SHARE_RE = re.compile(r"^[A-Za-z0-9._\- ]+$")`
- `DEFAULT_NETWORK_CONFIG`:
  ```python
  {
      "enabled": False,
      "server": "",
      "share": "",
      "username": "",
      "password": "",
      "domain": "",
      "sync_days": 7,
      "sync_interval_minutes": 15,
      "last_sync": None,
      "last_sync_count": 0,
      "last_error": "",
  }
  ```
- `load_network_config()` / `save_network_config()` — identisches Muster zu
  `load_sync_config()`/`save_sync_config()` in `storage_manager.py` (defaults mergen, JSON
  schreiben mit `json.dump(..., indent=2)`)
- `_run(args_list, timeout=30)`: `subprocess.run(args_list, capture_output=True, text=True,
  timeout=timeout)` — **keine** `shell=True`, Argumente immer als Liste
- `_write_credentials_file(username, password, domain)`:
  - Schreibt `username=...\npassword=...\ndomain=...\n` (domain-Zeile nur wenn gesetzt) nach
    `CRED_FILE`
  - `os.chmod(CRED_FILE, 0o600)` direkt nach dem Schreiben
- `_validate_server_share(server, share)`: prueft `SERVER_RE`/`SHARE_RE`, gibt
  `(True, "")` oder `(False, "Fehlermeldung")` zurueck
- `_translate_mount_error(stderr)`: Mapping bekannter `mount.cifs`-Fehlermeldungen auf deutsche
  Klartexte:
  - `"Permission denied"` / `"error(13)"` -> "Zugriff verweigert — Benutzername/Passwort pruefen"
  - `"No such file or directory"` / `"error(2)"` -> "Freigabe nicht gefunden — Freigabename pruefen"
  - `"Host is down"` / `"unreachable"` / `"error(112)"` / `"error(101)"` ->
    "Server nicht erreichbar — IP/Hostname pruefen"
  - Fallback: Original-Fehlertext
- `is_mounted()`: `os.path.ismount(NETWORK_MOUNT_POINT)`
- `mount_network_share(cfg=None)`:
  - `cfg = cfg or load_network_config()`
  - Validierung (enabled, server, share, `_validate_server_share`) — bei Fehler `(False, msg)`
  - `is_mounted()` -> `(True, "bereits gemountet")`
  - `_write_credentials_file(...)`
  - `sudo mkdir -p NETWORK_MOUNT_POINT` (ueber `_run`)
  - UNC-Pfad: `f"//{cfg['server']}/{cfg['share']}"`
  - `sudo mount -t cifs <unc> <mount_point> -o credentials=<cred_file>,uid=1000,gid=1000,iocharset=utf8,_netdev,file_mode=0644,dir_mode=0755`
  - Bei Erfolg: `os.makedirs` fuer `NETWORK_PDF_SUBDIR`/`NETWORK_CAPTURE_SUBDIR` unter dem
    Mount-Point, `last_error=""` in Config speichern
  - Bei Fehler: `_translate_mount_error(stderr)` in `last_error` speichern, `(False, msg)`
- `unmount_network_share()`: `sudo umount NETWORK_MOUNT_POINT` (Fallback `umount -l`), analog
  `unmount_usb()`
- `test_network_connection(server, share, username, password, domain)`:
  - Validiert Eingaben
  - Schreibt temporaere Credentials-Datei (`CRED_FILE + ".test"`, chmod 600)
  - Falls `NETWORK_MOUNT_POINT` bereits mit denselben Daten gemountet ist: sofort `(True, "Verbindung OK (bereits verbunden)")`
  - Sonst: `sudo mkdir -p`, `sudo mount -t cifs <unc> NETWORK_MOUNT_POINT -o
    credentials=<test_cred_file>,...`; bei Erfolg sofort wieder `sudo umount`; Ergebnis als
    `(ok, message)` zurueckgeben (Fehler uebersetzt via `_translate_mount_error`)
  - temporaere Cred-Datei am Ende loeschen
- `get_network_storage_status()`:
  - liest Config, gibt zurueck: `enabled`, `mounted` (`is_mounted()`), `server`, `share`,
    `username`, `has_password` (`bool(cfg["password"])`), `domain`, `sync_days`,
    `sync_interval_minutes`, `last_sync`, `last_sync_count`, `last_error`
  - falls `mounted`: zusaetzlich `free_gb`/`total_gb`/`used_percent` via `shutil.disk_usage`
- `sync_pdfs_to_network(days=None)` — Kopie von `sync_pdfs_to_usb()`, aber:
  - `cfg = load_network_config()`; wenn `not cfg["enabled"]`: `(False, "Netzwerk-Sync deaktiviert", 0)`
  - wenn `not is_mounted()`: `mount_network_share(cfg)` versuchen, bei Fehler `(False, msg, 0)`
  - Ziel: `os.path.join(NETWORK_MOUNT_POINT, NETWORK_PDF_SUBDIR)`
  - gleiche Cutoff/Vergleichs-Logik wie USB-Variante (mtime/size-Vergleich, `shutil.copy2`)
  - Ergebnis in `last_sync`/`last_sync_count` der Network-Config speichern
- `sync_captures_to_network(days=None)` — analog `sync_captures_to_usb()`, Ziel
  `NETWORK_MOUNT_POINT/NETWORK_CAPTURE_SUBDIR`
- Hintergrund-Thread:
  - `_sync_thread = None`, `_sync_running = False`
  - `start_network_sync()`: startet `_network_sync_loop` als Daemon-Thread (Guard gegen
    Doppelstart wie `start_auto_sync()`)
  - `stop_network_sync()`
  - `_network_sync_loop()`:
    ```
    last_sync_time = 0.0
    last_mount_attempt = 0.0
    while _sync_running:
        cfg = load_network_config()
        if not cfg["enabled"]:
            if is_mounted(): unmount_network_share()
            time.sleep(30); continue

        if not is_mounted():
            if time.time() - last_mount_attempt >= 60:  # Backoff
                ok, msg = mount_network_share(cfg)
                last_mount_attempt = time.time()
                if not ok:
                    time.sleep(30); continue

        interval = cfg.get("sync_interval_minutes", 15) * 60
        if time.time() - last_sync_time >= interval:
            try:
                sync_pdfs_to_network()
                sync_captures_to_network()
            except Exception as e:
                logger.error(f"Netzwerk-Sync Fehler: {e}")
            last_sync_time = time.time()

        time.sleep(30)
    ```

**Betroffene Dateien:**

- `src/docucontrol/network_storage_manager.py` (neu)

---

### Schritt 2: Sudoers fuer CIFS-Mount erweitern

**Aktionen:**

- Auf dem Pi `/etc/sudoers.d/docucontrol-storage` um folgende Zeile ergaenzen (per `visudo -c -f`
  validieren, dann `install -o root -g root -m 0440`, wie bei der nftables-Sudoers-Erweiterung
  zuvor):
  ```
  docucontrol ALL=(ALL) NOPASSWD: /usr/bin/mount -t cifs *, /usr/sbin/mount.cifs *
  ```
  (Hinweis: `mount` mit Wildcard-Argumenten via sudoers ist moeglich, da `/usr/bin/mount` und
  `/usr/sbin/mount.cifs` bereits in der bestehenden NOPASSWD-Zeile fuer `mount`/`umount` pauschal
  enthalten sind — pruefen, ob die bestehende `NOPASSWD: /usr/bin/mount, /usr/bin/umount, ...`
  Zeile CIFS-Mounts bereits erlaubt; falls ja, ist Schritt 2 ggf. nicht noetig. Falls `mount -t
  cifs` dennoch ein Passwort verlangt — z.B. weil sudoers `mount` ohne Argumente matched, aber mit
  `-t cifs ...` als andere Befehlszeile gewertet wird — explizite Zeile mit `*` ergaenzen.)
- Verifikation: `sudo -n mount -t cifs //testserver/testshare /mnt/docucontrol_share -o
  credentials=/tmp/test.cred` sollte kein Passwort verlangen (auch wenn der Mount selbst
  fehlschlaegt, weil testserver nicht existiert — entscheidend ist "sudo: a password is required"
  vs. echter Mount-Fehler)

**Betroffene Dateien:**

- `/etc/sudoers.d/docucontrol-storage` (auf dem Pi, nicht im Repo)

---

### Schritt 3: `app.py` — neue Routen und Startup-Hook

**Aktionen:**

- Import ergaenzen:
  ```python
  from network_storage_manager import (
      load_network_config, save_network_config, get_network_storage_status,
      test_network_connection, sync_pdfs_to_network, sync_captures_to_network,
      start_network_sync, mount_network_share, unmount_network_share,
  )
  ```
- Neue Routen (Platzierung: nahe den bestehenden `/api/storage/sync/*`-Routen, ca. Zeile 434):

  ```python
  @app.route("/api/storage/network/config", methods=["GET", "POST"])
  def api_network_storage_config():
      if request.method == "POST":
          data = request.get_json(silent=True) or {}
          cfg = load_network_config()
          for key in ("enabled",):
              if key in data:
                  cfg[key] = bool(data[key])
          for key in ("server", "share", "username", "domain"):
              if key in data:
                  cfg[key] = str(data[key]).strip()
          if data.get("password"):  # nur ueberschreiben wenn nicht leer
              cfg["password"] = data["password"]
          for key, cast in (("sync_days", int), ("sync_interval_minutes", int)):
              if key in data:
                  cfg[key] = cast(data[key])
          save_network_config(cfg)
          log_event("INFO", "Netzwerk-Speicherort-Konfiguration gespeichert")
          return jsonify({"success": True, "message": "Gespeichert"})
      cfg = load_network_config()
      cfg = dict(cfg)
      cfg["has_password"] = bool(cfg.pop("password", ""))
      return jsonify(cfg)

  @app.route("/api/storage/network/status")
  def api_network_storage_status():
      return jsonify(get_network_storage_status())

  @app.route("/api/storage/network/test", methods=["POST"])
  def api_network_storage_test():
      data = request.get_json(silent=True) or {}
      cfg = load_network_config()
      server = data.get("server", cfg["server"])
      share = data.get("share", cfg["share"])
      username = data.get("username", cfg["username"])
      password = data.get("password") or cfg["password"]
      domain = data.get("domain", cfg["domain"])
      ok, msg = test_network_connection(server, share, username, password, domain)
      log_event("INFO" if ok else "WARN", f"Netzwerk-Speicherort Test: {msg}")
      return jsonify({"success": ok, "message": msg})

  @app.route("/api/storage/network/sync", methods=["POST"])
  def api_network_storage_sync():
      ok1, msg1, n1 = sync_pdfs_to_network()
      ok2, msg2, n2 = sync_captures_to_network()
      ok = ok1 and ok2
      log_event("INFO" if ok else "ERROR", f"Netzwerk-Sync: {msg1} / {msg2}")
      return jsonify({"success": ok, "message": f"{msg1}; {msg2}", "count": n1 + n2})
  ```
- Im Startup-Bereich (dort wo `start_auto_sync()` fuer USB aufgerufen wird) zusaetzlich
  `start_network_sync()` aufrufen.

**Betroffene Dateien:**

- `src/docucontrol/app.py`

---

### Schritt 4: Settings-UI — Card "Netzwerk-Speicherort"

**Aktionen:**

- Neue Card nach der "USB-Synchronisation"-Card (nach Zeile ~401) einfuegen, vor `</div></div>`
  des Tab-Panels:

  ```html
  <!-- Netzwerk-Speicherort (SMB) -->
  <div class="card">
      <div class="card-head">
          <span><i class="bi bi-hdd-network-fill"></i> Netzwerk-Speicherort</span>
          <span class="badge" id="netStorageStatusBadge" style="font-size:11px;padding:2px 8px;border-radius:4px;background:var(--muted);color:#fff">—</span>
          <label class="switch" style="margin-left:auto">
              <input type="checkbox" id="netStorageEnabled" onchange="saveNetworkStorageConfig()">
              <span class="track"></span>
          </label>
      </div>
      <div class="card-body">
          <div class="set-row">
              <div class="info"><div class="name">Server (IP oder Name)</div><div class="desc">z.B. 192.168.0.50 oder PC-BUERO</div></div>
              <input type="text" class="ctrl" id="netStorageServer" placeholder="192.168.0.50" style="width:185px">
          </div>
          <div class="set-row">
              <div class="info"><div class="name">Freigabename</div><div class="desc">Name der Windows-Freigabe</div></div>
              <input type="text" class="ctrl" id="netStorageShare" placeholder="DocuControl" style="width:185px">
          </div>
          <div class="set-row">
              <div class="info"><div class="name">Benutzername</div></div>
              <input type="text" class="ctrl" id="netStorageUser" placeholder="benutzer" style="width:185px">
          </div>
          <div class="set-row">
              <div class="info"><div class="name">Passwort</div><div class="desc" id="netStoragePwHint">—</div></div>
              <input type="password" class="ctrl" id="netStoragePw" placeholder="unveraendert lassen" style="width:185px">
          </div>
          <div class="set-row">
              <div class="info"><div class="name">Domain / Workgroup</div><div class="desc">optional</div></div>
              <input type="text" class="ctrl" id="netStorageDomain" placeholder="WORKGROUP" style="width:185px">
          </div>
          <hr style="margin:12px 0;border:none;border-top:1px solid var(--border)">
          <div class="set-row">
              <div class="info"><div class="name">Letzter Sync</div><div class="desc">Zeitpunkt und Anzahl synchronisierter Dateien</div></div>
              <span class="value" id="netStorageLastSync" style="font-size:12.5px;color:var(--muted)">—</span>
          </div>
          <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:10px">
              <button class="btn btn-glass" onclick="testNetworkStorage()"><i class="bi bi-plug"></i> Verbindung testen</button>
              <button class="btn btn-glass" onclick="syncNetworkNow()"><i class="bi bi-arrow-repeat"></i> Jetzt sync.</button>
              <button class="btn btn-primary" onclick="saveNetworkStorageConfig()"><i class="bi bi-save"></i> Speichern</button>
          </div>
      </div>
  </div>
  ```

- JS-Funktionen ergaenzen (im `<script>`-Block, in der Naehe der USB-Sync-Funktionen):

  ```javascript
  function loadNetworkStorageConfig() {
      fetch('/api/storage/network/config').then(r => r.json()).then(d => {
          document.getElementById('netStorageEnabled').checked = !!d.enabled;
          document.getElementById('netStorageServer').value = d.server || '';
          document.getElementById('netStorageShare').value = d.share || '';
          document.getElementById('netStorageUser').value = d.username || '';
          document.getElementById('netStorageDomain').value = d.domain || '';
          document.getElementById('netStoragePwHint').textContent = d.has_password ? 'Passwort gesetzt — Feld leer lassen, um es zu behalten' : 'Kein Passwort gesetzt';
      });
      pollNetworkStorageStatus();
  }

  function pollNetworkStorageStatus() {
      fetch('/api/storage/network/status').then(r => r.json()).then(d => {
          var badge = document.getElementById('netStorageStatusBadge');
          if (!d.enabled) {
              badge.textContent = 'Deaktiviert';
              badge.style.background = 'var(--muted)';
          } else if (d.mounted) {
              badge.textContent = 'Verbunden';
              badge.style.background = 'var(--success)';
          } else {
              badge.textContent = d.last_error ? 'Fehler' : 'Getrennt';
              badge.style.background = d.last_error ? 'var(--danger)' : 'var(--muted)';
          }
          var info = document.getElementById('netStorageLastSync');
          info.textContent = d.last_sync ? (d.last_sync + ' · ' + d.last_sync_count + ' Dateien') : '—';
          if (d.last_error) info.textContent += ' · ' + d.last_error;
      });
  }

  window.saveNetworkStorageConfig = function() {
      var body = {
          enabled: document.getElementById('netStorageEnabled').checked,
          server: document.getElementById('netStorageServer').value.trim(),
          share: document.getElementById('netStorageShare').value.trim(),
          username: document.getElementById('netStorageUser').value.trim(),
          domain: document.getElementById('netStorageDomain').value.trim(),
          sync_days: 7,
          sync_interval_minutes: 15
      };
      var pw = document.getElementById('netStoragePw').value;
      if (pw) body.password = pw;
      fetch('/api/storage/network/config', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})
          .then(r => r.json()).then(d => {
              showToast(d.message || 'Gespeichert');
              document.getElementById('netStoragePw').value = '';
              loadNetworkStorageConfig();
          });
  };

  window.testNetworkStorage = function() {
      var body = {
          server: document.getElementById('netStorageServer').value.trim(),
          share: document.getElementById('netStorageShare').value.trim(),
          username: document.getElementById('netStorageUser').value.trim(),
          domain: document.getElementById('netStorageDomain').value.trim()
      };
      var pw = document.getElementById('netStoragePw').value;
      if (pw) body.password = pw;
      fetch('/api/storage/network/test', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})
          .then(r => r.json()).then(d => showToast(d.message));
  };

  window.syncNetworkNow = function() {
      fetch('/api/storage/network/sync', {method: 'POST'}).then(r => r.json()).then(d => {
          showToast(d.message);
          pollNetworkStorageStatus();
      });
  };
  ```

  Hinweis: `showToast()` existiert bereits im Template (wird fuer Hostname/NTP/etc. genutzt) —
  bei abweichendem Funktionsnamen den tatsaechlichen Toast-Helfer aus `settings.html`
  uebernehmen.

- `loadNetworkStorageConfig()` in `loadStaticSettings()` ergaenzen (einmaliger Aufruf beim
  Seitenladen, gleiche Stelle wie `loadInterfaces()`/`loadHostname()`)
- `pollNetworkStorageStatus()` zusaetzlich in den bestehenden 30s-Status-Poll einhaengen
  (analog `pollCurrentIPs()`, aber im 30s- statt 5s-Takt, da SMB-Status sich selten aendert)

**Betroffene Dateien:**

- `src/docucontrol/templates/settings.html`

---

### Schritt 5: CLAUDE.md aktualisieren

**Aktionen:**

- Im Abschnitt "Neue API-Endpunkte" die vier neuen Routen ergaenzen
- Neuen Unterabschnitt "Netzwerk-Speicherort (SMB-Sync, 2026-06-12)" mit Kurzbeschreibung
  (Mount-Punkt, Unterordner, Hintergrund-Sync-Intervall, Sudoers-Hinweis) ergaenzen

**Betroffene Dateien:**

- `CLAUDE.md`

---

### Schritt 6: Deploy & Test auf dem Pi

**Aktionen:**

- `scp` der neuen/aenderten Dateien auf den Pi (`network_storage_manager.py`, `app.py`,
  `settings.html`)
- Sudoers-Erweiterung pruefen/einspielen (Schritt 2)
- `sudo systemctl restart docucontrol.service`
- Im Browser: Settings -> Geraete & Netzwerk -> Card "Netzwerk-Speicherort" pruefen
  - Mit Test-Zugangsdaten "Verbindung testen" pruefen (Fehlermeldungen lesbar?)
  - Falls eine echte Freigabe verfuegbar ist: aktivieren, speichern, "Jetzt sync." testen,
    pruefen ob `DocuControl/`- und `docucontrol/captures/`-Ordner auf der Freigabe entstehen
    und PDFs/Captures ankommen
  - Service-Log pruefen (`journalctl -u docucontrol -n 50`) auf Fehler im Hintergrund-Thread

**Betroffene Dateien:**

- Keine weiteren (Deploy-Schritt)

---

## Verbindungen & Abhaengigkeiten

### Dateien, die diesen Bereich referenzieren

- `src/docucontrol/app.py` importiert aus `storage_manager` und startet `start_auto_sync()` beim
  Boot — `start_network_sync()` wird an derselben Stelle ergaenzt
- `settings.html` laedt alle Settings-Cards ueber `loadStaticSettings()` / Polling-Funktionen

### Noetige Updates fuer Konsistenz

- `CLAUDE.md` (Schritt 5)

### Auswirkungen auf bestehende Workflows

- Kein Einfluss auf USB-Sync, TCP-Capture, Druck-Pipeline — vollstaendig additiv
- Neuer Hintergrund-Thread laeuft parallel zu `_auto_sync_loop()` (USB)

---

## Validierungs-Checkliste

- [x] `network_storage_manager.py` importierbar ohne Fehler (`python3 -c "import network_storage_manager"`)
- [x] `GET /api/storage/network/config` liefert Defaults (enabled:false, has_password:false)
- [x] `POST /api/storage/network/config` speichert Werte, Passwort wird bei leerem Feld nicht
      ueberschrieben
- [x] `POST /api/storage/network/test` mit falschen Zugangsdaten liefert lesbare deutsche
      Fehlermeldung
- [x] Mit echter Freigabe: Mount erfolgreich, `DocuControl/` + `docucontrol/captures/` werden
      angelegt, Sync kopiert Dateien — verifiziert gegen Thomas' Windows-PC (192.168.0.86,
      Freigabe `temp`, dediziertes Konto `docucontrol`), 88 Dateien synchronisiert
- [x] Settings-UI zeigt Status-Badge korrekt (Deaktiviert/Verbunden/Getrennt/Fehler)
- [x] Service-Neustart funktioniert ohne Fehler, Hintergrund-Thread laeuft (`journalctl`)
- [x] CLAUDE.md aktualisiert

---

## Erfolgskriterien

Die Implementierung ist abgeschlossen, wenn:

1. In den Settings unter "Geraete & Netzwerk" eine Card "Netzwerk-Speicherort" existiert, in der
   Server/Freigabe/Zugangsdaten eingegeben und gespeichert werden koennen
2. Eine aktivierte, korrekt konfigurierte Freigabe automatisch im konfigurierten Intervall
   PDFs und Rohdaten-Captures erhaelt
3. Verbindungsfehler (falsches Passwort, falscher Servername, Freigabe nicht erreichbar) als
   verstaendliche deutsche Meldung im UI angezeigt werden
4. Das Feature auf dem Pi bei getmatic deployed und mit mindestens einem Testfall (echte Freigabe
   oder gezielter Fehlerfall) verifiziert ist

---

## Notizen

- Falls der Zielrechner SMB1 (sehr alte Windows-Versionen) erfordert, muesste ggf.
  `vers=1.0`/`vers=2.0` als Mount-Option ergaenzt werden — aktuell bewusst nicht hardcodiert, da
  moderne Windows-Versionen SMB1 standardmaessig deaktiviert haben und `mount.cifs` ohne
  `vers=`-Angabe automatisch aushandelt.
- Die Credentials-Datei (`data/network_share.cred`) liegt im `data/`-Verzeichnis, das bereits
  gitignored ist (wie `config.json`, `*.db`) — keine zusaetzliche `.gitignore`-Aenderung noetig,
  aber im Implementierungsschritt verifizieren.
- Perspektivisch koennte dieselbe Sync-Engine auch fuer ein zweites Freigabe-Ziel (z.B. Backup-NAS)
  erweitert werden — aktuell bewusst auf ein Ziel beschraenkt, um die UI einfach zu halten.

---

## Implementierungsnotizen

**Implementiert:** 2026-06-12

### Zusammenfassung

Neues Modul `network_storage_manager.py` implementiert SMB/CIFS-Mount, Verbindungstest, PDF- und
Capture-Sync sowie einen Hintergrund-Sync-Thread (analog zur USB-Synchronisation). `app.py` erhielt
4 neue Routen (`GET/POST /api/storage/network/config`, `GET /api/storage/network/status`,
`POST /api/storage/network/test`, `POST /api/storage/network/sync`) und startet
`start_network_sync()` beim Boot. `settings.html` erhielt eine neue Card "Netzwerk-Speicherort" im
Tab "Geraete & Netzwerk" mit Formular, Status-Badge, Verbindungstest- und Sofort-Sync-Buttons.
CLAUDE.md wurde mit den neuen Endpunkten und einer Feature-Beschreibung aktualisiert. Alles wurde
auf den Pi (192.168.0.171) deployed, der Service neu gestartet und end-to-end gegen einen
nicht-existenten Test-Share validiert (Mount-Fehler korrekt erkannt, uebersetzt und in
`last_error` persistiert; Hintergrund-Thread laeuft stabil mit 60s-Mount-Backoff).

### Abweichungen vom Plan

- **Schritt 2 (Sudoers-Erweiterung) entfiel**: Die bestehende Zeile in
  `/etc/sudoers.d/docucontrol-storage` (`NOPASSWD: /usr/bin/mount, /usr/bin/umount, ...`) erlaubt
  bereits `sudo mount -t cifs ...` ohne Passwort, da sudoers Pfad-Matches unabhaengig von den
  Argumenten erlaubt (sofern keine Argument-Restriktion definiert ist). Empirisch verifiziert mit
  `sudo -n mount -t cifs //127.0.0.1/nonexistent ...` — kein Passwort verlangt. Keine
  Sudoers-Datei geaendert.
- `_translate_mount_error()` wurde um `error(113)` / `"could not connect"` ergaenzt (im Plan nicht
  explizit aufgefuehrt, aber von der `error(112)`/`unreachable`-Kategorie "Server nicht erreichbar"
  abgedeckt) — beim Testen gegen eine nicht erreichbare IP lieferte `mount.cifs` `error(113)`
  statt `error(112)`.

### Aufgetretene Probleme

- **scp-Zielpfad**: `scp` mit mehreren Quelldateien und einem Zielverzeichnis ohne Trailing-Slash
  legte `settings.html` versehentlich flach in `/home/docucontrol/docupi/` statt in
  `templates/` ab. Erkannt und behoben (Datei in `templates/` kopiert, Fehlkopie geloescht).
- **Lokale Python-Pruefung nicht moeglich**: `python3` ist unter Windows nicht verfuegbar
  (Microsoft-Store-Alias). Syntax-/Import-Checks wurden stattdessen direkt auf dem Pi via SSH
  durchgefuehrt (`python3 -m py_compile app.py`, `python3 -c "import network_storage_manager"`).
- **Kein echter SMB-Server im Testnetz verfuegbar**: Der End-to-End-Test mit einer echten Freigabe
  (Mount + Sync von Dateien) konnte nicht durchgefuehrt werden. Stattdessen wurde der
  Fehlerpfad vollstaendig verifiziert (Validierung, Mount-Fehlschlag, Fehleruebersetzung,
  Hintergrund-Thread-Backoff, Service-Stabilitaet). Die Test-Konfiguration
  (`192.168.0.50`/`DocuTest`/`tester`/`geheim123`) wurde nach der Validierung wieder auf die
  Defaults (`enabled:false`, alle Felder leer) zurueckgesetzt und die Credentials-Datei geloescht,
  damit der Hintergrund-Thread im Produktivbetrieb nicht gegen eine Fantom-Freigabe retried.
  **Naechster Schritt vor Ort**: mit einer echten Windows-Freigabe im Tierlabor/Kliniknetz
  konfigurieren und den verbleibenden Checklistenpunkt abschliessen.
