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

            # 启动轮询任务
            self.poll_task = asyncio.create_task(self._poll_messages())

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
                    logger.info(f"[轮询] 获取到 {len(messages)} 条消息，其中 {chat_count} 条聊天")

        except Exception as e:
            logger.debug(f"处理响应失败: {e}")

    async def _poll_messages(self):
        """主动轮询获取新弹幕"""
        logger.info("启动弹幕轮询任务...")

        consecutive_errors = 0
        max_consecutive_errors = 5

        while self.is_running:
            try:
                # 检查浏览器是否还连接
                if self.page and self.browser:
                    try:
                        is_closed = await self.page.is_closed()
                        if is_closed:
                            logger.error("="*60)
                            logger.error("❌ 浏览器页面已关闭！")
                            logger.error("="*60)
                            logger.error("请重新启动Chrome调试模式：")
                            logger.error("  .\\start_chrome_debug.bat")
                            logger.error("="*60)
                            break
                    except:
                        pass

                # 使用JavaScript在浏览器中发送fetch请求
                # 这样可以自动处理所有签名参数
                result = await self.page.evaluate('''async () => {
                    try {
                        // 从页面中获取内部room_id
                        const getInternalRoomId = () => {
                            if (window.__pace_f) {
                                for (let i = 0; i < window.__pace_f.length; i++) {
                                    if (window.__pace_f[i]) {
                                        const items = Array.isArray(window.__pace_f[i]) ? window.__pace_f[i] : [window.__pace_f[i]];
                                        for (const item of items) {
                                            if (typeof item === 'string') {
                                                const match = item.match(/"roomId":"(\\d+)"/);
                                                if (match) return match[1];
                                            }
                                        }
                                    }
                                }
                            }
                            return null;
                        };

                        const roomId = getInternalRoomId();
                        if (!roomId) return null;

                        // 构建请求URL（使用页面已有的参数）
                        const url = `/webcast/im/fetch/?room_id=${roomId}&need_persist_msg_count=15&fetch_rule=1`;

                        // 发送fetch请求
                        const response = await fetch(url, {
                            method: 'GET',
                            credentials: 'include'
                        });

                        if (!response.ok) return null;

                        const arrayBuffer = await response.arrayBuffer();
                        // 转换为base64以便传递
                        const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));

                        return {
                            success: true,
                            data: base64,
                            length: arrayBuffer.byteLength
                        };
                    } catch (e) {
                        return {
                            success: false,
                            error: e.toString()
                        };
                    }
                }''')

                if result and result.get('success'):
                    import base64
                    # 解析base64数据
                    data = base64.b64decode(result['data'])

                    # 如果有数据，解析并放入队列
                    if len(data) > 0:
                        messages = self.parser.parse_response(data)
                        for msg in messages:
                            await self.message_queue.put(msg)

                        if messages:
                            chat_count = sum(1 for m in messages if m.method == "WebChatMessage")
                            logger.info(f"[轮询] 获取到 {len(messages)} 条消息，其中 {chat_count} 条聊天")
                            consecutive_errors = 0  # 重置错误计数

                # 等待下次轮询
                await asyncio.sleep(self.poll_interval)

            except Exception as e:
                consecutive_errors += 1
                logger.error(f"轮询失败 ({consecutive_errors}/{max_consecutive_errors}): {e}")

                if consecutive_errors >= max_consecutive_errors:
                    logger.error("="*60)
                    logger.error("❌ 连续错误过多，停止轮询")
                    logger.error("="*60)
                    break

                await asyncio.sleep(self.poll_interval)

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

        # 停止轮询任务
        if hasattr(self, 'poll_task'):
            self.poll_task.cancel()
            try:
                await self.poll_task
            except asyncio.CancelledError:
                pass

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
