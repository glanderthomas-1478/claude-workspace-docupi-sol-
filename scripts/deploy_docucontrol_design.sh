#!/bin/bash
# deploy_docucontrol_design.sh
# Deployed das neue Design-System auf den DocuControl-Pi.
# Ausführen von: diesem Workspace-Verzeichnis
# Voraussetzung: sshpass installiert (brew install sshpass / apt install sshpass)

set -e

PI="docucontrol@192.168.0.171"
PASS="Xtend1478"
PI_BASE="/home/docucontrol/docupi"
LOCAL="src/docucontrol"

echo "=== DocuControl Design-System Deployment ==="
echo "Ziel: $PI"
echo ""

# ── CSS ──────────────────────────────────────────────────────────────────
echo "[1/4] CSS übertragen …"
sshpass -p "$PASS" scp \
    "$LOCAL/static/docucontrol.css" \
    "$PI:$PI_BASE/static/docucontrol.css"
echo "      ✓ static/docucontrol.css"

# ── Templates ─────────────────────────────────────────────────────────────
echo "[2/4] Templates übertragen …"
for tpl in base.html dashboard.html settings.html filemanager.html; do
    sshpass -p "$PASS" scp \
        "$LOCAL/templates/$tpl" \
        "$PI:$PI_BASE/templates/$tpl"
    echo "      ✓ templates/$tpl"
done

# ── app.py Patch ──────────────────────────────────────────────────────────
echo "[3/4] app.py: app_additions.py hochladen …"
sshpass -p "$PASS" scp \
    "$LOCAL/app_additions.py" \
    "$PI:/tmp/app_additions.py"
echo "      Hinweis: app_additions.py liegt unter /tmp/ auf dem Pi."
echo "      Füge den Inhalt manuell in app.py ein (Context Processor + API-Routen)."
echo "      Oder führe auf dem Pi aus:"
echo "        cat /tmp/app_additions.py"

# ── Service neustarten ────────────────────────────────────────────────────
echo "[4/4] Service neustarten …"
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no "$PI" \
    "sudo systemctl restart docucontrol.service && sleep 2 && systemctl is-active docucontrol.service"

echo ""
echo "=== Deployment abgeschlossen ==="
echo "Web-Interface: http://192.168.0.171"
echo ""
echo "Nächste Schritte:"
echo "  1. http://192.168.0.171 im Browser öffnen"
echo "  2. Topbar, 3-Tab-Nav und Protokoll-Tabelle prüfen"
echo "  3. Testprotokoll senden: python3 scripts/send_krefeld_protocol.py"
echo "  4. app_additions.py manuell in app.py integrieren (Context Processor + /api/protocols)"
