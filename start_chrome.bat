@echo off
echo Starting Chrome with remote debugging...
taskkill /F /IM chrome.exe 2>nul
timeout /t 2 /nobreak >nul
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --new-window https://live.douyin.com/168465302284
echo Chrome started. Waiting for it to be ready...
timeout /t 5 /nobreak
echo Done! You can now run the test script.
pause
