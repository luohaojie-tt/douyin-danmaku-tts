#!/usr/bin/env python3
"""
域名测试工具

测试可能的抖音WebSocket服务器域名是否有效。
"""

import asyncio
import socket
from pathlib import Path

# 可能的域名列表
DOMAINS = [
    # 原有的amemv.com域名
    "webcast5-ws-web-lf.amemv.com",
    "webcast5-ws-web-hl.amemv.com",
    "webcast3-ws-web-lf.amemv.com",
    "webcast62-ws-web-lf.amemv.com",
    "webcast-ws-web-lq.amemv.com",

    # 可能的新域名（douyin.com）
    "webcast5-ws-web-lf.douyin.com",
    "webcast5-ws-web-hl.douyin.com",
    "webcast3-ws-web-lf.douyin.com",
    "webcast62-ws-web-lf.douyin.com",

    # bytedance.com
    "webcast5-ws-web-lf.byteimg.com",
    "webcast5-ws-web-lf.bytedance.com",

    # 其他可能的域名
    "webcast.amemv.com",
    "webcast.douyin.com",
    "live.douyin.com",
]


async def test_domain(domain: str) -> dict:
    """测试单个域名"""
    try:
        # 尝试DNS解析
        loop = asyncio.get_event_loop()
        future = loop.getaddrinfo(domain, 443)
        try:
            result = await asyncio.wait_for(future, timeout=5)
            # 解析成功
            ip = result[0][4][0] if result else None
            return {
                "domain": domain,
                "status": "success",
                "ip": ip,
            }
        except asyncio.TimeoutError:
            return {
                "domain": domain,
                "status": "timeout",
            }
    except socket.gaierror:
        return {
            "domain": domain,
            "status": "not_found",
        }
    except Exception as e:
        return {
            "domain": domain,
            "status": "error",
            "error": str(e),
        }


async def main():
    """主函数"""
    print("="*60)
    print("  抖音WebSocket域名测试")
    print("="*60)
    print(f"测试 {len(DOMAINS)} 个域名...")
    print()

    results = []
    tasks = [test_domain(domain) for domain in DOMAINS]
    results = await asyncio.gather(*tasks)

    # 分类结果
    success = [r for r in results if r["status"] == "success"]
    timeout = [r for r in results if r["status"] == "timeout"]
    not_found = [r for r in results if r["status"] == "not_found"]
    errors = [r for r in results if r["status"] == "error"]

    # 打印结果
    print("\n[OK] 成功解析的域名:")
    if success:
        for r in success:
            print(f"  {r['domain']} -> {r['ip']}")
    else:
        print("  无")

    print("\n[TIMEOUT] 超时的域名:")
    if timeout:
        for r in timeout:
            print(f"  {r['domain']}")
    else:
        print("  无")

    print(f"\n[NOT FOUND] 不存在的域名: {len(not_found)} 个")
    print(f"[ERROR] 其他错误: {len(errors)} 个")

    # 保存结果
    if success:
        print("\n" + "="*60)
        print("发现可用域名！")
        print("="*60)

        valid_domains = [r["domain"] for r in success]
        ws_urls = [f"wss://{domain}/webcast/im/push/v2/" for domain in valid_domains]

        print("\n可用的WebSocket URL:")
        for url in ws_urls:
            print(f"  {url}")

        # 保存到文件
        output = Path("valid_websocket_urls.txt")
        output.write_text("\n".join(ws_urls))
        print(f"\n已保存到: {output.absolute()}")

    print("\n测试完成")


if __name__ == "__main__":
    asyncio.run(main())
