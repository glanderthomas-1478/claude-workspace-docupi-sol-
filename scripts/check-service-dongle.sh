#!/bin/bash
# check-service-dongle.sh
# PAM-Helper fuer DocuControl-SOL: SSH-Login nur mit eingestecktem
# Service-Dongle (USB-Stick mit Label SOLDONGLE) erlauben.
#
# Einbindung in /etc/pam.d/sshd (Zeile direkt nach pam_nologin.so):
#   account    required     pam_exec.so /usr/local/bin/check-service-dongle.sh
#
# WICHTIG: Bevor diese PAM-Regel aktiviert wird, unbedingt einen physischen
# Not-Zugang einrichten (z.B. `systemctl enable --now getty@tty2.service`),
# falls SSH der einzige Zugangsweg zum Geraet ist (z.B. weil getty@tty1
# fuer den Kiosk deaktiviert wurde). /etc/pam.d/login ist von dieser Regel
# NICHT betroffen, ein lokaler Konsolen-Login bleibt also immer moeglich.
#
# Deploy-Schritte auf dem Ziel-Pi:
#   sudo cp check-service-dongle.sh /usr/local/bin/check-service-dongle.sh
#   sudo chmod 755 /usr/local/bin/check-service-dongle.sh
#   sudo cp /etc/pam.d/sshd /etc/pam.d/sshd.bak
#   sudo sed -i '/^account.*required.*pam_nologin.so/a account    required     pam_exec.so /usr/local/bin/check-service-dongle.sh' /etc/pam.d/sshd
#
# Test IMMER zuerst mit einer zweiten, parallelen SSH-Verbindung durchfuehren
# (bestehende Sitzung offen lassen!), bevor man sich abmeldet.

if /usr/bin/lsblk -rno LABEL 2>/dev/null | grep -qx "SOLDONGLE"; then
    exit 0
fi
exit 1
