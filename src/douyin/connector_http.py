"""
HTTP轮询连接器 - 使用 /webcast/im/fetch/ API获取弹幕
"""

import asyncio
import gzip
import logging
import aiohttp
from typing import Callable, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


def read_varint(data, pos):
    """读取varint"""
    result = 0
    shift = 0
    while pos < len(data):
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return result, pos


class DouyinHTTPConnector:
    """
    HTTP轮询连接器 - 使用 im/fetch API 获取弹幕
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
        self.session: Optional[aiohttp.ClientSession] = None

        # 内部room_id（从页面提取的真实ID，如 7602589690532825856）
        self.internal_room_id: Optional[str] = None

        # 游标（用于分页）
        self.cursor: Optional[str] = None

        # 用户唯一ID
        self.user_unique_id: Optional[str] = None

    async def connect(self) -> bool:
        """建立连接 - 获取内部room_id"""
        logger.info("="*60)
        logger.info("HTTP轮询连接器启动")
        logger.info("="*60)

        try:
            # 创建HTTP会话
            self.session = aiohttp.ClientSession()

            # 步骤1: 访问直播间页面，获取内部room_id
            logger.info("步骤1: 获取内部room_id...")
            if not await self._get_internal_room_id():
                logger.error("无法获取内部room_id")
                return False

            logger.info(f"[OK] 内部room_id: {self.internal_room_id}")

            # 步骤2: 初始化游标
            logger.info("步骤2: 初始化消息获取...")
            await self._fetch_messages()

            logger.info("="*60)
            logger.info("连接器启动成功")
            logger.info("="*60)

            self.is_running = True
            return True

        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False

    async def _get_internal_room_id(self) -> bool:
        """从直播间页面获取内部room_id"""
        from playwright.async_api import async_playwright

        playwright = await (async_playwright()).start()

        try:
            # 连接Chrome
            browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")

            # 创建context
            context = await browser.new_context()

            # 设置cookie
            await context.add_cookies([{
                'name': 'ttwid',
                'value': self.ttwid,
                'domain': '.douyin.com',
                'path': '/'
            }])

            # 创建页面
            page = await context.new_page()

            # 访问直播间
            url = f"https://live.douyin.com/{self.room_id}"
            logger.info(f"访问直播间: {url}")

            await page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # 等待页面加载
            await asyncio.sleep(3)

            # 从页面提取内部room_id
            # 尝试多个可能的位置
            scripts = await page.evaluate('''() => {
                // 方法1: 从__pace_f[24]提取
                if (window.__pace_f && window.__pace_f[24]) {
                    try {
                        const match = window.__pace_f[24].match(/"roomId":"?(\\d+)"?/);
                        if (match) return match[1];
                    } catch(e) {}
                }

                // 方法2: 从__INITIAL_STATE__提取
                if (window.__INITIAL_STATE__) {
                    try {
                        const state = JSON.parse(window.__INITIAL_STATE__);
                        if (state.roomInfo && state.roomInfo.roomId) {
                            return state.roomInfo.roomId;
                        }
                    } catch(e) {}
                }

                // 方法3: 从URL提取
                const urlMatch = window.location.href.match(/room_id=(\\d+)/);
                if (urlMatch) return urlMatch[1];

                return null;
            }''')

            await page.close()
            await context.close()
            await browser.close()

            if scripts:
                self.internal_room_id = scripts
                return True

            logger.error("无法从页面提取room_id")
            return False

        except Exception as e:
            logger.error(f"获取room_id失败: {e}")
            return False

        finally:
            await playwright.stop()

    async def _fetch_messages(self) -> list:
        """获取消息"""
        if not self.internal_room_id:
            return []

        # 构建请求参数
        params = {
            'resp_content_type': 'protobuf',
            'did_rule': '3',
            'device_id': '',
            'app_name': 'douyin_web',
            'endpoint': 'live_pc',
            'support_wrds': '1',
            'user_unique_id': self.user_unique_id or '',
            'identity': 'audience',
            'need_persist_msg_count': '15',
            'insert_task_id': '',
            'live_reason': '',
            'room_id': self.internal_room_id,
            'version_code': '180800',
            'last_rtt': '0',
            'live_id': '1',
            'aid': '6383',
            'fetch_rule': '1',
            'cursor': self.cursor or '',
            'internal_ext': '',
            'device_platform': 'web',
            'cookie_enabled': 'true',
            'screen_width': '1280',
            'screen_height': '720',
            'browser_language': 'zh-CN',
            'browser_platform': 'Win32',
            'browser_name': 'Mozilla',
            'browser_online': 'true',
            'tz_name': 'Asia/Shanghai',
        }

        headers = {
            'Cookie': f'ttwid={self.ttwid}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': f'https://live.douyin.com/{self.room_id}',
            'Accept': 'application/json, text/plain, */*',
        }

        url = f"https://live.douyin.com/webcast/im/fetch/?{urlencode(params)}"

        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.read()

                    # 检查是否是protobuf
                    content_type = response.headers.get('Content-Type', '')
                    if 'protobuf' in content_type or not content_type:
                        # 返回原始数据
                        return [data]

                    # 可能是gzip压缩
                    try:
                        decompressed = gzip.decompress(data)
                        return [decompressed]
                    except:
                        return [data]
                else:
                    logger.warning(f"请求失败: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"获取消息失败: {e}")
            return []

    async def listen(self, message_handler: Callable):
        """监听消息"""
        logger.info("开始轮询消息...")
        logger.info("按 Ctrl+C 退出")

        try:
            while self.is_running:
                # 获取消息
                messages = await self._fetch_messages()

                # 处理每条消息
                for raw_message in messages:
                    try:
                        if asyncio.iscoroutinefunction(message_handler):
                            await message_handler(raw_message)
                        else:
                            message_handler(raw_message)
                    except Exception as e:
                        logger.error(f"处理消息失败: {e}")

                # 等待下次轮询
                await asyncio.sleep(self.poll_interval)

        except KeyboardInterrupt:
            logger.info("用户中断")
        except Exception as e:
            logger.error(f"监听异常: {e}")

    async def disconnect(self):
        """断开连接"""
        logger.info("正在断开连接...")

        self.is_running = False

        if self.session:
            try:
                await self.session.close()
            except:
                pass

        logger.info("已断开连接")
