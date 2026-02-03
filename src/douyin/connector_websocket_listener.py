"""
WebSocket监听连接器 - 直接监听浏览器WebSocket消息

这是最可靠的方法：浏览器会自动接收弹幕WebSocket消息
我们只需要监听这些消息即可
"""

import asyncio
import logging
import json
from typing import Callable, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UserInfo:
    """用户信息"""
    id: str
    nickname: str


@dataclass
class ParsedMessage:
    """解析后的消息"""
    method: str
    user: Optional[UserInfo] = None
    content: Optional[str] = None


class WebSocketListenerConnector:
    """
    WebSocket监听连接器

    直接监听浏览器接收到的WebSocket消息
    """

    def __init__(self, room_id: str, ttwid: str):
        self.room_id = room_id
        self.ttwid = ttwid
        self.is_running = False

        # Playwright对象
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        # WebSocket连接
        self.ws = None

        # 消息队列
        self.message_queue = asyncio.Queue()

        # 消息统计
        self.stats = {
            "received": 0,
            "chat_messages": 0
        }

    async def connect(self) -> bool:
        """建立连接"""
        logger.info("="*60)
        logger.info("WebSocket监听连接器启动")
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

            # ========== 关键：注入WebSocket监听代码 ==========
            await self.page.add_init_script("""
            window.douyinMessages = [];
            window.wsMessageCount = 0;

            // 保存原始WebSocket
            const OriginalWebSocket = window.WebSocket;

            // 重写WebSocket
            window.WebSocket = function(...args) {
                const ws = new OriginalWebSocket(...args);

                console.log('[WebSocket] 创建新连接:', args[0]);

                ws.addEventListener('message', (event) => {
                    const data = event.data;
                    window.wsMessageCount++;

                    // 每100条消息打印一次统计
                    if (window.wsMessageCount % 100 === 0) {
                        console.log('[WebSocket] 已接收', window.wsMessageCount, '条消息');
                    }

                    // 检查是否是二进制消息
                    if (data instanceof ArrayBuffer || data instanceof Buffer) {
                        try {
                            // 转换为Uint8Array
                            const bytes = new Uint8Array(data);

                            // 尝试解码为文本
                            const decoder = new TextDecoder('utf-8', {fatal: false});
                            const text = decoder.decode(bytes);

                            // 检查是否包含聊天消息
                            if (text.includes('WebcastChatMessage') ||
                                text.includes('chatmessage') ||
                                text.includes('content')) {

                                // 提取弹幕内容（使用更宽松的模式）
                                const contentMatch = text.match(/content[^a-zA-Z0-9]{0,}([\u4e00-\u9fff\u0020-\u007e]{2,})/);
                                const nicknameMatch = text.match(/nickname[^a-zA-Z0-9]{0,}([\u4e00-\u9fff]{2,})/);

                                if (contentMatch && contentMatch[1]) {
                                    const content = contentMatch[1];
                                    const nickname = nicknameMatch && nicknameMatch[1] ? nicknameMatch[1] : '用户';

                                    window.douyinMessages.push({
                                        content: content,
                                        nickname: nickname,
                                        raw: text.substring(0, 200) // 保存前200字符用于调试
                                    });

                                    console.log('[弹幕]', nickname, ':', content);
                                }
                            }
                        } catch (e) {
                            console.error('[解析失败]', e);
                        }
                    }
                });

                return ws;
            };
            """)

            # 访问直播间
            url = f"https://live.douyin.com/{self.room_id}"
            logger.info(f"访问直播间: {url}")
            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # 等待页面加载
            await asyncio.sleep(5)

            # 启动消息提取任务
            asyncio.create_task(self._extract_messages())

            logger.info("="*60)
            logger.info("连接器启动成功")
            logger.info("="*60)

            self.is_running = True
            return True

        except Exception as e:
            logger.error(f"连接失败: {e}")
            await self.disconnect()
            return False

    async def _extract_messages(self):
        """定期从页面提取消息"""
        consecutive_empty = 0
        while self.is_running:
            try:
                # 从页面提取收集到的消息
                messages = await self.page.evaluate('''() => {
                    if (!window.douyinMessages) return [];

                    const msgs = window.douyinMessages;
                    window.douyinMessages = [];  // 清空

                    return msgs;
                }''')

                if messages:
                    consecutive_empty = 0
                    logger.debug(f"[调试] 从页面提取到 {len(messages)} 条原始消息")

                    for msg in messages:
                        self.stats["received"] += 1

                        content = msg.get('content', '').strip()
                        nickname = msg.get('nickname', '用户')
                        raw = msg.get('raw', '')

                        logger.debug(f"[调试] 消息内容: {content}, 昵称: {nickname}")

                        # 过滤系统消息
                        if self._is_valid_danmaku(content):
                            self.stats["chat_messages"] += 1

                            user_info = UserInfo(
                                id="unknown",
                                nickname=nickname[:20]
                            )

                            parsed = ParsedMessage(
                                method="WebChatMessage",
                                user=user_info,
                                content=content
                            )

                            await self.message_queue.put(parsed)
                            logger.info(f"[收到] {nickname}: {content}")
                        else:
                            logger.debug(f"[过滤] 跳过非弹幕内容: {content}")
                else:
                    consecutive_empty += 1
                    if consecutive_empty % 10 == 0:  # 每10秒打印一次
                        logger.debug(f"[调试] 暂无消息，已等待 {consecutive_empty} 秒")

            except Exception as e:
                logger.debug(f"提取消息失败: {e}")

            await asyncio.sleep(1)  # 每秒检查一次

    def _is_valid_danmaku(self, text: str) -> bool:
        """检查是否是有效弹幕"""
        if not text or len(text) < 2:
            return False

        # 过滤系统消息
        invalid_patterns = [
            r'^在线观众',
            r'^正在观看',
            r'^人数',
            r'^点赞',
            r'^关注',
            r'^粉丝',
            r'^主播',
            r'^直播',
            r'^房间',
            r'^榜',
            r'^贡献',
            r'^热度',
            r'^礼物',
            r'^感谢',
            r'^欢迎',
            r'^进入',
        ]

        import re
        for pattern in invalid_patterns:
            if re.match(pattern, text):
                return False

        # 必须是中文内容
        chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        return chinese_count > 0

    async def listen(self, message_handler: Callable):
        """监听消息"""
        logger.info("开始监听WebSocket消息...")
        logger.info("按 Ctrl+C 退出")

        try:
            while self.is_running:
                try:
                    msg = await asyncio.wait_for(
                        self.message_queue.get(),
                        timeout=2.0
                    )

                    if asyncio.iscoroutinefunction(message_handler):
                        await message_handler(msg)
                    else:
                        message_handler(msg)

                except asyncio.TimeoutError:
                    continue

        except KeyboardInterrupt:
            logger.info("用户中断")
        except Exception as e:
            logger.error(f"监听异常: {e}")

    async def disconnect(self):
        """断开连接"""
        logger.info("正在断开连接...")

        self.is_running = False

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

        if self.browser:
            try:
                await self.browser.close()
            except:
                pass

        if self.playwright:
            try:
                await self.playwright.stop()
            except:
                pass

        logger.info("已断开连接")
