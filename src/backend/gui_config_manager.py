"""
GUI配置管理器 - 处理GUI特定配置的保存和加载

提供房间号记忆、窗口大小保存等功能。
"""

import configparser
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class GUIConfigManager:
    """
    GUI配置管理器

    管理GUI相关的配置项，如记住房间号、窗口大小等。
    """

    def __init__(self, config_path: str = "config.ini"):
        """
        初始化GUI配置管理器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.parser = configparser.ConfigParser(interpolation=None)

        # 加载现有配置
        if self.config_path.exists():
            self.parser.read(self.config_path, encoding='utf-8')

        # 确保gui节存在
        if not self.parser.has_section('gui'):
            self.parser.add_section('gui')

    def get_last_room_id(self) -> str:
        """
        获取上次连接的房间号

        Returns:
            房间号，如果没有则返回空字符串
        """
        if self.parser.has_option('gui', 'last_room_id'):
            return self.parser.get('gui', 'last_room_id')
        return ""

    def get_remember_room(self) -> bool:
        """
        获取是否记住房间号设置

        Returns:
            是否记住房间号
        """
        if self.parser.has_option('gui', 'remember_room'):
            return self.parser.getboolean('gui', 'remember_room')
        return True  # 默认记住

    def save_room_id(self, room_id: str, remember: bool = True) -> bool:
        """
        保存房间号

        Args:
            room_id: 房间号
            remember: 是否记住（默认True）

        Returns:
            是否保存成功
        """
        try:
            # 更新配置
            self.parser.set('gui', 'last_room_id', room_id)
            self.parser.set('gui', 'remember_room', 'true' if remember else 'false')

            # 保存到文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.parser.write(f)

            logger.info(f"房间号已保存: {room_id} (记住: {remember})")
            return True

        except Exception as e:
            logger.error(f"保存房间号失败: {e}")
            return False

    def clear_room_id(self) -> bool:
        """
        清除保存的房间号

        Returns:
            是否清除成功
        """
        try:
            if self.parser.has_option('gui', 'last_room_id'):
                self.parser.remove_option('gui', 'last_room_id')

            # 设置remember为false
            self.parser.set('gui', 'remember_room', 'false')

            # 保存到文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.parser.write(f)

            logger.info("房间号已清除")
            return True

        except Exception as e:
            logger.error(f"清除房间号失败: {e}")
            return False

    def get_window_size(self) -> tuple[int, int]:
        """
        获取保存的窗口大小

        Returns:
            (width, height) 窗口大小，如果没有保存则返回默认值
        """
        width = 1000
        height = 700

        if self.parser.has_option('gui', 'window_width'):
            try:
                width = self.parser.getint('gui', 'window_width')
            except ValueError:
                pass

        if self.parser.has_option('gui', 'window_height'):
            try:
                height = self.parser.getint('gui', 'window_height')
            except ValueError:
                pass

        return (width, height)

    def save_window_size(self, width: int, height: int) -> bool:
        """
        保存窗口大小

        Args:
            width: 窗口宽度
            height: 窗口高度

        Returns:
            是否保存成功
        """
        try:
            self.parser.set('gui', 'window_width', str(width))
            self.parser.set('gui', 'window_height', str(height))

            # 保存到文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.parser.write(f)

            logger.debug(f"窗口大小已保存: {width}x{height}")
            return True

        except Exception as e:
            logger.error(f"保存窗口大小失败: {e}")
            return False

    def get_auto_start_chrome(self) -> bool:
        """
        获取是否自动启动Chrome调试模式

        Returns:
            是否自动启动Chrome
        """
        if self.parser.has_option('gui', 'auto_start_chrome'):
            return self.parser.getboolean('gui', 'auto_start_chrome')
        return True  # 默认自动启动

    def set_auto_start_chrome(self, enabled: bool) -> bool:
        """
        设置是否自动启动Chrome调试模式

        Args:
            enabled: 是否启用

        Returns:
            是否设置成功
        """
        try:
            self.parser.set('gui', 'auto_start_chrome', 'true' if enabled else 'false')

            # 保存到文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.parser.write(f)

            logger.info(f"自动启动Chrome设置已保存: {enabled}")
            return True

        except Exception as e:
            logger.error(f"保存自动启动Chrome设置失败: {e}")
            return False

    def get_all_gui_settings(self) -> dict:
        """
        获取所有GUI设置

        Returns:
            包含所有GUI设置的字典
        """
        return {
            'last_room_id': self.get_last_room_id(),
            'remember_room': self.get_remember_room(),
            'window_size': self.get_window_size(),
            'auto_start_chrome': self.get_auto_start_chrome()
        }
