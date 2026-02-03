"""
抖音直播间消息解析器

负责解析WebSocket接收到的二进制消息，提取用户信息和弹幕内容。
"""

import gzip
import logging
import re
from dataclasses import dataclass
from typing import Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class UserInfo:
    """用户信息"""
    id: str
    nickname: str
    level: int = 1
    badge: Optional[str] = None  # 勋章/舰队


@dataclass
class ParsedMessage:
    """解析后的消息"""
    # 消息类型
    method: str  # WebChatMessage, WebGiftMessage, WebLiveEndEvent等

    # 用户信息
    user: Optional[UserInfo] = None

    # 消息内容
    content: Optional[str] = None  # 弹幕文本

    # 礼物信息（如果是礼物消息）
    gift_name: Optional[str] = None
    gift_count: Optional[int] = None

    # 时间戳
    timestamp: int = 0

    # 原始数据（用于调试）
    raw: bool = False


class MessageParser:
    """
    消息解析器

    负责解析抖音WebSocket接收到的二进制消息
    """

    def __init__(self):
        """初始化解析器"""
        self.message_count = 0

    async def parse_message(self, raw_data: bytes) -> Optional[ParsedMessage]:
        """
        解析二进制消息

        Args:
            raw_data: 原始二进制数据（可能是gzip压缩的protobuf）

        Returns:
            ParsedMessage: 解析后的消息，如果解析失败返回None
        """
        try:
            self.message_count += 1

            # 1. 尝试解压（gzip压缩）
            decompressed = self._try_decompress(raw_data)

            # 2. 尝试解析protobuf
            parsed = self._try_parse_protobuf(decompressed)

            if parsed:
                logger.debug(f"消息 #{self.message_count}: {parsed.method}")
                return parsed
            else:
                # protobuf解析失败，返回基本信息
                return ParsedMessage(
                    method="Unknown",
                    timestamp=0,
                    raw=True,
                    content=f"[未解析的消息 {len(decompressed)}字节]"
                )

        except Exception as e:
            logger.error(f"解析消息失败: {e}")
            return None

    def _try_decompress(self, data: bytes) -> bytes:
        """
        尝试解压数据

        Args:
            data: 原始数据

        Returns:
            bytes: 解压后的数据
        """
        try:
            # 尝试gzip解压
            decompressed = gzip.decompress(data)
            logger.debug(f"数据已解压: {len(data)} -> {len(decompressed)} 字节")
            return decompressed
        except:
            # 不是gzip数据，直接返回原始数据
            logger.debug(f"数据未压缩: {len(data)} 字节")
            return data

    def _try_parse_protobuf(self, data: bytes) -> Optional[ParsedMessage]:
        """
        尝试解析protobuf数据

        注意：完整的protobuf解析需要.proto文件和protoc编译
        这里实现简化的解析逻辑

        Args:
            data: protobuf二进制数据

        Returns:
            ParsedMessage: 解析后的消息
        """
        try:
            # TODO: 完整的protobuf解析（需要.proto文件）
            # 当前实现：尝试从数据中提取可读文本

            # 方法1: 查找字符串（用户昵称、弹幕内容）
            text_parts = self._extract_text(data)

            # 方法2: 检测消息类型
            method = self._detect_message_type(data, text_parts)

            if method == "WebChatMessage":
                return self._parse_chat_message(data, text_parts)
            elif method == "WebGiftMessage":
                return self._parse_gift_message(data, text_parts)
            elif method == "WebLiveEndEvent":
                return ParsedMessage(
                    method="WebLiveEndEvent",
                    timestamp=0,
                    content="直播结束"
                )
            else:
                # 未知消息类型
                return None

        except Exception as e:
            logger.debug(f"protobuf解析失败: {e}")
            return None

    def _extract_text(self, data: bytes) -> list:
        """
        从二进制数据中提取可读文本

        Args:
            data: 二进制数据

        Returns:
            list: 提取出的文本片段列表
        """
        try:
            # 尝试将数据解码为文本（忽略错误）
            text = data.decode('utf-8', errors='ignore')

            # 提取连续的可读字符（中文、英文、数字）
            import re
            # 匹配中文、英文字符
            pattern = re.compile(r'[\u4e00-\u9fff\w\s]{2,}')
            matches = pattern.findall(text)

            return matches[:10]  # 返回前10个匹配

        except Exception as e:
            logger.debug(f"提取文本失败: {e}")
            return []

    def _detect_message_type(self, data: bytes, text_parts: list) -> str:
        """
        检测消息类型

        Args:
            data: 二进制数据
            text_parts: 提取的文本片段

        Returns:
            str: 消息类型
        """
        # 根据数据特征判断消息类型
        data_str = data.decode('utf-8', errors='ignore').lower()

        # 检查关键字
        if 'chatmessage' in data_str:
            return "WebChatMessage"
        elif 'giftmessage' in data_str:
            return "WebGiftMessage"
        elif 'liveend' in data_str:
            return "WebLiveEndEvent"
        elif 'auth' in data_str:
            return "WebcastAuthMessage"

        # 根据文本内容判断
        if text_parts:
            # 如果有较长的文本，可能是聊天消息
            long_texts = [t for t in text_parts if len(t) > 5]
            if long_texts:
                return "WebChatMessage"

        return "Unknown"

    def _parse_chat_message(self, data: bytes, text_parts: list) -> Optional[ParsedMessage]:
        """
        解析聊天消息

        Args:
            data: 原始数据
            text_parts: 提取的文本片段

        Returns:
            ParsedMessage: 解析后的消息
        """
        try:
            # 简化版：使用提取的文本
            if text_parts:
                # 第一个较长的文本可能是弹幕内容
                content = next((t for t in text_parts if len(t.strip()) > 2), "")

                # 构造模拟的用户信息
                user = UserInfo(
                    id="unknown",
                    nickname="用户",
                    level=1
                )

                return ParsedMessage(
                    method="WebChatMessage",
                    user=user,
                    content=content.strip(),
                    timestamp=0
                )

            return None

        except Exception as e:
            logger.debug(f"解析聊天消息失败: {e}")
            return None

    def _parse_gift_message(self, data: bytes, text_parts: list) -> Optional[ParsedMessage]:
        """
        解析礼物消息

        Args:
            data: 原始数据
            text_parts: 提取的文本片段

        Returns:
            ParsedMessage: 解析后的消息
        """
        try:
            # 简化版：查找礼物相关文本
            gift_name = None

            # 常见礼物名称
            common_gifts = ["玫瑰", "爱心", "掌声", "鲜花", "跑车", "火箭"]

            for text in text_parts:
                for gift in common_gifts:
                    if gift in text:
                        gift_name = gift
                        break
                if gift_name:
                    break

            if gift_name:
                user = UserInfo(
                    id="unknown",
                    nickname="用户",
                    level=1
                )

                return ParsedMessage(
                    method="WebGiftMessage",
                    user=user,
                    gift_name=gift_name,
                    gift_count=1,
                    timestamp=0,
                    content=f"送出 {gift_name}"
                )

            return None

        except Exception as e:
            logger.debug(f"解析礼物消息失败: {e}")
            return None

    def parse_test_message(self, message_data: dict) -> ParsedMessage:
        """
        解析测试消息（用于单元测试）

        Args:
            message_data: 测试消息字典

        Returns:
            ParsedMessage: 解析后的消息
        """
        method = message_data.get("method", "Unknown")

        if method == "WebChatMessage":
            payload = message_data.get("payload", {})
            user_data = payload.get("user", {})

            user = UserInfo(
                id=user_data.get("id", "unknown"),
                nickname=user_data.get("nickname", "用户"),
                level=user_data.get("level", 1)
            )

            return ParsedMessage(
                method=method,
                user=user,
                content=payload.get("content", ""),
                timestamp=payload.get("timestamp", 0)
            )

        elif method == "WebGiftMessage":
            payload = message_data.get("payload", {})
            user_data = payload.get("user", {})

            user = UserInfo(
                id=user_data.get("id", "unknown"),
                nickname=user_data.get("nickname", "用户"),
                level=user_data.get("level", 1)
            )

            return ParsedMessage(
                method=method,
                user=user,
                gift_name=payload.get("gift", {}).get("name", ""),
                gift_count=payload.get("gift", {}).get("count", 1),
                timestamp=payload.get("timestamp", 0),
                content=f"送出 {payload.get('gift', {}).get('name', '')}"
            )

        # 默认返回
        return ParsedMessage(
            method=method,
            timestamp=0,
            content=str(message_data)
        )


# 默认解析器实例
default_parser = MessageParser()
