"""
实时弹幕解析器 - 简化版

从真实的WebSocket消息中提取弹幕内容
"""

import gzip
import logging
from dataclasses import dataclass
from typing import Optional, List
import re

logger = logging.getLogger(__name__)


@dataclass
class UserInfo:
    """用户信息"""
    id: str = ""
    nickname: str = "匿名用户"


@dataclass
class ParsedMessage:
    """解析后的消息"""
    # 消息类型
    method: str = "Unknown"

    # 用户信息
    user: Optional[UserInfo] = None

    # 消息内容
    content: Optional[str] = None

    # 原始数据
    raw_data: Optional[bytes] = None


class RealtimeMessageParser:
    """
    实时消息解析器

    从真实的WebSocket消息中提取弹幕
    """

    def __init__(self):
        """初始化解析器"""
        self.message_count = 0
        self.danmaku_count = 0

    def parse_message(self, raw_data: bytes) -> Optional[ParsedMessage]:
        """
        解析二进制消息

        Args:
            raw_data: 原始二进制数据

        Returns:
            ParsedMessage: 解析后的消息
        """
        try:
            self.message_count += 1

            # 提取字段8（gzip压缩的protobuf数据）
            decompressed = self._extract_field_8(raw_data)

            if not decompressed:
                return None

            # 提取所有字符串
            strings = self._extract_all_strings(decompressed)

            if not strings:
                return None

            # 分析消息类型
            message_type = self._detect_message_type(strings)

            # 如果是聊天消息，提取弹幕
            if message_type == "WebcastChatMessage":
                danmaku = self._extract_danmaku(strings)
                if danmaku:
                    self.danmaku_count += 1
                    return danmaku

            # 对于其他消息类型，也可以返回（用于调试）
            return ParsedMessage(
                method=message_type,
                raw_data=raw_data
            )

        except Exception as e:
            logger.debug(f"解析消息失败: {e}")
            return None

    def _extract_field_8(self, raw_data: bytes) -> Optional[bytes]:
        """提取字段8并解压"""
        pos = 0

        while pos < len(raw_data):
            try:
                # 读取tag
                tag, pos = self._read_varint(raw_data, pos)

                if pos >= len(raw_data):
                    break

                field_number = tag >> 3
                wire_type = tag & 0x07

                # 查找字段8
                if field_number == 8 and wire_type == 2:
                    # 读取长度
                    length, pos = self._read_varint(raw_data, pos)

                    if pos + length <= len(raw_data):
                        field_8_data = raw_data[pos:pos + length]

                        # 尝试解压
                        try:
                            return gzip.decompress(field_8_data)
                        except:
                            # 解压失败，返回原始数据
                            return field_8_data

                # 跳过这个字段
                if wire_type == 0:  # varint
                    _, pos = self._read_varint(raw_data, pos)
                elif wire_type == 2:  # length-delimited
                    length, pos = self._read_varint(raw_data, pos)
                    pos += length
                else:
                    pos += 1

            except:
                break

        return None

    def _extract_all_strings(self, data: bytes) -> List[dict]:
        """
        提取所有字符串

        Returns:
            List[dict]: 字符串列表，每项包含field和text
        """
        strings = []
        pos = 0

        while pos < len(data):
            try:
                # 读取tag
                tag, pos = self._read_varint(data, pos)

                if pos >= len(data):
                    break

                field_number = tag >> 3
                wire_type = tag & 0x07

                if wire_type == 2:  # length-delimited
                    length, pos = self._read_varint(data, pos)

                    if pos + length > len(data):
                        break

                    value = data[pos:pos + length]
                    pos += length

                    # 尝试解析为字符串
                    try:
                        text = value.decode('utf-8', errors='ignore')

                        # 只保留合理的字符串
                        if 1 <= len(text) <= 200:
                            # 检查是否包含可打印字符
                            printable_count = sum(1 for c in text if c.isprintable())
                            if printable_count > len(text) * 0.3:
                                strings.append({
                                    'field': field_number,
                                    'text': text
                                })
                    except:
                        pass

                elif wire_type == 0:  # varint
                    _, pos = self._read_varint(data, pos)
                else:
                    pos += 1

            except:
                break

        return strings

    def _detect_message_type(self, strings: List[dict]) -> str:
        """
        检测消息类型

        Args:
            strings: 字符串列表

        Returns:
            str: 消息类型
        """
        for s in strings:
            text = s['text']

            # 检查是否是已知消息类型
            if 'WebcastChatMessage' in text:
                return "WebChatMessage"
            elif 'WebcastGiftMessage' in text:
                return "WebGiftMessage"
            elif 'WebcastRoomStatsMessage' in text:
                return "WebcastRoomStatsMessage"
            elif 'WebcastRoomUserSeqMessage' in text:
                return "WebcastRoomUserSeqMessage"
            elif 'WebcastLikeMessage' in text:
                return "WebcastLikeMessage"

        return "Unknown"

    def _extract_danmaku(self, strings: List[dict]) -> Optional[ParsedMessage]:
        """
        从聊天消息中提取弹幕

        Args:
            strings: 字符串列表

        Returns:
            ParsedMessage: 包含弹幕的消息
        """
        user = UserInfo()
        content = None

        # 查找用户昵称和弹幕内容
        # 基于我们的研究发现：
        # - 用户昵称通常较短（2-20字符），可能包含*号
        # - 弹幕内容也是短文本（2-50字符）
        # - 需要过滤掉URL、路径等非弹幕内容

        for s in strings:
            text = s['text']

            # 过滤掉明显的非弹幕内容
            if self._is_system_message(text):
                continue

            # 检查是否是用户昵称
            if 2 <= len(text) <= 20 and self._is_valid_nickname(text):
                user.nickname = text
                user.id = text  # 暂时使用昵称作为ID

            # 检查是否是弹幕内容
            elif 2 <= len(text) <= 50 and self._is_valid_danmaku(text):
                content = text
                break  # 找到弹幕内容就停止

        if content:
            return ParsedMessage(
                method="WebChatMessage",
                user=user,
                content=content
            )

        return None

    def _is_system_message(self, text: str) -> bool:
        """检查是否是系统消息"""
        system_keywords = [
            'http', 'https', '.png', '.jpg', '.image',
            'webcast', 'douyinpic', '/',
            '荣誉等级', '勋章', '粉丝团', '在线观众',
            '小时榜', '人气榜', '任务', '礼物',
            'level', 'badge', 'rank',
            'internal_src', 'first_req_ms',
            'compress_type', 'im-cursor',
        ]

        text_lower = text.lower()
        return any(keyword in text_lower for keyword in system_keywords)

    def _is_valid_nickname(self, text: str) -> bool:
        """检查是否是有效的用户昵称"""
        # 包含中文或字母
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text)
        has_alpha = any(c.isalpha() for c in text)

        if not (has_chinese or has_alpha):
            return False

        # 过滤掉明显不是昵称的内容
        if any(s in text for s in ['http', 'level', 'badge', '勋章']):
            return False

        return True

    def _is_valid_danmaku(self, text: str) -> bool:
        """检查是否是有效的弹幕内容"""
        # 必须包含中文或合理的英文
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text)
        has_alpha = any(c.isalpha() for c in text)

        if not (has_chinese or has_alpha):
            return False

        # 过滤掉URL和路径
        if any(s in text for s in ['http', 'https', '/', '.png', '.jpg']):
            return False

        # 过滤掉纯数字
        if text.isdigit():
            return False

        # 过滤掉过长的字母数字混合（可能是ID）
        if len(text) > 15:
            alpha_num = sum(1 for c in text if c.isalnum())
            if alpha_num / len(text) > 0.8:
                return False

        return True

    def _read_varint(self, data: bytes, pos: int) -> tuple:
        """
        读取varint编码的整数

        Returns:
            tuple: (value, new_pos)
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
