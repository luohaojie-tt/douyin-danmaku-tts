"""
控制面板 - 用户控制界面

提供房间号输入、连接控制、TTS开关、语速和音量调节功能。
"""

import logging
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QCheckBox, QSlider, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject

logger = logging.getLogger(__name__)


class ControlPanelSignals(QObject):
    """控制面板信号"""
    # 连接信号
    connect_requested = pyqtSignal(str)  # 参数: 房间号
    disconnect_requested = pyqtSignal()
    
    # TTS设置信号
    tts_enabled_changed = pyqtSignal(bool)
    speech_rate_changed = pyqtSignal(int)  # 参数: 语速百分比 (-50 到 +100)
    volume_changed = pyqtSignal(int)  # 参数: 音量 (0-100)


class ControlPanel(QWidget):
    """
    控制面板
    
    功能:
        - 房间号输入
        - 连接/断开按钮
        - TTS开关
        - 语速调节 (-50% 到 +100%)
        - 音量调节 (0-100)
        - 设置按钮
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化控制面板
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        
        # 信号对象
        self.signals = ControlPanelSignals()
        
        # 连接状态
        self._is_connected = False
        
        # 初始化UI
        self._init_ui()
        
        logger.debug("控制面板已初始化")

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # === 连接控制组 ===
        connection_group = QGroupBox("连接控制")
        connection_layout = QVBoxLayout()
        
        # 房间号输入
        room_layout = QHBoxLayout()
        room_label = QLabel("直播间号:")
        self.room_input = QLineEdit()
        self.room_input.setPlaceholderText("请输入房间号")
        self.room_input.setText("728804746624")  # 默认房间号
        room_layout.addWidget(room_label)
        room_layout.addWidget(self.room_input)
        connection_layout.addLayout(room_layout)
        
        # 连接按钮
        self.connect_button = QPushButton("连接")
        self.connect_button.setCheckable(True)
        self.connect_button.clicked.connect(self._on_connect_clicked)
        connection_layout.addWidget(self.connect_button)
        
        connection_group.setLayout(connection_layout)
        layout.addWidget(connection_group)
        
        # === TTS控制组 ===
        tts_group = QGroupBox("语音播报")
        tts_layout = QVBoxLayout()
        
        # TTS开关
        self.tts_checkbox = QCheckBox("启用语音播报")
        self.tts_checkbox.setChecked(True)
        self.tts_checkbox.stateChanged.connect(self._on_tts_changed)
        tts_layout.addWidget(self.tts_checkbox)
        
        # 语速控制
        rate_label_layout = QHBoxLayout()
        rate_label_layout.addWidget(QLabel("语速:"))
        self.rate_value_label = QLabel("+50%")
        rate_label_layout.addStretch()
        rate_label_layout.addWidget(self.rate_value_label)
        tts_layout.addLayout(rate_label_layout)
        
        self.rate_slider = QSlider(Qt.Horizontal)
        self.rate_slider.setMinimum(-50)
        self.rate_slider.setMaximum(100)
        self.rate_slider.setValue(50)
        self.rate_slider.setTickPosition(QSlider.TicksBelow)
        self.rate_slider.setTickInterval(10)
        self.rate_slider.valueChanged.connect(self._on_rate_changed)
        tts_layout.addWidget(self.rate_slider)
        
        # 音量控制
        volume_label_layout = QHBoxLayout()
        volume_label_layout.addWidget(QLabel("音量:"))
        self.volume_value_label = QLabel("70")
        volume_label_layout.addStretch()
        volume_label_layout.addWidget(self.volume_value_label)
        tts_layout.addLayout(volume_label_layout)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(70)
        self.volume_slider.setTickPosition(QSlider.TicksBelow)
        self.volume_slider.setTickInterval(10)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        tts_layout.addWidget(self.volume_slider)
        
        tts_group.setLayout(tts_layout)
        layout.addWidget(tts_group)
        
        # === 设置组 ===
        settings_group = QGroupBox("设置")
        settings_layout = QVBoxLayout()
        
        # 设置按钮
        self.settings_button = QPushButton("打开设置")
        self.settings_button.clicked.connect(self.open_settings_dialog)
        settings_layout.addWidget(self.settings_button)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 添加弹性空间
        layout.addStretch()
        
        logger.debug("控制面板UI已创建")

    def _on_connect_clicked(self):
        """连接按钮点击事件"""
        if self.connect_button.isChecked():
            # 连接
            room_id = self.room_input.text().strip()
            if not room_id:
                logger.warning("房间号为空")
                self.connect_button.setChecked(False)
                return
            
            logger.info(f"请求连接房间: {room_id}")
            self._is_connected = True
            self.connect_button.setText("断开")
            self.room_input.setEnabled(False)
            
            # 发射连接信号
            self.signals.connect_requested.emit(room_id)
        else:
            # 断开
            logger.info("请求断开连接")
            self._is_connected = False
            self.connect_button.setText("连接")
            self.room_input.setEnabled(True)
            
            # 发射断开信号
            self.signals.disconnect_requested.emit()

    def _on_tts_changed(self, state: int):
        """
        TTS开关状态变化
        
        Args:
            state: 复选框状态
        """
        enabled = state == Qt.Checked
        logger.info(f"TTS {'启用' if enabled else '禁用'}")
        self.signals.tts_enabled_changed.emit(enabled)

    def _on_rate_changed(self, value: int):
        """
        语速变化
        
        Args:
            value: 语速值 (-50 到 +100)
        """
        self.rate_value_label.setText(f"{value:+d}%")
        logger.debug(f"语速调整为: {value:+d}%")
        self.signals.speech_rate_changed.emit(value)

    def _on_volume_changed(self, value: int):
        """
        音量变化
        
        Args:
            value: 音量值 (0-100)
        """
        self.volume_value_label.setText(str(value))
        logger.debug(f"音量调整为: {value}")
        self.signals.volume_changed.emit(value)

    def open_settings_dialog(self):
        """打开设置对话框"""
        logger.info("打开设置对话框")
        from src.gui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        dialog.exec_()

    def get_room_id(self) -> str:
        """
        获取房间号
        
        Returns:
            房间号
        """
        return self.room_input.text().strip()

    def set_connected(self, connected: bool):
        """
        设置连接状态
        
        Args:
            connected: 是否已连接
        """
        self._is_connected = connected
        self.connect_button.setChecked(connected)
        self.connect_button.setText("断开" if connected else "连接")
        self.room_input.setEnabled(not connected)

    def is_connected(self) -> bool:
        """
        是否已连接
        
        Returns:
            是否已连接
        """
        return self._is_connected
