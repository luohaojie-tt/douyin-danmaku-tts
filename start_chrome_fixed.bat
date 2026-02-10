@echo off
REM Chrome Debug Mode Launcher - Final Version
echo ============================================================
echo  Chrome Debug Mode Launcher
echo ============================================================
echo.

REM Chrome Path
set CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe

REM Check Chrome exists
if not exist "%CHROME_PATH%" (
    echo [ERROR] Chrome not found!
    echo Path: %CHROME_PATH%
    pause
    exit /b 1
)

echo [1/3] Closing all Chrome processes...
taskkill /F /IM chrome.exe >NUL 2>&1
timeout /t 2 /nobreak >NUL
echo [OK] Chrome closed
echo.

echo [2/3] Checking port 9222...
netstat -ano | findstr :9222 >NUL
if %ERRORLEVEL%==0 (
    echo [WARNING] Port 9222 is in use!
    echo.
    echo Please close the process using the port or restart computer.
    pause
    exit /b 1
)
echo [OK] Port 9222 available
echo.

echo [3/3] Starting Chrome debug mode...
echo ============================================================
echo.
echo Debug Port: 9222
echo User Data: C:\chrome_debug_temp
echo.
echo [IMPORTANT]
echo   1. Chrome will open in a new window
echo   2. Keep THIS window open
echo   3. Do NOT close Chrome!
echo.
echo After Chrome opens, run in NEW PowerShell window:
echo   cd "d:\work\LiveStreamInfoRetrievalProject"
echo   python main.py 168465302284 --ws --debug
echo.
echo ============================================================
echo.

REM Start Chrome with debug port and separate user data
"%CHROME_PATH%" --remote-debugging-port=9222 --user-data-dir="C:\chrome_debug_temp"

echo.
echo Chrome has been closed
pause
