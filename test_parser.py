#!/usr/bin/env python3
"""
消息解析器测试脚本

测试消息解析功能是否正常工作。
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.douyin.parser import MessageParser, ParsedMessage, UserInfo


def print_section(title: str):
    """Print section title"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def test_parse_test_message():
    """测试解析测试消息"""
    print_section("Test 1: Parse Test Message (Dict)")

    parser = MessageParser()

    # 测试聊天消息
    chat_msg = {
        "method": "WebChatMessage",
        "payload": {
            "user": {
                "nickname": "测试用户",
                "id": "123456789",
                "level": 10
            },
            "content": "主播好厉害！",
            "timestamp": 1706841600
        }
    }

    parsed = parser.parse_test_message(chat_msg)

    if parsed and parsed.method == "WebChatMessage":
        print("[OK] 聊天消息解析成功")
        print(f"  用户: {parsed.user.nickname}")
        print(f"  内容: {parsed.content}")
        print(f"  时间戳: {parsed.timestamp}")
        return True
    else:
        print("[FAIL] 聊天消息解析失败")
        return False


async def test_parse_gift_message():
    """测试解析礼物消息"""
    print_section("Test 2: Parse Gift Message")

    parser = MessageParser()

    gift_msg = {
        "method": "WebGiftMessage",
        "payload": {
            "user": {
                "nickname": "送礼用户",
                "id": "987654321",
                "level": 50
            },
            "gift": {
                "name": "玫瑰",
                "count": 1
            },
            "timestamp": 1706841602
        }
    }

    parsed = parser.parse_test_message(gift_msg)

    if parsed and parsed.method == "WebGiftMessage":
        print("[OK] 礼物消息解析成功")
        print(f"  用户: {parsed.user.nickname}")
        print(f"  礼物: {parsed.gift_name} x{parsed.gift_count}")
        return True
    else:
        print("[FAIL] 礼物消息解析失败")
        return False


async def test_parse_binary_message():
    """测试解析二进制消息"""
    print_section("Test 3: Parse Binary Message")

    parser = MessageParser()

    # 构造测试用的二进制数据（模拟protobuf）
    test_data = b'WebChatMessage\x00\x01\x02\x03\x04\x05'
    test_data += b'\xe4\xb8\xbb\xe6\x92\xad\xe5\xa5\xbd'  # UTF-8编码的"主播好"
    test_data += b'\x00\x00'

    parsed = await parser.parse_message(test_data)

    if parsed:
        print("[OK] 二进制消息解析成功")
        print(f"  类型: {parsed.method}")
        print(f"  内容: {parsed.content}")
        print(f"  原始: {parsed.raw}")
        return True
    else:
        print("[FAIL] 二进制消息解析失败")
        return False


async def test_gzip_decompression():
    """测试gzip解压"""
    print_section("Test 4: Gzip Decompression")

    parser = MessageParser()

    # 创建测试数据并压缩
    original_data = b"Test message data for compression"
    import gzip
    compressed = gzip.compress(original_data)

    print(f"原始数据: {len(original_data)} 字节")
    print(f"压缩后: {len(compressed)} 字节")

    # 测试解压
    decompressed = parser._try_decompress(compressed)

    if decompressed == original_data:
        print("[OK] Gzip解压成功")
        print(f"  解压后: {len(decompressed)} 字节")
        return True
    else:
        print("[FAIL] Gzip解压失败")
        return False


async def test_text_extraction():
    """测试文本提取"""
    print_section("Test 5: Text Extraction from Binary")

    parser = MessageParser()

    # 构造包含中文和英文的二进制数据
    test_data = b'\x00\x01\x02'
    test_data += "主播好厉害！Hello".encode('utf-8')
    test_data += b'\x03\x04\x05'

    text_parts = parser._extract_text(test_data)

    if text_parts:
        print("[OK] 文本提取成功")
        print(f"  提取的文本: {text_parts[:5]}")
        return True
    else:
        print("[FAIL] 文本提取失败")
        return False


async def test_message_type_detection():
    """测试消息类型检测"""
    print_section("Test 6: Message Type Detection")

    parser = MessageParser()

    test_cases = [
        (b'WebChatMessage\x00data', "WebChatMessage"),
        (b'WebGiftMessage\x00data', "WebGiftMessage"),
        (b'WebLiveEndEvent\x00data', "WebLiveEndEvent"),
    ]

    all_passed = True
    for data, expected in test_cases:
        result = parser._detect_message_type(data, [])
        if result == expected:
            print(f"[OK] {expected}: {result}")
        else:
            print(f"[FAIL] 期望 {expected}, 得到 {result}")
            all_passed = False

    return all_passed


async def test_user_info():
    """测试UserInfo数据类"""
    print_section("Test 7: UserInfo DataClass")

    user = UserInfo(
        id="123456",
        nickname="测试用户",
        level=10,
        badge="VIP"
    )

    if user.id == "123456" and user.nickname == "测试用户":
        print("[OK] UserInfo创建成功")
        print(f"  ID: {user.id}")
        print(f"  昵称: {user.nickname}")
        print(f"  等级: {user.level}")
        print(f"  勋章: {user.badge}")
        return True
    else:
        print("[FAIL] UserInfo创建失败")
        return False


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("  Message Parser Test")
    print("=" * 60)

    # Run tests
    results = []
    results.append(await test_parse_test_message())
    results.append(await test_parse_gift_message())
    results.append(await test_parse_binary_message())
    results.append(await test_gzip_decompression())
    results.append(await test_text_extraction())
    results.append(await test_message_type_detection())
    results.append(await test_user_info())

    # Summary
    print_section("Test Summary")

    passed = sum(1 for r in results if r)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n[OK] All tests passed! Parser works correctly")
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")

    print("\nTest completed\n")


if __name__ == "__main__":
    asyncio.run(main())
