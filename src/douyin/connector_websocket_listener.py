"""
WebSocket监听连接器 - 直接监听浏览器WebSocket消息

这是最可靠的方法：浏览器会自动接收弹幕WebSocket消息
我们只需要监听这些消息即可
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Optional

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

            # 获取所有已存在的context
            contexts = self.browser.contexts
            logger.info(f"发现 {len(contexts)} 个浏览器上下文")

            # 关键：必须创建新的context，不能使用已存在的！
            # 已存在的context中WebSocket可能已经建立，无法被我们的代码拦截
            logger.info("创建新的浏览器上下文（用于注入WebSocket监听）")
            self.context = await self.browser.new_context()

            # 设置cookie
            await self.context.add_cookies([{
                'name': 'ttwid',
                'value': self.ttwid,
                'domain': '.douyin.com',
                'path': '/'
            }])

            # ========== 新方法：使用DOM监听获取弹幕（最可靠） ==========

            # 存储消息的列表
            self.cdp_messages = []
            self.dom_message_count = 0

            # 创建新页面
            logger.info("创建新页面")
            self.page = await self.context.new_page()

            # 注入DOM监听脚本
            logger.info("注入DOM弹幕监听脚本")
            await self.context.add_init_script("""
            window.douyinMessages = [];
            window.domMessageCount = 0;
            window.lastScanTime = Date.now();
            window.chatContainer = null;

            // 辅助函数：寻找弹幕容器
            function findChatContainer() {
                if (window.chatContainer && window.chatContainer.isConnected) {
                    return window.chatContainer;
                }

                // 策略1：根据已知类名查找（最准确）
                // 抖音直播网页版通常包含 'webcast-chatroom___list' 或 'webcast-chatroom___items'
                const potentialClasses = [
                    'webcast-chatroom___list',
                    'webcast-chatroom___items',
                    'Barrage-list',
                    'chat-scroll-area'
                ];

                for (const cls of potentialClasses) {
                    const el = document.querySelector(`div[class*="${cls}"], ul[class*="${cls}"]`);
                    if (el) {
                        console.log(`[DOM监听] 找到弹幕容器，类名: ${el.className}`);
                        window.chatContainer = el;
                        return el;
                    }
                }

                // 策略2：查找包含大量 "div" 子元素的容器（启发式）
                // 仅在策略1失效时使用，避免误判
                return null;
            }

            // 处理单个弹幕节点
            function processNode(node) {
                if (!node) return;
                
                // 使用 innerText 获取可见文本，格式通常为 "昵称：内容"
                const rawText = node.innerText || node.textContent || '';
                const textKey = rawText.trim();

                if (!textKey) return;

                // 检查是否已处理
                if (node.__douyin_processed) return;
                node.__douyin_processed = true;
                
                // --- 步骤1: 尝试分离昵称和内容 ---
                let nickname = '';
                let content = textKey;
                
                // 尝试寻找分隔符 (中文冒号或英文冒号)
                // 注意：有些弹幕结构是 <span>昵称</span><span>内容</span>，innerText 会自动拼接
                let colonIndex = textKey.indexOf('：');
                if (colonIndex === -1) {
                    colonIndex = textKey.indexOf(': ');
                }

                if (colonIndex > 0 && colonIndex < 30) { // 假设昵称不会超过30字符
                    nickname = textKey.substring(0, colonIndex).trim();
                    content = textKey.substring(colonIndex + 1).trim();
                }

                // --- 步骤2: 严格过滤非弹幕内容 (基于内容部分) ---
                // 这些是系统生成的动态消息，混合在弹幕列表中
                const systemKeywords = [
                    '为主播点赞了', '点亮了',
                    '关注了主播', '关注了直播间',
                    '分享了直播间', '分享了',
                    '加入了直播间', '来了', '进入直播间',
                    '送出了', '送出',
                    '正在去购买', '正在购买', '成功购买', '去购买',
                    '连击', 'Combo',
                    '点击', '浏览', '查看',
                    '欢迎', '感谢',
                    '购买了'
                ];

                // 检查内容是否包含系统关键词
                const isSystem = systemKeywords.some(kw => content.includes(kw));
                
                // 特殊处理 "来了" (通常在结尾)
                const isArrival = content.endsWith('来了');

                if (isSystem || isArrival) {
                    return; // 丢弃系统消息
                }

                // 过滤纯数字 (可能是ID、等级、统计数据)
                // 但保留简单的数字弹幕 (如 "666", "111")
                // 如果是纯数字且长度 > 6，或者是 "1.2w" 这种格式，则过滤
                const isLongId = /^\d{7,}$/.test(content);
                const isStat = /^\d+(\.\d+)?[万千百w]+$/i.test(content);
                
                if (isLongId || isStat) {
                    return;
                }

                // --- 步骤3: 输出有效弹幕 ---
                // 如果没有分离出昵称，暂时用 '用户' 代替，或者整句作为内容
                // 只有非空内容才推送
                if (content && content.length > 0) {
                    window.douyinMessages.push({
                        content: content,
                        nickname: nickname || '用户',
                        raw: textKey,
                        timestamp: Date.now()
                    });
                    window.domMessageCount++;
                }
            }

            // 使用 MutationObserver 监听 DOM 变化（最高效）
            const observer = new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                    if (mutation.type === 'childList') {
                        mutation.addedNodes.forEach(node => {
                            // 只处理元素节点
                            if (node.nodeType === 1) { // ELEMENT_NODE
                                processNode(node);
                            }
                        });
                    }
                }
            });

            // 启动监听
            function startObserving() {
                const container = findChatContainer();
                if (container) {
                    console.log('[DOM监听] 启动 MutationObserver 监听');
                    observer.observe(container, {
                        childList: true,
                        subtree: true // 监听子孙节点变化，因为文字可能在深层 span 中
                    });
                } else {
                    console.log('[DOM监听] 未找到弹幕容器，将在 2 秒后重试');
                    setTimeout(startObserving, 2000);
                }
            }
            
            // 页面加载完成后启动
            if (document.readyState === 'complete') {
                startObserving();
            } else {
                window.addEventListener('load', startObserving);
            }
            
            // 备用：如果 MutationObserver 失效，保留一个低频的全局扫描（每3秒）
            // 但仅扫描特定容器（如果找到）
            setInterval(() => {
                if (!window.chatContainer || !window.chatContainer.isConnected) {
                    startObserving();
                }
            }, 3000);

            console.log('[初始化] DOM弹幕监听器已注入 (MutationObserver模式)');
            """)
            logger.info("✓ DOM监听脚本已注入")

            # 导航到直播间
            url = f"https://live.douyin.com/{self.room_id}"
            logger.info(f"导航到直播间: {url}")

            try:
                await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
                logger.info(f"✓ 页面导航成功")
            except Exception as e:
                logger.error(f"✗ 页面导航失败: {e}")
                raise

            logger.info("等待页面完全加载...")
            await asyncio.sleep(8)  # 等待页面完全加载和WebSocket连接建立

            # 尝试触发页面交互，确保WebSocket建立
            logger.info("尝试触发页面交互...")
            try:
                # 点击页面body，确保页面获得焦点
                await self.page.click('body')
                await asyncio.sleep(2)

                # 尝试滚动页面
                await self.page.evaluate('() => window.scrollBy(0, 100)')
                await asyncio.sleep(2)
            except Exception as e:
                logger.warning(f"页面交互失败: {e}")

            # 调试：检查页面状态
            logger.info("=== 调试信息 ===")

            # 检查init_script是否执行
            init_check = await self.page.evaluate('''() => {
                return {
                    has_douyinMessages: typeof window.douyinMessages !== 'undefined',
                    has_wsMessageCount: typeof window.wsMessageCount !== 'undefined',
                    has_wsConnections: typeof window.wsConnections !== 'undefined',
                    wsConnections: window.wsConnections || 0,
                    wsMessageCount: window.wsMessageCount || 0,
                    pageURL: window.location.href
                };
            }''')
            logger.info(f"Init脚本检查: {init_check}")

            # 截图保存
            screenshot_path = "debug_page.png"
            await self.page.screenshot(path=screenshot_path)
            logger.info(f"页面截图已保存: {screenshot_path}")

            # 获取页面标题
            title = await self.page.title()
            logger.info(f"页面标题: {title}")

            logger.info("=== 调试信息结束 ===")

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
        """定期从页面DOM提取消息"""
        consecutive_empty = 0
        last_dom_count = 0

        while self.is_running:
            try:
                # 从页面JavaScript中获取DOM监听到的消息
                messages = await self.page.evaluate('''() => {
                    if (!window.douyinMessages) return [];

                    const msgs = window.douyinMessages;
                    window.douyinMessages = [];  // 清空

                    return msgs;
                }''')

                # 获取DOM消息统计
                dom_stats = await self.page.evaluate('''() => {
                    return {
                        count: window.domMessageCount || 0
                    };
                }''')

                # 如果DOM消息数增加了，打印日志
                if dom_stats['count'] > last_dom_count:
                    logger.info(f"[DOM统计] 已捕获 {dom_stats['count']} 条弹幕")
                    last_dom_count = dom_stats['count']

                if messages:
                    consecutive_empty = 0
                    logger.info(f"[调试] 从CDP提取到 {len(messages)} 条弹幕")

                    for msg in messages:
                        self.stats["received"] += 1

                        content = msg.get('content', '').strip()
                        nickname = msg.get('nickname', '用户')
                        raw = msg.get('raw', '')

                        logger.debug(f"[调试] 消息内容: {content}, 昵称: {nickname}")
                        logger.debug(f"[调试] 原始数据: {raw}")

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
                    if consecutive_empty % 10 == 0:  # 每3秒打印一次
                        logger.info(f"[调试] 暂无弹幕，已等待 {consecutive_empty} 秒")
                        logger.info(f"[调试] DOM统计: 已捕获 {dom_stats['count']} 条弹幕")
                        if dom_stats['count'] == 0:
                            logger.warning("[警告] 未检测到弹幕！请确认直播间是否有弹幕")

            except Exception as e:
                logger.debug(f"提取消息失败: {e}")

            await asyncio.sleep(0.3)  # 每0.3秒检查一次，减少延迟

    def _is_valid_danmaku(self, text: str) -> bool:
        """检查是否是有效弹幕"""
        if not text:
            return False
            
        # 长度限制放宽
        if len(text) > 50:
            return False

        # 过滤系统消息
        invalid_patterns = [
            r'^在线观众',
            r'^正在观看',
            r'^人数',
            r'^点赞',
            r'^关注',
            r'^粉丝',
            # r'^主播', # 单独处理
            r'^直播',
            r'^房间',
            r'^榜',
            r'^贡献',
            r'^热度',
            r'^礼物',
            r'^感谢',
            r'^欢迎',
            r'^进入',
            r'^送出',
            r'^购买',
            r'^充值',
            r'^金币',
            r'^钻石',
            r'^点击',
            r'^发送',
            r'^分享',
            r'^复制',
            r'^举报',
            r'^取消',
            r'^确定',
            r'^连击',
            r'^浏览',
            r'^查看',
        ]

        import re
        for pattern in invalid_patterns:
            if re.search(pattern, text): # 改为search，只要包含就过滤
                return False

        # 特殊处理 "主播"
        if text == '主播' or text.startswith('主播 '):
            return False

        # 过滤纯数字（可能是ID或统计数据），但保留简单数字弹幕（如666）
        # 如果是纯数字且长度>6，认为是ID/时间/统计
        if text.isdigit() and len(text) > 6:
            return False
            
        # 过滤统计格式（1.2w, 1000+, 10k）
        if re.match(r'^\d+(\.\d+)?[万千百十wk]+$', text, re.IGNORECASE):
            return False

        # 必须包含至少一个有效字符（中文、字母、数字、符号）
        # 不再强制要求中文，允许 "666", "hello", "..."
        valid_char_count = sum(1 for c in text if c.isprintable() and not c.isspace())
        return valid_char_count > 0

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
