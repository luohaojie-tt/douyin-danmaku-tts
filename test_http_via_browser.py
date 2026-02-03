"""
使用浏览器直接请求im/fetch API并获取响应
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.douyin.cookie import CookieManager
from playwright.async_api import async_playwright
from src.douyin.parser_v2 import ImprovedMessageParser


async def test_http_via_browser():
    """使用浏览器请求API"""

    room_id = "118636942397"

    # 加载cookie
    cookie_manager = CookieManager()
    ttwid = cookie_manager.load_from_file()

    if not ttwid:
        print("[错误] 无法加载ttwid")
        return

    print("="*60)
    print("  使用浏览器请求im/fetch API")
    print("="*60)
    print(f"房间号: {room_id}")
    print()

    playwright = await async_playwright().start()

    try:
        # 连接Chrome
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")

        # 创建context
        context = await browser.new_context()

        # 设置cookie
        await context.add_cookies([{
            'name': 'ttwid',
            'value': ttwid,
            'domain': '.douyin.com',
            'path': '/'
        }])

        # 创建页面
        page = await context.new_page()

        # 监听响应
        message_count = 0
        danmaku_count = 0
        parser = ImprovedMessageParser()

        async def handle_response(response):
            nonlocal message_count, danmaku_count

            # 只关心 im/fetch 请求
            if 'webcast/im/fetch' not in response.url:
                return

            message_count += 1

            print(f"\n[响应 #{message_count}]")
            print(f"URL: {response.url[:100]}...")
            print(f"状态: {response.status}")

            try:
                # 获取响应数据
                data = await response.body()

                print(f"大小: {len(data)} bytes")

                if len(data) > 0:
                    # 解析消息
                    parsed = parser.parse_message(data)

                    print(f"消息类型: {parsed.method}")

                    if parsed.method == "WebChatMessage" and parsed.content:
                        danmaku_count += 1
                        user = parsed.user.nickname if parsed.user else "未知用户"
                        print(f">>> [弹幕 #{danmaku_count}] {user}: {parsed.content}")
                else:
                    print("[警告] 响应为空")

            except Exception as e:
                print(f"处理失败: {e}")

        page.on("response", handle_response)

        # 访问直播间
        url = f"https://live.douyin.com/{room_id}"
        print(f"访问直播间: {url}")
        print("\n开始监听im/fetch响应（30秒）...")
        print("="*60)

        await page.goto(url, wait_until='domcontentloaded', timeout=30000)

        # 等待30秒，收集响应
        await asyncio.sleep(30)

        # 关闭
        await page.close()
        await context.close()
        await browser.close()

        print("\n" + "="*60)
        print("测试总结:")
        print(f"  im/fetch请求数: {message_count}")
        print(f"  弹幕数: {danmaku_count}")
        print("="*60)

    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()

    finally:
        await playwright.stop()


if __name__ == "__main__":
    try:
        asyncio.run(test_http_via_browser())
    except KeyboardInterrupt:
        print("\n\n用户中断")
