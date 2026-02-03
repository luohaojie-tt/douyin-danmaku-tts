"""
使用Playwright监听浏览器实际的HTTP请求
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.douyin.cookie import CookieManager
from playwright.async_api import async_playwright


async def monitor_browser_requests():
    """监听浏览器请求"""

    room_id = "118636942397"

    # 加载cookie
    cookie_manager = CookieManager()
    ttwid = cookie_manager.load_from_file()

    if not ttwid:
        print("无法加载ttwid")
        return

    print("="*60)
    print("监听浏览器HTTP请求")
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

        captured = []

        async def handle_request(request):
            """监听请求"""
            url = request.url
            if 'webcast/im/fetch' in url:
                print(f"\n[REQUEST] {url[:150]}...")
                print(f"Method: {request.method}")
                headers = request.headers
                print(f"Headers: {len(headers)} headers")

        async def handle_response(response):
            """监听响应"""
            url = response.url
            if 'webcast/im/fetch' in url:
                print(f"\n[RESPONSE] Status: {response.status}")
                print(f"URL: {url[:150]}...")

                try:
                    data = await response.body()
                    print(f"Size: {len(data)} bytes")

                    if len(data) > 0:
                        # 保存响应
                        output_file = Path(__file__).parent / "browser_response.raw"
                        with open(output_file, 'wb') as f:
                            f.write(data)
                        print(f"Saved to: {output_file}")

                        # 尝试解析
                        import gzip
                        try:
                            decompressed = gzip.decompress(data)
                            print(f"Decompressed: {len(decompressed)} bytes")

                            text = decompressed.decode('utf-8', errors='ignore')
                            if 'WebcastChatMessage' in text:
                                print("[FOUND] WebcastChatMessage detected!")

                                # 使用我们的parser解析
                                from src.douyin.parser_http import HTTPResponseParser
                                parser = HTTPResponseParser()
                                messages = parser.parse_response(decompressed)
                                print(f"\nParsed {len(messages)} messages:")
                                for msg in messages[:5]:
                                    if msg.method == "WebChatMessage":
                                        user = msg.user.nickname if msg.user else "未知"
                                        print(f"  [{user}]: {msg.content}")

                        except Exception as e:
                            print(f"Decompress error: {e}")

                except Exception as e:
                    print(f"Error reading response: {e}")

                captured.append(url)

        page.on("request", handle_request)
        page.on("response", handle_response)

        # 访问直播间
        url = f"https://live.douyin.com/{room_id}"
        print(f"访问直播间: {url}\n")

        await page.goto(url, wait_until='domcontentloaded', timeout=30000)

        # 等待捕获请求
        print("等待捕获im/fetch请求（15秒）...")
        for i in range(15):
            await asyncio.sleep(1)
            if captured:
                print(f"\n已捕获请求！（{i+1}秒）")
                break
            print(f"  {i+1}/15 秒...")

        await page.close()
        await context.close()
        await browser.close()

        print("\n" + "="*60)
        print("监听完成")
        print("="*60)

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await playwright.stop()


if __name__ == "__main__":
    try:
        asyncio.run(monitor_browser_requests())
    except KeyboardInterrupt:
        print("\n\n用户中断")
