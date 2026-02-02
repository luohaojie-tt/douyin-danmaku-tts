"""
抖音直播间WebSocket连接器 - Playwright集成版

集成Playwright浏览器自动化，获取真实签名并建立WebSocket连接
"""

import asyncio
import gzip
import json
import logging
import subprocess
from typing import Callable, Optional
from pathlib import Path

from playwright.async_api import async_playwright
import websockets

logger = logging.getLogger(__name__)


class DouyinConnectorReal:
    """
    抖音直播间真实连接器

    使用Playwright获取签名，建立真实的WebSocket连接
    """

    # WebSocket服务器列表
    WS_SERVERS = [
        "wss://webcast5-ws-web-lf.douyin.com",
        "wss://webcast5-ws-web-hl.douyin.com",
        "wss://webcast3-ws-web-lf.douyin.com",
    ]

    def __init__(self, room_id: str, ttwid: str):
        """
        初始化连接器

        Args:
            room_id: 直播间房间ID
            ttwid: 抖音ttwid cookie
        """
        self.room_id = room_id
        self.ttwid = ttwid
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False

        # Playwright浏览器实例
        self.browser = None
        self.context = None
        self.page = None

        # 签名
        self.signature = None

        # 完整的WebSocket URL（从浏览器捕获）
        self.captured_ws_url = None

    async def connect(self) -> bool:
        """
        建立WebSocket连接

        1. 使用Playwright获取签名
        2. 建立WebSocket连接
        3. 返回连接结果

        Returns:
            bool: 连接是否成功
        """
        logger.info("="*60)
        logger.info("启动真实连接器")
        logger.info("="*60)

        try:
            # 步骤1: 获取签名
            logger.info("步骤1: 获取X-Bogus签名...")
            if not await self._get_signature():
                logger.error("获取签名失败")
                return False

            logger.info(f"[OK] 签名获取成功: {self.signature[:20]}...")

            # 步骤2: 建立WebSocket连接
            logger.info("步骤2: 建立WebSocket连接...")
            if not await self._connect_websocket():
                logger.error("WebSocket连接失败")
                return False

            logger.info("[OK] WebSocket连接成功")
            self.is_connected = True

            logger.info("="*60)
            logger.info("连接器启动成功")
            logger.info("="*60)
            return True

        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False

    async def _get_signature(self) -> bool:
        """
        使用Playwright获取X-Bogus签名并捕获WebSocket URL

        Returns:
            bool: 是否成功获取签名和WebSocket URL
        """
        try:
            async with async_playwright() as p:
                # 连接到Chrome
                try:
                    self.browser = await p.chromium.connect_over_cdp("http://localhost:9222")
                    logger.info("  [OK] 已连接到Chrome")
                except Exception as e:
                    logger.error(f"  [FAIL] 无法连接到Chrome: {e}")
                    logger.info("  提示: 请启动Chrome调试模式:")
                    logger.info("  chrome.exe --remote-debugging-port=9222")
                    return False

                # 创建新的context（避免其他标签页干扰）
                self.context = await self.browser.new_context()
                logger.info("  [OK] 创建新context")

                # 设置cookie
                await self.context.add_cookies([{
                    'name': 'ttwid',
                    'value': self.ttwid,
                    'domain': '.douyin.com',
                    'path': '/'
                }])
                logger.info("  [OK] 已设置cookie")

                # 创建页面并监听WebSocket
                self.page = await self.context.new_page()

                # 监听WebSocket连接以捕获URL
                ws_url_holder = []

                def on_websocket(ws):
                    url = ws.url
                    if 'webcast' in url and 'douyin.com' in url:
                        logger.info(f"  [捕获] 发现WebSocket连接")
                        ws_url_holder.append(url)
                        logger.debug(f"  WebSocket URL长度: {len(url)} 字符")

                self.page.on("websocket", on_websocket)

                # 访问直播间
                url = f"https://live.douyin.com/{self.room_id}"
                logger.info(f"  访问直播间: {url}")

                await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
                logger.info("  [OK] 页面加载完成")

                # 等待WebSocket连接建立
                logger.info("  等待WebSocket连接...")
                for i in range(30):  # 等待最多30秒
                    await asyncio.sleep(1)
                    if ws_url_holder:
                        self.captured_ws_url = ws_url_holder[0]
                        logger.info(f"  [OK] 捕获到WebSocket URL")
                        logger.debug(f"  等待2秒让浏览器连接稳定...")
                        await asyncio.sleep(2)  # 等待浏览器连接稳定
                        break
                else:
                    logger.warning("  [WARN] 未捕获到WebSocket连接，尝试手动获取签名")

                # 调用frontierSign获取签名（作为备用）
                signature_data = await self.page.evaluate('''() => {
                    if (window.byted_acrawler && window.byted_acrawler.frontierSign) {
                        const result = window.byted_acrawler.frontierSign({
                            room_id: window.location.pathname.slice(1)
                        });
                        return {
                            'X-Bogus': result['X-Bogus'] || result.X-Bogus || ''
                        };
                    }
                    return null;
                }''')

                if not signature_data or not signature_data.get('X-Bogus'):
                    logger.error("  [FAIL] 无法获取X-Bogus签名")
                    return False

                self.signature = signature_data['X-Bogus']
                logger.info(f"  [OK] X-Bogus签名: {self.signature}")

                # 如果捕获到了WebSocket URL，从中提取更多参数
                if self.captured_ws_url:
                    logger.info(f"  [OK] 将使用捕获的WebSocket URL连接")
                else:
                    logger.warning("  [WARN] 将使用构造的WebSocket URL")

                return True

        except Exception as e:
            logger.error(f"  [ERROR] 获取签名失败: {e}")
            return False

    async def _connect_websocket(self) -> bool:
        """
        建立WebSocket连接

        优先使用从浏览器捕获的WebSocket URL，如果没有则使用构造的URL

        Returns:
            bool: 连接是否成功
        """
        headers = {
            "Cookie": f"ttwid={self.ttwid}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://live.douyin.com",
            "Referer": f"https://live.douyin.com/{self.room_id}",
        }

        # 优先使用捕获的URL
        if self.captured_ws_url:
            try:
                logger.info(f"  使用捕获的WebSocket URL连接")
                logger.debug(f"  URL: {self.captured_ws_url[:100]}...")

                self.ws = await websockets.connect(
                    self.captured_ws_url,
                    additional_headers=headers,
                    ping_interval=None,
                    close_timeout=10,
                )

                logger.info(f"  [OK] WebSocket连接成功（使用捕获的URL）")
                return True

            except Exception as e:
                logger.warning(f"  [WARN] 使用捕获URL连接失败: {e}")
                logger.info(f"  尝试使用构造的URL...")

        # 构造WebSocket URL（备用方案）
        import urllib.parse
        from urllib.parse import urlencode

        # 生成用户唯一ID
        import time
        user_unique_id = f"{int(time.time() * 1000)}"

        params = {
            'app_name': 'douyin_web',
            'version_code': '180800',
            'webcast_sdk_version': '1.0.15',
            'update_version_code': '1.0.15',
            'compress': 'gzip',
            'device_platform': 'web',
            'cookie_enabled': 'true',
            'screen_width': '1920',
            'screen_height': '1080',
            'browser_language': 'zh-CN',
            'browser_platform': 'Win32',
            'browser_name': 'Mozilla',
            'browser_online': 'true',
            'tz_name': 'Asia/Shanghai',
            'cursor': '0-0',
            'user_unique_id': user_unique_id,
            'live_id': '1',
            'aid': '6383',
            'did_rule': '3',
            'endpoint': 'live_pc',
            'identity': 'audience',
            'room_id': self.room_id,
            'signature': self.signature,
        }

        # 尝试多个服务器
        for server in self.WS_SERVERS:
            try:
                ws_url = f"{server}/webcast/im/push/v2/?{urlencode(params)}"
                logger.info(f"  尝试连接: {server}")
                logger.debug(f"  URL参数: {len(params)} 个")

                self.ws = await websockets.connect(
                    ws_url,
                    additional_headers=headers,
                    ping_interval=None,
                    close_timeout=10,
                )

                logger.info(f"  [OK] WebSocket连接成功")
                return True

            except Exception as e:
                logger.warning(f"  [WARN] 连接{server}失败: {e}")
                continue

        logger.error("  [FAIL] 所有服务器连接失败")
        return False

    async def listen(self, message_handler: Callable):
        """
        监听消息

        Args:
            message_handler: 消息处理函数，接收原始消息数据
        """
        logger.info("开始监听消息...")
        logger.info("按 Ctrl+C 退出")

        try:
            async for raw_message in self.ws:
                try:
                    # 处理消息
                    if asyncio.iscoroutinefunction(message_handler):
                        await message_handler(raw_message)
                    else:
                        message_handler(raw_message)
                except Exception as e:
                    logger.error(f"处理消息失败: {e}")

        except KeyboardInterrupt:
            logger.info("用户中断")
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket连接已关闭")
        except Exception as e:
            logger.error(f"监听异常: {e}")

    async def disconnect(self):
        """断开连接"""
        logger.info("正在断开连接...")

        # 关闭WebSocket
        if self.ws:
            try:
                await self.ws.close()
            except:
                pass

        # 关闭浏览器
        if self.browser:
            try:
                await self.browser.close()
            except:
                pass

        self.is_connected = False
        logger.info("已断开连接")
