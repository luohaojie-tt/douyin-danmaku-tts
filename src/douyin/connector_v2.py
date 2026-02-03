"""
抖音直播间连接器 - 改进版

基于 https://github.com/skmcj/dycast 项目的实现原理
"""

import asyncio
import hashlib
import json
import logging
import random
import re
import string
from collections import Counter
from pathlib import Path
from typing import Optional

import websockets

logger = logging.getLogger(__name__)


class DouyinConnectorV2:
    """
    抖音直播间连接器 V2

    实现原理：
    1. 从直播间HTML获取roomId和uniqueId
    2. 调用/webcast/im/fetch获取cursor和internalExt
    3. 构造WebSocket连接参数
    4. 连接并接收弹幕
    """

    # 基础配置
    BASE_URL = "wss://webcast5-ws-web-lf.douyin.com/webcast/im/push/v2/"
    VERSION = "1.0.14-beta.0"
    VERSION_CODE = "180800"
    AID = "6383"

    # User-Agent
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(self, room_id: str, ttwid: str):
        """
        初始化连接器

        Args:
            room_id: 直播间房间ID（URL中的数字）
            ttwid: 抖音ttwid cookie
        """
        self.room_id = room_id
        self.ttwid = ttwid
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False

        # 房间信息
        self.real_room_id = ""
        self.unique_id = ""
        self.cursor = ""
        self.internal_ext = ""

    def _get_signature_from_node(self) -> str:
        """
        通过Node.js计算signature

        Returns:
            str: signature值
        """
        import subprocess
        import json
        import sys
        from pathlib import Path

        # 查找tools目录
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent
        script_path = project_root / "tools" / "signature.js"

        logger.debug(f"查找signature.js: {script_path}")

        if not script_path.exists():
            logger.error(f"signature.js不存在: {script_path}")
            return ""

        try:
            result = subprocess.run(
                ["node", str(script_path), self.real_room_id, self.unique_id],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(project_root)
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data.get("success"):
                    logger.info(f"signature计算成功: {data['signature'][:16]}...")
                    return data['signature']
                else:
                    logger.error(f"signature计算失败: {data.get('error')}")
            else:
                logger.error(f"Node.js脚本错误: {result.stderr}")

        except Exception as e:
            logger.error(f"调用Node.js失败: {e}")

        # 备用：返回空字符串
        return ""

    def _generate_ms_token(self, length: int = 184) -> str:
        """生成msToken（模拟）"""
        chars = string.ascii_letters + string.digits + "-_"
        return ''.join(random.choice(chars) for _ in range(length))

    def _calculate_signature_stub(self, params: str) -> str:
        """
        计算signature stub（通过Node.js）

        Args:
            params: 参数字符串

        Returns:
            str: MD5哈希值（十六进制）
        """
        # 使用Node.js计算MD5
        import subprocess
        from pathlib import Path

        script_path = Path(__file__).parent.parent / "tools" / "signature.js"

        try:
            # 调用Node.js脚本
            result = subprocess.run(
                ["node", str(script_path), self.real_room_id, self.unique_id],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(script_path.parent)
            )

            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                if data.get("success"):
                    logger.debug(f"signature计算成功: {data['signature'][:16]}...")
                    return data['signature']

        except Exception as e:
            logger.warning(f"Node.js计算signature失败: {e}")

        # 备用：使用Python的MD5
        logger.debug("使用Python MD5作为备用")
        encoded = params.encode('utf-8')
        return hashlib.md5(encoded).hexdigest()

    async def _fetch_room_info(self) -> dict:
        """
        从直播间页面获取房间信息

        Returns:
            dict: 包含roomId, uniqueId, nickname等
        """
        url = f"https://live.douyin.com/{self.room_id}"

        headers = {
            "User-Agent": self.USER_AGENT,
            "Cookie": f"ttwid={self.ttwid}",
            "Referer": "https://live.douyin.com/",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                html = await resp.text()

        # 解析HTML获取房间信息
        info = self._parse_room_html(html)

        if not info.get("roomId"):
            raise ValueError("无法从HTML中获取roomId")

        logger.info(f"获取房间信息成功:")
        logger.info(f"  roomId: {info['roomId']}")
        logger.info(f"  uniqueId: {info['uniqueId']}")
        logger.info(f"  主播: {info.get('nickname', 'N/A')}")

        return info

    def _parse_room_html(self, html: str) -> dict:
        """
        从HTML中解析房间信息
        """
        info = {
            "roomId": "",
            "uniqueId": f"guest_{random.randint(1000000000, 9999999999)}",
            "nickname": "",
            "title": "",
            "status": 4
        }

        try:
            # 简化方法：直接在__pace_f.push中查找房间ID（9-12位数字）
            pattern = r'self\.__pace_f\.push\(\[1,"[a-z]*?:.*?\]\)'
            matches = re.findall(pattern, html)

            for match in matches:
                # 在匹配的文本中查找9-12位数字
                numbers = re.findall(r'\b\d{9,12}\b', match)

                # 找到出现次数最多的数字（通常是roomId）
                from collections import Counter
                if numbers:
                    counter = Counter(numbers)
                    most_common = counter.most_common(1)[0][0]

                    # 验证这是roomId（通常是当前房间ID）
                    if most_common == self.room_id or len(most_common) >= 9:
                        info["roomId"] = most_common
                        logger.info(f"找到roomId: {most_common}")
                        break

            # 如果没找到，使用URL中的ID
            if not info["roomId"]:
                info["roomId"] = self.room_id
                logger.info(f"使用URL中的ID作为roomId: {self.room_id}")

            # 提取主播名
            nickname_match = re.search(r'"nickname":"([^"]+)"', html)
            if nickname_match:
                info["nickname"] = nickname_match.group(1)

            # 检查直播状态
            if "isLive" in html or "status\":2" in html:
                info["status"] = 2

            return info

        except Exception as e:
            logger.warning(f"解析HTML失败: {e}")
            return self._parse_room_html_fallback(html)

    def _parse_room_html_fallback(self, html: str) -> dict:
        """备用方法：直接从HTML中提取信息"""
        info = {
            "roomId": "",
            "uniqueId": f"guest_{random.randint(1000000000, 9999999999)}",
            "nickname": "",
            "title": "",
            "status": 4
        }

        # 尝试提取roomId
        patterns = [
            r'"roomId":"(\d+)"',
            r'"room_id":"(\d+)"',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html)
            if matches:
                info["roomId"] = matches[0]
                break

        # 如果还是没找到，使用URL中的ID
        if not info["roomId"]:
            info["roomId"] = self.room_id

        # 提取主播名
        nickname_match = re.search(r'"nickname":"([^"]+)"', html)
        if nickname_match:
            info["nickname"] = nickname_match.group(1)

        # 检查直播状态
        if "isLive" in html or "liveRoom" in html:
            info["status"] = 2

        logger.info("使用备用方法解析房间信息")
        return info

    async def _fetch_im_info(self, room_id: str, unique_id: str) -> dict:
        """
        获取IM连接信息

        Args:
            room_id: 真实的房间ID
            unique_id: 用户唯一ID

        Returns:
            dict: 包含cursor和internalExt
        """
        ms_token = self._generate_ms_token(184)

        params = {
            "aid": self.AID,
            "app_name": "douyin_web",
            "browser_language": "zh-CN",
            "browser_name": "Mozilla",
            "browser_online": "true",
            "browser_platform": "Win32",
            "browser_version": self.USER_AGENT,
            "cookie_enabled": "true",
            "device_platform": "web",
            "did_rule": "3",
            "endpoint": "live_pc",
            "identity": "audience",
            "live_id": "1",
            "msToken": ms_token,
            "room_id": room_id,
            "user_unique_id": unique_id,
            "version_code": self.VERSION_CODE,
            "webcast_sdk_version": self.VERSION,
            # a_bogus可以硬编码为00000000（不一定验证）
            "a_bogus": "00000000",
        }

        url = f"https://live.douyin.com/webcast/im/fetch/?{urlencode(params)}"

        headers = {
            "User-Agent": self.USER_AGENT,
            "Cookie": f"ttwid={self.ttwid}",
            "Referer": f"https://live.douyin.com/{self.room_id}",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        # 响应是protobuf格式，暂时跳过解析
                        # 使用默认值
                        pass
        except Exception as e:
            logger.warning(f"获取IM信息失败: {e}")

        # 返回默认值
        now = int(asyncio.get_event_loop().time() * 1000)
        return {
            "cursor": f"r-{random.randint(1000000000000000000, 9999999999999999999)}_d-1_u-1",
            "internal_ext": f"internal_src:dim|wss_push_room_id:{room_id}|wss_push_did:{unique_id}",
        }

    def _build_ws_url(self) -> str:
        """
        构造WebSocket URL

        Returns:
            str: 完整的WebSocket URL
        """
        # 通过Node.js计算signature
        signature = self._get_signature_from_node()

        # 构造参数
        params = {
            "aid": self.AID,
            "app_name": "douyin_web",
            "browser_language": "zh-CN",
            "browser_name": "Mozilla",
            "browser_online": "true",
            "browser_platform": "Win32",
            "browser_version": self.USER_AGENT,
            "compress": "gzip",
            "cookie_enabled": "true",
            "cursor": self.cursor,
            "device_platform": "web",
            "did_rule": "3",
            "endpoint": "live_pc",
            "heartbeatDuration": "0",
            "host": "https://live.douyin.com",
            "identity": "audience",
            "internal_ext": self.internal_ext,
            "live_id": "1",
            "live_reason": "",
            "need_persist_msg_count": "15",
            "room_id": self.real_room_id,
            "screen_height": "1080",
            "screen_width": "1920",
            "signature": signature,  # 使用Node.js计算的signature
            "support_wrds": "1",
            "tz_name": "Asia/Shanghai",
            "update_version_code": self.VERSION,
            "user_unique_id": self.unique_id,
            "version_code": self.VERSION_CODE,
            "webcast_sdk_version": self.VERSION,
            "X-MS-STUB": signature,  # 同时添加X-MS-STUB
        }

        # 构造URL
        query_string = urlencode(params)
        return f"{self.BASE_URL}?{query_string}"

    async def connect(self) -> bool:
        """
        建立WebSocket连接

        Returns:
            bool: 连接是否成功
        """
        try:
            logger.info(f"正在连接直播间: {self.room_id}")

            # 1. 获取房间信息
            room_info = await self._fetch_room_info()
            self.real_room_id = room_info["roomId"]
            self.unique_id = room_info["uniqueId"]

            # 检查直播状态
            if room_info.get("status") != 2:
                logger.warning("直播间未开播")
                # 继续尝试连接，可能很快会开播

            # 2. 获取IM信息
            im_info = await self._fetch_im_info(self.real_room_id, self.unique_id)
            self.cursor = im_info["cursor"]
            self.internal_ext = im_info["internal_ext"]

            # 3. 构造WebSocket URL
            ws_url = self._build_ws_url()
            logger.info(f"WebSocket URL长度: {len(ws_url)} 字符")

            # 4. 建立连接
            headers = {
                "Cookie": f"ttwid={self.ttwid}",
                "User-Agent": self.USER_AGENT,
                "Origin": "https://live.douyin.com",
            }

            logger.info("正在建立WebSocket连接...")
            self.ws = await websockets.connect(ws_url, additional_headers=headers, ping_interval=None)

            self.is_connected = True
            logger.info("WebSocket连接成功！")

            return True

        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False

    async def listen(self, callback):
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
                        # 二进制消息
                        await self._handle_binary_message(message, callback)
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

    async def _handle_binary_message(self, data: bytes, callback):
        """
        处理二进制消息

        Args:
            data: 二进制数据
            callback: 回调函数
        """
        try:
            # 尝试解压
            try:
                decompressed = gzip.decompress(data)
                logger.debug(f"消息已解压: {len(data)} -> {len(decompressed)} 字节")
            except:
                decompressed = data

            # 简化处理：提取可读文本
            text = decompressed.decode('utf-8', errors='ignore')

            # 提取弹幕内容（简化版）
            if "content" in text:
                # 尝试提取弹幕
                import re
                content_match = re.search(r'"content":"([^"]+)"', text)
                if content_match:
                    content = content_match.group(1)

                    # 构造消息对象
                    msg = {
                        "type": "chat",
                        "content": content,
                        "timestamp": asyncio.get_event_loop().time(),
                    }

                    await callback(msg)

        except Exception as e:
            logger.error(f"处理二进制消息失败: {e}")

    async def disconnect(self):
        """断开WebSocket连接"""
        logger.info("正在断开连接...")

        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                logger.error(f"关闭WebSocket时出错: {e}")

        self.is_connected = False
        logger.info("已断开连接")


class DouyinConnectorV2Mock(DouyinConnectorV2):
    """Mock连接器用于测试"""

    def __init__(self, room_id: str, ttwid: str):
        super().__init__(room_id, ttwid)
        self.mock_messages = [
            {"type": "chat", "content": "测试弹幕1", "timestamp": 1234567890},
            {"type": "chat", "content": "测试弹幕2", "timestamp": 1234567891},
        ]

    async def connect(self) -> bool:
        """Mock连接"""
        logger.info(f"[MOCK V2] 模拟连接到直播间: {self.room_id}")
        self.is_connected = True
        return True

    async def listen(self, callback):
        """Mock监听"""
        logger.info("[MOCK V2] 开始发送模拟消息...")

        for msg in self.mock_messages:
            if not self.is_connected:
                break
            await callback(msg)
            await asyncio.sleep(1)

        logger.info("[MOCK V2] 模拟消息发送完毕")
