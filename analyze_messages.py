"""
详细分析所有收到的消息 - 显示完整内容
"""
import asyncio
import sys
import logging
import gzip
from pathlib import Path

logging.basicConfig(
    level=logging.WARNING,  # 只显示WARNING及以上，减少日志噪音
    format='%(levelname)s - %(message)s'
)

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.douyin.cookie import CookieManager
from src.douyin.connector_real import DouyinConnectorReal
from src.douyin.parser_real import RealtimeMessageParser
from src.douyin.protobuf import PushFrameCodec


def extract_and_display_strings(payload: bytes, msg_num: int):
    """提取并显示payload中的所有字符串"""
    try:
        # 尝试解压gzip
        try:
            decompressed = gzip.decompress(payload)
            print(f"  [解压后] {len(decompressed)} 字节")
            data = decompressed
        except:
            print(f"  [未压缩] {len(payload)} 字节")
            data = payload

        # 提取所有字符串
        strings = []
        pos = 0

        while pos < len(data):
            try:
                # 读取varint tag
                tag = 0
                shift = 0
                while pos < len(data):
                    byte = data[pos]
                    pos += 1
                    tag |= (byte & 0x7F) << shift
                    if not (byte & 0x80):
                        break
                    shift += 7

                field_number = tag >> 3
                wire_type = tag & 0x07

                if wire_type == 2:  # length-delimited
                    # 读取长度
                    length = 0
                    shift = 0
                    while pos < len(data):
                        byte = data[pos]
                        pos += 1
                        length |= (byte & 0x7F) << shift
                        if not (byte & 0x80):
                            break
                        shift += 7

                    if pos + length > len(data):
                        break

                    value = data[pos:pos + length]
                    pos += length

                    # 尝试解码为字符串
                    try:
                        text = value.decode('utf-8', errors='ignore')
                        if 1 <= len(text) <= 500:  # 增加长度限制
                            # 只显示可打印字符较多的字符串
                            printable = sum(1 for c in text if c.isprintable() or c in '\n\r\t')
                            if printable > len(text) * 0.2:  # 降低阈值
                                strings.append({
                                    'field': field_number,
                                    'length': len(text),
                                    'text': text
                                })
                    except:
                        pass

                elif wire_type == 0:  # varint
                    # 跳过varint
                    while pos < len(data):
                        byte = data[pos]
                        pos += 1
                        if not (byte & 0x80):
                            break
                else:
                    # 跳过其他类型
                    pos += 1

            except:
                break

        # 显示字符串
        if strings:
            print(f"  提取到 {len(strings)} 个字符串:")
            for i, s in enumerate(strings):
                text = s['text']
                # 截断过长的字符串
                if len(text) > 150:
                    text = text[:150] + f"...(总长度:{len(text)})"

                print(f"    [{i+1}] 字段{s['field']} (长度{s['length']}): {text}")

                # 高亮显示可能包含弹幕的字符串
                if any(keyword in text.lower() for keyword in ['chat', 'content', 'user', 'nickname', 'message']):
                    print(f"         ^^^ 可能包含弹幕/用户信息!")
        else:
            print(f"  未提取到字符串")

    except Exception as e:
        print(f"  解析失败: {e}")


async def analyze():
    room_id = "168465302284"

    cookie_manager = CookieManager()
    ttwid = cookie_manager.load_from_file()

    print("="*80)
    print(f"分析直播间: {room_id}")
    print(f"ttwid: {ttwid[:30]}...")
    print("="*80)
    print()

    connector = DouyinConnectorReal(room_id, ttwid)

    if not await connector.connect():
        print("连接失败")
        return

    print("\n开始接收并分析所有消息...")
    print("="*80)
    print()

    message_count = 0
    messages_data = []

    async def handle_message(raw_message):
        nonlocal message_count
        message_count += 1

        print(f"\n{'='*80}")
        print(f"消息 #{message_count}")
        print(f"{'='*80}")

        if isinstance(raw_message, bytes):
            # 解析PushFrame
            frame = PushFrameCodec.decode(raw_message)

            if frame:
                print(f"Payload Type: {frame.payload_type}")
                print(f"Log ID: {frame.log_id}")

                if frame.headers_list:
                    print(f"\nHeaders:")
                    for key, value in frame.headers_list.items():
                        if len(value) > 100:
                            value = value[:100] + "..."
                        print(f"  {key}: {value}")

                if frame.payload:
                    print(f"\nPayload 大小: {len(frame.payload)} 字节")
                    print(f"\n详细内容:")
                    extract_and_display_strings(frame.payload, message_count)

                # 尝试用parser识别
                parser = RealtimeMessageParser()
                parsed = parser.parse_message(raw_message)
                if parsed:
                    print(f"\nParser 识别类型: {parsed.method}")
                    if parsed.user:
                        print(f"  用户: {parsed.user.nickname}")
                    if parsed.content:
                        print(f"  内容: {parsed.content}")
                        print(f"\n  *** 这是一个聊天消息！***")

        # 只分析前20条详细内容
        if message_count >= 20:
            print(f"\n...")
            print("(前20条已详细分析，后续只统计)")
            await connector.disconnect()

    try:
        listen_task = asyncio.create_task(connector.listen(handle_message))

        # 等待15秒
        await asyncio.sleep(15)

        print(f"\n\n时间到，正在断开...")
        await connector.disconnect()

        try:
            await asyncio.wait_for(listen_task, timeout=5)
        except:
            pass

    except Exception as e:
        print(f"\n异常: {e}")

    print(f"\n{'='*80}")
    print(f"分析完成！")
    print(f"总计接收: {message_count} 条消息")
    print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(analyze())
