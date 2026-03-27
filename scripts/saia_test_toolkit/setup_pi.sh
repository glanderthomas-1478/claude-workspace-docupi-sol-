#!/bin/bash
# DocuPi 3000 - Setup für Raspberry Pi
# ======================================
# Installiert alle Abhängigkeiten für den SAIA-Test

echo "═══════════════════════════════════════════════════"
echo "  DocuPi 3000 - Raspberry Pi Setup"
echo "═══════════════════════════════════════════════════"

echo "📦 Installiere System-Pakete..."
sudo apt update
sudo apt install -y libsnap7-dev python3-pip

echo ""
echo "📦 Installiere Python-Pakete..."
pip3 install -r "$(dirname "$0")/requirements.txt" --break-system-packages

echo ""
echo "📦 Füge User zur dialout-Gruppe hinzu (USB-Serial Zugriff)..."
sudo usermod -aG dialout $USER
echo "   ⚠️  Ggf. Ab- und wieder Anmelden damit Gruppe aktiv wird!"

echo ""
echo "✅ Setup abgeschlossen!"
echo ""
echo "Nächster Schritt:"
echo "  python3 run_all_tests.py"
echo "═══════════════════════════════════════════════════"
