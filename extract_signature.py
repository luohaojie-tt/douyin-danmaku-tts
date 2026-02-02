#!/usr/bin/env python3
"""
从浏览器直接提取signature和WebSocket URL
"""

import asyncio
import json
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright


async def extract_signature(room_id: str, ttwid: str):
    """从浏览器提取signature和WebSocket URL"""

    result = {
        "success": False,
        "roomId": "",
        "signature": "",
        "cursor": "",
        "wsUrl": "",
        "error": ""
    }

    async with async_playwright() as p:
        try:
            # 连接到Chrome
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

            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            print("[OK] 页面加载完成")

            # 等待JavaScript初始化
            await asyncio.sleep(2)

            # 1. 检查frontierSign是否可用
            print("\n检查frontierSign...")
            frontier_sign_exists = await page.evaluate(
                '''() => typeof window.byted_acrawler !== "undefined" &&
                         typeof window.byted_acrawler.frontierSign !== "undefined"'''
            )

            if not frontier_sign_exists:
                result['error'] = "frontierSign不可用"
                print("[FAIL] frontierSign不可用")
                return result

            print("[OK] frontierSign可用")

            # 2. 从__pace_f提取房间信息
            print("\n从__pace_f提取房间信息...")
            room_info = await page.evaluate('''() => {
                if (!window.__pace_f) {
                    return null;
                }

                // 查找包含room_id的项
                for (let item of window.__pace_f) {
                    if (item && item[1] && item[1].room_id) {
                        return {
                            roomId: item[1].room_id,
                            nickname: item[1].owner?.nickname || "",
                            uniqueId: item[1].owner?.web_rid || ""
                        };
                    }
                }

                return null;
            }''')

            if room_info:
                print(f"[OK] 房间信息:")
                print(f"      roomId: {room_info['roomId']}")
                print(f"      nickname: {room_info['nickname']}")
                print(f"      uniqueId: {room_info['uniqueId']}")
                result['roomId'] = room_info['roomId']
            else:
                print("[WARN] 从__pace_f未找到房间信息")

            # 3. 生成signature
            print("\n生成signature...")

            # 方法1: 尝试获取已有的signature参数
            signature_data = await page.evaluate('''() => {
                // 尝试从URL获取
                const urlParams = new URLSearchParams(window.location.search);
                if (urlParams.has('signature')) {
                    return {
                        signature: urlParams.get('signature'),
                        source: 'url'
                    };
                }

                // 尝试从页面配置获取
                if (window.__roomInfo && window.__roomInfo.signature) {
                    return {
                        signature: window.__roomInfo.signature,
                        source: '__roomInfo'
                    };
                }

                // 尝试调用frontierSign
                if (window.byted_acrawler && window.byted_acrawler.frontierSign) {
                    try {
                        // 获取当前页面的URL参数
                        const params = new URLSearchParams(window.location.search);
                        const roomId = params.get('room_id') || window.location.pathname.slice(1);

                        // 构造待签名字符串
                        const signStr = `room_id=${roomId}&live_id=1&aid=6383`;
                        const signature = window.byted_acrawler.frontierSign(signStr);

                        return {
                            signature: signature,
                            source: 'frontierSign'
                        };
                    } catch(e) {
                        return {
                            error: e.toString(),
                            source: 'frontierSign_error'
                        };
                    }
                }

                return null;
            }''')

            if signature_data:
                if 'error' in signature_data:
                    print(f"[WARN] frontierSign调用失败: {signature_data['error']}")
                elif 'signature' in signature_data:
                    result['signature'] = signature_data['signature']
                    print(f"[OK] signature来源: {signature_data['source']}")
                    sig_value = result['signature']
                    if isinstance(sig_value, str):
                        print(f"      signature: {sig_value[:30]}...")
                    else:
                        print(f"      signature: {json.dumps(sig_value, ensure_ascii=False)}")
                elif 'X-Bogus' in signature_data:
                    # frontierSign返回的是X-Bogus对象
                    result['signature'] = signature_data['X-Bogus']
                    print(f"[OK] X-Bogus签名: {result['signature']}")
                    print(f"      完整数据: {json.dumps(signature_data, ensure_ascii=False)}")
                else:
                    print(f"[OK] 获取到数据: {json.dumps(signature_data, ensure_ascii=False)}")
                    result['signature'] = signature_data

            # 4. 监听WebSocket连接
            print("\n监听WebSocket连接...")

            ws_captured = False
            ws_url = ""

            def on_websocket(ws):
                nonlocal ws_captured, ws_url
                print(f"\n[WS] 捕获到WebSocket连接!")
                print(f"     URL: {ws.url[:150]}...")
                ws_captured = True
                ws_url = ws.url

            page.on('websocket', on_websocket)

            # 5. 尝试触发WebSocket连接
            print("尝试触发WebSocket...")

            # 尝试1: 等待自动连接
            for i in range(5):
                await asyncio.sleep(1)
                if ws_captured:
                    break

            # 尝试2: 滚动页面
            if not ws_captured:
                print("  尝试滚动页面...")
                try:
                    await page.evaluate('window.scrollBy(0, 100)')
                except:
                    pass
                await asyncio.sleep(2)

            # 尝试3: 点击视频区域
            if not ws_captured:
                print("  尝试点击视频区域...")
                try:
                    await page.click('div[class*="player"]', timeout=2000)
                except:
                    try:
                        await page.click('video', timeout=2000)
                    except:
                        pass
                await asyncio.sleep(2)

            # 尝试4: 执行JavaScript触发连接
            if not ws_captured:
                print("  尝试通过JavaScript触发...")

                # 尝试直接调用页面内部的连接函数
                triggered = await page.evaluate('''() => {
                    // 尝试找到并触发连接函数
                    if (window.__roomInit) {
                        try {
                            window.__roomInit();
                            return 'roomInit';
                        } catch(e) {}
                    }

                    if (window.__connectWebSocket) {
                        try {
                            window.__connectWebSocket();
                            return 'connectWebSocket';
                        } catch(e) {}
                    }

                    // 尝试触发自定义事件
                    window.dispatchEvent(new Event('load'));
                    window.dispatchEvent(new Event('DOMContentLoaded'));

                    return 'event_dispatched';
                }''')

                print(f"     触发方式: {triggered}")
                await asyncio.sleep(3)

            # 6. 检查WebSocket结果
            if ws_captured:
                result['wsUrl'] = ws_url
                result['success'] = True
                print("\n[SUCCESS] 成功捕获WebSocket URL!")

                # 解析参数
                parsed = urlparse(ws_url)
                params = parse_qs(parsed.query)

                print("\nWebSocket参数:")
                if 'signature' in params:
                    result['signature'] = params['signature'][0]
                    print(f"  signature: {result['signature'][:30]}...")

                if 'cursor' in params:
                    result['cursor'] = params['cursor'][0]
                    print(f"  cursor: {result['cursor'][:30]}...")

                if 'room_id' in params:
                    print(f"  room_id: {params['room_id'][0]}")

            else:
                print("\n[FAIL] 未捕获到WebSocket连接")
                result['error'] = "WebSocket连接未建立"

                # 即使没有WebSocket，也检查是否有其他方式获取参数
                print("\n尝试从页面获取连接参数...")

                connection_params = await page.evaluate('''() => {
                    // 尝试从多个可能的来源获取连接参数
                    const sources = [
                        'window.__roomInfo',
                        'window.__liveInfo',
                        'window._SSR_HYDRATED_DATA',
                    ];

                    for (let source of sources) {
                        try {
                            const parts = source.split('.');
                            let obj = window;
                            for (let part of parts) {
                                if (part === 'window') continue;
                                obj = obj[part];
                                if (!obj) break;
                            }

                            if (obj && obj.roomId) {
                                return {
                                    source: source,
                                    data: obj
                                };
                            }
                        } catch(e) {}
                    }

                    return null;
                }''')

                if connection_params:
                    print(f"[OK] 找到数据源: {connection_params['source']}")
                    print(f"     数据: {json.dumps(connection_params['data'], indent=2, ensure_ascii=False)}")

            # 7. 截图保存
            try:
                await page.screenshot(path="signature_extraction.png")
                print("\n[OK] 截图已保存: signature_extraction.png")
            except:
                pass

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
    room_id = "728804746624"
    ttwid = "1%7CYlCMjX02ZOR2HqYrdJCB7PTikyVrzsXt8tWCYsVpYgA%7C1770031932%7Cbea202516c970c8f6848050ffc06b3c0f45ca8a4785ba6a0099a6e0446aa0c02"

    print("="*60)
    print("  抖音直播间Signature提取")
    print("="*60)
    print()

    result = await extract_signature(room_id, ttwid)

    print("\n" + "="*60)
    print("  结果")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result.get('success') and result.get('wsUrl'):
        print("\n[SUCCESS] 成功获取WebSocket URL!")
        print(f"\n完整URL:")
        print(result['wsUrl'])
    elif result.get('signature'):
        sig = result['signature']
        if isinstance(sig, dict):
            print(f"\n[PARTIAL] 获取到签名数据: {json.dumps(sig, ensure_ascii=False)}")
        else:
            print(f"\n[PARTIAL] 获取到signature: {sig[:30] if len(sig) > 30 else sig}...")
    else:
        print(f"\n[FAIL] 失败: {result.get('error')}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
