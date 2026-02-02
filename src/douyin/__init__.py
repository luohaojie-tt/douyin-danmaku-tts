"""
抖音直播间连接模块

包含Cookie管理、WebSocket连接和消息解析功能。
"""

from src.douyin.cookie import CookieManager, default_cookie_manager

__all__ = [
    'CookieManager',
    'default_cookie_manager',
]
