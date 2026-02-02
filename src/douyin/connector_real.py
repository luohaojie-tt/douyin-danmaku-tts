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

from .protobuf import PushFrameCodec, PushFrameFactory

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
        self.playwright = None  # 保存playwright实例
        self.browser = None
        self.context = None
        self.page = None

        # 签名
        self.signature = None

        # 真实的roomId和uniqueId（从页面获取）
        self.real_room_id = None
        self.unique_id = None

        # 完整的WebSocket URL（从浏览器捕获）
        self.captured_ws_url = None

        # IM初始化参数（独立获取）
        self.im_cursor = None
        self.im_internal_ext = None

        # 心跳相关
        self.heartbeat_task = None
        self.heartbeat_interval = 10  # 心跳间隔（秒）
        self.should_stop_heartbeat = False

        # ACK相关 - 存储需要确认的消息信息
        self.last_internal_ext = None
        self.last_log_id = None

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

            # 步骤3: 启动心跳
            logger.info("步骤3: 启动心跳...")
            await self._start_heartbeat()
            logger.info("[OK] 心跳已启动")

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
            # 创建playwright实例并保存（不使用async with，避免自动关闭）
            self.playwright = async_playwright()
            p = await self.playwright.__aenter__()

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

            # 等待页面完全渲染和JavaScript执行完成
            # 这是关键！页面需要时间来加载所有数据
            logger.info("  等待页面完全渲染...")
            await asyncio.sleep(15)  # 增加到15秒，与deep_explore保持一致

            # 从浏览器中获取roomId和uniqueId（带重试机制）
            logger.info("  获取房间信息...")
            room_info = None
            for attempt in range(3):  # 最多尝试3次
                room_info = await self.page.evaluate('''() => {
                    // Extract from __pace_f element 24 using regex
                    if (window.self && window.self.__pace_f && window.self.__pace_f.length > 24) {
                        try {
                            const item = window.self.__pace_f[24];
                            if (item && item[1] && typeof item[1] === 'string') {
                                const content = item[1];

                                // Use regex to extract roomId (avoid JSON parse issues)
                                const roomMatch = content.match(/"roomId":"([0-9]+)"/);
                                const uniqueMatch = content.match(/"user_unique_id":"([0-9]+)"/);

                                if (roomMatch || uniqueMatch) {
                                    return {
                                        found: true,
                                        roomId: roomMatch ? roomMatch[1] : null,
                                        uniqueId: uniqueMatch ? uniqueMatch[1] : null
                                    };
                                }
                            }
                        } catch (e) {
                            console.error("Failed to extract from __pace_f[24]:", e);
                        }
                    }

                    return {found: false, pace_length: window.self?.__pace_f?.length || 0};
                }''')

                if room_info and room_info.get('found'):
                    break

                if attempt < 2:  # 不是最后一次尝试
                    logger.info(f"  第{attempt + 1}次尝试失败，__pace_f长度: {room_info.get('pace_length', 0)}，等待5秒后重试...")
                    await asyncio.sleep(5)

            if room_info and room_info.get('found'):
                self.real_room_id = room_info['roomId']
                self.unique_id = room_info['uniqueId']
                logger.info(f"  [OK] roomId: {self.real_room_id}")
                logger.info(f"  [OK] uniqueId: {self.unique_id}")
            else:
                logger.warning("  [WARN] 无法从页面获取roomId和uniqueId")
                self.real_room_id = None
                self.unique_id = None

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

            # 如果获取到了真实的roomId和uniqueId，获取IM初始化信息
            if self.real_room_id and self.unique_id:
                logger.info("  获取IM初始化参数...")
                import time
                now_ms = int(time.time() * 1000)

                # 生成cursor和internal_ext（参考dycast的格式）
                # cursor格式: t-{timestamp}_r-{room_id}_d-{device_id}_u-{user_id}_h-{hash}
                self.im_cursor = f"t-{now_ms}_r-{self.real_room_id}_d-1_u-1"

                # internal_ext格式: internal_src:dim|wss_push_room_id:{room_id}|wss_push_did:{unique_id}|...
                self.im_internal_ext = f"internal_src:dim|wss_push_room_id:{self.real_room_id}|wss_push_did:{self.unique_id}|first_req_ms:{now_ms}|fetch_time:{now_ms}|seq:1|wss_info:0-{now_ms}-0-0"

                logger.info(f"  [OK] cursor: {self.im_cursor[:80]}...")
                logger.info(f"  [OK] internal_ext: {self.im_internal_ext[:80]}...")
            else:
                logger.warning("  [WARN] 未获取到roomId和uniqueId，将使用默认参数")
                import time
                now_ms = int(time.time() * 1000)
                self.im_cursor = f"t-{now_ms}_r-{self.room_id}_d-1_u-1"
                self.im_internal_ext = f"internal_src:dim|wss_push_room_id:{self.room_id}|wss_push_did:{int(time.time()*1000)}|first_req_ms:{now_ms}"

            # 如果捕获到了WebSocket URL，从中提取更多参数
            if self.captured_ws_url:
                logger.info(f"  [INFO] 已捕获WebSocket URL（但不会使用它）")
                logger.info(f"  [INFO] 将使用独立生成的参数来接收弹幕")
            else:
                logger.info(f"  [INFO] 将使用独立生成的参数连接")

            # 注意：不要在这里关闭浏览器，保持连接！

            return True

        except Exception as e:
            logger.error(f"  [ERROR] 获取签名失败: {e}")
            return False

    async def _connect_websocket(self) -> bool:
        """
        建立WebSocket连接

        使用独立的cursor和internal_ext参数构造URL，而不是复用浏览器的URL

        Returns:
            bool: 连接是否成功
        """
        headers = {
            "Cookie": f"ttwid={self.ttwid}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://live.douyin.com",
            "Referer": f"https://live.douyin.com/{self.room_id}",
        }

        # 使用独立的参数构造WebSocket URL
        logger.info("  使用独立参数构造WebSocket URL")

        # 选择WebSocket服务器
        import random
        ws_server = random.choice(self.WS_SERVERS)
        logger.info(f"  WebSocket服务器: {ws_server}")

        # 构造URL参数
        import time
        from urllib.parse import urlencode

        # 使用真实的roomId（如果获取到了），否则使用room_id
        room_id_to_use = self.real_room_id if self.real_room_id else self.room_id

        # 生成用户唯一ID
        user_unique_id = self.unique_id if self.unique_id else f"{int(time.time() * 1000)}"

        params = {
            'app_name': 'douyin_web',
            'version_code': '180800',
            'webcast_sdk_version': '1.0.15',
            'update_version_code': '1.0.15',
            'compress': 'gzip',
            'device_platform': 'web',
            'cookie_enabled': 'true',
            'screen_width': '2560',
            'screen_height': '1440',
            'browser_language': 'zh-CN',
            'browser_platform': 'Win32',
            'browser_name': 'Mozilla',
            'browser_version': '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'browser_online': 'true',
            'tz_name': 'Asia/Shanghai',
            'cursor': self.im_cursor if self.im_cursor else f"t-{int(time.time()*1000)}_r-{room_id_to_use}_d-1_u-1",
            'internal_ext': self.im_internal_ext if self.im_internal_ext else f"internal_src:dim|wss_push_room_id:{room_id_to_use}",
            'host': 'https://live.douyin.com',
            'aid': '6383',
            'live_id': '1',
            'did_rule': '3',
            'endpoint': 'live_pc',
            'support_wrds': '1',
            'user_unique_id': user_unique_id,
            'im_path': '/webcast/im/fetch/',
            'identity': 'audience',
            'need_persist_msg_count': '15',
            'insert_task_id': '',
            'live_reason': '',
            'room_id': room_id_to_use,
            'heartbeatDuration': '0',
            'signature': self.signature if self.signature else ''
        }

        # 构造完整URL（注意路径是/webcast/im/push/v2/）
        ws_url = f"{ws_server}/webcast/im/push/v2/?{urlencode(params)}"

        logger.info(f"  WebSocket URL长度: {len(ws_url)} 字符")
        logger.debug(f"  room_id: {room_id_to_use}")
        logger.debug(f"  user_unique_id: {user_unique_id}")

        try:
            self.ws = await websockets.connect(
                ws_url,
                additional_headers=headers,
                ping_interval=None,
                close_timeout=10,
            )

            logger.info(f"  [OK] WebSocket连接成功（使用独立参数）")
            return True

        except Exception as e:
            logger.error(f"  [FAIL] WebSocket连接失败: {e}")
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
                    # 解析PushFrame获取internal_ext和log_id
                    if isinstance(raw_message, bytes):
                        frame = PushFrameCodec.decode(raw_message)
                        if frame:
                            logger.debug(f"  [Frame] payload_type: {frame.payload_type}, has_payload: {frame.payload is not None}")

                            if frame.payload:
                                # 解析Response检查是否需要ACK
                                need_ack, internal_ext = self._parse_response_for_ack(frame.payload)
                                logger.debug(f"  [Response] need_ack: {need_ack}, internal_ext: {internal_ext[:30] if internal_ext else 'None'}...")

                                if need_ack:
                                    # 保存用于ACK
                                    self.last_internal_ext = internal_ext
                                    self.last_log_id = frame.log_id

                                    # 发送ACK确认
                                    await self._send_ack_if_needed()

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

        # 停止心跳
        await self._stop_heartbeat()

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

    async def _start_heartbeat(self):
        """启动心跳任务"""
        self.should_stop_heartbeat = False
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.debug("  [Heartbeat] 心跳任务已创建")

    async def _stop_heartbeat(self):
        """停止心跳任务"""
        self.should_stop_heartbeat = True
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            self.heartbeat_task = None
            logger.debug("  [Heartbeat] 心跳任务已停止")

    async def _heartbeat_loop(self):
        """心跳循环"""
        logger.info("  [Heartbeat] 心跳循环已启动，间隔: {}秒".format(self.heartbeat_interval))

        while not self.should_stop_heartbeat:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                if self.should_stop_heartbeat:
                    break

                # 发送心跳帧
                await self._send_heartbeat()

            except asyncio.CancelledError:
                logger.debug("  [Heartbeat] 心跳任务被取消")
                break
            except Exception as e:
                logger.error(f"  [Heartbeat] 心跳发送失败: {e}")

    async def _send_heartbeat(self):
        """发送心跳帧"""
        try:
            if self.ws and self.is_connected:
                heartbeat_frame = PushFrameFactory.create_heartbeat()
                await self.ws.send(heartbeat_frame)
                logger.info(f"  [Heartbeat] 心跳已发送 (帧长度: {len(heartbeat_frame)} 字节)")
        except Exception as e:
            logger.error(f"  [Heartbeat] 发送心跳异常: {e}")

    async def _send_ack_if_needed(self):
        """
        发送ACK确认

        参考dycast第611-623行的逻辑
        """
        try:
            if self.last_internal_ext and self.ws and self.is_connected:
                ack_frame = PushFrameFactory.create_ack(
                    self.last_internal_ext,
                    self.last_log_id
                )
                await self.ws.send(ack_frame)
                logger.info(f"  [ACK] 已发送确认 (log_id: {self.last_log_id}, 长度: {len(ack_frame)} 字节)")
        except Exception as e:
            logger.error(f"  [ACK] 发送ACK异常: {e}")

    def _parse_response_for_ack(self, payload: bytes) -> tuple[bool, str]:
        """
        解析Response检查是否需要ACK

        Args:
            payload: PushFrame的payload字段

        Returns:
            (need_ack, internal_ext)
        """
        need_ack = False
        internal_ext = ""

        try:
            pos = 0
            while pos < len(payload):
                # 读取tag
                tag, pos = self._decode_varint(payload, pos)
                field_number = tag >> 3
                wire_type = tag & 0x07

                if field_number == 2 and wire_type == 2:  # internal_ext
                    length, pos = self._decode_varint(payload, pos)
                    internal_ext = payload[pos:pos + length].decode('utf-8', errors='ignore')
                    pos += length
                elif field_number == 9 and wire_type == 0:  # need_ack
                    # bool类型，读取一个字节
                    if pos < len(payload):
                        need_ack = bool(payload[pos])
                        pos += 1
                else:
                    # 跳过其他字段
                    if wire_type == 0:  # varint
                        _, pos = self._decode_varint(payload, pos)
                    elif wire_type == 2:  # length-delimited
                        length, pos = self._decode_varint(payload, pos)
                        pos += length
                    else:
                        pos += 1

        except Exception as e:
            logger.debug(f"解析Response失败: {e}")

        return need_ack, internal_ext

    @staticmethod
    def _decode_varint(data: bytes, pos: int) -> tuple[int, int]:
        """解码varint，返回(value, new_pos)"""
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

