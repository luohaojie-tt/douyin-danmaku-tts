"""
改进的连接器 - 查找并连接到聊天WebSocket

策略：
1. 在浏览器中监听所有WebSocket连接
2. 找到包含聊天消息的那个
3. 使用那个URL建立Python连接
"""

import asyncio
import gzip
import logging
from typing import Callable, Optional, List
from playwright.async_api import async_playwright
import websockets

logger = logging.getLogger(__name__)


def read_varint(data, pos):
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


def extract_field_8(raw_data):
    """提取字段8并解压"""
    pos = 0
    while pos < len(raw_data):
        tag, pos = read_varint(raw_data, pos)
        field_number = tag >> 3
        wire_type = tag & 0x07

        if field_number == 8 and wire_type == 2:
            length, pos = read_varint(raw_data, pos)
            if pos + length <= len(raw_data):
                field_8_data = raw_data[pos:pos + length]
                try:
                    return gzip.decompress(field_8_data)
                except:
                    return field_8_data
            break

        if wire_type == 0:
            _, pos = read_varint(raw_data, pos)
        elif wire_type == 2:
            length, pos = read_varint(raw_data, pos)
            pos += length
        else:
            pos += 1

    return None


def check_has_chat_message(raw_data):
    """快速检查消息是否包含聊天"""
    try:
        decompressed = extract_field_8(raw_data)
        if decompressed:
            # 搜索WebcastChatMessage
            return b'WebcastChatMessage' in decompressed
    except:
        pass
    return False


class DouyinConnectorV4:
    """
    改进的连接器 - 找到正确的聊天WebSocket
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

        # 检测到的WebSocket信息
        self.ws_info_list = []
        self.chat_ws_url = None

    async def connect(self) -> bool:
        """建立连接"""
        logger.info("="*60)
        logger.info("启动V4连接器（查找聊天WebSocket）")
        logger.info("="*60)

        try:
            # 步骤1: 启动浏览器并监听所有WebSocket
            logger.info("步骤1: 监听浏览器中的所有WebSocket...")
            if not await self._monitor_all_websockets():
                logger.error("监听WebSocket失败")
                return False

            logger.info(f"[OK] 检测到 {len(self.ws_info_list)} 个WebSocket连接")

            # 步骤2: 分析哪个WebSocket包含聊天消息
            logger.info("步骤2: 分析哪个WebSocket包含聊天消息...")
            if not await self._find_chat_websocket():
                logger.error("找不到包含聊天的WebSocket")
                return False

            logger.info(f"[OK] 找到聊天WebSocket")

            # 步骤3: 使用找到的URL建立Python连接
            logger.info("步骤3: 建立Python WebSocket连接...")
            if not await self._connect_python_websocket():
                logger.error("Python WebSocket连接失败")
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

    async def _monitor_all_websockets(self) -> bool:
        """监听浏览器中的所有WebSocket"""
        try:
            self.playwright = async_playwright()
            p = await self.playwright.__aenter__()

            # 连接Chrome
            try:
                self.browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            except Exception as e:
                logger.error(f"无法连接Chrome: {e}")
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

            # 创建页面
            self.page = await self.context.new_page()

            # 监听所有WebSocket
            detected_ws = []
            ws_data = {}  # ws_url -> {ws, message_count, has_chat}

            def on_websocket(ws):
                url = ws.url
                logger.info(f"  [发现] WebSocket: {url[:80]}...")

                ws_data[url] = {
                    'ws': ws,
                    'message_count': 0,
                    'has_chat': False,
                    'sample_messages': []
                }
                detected_ws.append(url)

                # 监听这个WebSocket的消息
                async def monitor_messages():
                    try:
                        async for msg in ws:
                            ws_info = ws_data[url]
                            ws_info['message_count'] += 1

                            # 检查是否包含聊天
                            if check_has_chat_message(msg):
                                ws_info['has_chat'] = True
                                logger.info(f"    [聊天] WebSocket包含聊天消息！(已收到{ws_info['message_count']}条)")

                            # 保存前几条消息样本
                            if len(ws_info['sample_messages']) < 5:
                                ws_info['sample_messages'].append(msg)

                            # 如果所有WebSocket都检查过了，可以停止
                            total_messages = sum(info['message_count'] for info in ws_data.values())
                            if total_messages > 50:  # 至少50条消息
                                logger.info(f"    已收集 {total_messages} 条消息样本")
                                break

                    except Exception as e:
                        logger.debug(f"监控WebSocket消息失败: {e}")

                # 启动监控任务
                asyncio.create_task(monitor_messages())

            self.page.on("websocket", on_websocket)

            # 访问直播间
            url = f"https://live.douyin.com/{self.room_id}"
            logger.info(f"访问直播间: {url}")

            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            logger.info("页面加载完成")

            # 等待WebSocket连接并收集消息
            logger.info("等待WebSocket连接并收集消息样本（30秒）...")
            await asyncio.sleep(30)

            # 保存WebSocket信息
            for ws_url, info in ws_data.items():
                self.ws_info_list.append({
                    'url': ws_url,
                    'message_count': info['message_count'],
                    'has_chat': info['has_chat'],
                    'sample_messages': info['sample_messages']
                })

            # 打印统计
            logger.info("\nWebSocket统计:")
            for i, info in enumerate(self.ws_info_list):
                has_chat_mark = " [✓有聊天]" if info['has_chat'] else "      "
                logger.info(f"  WS{i+1}: {info['message_count']} 条消息{has_chat_mark}")
                logger.debug(f"       URL: {info['url'][:80]}...")

            return True

        except Exception as e:
            logger.error(f"监听WebSocket失败: {e}")
            return False

    async def _find_chat_websocket(self) -> bool:
        """找到包含聊天消息的WebSocket"""
        # 查找有聊天消息的WebSocket
        for info in self.ws_info_list:
            if info['has_chat']:
                self.chat_ws_url = info['url']
                logger.info(f"找到聊天WebSocket!")
                logger.debug(f"URL: {self.chat_ws_url}")
                return True

        logger.warning("  没有找到包含聊天的WebSocket")
        logger.info("  将使用第一个WebSocket")

        # 如果都没找到聊天，使用第一个
        if self.ws_info_list:
            self.chat_ws_url = self.ws_info_list[0]['url']
            return True

        return False

    async def _connect_python_websocket(self) -> bool:
        """使用找到的URL建立Python连接"""
        if not self.chat_ws_url:
            return False

        headers = {
            "Cookie": f"ttwid={self.ttwid}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://live.douyin.com",
            "Referer": f"https://live.douyin.com/{self.room_id}",
        }

        logger.info(f"连接到: {self.chat_ws_url[:80]}...")

        try:
            self.ws = await websockets.connect(
                self.chat_ws_url,
                additional_headers=headers,
                ping_interval=None,
                close_timeout=10,
            )

            logger.info("[OK] WebSocket连接成功")
            return True

        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False

    async def listen(self, message_handler: Callable):
        """监听消息"""
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

        if self.ws:
            try:
                await self.ws.close()
            except:
                pass

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
                await self.playwright.__aexit__(None, None, None)
            except:
                pass

        self.is_connected = False
        logger.info("已断开连接")
