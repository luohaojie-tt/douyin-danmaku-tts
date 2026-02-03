"""
调试room_id提取
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.douyin.cookie import CookieManager
from playwright.async_api import async_playwright


async def debug_room_id():
    """调试room_id提取"""

    room_id = "118636942397"

    # 加载cookie
    cookie_manager = CookieManager()
    ttwid = cookie_manager.load_from_file()

    if not ttwid:
        print("无法加载ttwid")
        return

    print("="*60)
    print("调试room_id提取")
    print("="*60)
    print(f"房间号: {room_id}")
    print()

    playwright = await async_playwright().start()

    try:
        # 连接Chrome
        print("连接Chrome CDP...")
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

        # 访问直播间
        url = f"https://live.douyin.com/{room_id}"
        print(f"访问直播间: {url}")

        await page.goto(url, wait_until='domcontentloaded', timeout=30000)

        # 等待页面加载
        print("等待页面加载...")
        await asyncio.sleep(5)

        # 检查页面标题
        title = await page.title()
        print(f"页面标题: {title}")

        # 检查URL
        current_url = page.url
        print(f"当前URL: {current_url}")

        # 尝试提取room_id的多个方法
        print("\n尝试提取room_id...")

        # 方法1: 从__pace_f数组提取
        try:
            pace_result = await page.evaluate('''() => {
                if (window.__pace_f) {
                    // 遍历整个数组
                    for (let i = 0; i < window.__pace_f.length; i++) {
                        if (window.__pace_f[i]) {
                            // 可能是数组或字符串
                            const items = Array.isArray(window.__pace_f[i]) ? window.__pace_f[i] : [window.__pace_f[i]];
                            for (const item of items) {
                                if (typeof item === 'string') {
                                    const match = item.match(/"roomId":"?(\\d+)"?/);
                                    if (match) return { found: true, roomId: match[1], index: i };
                                }
                            }
                        }
                    }
                }
                return { found: false };
            }''')

            if pace_result and pace_result.get('found'):
                print(f"[OK] Method 1: room_id = {pace_result['roomId']}, at __pace_f[{pace_result['index']}]")
            else:
                print("Method 1 failed: roomId not found")
        except Exception as e:
            print(f"方法1失败: {e}")

        # 方法2: 从__INITIAL_STATE__提取
        try:
            initial_state = await page.evaluate('''() => {
                if (window.__INITIAL_STATE__) {
                    return window.__INITIAL_STATE__;
                }
                return null;
            }''')
            if initial_state:
                print(f"__INITIAL_STATE__ 存在，长度: {len(initial_state)}")
        except Exception as e:
            print(f"方法2失败: {e}")

        # 方法3: 从URL提取
        if 'room_id=' in current_url:
            import re
            match = re.search(r'room_id=(\d+)', current_url)
            if match:
                print(f"✅ 方法3成功: room_id = {match.group(1)}")

        # 方法4: 检查是否有"直播结束"提示
        try:
            has_ended = await page.evaluate('''() => {
                // 查找可能的"直播结束"文本
                const body = document.body.innerText;
                return body.includes('直播结束') || body.includes('主播已离线') || body.includes('直播已结束');
            }''')
            if has_ended:
                print("\n[WARNING] Detected 'live ended' message")
        except:
            pass

        # 截图
        screenshot_path = Path(__file__).parent / "debug_screenshot.png"
        await page.screenshot(path=str(screenshot_path))
        print(f"\n页面截图已保存: {screenshot_path}")

        await page.close()
        await context.close()
        await browser.close()

        print("\n" + "="*60)
        print("调试完成")
        print("="*60)

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await playwright.stop()


if __name__ == "__main__":
    try:
        asyncio.run(debug_room_id())
    except KeyboardInterrupt:
        print("\n\n用户中断")
