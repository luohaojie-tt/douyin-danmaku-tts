#!/usr/bin/env python3
"""
测试真实的抖音WebSocket连接
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.douyin.connector import DouyinConnector, DouyinConnectorMock
from src.douyin.cookie import CookieManager


async def test_real_connection():
    """测试真实连接"""
    print("=" * 60)
    print("测试真实的抖音WebSocket连接")
    print("=" * 60)

    # Load cookie
    cookie_mgr = CookieManager()
    ttwid = cookie_mgr.load_from_file()

    if not ttwid:
        print("ERROR: 无法加载ttwid")
        return False

    print(f"[OK] ttwid加载成功 (长度: {len(ttwid)})")

    # Create connector
    connector = DouyinConnector(
        room_id="728804746624",
        ttwid=ttwid
    )

    # Try to connect
    print("\n尝试连接到直播间...")
    connected = await connector.connect()

    if connected:
        print(f"[OK] 连接成功！")
        print(f"  服务器: {connector.WS_SERVERS[0]}")

        # Listen for a few seconds
        print("\n监听消息（5秒）...\n")

        message_count = 0

        async def count_message(msg):
            nonlocal message_count
            message_count += 1
            print(f"收到消息 #{message_count}:")
            print(f"  类型: {msg.get('type')}")
            print(f"  长度: {msg.get('raw_length', 'N/A')}")
            if msg.get('raw'):
                print(f"  预览: {msg.get('preview', 'N/A')[:40]}...")
            print()

        try:
            # Listen for 5 seconds
            await asyncio.wait_for(connector.listen(count_message), timeout=5.0)
        except asyncio.TimeoutError:
            pass

        print(f"\n[OK] 在5秒内收到 {message_count} 条消息")

        # Disconnect
        await connector.disconnect()
        print("[OK] 已断开连接")

        return True
    else:
        print("[FAIL] 连接失败")
        return False


async def test_mock_connection():
    """测试Mock连接器"""
    print("\n" + "=" * 60)
    print("测试Mock连接器")
    print("=" * 60)

    connector = DouyinConnectorMock(
        room_id="728804746624",
        ttwid="mock_ttwid"
    )

    print("\n模拟连接...")
    connected = await connector.connect()

    if connected:
        print("[OK] Mock connection successful")

        print("\nReceiving mock messages...")
        message_count = 0

        async def count_message(msg):
            nonlocal message_count
            message_count += 1
            print(f"Message #{message_count}:")
            print(f"  User: {msg.get('user', {}).get('nickname')}")
            print(f"  Content: {msg.get('content')}")
            print()

        await connector.listen(count_message)

        print(f"\n[OK] Received {message_count} mock messages")

        await connector.disconnect()
        print("[OK] Mock disconnected")

        return True
    else:
        print("[FAIL] Mock connection failed")
        return False


async def main():
    print("\n抖音连接器测试\n")

    # Test 1: Mock connection
    mock_ok = await test_mock_connection()

    # Test 2: Real connection
    print("\n" + "=" * 60)
    real_ok = await test_real_connection()

    # Summary
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"Mock连接器: {'[OK] 通过' if mock_ok else '[FAIL] 失败'}")
    print(f"真实连接器: {'[OK] 通过' if real_ok else '[FAIL] 失败'}")
    print()

    if real_ok:
        print("🎉 成功！WebSocket连接器工作正常！")
        print("注意：消息解析将在步骤1.7完成")
    elif mock_ok:
        print("[WARN] Mock连接器工作正常")
        print("真实连接需要进一步调试或等待步骤1.7完成protobuf解析")
    else:
        print("[ERROR] 连接器需要修复")


if __name__ == "__main__":
    asyncio.run(main())
