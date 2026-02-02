"""
默认配置定义

使用dataclass定义所有配置项的默认值，提供类型安全和优雅降级。
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RoomConfig:
    """直播间配置"""
    room_id: str = ""  # 直播间房间ID（必填，但提供空字符串默认值）
    cookie_file: str = "cookies.txt"  # Cookie文件路径
    auto_reconnect: bool = True  # 自动重连
    heartbeat_interval: int = 30  # 心跳间隔（秒）


@dataclass
class TTSConfig:
    """文字转语音配置"""
    engine: str = "edge"  # TTS引擎（edge: 微软Edge TTS）
    voice: str = "zh-CN-XiaoxiaoNeural"  # 音色（默认女声）
    rate: str = "+0%"  # 语速（范围：-50% 到 +100%）
    volume: str = "+0%"  # 音量（范围：-50% 到 +100%）
    cache_enabled: bool = True  # 启用音频缓存
    cache_days: int = 7  # 缓存保留天数


@dataclass
class FilterUserConfig:
    """用户过滤配置"""
    blocked: List[str] = field(default_factory=list)  # 黑名单用户
    only_vip: bool = False  # 仅播放VIP用户弹幕


@dataclass
class FilterKeywordConfig:
    """关键词过滤配置"""
    blocked: List[str] = field(default_factory=list)  # 屏蔽关键词
    only: List[str] = field(default_factory=list)  # 仅播放包含关键词的弹幕


@dataclass
class FilterConfig:
    """弹幕过滤配置"""
    min_length: int = 1  # 最小弹幕长度
    max_length: int = 100  # 最大弹幕长度
    enable_filter: bool = True  # 启用过滤
    users: FilterUserConfig = field(default_factory=FilterUserConfig)  # 用户过滤
    keywords: FilterKeywordConfig = field(default_factory=FilterKeywordConfig)  # 关键词过滤


@dataclass
class PlaybackConfig:
    """播放配置"""
    max_queue_size: int = 10  # 最大播放队列长度
    play_interval: float = 0.5  # 播放间隔（秒）
    volume: float = 0.7  # 播放音量（0.0-1.0）


@dataclass
class LogConfig:
    """日志配置"""
    level: str = "INFO"  # 日志级别（DEBUG, INFO, WARNING, ERROR）
    enable_console: bool = True  # 启用控制台输出
    enable_file: bool = False  # 启用文件输出
    file_path: str = "logs/danmu.log"  # 日志文件路径


@dataclass
class AppConfig:
    """应用程序总配置"""
    room: RoomConfig = field(default_factory=RoomConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    filter: FilterConfig = field(default_factory=FilterConfig)
    playback: PlaybackConfig = field(default_factory=PlaybackConfig)
    log: LogConfig = field(default_factory=LogConfig)


# 默认配置实例（单例）
DEFAULT_CONFIG = AppConfig()
