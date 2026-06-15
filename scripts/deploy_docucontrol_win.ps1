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

# ── Dateien direkt uebertragen (scp) ──────────────────────────────────────────
Write-Host "[1/3] Dateien pruefen ..."
$files = @(
    @{ src = "$LOCAL\app.py";                       dst = "${PI_BASE}/app.py" },
    @{ src = "$LOCAL\print_manager.py";             dst = "${PI_BASE}/print_manager.py" },
    @{ src = "$LOCAL\static\docucontrol.css";       dst = "${PI_BASE}/static/docucontrol.css" },
    @{ src = "$LOCAL\templates\base.html";          dst = "${PI_BASE}/templates/base.html" },
    @{ src = "$LOCAL\templates\dashboard.html";     dst = "${PI_BASE}/templates/dashboard.html" },
    @{ src = "$LOCAL\templates\settings.html";      dst = "${PI_BASE}/templates/settings.html" },
    @{ src = "$LOCAL\templates\filemanager.html";   dst = "${PI_BASE}/templates/filemanager.html" }
)
foreach ($f in $files) {
    if (-not (Test-Path $f.src)) {
        Write-Host "  FEHLER: $($f.src) nicht gefunden" -ForegroundColor Red
        exit 1
    }
    Write-Host "  + $($f.src.Split('\')[-1])"
}
Write-Host ""

Write-Host "[2/3] Dateien uebertragen (scp) ..." -ForegroundColor Yellow
Write-Host "      => Passwort: Xtend1478" -ForegroundColor DarkGray
Write-Host ""

foreach ($f in $files) {
    scp -o StrictHostKeyChecking=no $f.src "${PI_USER}@${PI_HOST}:$($f.dst)"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FEHLER: scp fehlgeschlagen fuer $($f.src)" -ForegroundColor Red
        exit 1
    }
    Write-Host "  OK: $($f.src.Split('\')[-1])" -ForegroundColor Green
}
Write-Host ""

# ── Remote-Installation ────────────────────────────────────────────────────────
Write-Host "[3/3] Installation auf Pi (ssh) ..." -ForegroundColor Yellow
Write-Host "      => Passwort: Xtend1478" -ForegroundColor DarkGray
Write-Host ""

$remoteCmd = @"
set -e
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
