@echo off
REM Chrome调试模式启动脚本 - 改进版
setlocal EnableDelayedExpansion

echo ============================================================
echo  Chrome调试模式启动工具
echo ============================================================
echo.

REM Chrome路径
set CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe

REM 检查Chrome是否存在
if not exist "%CHROME_PATH%" (
    echo [错误] 找不到Chrome浏览器！
    echo 路径: %CHROME_PATH%
    echo.
    pause
    exit /b 1
)

REM 检查Chrome是否正在运行
echo [1/3] 检查Chrome进程...
tasklist /FI "IMAGENAME eq chrome.exe" 2>NUL | find /I /N "chrome.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [警告] 检测到Chrome正在运行！
    echo.
    echo 必须先关闭所有Chrome窗口才能启动调试模式！
    echo.
    choice /C YN /M "是否自动关闭所有Chrome窗口"
    if errorlevel 2 (
        echo 已取消操作
        pause
        exit /b 1
    )

    echo.
    echo [2/3] 关闭所有Chrome进程...
    taskkill /F /IM chrome.exe >NUL 2>&1
    timeout /t 2 /nobreak >NUL
    echo Chrome已关闭
    echo.
) else (
    echo [OK] Chrome未运行
    echo.
)

REM 检查端口9222是否被占用
echo [3/3] 检查调试端口9222...
netstat -ano | findstr :9222 >NUL
if "%ERRORLEVEL%"=="0" (
    echo [警告] 端口9222已被占用！
    echo.
    echo 请结束占用该端口的进程:
    echo   netstat -ano ^| findstr :9222
    echo.
    pause
    exit /b 1
)

echo [OK] 端口9222可用
echo.
echo ============================================================
echo  启动Chrome调试模式...
echo ============================================================
echo.
echo 调试端口: 9222
echo.
echo [重要] 请保持此窗口打开，不要关闭！
echo.
echo 当你看到Chrome浏览器打开后，就可以运行主程序了：
echo   python main.py ^<直播间ID^> --ws --debug
echo.
echo ============================================================
echo.

REM 启动Chrome（前台运行，保持窗口打开）
"%CHROME_PATH%" --remote-debugging-port=9222 --new-window

echo.
echo Chrome已关闭
pause
