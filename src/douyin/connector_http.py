"""
HTTP轮询连接器 - 使用Playwright监听浏览器HTTP请求

通过监听浏览器的 /webcast/im/fetch/ 响应来获取弹幕
自动处理签名参数（a_bogus等）
"""

import asyncio
import logging
from typing import Callable, Optional
from .parser_http import HTTPResponseParser, ParsedMessage

logger = logging.getLogger(__name__)


class DouyinHTTPConnector:
    """
    HTTP轮询连接器

    使用Playwright监听浏览器发送的HTTP请求
    """

    def __init__(self, room_id: str, ttwid: str, poll_interval: float = 1.0):
        """
        初始化连接器

        Args:
            room_id: 直播间ID（用户输入的，如 118636942397）
            ttwid: 抖音cookie
            poll_interval: 轮询间隔（秒）
        """
        self.room_id = room_id
        self.ttwid = ttwid
        self.poll_interval = poll_interval
        self.is_running = False

        # Playwright对象
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        # HTTP响应解析器
        self.parser = HTTPResponseParser()

        # 消息队列
        self.message_queue = asyncio.Queue()

    async def connect(self) -> bool:
        """建立连接 - 启动浏览器并访问直播间"""
        logger.info("="*60)
        logger.info("HTTP轮询连接器启动")
        logger.info("="*60)

        try:
            from playwright.async_api import async_playwright

            # 启动Playwright
            self.playwright = await async_playwright().start()

            # 连接Chrome
            logger.info("连接Chrome...")
            self.browser = await self.playwright.chromium.connect_over_cdp("http://localhost:9222")

            # 创建context
            self.context = await self.browser.new_context()

            # 设置cookie
            await self.context.add_cookies([{
                'name': 'ttwid',
                'value': self.ttwid,
                'domain': '.douyin.com',
                'path': '/'
            }])

            # 创建页面
            self.page = await self.context.new_page()

            # 设置响应监听
            self.page.on("response", self._handle_response)

            # 访问直播间
            url = f"https://live.douyin.com/{self.room_id}"
            logger.info(f"访问直播间: {url}")
            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # 等待页面加载
            await asyncio.sleep(3)

            logger.info("="*60)
            logger.info("连接器启动成功")
            logger.info("="*60)

            self.is_running = True
            return True

        except Exception as e:
            logger.error(f"连接失败: {e}")
            await self.disconnect()
            return False

    async def _handle_response(self, response):
        """处理HTTP响应"""
        try:
            url = response.url

            # 只关心im/fetch响应
            if 'webcast/im/fetch' not in url:
                return

            # 只处理成功的响应
            if response.status != 200:
                return

            # 读取响应数据
            data = await response.body()

            # 如果有数据，解析并放入队列
            if len(data) > 0:
                messages = self.parser.parse_response(data)
                for msg in messages:
                    await self.message_queue.put(msg)

                if messages:
                    chat_count = sum(1 for m in messages if m.method == "WebChatMessage")
                    logger.debug(f"获取到 {len(messages)} 条消息，其中 {chat_count} 条聊天")

        except Exception as e:
            logger.debug(f"处理响应失败: {e}")

    async def listen(self, message_handler: Callable):
        """监听消息"""
        logger.info("开始监听弹幕...")
        logger.info("按 Ctrl+C 退出")

        try:
            while self.is_running:
                try:
                    # 从队列获取消息（带超时）
                    msg = await asyncio.wait_for(
                        self.message_queue.get(),
                        timeout=1.0
                    )

                    # 调用消息处理器
                    if asyncio.iscoroutinefunction(message_handler):
                        await message_handler(msg)
                    else:
                        message_handler(msg)

                except asyncio.TimeoutError:
                    # 超时继续循环
                    continue

        except KeyboardInterrupt:
            logger.info("用户中断")
        except Exception as e:
            logger.error(f"监听异常: {e}")

    async def disconnect(self):
        """断开连接"""
        logger.info("正在断开连接...")

        self.is_running = False

        # 关闭页面
        if self.page:
            try:
                await self.page.close()
            except:
                pass

        # 关闭context
        if self.context:
            try:
                await self.context.close()
            except:
                pass

        # 关闭浏览器
        if self.browser:
            try:
                await self.browser.close()
            except:
                pass

        # 停止Playwright
        if self.playwright:
            try:
                await self.playwright.stop()
            except:
                pass

        logger.info("已断开连接")
