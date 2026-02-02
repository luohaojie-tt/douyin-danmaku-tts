"""
启动Chrome调试模式 - 无需等待
"""
import subprocess
import time

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
print(f"Starting Chrome: {chrome_path}")
print("Debug port: 9222")
print("User data: C:\\chrome_debug_profile")
print()

try:
    subprocess.Popen([
        chrome_path,
        "--remote-debugging-port=9222",
        "--user-data-dir=C:\\chrome_debug_profile"
    ])
    print("Chrome launched successfully!")
    print("\nChrome will open in a new window.")
    print("Keep that window open for the danmaku tool to work.")
except Exception as e:
    print(f"Failed: {e}")

time.sleep(2)
