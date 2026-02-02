@echo off
echo Starting Chrome with remote debugging on port 9222...
echo.
echo Please keep this Chrome window open.
echo.
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=C:\chrome_debug_profile
echo Chrome started! You can close this window.
timeout /t 3 >nul
