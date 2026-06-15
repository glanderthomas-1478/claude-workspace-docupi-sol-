# deploy_docucontrol_win.ps1
# Deployed geaenderte Dateien auf den DocuControl Pi.
# Voraussetzung: Windows OpenSSH (ssh.exe + scp.exe) — bereits in Windows 10 eingebaut.
# Passwort wird abgefragt: Xtend1478
#
# Ausfuehren: .\scripts\deploy_docucontrol_win.ps1
# Oder aus Claude: ! powershell -ExecutionPolicy Bypass -File scripts\deploy_docucontrol_win.ps1

$PI_HOST = "192.168.0.171"
$PI_USER = "docucontrol"
$PI_BASE = "/home/docucontrol/docupi"
$LOCAL   = "src\docucontrol"

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== DocuControl Deployment ===" -ForegroundColor Cyan
Write-Host "Ziel: ${PI_USER}@${PI_HOST}" -ForegroundColor Cyan
Write-Host ""

# ── Erreichbarkeit pruefen ─────────────────────────────────────────────────────
Write-Host "[0/3] Verbindung pruefen ..."
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

# Python-Backend
foreach ($py in @("app.py", "print_manager.py")) {
    Copy-Item "$LOCAL\$py" "$tmpDir\$py"
    Write-Host "  + $py"
}

# CSS
Copy-Item "$LOCAL\static\docucontrol.css" "$tmpDir\static\docucontrol.css"
Write-Host "  + static/docucontrol.css"

# Templates
foreach ($tpl in @("base.html", "dashboard.html", "settings.html", "filemanager.html")) {
    Copy-Item "$LOCAL\templates\$tpl" "$tmpDir\templates\$tpl"
    Write-Host "  + templates/$tpl"
}

# Tar-Archiv erstellen
$tarPath = Join-Path $env:TEMP "docucontrol_deploy.tar.gz"
if (Test-Path $tarPath) { Remove-Item $tarPath -Force }
tar -czf $tarPath -C $env:TEMP "docucontrol_deploy"
Write-Host "  Archiv: $tarPath ($([Math]::Round((Get-Item $tarPath).Length / 1KB, 1)) KB)"
Write-Host ""

# ── Datei-Transfer ────────────────────────────────────────────────────────────
Write-Host "[2/3] Dateien uebertragen (scp) ..." -ForegroundColor Yellow
Write-Host "      => Passwort: Xtend1478" -ForegroundColor DarkGray
Write-Host ""

scp -o StrictHostKeyChecking=no $tarPath "${PI_USER}@${PI_HOST}:/tmp/docucontrol_deploy.tar.gz"

if ($LASTEXITCODE -ne 0) {
    Write-Host "FEHLER: scp fehlgeschlagen." -ForegroundColor Red
    exit 1
}
Write-Host "  OK: Archiv uebertragen." -ForegroundColor Green
Write-Host ""

# ── Remote-Installation ────────────────────────────────────────────────────────
Write-Host "[3/3] Installation auf Pi (ssh) ..." -ForegroundColor Yellow
Write-Host "      => Passwort: Xtend1478" -ForegroundColor DarkGray
Write-Host ""

$remoteCmd = @"
set -e
echo '--- Entpacke Archiv ---'
rm -rf /tmp/docucontrol_deploy
tar -xzf /tmp/docucontrol_deploy.tar.gz -C /tmp/

echo '--- Kopiere Backend ---'
cp /tmp/docucontrol_deploy/app.py ${PI_BASE}/app.py
echo '  OK: app.py'
cp /tmp/docucontrol_deploy/print_manager.py ${PI_BASE}/print_manager.py
echo '  OK: print_manager.py'

echo '--- Kopiere CSS ---'
cp /tmp/docucontrol_deploy/static/docucontrol.css ${PI_BASE}/static/docucontrol.css
echo '  OK: static/docucontrol.css'

echo '--- Kopiere Templates ---'
for tpl in base.html dashboard.html settings.html filemanager.html; do
    cp /tmp/docucontrol_deploy/templates/\$tpl ${PI_BASE}/templates/\$tpl
    echo "  OK: templates/\$tpl"
done

echo '--- Sudoers fuer lpadmin ---'
echo 'docucontrol ALL=(ALL) NOPASSWD: /usr/sbin/lpadmin' | sudo tee /etc/sudoers.d/docucontrol-cups > /dev/null
sudo chmod 440 /etc/sudoers.d/docucontrol-cups
echo '  OK: sudoers'

echo '--- Starte Service neu ---'
sudo systemctl restart docucontrol.service
sleep 3
STATUS=\$(systemctl is-active docucontrol.service)
echo "Service-Status: \$STATUS"
if [ "\$STATUS" = "active" ]; then
    echo 'OK: docucontrol.service laeuft.'
else
    echo 'WARNUNG: Service nicht aktiv!'
    journalctl -u docucontrol.service -n 20 --no-pager
fi

echo '--- Aufraumen ---'
rm -rf /tmp/docucontrol_deploy /tmp/docucontrol_deploy.tar.gz
echo 'Fertig!'
"@

ssh -o StrictHostKeyChecking=no "${PI_USER}@${PI_HOST}" $remoteCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "FEHLER: Remote-Ausfuehrung fehlgeschlagen." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Deployment abgeschlossen ===" -ForegroundColor Green
Write-Host ""
Write-Host "Web-Interface: http://$PI_HOST" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test:" -ForegroundColor Yellow
Write-Host "  1. http://$PI_HOST/settings -> Einstellungen -> Drucker"
Write-Host "  2. Button 'USB einrichten' klicken"
Write-Host "  3. Testdruck ausfuehren"
Write-Host ""

# Aufraumen
Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $tarPath -Force -ErrorAction SilentlyContinue
