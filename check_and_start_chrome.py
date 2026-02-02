#!/usr/bin/env python3
"""
检查Chrome调试端口并启动测试
"""

import subprocess
import sys
import time
import socket
from pathlib import Path


def check_chrome_debug_port():
    """检查9222端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', 9222))
        sock.close()
        return result == 0
    except:
        return False


def start_chrome_debug():
    """启动Chrome调试模式"""
    print("正在启动Chrome调试模式...")

    # 尝试找到Chrome路径
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(
            Path.home()
        ),
    ]

    chrome_path = None
    for path in possible_paths:
        if Path(path).exists():
            chrome_path = path
            break

    if not chrome_path:
        print("错误: 找不到Chrome浏览器")
        print("请手动安装Chrome或修改脚本中的路径")
        return False

    print(f"Chrome路径: {chrome_path}")

    # 启动Chrome
    try:
        subprocess.Popen([
            chrome_path,
            "--remote-debugging-port=9222",
            "--user-data-dir=C:\\chrome_debug_profile",
            "about:blank"  # 加载空白页避免干扰
        ])

        print("Chrome已启动！")
        print("等待5秒让Chrome完全启动...")
        time.sleep(5)
        return True
    except Exception as e:
        print(f"启动Chrome失败: {e}")
        return False


def main():
    print("="*60)
    print("  Chrome调试模式检查和启动")
    print("="*60)
    print()

    # 检查端口
    if check_chrome_debug_port():
        print("[OK] Chrome调试端口(9222)已开放")
        print()
        print("现在运行测试脚本:")
        print("  python test_chrome_cdp.py")
        return
    else:
        print("[WARN] Chrome调试端口(9222)未开放")
        print()

    # 询问是否启动
    print("是否自动启动Chrome调试模式？")
    print("  输入 'y' 启动")
    print("  输入其他键退出")
    print()

    try:
        choice = input("你的选择: ").strip().lower()
        if choice == 'y':
            if start_chrome_debug():
                print()
                print("="*60)
                print("Chrome已准备好！")
                print("现在在新终端运行:")
                print("  python test_chrome_cdp.py")
                print("="*60)
            else:
                print("启动失败，请手动启动Chrome:")
                print(r"  chrome.exe --remote-debugging-port=9222")
        else:
            print("已取消")
            print()
            print("手动启动Chrome的方法:")
            print(r"  chrome.exe --remote-debugging-port=9222")
            print()
            print("或者双击运行: start_chrome_debug.bat")
    except KeyboardInterrupt:
        print("\n\n已取消")


if __name__ == "__main__":
    main()
