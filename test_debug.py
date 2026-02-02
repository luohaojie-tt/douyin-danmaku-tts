"""
调试测试 - 记录前10条消息的详细信息
"""
import asyncio
import sys
import logging
from pathlib import Path

# 配置日志 - 只显示INFO及以上，避免DEBUG刷屏
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.douyin.cookie import CookieManager
from src.douyin.connector_real import DouyinConnectorReal
from src.douyin.parser_real import RealtimeMessageParser
from src.douyin.protobuf import PushFrameCodec


async def test():
    room_id = "168465302284"

    # 加载cookie
    cookie_manager = CookieManager()
    ttwid = cookie_manager.load_from_file()

    print(f"测试直播间: {room_id}")
    print(f"ttwid: {ttwid[:30]}...")
    print()

    # 创建连接器
    connector = DouyinConnectorReal(room_id, ttwid)

    # 连接
    if not await connector.connect():
        print("连接失败")
        return

    print("\n开始分析前10条消息...")
    print("="*80)

    message_count = 0
    chat_count = 0

    async def handle_message(raw_message):
        nonlocal message_count, chat_count
        message_count += 1

        # 只分析前10条
        if message_count <= 10:
            print(f"\n消息 #{message_count}:")

            if isinstance(raw_message, bytes):
                # 解析PushFrame
                frame = PushFrameCodec.decode(raw_message)

                if frame:
                    print(f"  Payload Type: {frame.payload_type}")
                    print(f"  Has Payload: {frame.payload is not None}")
                    print(f"  Log ID: {frame.log_id}")

                    if frame.headers_list:
                        print(f"  Headers:")
                        for key, value in frame.headers_list.items():
                            print(f"    {key}: {value[:50]}...")

                    # 解析payload
                    if frame.payload:
                        need_ack, internal_ext = connector._parse_response_for_ack(frame.payload)
                        print(f"  Need ACK: {need_ack}")
                        if internal_ext:
                            print(f"  Internal Ext: {internal_ext[:50]}...")

                    # 尝试解析为聊天消息
                    parser = RealtimeMessageParser()
                    parsed = parser.parse_message(raw_message)
                    if parsed:
                        print(f"  Message Type: {parsed.method}")
                        if parsed.method == "WebChatMessage":
                            chat_count += 1
                            print(f"  *** 弹幕! ***")
                            print(f"  User: {parsed.user.nickname if parsed.user else 'Unknown'}")
                            print(f"  Content: {parsed.content}")
        elif message_count == 11:
            print("\n...")
            print("(只显示前10条消息的详情)")
            print("="*80)

        # 15秒后退出
        if message_count >= 50:
            print(f"\n达到50条消息，退出")
            await connector.disconnect()

    try:
        # 创建监听任务
        listen_task = asyncio.create_task(connector.listen(handle_message))

        # 等待15秒
        for i in range(15, 0, -1):
            print(f"\r倒计时: {i} 秒", end='', flush=True)
            await asyncio.sleep(1)

        print("\n\n时间到，正在断开连接...")
        await connector.disconnect()

        try:
            await asyncio.wait_for(listen_task, timeout=5)
        except:
            pass

    except Exception as e:
        print(f"\n监听异常: {e}")

    print("\n" + "="*80)
    print(f"测试完成！")
    print(f"总计: {message_count} 条消息")
    print(f"弹幕: {chat_count} 条")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test())
