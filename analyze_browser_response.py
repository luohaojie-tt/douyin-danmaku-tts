"""
分析浏览器捕获的响应数据
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))


def analyze_response():
    """分析响应数据"""

    response_file = Path(__file__).parent / "browser_response.raw"

    if not response_file.exists():
        print(f"文件不存在: {response_file}")
        return

    with open(response_file, 'rb') as f:
        data = f.read()

    print("="*60)
    print("分析浏览器响应数据")
    print("="*60)
    print(f"文件大小: {len(data)} bytes")
    print()

    # 检查开头
    print("前16字节(hex):", data[:16].hex())
    print("前16字节(dec):", list(data[:16]))
    print()

    # 尝试直接解码
    try:
        text = data.decode('utf-8', errors='ignore')
        print("直接解码前500字符:")
        print(text[:500])
        print()

        # 查找关键字
        if 'WebcastChatMessage' in text:
            print("[OK] 找到 WebcastChatMessage")
        if 'nickname' in text:
            print("[OK] 找到 nickname")
        if 'content' in text:
            print("[OK] 找到 content")
        print()

    except Exception as e:
        print(f"解码失败: {e}")
        print()

    # 使用parser解析
    from src.douyin.parser_http import HTTPResponseParser
    parser = HTTPResponseParser()

    print("使用HTTPResponseParser解析...")
    messages = parser.parse_response(data)
    print(f"解析出 {len(messages)} 条消息")
    print()

    # 打印前5条聊天消息
    chat_count = 0
    for msg in messages:
        if msg.method == "WebChatMessage" and msg.content:
            chat_count += 1
            user = msg.user.nickname if msg.user else "未知"
            print(f"#{chat_count} [{user}]: {msg.content}")

            if chat_count >= 10:
                break

    print()
    print("="*60)
    print(f"总共 {chat_count} 条聊天消息")
    print("="*60)


if __name__ == "__main__":
    analyze_response()
