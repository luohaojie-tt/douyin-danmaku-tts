"""
从网络请求中提取room_id
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.douyin.cookie import CookieManager
from playwright.async_api import async_playwright


async def get_room_id_from_network():
    """从网络请求中提取room_id"""

    room_id = "118636942397"

    # 加载cookie
    cookie_manager = CookieManager()
    ttwid = cookie_manager.load_from_file()

    if not ttwid:
        print("[错误] 无法加载ttwid")
        return

    print("="*60)
    print("  从网络请求中提取room_id")
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

        # 存储room_id
        found_room_id = []

        # 监听请求
        def handle_request(request):
            url = request.url

            # 检查是否是 im/fetch 请求
            if 'webcast/im/fetch' in url:
                # 从URL中提取room_id
                import re
                match = re.search(r'room_id=(\d+)', url)
                if match:
                    found_room_id.append(match.group(1))
                    print(f"[找到] room_id: {match.group(1)}")

        page.on("request", handle_request)

        # 访问直播间
        url = f"https://live.douyin.com/{room_id}"
        print(f"访问直播间: {url}")
        print("\n正在监听网络请求...\n")

        await page.goto(url, wait_until='domcontentloaded', timeout=30000)

        # 等待捕获请求
        print("等待捕获im/fetch请求（最多15秒）...")
        for i in range(15):
            await asyncio.sleep(1)
            if found_room_id:
                break
            print(f"  {i+1}/15 秒...")

        # 关闭页面
        await page.close()
        await context.close()
        await browser.close()

        if found_room_id:
            room_id_value = found_room_id[0]

            print("\n" + "="*60)
            print(f"成功提取room_id: {room_id_value}")

            # 保存到文件
            output_file = Path(__file__).parent / "current_room_id.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(room_id_value)
            print(f"已保存到: {output_file}")
            print("="*60)

            return room_id_value
        else:
            print("\n[失败] 未找到im/fetch请求")
            print("可能的原因:")
            print("1. 直播间已结束")
            print("2. 页面加载超时")
            print("3. 网络问题")
            return None

    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        await playwright.stop()


if __name__ == "__main__":
    try:
        asyncio.run(get_room_id_from_network())
    except KeyboardInterrupt:
        print("\n\n用户中断")
