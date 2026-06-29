#!/bin/bash
# setup_luks_nvme.sh
# LUKS-Verschluesselung fuer neue DocuControl-Deployments (NVMe-SSD)
#
# Schutzziel:
#   a) Physischer Diebstahl: Root-Partition ohne USB-Dongle nicht lesbar
#   c) Quellcode-Schutz: Python-Code liegt auf verschluesselter Partition,
#      nicht auslesbar ohne den USB-Dongle
#
# Ablauf:
#   1. NVMe partitionieren (Boot FAT32 unverschluesselt + LUKS-Root)
#   2. Keyfile auf USB-Dongle generieren + Backup-Passphrase setzen
#   3. Verschluesselte Root-Partition formatieren
#   4. OS von laufender SD-Karte in verschluesseltes NVMe kopieren (rsync)
#   5. Zielsystem konfigurieren (crypttab, fstab, cmdline.txt)
#   6. USB-Keyfile-Hook fuer initramfs installieren
#   7. initramfs neu bauen (chroot)
#   8. EEPROM-Boot-Reihenfolge auf NVMe setzen
#
# Unlock-Mechanismus:
#   - Beim Boot sucht das initramfs nach einem USB-Stick mit der Datei
#     "docucontrol.key" und entschluesselt damit automatisch die SSD
#   - Kein Passwort-Dialog wenn Dongle eingesteckt
#   - Fallback auf manuelle Passphrase wenn Dongle fehlt (Notfall)
#   - Dongle bleibt beim Techniker, nicht beim Kunden
#
# Voraussetzungen:
#   - Pi 5 bootet von SD-Karte (Raspberry Pi OS / Debian Trixie)
#   - NVMe-SSD eingesteckt (/dev/nvme0n1 oder anpassen)
#   - USB-Dongle fuer Keyfile eingesteckt (z.B. /dev/sda1 oder anpassen)
#   - Netzwerkzugang fuer apt-Pakete
#
# Ausfuehren auf dem Pi (nicht von der Claude-Sandbox):
#   ssh docucontrol
#   sudo bash setup_luks_nvme.sh --nvme /dev/nvme0n1 --usb /dev/sda1 --confirm
#
# WARNUNG: --nvme-Geraet wird VOLLSTAENDIG GELOESCHT (Partitionierung)!

set -euo pipefail

# ============================================================================
# Argumente
# ============================================================================

NVME_DEV=""
USB_DEV=""
CONFIRM=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --nvme)   NVME_DEV="$2"; shift 2 ;;
        --usb)    USB_DEV="$2"; shift 2 ;;
        --confirm) CONFIRM=1; shift ;;
        *)
            echo "Unbekanntes Argument: $1"
            echo "Verwendung: sudo bash $0 --nvme /dev/nvme0n1 --usb /dev/sda1 --confirm"
            exit 1
            ;;
    esac
done

if [[ -z "$NVME_DEV" || -z "$USB_DEV" ]]; then
    echo "Fehler: --nvme und --usb sind Pflichtparameter."
    echo "Verwendung: sudo bash $0 --nvme /dev/nvme0n1 --usb /dev/sda1 --confirm"
    echo ""
    echo "Verfuegbare Block-Geraete:"
    lsblk -d -o NAME,SIZE,TYPE,MODEL
    exit 1
fi

if [[ $CONFIRM -ne 1 ]]; then
    echo "Sicherheitssperre: --confirm fehlt."
    echo "Bitte nochmals lesen und --confirm hinzufuegen wenn klar ist, dass"
    echo "$NVME_DEV komplett geloescht wird."
    exit 1
fi

# ============================================================================
# Konfiguration (anpassen falls noetig)
# ============================================================================

NVME_BOOT="${NVME_DEV}p1"       # Boot-Partition (FAT32, unverschluesselt)
NVME_ROOT="${NVME_DEV}p2"       # Root-Partition (LUKS)
MAPPER_NAME="cryptroot"          # /dev/mapper/cryptroot
MOUNT_ROOT="/mnt/cryptroot"
MOUNT_BOOT="/mnt/cryptroot/boot/firmware"
USB_MOUNT="/mnt/docucontrol_key"
KEYFILE_NAME="docucontrol.key"
KEYSCRIPT_PATH="/lib/cryptsetup/scripts/docucontrol-usb.sh"

# ============================================================================
# Schritt 0: Voraussetzungen pruefen
# ============================================================================

echo "==================================================================="
echo " DocuControl LUKS-Setup fuer neues Deployment"
echo "==================================================================="
echo ""

[[ $EUID -eq 0 ]] || { echo "Fehler: sudo erforderlich"; exit 1; }

[[ -b "$NVME_DEV" ]] || {
    echo "Fehler: NVMe-Geraet $NVME_DEV nicht gefunden."
    lsblk -d -o NAME,SIZE,TYPE,MODEL
    exit 1
}

[[ -b "$USB_DEV" ]] || {
    echo "Fehler: USB-Geraet $USB_DEV nicht gefunden."
    lsblk -d -o NAME,SIZE,TYPE,MODEL
    exit 1
}

# NVMe darf nicht das aktuelle Root-Device sein
CURRENT_ROOT=$(findmnt -n -o SOURCE /)
if [[ "$CURRENT_ROOT" == "${NVME_DEV}"* ]]; then
    echo "Fehler: $NVME_DEV ist das aktuelle Root-Geraet -- Abbruch."
    exit 1
fi

# Pakete installieren
for pkg in cryptsetup cryptsetup-initramfs parted; do
    dpkg -l "$pkg" &>/dev/null || apt-get install -y "$pkg"
done

echo "NVMe : $(lsblk -d -o SIZE,MODEL "$NVME_DEV" | tail -1) — wird GELOESCHT"
echo "USB  : $(lsblk -d -o SIZE,MODEL "$USB_DEV" | tail -1) — Keyfile-Traeger"
echo ""

# ============================================================================
# Schritt 1: NVMe partitionieren
# ============================================================================

echo "--- Schritt 1: NVMe partitionieren ---"

# Bestehende Mounts und LUKS-Container schliessen
umount "${NVME_DEV}"p* 2>/dev/null || true
cryptsetup luksClose "$MAPPER_NAME" 2>/dev/null || true

parted -s "$NVME_DEV" \
    mklabel gpt \
    mkpart boot fat32 1MiB 513MiB \
    mkpart root ext4 513MiB 100% \
    set 1 boot on

partprobe "$NVME_DEV"
sleep 2

mkfs.vfat -F 32 -n bootfs "$NVME_BOOT"
echo "  Boot-Partition: $NVME_BOOT (FAT32, unverschluesselt)"
echo "  Root-Partition: $NVME_ROOT (wird LUKS)"

# ============================================================================
# Schritt 2: USB-Dongle vorbereiten + Keyfile generieren
# ============================================================================

echo ""
echo "--- Schritt 2: Keyfile auf USB-Dongle generieren ---"

mkdir -p "$USB_MOUNT"
mount "$USB_DEV" "$USB_MOUNT"

# Vorhandenen Keyfile nicht stillschweigend ueberschreiben
if [[ -f "$USB_MOUNT/$KEYFILE_NAME" ]]; then
    echo "  WARNUNG: $KEYFILE_NAME existiert bereits auf dem USB-Stick."
    read -rp "  Ueberschreiben? [ja/NEIN]: " OW
    [[ "$OW" == "ja" ]] || { umount "$USB_MOUNT"; echo "Abgebrochen."; exit 0; }
fi

echo "  Generiere 4096-Byte Zufalls-Keyfile..."
dd if=/dev/urandom of="$USB_MOUNT/$KEYFILE_NAME" bs=1 count=4096 status=none
chmod 400 "$USB_MOUNT/$KEYFILE_NAME"
sync
echo "  Gespeichert: $USB_MOUNT/$KEYFILE_NAME"
echo ""
echo "  *** WICHTIG: Diesen USB-Stick sicher aufbewahren. ***"
echo "  *** Ohne ihn kann die SSD nicht entschluesselt werden. ***"
echo "  *** Backup-Kopie des Keyfiles in secrets/-Ablage sichern! ***"
echo ""

# ============================================================================
# Schritt 3: LUKS-Container erstellen
# ============================================================================

echo "--- Schritt 3: LUKS-Container erstellen ---"
echo ""
echo "  LUKS-Format mit Keyfile (Slot 0) + Backup-Passphrase (Slot 1)."
echo "  Die Backup-Passphrase gilt fuer den Fall, dass der USB-Dongle verloren geht."
echo ""

cryptsetup luksFormat \
    --type luks2 \
    --cipher aes-xts-plain64 \
    --key-size 512 \
    --hash sha256 \
    --label "docucontrol-root" \
    --batch-mode \
    --key-file "$USB_MOUNT/$KEYFILE_NAME" \
    "$NVME_ROOT"

echo "  Slot 0: Keyfile gesetzt."
echo ""
echo "  Jetzt Backup-Passphrase eingeben (2x):"
cryptsetup luksAddKey \
    --key-file "$USB_MOUNT/$KEYFILE_NAME" \
    "$NVME_ROOT"
echo "  Slot 1: Backup-Passphrase gesetzt."

LUKS_UUID=$(cryptsetup luksUUID "$NVME_ROOT")
echo "  LUKS-UUID: $LUKS_UUID"

# ============================================================================
# Schritt 4: Verschluesselte Root-Partition oeffnen + formatieren
# ============================================================================

echo ""
echo "--- Schritt 4: Root-Partition oeffnen + ext4 erstellen ---"

cryptsetup luksOpen \
    --key-file "$USB_MOUNT/$KEYFILE_NAME" \
    "$NVME_ROOT" "$MAPPER_NAME"

mkfs.ext4 -L rootfs "/dev/mapper/$MAPPER_NAME"
echo "  /dev/mapper/$MAPPER_NAME: ext4 erstellt"

# ============================================================================
# Schritt 5: OS von SD auf NVMe kopieren
# ============================================================================

echo ""
echo "--- Schritt 5: OS von SD-Karte in verschluesselte NVMe kopieren ---"

mkdir -p "$MOUNT_ROOT"
mount "/dev/mapper/$MAPPER_NAME" "$MOUNT_ROOT"
mkdir -p "$MOUNT_BOOT"
mount "$NVME_BOOT" "$MOUNT_BOOT"

echo "  Kopiere Root-Dateisystem (rsync, ohne /boot/firmware und Docker)..."
rsync -aHAXx --info=progress2 \
    --exclude=/proc \
    --exclude=/sys \
    --exclude=/dev \
    --exclude=/run \
    --exclude=/tmp \
    --exclude=/mnt \
    --exclude=/media \
    --exclude=/boot/firmware \
    --exclude=/var/lib/docker \
    / "$MOUNT_ROOT/"

# /boot/firmware separat (ohne -x, da eigenes Dateisystem auf der Quelle)
echo "  Kopiere /boot/firmware..."
rsync -aHAX --info=progress2 /boot/firmware/ "$MOUNT_BOOT/"

mkdir -p "$MOUNT_ROOT/var/lib/docker"
echo "  Kopie abgeschlossen."

# ============================================================================
# Schritt 6: Zielsystem konfigurieren (crypttab, fstab, cmdline.txt)
# ============================================================================

echo ""
echo "--- Schritt 6: Zielsystem konfigurieren ---"

BOOT_UUID=$(blkid -s UUID -o value "$NVME_BOOT")
ROOT_UUID=$(blkid -s UUID -o value "/dev/mapper/$MAPPER_NAME")

# /etc/crypttab: LUKS-Container mit USB-Keyfile-Keyscript
cat > "$MOUNT_ROOT/etc/crypttab" << EOF
# DocuControl LUKS: entschluesselt automatisch via USB-Dongle (docucontrol.key)
# Fallback: Passphrase-Eingabe wenn Dongle nicht gefunden
$MAPPER_NAME  UUID=$LUKS_UUID  none  luks,keyscript=$KEYSCRIPT_PATH
EOF
echo "  /etc/crypttab gesetzt"

# /etc/fstab: verschluesselte Root-Partition
cat > "$MOUNT_ROOT/etc/fstab" << EOF
proc             /proc           proc  defaults            0 0
UUID=$ROOT_UUID  /               ext4  defaults,noatime    0 1
UUID=$BOOT_UUID  /boot/firmware  vfat  defaults,flush      0 2
EOF
echo "  /etc/fstab gesetzt"

# /boot/firmware/cmdline.txt: root auf /dev/mapper/cryptroot umstellen
CMDLINE=$(cat "$MOUNT_BOOT/cmdline.txt")
# root= ersetzen
CMDLINE=$(echo "$CMDLINE" | sed "s|root=[^ ]*|root=/dev/mapper/$MAPPER_NAME|")
# rootfstype auf ext4 sicherstellen
CMDLINE=$(echo "$CMDLINE" | sed "s|rootfstype=[^ ]*|rootfstype=ext4|")
# cryptdevice-Parameter hinzufuegen
if ! echo "$CMDLINE" | grep -q "cryptdevice"; then
    CMDLINE="$CMDLINE cryptdevice=UUID=$LUKS_UUID:$MAPPER_NAME"
fi
echo "$CMDLINE" > "$MOUNT_BOOT/cmdline.txt"
echo "  cmdline.txt gesetzt: $CMDLINE"

# ============================================================================
# Schritt 7: USB-Keyfile-Keyscript + initramfs-Hook installieren
# ============================================================================

echo ""
echo "--- Schritt 7: USB-Keyfile-Hook fuer initramfs installieren ---"

# Keyscript: wird im initramfs beim Boot ausgefuehrt.
# Durchsucht USB-Geraete nach docucontrol.key, gibt Inhalt auf stdout aus.
# cryptsetup liest den Keyfile-Inhalt von stdin.
install -D -m 755 /dev/stdin \
    "$MOUNT_ROOT$KEYSCRIPT_PATH" << 'KEYSCRIPT'
#!/bin/sh
# docucontrol-usb.sh — USB-Keyfile-Keyscript fuer LUKS
# Laeuft im initramfs. Sucht docucontrol.key auf USB-Geraeten.
# Gibt Keyfile-Inhalt auf stdout aus (cryptsetup liest stdin).
# Fallback: manuelle Passphrase-Eingabe.

KEYFILE="docucontrol.key"
TIMEOUT=15  # Sekunden warten auf USB-Erkennung
MNT="/tmp/usbkey_mnt"

mkdir -p "$MNT"

for i in $(seq 1 $TIMEOUT); do
    for dev in /dev/sd?1 /dev/sd? /dev/vd?1; do
        [ -b "$dev" ] || continue
        if mount -r "$dev" "$MNT" 2>/dev/null; then
            if [ -f "$MNT/$KEYFILE" ]; then
                cat "$MNT/$KEYFILE"
                umount "$MNT" 2>/dev/null
                exit 0
            fi
            umount "$MNT" 2>/dev/null
        fi
    done
    sleep 1
done

# Kein USB-Dongle gefunden -- Backup-Passphrase abfragen
echo "DocuControl: USB-Dongle nicht gefunden. Backup-Passphrase eingeben:" >&2
/lib/cryptsetup/askpass "Passphrase: "
KEYSCRIPT
echo "  Keyscript installiert: $MOUNT_ROOT$KEYSCRIPT_PATH"

# initramfs-Hook: kopiert Keyscript + USB-Module in das initramfs
install -D -m 755 /dev/stdin \
    "$MOUNT_ROOT/etc/initramfs-tools/hooks/docucontrol-luks" << HOOK
#!/bin/sh
# initramfs-Hook: stellt sicher, dass USB-Module und Keyscript im initramfs landen
PREREQS=""
prereqs() { echo "\$PREREQS"; }
case \$1 in prereqs) prereqs; exit 0;; esac

. /usr/share/initramfs-tools/hook-functions

# USB-Storage-Module fuer Dongle-Erkennung
manual_add_modules usb_storage sd_mod

# mount/umount fuer das Keyscript
copy_exec /bin/mount /bin
copy_exec /bin/umount /bin

# Keyscript selbst in initramfs kopieren
mkdir -p "\${DESTDIR}/lib/cryptsetup/scripts"
cp -p "$KEYSCRIPT_PATH" "\${DESTDIR}$KEYSCRIPT_PATH"
chmod 755 "\${DESTDIR}$KEYSCRIPT_PATH"
HOOK
echo "  initramfs-Hook installiert"

# initramfs im chroot neu bauen
echo "  Baue initramfs neu (chroot)..."
for fs in proc sys dev run; do
    mount --bind "/$fs" "$MOUNT_ROOT/$fs"
done

chroot "$MOUNT_ROOT" /bin/bash -c "
    export CRYPTSETUP=y
    update-initramfs -u -k all
" && echo "  initramfs neu gebaut." \
  || echo "  WARNUNG: initramfs-Neubau fehlgeschlagen -- nach erstem Boot nochmals: sudo update-initramfs -u -k all"

for fs in run dev sys proc; do
    umount "$MOUNT_ROOT/$fs" 2>/dev/null || true
done

# ============================================================================
# Schritt 8: EEPROM-Boot-Reihenfolge auf NVMe setzen
# ============================================================================

echo ""
echo "--- Schritt 8: EEPROM Boot-Reihenfolge ---"

EEPROM_TMP=$(mktemp)
rpi-eeprom-config > "$EEPROM_TMP"
if grep -q "^BOOT_ORDER=" "$EEPROM_TMP"; then
    sed -i "s/^BOOT_ORDER=.*/BOOT_ORDER=0xf61/" "$EEPROM_TMP"
else
    echo "BOOT_ORDER=0xf61" >> "$EEPROM_TMP"
fi
rpi-eeprom-config --apply "$EEPROM_TMP"
rm "$EEPROM_TMP"
echo "  BOOT_ORDER=0xf61 gesetzt (NVMe(6) > SD(1) > Stop(f))"
echo "  Wird beim naechsten Reboot aktiv."

# ============================================================================
# Aufraeum
# ============================================================================

echo ""
echo "--- Aufraeumen ---"

umount "$MOUNT_BOOT" 2>/dev/null || true
umount "$MOUNT_ROOT" 2>/dev/null || true
umount "$USB_MOUNT"  2>/dev/null || true
cryptsetup luksClose "$MAPPER_NAME" 2>/dev/null || true
rmdir "$MOUNT_ROOT" "$USB_MOUNT" 2>/dev/null || true

# ============================================================================
# Zusammenfassung
# ============================================================================

echo ""
echo "==================================================================="
echo " LUKS-Setup abgeschlossen"
echo "==================================================================="
echo ""
echo "  LUKS-UUID  : $LUKS_UUID"
echo "  Keyfile    : $USB_DEV -> $KEYFILE_NAME"
echo ""
echo "  Naechste Schritte:"
echo "  1. Keyfile-Backup anlegen:"
echo "     cp $USB_MOUNT/$KEYFILE_NAME /sicherer/Ort/docucontrol.key"
echo "     -> secrets/-Ablage im Projekt"
echo ""
echo "  2. SD-Karte entfernen, USB-Dongle einstecken, Pi neu starten:"
echo "     sudo reboot"
echo ""
echo "  3. Pi bootet von NVMe (LUKS), entschluesselt via USB-Dongle"
echo "     -> kein Passwort-Dialog wenn Dongle steckt"
echo ""
echo "  4. Docker-Setup normal abschliessen:"
echo "     cd /home/docucontrol/docupi && sudo docker-compose up -d"
echo ""
echo "  5. Danach USB-Dongle abstecken (bleibt beim Techniker)"
echo "     -> Kiosk laeuft normal weiter (Dongle nur fuer Boot benoetigt)"
echo ""
echo "  Notfall (Dongle verloren):"
echo "  - Boot ohne Dongle -> Passphrase-Eingabe erscheint automatisch"
echo "  - Backup-Passphrase aus secrets/-Ablage verwenden"
echo ""
echo "  HINWEIS Docker:"
echo "  - Docker (overlay2 oder vfs) ist vollstaendig LUKS-kompatibel"
echo "  - Keine Sonderkonfiguration noetig, LUKS ist transparent"
echo "==================================================================="
