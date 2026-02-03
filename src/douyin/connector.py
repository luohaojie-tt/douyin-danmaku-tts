"""
抖音直播间WebSocket连接器

基于已验证的抖音直播协议实现，参考：
- GitHub: zeusec/DouyinLive
- GitHub: reqbat/douyin-live
"""

import asyncio
import gzip
import logging
from typing import Callable, Optional

import websockets

logger = logging.getLogger(__name__)


class DouyinConnector:
    """
    抖音直播间连接器

    基于已验证的协议实现
    """

    # 已验证的WebSocket服务器列表（2025年2月）
    WS_SERVERS = [
        "wss://webcast5-ws-web-lf.douyin.com/webcast/im/push/v2/",
        "wss://webcast5-ws-web-hl.douyin.com/webcast/im/push/v2/",
        "wss://webcast3-ws-web-lf.douyin.com/webcast/im/push/v2/",
        "wss://webcast.amemv.com/webcast/im/push/v2/",
    ]

    # User-Agent
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

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
        self.heartbeat_task: Optional[asyncio.Task] = None

        # 序列号（用于消息）
        self.seq_id = 1

    async def connect(self) -> bool:
        """
        建立WebSocket连接

        使用已验证的WebSocket服务器地址

        Returns:
            bool: 连接是否成功
        """
        logger.info(f"正在连接直播间: {self.room_id}")

        # 尝试多个服务器
        for ws_url in self.WS_SERVERS:
            try:
                # 在URL中添加房间ID参数
                full_url = f"{ws_url}?room_id={self.room_id}"
                logger.info(f"尝试连接: {full_url}")

                headers = {
                    "Cookie": f"ttwid={self.ttwid}",
                    "User-Agent": self.USER_AGENT,
                    "Origin": "https://live.douyin.com",
                }

                self.ws = await websockets.connect(
                    full_url,
                    additional_headers=headers,
                    ping_interval=None,
                    close_timeout=10,
                )

                self.is_connected = True
                logger.info(f"WebSocket连接成功: {full_url}")

                # 启动心跳
                self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                return True

            except Exception as e:
                logger.warning(f"连接 {ws_url} 失败: {e}")
                continue

        # 所有服务器都失败
        logger.error("所有WebSocket服务器连接失败")
        return False

    async def listen(self, callback: Callable[[dict], None]):
        """
        监听消息

        Args:
            callback: 消息回调函数
        """
        if not self.is_connected or not self.ws:
            raise ConnectionError("未连接到直播间")

        logger.info("开始监听消息...")

        try:
            async for message in self.ws:
                try:
                    if isinstance(message, bytes):
                        # 二进制消息（gzip压缩的protobuf）
                        parsed = await self._parse_message(message)
                        if parsed:
                            await callback(parsed)
                    else:
                        # 文本消息
                        logger.debug(f"收到文本消息: {message}")

                except Exception as e:
                    logger.error(f"处理消息失败: {e}")

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"WebSocket连接已关闭: {e}")
            self.is_connected = False
        except Exception as e:
            logger.error(f"监听消息异常: {e}")
            self.is_connected = False

    async def disconnect(self):
        """断开WebSocket连接"""
        logger.info("正在断开连接...")

        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                logger.error(f"关闭WebSocket时出错: {e}")

        self.is_connected = False
        logger.info("已断开连接")

    async def _heartbeat_loop(self):
        """心跳保活循环"""
        try:
            while self.is_connected and self.ws and not self.ws.closed:
                await asyncio.sleep(30)

                if self.ws and not self.ws.closed:
                    try:
                        pong_waiter = await self.ws.ping()
                        await asyncio.wait_for(pong_waiter, timeout=5)
                        logger.debug("心跳ping成功")
                    except asyncio.TimeoutError:
                        logger.warning("心跳ping超时")
                        break
                    except Exception as e:
                        logger.error(f"心跳ping失败: {e}")
                        break

        except asyncio.CancelledError:
            logger.debug("心跳任务已取消")
        except Exception as e:
            logger.error(f"心跳异常: {e}")

    async def _parse_message(self, raw_data: bytes) -> Optional[dict]:
        """
        解析二进制消息

        抖音消息格式：
        - 前端可能有包头（长度、类型等）
        - 可能是gzip压缩的
        - 主体是protobuf格式

        Args:
            raw_data: 原始二进制数据

        Returns:
            dict: 解析后的消息，如果解析失败返回None
        """
        try:
            # 尝试解压（可能是gzip压缩）
            try:
                decompressed = gzip.decompress(raw_data)
                logger.debug(f"消息已解压: {len(raw_data)} -> {len(decompressed)} 字节")
            except:
                # 不是gzip，直接使用原始数据
                decompressed = raw_data
                logger.debug(f"消息未压缩: {len(decompressed)} 字节")

            # TODO: 实现protobuf解析（步骤1.7）
            # 目前返回原始数据的摘要
            return {
                "type": "binary",
                "raw_length": len(raw_data),
                "decompressed_length": len(decompressed),
                "preview": decompressed[:50].hex() if decompressed else b"",
                "timestamp": asyncio.get_event_loop().time(),
                "raw": True  # 标记为未完全解析
            }

        except Exception as e:
            logger.error(f"解析消息失败: {e}")
            return None

    def _extract_host(self, ws_url: str) -> str:
        """从WebSocket URL提取主机名"""
        return ws_url.replace("wss://", "").replace("ws://", "").split("/")[0]

    async def send_ping(self):
        """发送ping消息"""
        if self.ws and not self.ws.closed:
            # 构造ping消息（简化版）
            ping_data = self._build_ping_message()
            if ping_data:
                await self.ws.send(ping_data)
                logger.debug("发送ping消息")

    def _build_ping_message(self) -> Optional[bytes]:
        """
        构造ping消息

        基于已验证的协议格式
        """
        try:
            # 简化的ping消息（实际需要更复杂的protobuf序列化）
            # 这里先返回None，使用WebSocket自带的ping
            return None
        except Exception as e:
            logger.error(f"构造ping消息失败: {e}")
            return None

    @property
    def connected(self) -> bool:
        """是否已连接"""
        return self.is_connected and self.ws is not None and not self.ws.closed


class DouyinConnectorMock(DouyinConnector):
    """
    Mock连接器用于测试

    不实际连接抖音，而是模拟接收消息
    """

    def __init__(self, room_id: str, ttwid: str):
        super().__init__(room_id, ttwid)
        self.mock_messages = [
            {
                "method": "WebChatMessage",
                "payload": {
                    "user": {
                        "nickname": "测试用户1",
                        "id": "123456",
                        "level": 10
                    },
                    "content": "主播好！",
                    "timestamp": 1234567890,
                }
            },
            {
                "method": "WebChatMessage",
                "payload": {
                    "user": {
                        "nickname": "测试用户2",
                        "id": "789012",
                        "level": 20
                    },
                    "content": "支持主播！",
                    "timestamp": 1234567891,
                }
            },
        ]

    async def connect(self) -> bool:
        """Mock连接"""
        logger.info(f"[MOCK] 模拟连接到直播间: {self.room_id}")
        self.is_connected = True
        return True

    async def listen(self, callback: Callable[[dict], None]):
        """Mock监听"""
        logger.info("[MOCK] 开始发送模拟消息...")

        for msg in self.mock_messages:
            if not self.is_connected:
                break
            await callback(msg)
            await asyncio.sleep(1)  # 模拟消息间隔

        logger.info("[MOCK] 模拟消息发送完毕")

    async def disconnect(self):
        """Mock断开"""
        logger.info("[MOCK] 模拟断开连接")
        self.is_connected = False
