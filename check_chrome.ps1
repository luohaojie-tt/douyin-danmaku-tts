# Chrome调试模式检查脚本
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Chrome调试模式状态检查" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# 检查Chrome进程
Write-Host "[1/3] 检查Chrome进程..." -ForegroundColor Yellow
$chromeProcess = Get-Process chrome -ErrorAction SilentlyContinue
if ($chromeProcess) {
    Write-Host "  ✓ Chrome正在运行 (PID: $($chromeProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "  ✗ Chrome未运行" -ForegroundColor Red
    Write-Host ""
    Write-Host "请先启动Chrome调试模式:" -ForegroundColor Yellow
    Write-Host "  .\start_chrome_debug.bat" -ForegroundColor Cyan
    exit 1
}

Write-Host ""

# 检查端口9222
Write-Host "[2/3] 检查调试端口9222..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9222/json" -TimeoutSec 2 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "  ✓ 调试端口响应正常" -ForegroundColor Green

        $tabs = $response.Content | ConvertFrom-Json
        Write-Host "  ✓ 已打开 $($tabs.Count) 个标签页" -ForegroundColor Green
    }
} catch {
    Write-Host "  ✗ 无法连接到调试端口" -ForegroundColor Red
    Write-Host "  错误: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "可能的原因:" -ForegroundColor Yellow
    Write-Host "  1. Chrome未在调试模式下运行" -ForegroundColor White
    Write-Host "  2. 端口9222被其他程序占用" -ForegroundColor White
    Write-Host ""
    Write-Host "解决方法:" -ForegroundColor Yellow
    Write-Host "  1. 关闭所有Chrome窗口" -ForegroundColor White
    Write-Host "  2. 运行: .\start_chrome_debug.bat" -ForegroundColor White
    exit 1
}

Write-Host ""

# 检查Cookie
Write-Host "[3/3] 检查Cookie文件..." -ForegroundColor Yellow
$cookiePath = "cookies.txt"
if (Test-Path $cookiePath) {
    $content = Get-Content $cookiePath -Raw
    if ($content -and $content.Trim().Length -gt 10) {
        Write-Host "  ✓ Cookie文件存在 (长度: $($content.Trim().Length))" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Cookie文件为空或无效" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ Cookie文件不存在" -ForegroundColor Red
    Write-Host "  请将ttwid保存到 cookies.txt 文件" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "✓ Chrome调试模式运行正常！" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""
Write-Host "现在可以运行主程序:" -ForegroundColor Yellow
Write-Host "  python main.py 168465302284 --ws --debug" -ForegroundColor Cyan
Write-Host ""
