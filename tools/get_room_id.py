#!/usr/bin/env python3
"""
获取真实room_id

从抖音直播间页面提取真实的房间ID。
"""

import asyncio
import json
import re
import sys
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def get_real_room_id(room_url: str, ttwid: str):
    """获取真实room_id"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cookie": f"ttwid={ttwid}",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(room_url) as resp:
            html = await resp.text()

    # 方法1: 从HTML中提取roomId
    patterns = [
        r'"roomId":"(\d+)"',
        r'"room_id":"?(\d+)"?',
        r'roomId=(\d+)',
        r'"liveRoom":\{"roomId":"(\d+)"',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html)
        if matches:
            real_room_id = matches[0]
            print(f"找到真实room_id: {real_room_id}")
            return real_room_id

    # 方法2: 尝试从API获取
    # 提取web_rid
    web_rid_match = re.search(r'/(\d+)', room_url)
    if not web_rid_match:
        print("无法从URL中提取ID")
        return None

    web_rid = web_rid_match.group(1)

    api_url = "https://live.douyin.com/live/api/webroom/live"
    params = {
        "aid": "6383",
        "web_rid": web_rid,
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(api_url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"\nAPI响应:")
                print(json.dumps(data, indent=2, ensure_ascii=False))

                if data.get("status_code") == 0:
                    room_data = data.get("data", {})
                    real_room_id = room_data.get("id", {}).get("id", "")
                    if real_room_id:
                        print(f"\n真实room_id: {real_room_id}")
                        return real_room_id

    print("\n未找到真实room_id")
    return None


async def main():
    """主函数"""
    # 使用测试ttwid
    ttwid = "1%7CYlCMjX02ZOR2HqYrdJCB7PTikyVrzsXt8tWCYsVpYgA%7C1770031932%7Cbea202516c970c8f6848050ffc06b3c0f45ca8a4785ba6a0099a6e0446aa0c02"

    # 测试URL
    room_url = "https://live.douyin.com/728804746624"

    print(f"访问直播间: {room_url}")
    print("="*60)

    real_room_id = await get_real_room_id(room_url, ttwid)

    if real_room_id:
        # 保存到文件
        output = Path("real_room_id.txt")
        output.write_text(real_room_id)
        print(f"\n已保存到: {output.absolute()}")
    else:
        print("\n获取失败")


if __name__ == "__main__":
    asyncio.run(main())
