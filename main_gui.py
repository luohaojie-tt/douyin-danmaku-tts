#!/usr/bin/env python3
"""
抖音弹幕语音播报工具 - GUI主程序入口

使用方法:
    python main_gui.py

特性:
    - 图形化界面控制弹幕播报
    - 实时显示弹幕内容
    - 可调节语速、音量
    - 支持黑名单过滤
    - 日志输出显示
"""

import sys
import logging
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from src.gui.main_window import MainWindow

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO"):
    """设置日志"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%H:%M:%S"
    )


def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════╗
║     抖音弹幕语音播报工具 GUI v0.1.0             ║
║     LiveStreamInfoRetrievalProject               ║
╚══════════════════════════════════════════════════╝
"""
    print(banner)


def main():
    """GUI主程序入口"""
    print_banner()

    # 设置日志
    setup_logging()

    # 创建QApplication实例
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("抖音弹幕语音播报工具")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("LiveStreamInfoRetrievalProject")

    # 启用高DPI缩放
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # 创建主窗口
    main_window = MainWindow()
    main_window.show()

    logger.info("GUI已启动")

    # 进入事件循环
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
