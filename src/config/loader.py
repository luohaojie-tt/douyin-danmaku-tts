"""
配置加载器

负责从config.ini文件加载配置，并与默认值合并，提供优雅降级。
"""

import configparser
import logging
from pathlib import Path
from typing import List

from src.config.defaults import (
    AppConfig,
    RoomConfig,
    TTSConfig,
    FilterConfig,
    FilterUserConfig,
    FilterKeywordConfig,
    PlaybackConfig,
    LogConfig,
    GUIConfig,
    DEFAULT_CONFIG
)

logger = logging.getLogger(__name__)


def _parse_bool(value: str) -> bool:
    """解析布尔值"""
    if isinstance(value, bool):
        return value
    return value.lower() in ('true', 'yes', '1', 'on')


def _parse_list(value: str) -> List[str]:
    """解析列表（逗号分隔）"""
    if not value or not value.strip():
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def _load_room_config(parser: configparser.ConfigParser) -> RoomConfig:
    """加载直播间配置"""
    section = 'room'
    if not parser.has_section(section):
        logger.warning(f"配置文件缺少 [{section}] 节，使用默认配置")
        return DEFAULT_CONFIG.room

    config = DEFAULT_CONFIG.room

    # room_id (必填，但可以空)
    if parser.has_option(section, 'room_id'):
        config.room_id = parser.get(section, 'room_id')

    # cookie_file
    if parser.has_option(section, 'cookie_file'):
        config.cookie_file = parser.get(section, 'cookie_file')

    # auto_reconnect
    if parser.has_option(section, 'auto_reconnect'):
        try:
            config.auto_reconnect = _parse_bool(parser.get(section, 'auto_reconnect'))
        except ValueError:
            logger.warning(f"auto_reconnect 配置值无效，使用默认值: {config.auto_reconnect}")

    # heartbeat_interval
    if parser.has_option(section, 'heartbeat_interval'):
        try:
            config.heartbeat_interval = parser.getint(section, 'heartbeat_interval')
        except ValueError:
            logger.warning(f"heartbeat_interval 配置值无效，使用默认值: {config.heartbeat_interval}")

    return config


def _load_tts_config(parser: configparser.ConfigParser) -> TTSConfig:
    """加载TTS配置"""
    section = 'tts'
    if not parser.has_section(section):
        logger.warning(f"配置文件缺少 [{section}] 节，使用默认配置")
        return DEFAULT_CONFIG.tts

    config = DEFAULT_CONFIG.tts

    # engine
    if parser.has_option(section, 'engine'):
        config.engine = parser.get(section, 'engine')

    # voice
    if parser.has_option(section, 'voice'):
        config.voice = parser.get(section, 'voice')

    # rate (可能包含%符号，使用safe_get避免格式化警告)
    if parser.has_option(section, 'rate'):
        config.rate = parser.get(section, 'rate')

    # volume (可能包含%符号，使用safe_get避免格式化警告)
    if parser.has_option(section, 'volume'):
        config.volume = parser.get(section, 'volume')

    # cache_enabled
    if parser.has_option(section, 'cache_enabled'):
        try:
            config.cache_enabled = _parse_bool(parser.get(section, 'cache_enabled'))
        except ValueError:
            logger.warning(f"cache_enabled 配置值无效，使用默认值: {config.cache_enabled}")

    # cache_days
    if parser.has_option(section, 'cache_days'):
        try:
            config.cache_days = parser.getint(section, 'cache_days')
        except ValueError:
            logger.warning(f"cache_days 配置值无效，使用默认值: {config.cache_days}")

    return config


def _load_filter_config(parser: configparser.ConfigParser) -> FilterConfig:
    """加载过滤配置"""
    section = 'filter'
    if not parser.has_section(section):
        logger.warning(f"配置文件缺少 [{section}] 节，使用默认配置")
        return DEFAULT_CONFIG.filter

    config = DEFAULT_CONFIG.filter

    # min_length
    if parser.has_option(section, 'min_length'):
        try:
            config.min_length = parser.getint(section, 'min_length')
        except ValueError:
            logger.warning(f"min_length 配置值无效，使用默认值: {config.min_length}")

    # max_length
    if parser.has_option(section, 'max_length'):
        try:
            config.max_length = parser.getint(section, 'max_length')
        except ValueError:
            logger.warning(f"max_length 配置值无效，使用默认值: {config.max_length}")

    # enable_filter
    if parser.has_option(section, 'enable_filter'):
        try:
            config.enable_filter = _parse_bool(parser.get(section, 'enable_filter'))
        except ValueError:
            logger.warning(f"enable_filter 配置值无效，使用默认值: {config.enable_filter}")

    # users子配置
    config.users = _load_filter_user_config(parser)

    # keywords子配置
    config.keywords = _load_filter_keyword_config(parser)

    return config


def _load_filter_user_config(parser: configparser.ConfigParser) -> FilterUserConfig:
    """加载用户过滤配置"""
    section = 'filter.users'
    config = FilterUserConfig()

    if parser.has_section(section):
        # blocked
        if parser.has_option(section, 'blocked'):
            config.blocked = _parse_list(parser.get(section, 'blocked'))

        # only_vip
        if parser.has_option(section, 'only_vip'):
            try:
                config.only_vip = _parse_bool(parser.get(section, 'only_vip'))
            except ValueError:
                logger.warning(f"only_vip 配置值无效，使用默认值: {config.only_vip}")

    return config


def _load_filter_keyword_config(parser: configparser.ConfigParser) -> FilterKeywordConfig:
    """加载关键词过滤配置"""
    section = 'filter.keywords'
    config = FilterKeywordConfig()

    if parser.has_section(section):
        # blocked
        if parser.has_option(section, 'blocked'):
            config.blocked = _parse_list(parser.get(section, 'blocked'))

        # only
        if parser.has_option(section, 'only'):
            config.only = _parse_list(parser.get(section, 'only'))

    return config


def _load_playback_config(parser: configparser.ConfigParser) -> PlaybackConfig:
    """加载播放配置"""
    section = 'playback'
    if not parser.has_section(section):
        logger.warning(f"配置文件缺少 [{section}] 节，使用默认配置")
        return DEFAULT_CONFIG.playback

    config = DEFAULT_CONFIG.playback

    # max_queue_size
    if parser.has_option(section, 'max_queue_size'):
        try:
            config.max_queue_size = parser.getint(section, 'max_queue_size')
        except ValueError:
            logger.warning(f"max_queue_size 配置值无效，使用默认值: {config.max_queue_size}")

    # play_interval
    if parser.has_option(section, 'play_interval'):
        try:
            config.play_interval = parser.getfloat(section, 'play_interval')
        except ValueError:
            logger.warning(f"play_interval 配置值无效，使用默认值: {config.play_interval}")

    # volume
    if parser.has_option(section, 'volume'):
        try:
            config.volume = parser.getfloat(section, 'volume')
            # 验证范围
            if not 0.0 <= config.volume <= 1.0:
                logger.warning(f"volume 超出范围 [0.0-1.0]，使用默认值: {DEFAULT_CONFIG.playback.volume}")
                config.volume = DEFAULT_CONFIG.playback.volume
        except ValueError:
            logger.warning(f"volume 配置值无效，使用默认值: {config.volume}")

    return config


def _load_log_config(parser: configparser.ConfigParser) -> LogConfig:
    """加载日志配置"""
    section = 'log'
    if not parser.has_section(section):
        logger.warning(f"配置文件缺少 [{section}] 节，使用默认配置")
        return DEFAULT_CONFIG.log

    config = DEFAULT_CONFIG.log

    # level
    if parser.has_option(section, 'level'):
        config.level = parser.get(section, 'level').upper()

    # enable_console
    if parser.has_option(section, 'enable_console'):
        try:
            config.enable_console = _parse_bool(parser.get(section, 'enable_console'))
        except ValueError:
            logger.warning(f"enable_console 配置值无效，使用默认值: {config.enable_console}")

    # enable_file
    if parser.has_option(section, 'enable_file'):
        try:
            config.enable_file = _parse_bool(parser.get(section, 'enable_file'))
        except ValueError:
            logger.warning(f"enable_file 配置值无效，使用默认值: {config.enable_file}")

    # file_path
    if parser.has_option(section, 'file_path'):
        config.file_path = parser.get(section, 'file_path')

    return config


def _load_gui_config(parser: configparser.ConfigParser) -> GUIConfig:
    """加载GUI配置"""
    section = 'gui'
    if not parser.has_section(section):
        logger.debug(f"配置文件缺少 [{section}] 节，使用默认配置")
        return DEFAULT_CONFIG.gui

    config = DEFAULT_CONFIG.gui

    # last_room_id
    if parser.has_option(section, 'last_room_id'):
        config.last_room_id = parser.get(section, 'last_room_id')

    # remember_room
    if parser.has_option(section, 'remember_room'):
        try:
            config.remember_room = _parse_bool(parser.get(section, 'remember_room'))
        except ValueError:
            logger.warning(f"remember_room 配置值无效，使用默认值: {config.remember_room}")

    # window_width
    if parser.has_option(section, 'window_width'):
        try:
            config.window_width = parser.getint(section, 'window_width')
        except ValueError:
            logger.warning(f"window_width 配置值无效，使用默认值: {config.window_width}")

    # window_height
    if parser.has_option(section, 'window_height'):
        try:
            config.window_height = parser.getint(section, 'window_height')
        except ValueError:
            logger.warning(f"window_height 配置值无效，使用默认值: {config.window_height}")

    # auto_start_chrome
    if parser.has_option(section, 'auto_start_chrome'):
        try:
            config.auto_start_chrome = _parse_bool(parser.get(section, 'auto_start_chrome'))
        except ValueError:
            logger.warning(f"auto_start_chrome 配置值无效，使用默认值: {config.auto_start_chrome}")

    return config


def load_config(path: str = "config.ini") -> AppConfig:
    """
    加载配置文件

    Args:
        path: 配置文件路径（默认: config.ini）

    Returns:
        AppConfig: 配置对象（如果文件不存在或解析失败，返回默认配置）
    """
    config_path = Path(path)

    # 1. 检查文件是否存在
    if not config_path.exists():
        logger.warning(f"配置文件不存在: {config_path}")
        logger.info("使用默认配置")
        return DEFAULT_CONFIG

    # 2. 解析配置文件（禁用插值以支持%符号）
    parser = configparser.ConfigParser(interpolation=None)
    try:
        # 使用utf-8编码读取文件
        read_files = parser.read(config_path, encoding='utf-8')
        if not read_files:
            logger.error(f"无法读取配置文件: {config_path}")
            logger.info("使用默认配置")
            return DEFAULT_CONFIG
    except Exception as e:
        logger.error(f"配置文件解析失败: {e}")
        logger.info("使用默认配置")
        return DEFAULT_CONFIG

    # 3. 加载各个配置节
    try:
        room_config = _load_room_config(parser)
        tts_config = _load_tts_config(parser)
        filter_config = _load_filter_config(parser)
        playback_config = _load_playback_config(parser)
        log_config = _load_log_config(parser)
        gui_config = _load_gui_config(parser)

        config = AppConfig(
            room=room_config,
            tts=tts_config,
            filter=filter_config,
            playback=playback_config,
            log=log_config,
            gui=gui_config
        )

        logger.info(f"配置加载成功: {config_path}")
        return config

    except Exception as e:
        logger.error(f"配置转换失败: {e}")
        logger.info("使用默认配置")
        return DEFAULT_CONFIG


def validate_config(config: AppConfig) -> bool:
    """
    验证配置是否有效

    Args:
        config: 配置对象

    Returns:
        bool: 配置是否有效
    """
    # 验证必填项
    if not config.room.room_id:
        logger.error("room_id 不能为空，请在config.ini中设置或通过命令行参数指定")
        return False

    # 验证数值范围
    if config.filter.min_length < 0 or config.filter.min_length > config.filter.max_length:
        logger.error("min_length 不能大于 max_length")
        return False

    if config.playback.volume < 0.0 or config.playback.volume > 1.0:
        logger.error("volume 必须在 0.0-1.0 之间")
        return False

    return True
