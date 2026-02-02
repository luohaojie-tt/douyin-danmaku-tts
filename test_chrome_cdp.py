#!/usr/bin/env python3
"""
使用已安装的Chrome浏览器获取signature

通过CDP (Chrome DevTools Protocol) 连接到已安装的Chrome浏览器。
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright


async def get_signature_with_existing_browser(room_id: str, ttwid: str) -> dict:
    """
    使用已安装的Chrome浏览器获取signature

    Args:
        room_id: 直播间房间ID
        ttwid: 抖音ttwid cookie

    Returns:
        dict: 包含signature等信息
    """
    result = {
        "success": False,
        "signature": "",
        "roomId": "",
        "uniqueId": "",
        "wsUrl": "",
        "error": ""
    }

    async with async_playwright() as p:
        # 连接到已安装的Chrome
        try:
            # 尝试使用已安装的Chrome
            browser = await p.chromium.connect_over_cdp(
                "http://localhost:9222"  # Chrome远程调试端口
            )
            print("已连接到Chrome浏览器")
        except Exception as e:
            result['error'] = f"无法连接到Chrome: {e}\n请启动Chrome并添加参数: --remote-debugging-port=9222"
            print(result['error'])
            return result

        try:
            # 获取所有页面
            pages = browser.contexts

            if not pages:
                result['error'] = "浏览器中没有打开的页面"
                return result

            # 使用第一个页面
            page = pages[0]

            # 获取页面URL
            try:
                current_url = page.url
                print(f"当前页面: {current_url}")
            except:
                print("当前页面: (无法获取URL)")
                current_url = ""

            # 设置cookie
            await page.context.add_cookies([{
                'name': 'ttwid',
                'value': ttwid,
                'domain': '.douyin.com',
                'path': '/'
            }])

            # 访问直播间
            url = f"https://live.douyin.com/{room_id}"
            print(f"访问: {url}")

            await page.goto(url, wait_until='networkidle', timeout=30000)
            print("页面加载完成")

            # 等待JavaScript执行
            await asyncio.sleep(5)

            # 监听WebSocket
            ws_urls = []

            def on_websocket(ws):
                print(f"捕获到WebSocket: {ws.url[:100]}...")
                ws_urls.append(ws.url)

            page.on('websocket', on_websocket)

            # 尝试滚动页面触发WebSocket连接
            await page.evaluate('() => { window.scrollTo(0, document.body.scrollHeight) }')
            await asyncio.sleep(3)

            # 检查是否捕获到WebSocket
            if ws_urls:
                result['wsUrl'] = ws_urls[0]
                result['success'] = True
                print(f"\n成功捕获WebSocket URL!")
                print(f"URL: {ws_urls[0][:150]}...")

                # 解析参数
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(ws_urls[0])
                params = parse_qs(parsed.query)

                if 'signature' in params:
                    result['signature'] = params['signature'][0]
                    print(f"signature: {result['signature'][:20]}...")

            else:
                result['error'] = "未捕获到WebSocket连接"
                print("未捕获到WebSocket连接")

        except Exception as e:
            result['error'] = str(e)
            print(f"发生错误: {e}")

    return result


async def main():
    """主函数"""
    ttwid = "1%7CYlCMjX02ZOR2HqYrdJCB7PTikyVrzsXt8tWCYsVpYgA%7C1770031932%7Cbea202516c970c8f6848050ffc06b3c0f45ca8a4785ba6a0099a6e0446aa0c02"
    room_id = "728804746624"

    print("="*60)
    print("  Chrome CDP Signature获取测试")
    print("="*60)
    print()
    print("尝试连接到Chrome浏览器 (http://localhost:9222)...")
    print()

    result = await get_signature_with_existing_browser(room_id, ttwid)

    print()
    print("="*60)
    print("结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
