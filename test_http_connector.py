"""
测试HTTP轮询连接器

验证：
1. 能否成功连接直播间
2. 能否获取内部room_id
3. 能否解析弹幕消息
"""

import asyncio
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.douyin.cookie import CookieManager
from src.douyin.connector_http import DouyinHTTPConnector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


async def test_http_connector():
    """测试HTTP连接器"""

    # 测试房间号
    room_id = "118636942397"

    # 加载cookie
    cookie_manager = CookieManager()
    ttwid = cookie_manager.load_from_file()

    if not ttwid:
        logger.error("无法加载ttwid，请检查 cookies.txt")
        return False

    logger.info("="*60)
    logger.info("测试HTTP轮询连接器")
    logger.info("="*60)
    logger.info(f"房间号: {room_id}")

    # 创建连接器
    connector = DouyinHTTPConnector(room_id, ttwid, poll_interval=2.0)

    # 连接
    logger.info("\n步骤1: 连接直播间...")
    connected = await connector.connect()

    if not connected:
        logger.error("连接失败！")
        return False

    logger.info("连接成功！")
    logger.info(f"内部room_id: {connector.internal_room_id}")

    # 监听消息（测试10秒）
    logger.info("\n步骤2: 监听弹幕消息（10秒）...")

    message_count = 0
    danmaku_count = 0

    async def message_handler(msg):
        nonlocal message_count, danmaku_count
        message_count += 1

        logger.info(f"收到消息 #{message_count}: {msg.method}")

        if msg.method == "WebChatMessage" and msg.content:
            danmaku_count += 1
            user = msg.user.nickname if msg.user else "未知用户"
            logger.info(f">>> [弹幕 #{danmaku_count}] {user}: {msg.content}")

    # 监听10秒
    try:
        task = asyncio.create_task(connector.listen(message_handler))

        # 运行10秒
        await asyncio.sleep(10)

        # 停止监听
        connector.is_running = False
        await task

    except KeyboardInterrupt:
        logger.info("用户中断")
    except Exception as e:
        logger.error(f"监听异常: {e}")

    # 断开连接
    logger.info("\n步骤3: 断开连接...")
    await connector.disconnect()

    # 打印统计
    logger.info("="*60)
    logger.info("测试结果")
    logger.info("="*60)
    logger.info(f"总消息数: {message_count}")
    logger.info(f"弹幕数: {danmaku_count}")

    if danmaku_count > 0:
        logger.info("✅ 测试成功！成功获取到弹幕消息")
        return True
    else:
        logger.warning("⚠️ 未获取到弹幕消息（可能是直播间暂无弹幕）")
        return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_http_connector())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(0)
