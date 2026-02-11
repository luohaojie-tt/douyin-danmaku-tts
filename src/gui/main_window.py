"""
主窗口 - 抖音弹幕语音播报工具

提供主应用程序窗口，包含菜单栏、控制面板、弹幕显示区域和日志输出。
"""

import logging
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QVBoxLayout,
    QMenuBar, QMenu, QAction, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from src.gui.control_panel import ControlPanel
from src.gui.danmaku_widget import DanmakuWidget
from src.gui.log_widget import LogWidget
from src.gui.status_bar import StatusBar

logger = logging.getLogger(__name__)


def load_stylesheet():
    """加载样式表"""
    style_path = Path(__file__).parent.parent.parent / "resources" / "styles" / "dark_theme.qss"
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.warning(f"加载样式表失败: {e}")
        return ""


class MainWindow(QMainWindow):
    """
    主窗口
    
    布局:
        顶部: 菜单栏 (文件 | 设置 | 帮助)
        中间: 分割器 (左侧控制面板, 右侧弹幕列表)
        底部: 日志输出区域
        状态栏: 连接状态、消息计数、错误计数
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化主窗口
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        
        # 窗口标题
        self.setWindowTitle("抖音弹幕语音播报工具 v0.1.0")
        
        # 窗口大小
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)
        
        # UI组件
        self.control_panel: Optional[ControlPanel] = None
        self.danmaku_widget: Optional[DanmakuWidget] = None
        self.log_widget: Optional[LogWidget] = None
        self.status_bar: Optional[StatusBar] = None
        
        # 初始化UI
        self._init_ui()
        self._create_menu_bar()
        self._create_status_bar()
        
        # 应用深色主题
        self._apply_theme()
        
        logger.info("主窗口已初始化")

    def _apply_theme(self):
        """应用样式表"""
        stylesheet = load_stylesheet()
        if stylesheet:
            self.setStyleSheet(stylesheet)
            logger.debug("已应用深色主题")

    def _init_ui(self):
        """初始化UI布局"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # 创建水平分割器 (控制面板 | 弹幕显示)
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧: 控制面板
        self.control_panel = ControlPanel()
        splitter.addWidget(self.control_panel)
        
        # 右侧: 弹幕显示区域
        self.danmaku_widget = DanmakuWidget()
        splitter.addWidget(self.danmaku_widget)
        
        # 设置分割器比例 (控制面板30%, 弹幕70%)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)
        
        # 添加分割器到主布局
        main_layout.addWidget(splitter, stretch=3)
        
        # 底部: 日志输出区域
        self.log_widget = LogWidget()
        main_layout.addWidget(self.log_widget, stretch=1)
        
        logger.debug("UI布局已创建")

    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        
        # 导出弹幕 -> 导出TXT
        export_txt_action = QAction("导出弹幕为TXT(&T)", self)
        export_txt_action.setStatusTip("将弹幕导出为TXT文本文件")
        export_txt_action.triggered.connect(self._export_txt)
        file_menu.addAction(export_txt_action)
        
        # 导出弹幕 -> 导出JSON
        export_json_action = QAction("导出弹幕为JSON(&J)", self)
        export_json_action.setStatusTip("将弹幕导出为JSON格式文件")
        export_json_action.triggered.connect(self._export_json)
        file_menu.addAction(export_json_action)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("退出程序")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 设置菜单
        settings_menu = menubar.addMenu("设置(&S)")
        
        # 打开设置对话框
        config_action = QAction("配置(&C)", self)
        config_action.setStatusTip("打开设置对话框")
        config_action.triggered.connect(self._open_settings)
        settings_menu.addAction(config_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        # 关于
        about_action = QAction("关于(&A)", self)
        about_action.setStatusTip("关于本程序")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = StatusBar()
        self.setStatusBar(self.status_bar.widget)

    def _export_txt(self):
        """导出弹幕为TXT"""
        logger.info("触发导出TXT操作")
        # TODO: 实现导出功能
        QMessageBox.information(self, "提示", "导出TXT功能将在后续版本实现")

    def _export_json(self):
        """导出弹幕为JSON"""
        logger.info("触发导出JSON操作")
        # TODO: 实现导出功能
        QMessageBox.information(self, "提示", "导出JSON功能将在后续版本实现")

    def _open_settings(self):
        """打开设置对话框"""
        logger.info("打开设置对话框")
        if self.control_panel:
            self.control_panel.open_settings_dialog()

    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            """
            <h3>抖音弹幕语音播报工具 v0.1.0</h3>
            <p>基于PyQt5的图形界面版本</p>
            <p><b>功能特性:</b></p>
            <ul>
                <li>实时监听抖音直播间弹幕</li>
                <li>语音播报弹幕内容</li>
                <li>可调节语速和音量</li>
                <li>支持黑名单过滤</li>
                <li>弹幕导出功能</li>
            </ul>
            <p><b>项目地址:</b> LiveStreamInfoRetrievalProject</p>
            """
        )

    def closeEvent(self, event):
        """窗口关闭事件"""
        reply = QMessageBox.question(
            self,
            "确认退出",
            "确定要退出程序吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            logger.info("用户确认退出")
            event.accept()
        else:
            logger.info("用户取消退出")
            event.ignore()
