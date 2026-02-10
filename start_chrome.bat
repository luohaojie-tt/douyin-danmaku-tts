@echo off
REM Chrome调试模式启动脚本
echo ============================================================
echo  正在启动Chrome调试模式...
echo ============================================================
echo.
echo [提示] 使用方法: 启动后保持此窗口打开
echo   然后运行: python main.py <直播间ID> --ws
echo.
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
echo Chrome已在调试模式启动！
echo.
pause
