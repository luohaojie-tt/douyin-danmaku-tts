#!/usr/bin/env python3
"""
使用Playwright获取signature - 简化版
"""

import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright


async def get_signature_playwright(room_id: str, ttwid: str):
    """
    使用Playwright获取signature
    """
    result = {"success": False, "signature": "", "error": ""}

    async with async_playwright() as p:
        try:
            # 连接到已启动的Chrome
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            print("[OK] 已连接到Chrome")

            # 获取所有context
            contexts = browser.contexts
            if not contexts:
                # 如果没有context，创建一个
                context = await browser.new_context()
                print("[OK] 创建新context")
            else:
                context = contexts[0]
                print(f"[OK] 使用现有context (有{len(context.pages)}个页面)")

            # 设置cookie
            await context.add_cookies([{
                'name': 'ttwid',
                'value': ttwid,
                'domain': '.douyin.com',
                'path': '/'
            }])
            print("[OK] 已设置cookie")

            # 获取或创建页面
            pages = context.pages
            if pages:
                page = pages[0]
                print(f"[OK] 使用现有页面")
            else:
                page = await context.new_page()
                print("[OK] 创建新页面")

            # 监听WebSocket
            ws_urls = []

            def on_websocket(ws):
                print(f"\n[OK] 捕获到WebSocket!")
                print(f"  URL: {ws.url[:100]}...")
                ws_urls.append(ws.url)

            page.on('websocket', on_websocket)

            # 访问直播间
            url = f"https://live.douyin.com/{room_id}"
            print(f"\n访问直播间: {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            print("[OK] 页面加载完成")

            # 等待并尝试触发WebSocket
            print("\n等待WebSocket连接...")
            for i in range(10):
                await asyncio.sleep(1)

                # 尝试滚动触发连接
                try:
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                except:
                    pass

                if ws_urls:
                    break

                if i >= 9:
                    print("[FAIL] 未捕获到WebSocket连接")
                    break

            # 检查结果
            if ws_urls:
                result['success'] = True
                result['wsUrl'] = ws_urls[0]
                print(f"\n成功捕获WebSocket URL!")
                print(f"完整URL: {ws_urls[0][:200]}...")

                # 解析参数
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(ws_urls[0])
                params = parse_qs(parsed.query)

                if 'signature' in params:
                    result['signature'] = params['signature'][0]
                    print(f"\n[OK] signature: {result['signature'][:30]}...")

                if 'cursor' in params:
                    print(f"[OK] cursor: {params['cursor'][0][:50]}...")

                if 'room_id' in params:
                    print(f"[OK] room_id: {params['room_id'][0]}")

            else:
                result['error'] = "未捕获到WebSocket连接"

        except Exception as e:
            result['error'] = str(e)
            print(f"[FAIL] 发生错误: {e}")

        finally:
            try:
                await browser.close()
                print("\n已关闭浏览器连接")
            except:
                pass

    return result


async def main():
    room_id = "728804746624"
    ttwid = "1%7CYlCMjX02ZOR2HqYrdJCB7PTikyVrzsXt8tWCYsVpYgA%7C1770031932%7Cbea202516c970c8f6848050ffc06b3c0f45ca8a4785ba6a0099a6e0446aa0c02"

    print("="*60)
    print("  Playwright Signature 测试")
    print("="*60)
    print()

    result = await get_signature_playwright(room_id, ttwid)

    print("\n" + "="*60)
    print("  结果")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result.get('success'):
        print("\n[OK] 成功获取signature!")
    else:
        print(f"\n[FAIL] 失败: {result.get('error')}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
