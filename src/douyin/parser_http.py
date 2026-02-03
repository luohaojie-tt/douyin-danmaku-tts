"""
HTTP响应解析器 - 解析 /webcast/im/fetch/ API返回的protobuf

HTTP API返回格式与WebSocket PushFrame不同，直接包含消息列表
"""

import gzip
import logging
import re
from dataclasses import dataclass
from typing import Optional, List

logger = logging.getLogger(__name__)


@dataclass
class UserInfo:
    """用户信息"""
    id: str
    nickname: str
    level: int = 1
    badge: Optional[str] = None


@dataclass
class ParsedMessage:
    """解析后的消息"""
    method: str  # WebChatMessage, WebGiftMessage等
    user: Optional[UserInfo] = None
    content: Optional[str] = None
    gift_name: Optional[str] = None
    gift_count: Optional[int] = None
    timestamp: int = 0


class HTTPResponseParser:
    """
    HTTP响应解析器

    专门解析 /webcast/im/fetch/ 返回的protobuf格式
    """

    def __init__(self):
        """初始化解析器"""
        self.message_count = 0

    def parse_response(self, raw_data: bytes) -> List[ParsedMessage]:
        """
        解析HTTP响应

        Args:
            raw_data: 原始响应数据（可能是gzip压缩）

        Returns:
            List[ParsedMessage]: 解析出的消息列表
        """
        try:
            # 1. 尝试解压
            data = self._try_decompress(raw_data)

            # 2. 解析protobuf，提取消息
            messages = self._extract_messages(data)

            logger.debug(f"解析出 {len(messages)} 条消息")
            return messages

        except Exception as e:
            logger.error(f"解析HTTP响应失败: {e}")
            return []

    def _try_decompress(self, data: bytes) -> bytes:
        """尝试解压gzip数据"""
        try:
            decompressed = gzip.decompress(data)
            logger.debug(f"Gzip解压: {len(data)} -> {len(decompressed)} 字节")
            return decompressed
        except:
            # 不是gzip数据
            return data

    def _extract_messages(self, data: bytes) -> List[ParsedMessage]:
        """
        从protobuf数据中提取消息

        HTTP API返回的结构大致是：
        Response {
            repeated Message messages = 1;
            ...
        }

        Message {
            MessageType type = 1;
            WebcastChatMessage chat = 2;
            WebcastGiftMessage gift = 3;
            ...
        }
        """
        messages = []

        try:
            # 简化版解析：查找所有嵌入的消息
            # 通过查找重复的protobuf模式来定位消息

            pos = 0
            while pos < len(data):
                # 读取tag
                tag, pos = self._read_varint(data, pos)
                if pos >= len(data):
                    break

                field_number = tag >> 3
                wire_type = tag & 0x07

                # 字段1通常包含消息列表
                if field_number == 1 and wire_type == 2:
                    # 这是一个嵌套消息
                    length, pos = self._read_varint(data, pos)
                    if pos + length > len(data):
                        break

                    message_data = data[pos:pos + length]
                    parsed = self._parse_message(message_data)
                    if parsed:
                        messages.append(parsed)

                    pos += length
                elif wire_type == 2:
                    # 跳过其他嵌套字段
                    length, pos = self._read_varint(data, pos)
                    pos += length
                elif wire_type == 0:
                    # 跳过varint字段
                    _, pos = self._read_varint(data, pos)
                else:
                    # 未知类型，跳过
                    break

        except Exception as e:
            logger.debug(f"提取消息失败: {e}")

        return messages

    def _parse_message(self, data: bytes) -> Optional[ParsedMessage]:
        """
        解析单条消息

        Message结构：
        Message {
            MessageType type = 1;  // varint
            oneof payload {
                WebcastChatMessage chat = 2;
                WebcastGiftMessage gift = 3;
                ...
            }
        }
        """
        try:
            pos = 0
            msg_type = None
            payload = None

            while pos < len(data):
                tag, pos = self._read_varint(data, pos)
                if pos >= len(data):
                    break

                field_number = tag >> 3
                wire_type = tag & 0x07

                if field_number == 1 and wire_type == 0:
                    # 消息类型
                    msg_type, pos = self._read_varint(data, pos)
                elif field_number == 2 and wire_type == 2:
                    # WebcastChatMessage
                    length, pos = self._read_varint(data, pos)
                    payload = data[pos:pos + length]
                    pos += length
                elif field_number == 3 and wire_type == 2:
                    # WebcastGiftMessage
                    length, pos = self._read_varint(data, pos)
                    payload = data[pos:pos + length]
                    pos += length
                    msg_type = 3  # 礼物消息
                elif wire_type == 2:
                    # 跳过其他嵌套字段
                    length, pos = self._read_varint(data, pos)
                    pos += length
                elif wire_type == 0:
                    # 跳过varint字段
                    _, pos = self._read_varint(data, pos)
                else:
                    break

            # 根据类型解析payload
            if msg_type == 1 or (msg_type is None and payload):
                # 聊天消息
                return self._parse_chat_message(payload)
            elif msg_type == 3:
                # 礼物消息
                return self._parse_gift_message(payload)

        except Exception as e:
            logger.debug(f"解析消息失败: {e}")

        return None

    def _parse_chat_message(self, data: bytes) -> Optional[ParsedMessage]:
        """
        解析WebcastChatMessage

        结构：
        WebcastChatMessage {
            User user = 1;
            string content = 2;
            ...
        }

        User {
            int64 id = 1;
            string nickname = 2;
            ...
        }
        """
        try:
            if not data:
                return None

            # 简化版：从数据中提取文本
            text = data.decode('utf-8', errors='ignore')

            # 提取用户昵称和内容
            # 查找连续的中文字符（可能是弹幕内容）
            chinese_pattern = re.compile(r'[\u4e00-\u9fff]{2,}')
            matches = chinese_pattern.findall(text)

            if not matches:
                return None

            # 通常最后一个较长的匹配是弹幕内容
            content = matches[-1] if len(matches) > 0 else ""

            # 尝试提取用户昵称（格式通常是 "昵称..."）
            nickname_match = re.search(r'[\u4e00-\u9fff]+[^\u4e00-\u9fff]*[\u4e00-\u9fff]+', text)
            nickname = nickname_match.group(0) if nickname_match else "用户"

            # 简单的用户信息
            user = UserInfo(
                id="unknown",
                nickname=nickname[:20],  # 限制长度
                level=1
            )

            # 过滤掉一些非弹幕内容
            if self._is_valid_danmaku(content):
                return ParsedMessage(
                    method="WebChatMessage",
                    user=user,
                    content=content,
                    timestamp=0
                )

        except Exception as e:
            logger.debug(f"解析聊天消息失败: {e}")

        return None

    def _parse_gift_message(self, data: bytes) -> Optional[ParsedMessage]:
        """解析礼物消息"""
        try:
            if not data:
                return None

            text = data.decode('utf-8', errors='ignore')

            # 查找礼物名称
            gift_match = re.search(r'[\u4e00-\u9fff]{2,4}', text)
            gift_name = gift_match.group(0) if gift_match else "礼物"

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

        except Exception as e:
            logger.debug(f"解析礼物消息失败: {e}")

        return None

    def _is_valid_danmaku(self, text: str) -> bool:
        """检查是否是有效弹幕"""
        if not text or len(text) < 2:
            return False

        # 过滤颜色代码
        if text.startswith('#') and len(text) in [7, 9]:
            return False

        # 过滤系统消息和排行榜消息
        system_keywords = [
            '榜', '第', '名', '贡献', '热度', '人气',
            '主播', '欢迎', '进入', '直播间', '关注',
            '礼物', '感谢', '送出', '点赞', '分享',
            'join', 'room', 'gift', 'like', 'follow'
        ]

        text_lower = text.lower()
        for keyword in system_keywords:
            if keyword in text or keyword in text_lower:
                # 允许某些特殊情况
                # 比如"欢迎"单独出现可以过滤，但"欢迎你"这种用户消息应该保留
                if keyword == '欢迎' and len(text) > 4:
                    continue
                if keyword == '主播' and '赞' in text:
                    continue  # "赞主播"这种可以保留
                return False

        # 必须包含中文
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text)
        if not has_chinese:
            return False

        # 过滤纯数字或特殊字符
        if len(text.strip('0123456789')) == 0:
            return False

        # 过滤太短的内容（2个字以下）
        if len(text) < 2:
            return False

        # 过滤重复字符（比如"哈哈哈"可以，但"啊啊啊啊啊啊"太长不行）
        if len(set(text)) < 2 and len(text) > 5:
            return False

        return True

    def _read_varint(self, data: bytes, pos: int) -> tuple[int, int]:
        """
        读取varint

        Returns:
            (value, new_pos)
        """
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


# 默认解析器实例
default_parser = HTTPResponseParser()
