#!/usr/bin/env python3
"""
抖音弹幕消息解析器
解析从WebSocket接收的protobuf消息
"""

import gzip
import struct
from typing import List, Dict, Any, Optional


class DanmakuMessage:
    """弹幕消息"""

    def __init__(self, content: str, user: str, user_id: str = "", timestamp: int = 0):
        self.content = content  # 弹幕内容
        self.user = user  # 用户昵称
        self.user_id = user_id  # 用户ID
        self.timestamp = timestamp  # 时间戳

    def __repr__(self):
        return f"[{self.user}]: {self.content}"

    def to_dict(self):
        return {
            "content": self.content,
            "user": self.user,
            "user_id": self.user_id,
            "timestamp": self.timestamp
        }


class DouyinMessageParser:
    """抖音消息解析器"""

    def __init__(self):
        self.message_count = 0
        self.danmaku_count = 0

    def parse_message(self, raw_data: bytes) -> List[Dict[str, Any]]:
        """
        解析原始消息

        Args:
            raw_data: 原始消息字节

        Returns:
            解析后的消息列表
        """
        messages = []

        try:
            # 检查是否gzip压缩
            if self._is_gzip_compressed(raw_data):
                # 解压gzip
                try:
                    decompressed = gzip.decompress(raw_data)
                    return self._parse_protobuf_message(decompressed)
                except Exception as e:
                    # 如果gzip解压失败，直接解析
                    pass

            # 直接解析protobuf
            return self._parse_protobuf_message(raw_data)

        except Exception as e:
            # 静默失败，不打印警告
            return messages

    def _is_gzip_compressed(self, data: bytes) -> bool:
        """检查是否是gzip压缩"""
        return data[:2] == b'\x1f\x8b'

    def _parse_protobuf_message(self, data: bytes) -> List[Dict[str, Any]]:
        """
        解析protobuf消息

        抖音消息格式 (简化版):
        - 每个字段使用 varint 编码的 tag-length-value 格式
        - tag = (field_number << 3) | wire_type
        - wire_type: 0=varint, 1=64bit, 2=length-delimited, 5=32bit
        """
        messages = []
        pos = 0

        while pos < len(data):
            try:
                # 读取tag
                tag, pos = self._read_varint(data, pos)
                field_number = tag >> 3
                wire_type = tag & 0x07

                # 根据wire_type读取值
                if wire_type == 0:  # varint
                    value, pos = self._read_varint(data, pos)

                    # 检查是否是消息类型字段
                    if field_number == 1:  # 通常是method字段
                        pass

                elif wire_type == 2:  # length-delimited (字符串或嵌套消息)
                    length, pos = self._read_varint(data, pos)
                    value = data[pos:pos + length]
                    pos += length

                    # 尝试解析为嵌套消息
                    if field_number == 2:  # messages字段
                        nested_messages = self._parse_nested_message(value)
                        messages.extend(nested_messages)

                    # 尝试解析为字符串
                    elif field_number in [6, 7]:  # 可能是文本内容
                        try:
                            text = value.decode('utf-8', errors='ignore')
                            if len(text) > 0 and len(text) < 500:  # 合理的文本长度
                                messages.append({
                                    'type': 'text',
                                    'field': field_number,
                                    'content': text
                                })
                        except:
                            pass

                elif wire_type == 5:  # 32bit
                    if pos + 4 <= len(data):
                        value = struct.unpack('<I', data[pos:pos + 4])[0]
                        pos += 4

                else:
                    # 跳过未知类型
                    pos += 1

            except Exception as e:
                # 解析错误，跳过
                break

        return messages

    def _parse_nested_message(self, data: bytes) -> List[Dict[str, Any]]:
        """解析嵌套消息（弹幕内容）"""
        messages = []
        pos = 0

        # 提取文本内容
        content = ""
        user = ""

        while pos < len(data):
            try:
                tag, pos = self._read_varint(data, pos)
                field_number = tag >> 3
                wire_type = tag & 0x07

                if wire_type == 0:
                    value, pos = self._read_varint(data, pos)

                elif wire_type == 2:
                    length, pos = self._read_varint(data, pos)
                    if pos + length > len(data):
                        break

                    value = data[pos:pos + length]
                    pos += length

                    # 尝试解析为字符串
                    try:
                        text = value.decode('utf-8', errors='ignore')

                        # 字段1通常是用户信息
                        if field_number == 1 and not user:
                            # 可能是用户昵称
                            if self._is_valid_nickname(text):
                                user = text

                        # 字段6、7、8通常是消息内容
                        elif field_number in [6, 7, 8]:
                            if self._is_valid_danmaku(text):
                                content = text

                    except:
                        pass

                else:
                    pos += 1

            except:
                break

        # 如果提取到有效弹幕，添加到列表
        if content and len(content) > 0 and len(content) < 500:
            messages.append({
                'type': 'danmaku',
                'content': content,
                'user': user or '匿名用户',
                'user_id': '',
                'timestamp': 0
            })
            self.danmaku_count += 1

        self.message_count += 1
        return messages

    def _read_varint(self, data: bytes, pos: int) -> tuple:
        """读取varint编码的整数"""
        result = 0
        shift = 0

        while pos < len(data):
            byte = data[pos]
            pos += 1

            result |= (byte & 0x7F) << shift

            if not (byte & 0x80):
                break

            shift += 7

            if shift >= 64:
                break

        return result, pos

    def _is_valid_nickname(self, text: str) -> bool:
        """检查是否是有效的用户昵称"""
        if not text:
            return False

        # 合理的昵称长度
        if len(text) > 50:
            return False

        # 包含中文字符或常见昵称字符
        return any(c.isalpha() or '\u4e00' <= c <= '\u9fff' for c in text)

    def _is_valid_danmaku(self, text: str) -> bool:
        """检查是否是有效的弹幕内容"""
        if not text:
            return False

        # 合理的弹幕长度
        if len(text) > 500 or len(text) < 1:
            return False

        # 过滤掉明显不是弹幕的内容
        invalid_patterns = [
            'compress_type',
            'internal_ext',
            'first_req_ms',
            'fetch_time',
            'wss_push',
        ]

        for pattern in invalid_patterns:
            if pattern in text:
                return False

        # 包含可读字符
        readable_chars = sum(1 for c in text if c.isprintable())
        if readable_chars < len(text) * 0.5:
            return False

        return True

    def parse_to_danmaku(self, raw_data: bytes) -> List[DanmakuMessage]:
        """解析为DanmakuMessage对象列表"""
        messages = self.parse_message(raw_data)

        danmaku_list = []
        for msg in messages:
            if msg.get('type') == 'danmaku':
                danmaku = DanmakuMessage(
                    content=msg['content'],
                    user=msg['user'],
                    user_id=msg.get('user_id', ''),
                    timestamp=msg.get('timestamp', 0)
                )
                danmaku_list.append(danmaku)

        return danmaku_list

    def get_stats(self):
        """获取统计信息"""
        return {
            'total_messages': self.message_count,
            'danmaku_count': self.danmaku_count
        }
