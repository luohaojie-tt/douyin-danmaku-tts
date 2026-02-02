"""
快速测试脚本 - 20秒后自动退出
"""
import asyncio
import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,  # 启用DEBUG级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.douyin.cookie import CookieManager
from src.douyin.connector_real import DouyinConnectorReal
from src.douyin.parser_real import RealtimeMessageParser


async def test():
    room_id = "168465302284"

    # 加载cookie
    cookie_manager = CookieManager()
    ttwid = cookie_manager.load_from_file()

    print(f"测试直播间: {room_id}")
    print(f"ttwid: {ttwid[:30]}...")

    # 创建连接器和解析器
    connector = DouyinConnectorReal(room_id, ttwid)
    parser = RealtimeMessageParser()

    # 连接
    if not await connector.connect():
        print("连接失败")
        return

    print("\n开始监听20秒...\n")
    print("【提示】如果这个时间段没有弹幕，可以:")
    print("  1. 尝试其他时间段（晚上8-11点通常是高峰期）")
    print("  2. 尝试其他更活跃的直播间")
    print()

    message_count = 0
    chat_count = 0

    async def handle_message(raw_message):
        nonlocal message_count, chat_count
        message_count += 1

        if isinstance(raw_message, bytes):
            parsed = parser.parse_message(raw_message)

            if parsed and parsed.method == "WebChatMessage":
                chat_count += 1
                print(f"[弹幕 #{chat_count}] {parsed.user.nickname if parsed.user else 'Unknown'}: {parsed.content}")

    try:
        # 创建监听任务
        listen_task = asyncio.create_task(connector.listen(handle_message))

        # 等待20秒
        for i in range(20, 0, -1):
            print(f"\r倒计时: {i} 秒 (已接收: {message_count} 条消息, {chat_count} 条弹幕)", end='')
            await asyncio.sleep(1)

        print("\n\n时间到，正在断开连接...")

        # 断开连接
        await connector.disconnect()

        # 等待listen任务结束
        try:
            await asyncio.wait_for(listen_task, timeout=5)
        except asyncio.TimeoutError:
            print("监听任务超时")
        except:
            pass

    except Exception as e:
        print(f"\n监听异常: {e}")

    print("\n" + "="*60)
    print(f"测试完成！")
    print(f"总计: {message_count} 条消息")
    print(f"弹幕: {chat_count} 条")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test())
