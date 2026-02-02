"""
启动Chrome调试模式
"""
import os
import subprocess
import sys

def find_chrome():
    """查找Chrome可执行文件路径"""
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME')),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def main():
    chrome_path = find_chrome()

    if not chrome_path:
        print("[ERROR] Chrome not found")
        print("\nPlease start Chrome manually:")
        print("Press Win+R and enter:")
        print("chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\\chrome_debug_profile")
        return

    print(f"[OK] Found Chrome: {chrome_path}")
    print("\nStarting Chrome in debug mode...")
    print("Port: 9222")
    print("User data: C:\\chrome_debug_profile")
    print("\nPlease keep Chrome window open...\n")

    try:
        subprocess.Popen([
            chrome_path,
            "--remote-debugging-port=9222",
            "--user-data-dir=C:\\chrome_debug_profile"
        ])
        print("[OK] Chrome started successfully!")
        print("\nPress any key to exit this script...")
        input()
    except Exception as e:
        print(f"[ERROR] Failed to start: {e}")

if __name__ == "__main__":
    main()
