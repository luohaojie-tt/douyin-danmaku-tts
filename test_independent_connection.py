"""
使用已知的roomId和uniqueId测试独立WebSocket连接
"""
import asyncio
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

from src.douyin.cookie import CookieManager
from src.douyin.connector_real import DouyinConnectorReal


async def test_with_known_values():
    """使用已知的roomId和uniqueId进行测试"""

    print("="*60)
    print("使用已提取的值进行独立连接测试")
    print("="*60)

    # 已知值（从pace_data_full.json提取）
    ROOM_ID = "168465302284"  # 直播间ID
    REAL_ROOM_ID = "7602221887833574184"  # 真实的roomId
    UNIQUE_ID = "7495056930692580904"  # uniqueId

    print(f"\n测试参数:")
    print(f"  room_id: {ROOM_ID}")
    print(f"  real_room_id: {REAL_ROOM_ID}")
    print(f"  unique_id: {UNIQUE_ID}")

    # 获取ttwid
    cookie_manager = CookieManager()
    ttwid = cookie_manager.load_from_file()
    print(f"  ttwid: {ttwid[:30]}...")

    # 创建连接器
    connector = DouyinConnectorReal(ROOM_ID, ttwid)

    # 手动设置已知值
    connector.real_room_id = REAL_ROOM_ID
    connector.unique_id = UNIQUE_ID

    # 生成IM初始化参数
    import time
    now_ms = int(time.time() * 1000)
    connector.im_cursor = f"t-{now_ms}_r-{REAL_ROOM_ID}_d-1_u-1"
    connector.im_internal_ext = f"internal_src:dim|wss_push_room_id:{REAL_ROOM_ID}|wss_push_did:{UNIQUE_ID}|first_req_ms:{now_ms}|fetch_time:{now_ms}|seq:1|wss_info:0-{now_ms}-0-0"

    print(f"\n生成的参数:")
    print(f"  cursor: {connector.im_cursor[:80]}...")
    print(f"  internal_ext: {connector.im_internal_ext[:80]}...")

    # 尝试直接连接WebSocket（跳过Playwright部分）
    print("\n" + "="*60)
    print("尝试直接连接WebSocket...")
    print("="*60)

    # 我们需要先生成signature
    # 但是signature需要通过Playwright获取
    # 所以这个测试还是需要Playwright

    # 让我们修改一下：只运行_connect_websocket部分
    # 为此，我们需要先设置signature

    print("\n注意：这个测试需要signature，必须通过Playwright获取")
    print("让我们先运行一个简化的版本，只获取signature")

    # 使用Node.js获取signature
    try:
        import subprocess
        import json

        print("\n使用Node.js获取signature...")
        result = subprocess.run(
            ["node", "tools/signature.js", ROOM_ID, UNIQUE_ID],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            connector.signature = data.get('signature')
            print(f"signature: {connector.signature[:30] if connector.signature else 'N/A'}...")
        else:
            print(f"获取signature失败: {result.stderr}")
            connector.signature = None

        if connector.signature:
            print("\n现在尝试连接WebSocket...")
            success = await connector._connect_websocket()

            if success:
                print("\n✓ WebSocket连接成功!")

                # 监听一段时间看看是否收到弹幕
                print("\n监听消息（30秒）...")

                message_count = 0
                danmaku_count = 0

                async def count_messages(raw_message):
                    nonlocal message_count, danmaku_count
                    message_count += 1

                    # 尝试解析消息
                    if isinstance(raw_message, bytes):
                        from src.douyin.protobuf import PushFrameCodec
                        frame = PushFrameCodec.decode(raw_message)
                        if frame and frame.payload:
                            from src.douyin.parser_real import DouyinParserReal
                            messages = DouyinParserReal.parse_payload(frame.payload)
                            for msg in messages:
                                if msg['method'] == 'WebcastChatMessage':
                                    danmaku_count += 1
                                    print(f"  [弹幕] {msg.get('content', 'N/A')}")

                try:
                    await asyncio.wait_for(
                        connector.listen(count_messages),
                        timeout=30
                    )
                except asyncio.TimeoutError:
                    pass

                print(f"\n统计:")
                print(f"  总消息数: {message_count}")
                print(f"  弹幕数: {danmaku_count}")

                if danmaku_count > 0:
                    print("\n✓✓✓ 成功收到弹幕!")
                else:
                    print("\n✗ 未收到弹幕")

            else:
                print("\n✗ WebSocket连接失败")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()

    print("\n测试完成")


if __name__ == "__main__":
    asyncio.run(test_with_known_values())
