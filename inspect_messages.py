"""
检查WebSocket消息内容
查看是否有弹幕数据
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.douyin.cookie import CookieManager
from src.douyin.connector_real import DouyinConnectorReal
from src.douyin.parser_real import RealtimeMessageParser


async def inspect_messages():
    room_id = "253247782652"

    # 加载cookie
    cookie_manager = CookieManager()
    ttwid = cookie_manager.load_from_file()

    print(f"检查直播间: {room_id}")
    print(f"ttwid: {ttwid[:30]}...")

    # 创建连接器和解析器
    connector = DouyinConnectorReal(room_id, ttwid)
    parser = RealtimeMessageParser()

    # 连接
    if not await connector.connect():
        print("连接失败")
        return

    print("\n开始检查消息...\n")
    print("="*60)

    message_count = 0
    chat_count = 0

    async def handle_message(raw_message):
        nonlocal message_count, chat_count
        message_count += 1

        if isinstance(raw_message, bytes):
            parsed = parser.parse_message(raw_message)

            print(f"\n消息 #{message_count}")
            print(f"  类型: {parsed.method}")

            # 如果不是Unknown，打印更多信息
            if parsed.method != "Unknown":
                if parsed.user:
                    print(f"  用户: {parsed.user.nickname}")
                if parsed.content:
                    print(f"  内容: {parsed.content}")
                    chat_count += 1
                    print(f"  *** 这是第{chat_count}条可能的聊天/弹幕消息 ***")

            # 每20条消息检查一次
            if message_count >= 100:
                print(f"\n已检查100条消息，找到 {chat_count} 条可能的聊天消息")
                await connector.disconnect()

    try:
        await connector.listen(handle_message)
    except Exception as e:
        print(f"\n监听结束: {e}")

    print("\n" + "="*60)
    print(f"总计: {message_count} 条消息, {chat_count} 条聊天消息")


if __name__ == "__main__":
    asyncio.run(inspect_messages())
