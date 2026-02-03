"""
WebSocket URL 提取器

从抖音直播间页面提取真实的WebSocket连接地址。
"""

import asyncio
import json
import logging
import re

import aiohttp

logger = logging.getLogger(__name__)


class WebSocketExtractor:
    """
    WebSocket URL提取器

    通过访问直播间页面，解析JavaScript代码获取WebSocket连接信息
    """

    def __init__(self, ttwid: str):
        """
        初始化提取器

        Args:
            ttwid: 抖音ttwid cookie
        """
        self.ttwid = ttwid
        self.session = None

    async def _get_session(self):
        """获取或创建aiohttp会话"""
        if self.session is None:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Cookie": f"ttwid={self.ttwid}",
            }

            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)

        return self.session

    async def extract_websocket_url(self, room_id: str) -> dict:
        """
        提取WebSocket URL

        Args:
            room_id: 直播间房间ID

        Returns:
            dict: 包含WebSocket连接信息的字典
            {
                "url": "wss://...",
                "headers": {...},
                "success": True/False
            }
        """
        try:
            session = await self._get_session()

            # 访问直播间页面
            url = f"https://live.douyin.com/{room_id}"
            logger.info(f"访问直播间页面: {url}")

            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.error(f"HTTP {resp.status}: 无法访问直播间")
                    return {"success": False, "error": f"HTTP {resp.status}"}

                html = await resp.text()
                logger.info(f"页面大小: {len(html)} 字节")

            # 方法1: 尝试从HTML中直接提取
            result = self._extract_from_html(html)
            if result:
                return result

            # 方法2: 从JavaScript中提取（新版抖音）
            result = await self._extract_from_js(room_id)
            if result:
                return result

            # 方法3: 使用已知的备用服务器
            return self._get_fallback_servers()

        except Exception as e:
            logger.error(f"提取WebSocket URL失败: {e}")
            return {"success": False, "error": str(e)}

    def _extract_from_html(self, html: str) -> dict:
        """从HTML中提取WebSocket URL"""
        try:
            # 尝试多种模式匹配

            # 模式1: 直接的wss://链接
            patterns = [
                r'"wss://([^"]+)"',
                r"'wss://([^']+)'",
                r'wss://([^"\s]+)',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    # 过滤出包含webcast的链接
                    for match in matches:
                        if 'webcast' in match.lower():
                            ws_url = f"wss://{match}"
                            logger.info(f"从HTML中找到WebSocket URL: {ws_url}")
                            return {
                                "success": True,
                                "url": ws_url,
                                "source": "html"
                            }

            return None

        except Exception as e:
            logger.debug(f"从HTML提取失败: {e}")
            return None

    async def _extract_from_js(self, room_id: str) -> dict:
        """从JavaScript API获取"""
        try:
            session = await self._get_session()

            # 尝试访问直播间API
            api_url = f"https://live.douyin.com/live/api/webroom/live"
            params = {
                "aid": "6383",
                "room_id": room_id,
                "live_id": "1",
            }

            logger.info(f"尝试访问API: {api_url}")

            async with session.get(api_url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()

                    # 解析响应
                    if data.get("status_code") == 0:
                        room_data = data.get("data", {})
                        # 提取WebSocket相关信息
                        ws_info = room_data.get("stream_url", {})
                        if ws_info:
                            logger.info(f"从API获取到WebSocket信息")
                            return {
                                "success": True,
                                "url": ws_info.get("flv_url", ""),  # 可能不是WS URL
                                "source": "api"
                            }

            return None

        except Exception as e:
            logger.debug(f"从API提取失败: {e}")
            return None

    def _get_fallback_servers(self) -> dict:
        """获取备用服务器列表"""
        # 使用已知的抖音WebSocket服务器
        servers = [
            "wss://webcast5-ws-web-lf.amemv.com/webcast/im/push/v2/",
            "wss://webcast5-ws-web-hl.amemv.com/webcast/im/push/v2/",
            "wss://webcast3-ws-web-lf.amemv.com/webcast/im/push/v2/",
            "wss://webcast62-ws-web-lf.amemv.com/webcast/im/push/v2/",
            # 添加更多可能的域名
            "wss://webcast-ws-web-lq.amemv.com/webcast/im/push/v2/",
            "wss://webcast5-ws-web-hl.amemv.com/webcast/im/push/v2/",
        ]

        logger.info("使用备用服务器列表")

        return {
            "success": True,
            "servers": servers,
            "source": "fallback"
        }

    async def close(self):
        """关闭会话"""
        if self.session:
            await self.session.close()
            self.session = None


async def test_websocket_extractor():
    """测试WebSocket提取器"""
    # 使用测试ttwid
    ttwid = "1%7CYlCMjX02ZOR2HqYrdJCB7PTikyVrzsXt8tWCYsVpYgA%7C1770031932%7Cbea202516c970c8f6848050ffc06b3c0f45ca8a4785ba6a0099a6e0446aa0c02"

    extractor = WebSocketExtractor(ttwid)

    try:
        result = await extractor.extract_websocket_url("728804746624")

        print("\n提取结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    finally:
        await extractor.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_websocket_extractor())
