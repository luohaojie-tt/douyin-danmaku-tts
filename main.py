#!/usr/bin/env python3
"""
抖音弹幕语音播报工具 - 主程序入口

使用方法:
    python main.py <room_id> [options]

示例:
    python main.py 728804746624
    python main.py 728804746624 --config custom.ini
    python main.py 728804746624 --debug
"""

import sys
import asyncio
import logging
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))


def setup_logging(level: str = "INFO"):
    """设置日志"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )


def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════╗
║     抖音弹幕语音播报工具 v0.1.0                  ║
║     LiveStreamInfoRetrievalProject               ║
╚══════════════════════════════════════════════════╝
"""
    print(banner)


async def main():
    """主程序"""
    # TODO: 实现主程序逻辑
    # 1. 加载配置
    # 2. 初始化模块
    # 3. 连接直播间
    # 4. 监听弹幕并转换播放
    print("主程序正在开发中...")


if __name__ == "__main__":
    print_banner()
    setup_logging()
    asyncio.run(main())
