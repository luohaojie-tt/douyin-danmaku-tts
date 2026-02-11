"""
日志输出组件 - 显示应用程序日志

提供颜色编码的日志输出显示区域。
"""

import logging
from typing import Optional
from datetime import datetime

from PyQt5.QtWidgets import QWidget, QTextEdit, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QColorConstants, QFont

logger = logging.getLogger(__name__)


class LogWidget(QWidget):
    """
    日志输出组件
    
    功能:
        - 颜色编码: INFO=蓝色, WARNING=黄色, ERROR=红色
        - 自动滚动到最新日志
        - 限制最大行数(500行)
        - 只读模式
    """

    MAX_LINES = 500  # 最大行数
    THROTTLE_MS = 50  # 节流时间（毫秒）

    # 日志颜色映射
    LOG_COLORS = {
        "INFO": QColor(100, 149, 237),    # 矢车菊蓝
        "WARNING": QColor(255, 215, 0),   # 金色
        "ERROR": QColor(220, 20, 60),     # 猩红色
        "DEBUG": QColor(128, 128, 128),   # 灰色
    }

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化日志组件

        Args:
            parent: 父窗口
        """
        super().__init__(parent)

        # 节流机制
        self._pending_logs = []
        self._flush_timer = QTimer()
        self._flush_timer.setSingleShot(True)
        self._flush_timer.timeout.connect(self._flush_pending_logs)

        # 初始化UI
        self._init_ui()

        logger.debug("日志组件已初始化")

    def _init_ui(self):
        """初始化UI"""
        # 创建文本编辑器
        self.text_edit = QTextEdit()
        
        # 设置为只读模式
        self.text_edit.setReadOnly(True)
        
        # 设置字体
        font = QFont("Consolas", 9)
        self.text_edit.setFont(font)
        
        # 设置背景色
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
            }
        """)
        
        # 设置布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.text_edit)

    def add_log(self, level: str, message: str, source: str = ""):
        """
        添加日志（带节流优化）

        Args:
            level: 日志级别 (INFO, WARNING, ERROR, DEBUG)
            message: 日志消息
            source: 日志来源 (可选)
        """
        # 添加到待处理队列
        self._pending_logs.append((level, message, source))

        # 如果定时器未运行，启动它
        if not self._flush_timer.isActive():
            self._flush_timer.start(self.THROTTLE_MS)

    def _flush_pending_logs(self):
        """批量处理待处理的日志"""
        if not self._pending_logs:
            return

        # 批量处理所有待处理的日志
        for level, message, source in self._pending_logs:
            self._add_log_impl(level, message, source)

        self._pending_logs.clear()

    def _add_log_impl(self, level: str, message: str, source: str = ""):
        """
        实际执行日志添加操作

        Args:
            level: 日志级别 (INFO, WARNING, ERROR, DEBUG)
            message: 日志消息
            source: 日志来源 (可选)
        """
        # 获取时间戳
        timestamp = datetime.now().strftime("%H:%M:%S")

        # 格式化日志
        if source:
            log_text = f"[{timestamp}] [{level}] [{source}] {message}"
        else:
            log_text = f"[{timestamp}] [{level}] {message}"

        # 获取颜色
        color = self.LOG_COLORS.get(level, QColor(220, 220, 220))

        # 移动光标到末尾
        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.End)

        # 插入带颜色的文本
        char_format = cursor.charFormat()
        char_format.setForeground(color)
        cursor.setCharFormat(char_format)
        cursor.insertText(log_text + "\n")

        # 自动滚动到底部
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()

        # 清理旧日志
        self._prune_old_logs()

        logger.debug(f"添加日志: {level} - {message}")

    def _prune_old_logs(self):
        """清理旧日志，保持最大行数限制"""
        # 获取当前行数
        line_count = self.text_edit.document().blockCount()
        
        if line_count > self.MAX_LINES:
            # 计算需要删除的行数
            lines_to_remove = line_count - self.MAX_LINES
            
            # 移动到文档开头
            cursor = self.text_edit.textCursor()
            cursor.movePosition(cursor.Start)
            
            # 选择并删除指定行数
            for _ in range(lines_to_remove):
                cursor.select(cursor.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()  # 删除换行符
            
            logger.debug(f"清理了 {lines_to_remove} 行旧日志")

    def info(self, message: str, source: str = ""):
        """
        添加INFO级别日志
        
        Args:
            message: 日志消息
            source: 日志来源
        """
        self.add_log("INFO", message, source)

    def warning(self, message: str, source: str = ""):
        """
        添加WARNING级别日志
        
        Args:
            message: 日志消息
            source: 日志来源
        """
        self.add_log("WARNING", message, source)

    def error(self, message: str, source: str = ""):
        """
        添加ERROR级别日志
        
        Args:
            message: 日志消息
            source: 日志来源
        """
        self.add_log("ERROR", message, source)

    def debug(self, message: str, source: str = ""):
        """
        添加DEBUG级别日志
        
        Args:
            message: 日志消息
            source: 日志来源
        """
        self.add_log("DEBUG", message, source)

    def clear(self):
        """清空所有日志"""
        self.text_edit.clear()
        logger.debug("已清空日志")
