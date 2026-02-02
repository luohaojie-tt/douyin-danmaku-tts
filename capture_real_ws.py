#!/usr/bin/env python3
"""
直接从浏览器捕获真实的WebSocket连接URL
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def capture_websocket_url(room_id: str, ttwid: str):
    """从浏览器捕获真实的WebSocket URL"""

    result = {
        "success": False,
        "wsUrl": "",
        "params": {},
        "error": ""
    }

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            print("[OK] 已连接到Chrome")

            contexts = browser.contexts
            context = contexts[0] if contexts else await browser.new_context()

            await context.add_cookies([{
                'name': 'ttwid',
                'value': ttwid,
                'domain': '.douyin.com',
                'path': '/'
            }])
            print("[OK] 已设置cookie")

            page = await context.new_page()

            url = f"https://live.douyin.com/{room_id}"
            print(f"\n访问直播间: {url}")

            # 监听WebSocket
            ws_captured = False
            ws_url = ""
            ws_frames = []

            def on_websocket(ws):
                nonlocal ws_captured, ws_url
                print(f"\n[WS] WebSocket连接建立!")
                print(f"     URL: {ws.url[:200]}...")
                ws_captured = True
                ws_url = ws.url

                # 监听消息
                def on_frame(frame):
                    ws_frames.append({
                        'type': 'received' if not isinstance(frame, str) else 'sent',
                        'length': len(frame) if isinstance(frame, (str, bytes)) else 0,
                        'data': frame[:100] if isinstance(frame, (str, bytes)) else str(frame)[:100]
                    })

                ws.on('framesreceived', on_frame)

            page.on('websocket', on_websocket)

            # 访问页面
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            print("[OK] 页面加载完成")

            # 等待WebSocket连接
            print("\n等待WebSocket连接...")

            max_wait = 20  # 最多等待20秒
            for i in range(max_wait):
                await asyncio.sleep(1)

                if ws_captured:
                    print(f"[OK] WebSocket已连接! (耗时 {i+1}秒)")
                    break

                # 尝试各种触发方式
                if i == 3:
                    print("  尝试滚动页面...")
                    try:
                        await page.evaluate('window.scrollBy(0, 100)')
                    except:
                        pass

                elif i == 6:
                    print("  尝试点击视频区域...")
                    try:
                        # 尝试点击可能的视频元素
                        selectors = [
                            'video',
                            'div[class*="player"]',
                            'div[class*="video"]',
                            'xg-video-container'
                        ]
                        for selector in selectors:
                            try:
                                await page.click(selector, timeout=1000)
                                print(f"     点击了: {selector}")
                                break
                            except:
                                pass
                    except:
                        pass

                elif i == 10:
                    print("  尝试执行JavaScript触发...")
                    triggered = await page.evaluate('''() => {
                        // 触发各种可能的初始化事件
                        window.dispatchEvent(new Event('load'));
                        window.dispatchEvent(new CustomEvent('liveReady'));
                        window.dispatchEvent(new CustomEvent('roomReady'));

                        // 检查是否有全局初始化函数
                        if (window.__initLive) {
                            try { window.__initLive(); return 'initLive'; } catch(e) {}
                        }
                        if (window.__connectIM) {
                            try { window.__connectIM(); return 'connectIM'; } catch(e) {}
                        }

                        return 'event_dispatched';
                    }''')
                    print(f"     触发结果: {triggered}")

                elif i == 15:
                    print("  尝试等待并刷新...")
                    await asyncio.sleep(2)
                    try:
                        await page.reload(wait_until='domcontentloaded')
                        print("     页面已刷新")
                    except:
                        pass

                # 显示进度
                if i > 0 and i % 5 == 0:
                    print(f"  等待中... ({i+1}/{max_wait}秒)")

            # 检查结果
            if ws_captured:
                result['success'] = True
                result['wsUrl'] = ws_url
                print("\n[SUCCESS] 成功捕获WebSocket URL!")

                # 解析URL参数
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(ws_url)
                params = parse_qs(parsed.query)

                result['params'] = {k: v[0] if len(v) == 1 else v for k, v in params.items()}

                print("\nWebSocket URL参数:")
                for key, value in sorted(params.items()):
                    value_str = value[0] if len(value) == 1 else value
                    if len(str(value_str)) > 50:
                        print(f"  {key}: {str(value_str)[:50]}...")
                    else:
                        print(f"  {key}: {value_str}")

                # 等待几秒收集消息
                print("\n等待接收消息...")
                await asyncio.sleep(5)

                if ws_frames:
                    print(f"\n[OK] 收到 {len(ws_frames)} 条消息:")
                    for i, frame in enumerate(ws_frames[:5]):
                        print(f"  [{i+1}] {frame['type']}: {frame['length']} bytes")
                else:
                    print("\n[WARN] 未收到消息")

                # 截图
                try:
                    await page.screenshot(path="websocket_captured.png")
                    print("\n[OK] 截图已保存: websocket_captured.png")
                except:
                    pass

            else:
                result['error'] = "WebSocket连接未建立"
                print(f"\n[FAIL] {max_wait}秒后WebSocket仍未连接")

                # 检查页面状态
                print("\n检查页面状态:")

                page_title = await page.title()
                print(f"  页面标题: {page_title}")

                current_url = page.url
                print(f"  当前URL: {current_url}")

                if 'login' in current_url.lower():
                    print("  [WARN] 页面重定向到登录")

                # 检查JavaScript对象
                js_objects = await page.evaluate('''() => {
                    return {
                        byted_acrawler: typeof window.byted_acrawler !== 'undefined',
                        frontierSign: typeof window.byted_acrawler?.frontierSign !== 'undefined',
                        __pace_f: typeof window.__pace_f !== 'undefined',
                        __RENDER_DATA__: typeof window.__RENDER_DATA__ !== 'undefined'
                    };
                }''')

                print(f"  JavaScript对象: {json.dumps(js_objects, indent=4, ensure_ascii=False)}")

            await browser.close()

        except Exception as e:
            result['error'] = str(e)
            print(f"\n[ERROR] 发生错误: {e}")

            try:
                await browser.close()
            except:
                pass

    return result


async def main():
    room_id = "666198550100"  # 正在直播的房间
    ttwid = "1%7CYlCMjX02ZOR2HqYrdJCB7PTikyVrzsXt8tWCYsVpYgA%7C1770031932%7Cbea202516c970c8f6848050ffc06b3c0f45ca8a4785ba6a0099a6e0446aa0c02"

    print("="*60)
    print("  捕获真实WebSocket连接URL")
    print("="*60)
    print()

    result = await capture_websocket_url(room_id, ttwid)

    print("\n" + "="*60)
    print("  结果")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result.get('success') and result.get('wsUrl'):
        print("\n[SUCCESS] 成功!")
        print(f"\n完整WebSocket URL:")
        print(result['wsUrl'])

        # 保存到文件
        with open('websocket_url.txt', 'w', encoding='utf-8') as f:
            f.write(result['wsUrl'])
        print(f"\n[OK] WebSocket URL已保存到: websocket_url.txt")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
