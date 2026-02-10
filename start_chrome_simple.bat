@echo off
REM Chrome调试模式简单启动脚本
echo ============================================================
echo  正在启动Chrome调试模式...
echo ============================================================
echo.

REM Chrome路径
set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"

REM 检查Chrome是否存在
if not exist "%CHROME_PATH%" (
    echo [错误] 找不到Chrome！
    echo.
    pause
    exit /b 1
)

echo [提示] 正在启动Chrome...
echo [重要] 启动后请保持Chrome窗口打开
echo.

REM 启动Chrome（使用start命令，在新窗口打开）
start "" "%CHROME_PATH%" --remote-debugging-port=9222 --new-window

echo.
echo ============================================================
echo  Chrome调试模式已启动！
echo ============================================================
echo.
echo 接下来的步骤:
echo   1. 等待Chrome浏览器打开
echo   2. 保持Chrome窗口打开
echo   3. 在PowerShell中运行:
echo      python main.py 168465302284 --ws --debug
echo.
echo 按任意键关闭此窗口...
pause >NUL
