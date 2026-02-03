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
    room_id = "168465302284"  # 活跃直播间：2489人

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
    print("【注意】我会显示所有消息的详细内容，包括Unknown类型")
    print("="*60)

    message_count = 0
    chat_count = 0
    unknown_detail_count = 0

    async def handle_message(raw_message):
        nonlocal message_count, chat_count, unknown_detail_count
        message_count += 1

        if isinstance(raw_message, bytes):
            parsed = parser.parse_message(raw_message)

            print(f"\n{'='*60}")
            print(f"消息 #{message_count}")
            print(f"  类型: {parsed.method}")

            # 调试：检查raw_strings属性
            has_raw_strings = hasattr(parsed, 'raw_strings')
            raw_strings_value = getattr(parsed, 'raw_strings', None)
            raw_strings_count = len(raw_strings_value) if raw_strings_value else 0

            print(f"  [DEBUG] has_raw_strings: {has_raw_strings}, count: {raw_strings_count}")

            # 如果不是Unknown，打印更多信息
            if parsed.method != "Unknown":
                if parsed.user:
                    print(f"  [USER] 用户: {parsed.user.nickname}")
                if parsed.content:
                    print(f"  [CHAT] 内容: {parsed.content}")
                    chat_count += 1
                    print(f"  *** FOUND: 这是第{chat_count}条聊天/弹幕消息 ***")
            else:
                # 对于Unknown类型，显示提取的字符串信息
                if has_raw_strings and raw_strings_value:
                    print(f"  [Unknown] 提取到 {len(raw_strings_value)} 个字符串:")
                    for i, s in enumerate(raw_strings_value[:10]):  # 只显示前10个
                        text = s.get('text', '')
                        if text:
                            print(f"     [{i+1}] {text[:100]}")
                            if len(text) > 100:
                                print(f"         ... (总长度: {len(text)})")
                    unknown_detail_count += 1
                else:
                    print(f"  [Unknown] 没有提取到字符串数据")

            # 检查50条消息就够了
            if message_count >= 50:
                print(f"\n{'='*60}")
                print(f"已检查50条消息")
                print(f"  - 聊天/弹幕消息: {chat_count} 条")
                print(f"  - Unknown消息有详细信息: {unknown_detail_count} 条")
                print(f"{'='*60}")
                await connector.disconnect()

    try:
        await connector.listen(handle_message)
    except Exception as e:
        print(f"\n监听结束: {e}")

    print("\n" + "="*60)
    print(f"检查完成！")
    print(f"总计: {message_count} 条消息")
    print(f"  - 聊天/弹幕消息: {chat_count} 条")
    print(f"  - Unknown消息有详细信息: {unknown_detail_count} 条")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(inspect_messages())
