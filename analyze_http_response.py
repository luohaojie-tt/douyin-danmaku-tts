"""
分析im/fetch响应数据格式
"""

import asyncio
import sys
import gzip
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.douyin.cookie import CookieManager
from playwright.async_api import async_playwright


async def analyze_http_response():
    """分析响应数据"""

    room_id = "118636942397"

    # 加载cookie
    cookie_manager = CookieManager()
    ttwid = cookie_manager.load_from_file()

    if not ttwid:
        print("[错误] 无法加载ttwid")
        return

    print("="*60)
    print("  分析im/fetch响应数据")
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

        # 标记是否已保存
        saved = False

        async def handle_response(response):
            nonlocal saved

            # 只关心第一个 im/fetch 响应
            if 'webcast/im/fetch' not in response.url or saved:
                return

            print(f"[响应] URL: {response.url[:80]}...")
            print(f"[响应] 状态: {response.status}")

            try:
                # 获取响应数据
                data = await response.body()

                print(f"[响应] 大小: {len(data)} bytes")
                print()

                # 保存原始数据
                output_file = Path(__file__).parent / "im_fetch_response.raw"
                with open(output_file, 'wb') as f:
                    f.write(data)
                print(f"[保存] 原始数据已保存到: {output_file}")

                # 尝试解压gzip
                try:
                    decompressed = gzip.decompress(data)
                    print(f"[解压] 成功！解压后大小: {len(decompressed)} bytes")

                    # 保存解压后的数据
                    output_file_dec = Path(__file__).parent / "im_fetch_response_decompressed.raw"
                    with open(output_file_dec, 'wb') as f:
                        f.write(decompressed)
                    print(f"[保存] 解压数据已保存到: {output_file_dec}")

                    # 尝试解码为文本
                    try:
                        text = decompressed.decode('utf-8', errors='ignore')
                        print()
                        print("[前500字符]:")
                        print(text[:500])
                    except:
                        pass

                except Exception as e:
                    print(f"[解压] 失败: {e}")

                    # 尝试直接解码
                    try:
                        text = data.decode('utf-8', errors='ignore')
                        print()
                        print("[前500字符]（未压缩）:")
                        print(text[:500])
                    except:
                        pass

                saved = True

            except Exception as e:
                print(f"[错误] 处理响应失败: {e}")
                import traceback
                traceback.print_exc()

        page.on("response", handle_response)

        # 访问直播间
        url = f"https://live.douyin.com/{room_id}"
        print(f"访问直播间: {url}\n")

        await page.goto(url, wait_until='domcontentloaded', timeout=30000)

        # 等待捕获响应
        print("等待捕获im/fetch响应...")
        for i in range(15):
            await asyncio.sleep(1)
            if saved:
                print(f"\n已捕获响应！（{i+1}秒）")
                break
            print(f"  {i+1}/15 秒...")

        # 关闭
        await page.close()
        await context.close()
        await browser.close()

        print("\n" + "="*60)
        print("分析完成！请查看保存的文件：")
        print("1. im_fetch_response.raw - 原始响应数据")
        print("2. im_fetch_response_decompressed.raw - 解压后数据（如果成功）")
        print("="*60)

    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()

    finally:
        await playwright.stop()


if __name__ == "__main__":
    try:
        asyncio.run(analyze_http_response())
    except KeyboardInterrupt:
        print("\n\n用户中断")
