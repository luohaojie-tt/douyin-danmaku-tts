"""
配置管理模块

提供配置加载、默认值定义和配置验证功能。
"""

from src.config.defaults import (
    DEFAULT_CONFIG,
    AppConfig,
    RoomConfig,
    TTSConfig,
    FilterConfig,
    PlaybackConfig,
    LogConfig,
)
from src.config.loader import load_config, validate_config

__all__ = [
    # 导出默认配置
    'DEFAULT_CONFIG',
    # 导出配置类
    'AppConfig',
    'RoomConfig',
    'TTSConfig',
    'FilterConfig',
    'PlaybackConfig',
    'LogConfig',
    # 导出加载函数
    'load_config',
    'validate_config',
]
