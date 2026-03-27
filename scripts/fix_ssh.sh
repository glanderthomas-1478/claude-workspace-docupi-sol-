#!/bin/bash
# Fix SSH + DNS for hotspot coexistence
# Run as: sudo bash /home/belimed/docupi/fix_ssh.sh

# 1. Fix sshd - disable DNS lookup (causes timeout when dnsmasq runs)
grep -q "UseDNS no" /etc/ssh/sshd_config || echo "UseDNS no" >> /etc/ssh/sshd_config
grep -q "GSSAPIAuthentication no" /etc/ssh/sshd_config || echo "GSSAPIAuthentication no" >> /etc/ssh/sshd_config

# 2. Restart sshd
systemctl restart sshd

echo "SSH fix applied"
