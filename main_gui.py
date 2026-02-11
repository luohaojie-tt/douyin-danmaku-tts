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

# 确定基础路径并添加src目录到Python路径
if getattr(sys, 'frozen', False):
    # 打包后的环境：_internal目录包含所有Python模块
    base_path = Path(sys.executable).parent / "_internal"
    sys.path.insert(0, str(base_path))
else:
    # 开发环境：脚本所在目录
    base_path = Path(__file__).parent
    sys.path.insert(0, str(base_path))
    sys.path.insert(0, str(base_path / "src"))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from src.gui.main_window import MainWindow

logger = logging.getLogger(__name__)


def get_resource_path(relative_path: str) -> Path:
    """
    获取资源文件的绝对路径（兼容开发和打包环境）

    Args:
        relative_path: 相对路径

    Returns:
        资源文件的绝对路径
    """
    if getattr(sys, 'frozen', False):
        # 打包后的环境：exe文件所在目录
        return Path(sys.executable).parent / relative_path
    else:
        # 开发环境：项目根目录
        return Path(__file__).parent / relative_path


def ensure_directories():
    """确保 cache/ 和 logs/ 目录存在"""
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent

    (base_path / "cache").mkdir(exist_ok=True)
    (base_path / "logs").mkdir(exist_ok=True)


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

    # 确保必要目录存在
    ensure_directories()

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
