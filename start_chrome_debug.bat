@echo off
echo ============================================================
echo   启动Chrome调试模式
echo ============================================================
echo.
echo 正在启动Chrome浏览器（调试模式，端口9222）...
echo.
echo 启动后，请保持Chrome窗口打开，然后在另一个终端运行:
echo   python test_chrome_cdp.py
echo.
echo ============================================================

REM 启动Chrome（调试模式）
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome_debug_profile"

echo.
echo Chrome已在调试模式下启动！
echo 端口: 9222
echo.
pause
