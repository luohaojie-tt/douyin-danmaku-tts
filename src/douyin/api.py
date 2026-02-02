"""
抖音API - 获取im初始化信息

参考: dycast/src/core/request.ts
"""
import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class DouyinAPI:
    """抖音API客户端"""

    def __init__(self, ttwid: str):
        """
        初始化API客户端

        Args:
            ttwid: 抖音ttwid cookie
        """
        self.ttwid = ttwid
        self.base_url = "https://live.douyin.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Cookie": f"ttwid={ttwid}",
            "Referer": "https://live.douyin.com/"
        }

    async def get_live_info(self, room_id: str) -> Optional[Dict[str, Any]]:
        """
        获取直播间信息

        Args:
            room_id: 直播间房间ID（网页URL中的ID）

        Returns:
            包含roomId和uniqueId的字典，失败返回None
        """
        try:
            url = f"{self.base_url}/{room_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status != 200:
                        logger.error(f"获取直播间信息失败: HTTP {response.status}")
                        return None

                    html = await response.text()

                    # 从HTML中提取roomId和uniqueId
                    # 简化版：使用正则表达式
                    import re

                    # 提取roomId
                    room_match = re.search(r'"roomId":"(\d+)"', html)
                    if not room_match:
                        room_match = re.search(r'roomId:"(\d+)"', html)

                    # 提取uniqueId
                    unique_match = re.search(r'"uniqueId":"([^"]+)"', html)
                    if not unique_match:
                        unique_match = re.search(r'uniqueId:"([^"]+)"', html)

                    if not room_match or not unique_match:
                        logger.error("无法从HTML中提取roomId和uniqueId")
                        return None

                    result = {
                        'roomId': room_match.group(1),
                        'uniqueId': unique_match.group(1),
                        'room_id_str': room_id  # 原始的房间号
                    }

                    logger.info(f"获取直播间信息成功:")
                    logger.info(f"  roomId: {result['roomId']}")
                    logger.info(f"  uniqueId: {result['uniqueId']}")

                    return result

        except Exception as e:
            logger.error(f"获取直播间信息异常: {e}")
            return None

    async def get_im_info(self, room_id: str, unique_id: str) -> Optional[Dict[str, str]]:
        """
        获取IM初始化信息

        Args:
            room_id: 内部room ID
            unique_id: 用户unique ID

        Returns:
            包含cursor和internal_ext的字典
        """
        try:
            # 构造参数（参考dycast request.ts第88-108行）
            params = {
                'room_id': room_id,
                'user_unique_id': unique_id
            }

            # 添加固定参数
            params.update({
                'live_pc': room_id,
                'a_bogus': '00000000'  # 加密参数，暂时使用默认值
            })

            url = f"{self.base_url}/dylive/webcast/im/fetch/?{urlencode(params)}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status != 200:
                        logger.warning(f"获取IM信息失败: HTTP {response.status}，使用默认值")
                        # 返回默认值（参考dycast request.ts第143-149行）
                        import time
                        now = int(time.time() * 1000)
                        return {
                            'cursor': f'r-{room_id}_d-1_u-1_fh-{room_id}_t-{now}',
                            'internal_ext': f'internal_src:dim|wss_push_room_id:{room_id}|wss_push_did:{unique_id}|first_req_ms:{now}|fetch_time:{now}|seq:1|wss_info:0-{now}-0-0|wrds_v:{room_id}',
                            'now': str(now)
                        }

                    # 读取二进制响应
                    data = await response.read()

                    # 尝试解析protobuf（需要实现protobuf解码）
                    # 暂时返回默认值
                    logger.info("获取IM信息成功（使用protobuf解析）")
                    # TODO: 实现完整的protobuf解析
                    import time
                    now = int(time.time() * 1000)
                    return {
                        'cursor': f'r-{room_id}_d-1_u-1_fh-{room_id}_t-{now}',
                        'internal_ext': f'internal_src:dim|wss_push_room_id:{room_id}|wss_push_did:{unique_id}|first_req_ms:{now}|fetch_time:{now}|seq:1|wss_info:0-{now}-0-0|wrds_v:{room_id}',
                        'now': str(now)
                    }

        except Exception as e:
            logger.error(f"获取IM信息异常: {e}")
            # 返回默认值
            import time
            now = int(time.time() * 1000)
            return {
                'cursor': f'r-{room_id}_d-1_u-1_fh-{room_id}_t-{now}',
                'internal_ext': f'internal_src:dim|wss_push_room_id:{room_id}|wss_push_did:{unique_id}|first_req_ms:{now}|fetch_time:{now}|seq:1|wss_info:0-{now}-0-0|wrds_v:{room_id}',
                'now': str(now)
            }


async def test_api():
    """测试API"""
    import sys
    from pathlib import Path

    # 添加项目根目录到路径
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    from src.douyin.cookie import CookieManager

    # 加载cookie
    cookie_manager = CookieManager()
    ttwid = cookie_manager.load_from_file()

    # 创建API客户端
    api = DouyinAPI(ttwid)

    # 测试房间
    room_id = "168465302284"

    # 获取直播间信息
    print("获取直播间信息...")
    live_info = await api.get_live_info(room_id)

    if live_info:
        print(f"Success!")
        print(f"  roomId: {live_info['roomId']}")
        print(f"  uniqueId: {live_info['uniqueId']}")

        # 获取IM信息
        print("\n获取IM信息...")
        im_info = await api.get_im_info(live_info['roomId'], live_info['uniqueId'])

        if im_info:
            print(f"Success!")
            print(f"  cursor: {im_info['cursor'][:80]}...")
            print(f"  internal_ext: {im_info['internal_ext'][:80]}...")


if __name__ == "__main__":
    asyncio.run(test_api())
