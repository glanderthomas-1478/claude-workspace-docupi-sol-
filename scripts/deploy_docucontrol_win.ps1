# deploy_docucontrol_win.ps1
# Deployed das DocuControl Design-System auf den Pi.
# Voraussetzung: Windows OpenSSH (ssh.exe + scp.exe) — bereits in Windows 10 eingebaut.
# Passwort wird 2x abgefragt: einmal für scp, einmal für ssh.
#
# Ausführen: .\scripts\deploy_docucontrol_win.ps1
# Oder aus Claude: ! powershell -ExecutionPolicy Bypass -File scripts\deploy_docucontrol_win.ps1

$PI_HOST = "192.168.0.171"
$PI_USER = "docucontrol"
$PI_BASE = "/home/docucontrol/docupi"
$LOCAL   = "src\docucontrol"

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== DocuControl Design-System Deployment ===" -ForegroundColor Cyan
Write-Host "Ziel: ${PI_USER}@${PI_HOST}" -ForegroundColor Cyan
Write-Host ""

# ── Erreichbarkeit prüfen ─────────────────────────────────────────────────────
Write-Host "[0/3] Verbindung prüfen ..."
$pingResult = Test-NetConnection -ComputerName $PI_HOST -Port 22 -InformationLevel Quiet -WarningAction SilentlyContinue
if (-not $pingResult) {
    Write-Host "  FEHLER: $PI_HOST Port 22 nicht erreichbar." -ForegroundColor Red
    Write-Host "  Bitte sicherstellen, dass du im getmatic-Netzwerk (192.168.0.x) bist." -ForegroundColor Yellow
    exit 1
}
Write-Host "  OK: $PI_HOST ist erreichbar." -ForegroundColor Green
Write-Host ""

# ── Deployment-Paket erstellen ────────────────────────────────────────────────
Write-Host "[1/3] Deployment-Paket erstellen ..."

$tmpDir = Join-Path $env:TEMP "docucontrol_deploy"
if (Test-Path $tmpDir) { Remove-Item $tmpDir -Recurse -Force }
New-Item -ItemType Directory -Path $tmpDir | Out-Null
New-Item -ItemType Directory -Path "$tmpDir\static" | Out-Null
New-Item -ItemType Directory -Path "$tmpDir\templates" | Out-Null

# CSS kopieren
Copy-Item "$LOCAL\static\docucontrol.css" "$tmpDir\static\docucontrol.css"
Write-Host "  + static/docucontrol.css"

# Templates kopieren
foreach ($tpl in @("base.html", "dashboard.html", "settings.html", "filemanager.html")) {
    Copy-Item "$LOCAL\templates\$tpl" "$tmpDir\templates\$tpl"
    Write-Host "  + templates/$tpl"
}

# app_additions.py kopieren
Copy-Item "$LOCAL\app_additions.py" "$tmpDir\app_additions.py"
Write-Host "  + app_additions.py"

# Patch-Script für app.py erstellen (läuft auf dem Pi)
$patchScript = @'
#!/usr/bin/env python3
"""Integriert app_additions.py in app.py (idempotent)."""
import os, sys

APP_PY = os.path.join(os.path.dirname(__file__).replace("/tmp/docucontrol_deploy", ""), "app.py")
# Suche app.py im docupi-Verzeichnis
for candidate in ["/home/docucontrol/docupi/app.py", os.path.expanduser("~/docupi/app.py")]:
    if os.path.exists(candidate):
        APP_PY = candidate
        break

ADDITIONS = os.path.join("/tmp/docucontrol_deploy", "app_additions.py")

if not os.path.exists(APP_PY):
    print(f"FEHLER: app.py nicht gefunden (gesucht: {APP_PY})")
    sys.exit(1)

with open(APP_PY, "r", encoding="utf-8") as f:
    app_content = f.read()

if "inject_tcp_status" in app_content:
    print(f"app.py bereits gepatcht (inject_tcp_status gefunden) — überspringe.")
    sys.exit(0)

with open(ADDITIONS, "r", encoding="utf-8") as f:
    raw = f.read()

# Docstring am Anfang entfernen
lines = raw.split("\n")
i = 0
if lines and lines[0].strip().startswith('"""'):
    i = 1
    while i < len(lines) and '"""' not in lines[i]:
        i += 1
    i += 1  # letzte """ überspringen
    while i < len(lines) and lines[i].strip() == "":
        i += 1

additions_clean = "\n".join(lines[i:])

MARKER = "if __name__ == '__main__':"
if MARKER in app_content:
    patched = app_content.replace(MARKER, additions_clean.rstrip() + "\n\n\n" + MARKER)
else:
    patched = app_content.rstrip() + "\n\n\n" + additions_clean

with open(APP_PY, "w", encoding="utf-8") as f:
    f.write(patched)

print(f"OK: app.py erfolgreich gepatcht ({APP_PY})")
'@

$patchScript | Out-File -FilePath "$tmpDir\patch_app.py" -Encoding utf8
Write-Host "  + patch_app.py (generiert)"

# Tar-Archiv erstellen
$tarPath = Join-Path $env:TEMP "docucontrol_deploy.tar.gz"
if (Test-Path $tarPath) { Remove-Item $tarPath -Force }
tar -czf $tarPath -C $env:TEMP "docucontrol_deploy"
Write-Host "  Archiv: $tarPath ($([Math]::Round((Get-Item $tarPath).Length / 1KB, 1)) KB)"
Write-Host ""

# ── Datei-Transfer ────────────────────────────────────────────────────────────
Write-Host "[2/3] Dateien übertragen (scp) ..." -ForegroundColor Yellow
Write-Host "      => Passwort-Eingabe: Xtend1478" -ForegroundColor DarkGray
Write-Host ""

scp -o StrictHostKeyChecking=no $tarPath "${PI_USER}@${PI_HOST}:/tmp/docucontrol_deploy.tar.gz"

if ($LASTEXITCODE -ne 0) {
    Write-Host "FEHLER: scp fehlgeschlagen." -ForegroundColor Red
    exit 1
}
Write-Host ""
Write-Host "  OK: Archiv übertragen." -ForegroundColor Green
Write-Host ""

# ── Remote-Ausführung ─────────────────────────────────────────────────────────
Write-Host "[3/3] Installation auf Pi (ssh) ..." -ForegroundColor Yellow
Write-Host "      => Passwort-Eingabe: Xtend1478" -ForegroundColor DarkGray
Write-Host ""

$remoteCmd = @"
set -e
echo '--- Entpacke Archiv ---'
rm -rf /tmp/docucontrol_deploy
tar -xzf /tmp/docucontrol_deploy.tar.gz -C /tmp/

echo '--- Kopiere CSS ---'
cp /tmp/docucontrol_deploy/static/docucontrol.css ${PI_BASE}/static/docucontrol.css
echo '  OK: static/docucontrol.css'

echo '--- Kopiere Templates ---'
for tpl in base.html dashboard.html settings.html filemanager.html; do
    cp /tmp/docucontrol_deploy/templates/\$tpl ${PI_BASE}/templates/\$tpl
    echo "  OK: templates/\$tpl"
done

echo '--- Patche app.py ---'
python3 /tmp/docucontrol_deploy/patch_app.py

echo '--- Starte Service neu ---'
sudo systemctl restart docucontrol.service
sleep 2
STATUS=\$(systemctl is-active docucontrol.service)
echo "Service-Status: \$STATUS"
if [ "\$STATUS" = "active" ]; then
    echo 'OK: docucontrol.service läuft.'
else
    echo 'WARNUNG: Service nicht aktiv — Log prüfen mit: journalctl -u docucontrol.service -n 30'
    journalctl -u docucontrol.service -n 15 --no-pager
fi

echo '--- Aufräumen ---'
rm -f /tmp/docucontrol_deploy.tar.gz
echo 'Fertig!'
"@

ssh -o StrictHostKeyChecking=no "${PI_USER}@${PI_HOST}" $remoteCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "FEHLER: Remote-Ausführung fehlgeschlagen." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Deployment abgeschlossen ===" -ForegroundColor Green
Write-Host ""
Write-Host "Web-Interface: http://$PI_HOST" -ForegroundColor Cyan
Write-Host ""
Write-Host "Validierung:" -ForegroundColor Yellow
Write-Host "  1. http://$PI_HOST im Browser öffnen"
Write-Host "  2. Topbar 'DocuControl by GeTmatic' und 3-Tab-Nav prüfen"
Write-Host "  3. Dashboard-Tabelle mit echten Protokollen prüfen"
Write-Host "  4. Testprotokoll senden: python3 scripts\send_krefeld_protocol.py"
Write-Host ""

# Aufräumen
Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $tarPath -Force -ErrorAction SilentlyContinue
