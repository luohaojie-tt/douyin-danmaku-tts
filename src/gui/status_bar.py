"""
状态栏组件 - 显示应用程序状态

提供连接状态、消息计数、错误计数等状态信息。
"""

import logging
from typing import Optional

from PyQt5.QtWidgets import QStatusBar, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class StatusBar:
    """
    状态栏组件
    
    显示:
        - 连接状态指示器
        - 消息计数
        - 错误计数
        - 当前房间ID
    """

    def __init__(self):
        """初始化状态栏"""
        # 创建QStatusBar
        self.widget = QStatusBar()
        
        # 状态数据
        self._is_connected = False
        self._message_count = 0
        self._error_count = 0
        self._room_id = ""
        
        # UI组件
        self._status_indicator: Optional[QLabel] = None
        self._message_label: Optional[QLabel] = None
        self._error_label: Optional[QLabel] = None
        self._room_label: Optional[QLabel] = None
        
        # 初始化UI
        self._init_ui()
        
        logger.debug("状态栏已初始化")

    def _init_ui(self):
        """初始化UI"""
        # 连接状态指示器
        self._status_indicator = QLabel("● 未连接")
        self._status_indicator.setStyleSheet("color: gray;")
        status_font = QFont()
        status_font.setBold(True)
        self._status_indicator.setFont(status_font)
        
        # 消息计数
        self._message_label = QLabel("消息: 0")
        self._message_label.setStyleSheet("color: #d4d4d4;")
        
        # 错误计数
        self._error_label = QLabel("错误: 0")
        self._error_label.setStyleSheet("color: #d4d4d4;")
        
        # 房间ID
        self._room_label = QLabel("房间: -")
        self._room_label.setStyleSheet("color: #d4d4d4;")
        
        # 添加到状态栏
        self.widget.addPermanentWidget(self._status_indicator, 1)  # 添加到左侧
        self.widget.addPermanentWidget(self._room_label)
        self.widget.addPermanentWidget(self._message_label)
        self.widget.addPermanentWidget(self._error_label)
        
        # 设置状态栏样式
        self.widget.setStyleSheet("""
            QStatusBar {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border-top: 1px solid #3e3e3e;
            }
            QStatusBar::item {
                border: none;
            }
        """)

    def set_connected(self, connected: bool, room_id: str = ""):
        """
        设置连接状态
        
        Args:
            connected: 是否已连接
            room_id: 房间ID
        """
        self._is_connected = connected
        self._room_id = room_id
        
        if connected:
            self._status_indicator.setText("● 已连接")
            self._status_indicator.setStyleSheet("color: #4ade80;")  # 绿色
            self._room_label.setText(f"房间: {room_id}")
            logger.info(f"状态栏: 已连接到房间 {room_id}")
        else:
            self._status_indicator.setText("● 未连接")
            self._status_indicator.setStyleSheet("color: gray;")
            self._room_label.setText("房间: -")
            logger.info("状态栏: 已断开连接")

    def set_message_count(self, count: int):
        """
        设置消息计数
        
        Args:
            count: 消息数量
        """
        self._message_count = count
        self._message_label.setText(f"消息: {count}")
        
        logger.debug(f"状态栏: 消息计数更新为 {count}")

    def increment_message_count(self):
        """消息计数加1"""
        self._message_count += 1
        self.set_message_count(self._message_count)

    def set_error_count(self, count: int):
        """
        设置错误计数
        
        Args:
            count: 错误数量
        """
        self._error_count = count
        self._error_label.setText(f"错误: {count}")
        
        # 如果有错误，显示红色
        if count > 0:
            self._error_label.setStyleSheet("color: #f87171;")  # 红色
        else:
            self._error_label.setStyleSheet("color: #d4d4d4;")
        
        logger.debug(f"状态栏: 错误计数更新为 {count}")

    def increment_error_count(self):
        """错误计数加1"""
        self._error_count += 1
        self.set_error_count(self._error_count)

    def reset_counts(self):
        """重置计数器"""
        self._message_count = 0
        self._error_count = 0
        self.set_message_count(0)
        self.set_error_count(0)
        logger.debug("状态栏: 计数器已重置")

    def show_message(self, message: str, timeout: int = 5000):
        """
        显示临时消息
        
        Args:
            message: 消息内容
            timeout: 显示时间(毫秒)，0表示永久显示
        """
        self.widget.showMessage(message, timeout)
        logger.debug(f"状态栏: 显示消息 '{message}' (超时: {timeout}ms)")

    def get_message_count(self) -> int:
        """
        获取消息计数
        
        Returns:
            消息数量
        """
        return self._message_count

    def get_error_count(self) -> int:
        """
        获取错误计数
        
        Returns:
            错误数量
        """
        return self._error_count

    def is_connected(self) -> bool:
        """
        是否已连接
        
        Returns:
            是否已连接
        """
        return self._is_connected
