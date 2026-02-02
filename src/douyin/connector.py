"""
抖音直播间WebSocket连接器

负责连接到抖音直播间，建立WebSocket连接，并接收弹幕消息。
"""

import asyncio
import logging
import re
import json
from typing import Callable, Optional
from pathlib import Path

import aiohttp
import websockets

logger = logging.getLogger(__name__)


class DouyinConnector:
    """
    抖音直播间连接器

    负责建立WebSocket连接，发送心跳，接收消息。
    """

    # 默认User-Agent
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    # 心跳间隔（秒）
    HEARTBEAT_INTERVAL = 30

    def __init__(self, room_id: str, ttwid: str):
        """
        初始化连接器

        Args:
            room_id: 直播间房间ID
            ttwid: 抖音ttwid cookie
        """
        self.room_id = room_id
        self.ttwid = ttwid
        self.ws_url: Optional[str] = None
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.heartbeat_task: Optional[asyncio.Task] = None

    async def _get_room_info(self) -> dict:
        """
        获取直播间信息（包括WebSocket URL）

        Returns:
            dict: 房间信息，包含WebSocket URL

        Raises:
            ConnectionError: 无法获取WebSocket URL
        """
        url = f"https://live.douyin.com/{self.room_id}"

        headers = {
            "User-Agent": self.USER_AGENT,
            "Cookie": f"ttwid={self.ttwid}",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        raise ConnectionError(f"HTTP {resp.status}: 无法访问直播间")

                    html = await resp.text()

                    # 从HTML中提取WebSocket URL
                    # 抖音直播间的WebSocket URL通常在JavaScript中
                    # 格式类似: wss://webcast5-ws-web-lf.amemv.com/webcast/im/push/v2/

                    # 方法1: 搜索wss://开头的URL
                    ws_matches = re.findall(r'"(wss://[^"]+)"', html)

                    if not ws_matches:
                        # 方法2: 尝试从其他模式提取
                        # 有时候URL会被编码或分散在多个地方
                        ws_matches = re.findall(r'webcast.*?\.amemv\.com', html)

                    if ws_matches:
                        # 使用第一个找到的WebSocket URL
                        ws_base = ws_matches[0]
                        if not ws_base.startswith('wss://'):
                            # 如果提取的URL不完整，尝试构造
                            self.ws_url = f"wss://{ws_base}/webcast/im/push/v2/"
                        else:
                            self.ws_url = ws_base

                        logger.info(f"获取到WebSocket URL: {self.ws_url}")
                        return {
                            "status": "success",
                            "ws_url": self.ws_url,
                            "room_id": self.room_id
                        }

                    raise ConnectionError("无法从HTML中提取WebSocket URL")

        except aiohttp.ClientError as e:
            raise ConnectionError(f"网络请求失败: {e}")
        except Exception as e:
            raise ConnectionError(f"获取房间信息失败: {e}")

    async def connect(self) -> bool:
        """
        建立WebSocket连接

        Returns:
            bool: 连接是否成功

        Raises:
            ConnectionError: 连接失败
        """
        try:
            # 1. 获取房间信息（包括WebSocket URL）
            logger.info(f"正在连接直播间: {self.room_id}")
            await self._get_room_info()

            if not self.ws_url:
                raise ConnectionError("WebSocket URL未设置")

            # 2. 建立WebSocket连接
            headers = {
                "Cookie": f"ttwid={self.ttwid}",
                "User-Agent": self.USER_AGENT,
                "Origin": "https://live.douyin.com",
            }

            logger.info(f"正在建立WebSocket连接: {self.ws_url}")
            self.ws = await websockets.connect(
                self.ws_url,
                extra_headers=headers,
                ping_interval=None,  # 我们自己实现心跳
                close_timeout=10,
            )

            self.is_connected = True
            logger.info("WebSocket连接成功")

            # 3. 启动心跳任务
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            return True

        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            self.is_connected = False
            raise

    async def listen(self, callback: Callable[[dict], None]):
        """
        监听消息

        Args:
            callback: 消息回调函数，接收原始消息数据
        """
        if not self.is_connected or not self.ws:
            raise ConnectionError("未连接到直播间")

        logger.info("开始监听消息...")

        try:
            async for message in self.ws:
                try:
                    # 解析消息
                    if isinstance(message, bytes):
                        # 二进制消息（protobuf格式）
                        # TODO: 实现protobuf解析（步骤1.7）
                        logger.debug(f"收到二进制消息: {len(message)} 字节")
                        # 暂时传递原始数据
                        await callback({
                            "type": "binary",
                            "data": message,
                            "raw": True
                        })
                    else:
                        # 文本消息（JSON格式）
                        logger.debug(f"收到文本消息: {message}")
                        msg_data = json.loads(message) if message else {}
                        await callback(msg_data)

                except Exception as e:
                    logger.error(f"处理消息失败: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket连接已关闭")
            self.is_connected = False
        except Exception as e:
            logger.error(f"监听消息异常: {e}")
            self.is_connected = False

    async def disconnect(self):
        """断开WebSocket连接"""
        logger.info("正在断开连接...")

        # 停止心跳任务
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        # 关闭WebSocket连接
        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                logger.error(f"关闭WebSocket时出错: {e}")

        self.is_connected = False
        logger.info("已断开连接")

    async def _heartbeat_loop(self):
        """
        心跳保活循环

        每30秒发送一次ping消息，保持连接活跃。
        """
        try:
            while self.is_connected and self.ws and not self.ws.closed:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)

                if self.ws and not self.ws.closed:
                    # 发送ping
                    try:
                        # websockets库的ping
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

    async def _send_auth(self):
        """
        发送认证消息

        注意：此方法需要protobuf序列化支持（在步骤1.7实现）
        目前为占位实现。
        """
        # TODO: 实现认证消息序列化（需要protobuf schema）
        logger.debug("发送认证消息（待实现protobuf序列化）")

        # 占位：发送一个简单的JSON格式消息
        # 实际抖音使用protobuf格式
        auth_msg = {
            "method": "WebcastAuthMessage",
            "payload": {
                "room_id": self.room_id,
                "ttwid": self.ttwid
            }
        }

        # 注意：这里只是示例，实际不会工作
        # 真正的实现需要protobuf编码
        logger.debug(f"认证消息（占位）: {auth_msg}")

    def _serialize_message(self, msg: dict) -> bytes:
        """
        序列化消息为字节格式

        注意：此方法需要protobuf支持（在步骤1.7实现）

        Args:
            msg: 消息字典

        Returns:
            bytes: 序列化后的字节数据
        """
        # TODO: 实现protobuf序列化
        # 暂时返回JSON编码
        return json.dumps(msg).encode('utf-8')

    @property
    def connected(self) -> bool:
        """是否已连接"""
        return self.is_connected and self.ws is not None and not self.ws.closed
