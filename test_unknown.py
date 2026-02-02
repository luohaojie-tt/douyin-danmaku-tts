"""
分析Unknown消息的详细内容
"""
import asyncio
import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.douyin.cookie import CookieManager
from src.douyin.connector_real import DouyinConnectorReal
from src.douyin.parser_real import RealtimeMessageParser
from src.douyin.protobuf import PushFrameCodec
import gzip


async def test():
    room_id = "168465302284"

    cookie_manager = CookieManager()
    ttwid = cookie_manager.load_from_file()

    print(f"测试直播间: {room_id}")
    print()

    connector = DouyinConnectorReal(room_id, ttwid)

    if not await connector.connect():
        print("连接失败")
        return

    print("\n开始分析消息内容...")
    print("="*80)

    message_count = 0

    async def handle_message(raw_message):
        nonlocal message_count
        message_count += 1

        if message_count > 5:  # 只分析前5条
            return

        print(f"\n消息 #{message_count}:")
        print("-"*80)

        if isinstance(raw_message, bytes):
            frame = PushFrameCodec.decode(raw_message)

            if frame and frame.payload:
                # 解压gzip
                try:
                    if frame.headers_list and frame.headers_list.get('compress_type') == 'gzip':
                        decompressed = gzip.decompress(frame.payload)
                        print(f"  [Gzip解压] 原始大小: {len(frame.payload)}, 解压后: {len(decompressed)}")

                        # 提取所有字符串
                        strings = extract_all_strings(decompressed)
                        print(f"  [字符串] 提取到 {len(strings)} 个字符串:")

                        for i, s in enumerate(strings[:20]):  # 只显示前20个
                            text = s.get('text', '')
                            if text:
                                preview = text[:100]
                                if len(text) > 100:
                                    preview += "..."
                                print(f"    [{i+1}] Field {s['field']}: {preview}")

                                # 检查是否是弹幕相关的关键词
                                if any(keyword in text for keyword in ['Chat', 'chat', 'user', 'content', 'message', 'WebcastChatMessage']):
                                    print(f"         ^^^ 可能是聊天相关!")

                except Exception as e:
                    print(f"  解压失败: {e}")

        if message_count >= 5:
            print("\n...")
            print("(只显示前5条消息)")
            await connector.disconnect()

    try:
        listen_task = asyncio.create_task(connector.listen(handle_message))
        await asyncio.sleep(10)
        await connector.disconnect()
        try:
            await asyncio.wait_for(listen_task, timeout=5)
        except:
            pass
    except Exception as e:
        print(f"\n监听异常: {e}")

    print("\n" + "="*80)
    print(f"分析完成！")


def extract_all_strings(data: bytes):
    """提取所有字符串"""
    strings = []
    pos = 0

    while pos < len(data):
        try:
            tag, pos = read_varint(data, pos)
            field_number = tag >> 3
            wire_type = tag & 0x07

            if wire_type == 2:
                length, pos = read_varint(data, pos)
                if pos + length > len(data):
                    break
                value = data[pos:pos + length]
                pos += length

                try:
                    text = value.decode('utf-8', errors='ignore')
                    if 1 <= len(text) <= 200:
                        printable_count = sum(1 for c in text if c.isprintable())
                        if printable_count > len(text) * 0.3:
                            strings.append({'field': field_number, 'text': text})
                except:
                    pass
            elif wire_type == 0:
                _, pos = read_varint(data, pos)
            else:
                pos += 1
        except:
            break

    return strings


def read_varint(data: bytes, pos: int):
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


if __name__ == "__main__":
    asyncio.run(test())
