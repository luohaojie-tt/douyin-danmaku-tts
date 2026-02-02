#!/usr/bin/env python3
"""
Debug script to inspect Douyin room page HTML
"""

import asyncio
import aiohttp
import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.douyin.cookie import CookieManager


async def debug_room_info():
    """Debug room info extraction"""

    # Load cookie
    cookie_mgr = CookieManager()
    ttwid = cookie_mgr.load_from_file()

    print(f"Using ttwid: {ttwid[:50]}...")

    room_id = "728804746624"
    url = f"https://live.douyin.com/{room_id}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": f"ttwid={ttwid}",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    print(f"\nFetching: {url}\n")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as resp:
                print(f"Status: {resp.status}")
                print(f"Headers: {dict(resp.headers)}\n")

                html = await resp.text()
                print(f"HTML length: {len(html)} characters")

                # Save HTML for inspection
                Path("debug_page.html").write_text(html, encoding='utf-8')
                print("HTML saved to debug_page.html\n")

                # Try different patterns
                patterns = [
                    (r'"wss://([^"]+)"', 'Pattern 1: "wss://..."'),
                    (r'wss://[a-zA-Z0-9\.\-]+', 'Pattern 2: wss://domain'),
                    (r'webcast[^\s"\']+', 'Pattern 3: webcast...'),
                    (r'WebSocket[^"\']*', 'Pattern 4: WebSocket'),
                    (r'im/push[^"\']*', 'Pattern 5: im/push'),
                ]

                print("Searching for WebSocket URL patterns:\n")
                for pattern, name in patterns:
                    matches = re.findall(pattern, html)
                    if matches:
                        print(f"[{name}] Found {len(matches)} match(es):")
                        for i, match in enumerate(matches[:3]):  # Show first 3
                            print(f"  {i+1}. {match[:100]}")
                    else:
                        print(f"[{name}] No matches")

                # Look for specific strings
                print("\n\nLooking for specific keywords:\n")
                keywords = [
                    'webcast',
                    'websocket',
                    'wss://',
                    'room_id',
                    'roomid',
                ]

                for keyword in keywords:
                    count = html.lower().count(keyword)
                    if count > 0:
                        print(f"'{keyword}': {count} occurrence(s)")

                # Show a snippet of HTML around 'webcast'
                if 'webcast' in html.lower():
                    idx = html.lower().find('webcast')
                    snippet = html[max(0, idx-100):idx+200]
                    print(f"\nSnippet around 'webcast':\n{snippet}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_room_info())
