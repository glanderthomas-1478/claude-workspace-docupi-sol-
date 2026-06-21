#!/bin/bash
# migrate_sd_to_nvme.sh
# Klont das laufende Raspberry-Pi-OS-System (SD-Karte) auf eine neue NVMe-SSD
# und richtet den Pi so ein, dass er danach von der SSD bootet.
#
# WICHTIG: Dieses Skript NICHT von der Claude-Sandbox aus ausfuehren --
# es gibt von dort keinen Netzwerkzugriff auf den Pi. Per SSH auf den Pi
# einloggen und dort manuell ausfuehren:
#
#   ssh docucontrol
#   sudo bash migrate_sd_to_nvme.sh --target /dev/nvme0n1 --confirm
#
# Die SD-Karte bleibt danach unveraendert (Fallback falls SSD-Boot scheitert).
#
# Ablauf:
#   1. Sicherheitschecks (Zielgeraet existiert, ist nicht das aktuelle Root-Device)
#   2. Partitionierung der SSD (boot FAT32 ~512MB + root ext4 Rest)
#   3. rsync von /boot/firmware und / auf die neuen Partitionen
#   4. cmdline.txt + fstab auf neue PARTUUIDs umschreiben
#   5. EEPROM-Boot-Reihenfolge auf NVMe-first setzen (rpi-eeprom-config)
#   6. Reboot-Hinweis (SD-Karte kann danach drin bleiben oder raus)

set -euo pipefail

TARGET=""
CONFIRM=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target) TARGET="$2"; shift 2 ;;
        --confirm) CONFIRM=1; shift ;;
        *) echo "Unbekannte Option: $1"; exit 1 ;;
    esac
done

if [[ -z "$TARGET" ]]; then
    echo "Nutzung: sudo bash migrate_sd_to_nvme.sh --target /dev/nvme0n1 --confirm"
    echo ""
    echo "Verfuegbare Block-Devices:"
    lsblk -d -o NAME,SIZE,MODEL,TRAN
    exit 1
fi

if [[ ! -b "$TARGET" ]]; then
    echo "FEHLER: $TARGET ist kein Block-Device."
    exit 1
fi

ROOT_SRC=$(findmnt -n -o SOURCE /)
ROOT_DISK=$(lsblk -no PKNAME "$ROOT_SRC" 2>/dev/null || true)
if [[ -n "$ROOT_DISK" && "/dev/$ROOT_DISK" == "$TARGET" ]]; then
    echo "FEHLER: $TARGET ist das aktuelle Root-Geraet (SD-Karte). Abbruch."
    exit 1
fi

echo "=== SD -> NVMe Migration ==="
echo "Quelle (aktuelles Root): $ROOT_SRC"
echo "Ziel (wird ueberschrieben): $TARGET"
lsblk "$TARGET"
echo ""

if [[ "$CONFIRM" -ne 1 ]]; then
    echo "Trockenlauf beendet (kein --confirm angegeben). Es wurde NICHTS geschrieben."
    echo "Wenn das Zielgeraet oben korrekt ist, erneut mit --confirm ausfuehren."
    exit 0
fi

read -rp "Letzte Warnung: ALLE Daten auf $TARGET werden geloescht. Wirklich fortfahren? (ja/nein) " ans
if [[ "$ans" != "ja" ]]; then
    echo "Abgebrochen."
    exit 0
fi

echo "[1/6] Partitioniere $TARGET ..."
sudo umount "${TARGET}"p1 2>/dev/null || true
sudo umount "${TARGET}"p2 2>/dev/null || true
sudo parted -s "$TARGET" mklabel gpt
sudo parted -s "$TARGET" mkpart fat32 1MiB 513MiB
sudo parted -s "$TARGET" set 1 boot on
sudo parted -s "$TARGET" mkpart ext4 513MiB 100%
partprobe "$TARGET"
sleep 2

BOOT_PART="${TARGET}p1"
ROOT_PART="${TARGET}p2"

echo "[2/6] Formatiere Partitionen ..."
sudo mkfs.vfat -F 32 -n bootfs "$BOOT_PART"
sudo mkfs.ext4 -F -L rootfs "$ROOT_PART"

echo "[3/6] Mounte Ziel ..."
sudo mkdir -p /mnt/nvme_root /mnt/nvme_boot
sudo mount "$ROOT_PART" /mnt/nvme_root
sudo mount "$BOOT_PART" /mnt/nvme_boot

echo "[4/6] Kopiere Root-Dateisystem (rsync, das kann einige Minuten dauern) ..."
sudo rsync -axHAWX --numeric-ids --info=progress2 \
    --exclude="/boot/firmware/*" \
    --exclude="/proc/*" --exclude="/sys/*" --exclude="/dev/*" \
    --exclude="/tmp/*" --exclude="/run/*" --exclude="/mnt/*" --exclude="/media/*" \
    --exclude="/lost+found" \
    / /mnt/nvme_root/

echo "[5/6] Kopiere Boot-Partition ..."
sudo rsync -axHAWX --numeric-ids --info=progress2 /boot/firmware/ /mnt/nvme_boot/

echo "[6/6] Passe cmdline.txt + fstab fuer das neue Root-Geraet an ..."
ROOT_PARTUUID=$(sudo blkid -s PARTUUID -o value "$ROOT_PART")
BOOT_PARTUUID=$(sudo blkid -s PARTUUID -o value "$BOOT_PART")

sudo sed -i "s|root=PARTUUID=[a-f0-9-]*|root=PARTUUID=${ROOT_PARTUUID}|" /mnt/nvme_boot/cmdline.txt
echo "Neue cmdline.txt:"
cat /mnt/nvme_boot/cmdline.txt

sudo sed -i "s|PARTUUID=[a-f0-9-]*\s\+/boot/firmware|PARTUUID=${BOOT_PARTUUID}  /boot/firmware|" /mnt/nvme_root/etc/fstab
sudo sed -i "s|PARTUUID=[a-f0-9-]*\s\+/\s|PARTUUID=${ROOT_PARTUUID}  / |" /mnt/nvme_root/etc/fstab
echo "Neue fstab:"
cat /mnt/nvme_root/etc/fstab

echo ""
echo "=== EEPROM Boot-Reihenfolge auf NVMe-first setzen ==="
CONFIG_TMP=$(mktemp)
sudo rpi-eeprom-config > "$CONFIG_TMP"
if grep -q "^BOOT_ORDER=" "$CONFIG_TMP"; then
    sudo sed -i "s|^BOOT_ORDER=.*|BOOT_ORDER=0xf416|" "$CONFIG_TMP"
else
    echo "BOOT_ORDER=0xf416" | sudo tee -a "$CONFIG_TMP" > /dev/null
fi
sudo rpi-eeprom-config --apply "$CONFIG_TMP"
rm -f "$CONFIG_TMP"

sudo umount /mnt/nvme_root /mnt/nvme_boot

echo ""
echo "=== Migration abgeschlossen ==="
echo "Naechste Schritte:"
echo "  1. sudo reboot"
echo "  2. Nach dem Neustart pruefen: mount | grep ' / ' -- sollte ${ROOT_PART} zeigen"
echo "  3. SD-Karte kann danach als Backup drinbleiben oder entfernt werden"
echo "  4. docucontrol.service Status pruefen: systemctl status docucontrol.service"
