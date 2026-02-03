"""
改进的WebSocket连接器 - 直接使用浏览器捕获的URL

解决HTTP 200错误的方法：不自己构造URL，而是直接使用从浏览器捕获的WebSocket URL
"""

import asyncio
import logging
from typing import Callable, Optional
from playwright.async_api import async_playwright
import websockets

logger = logging.getLogger(__name__)


class DouyinConnectorV3:
    """
    改进的抖音直播间连接器

    关键改进：直接使用从浏览器捕获的WebSocket URL，而不是自己构造
    """

    def __init__(self, room_id: str, ttwid: str):
        self.room_id = room_id
        self.ttwid = ttwid
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False

        # Playwright实例
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        # 捕获的WebSocket URL
        self.captured_ws_url = None

    async def connect(self) -> bool:
        """
        建立WebSocket连接

        策略：
        1. 启动浏览器并访问直播间
        2. 监听WebSocket连接，捕获真实的URL
        3. 关闭浏览器的WebSocket（释放端口）
        4. 用Python重新连接到相同的URL

        Returns:
            bool: 连接是否成功
        """
        logger.info("="*60)
        logger.info("启动V3连接器（使用捕获的URL）")
        logger.info("="*60)

        try:
            # 步骤1: 捕获WebSocket URL
            logger.info("步骤1: 捕获WebSocket URL...")
            if not await self._capture_websocket_url():
                logger.error("捕获WebSocket URL失败")
                return False

            logger.info(f"[OK] 捕获到WebSocket URL")
            logger.debug(f"  URL长度: {len(self.captured_ws_url)} 字符")

            # 步骤2: 使用捕获的URL建立连接
            logger.info("步骤2: 使用捕获的URL建立WebSocket连接...")
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

    async def _capture_websocket_url(self) -> bool:
        """
        捕获浏览器中的WebSocket URL

        Returns:
            bool: 是否成功捕获
        """
        try:
            # 创建playwright实例
            self.playwright = async_playwright()
            p = await self.playwright.__aenter__()

            # 连接到Chrome
            try:
                self.browser = await p.chromium.connect_over_cdp("http://localhost:9222")
                logger.info("  [OK] 已连接到Chrome")
            except Exception as e:
                logger.error(f"  [FAIL] 无法连接到Chrome: {e}")
                logger.info("  请启动Chrome调试模式:")
                logger.info("  chrome.exe --remote-debugging-port=9222")
                return False

            # 创建context
            self.context = await self.browser.new_context()

            # 设置cookie
            await self.context.add_cookies([{
                'name': 'ttwid',
                'value': self.ttwid,
                'domain': '.douyin.com',
                'path': '/'
            }])
            logger.info("  [OK] 已设置cookie")

            # 创建页面
            self.page = await self.context.new_page()

            # 监听WebSocket
            ws_url_holder = []
            ws_connections = []

            def on_websocket(ws):
                url = ws.url
                logger.info(f"  [发现] WebSocket连接: {url[:80]}...")

                # 只关心webcast的WebSocket
                if 'webcast' in url and 'douyin.com' in url:
                    ws_url_holder.append(url)
                    ws_connections.append(ws)
                    logger.info(f"  [捕获] 找到目标WebSocket!")

            self.page.on("websocket", on_websocket)

            # 访问直播间
            url = f"https://live.douyin.com/{self.room_id}"
            logger.info(f"  访问直播间: {url}")

            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            logger.info("  [OK] 页面加载完成")

            # 等待WebSocket连接
            logger.info("  等待WebSocket连接...")
            for i in range(30):  # 等待最多30秒
                await asyncio.sleep(1)
                if ws_url_holder:
                    self.captured_ws_url = ws_url_holder[0]
                    logger.info(f"  [OK] 捕获到WebSocket URL")
                    logger.debug(f"  等待2秒让连接稳定...")
                    await asyncio.sleep(2)
                    break
            else:
                logger.warning("  [WARN] 30秒内未捕获到WebSocket")
                return False

            # 不要关闭浏览器，保持WebSocket连接活跃
            # 我们将使用这个URL建立独立的Python WebSocket连接

            return True

        except Exception as e:
            logger.error(f"  [ERROR] 捕获WebSocket URL失败: {e}")
            return False

    async def _connect_websocket(self) -> bool:
        """
        使用捕获的URL建立Python WebSocket连接

        Returns:
            bool: 连接是否成功
        """
        if not self.captured_ws_url:
            logger.error("  没有捕获到WebSocket URL")
            return False

        headers = {
            "Cookie": f"ttwid={self.ttwid}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://live.douyin.com",
            "Referer": f"https://live.douyin.com/{self.room_id}",
        }

        logger.info(f"  连接到: {self.captured_ws_url[:80]}...")

        try:
            self.ws = await websockets.connect(
                self.captured_ws_url,
                additional_headers=headers,
                ping_interval=None,
                close_timeout=10,
            )

            logger.info(f"  [OK] WebSocket连接成功")
            return True

        except Exception as e:
            logger.error(f"  [FAIL] WebSocket连接失败: {e}")
            logger.debug(f"  URL: {self.captured_ws_url[:200]}")
            return False

    async def listen(self, message_handler: Callable):
        """
        监听消息

        Args:
            message_handler: 消息处理函数
        """
        logger.info("开始监听消息...")
        logger.info("按 Ctrl+C 退出")

        try:
            async for raw_message in self.ws:
                try:
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

        # 关闭页面和context
        if self.page:
            try:
                await self.page.close()
            except:
                pass

        if self.context:
            try:
                await self.context.close()
            except:
                pass

        # 关闭浏览器和playwright
        if self.browser:
            try:
                await self.browser.close()
            except:
                pass

        if self.playwright:
            try:
                await self.playwright.__aexit__(None, None, None)
            except:
                pass

        self.is_connected = False
        logger.info("已断开连接")
