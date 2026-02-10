# Chrome Debug Mode Launcher
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Chrome Debug Mode Launcher" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"

if (-not (Test-Path $chromePath)) {
    Write-Host "[ERROR] Chrome not found!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[1/3] Checking Chrome process..." -ForegroundColor Yellow
$chromeProcess = Get-Process chrome -ErrorAction SilentlyContinue

if ($chromeProcess) {
    Write-Host "[WARNING] Chrome is running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Must close ALL Chrome windows first!" -ForegroundColor Yellow
    Write-Host ""

    $response = Read-Host "Close all Chrome automatically? (Y/N)"
    if ($response -eq 'Y' -or $response -eq 'y') {
        Write-Host ""
        Write-Host "[2/3] Closing Chrome processes..." -ForegroundColor Yellow
        try {
            Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force
            Start-Sleep -Seconds 2
            Write-Host "[SUCCESS] Chrome closed" -ForegroundColor Green
        } catch {
            Write-Host "[ERROR] Cannot close Chrome" -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }
    } else {
        Write-Host "Cancelled" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "[OK] Chrome not running" -ForegroundColor Green
}

Write-Host ""
Write-Host "[3/3] Checking port 9222..." -ForegroundColor Yellow
$port9222 = Get-NetTCPConnection -LocalPort 9222 -ErrorAction SilentlyContinue

if ($port9222) {
    Write-Host "[WARNING] Port 9222 is in use!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Process info:" -ForegroundColor Yellow
    $port9222 | ForEach-Object {
        $process = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
        Write-Host "  PID: $($_.OwningProcess), Name: $($process.ProcessName)" -ForegroundColor White
    }
    Write-Host ""
    Write-Host "Please close the process or restart computer" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
} else {
    Write-Host "[OK] Port 9222 available" -ForegroundColor Green
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Starting Chrome debug mode..." -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""
Write-Host "Debug port: 9222" -ForegroundColor Cyan
Write-Host ""
Write-Host "[IMPORTANT]" -ForegroundColor Yellow
Write-Host "  1. Chrome will open in a new window" -ForegroundColor White
Write-Host "  2. Keep this PowerShell window OPEN" -ForegroundColor White
Write-Host "  3. Do NOT close Chrome window!" -ForegroundColor White
Write-Host ""
Write-Host "After Chrome opens, run in NEW PowerShell window:" -ForegroundColor Yellow
Write-Host "  cd 'd:\work\LiveStreamInfoRetrievalProject'" -ForegroundColor Cyan
Write-Host "  python main.py 168465302284 --ws --debug" -ForegroundColor Cyan
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

try {
    $process = Start-Process -FilePath $chromePath -ArgumentList "--remote-debugging-port=9222", "--new-window" -PassThru

    Write-Host ""
    Write-Host "[SUCCESS] Chrome started!" -ForegroundColor Green
    Write-Host "Process ID: $($process.Id)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Press Ctrl+C to stop monitoring (Chrome will continue running)" -ForegroundColor Yellow
    Write-Host ""

    # Monitor the Chrome process
    try {
        while (!$process.HasExited) {
            Start-Sleep -Seconds 1
        }
        Write-Host ""
        Write-Host "Chrome has been closed" -ForegroundColor Yellow
    } catch [System.Management.Automation.PipelineStoppedException] {
        Write-Host ""
        Write-Host "Monitoring stopped (Chrome still running)" -ForegroundColor Yellow
    }

} catch {
    Write-Host ""
    Write-Host "[ERROR] Failed to start Chrome: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Read-Host "Press Enter to exit"
