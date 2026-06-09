#!/bin/bash
# DocuPi 3000 - Setup für macOS
# ===============================
# Installiert alle Abhängigkeiten für den SAIA-Test

echo "═══════════════════════════════════════════════════"
echo "  DocuPi 3000 - macOS Setup"
echo "═══════════════════════════════════════════════════"

# Homebrew prüfen
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew nicht installiert!"
    echo "   Installation: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

echo "📦 Installiere snap7 C-Library..."
brew install snap7

echo ""
echo "📦 Installiere Python-Pakete..."
pip3 install -r "$(dirname "$0")/requirements.txt"

echo ""
echo "📦 Installiere USB-Serial Treiber (optional)..."
echo "   Falls die SAIA einen FTDI-Chip hat:"
echo "     brew install --cask ftdi-vcp-driver"
echo "   Falls die SAIA einen CH340-Chip hat:"
echo "     brew install --cask wch-ch34x-usb-serial-driver"

echo ""
echo "✅ Setup abgeschlossen!"
echo ""
echo "Nächster Schritt:"
echo "  python3 run_all_tests.py"
echo "═══════════════════════════════════════════════════"
