#!/bin/bash
# setup_luks_sd_failover.sh -- Verschluesselter Notfall-Klon der SSD auf die SD-Karte.
#
# Anders als die SSD (bootet automatisch OHNE Dongle, Keyfile liegt auf der
# eigenen Boot-Partition) bekommt die SD-Karte KEIN Keyfile auf ihrer eigenen
# Boot-Partition -- das Keyscript findet dort nichts und faellt automatisch auf
# die USB-Dongle-Suche zurueck. Die SD-Karte ist damit nur mit einem der beiden
# SOLDONGLE-Sticks (oder der Backup-Passphrase) entschluesselbar/lesbar.
#
# Beide physischen Dongles funktionieren unveraendert auch fuer die SD-Karte,
# da dasselbe Keyfile (docupi-sol.key) als LUKS-Schluessel wiederverwendet wird.
#
# WARNUNG: Loescht /dev/mmcblk0 komplett. Nur auf dem SOL-Pi mit der SD-Karte
# als /dev/mmcblk0 ausfuehren, NIEMALS auf /dev/nvme0n1 (die laufende SSD)!
set -e
set -x

SD=/dev/mmcblk0
NVME_KEYFILE=/boot/firmware/docupi-sol.key
BACKUP_PASSPHRASE_FILE=/root/.sd_backup_passphrase.tmp

if [ "$(blockdev --getsize64 "$SD")" -gt 200000000000 ]; then
    echo "FEHLER: $SD ist groesser als 200GB, sieht nicht nach der SD-Karte aus. Abbruch."
    exit 1
fi

# ─── 1. Partitionen formatieren (bestehende Tabelle: p1=Boot 512M, p2=Rest) ───
umount ${SD}p1 2>/dev/null || true
umount ${SD}p2 2>/dev/null || true
mkfs.vfat -F 32 -n bootfs ${SD}p1

# ─── 2. LUKS2-Container auf p2 anlegen, gleiches Keyfile + Backup-Passphrase ───
cryptsetup luksFormat --type luks2 --label docupi-sol-sd-root --batch-mode \
    ${SD}p2 "$NVME_KEYFILE"

printf '%s' "$1" > "$BACKUP_PASSPHRASE_FILE"
chmod 600 "$BACKUP_PASSPHRASE_FILE"
# --key-slot 1 explizit angeben: ohne dieses Flag landete die Passphrase beim
# Testlauf 2026-07-08 in einem Zustand, der sich per Datei pruefen liess, aber
# nicht per interaktiver Tastatureingabe entsperrte (Ursache nicht abschliessend
# geklaert) - mit explizitem --key-slot funktionierte danach beides zuverlaessig.
cryptsetup luksAddKey ${SD}p2 "$BACKUP_PASSPHRASE_FILE" --key-file "$NVME_KEYFILE" --key-slot 1
rm -f "$BACKUP_PASSPHRASE_FILE"

cryptsetup open ${SD}p2 cryptroot_sd --key-file "$NVME_KEYFILE"
mkfs.ext4 -F -L rootfs /dev/mapper/cryptroot_sd

# ─── 3. Mounten ───
mkdir -p /mnt/sdclone
mount /dev/mapper/cryptroot_sd /mnt/sdclone
mkdir -p /mnt/sdclone/boot/firmware
mount ${SD}p1 /mnt/sdclone/boot/firmware

# ─── 4. Root-Dateisystem kopieren (Docker-Layer ausgeschlossen, siehe Referenz) ───
mkdir -p /mnt/sdclone/var/lib/docker
rsync -aHAXx --info=progress2 \
    --exclude=/proc/* --exclude=/sys/* --exclude=/dev/* \
    --exclude=/tmp/* --exclude=/run/* --exclude=/mnt/* --exclude=/media/* \
    --exclude=/lost+found --exclude=/var/lib/docker/* \
    / /mnt/sdclone/

# ─── 5. Boot-Partition kopieren, ABER OHNE das Keyfile (Sicherheitskern!) ───
rsync -aHAX --info=progress2 \
    --exclude=docupi-sol.key \
    /boot/firmware/ /mnt/sdclone/boot/firmware/

if [ -f /mnt/sdclone/boot/firmware/docupi-sol.key ]; then
    echo "FEHLER: Keyfile wurde trotz Ausschluss kopiert. Abbruch, SD bleibt unfertig."
    exit 1
fi

# ─── 6. UUIDs ermitteln und fstab/crypttab/cmdline.txt auf der SD anpassen ───
SD_LUKS_UUID=$(cryptsetup luksUUID ${SD}p2)
SD_ROOT_UUID=$(blkid -s UUID -o value /dev/mapper/cryptroot_sd)
SD_BOOT_UUID=$(blkid -s UUID -o value ${SD}p1)

cat > /mnt/sdclone/etc/crypttab <<EOF
# DocuControl-SOL SD-Notfall-Klon: NUR per USB-Service-Dongle oder
# Backup-Passphrase entschluesselbar (kein Keyfile auf der SD-Boot-Partition,
# bewusst anders als die SSD).
cryptroot  UUID=${SD_LUKS_UUID}  none  luks,keyscript=/lib/cryptsetup/scripts/docupi-sol-usb.sh
EOF

sed -i "s|UUID=[a-f0-9-]*  /  |UUID=${SD_ROOT_UUID}  /  |" /mnt/sdclone/etc/fstab
sed -i "s|UUID=[A-F0-9-]*  /boot/firmware|UUID=${SD_BOOT_UUID}  /boot/firmware|" /mnt/sdclone/etc/fstab

sed -i "s/cryptdevice=UUID=[a-f0-9-]*:cryptroot/cryptdevice=UUID=${SD_LUKS_UUID}:cryptroot/" \
    /mnt/sdclone/boot/firmware/cmdline.txt

echo "=== SD fstab ==="
cat /mnt/sdclone/etc/fstab
echo "=== SD crypttab ==="
cat /mnt/sdclone/etc/crypttab
echo "=== SD cmdline.txt ==="
cat /mnt/sdclone/boot/firmware/cmdline.txt

# ─── 7. Initramfs im Chroot neu bauen (muss die SD-eigene crypttab-UUID kennen) ───
for d in proc sys dev dev/pts run; do
    mkdir -p /mnt/sdclone/$d
    mount --bind /$d /mnt/sdclone/$d
done

chroot /mnt/sdclone update-initramfs -u -k all

for d in dev/pts run dev sys proc; do
    umount /mnt/sdclone/$d
done

# ─── 8. Aufraeumen ───
sync
umount /mnt/sdclone/boot/firmware
umount /mnt/sdclone
cryptsetup close cryptroot_sd

echo "=== SD-NOTFALL-KLON FERTIG ==="
echo "LUKS-UUID der SD-Karte: ${SD_LUKS_UUID}"
