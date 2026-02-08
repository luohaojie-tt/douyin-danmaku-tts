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
            window.seenTexts = new Set();
            window.lastScanTime = Date.now();

            // 定期扫描页面中的弹幕元素（更可靠）
            function scanDanmaku() {
                try {
                    // 获取所有文本节点
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );

                    let node;
                    const newMessages = [];

                    while(node = walker.nextNode()) {
                        const text = node.textContent || '';

                        // 过滤条件
                        if (text.length >= 3 && text.length <= 50) {
                            // 检查是否包含中文
                            if (/[\\u4e00-\\u9fff]/.test(text)) {
                                // 排除系统消息和UI元素
                                const systemKeywords = [
                                    '点赞', '关注', '粉丝', '主播', '直播间', '进入', '送出', '购买了', '热榜', '在线人数',
                                    '放映厅', '小游戏', '充钻石', '客户端', '全部商品', '下载', '加载中', '在线观众',
                                    '退出', '开启', '关闭', '模式', '网页全屏', '小窗', '读屏标签',
                                    '小时榜', '人气榜', '贡献用户', '高等级用户', '嘉年华', '私人飞机',
                                    '抖音', '精选', '充值', '金币', '钻石', '账号', '登录', '注册',
                                    '许可证', '版权', '©', 'ICP备', '京ICP备', '网文', '视听',
                                    // 菜单项
                                    '我的喜欢', '我的收藏', '观看历史', '稍后再看', '我的作品', '我的预约', '我的订单',
                                    '发布视频', '视频管理', '作品数据', '开直播', '直播数据', '创作者学习中心', '创作者中心', '剪映专业版',
                                    // 法律和备案信息
                                    '药品', '医疗器械', '网络信息', '服务备案', '京', '网药械', '备字',
                                    '违法', '不良信息', '举报', '算法推荐', '专项举报', '从业人员', '违法违规', '反馈',
                                    // UI控制
                                    '屏幕旋转', '才能开始聊天',
                                    // 商品相关
                                    '爆款', '支持试用', '年终收官', '购物团'
                                ];
                                const isSystem = systemKeywords.some(kw => text.includes(kw));

                                // 排除纯数字、带单位的数字
                                const isNumber = /^\\d+[万千百十]+$/.test(text) || /^\\d+\\.\\d+万$/.test(text) || /^\\d+钻$/.test(text) || /^\\d+币$/.test(text);

                                // 排除按钮和链接
                                const parent = node.parentElement;
                                const isButton = parent && (parent.tagName === 'BUTTON' || parent.closest('button') || parent.tagName === 'A');

                                if (!isSystem && !isButton && !isNumber) {
                                    // 检查是否已处理
                                    const textKey = text.trim();
                                    if (!window.seenTexts.has(textKey)) {
                                        window.seenTexts.add(textKey);

                                        // 提取昵称
                                        let nickname = '用户';
                                        if (parent) {
                                            // 查找父元素的兄弟元素（可能包含用户名）
                                            const grandParent = parent.parentElement;
                                            if (grandParent) {
                                                const children = Array.from(grandParent.children);
                                                for (const child of children) {
                                                    if (child !== parent && child.textContent && child.textContent.length < 20 && child.textContent.length >= 2) {
                                                        const childText = child.textContent.trim();
                                                        // 过滤系统关键词和数字
                                                        const isChildSystem = systemKeywords.some(kw => childText.includes(kw));
                                                        const isChildNumber = /^\\d+[万千百十]+$/.test(childText) || /^\\d+\\.\\d+万$/.test(childText) || /^\\d+钻$/.test(childText) || /^\\d+币$/.test(childText);
                                                        if (!isChildSystem && !isChildNumber) {
                                                            nickname = childText;
                                                            break;
                                                        }
                                                    }
                                                }
                                            }
                                        }

                                        newMessages.push({
                                            content: text.trim(),
                                            nickname: nickname,
                                            timestamp: Date.now()
                                        });

                                        console.log('[DOM弹幕]', nickname, ':', text.trim());
                                    }
                                }
                            }
                        }
                    }

                    // 添加到全局消息列表
                    if (newMessages.length > 0) {
                        window.douyinMessages.push(...newMessages);
                        window.domMessageCount += newMessages.length;
                    }
                } catch(e) {
                    console.error('[扫描失败]', e);
                }
            }

            // 每秒扫描一次
            setInterval(scanDanmaku, 1000);

            console.log('[初始化] DOM弹幕监听器已启动（定期扫描模式）');
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
