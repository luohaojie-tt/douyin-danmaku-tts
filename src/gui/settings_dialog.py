"""
设置对话框 - 应用程序设置

提供过滤设置、高级设置和关于信息的配置界面。
"""

import logging
from typing import Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QPushButton, QListWidget,
    QListWidgetItem, QGroupBox, QTextEdit
)
from PyQt5.QtCore import Qt

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """
    设置对话框
    
    标签页:
        - 过滤器: 关键词黑名单、用户黑名单
        - 高级: 高级设置选项
        - 关于: 版本信息
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化设置对话框
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        
        # 设置窗口属性
        self.setWindowTitle("设置")
        self.setModal(True)
        self.resize(600, 500)
        
        # 初始化UI
        self._init_ui()
        
        logger.debug("设置对话框已初始化")

    def _init_ui(self):
        """初始化UI"""
        # 主布局
        layout = QVBoxLayout(self)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # === 过滤器标签页 ===
        filter_tab = self._create_filter_tab()
        tab_widget.addTab(filter_tab, "过滤器")
        
        # === 高级标签页 ===
        advanced_tab = self._create_advanced_tab()
        tab_widget.addTab(advanced_tab, "高级")
        
        # === 关于标签页 ===
        about_tab = self._create_about_tab()
        tab_widget.addTab(about_tab, "关于")
        
        layout.addWidget(tab_widget)
        
        # === 底部按钮 ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 保存按钮
        save_button = QPushButton("保存")
        save_button.clicked.connect(self._save_settings)
        button_layout.addWidget(save_button)
        
        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)

    def _create_filter_tab(self) -> QWidget:
        """创建过滤器标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # === 关键词黑名单 ===
        keyword_group = QGroupBox("关键词黑名单")
        keyword_layout = QVBoxLayout()
        
        # 关键词列表
        self.keyword_list = QListWidget()
        self._load_default_keywords()
        keyword_layout.addWidget(self.keyword_list)
        
        # 添加/删除按钮
        keyword_button_layout = QHBoxLayout()
        add_keyword_button = QPushButton("添加")
        add_keyword_button.clicked.connect(self._add_keyword)
        keyword_button_layout.addWidget(add_keyword_button)
        
        remove_keyword_button = QPushButton("删除")
        remove_keyword_button.clicked.connect(self._remove_keyword)
        keyword_button_layout.addWidget(remove_keyword_button)
        
        keyword_layout.addLayout(keyword_button_layout)
        keyword_group.setLayout(keyword_layout)
        layout.addWidget(keyword_group)
        
        # === 用户黑名单 ===
        user_group = QGroupBox("用户黑名单")
        user_layout = QVBoxLayout()
        
        # 用户列表
        self.user_list = QListWidget()
        user_layout.addWidget(self.user_list)
        
        # 添加/删除按钮
        user_button_layout = QHBoxLayout()
        add_user_button = QPushButton("添加")
        add_user_button.clicked.connect(self._add_user)
        user_button_layout.addWidget(add_user_button)
        
        remove_user_button = QPushButton("删除")
        remove_user_button.clicked.connect(self._remove_user)
        user_button_layout.addWidget(remove_user_button)
        
        user_layout.addLayout(user_button_layout)
        user_group.setLayout(user_layout)
        layout.addWidget(user_group)
        
        return widget

    def _create_advanced_tab(self) -> QWidget:
        """创建高级标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 说明文本
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setPlainText("""
高级设置选项

当前版本的高级设置功能正在开发中。

未来计划支持：
- 自定义TTS音色
- 弹幕过滤规则自定义
- 日志级别设置
- 自动重连设置
- 代理设置
        """)
        layout.addWidget(info_text)
        
        return widget

    def _create_about_tab(self) -> QWidget:
        """创建关于标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 版本信息
        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setPlainText("""
抖音弹幕语音播报工具 GUI 版本
版本: 0.1.0

功能特性:
• 实时监听抖音直播间弹幕
• 语音播报弹幕内容
• 可调节语速和音量
• 支持黑名单过滤
• 弹幕导出功能

技术栈:
• PyQt5 - 图形界面框架
• asyncio - 异步编程
• edge-tts - 微软Edge TTS
• pygame - 音频播放

项目地址:
LiveStreamInfoRetrievalProject

许可协议:
MIT License
        """)
        layout.addWidget(about_text)
        
        return widget

    def _load_default_keywords(self):
        """加载默认关键词黑名单"""
        # TODO: 从配置文件加载
        default_keywords = ["垃圾", "广告", "刷屏"]
        for keyword in default_keywords:
            self.keyword_list.addItem(keyword)

    def _add_keyword(self):
        """添加关键词"""
        from PyQt5.QtWidgets import QInputDialog
        
        keyword, ok = QInputDialog.getText(
            self, "添加关键词", "请输入要屏蔽的关键词:"
        )
        
        if ok and keyword:
            self.keyword_list.addItem(keyword)
            logger.info(f"添加关键词: {keyword}")

    def _remove_keyword(self):
        """删除关键词"""
        current_item = self.keyword_list.currentItem()
        if current_item:
            keyword = current_item.text()
            row = self.keyword_list.row(current_item)
            self.keyword_list.takeItem(row)
            logger.info(f"删除关键词: {keyword}")

    def _add_user(self):
        """添加用户"""
        from PyQt5.QtWidgets import QInputDialog
        
        user, ok = QInputDialog.getText(
            self, "添加用户", "请输入要屏蔽的用户名:"
        )
        
        if ok and user:
            self.user_list.addItem(user)
            logger.info(f"添加用户: {user}")

    def _remove_user(self):
        """删除用户"""
        current_item = self.user_list.currentItem()
        if current_item:
            user = current_item.text()
            row = self.user_list.row(current_item)
            self.user_list.takeItem(row)
            logger.info(f"删除用户: {user}")

    def _save_settings(self):
        """保存设置"""
        # TODO: 保存到配置文件
        
        # 收集关键词黑名单
        keywords = []
        for i in range(self.keyword_list.count()):
            item = self.keyword_list.item(i)
            keywords.append(item.text())
        
        # 收集用户黑名单
        users = []
        for i in range(self.user_list.count()):
            item = self.user_list.item(i)
            users.append(item.text())
        
        logger.info(f"保存设置: 关键词={keywords}, 用户={users}")
        
        # 关闭对话框
        self.accept()
