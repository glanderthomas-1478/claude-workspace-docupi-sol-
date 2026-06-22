#!/bin/bash
set -e
set -x

# Format SD card partitions (existing partition table reused: p1=boot FAT32, p2=root ext4)
mkfs.vfat -F 32 -n bootfs /dev/mmcblk0p1
mkfs.ext4 -F -L rootfs /dev/mmcblk0p2

mkdir -p /mnt/sdclone
mount /dev/mmcblk0p2 /mnt/sdclone
mkdir -p /mnt/sdclone/boot/firmware
mount /dev/mmcblk0p1 /mnt/sdclone/boot/firmware

# /var/lib/docker ausgeschlossen: vfs-Storage-Driver dupliziert jeden Layer voll
# (29G / 680k+ Einzeldateien) - auf microSD viel zu langsam und unnoetig, da
# 'docker-compose build' das Image beim ersten Start auf der SD-Karte neu baut.
mkdir -p /mnt/sdclone/var/lib/docker

rsync -aHAXx --info=progress2 \
  --exclude=/proc/* --exclude=/sys/* --exclude=/dev/* \
  --exclude=/tmp/* --exclude=/run/* --exclude=/mnt/* --exclude=/media/* \
  --exclude=/lost+found --exclude=/var/lib/docker/* \
  / /mnt/sdclone/

# WICHTIG: die obige rsync nutzt -x ("keine Dateisystemgrenzen ueberschreiten"),
# das gilt fuer die gesamte / -Hierarchie. /boot/firmware ist auf der Quelle
# (NVMe) ein eigenes Dateisystem (eigene Partition) - wird von -x deshalb
# komplett UEBERSPRUNGEN und muss separat (ohne -x) kopiert werden, sonst hat
# die SD-Karte keinen funktionierenden Bootloader (kein start4.elf/cmdline.txt)!
rsync -aHAX --info=progress2 /boot/firmware/ /mnt/sdclone/boot/firmware/

# Fix PARTUUID references on the SD clone to point to the SD's own partitions
SD_BOOT_PARTUUID=$(blkid -s PARTUUID -o value /dev/mmcblk0p1)
SD_ROOT_PARTUUID=$(blkid -s PARTUUID -o value /dev/mmcblk0p2)

sed -i "s/PARTUUID=[a-f0-9-]*[ \t]\+\/boot\/firmware/PARTUUID=${SD_BOOT_PARTUUID}  \/boot\/firmware/" /mnt/sdclone/etc/fstab
sed -i "s/PARTUUID=[a-f0-9-]*[ \t]\+\/[ \t]/PARTUUID=${SD_ROOT_PARTUUID}  \/  /" /mnt/sdclone/etc/fstab

sed -i "s/root=PARTUUID=[a-f0-9-]*/root=PARTUUID=${SD_ROOT_PARTUUID}/" /mnt/sdclone/boot/firmware/cmdline.txt

echo "=== SD fstab ==="
cat /mnt/sdclone/etc/fstab
echo "=== SD cmdline.txt ==="
cat /mnt/sdclone/boot/firmware/cmdline.txt

sync
umount /mnt/sdclone/boot/firmware
umount /mnt/sdclone
echo "=== CLONE DONE ==="
