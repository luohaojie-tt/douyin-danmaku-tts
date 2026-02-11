"""
弹幕显示组件 - 显示实时弹幕列表

提供滚动弹幕列表，显示时间戳、用户名和消息内容。
"""

import logging
from datetime import datetime
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QListWidget, QListWidgetItem, QMenu, QAction,
    QAbstractItemView, QVBoxLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QColor, QFont

logger = logging.getLogger(__name__)


class DanmakuWidgetSignals(QObject):
    """弹幕组件信号"""
    # 弹幕数量变化信号
    count_changed = pyqtSignal(int)


class DanmakuWidget(QWidget):
    """
    弹幕显示组件
    
    功能:
        - 显示格式: [HH:MM:SS] 用户名: 消息内容
        - 自动滚动到最新消息
        - 限制最大消息数量(1000条)
        - 右键菜单支持复制
    """

    MAX_MESSAGES = 1000  # 最大消息数量

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化弹幕组件
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        
        # 信号对象
        self.signals = DanmakuWidgetSignals()
        
        # 消息计数
        self._message_count = 0
        
        # 初始化UI
        self._init_ui()
        
        logger.debug("弹幕组件已初始化")

    def _init_ui(self):
        """初始化UI"""
        # 创建列表控件
        self.list_widget = QListWidget()
        
        # 设置选择模式
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # 启用右键菜单
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        
        # 设置布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list_widget)

    def add_danmaku(self, username: str, content: str, timestamp: Optional[datetime] = None):
        """
        添加弹幕
        
        Args:
            username: 用户名
            content: 弹幕内容
            timestamp: 时间戳 (默认为当前时间)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # 格式化时间
        time_str = timestamp.strftime("%H:%M:%S")
        
        # 创建列表项
        item_text = f"[{time_str}] {username}: {content}"
        item = QListWidgetItem(item_text)
        
        # 设置样式
        item.setForeground(QColor(220, 220, 220))  # 浅灰色文字
        font = QFont()
        font.setPointSize(10)
        item.setFont(font)
        
        # 添加到列表
        self.list_widget.addItem(item)
        
        # 自动滚动到底部
        self.list_widget.scrollToBottom()
        
        # 更新计数
        self._message_count += 1
        self._prune_old_messages()
        self.signals.count_changed.emit(self._message_count)
        
        logger.debug(f"添加弹幕: {username}: {content}")

    def _prune_old_messages(self):
        """清理旧消息，保持最大数量限制"""
        while self.list_widget.count() > self.MAX_MESSAGES:
            # 移除第一条消息
            self.list_widget.takeItem(0)
            self._message_count -= 1
        
        logger.debug(f"当前消息数量: {self.list_widget.count()}")

    def _show_context_menu(self, pos):
        """
        显示右键菜单
        
        Args:
            pos: 鼠标位置
        """
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        
        # 创建菜单
        menu = QMenu(self)
        
        # 复制动作
        copy_action = QAction("复制(&C)", self)
        copy_action.triggered.connect(lambda: self._copy_item(item))
        menu.addAction(copy_action)
        
        # 清空动作
        clear_action = QAction("清空弹幕(&L)", self)
        clear_action.triggered.connect(self.clear_danmaku)
        menu.addAction(clear_action)
        
        # 显示菜单
        menu.exec_(self.list_widget.mapToGlobal(pos))

    def _copy_item(self, item: QListWidgetItem):
        """
        复制列表项内容
        
        Args:
            item: 列表项
        """
        text = item.text()
        # 去掉时间戳，只复制用户名和内容
        if "] " in text:
            text = text.split("] ", 1)[1]
        
        clipboard = self.list_widget.clipboard()
        clipboard.setText(text)
        
        logger.debug(f"已复制: {text}")

    def clear_danmaku(self):
        """清空所有弹幕"""
        self.list_widget.clear()
        self._message_count = 0
        self.signals.count_changed.emit(0)
        logger.info("已清空弹幕")

    def get_message_count(self) -> int:
        """
        获取消息数量
        
        Returns:
            消息数量
        """
        return self._message_count

    def get_all_messages(self) -> list:
        """
        获取所有消息
        
        Returns:
            消息列表
        """
        messages = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            messages.append(item.text())
        return messages
