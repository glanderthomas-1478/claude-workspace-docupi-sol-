#!/bin/bash
# Kiosk-Display Setup fuer DocuControl Pi
# Installiert cage (Wayland) + Chromium Kiosk-Modus auf dem Pi.
# Ausfuehren: bash scripts/setup_kiosk_display.sh
#
# Technischer Hintergrund: Pi 5 hat zwei DRM-Devices (card0=vc4 Display, card1=V3D GPU).
# X.org schlaegt fehl weil es ohne BusID nicht zwischen beiden unterscheiden kann.
# cage (Wayland-Kiosk-Compositor) loest das Problem direkt auf KMS-Ebene.
#
# Hinweis: sudo benoetigt Passwort + use_pty im sudoers.
# Das Skript schreibt ein Setup-Skript nach /tmp und fuehrt es per ssh -tt + sudo -S aus.

set -e

SSH_TARGET="docucontrol@192.168.0.181"
SSH_OPTS="-o StrictHostKeyChecking=no"
SUDO_PW="Xtend1478"

echo "=== DocuControl Kiosk-Display Setup ==="
echo "Ziel: $SSH_TARGET"
echo ""

# ---------------------------------------------------------------------------
# Block A: Setup-Skript auf Pi laden (kein sudo noetig fuer /tmp)
# ---------------------------------------------------------------------------
echo "[1/3] Setup-Skript auf Pi laden..."
ssh $SSH_OPTS "$SSH_TARGET" "tee /tmp/kiosk_setup.sh > /dev/null" << 'SSHEOF'
#!/bin/bash
set -e

echo "  [A] Pakete installieren..."
apt-get update -qq
apt-get install -y \
  cage \
  chromium \
  fonts-liberation \
  wvkbd
echo "      Pakete installiert."

echo "  [B] Autologin systemd-Override..."
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << 'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin docucontrol --noclear %I $TERM
EOF
systemctl daemon-reload
echo "      Autologin konfiguriert."

echo "  [C] kiosk_start.sh erstellen..."
cat > /home/docucontrol/cursor_corner.py << 'EOF'
#!/usr/bin/env python3
# Mauszeiger einmalig in die untere rechte Ecke schieben.
# Benoetigt: python3-evdev, /dev/uinput schreibbar fuer Gruppe input.
import time
from evdev import UInput, ecodes as e
with UInput({e.EV_REL: [e.REL_X, e.REL_Y]}, name='cursor-hide') as ui:
    for _ in range(30):
        ui.write(e.EV_REL, e.REL_X, 1000)
        ui.write(e.EV_REL, e.REL_Y, 1000)
        ui.syn()
        time.sleep(0.02)
EOF
chmod +x /home/docucontrol/cursor_corner.py
chown docucontrol:docucontrol /home/docucontrol/cursor_corner.py

# udev-Regel: /dev/uinput fuer Gruppe input beschreibbar (persistent nach Reboot)
cat > /etc/udev/rules.d/99-uinput.conf << 'EOF'
KERNEL=="uinput", GROUP="input", MODE="0660"
EOF
udevadm control --reload-rules

# python3-evdev installieren
apt-get install -y python3-evdev -qq

cat > /home/docucontrol/kiosk_start.sh << 'EOF'
#!/bin/bash
# Kiosk-Starter: Aufloesung setzen, Mauszeiger verstecken, Chromium starten.
# Laeuft als cage-Anwendung (WAYLAND_DISPLAY gesetzt).
wlr-randr --output HDMI-A-1 --mode 1280x800 2>/dev/null || true
# Mauszeiger nach 3s in untere rechte Ecke schieben
(sleep 3 && python3 /home/docucontrol/cursor_corner.py) &
# Virtuelle Tastatur: zeigt sich automatisch bei Eingabefeldauswahl (Wayland text_input)
wvkbd-mobintl --landscape --hidden &
exec chromium \
  --kiosk \
  --incognito \
  --no-first-run \
  --disable-translate \
  --disable-infobars \
  --disable-features=TranslateUI \
  --disable-session-crashed-bubble \
  --disable-restore-session-state \
  --disable-pinch \
  --noerrdialogs \
  --check-for-update-interval=31536000 \
  --enable-zero-copy \
  --ignore-gpu-blocklist \
  http://localhost:5000
EOF
chmod +x /home/docucontrol/kiosk_start.sh
chown docucontrol:docucontrol /home/docucontrol/kiosk_start.sh
echo "      kiosk_start.sh erstellt."

echo "  [C] ~/.bash_profile konfigurieren..."
# Alte Eintraege entfernen (Idempotenz)
sed -i '/exec startx/d' /home/docucontrol/.bash_profile 2>/dev/null || true
sed -i '/exec cage/d' /home/docucontrol/.bash_profile 2>/dev/null || true
sed -i '/Kiosk:/d' /home/docucontrol/.bash_profile 2>/dev/null || true
sed -i '/if \[\[ -z.*DISPLAY/,/^fi$/d' /home/docucontrol/.bash_profile 2>/dev/null || true

cat >> /home/docucontrol/.bash_profile << 'EOF'

# Kiosk: Starte cage (Wayland) automatisch auf TTY1
if [[ -z "$WAYLAND_DISPLAY" && -z "$DISPLAY" && "$(tty)" == "/dev/tty1" ]]; then
  exec cage -- /home/docucontrol/kiosk_start.sh
fi
EOF
chown docucontrol:docucontrol /home/docucontrol/.bash_profile
echo "      ~/.bash_profile aktualisiert."

echo ""
echo "=== Kiosk-Setup abgeschlossen ==="
SSHEOF
echo "      Setup-Skript geladen."

# ---------------------------------------------------------------------------
# Block B: Setup-Skript mit sudo ausfuehren
# ---------------------------------------------------------------------------
echo "[2/3] Setup-Skript mit sudo ausfuehren..."
ssh -tt $SSH_OPTS "$SSH_TARGET" "echo '${SUDO_PW}' | sudo -S -p '' bash /tmp/kiosk_setup.sh" 2>/dev/null
echo "      Setup abgeschlossen."

# ---------------------------------------------------------------------------
# Block C: Neustart
# ---------------------------------------------------------------------------
echo "[3/3] Pi wird neugestartet..."
echo ""
echo "  Nach dem Reboot:"
echo "  - cage + Chromium starten automatisch im Vollbild mit localhost:5000"
echo "  - SSH bleibt erreichbar: ssh docucontrol@192.168.0.181"
echo "  - Recovery: Ctrl+Alt+F2 am Display oder via SSH"
echo "  - Display rotieren: in ~/.bash_profile den cage-Aufruf mit 'cage -r' erweitern"
echo ""
ssh -tt $SSH_OPTS "$SSH_TARGET" "echo '${SUDO_PW}' | sudo -S -p '' reboot" 2>/dev/null || true
echo "Reboot-Befehl gesendet."
