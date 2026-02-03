"""
抖音PushFrame Protobuf编码/解码模块

参考: dycast/src/core/model.ts
"""

import gzip
import logging
from dataclasses import dataclass
from typing import Optional, Dict

logger = logging.getLogger(__name__)


@dataclass
class PushFrame:
    """PushFrame消息结构"""
    seq_id: Optional[int] = None  # 字段1
    log_id: Optional[int] = None  # 字段2
    service: Optional[int] = None  # 字段3
    method: Optional[int] = None  # 字段4
    headers_list: Optional[Dict[str, str]] = None  # 字段5
    payload_encoding: Optional[str] = None  # 字段6
    payload_type: Optional[str] = None  # 字段7: "hb", "ack", "msg", "close"
    payload: Optional[bytes] = None  # 字段8
    lod_id_new: Optional[str] = None  # 字段9


class PushFrameCodec:
    """PushFrame编解码器"""

    @staticmethod
    def encode(frame: PushFrame) -> bytes:
        """
        编码PushFrame为二进制

        Args:
            frame: PushFrame对象

        Returns:
            bytes: 编码后的二进制数据
        """
        result = bytearray()

        # 字段1: seq_id (uint64)
        if frame.seq_id is not None:
            result.extend(PushFrameCodec._encode_varint(8))  # tag: 1 << 3 | 0
            result.extend(PushFrameCodec._encode_varint(frame.seq_id))

        # 字段2: log_id (uint64)
        if frame.log_id is not None:
            result.extend(PushFrameCodec._encode_varint(16))  # tag: 2 << 3 | 0
            result.extend(PushFrameCodec._encode_varint(frame.log_id))

        # 字段3: service (uint64)
        if frame.service is not None:
            result.extend(PushFrameCodec._encode_varint(24))  # tag: 3 << 3 | 0
            result.extend(PushFrameCodec._encode_varint(frame.service))

        # 字段4: method (uint64)
        if frame.method is not None:
            result.extend(PushFrameCodec._encode_varint(32))  # tag: 4 << 3 | 0
            result.extend(PushFrameCodec._encode_varint(frame.method))

        # 字段5: headers_list (map<string, string>)
        if frame.headers_list:
            for key, value in frame.headers_list.items():
                # 编码每个键值对
                entry = bytearray()
                # key
                entry.extend(PushFrameCodec._encode_varint(10))  # tag: 1 << 3 | 2
                entry.extend(PushFrameCodec._encode_string(key))
                # value
                entry.extend(PushFrameCodec._encode_varint(18))  # tag: 2 << 3 | 2
                entry.extend(PushFrameCodec._encode_string(value))

                # 外层包装
                result.extend(PushFrameCodec._encode_varint(42))  # tag: 5 << 3 | 2
                result.extend(PushFrameCodec._encode_varint(len(entry)))
                result.extend(entry)

        # 字段6: payload_encoding (string)
        if frame.payload_encoding is not None:
            result.extend(PushFrameCodec._encode_varint(50))  # tag: 6 << 3 | 2
            result.extend(PushFrameCodec._encode_string(frame.payload_encoding))

        # 字段7: payload_type (string)
        if frame.payload_type is not None:
            result.extend(PushFrameCodec._encode_varint(58))  # tag: 7 << 3 | 2
            result.extend(PushFrameCodec._encode_string(frame.payload_type))

        # 字段8: payload (bytes)
        if frame.payload is not None:
            result.extend(PushFrameCodec._encode_varint(66))  # tag: 8 << 3 | 2
            result.extend(PushFrameCodec._encode_varint(len(frame.payload)))
            result.extend(frame.payload)

        # 字段9: lod_id_new (string)
        if frame.lod_id_new is not None:
            result.extend(PushFrameCodec._encode_varint(74))  # tag: 9 << 3 | 2
            result.extend(PushFrameCodec._encode_string(frame.lod_id_new))

        return bytes(result)

    @staticmethod
    def decode(data: bytes) -> Optional[PushFrame]:
        """
        解码二进制为PushFrame

        Args:
            data: 二进制数据

        Returns:
            PushFrame: 解码后的对象
        """
        frame = PushFrame()
        pos = 0

        while pos < len(data):
            try:
                # 读取tag
                tag, pos = PushFrameCodec._decode_varint(data, pos)
                field_number = tag >> 3
                wire_type = tag & 0x07

                if field_number == 1 and wire_type == 0:  # seq_id
                    value, pos = PushFrameCodec._decode_varint(data, pos)
                    frame.seq_id = value
                elif field_number == 2 and wire_type == 0:  # log_id
                    value, pos = PushFrameCodec._decode_varint(data, pos)
                    frame.log_id = value
                elif field_number == 3 and wire_type == 0:  # service
                    value, pos = PushFrameCodec._decode_varint(data, pos)
                    frame.service = value
                elif field_number == 4 and wire_type == 0:  # method
                    value, pos = PushFrameCodec._decode_varint(data, pos)
                    frame.method = value
                elif field_number == 5 and wire_type == 2:  # headers_list
                    length, pos = PushFrameCodec._decode_varint(data, pos)
                    entry_end = pos + length

                    if frame.headers_list is None:
                        frame.headers_list = {}

                    key = None
                    value = None

                    while pos < entry_end:
                        entry_tag, pos = PushFrameCodec._decode_varint(data, pos)
                        entry_field = entry_tag >> 3

                        if entry_field == 1 and (entry_tag & 0x07) == 2:  # key
                            str_len, pos = PushFrameCodec._decode_varint(data, pos)
                            key = data[pos:pos + str_len].decode('utf-8', errors='ignore')
                            pos += str_len
                        elif entry_field == 2 and (entry_tag & 0x07) == 2:  # value
                            str_len, pos = PushFrameCodec._decode_varint(data, pos)
                            value = data[pos:pos + str_len].decode('utf-8', errors='ignore')
                            pos += str_len
                        else:
                            # 跳过未知字段
                            wire = entry_tag & 0x07
                            if wire == 2:
                                str_len, pos = PushFrameCodec._decode_varint(data, pos)
                                pos += str_len
                            elif wire == 0:
                                _, pos = PushFrameCodec._decode_varint(data, pos)
                            else:
                                pos += 1

                    if key is not None and value is not None:
                        frame.headers_list[key] = value

                elif field_number == 6 and wire_type == 2:  # payload_encoding
                    length, pos = PushFrameCodec._decode_varint(data, pos)
                    frame.payload_encoding = data[pos:pos + length].decode('utf-8', errors='ignore')
                    pos += length
                elif field_number == 7 and wire_type == 2:  # payload_type
                    length, pos = PushFrameCodec._decode_varint(data, pos)
                    frame.payload_type = data[pos:pos + length].decode('utf-8', errors='ignore')
                    pos += length
                elif field_number == 8 and wire_type == 2:  # payload
                    length, pos = PushFrameCodec._decode_varint(data, pos)
                    frame.payload = data[pos:pos + length]
                    pos += length
                elif field_number == 9 and wire_type == 2:  # lod_id_new
                    length, pos = PushFrameCodec._decode_varint(data, pos)
                    frame.lod_id_new = data[pos:pos + length].decode('utf-8', errors='ignore')
                    pos += length
                else:
                    # 跳过未知字段
                    if wire_type == 0:
                        _, pos = PushFrameCodec._decode_varint(data, pos)
                    elif wire_type == 2:
                        length, pos = PushFrameCodec._decode_varint(data, pos)
                        pos += length
                    else:
                        pos += 1

            except Exception as e:
                logger.debug(f"解码PushFrame字段时出错: {e}")
                break

        return frame

    @staticmethod
    def _encode_varint(value: int) -> bytes:
        """编码varint"""
        if value < 0:
            value = (1 << 64) + value  # 转换为无符号

        result = bytearray()
        while value > 0x7F:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value & 0x7F)
        return bytes(result)

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

    @staticmethod
    def _encode_string(value: str) -> bytes:
        """编码字符串（长度前缀）"""
        data = value.encode('utf-8')
        return PushFrameCodec._encode_varint(len(data)) + data


class PushFrameFactory:
    """PushFrame工厂类，用于创建各种类型的帧"""

    @staticmethod
    def create_heartbeat() -> bytes:
        """
        创建心跳帧

        Returns:
            bytes: 编码后的心跳帧
        """
        frame = PushFrame(
            payload_type="hb"
        )
        return PushFrameCodec.encode(frame)

    @staticmethod
    def create_ack(internal_ext: str, log_id: Optional[int] = None) -> bytes:
        """
        创建ACK确认帧

        Args:
            internal_ext: internal_ext字符串
            log_id: 消息的log_id

        Returns:
            bytes: 编码后的ACK帧
        """
        # 将internal_ext转换为字节（参考dycast第1004-1015行）
        payload = PushFrameFactory._encode_internal_ext(internal_ext)

        frame = PushFrame(
            payload_type="ack",
            payload=payload,
            log_id=log_id
        )
        return PushFrameCodec.encode(frame)

    @staticmethod
    def _encode_internal_ext(ext: str) -> bytes:
        """
        编码internal_ext为字节

        参考dycast第1004-1015行的getPayload函数

        Args:
            ext: internal_ext字符串

        Returns:
            bytes: 编码后的字节
        """
        arr = bytearray()
        for char in ext:
            index = ord(char)
            if index < 128:
                arr.append(index)
            elif index < 2048:
                arr.append(192 + (index >> 6))
                arr.append(128 + (63 & index))
            elif index < 65536:
                arr.append(224 + (index >> 12))
                arr.append(128 + ((index >> 6) & 63))
                arr.append(128 + (63 & index))
        return bytes(arr)


# 测试代码
if __name__ == "__main__":
    # 测试心跳帧编码
    heartbeat = PushFrameFactory.create_heartbeat()
    print(f"心跳帧长度: {len(heartbeat)}")
    print(f"心跳帧内容(hex): {heartbeat.hex()}")

    # 测试心跳帧解码
    decoded = PushFrameCodec.decode(heartbeat)
    print(f"解码后 payload_type: {decoded.payload_type}")

    # 测试ACK帧编码
    ack = PushFrameFactory.create_ack("test_internal_ext", 12345)
    print(f"\nACK帧长度: {len(ack)}")
    print(f"ACK帧内容(hex): {ack.hex()}")
