"""
主窗口 - 抖音弹幕语音播报工具

提供主应用程序窗口，包含菜单栏、控制面板、弹幕显示区域和日志输出。
集成GUIOrchestrator进行后端信号处理。
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QVBoxLayout,
    QMenuBar, QMenu, QAction, QMessageBox, QFileDialog, QProgressDialog
)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QIcon

from src.gui.control_panel import ControlPanel
from src.gui.danmaku_widget import DanmakuWidget
from src.gui.log_widget import LogWidget
from src.gui.status_bar import StatusBar
from src.backend.gui_orchestrator import GUIOrchestrator
from src.backend.gui_config_manager import GUIConfigManager

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

    集成:
        - GUIOrchestrator: 后端编排器
        - Asyncio事件循环: 通过QTimer集成
        - 信号连接: 所有后端信号连接到UI槽
        - Chrome调试模式: 自动检查并启动
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化主窗口

        Args:
            parent: 父窗口
        """
        super().__init__(parent)

        # 加载GUI配置管理器
        self.gui_config = GUIConfigManager()

        # 窗口标题
        self.setWindowTitle("抖音弹幕语音播报工具 v0.1.0")

        # 加载保存的窗口大小
        width, height = self.gui_config.get_window_size()
        self.resize(width, height)
        self.setMinimumSize(800, 600)

        # UI组件
        self.control_panel: Optional[ControlPanel] = None
        self.danmaku_widget: Optional[DanmakuWidget] = None
        self.log_widget: Optional[LogWidget] = None
        self.status_bar: Optional[StatusBar] = None

        # 后端组件
        self.orchestrator: Optional[GUIOrchestrator] = None
        self.asyncio_loop: Optional[asyncio.AbstractEventLoop] = None
        self.asyncio_timer: Optional[QTimer] = None

        # 初始化UI
        self._init_ui()
        self._create_menu_bar()
        self._create_status_bar()

        # 应用深色主题
        self._apply_theme()

        # 连接控制面板信号
        self._connect_control_panel_signals()

        # 初始化asyncio事件循环
        self._init_asyncio_loop()

        logger.info("主窗口已初始化")

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

    def _apply_theme(self):
        """应用样式表"""
        stylesheet = load_stylesheet()
        if stylesheet:
            self.setStyleSheet(stylesheet)
            logger.debug("已应用深色主题")

    def _connect_control_panel_signals(self):
        """连接控制面板信号到槽"""
        self.control_panel.signals.connect_requested.connect(self._on_connect_requested)
        self.control_panel.signals.disconnect_requested.connect(self._on_disconnect_requested)
        self.control_panel.signals.tts_enabled_changed.connect(self._on_tts_enabled_changed)
        self.control_panel.signals.speech_rate_changed.connect(self._on_speech_rate_changed)
        self.control_panel.signals.volume_changed.connect(self._on_volume_changed)

        # 连接弹幕计数信号到状态栏
        self.danmaku_widget.signals.count_changed.connect(self.status_bar.set_message_count)

        logger.debug("控制面板信号已连接")

    def _init_asyncio_loop(self):
        """初始化asyncio事件循环"""
        try:
            # 创建新的事件循环
            self.asyncio_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.asyncio_loop)

            # 创建QTimer用于处理asyncio事件
            self.asyncio_timer = QTimer()
            self.asyncio_timer.timeout.connect(self._process_asyncio_events)
            self.asyncio_timer.start(10)  # 每10ms处理一次

            logger.debug("Asyncio事件循环已初始化")
        except Exception as e:
            logger.error(f"初始化asyncio事件循环失败: {e}")
            self.log_widget.error(f"初始化失败: {e}", "MainWindow")

    def _process_asyncio_events(self):
        """处理asyncio事件（由QTimer调用）"""
        if self.asyncio_loop and not self.asyncio_loop.is_closed():
            # 运行一次事件循环迭代
            self.asyncio_loop.call_soon(self.asyncio_loop.stop)
            self.asyncio_loop.run_forever()

    # ==================== 后端信号槽 ====================

    @pyqtSlot(str, str, str)
    def _on_message_received(self, user_name: str, content: str, timestamp: str):
        """
        处理接收到的弹幕消息

        Args:
            user_name: 用户名
            content: 弹幕内容
            timestamp: ISO格式时间戳
        """
        try:
            # 解析时间戳
            dt = datetime.fromisoformat(timestamp)

            # 添加到弹幕显示
            self.danmaku_widget.add_danmaku(user_name, content, dt)

            # 添加到日志
            self.log_widget.info(f"{user_name}: {content}", "弹幕")

            logger.debug(f"显示弹幕: {user_name}: {content}")
        except Exception as e:
            logger.error(f"处理弹幕失败: {e}")

    @pyqtSlot(bool, str)
    def _on_connection_changed(self, connected: bool, message: str):
        """
        处理连接状态变化

        Args:
            connected: 是否已连接
            message: 状态消息
        """
        try:
            # 更新状态栏
            if self.orchestrator:
                room_id = self.orchestrator.room_id if connected else ""
                self.status_bar.set_connected(connected, room_id)
            else:
                self.status_bar.set_connected(connected, "")

            # 更新控制面板
            self.control_panel.set_connected(connected)

            # 保存房间号（连接成功时）
            if connected and self.orchestrator:
                room_id = self.orchestrator.room_id
                self.gui_config.save_room_id(room_id, remember=True)
                logger.debug(f"房间号已保存: {room_id}")

            # 添加日志
            if connected:
                self.log_widget.info(message, "连接")
            else:
                self.log_widget.warning(message, "连接")

            logger.info(f"连接状态变化: {connected} - {message}")
        except Exception as e:
            logger.error(f"处理连接状态变化失败: {e}")

    @pyqtSlot(str, str)
    def _on_error_occurred(self, error_type: str, error_message: str):
        """
        处理错误发生

        Args:
            error_type: 错误类型
            error_message: 错误消息
        """
        try:
            # 添加错误日志
            self.log_widget.error(f"[{error_type}] {error_message}", "错误")

            # 增加错误计数
            self.status_bar.increment_error_count()

            logger.error(f"错误发生: {error_type} - {error_message}")
        except Exception as e:
            logger.error(f"处理错误失败: {e}")

    @pyqtSlot(dict)
    def _on_stats_updated(self, stats: dict):
        """
        处理统计信息更新

        Args:
            stats: 统计信息字典
        """
        try:
            # 更新状态栏消息计数
            message_count = stats.get('messages_received', 0)
            self.status_bar.set_message_count(message_count)

            logger.debug(f"统计更新: {stats}")
        except Exception as e:
            logger.error(f"处理统计更新失败: {e}")

    # ==================== 控制面板信号槽 ====================

    def _on_connect_requested(self, room_id: str, remember: bool = True):
        """
        处理连接请求

        Args:
            room_id: 房间号
            remember: 是否记住房间号
        """
        try:
            self.log_widget.info(f"正在连接房间: {room_id}", "连接")
            self.log_widget.info("正在检查Chrome调试模式...", "Chrome")

            # 创建GUI编排器
            self.orchestrator = GUIOrchestrator(
                room_id=room_id,
                config_path="config.ini",
                use_ws=True  # 默认使用WebSocket监听模式
            )

            # 检查并启动Chrome调试模式（同步）
            self.log_widget.info("检查Chrome调试模式状态...", "Chrome")
            chrome_ready, chrome_message = self.orchestrator.ensure_chrome_debug_mode(
                kill_existing=False,
                wait_timeout=10
            )

            if not chrome_ready:
                # Chrome检查失败
                self.log_widget.error(f"Chrome调试模式检查失败: {chrome_message}", "Chrome")
                self.status_bar.increment_error_count()

                # 询问用户是否继续
                reply = QMessageBox.question(
                    self,
                    "Chrome调试模式不可用",
                    f"无法启动Chrome调试模式:\n\n{chrome_message}\n\n"
                    f"是否仍要尝试连接？\n\n"
                    f"提示: WebSocket监听模式需要Chrome在调试模式下运行。",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if reply == QMessageBox.No:
                    self.log_widget.warning("用户取消连接", "连接")
                    self.control_panel.set_connected(False)
                    return
                else:
                    self.log_widget.info("用户选择继续连接（可能失败）", "连接")
            else:
                # Chrome检查成功
                self.log_widget.info(f"Chrome就绪: {chrome_message}", "Chrome")

            # 连接信号
            self._connect_orchestrator_signals()

            # 保存房间号（如果需要记住）
            if remember:
                try:
                    self.control_panel.gui_config.save_room_id(room_id, remember=True)
                    self.log_widget.info(f"已保存房间号: {room_id}", "设置")
                except Exception as e:
                    logger.warning(f"保存房间号失败: {e}")

            # 在asyncio事件循环中初始化并运行
            asyncio.run_coroutine_threadsafe(
                self._run_orchestrator(),
                self.asyncio_loop
            )

        except Exception as e:
            error_msg = f"连接失败: {e}"
            self.log_widget.error(error_msg, "连接")
            self.status_bar.increment_error_count()
            logger.error(error_msg)
            self.control_panel.set_connected(False)

    def _on_disconnect_requested(self):
        """处理断开连接请求"""
        try:
            self.log_widget.warning("正在断开连接...", "连接")

            # 在asyncio事件循环中关闭编排器
            if self.orchestrator:
                asyncio.run_coroutine_threadsafe(
                    self.orchestrator.shutdown(),
                    self.asyncio_loop
                )
                self.orchestrator = None

            # 更新UI状态
            self.status_bar.set_connected(False, "")
            self.control_panel.set_connected(False)

            self.log_widget.info("已断开连接", "连接")

        except Exception as e:
            error_msg = f"断开连接失败: {e}"
            self.log_widget.error(error_msg, "连接")
            logger.error(error_msg)

    def _on_tts_enabled_changed(self, enabled: bool):
        """
        处理TTS开关变化

        Args:
            enabled: 是否启用TTS
        """
        try:
            if self.orchestrator:
                self.orchestrator.set_tts_enabled(enabled)
                self.log_widget.info(f"TTS已{'启用' if enabled else '禁用'}", "设置")
            else:
                self.log_widget.warning("编排器未初始化", "设置")
        except Exception as e:
            logger.error(f"处理TTS开关失败: {e}")

    def _on_speech_rate_changed(self, rate: int):
        """
        处理语速变化

        Args:
            rate: 语速值 (-50 到 +100)
        """
        try:
            if self.orchestrator:
                # 转换滑块值为速率字符串格式
                rate_str = f"{rate:+d}%"
                self.orchestrator.set_tts_rate(rate_str)
                # 不再记录日志到UI，避免频繁更新
                # 日志已在control_panel中通过logger.info记录到文件
            else:
                logger.warning("编排器未初始化，无法设置语速")
        except Exception as e:
            logger.error(f"处理语速变化失败: {e}")

    def _on_volume_changed(self, volume: int):
        """
        处理音量变化

        Args:
            volume: 音量值 (0-100)
        """
        try:
            if self.orchestrator:
                # 转换为0.0-1.0范围并更新音量
                normalized_volume = volume / 100.0
                self.orchestrator.set_tts_volume(normalized_volume)
                # 不再记录日志到UI，避免频繁更新
                # 日志已在control_panel中通过logger.info记录到文件
            else:
                logger.warning("编排器未初始化，无法设置音量")
        except Exception as e:
            logger.error(f"处理音量变化失败: {e}")

    # ==================== 编排器信号连接 ====================

    def _connect_orchestrator_signals(self):
        """连接编排器信号到UI槽"""
        if not self.orchestrator:
            return

        # 使用Qt.QueuedConnection确保线程安全
        self.orchestrator.message_received.connect(
            self._on_message_received,
            Qt.QueuedConnection
        )
        self.orchestrator.connection_changed.connect(
            self._on_connection_changed,
            Qt.QueuedConnection
        )
        self.orchestrator.error_occurred.connect(
            self._on_error_occurred,
            Qt.QueuedConnection
        )
        self.orchestrator.stats_updated.connect(
            self._on_stats_updated,
            Qt.QueuedConnection
        )

        logger.debug("编排器信号已连接")

    async def _run_orchestrator(self):
        """运行编排器（在asyncio事件循环中）"""
        try:
            # 初始化编排器
            success = await self.orchestrator.initialize()
            if not success:
                logger.error("编排器初始化失败")
                return

            # 运行主循环
            await self.orchestrator.run()
        except Exception as e:
            logger.error(f"运行编排器失败: {e}")
            self.log_widget.error(f"运行异常: {e}", "编排器")

    # ==================== 菜单动作 ====================

    def _export_txt(self):
        """导出弹幕为TXT"""
        if not self.orchestrator:
            QMessageBox.warning(self, "提示", "请先连接直播间")
            return

        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出TXT",
            f"danmaku_{self.orchestrator.room_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "文本文件 (*.txt)"
        )

        if file_path:
            # 在asyncio事件循环中导出
            asyncio.run_coroutine_threadsafe(
                self._async_export_txt(file_path),
                self.asyncio_loop
            )

    async def _async_export_txt(self, file_path: str):
        """异步导出TXT"""
        try:
            success = self.orchestrator.export_to_txt(file_path)
            if success:
                self.log_widget.info(f"导出成功: {file_path}", "导出")
                QMessageBox.information(self, "成功", f"弹幕已导出到:\n{file_path}")
            else:
                self.log_widget.error(f"导出失败: {file_path}", "导出")
                QMessageBox.warning(self, "失败", "导出失败，请查看日志")
        except Exception as e:
            logger.error(f"导出TXT失败: {e}")
            self.log_widget.error(f"导出失败: {e}", "导出")

    def _export_json(self):
        """导出弹幕为JSON"""
        if not self.orchestrator:
            QMessageBox.warning(self, "提示", "请先连接直播间")
            return

        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出JSON",
            f"danmaku_{self.orchestrator.room_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON文件 (*.json)"
        )

        if file_path:
            # 在asyncio事件循环中导出
            asyncio.run_coroutine_threadsafe(
                self._async_export_json(file_path),
                self.asyncio_loop
            )

    async def _async_export_json(self, file_path: str):
        """异步导出JSON"""
        try:
            success = self.orchestrator.export_to_json(file_path)
            if success:
                self.log_widget.info(f"导出成功: {file_path}", "导出")
                QMessageBox.information(self, "成功", f"弹幕已导出到:\n{file_path}")
            else:
                self.log_widget.error(f"导出失败: {file_path}", "导出")
                QMessageBox.warning(self, "失败", "导出失败，请查看日志")
        except Exception as e:
            logger.error(f"导出JSON失败: {e}")
            self.log_widget.error(f"导出失败: {e}", "导出")

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
                <li>自动启动Chrome调试模式</li>
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

            # 保存窗口大小
            width = self.width()
            height = self.height()
            self.control_panel.gui_config.save_window_size(width, height)
            logger.debug(f"窗口大小已保存: {width}x{height}")

            # 停止asyncio定时器
            if self.asyncio_timer:
                self.asyncio_timer.stop()

            # 关闭编排器
            if self.orchestrator:
                asyncio.run_coroutine_threadsafe(
                    self.orchestrator.shutdown(),
                    self.asyncio_loop
                )

            # 关闭事件循环
            if self.asyncio_loop:
                self.asyncio_loop.close()

            event.accept()
        else:
            logger.info("用户取消退出")
            event.ignore()
