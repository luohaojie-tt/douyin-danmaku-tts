#!/usr/bin/env python3
"""
抖音弹幕语音播报工具 - 主程序入口

使用方法:
    python main.py <room_id> [options]

示例:
    python main.py 728804746624
    python main.py 728804746624 --mock  # 使用Mock连接器
    python main.py 728804746624 --debug
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config.loader import load_config
from src.douyin.cookie import CookieManager
from src.douyin.connector import DouyinConnector, DouyinConnectorMock
from src.douyin.connector_real import DouyinConnectorReal
from src.douyin.parser import MessageParser
from src.douyin.parser_real import RealtimeMessageParser
from src.tts.edge_tts import EdgeTTSEngine
from src.player.pygame_player import PygamePlayer

logger = logging.getLogger(__name__)


class DanmakuOrchestrator:
    """
    弹幕播报编排器

    协调各个模块完成端到端的弹幕语音播报
    """

    def __init__(
        self,
        room_id: str,
        config_path: str = "config.ini",
        use_mock: bool = False,
        use_real: bool = False
    ):
        """
        初始化编排器

        Args:
            room_id: 直播间房间ID
            config_path: 配置文件路径
            use_mock: 是否使用Mock连接器
            use_real: 是否使用真实连接器（Playwright）
        """
        self.room_id = room_id
        self.config_path = config_path
        self.use_mock = use_mock
        self.use_real = use_real

        # 统计信息
        self.stats = {
            "messages_received": 0,
            "messages_played": 0,
            "errors": 0,
        }

        # 模块实例（稍后初始化）
        self.config = None
        self.cookie_manager = None
        self.ttwid = None
        self.connector = None
        self.parser = None
        self.tts = None
        self.player = None

        self.is_running = False

    async def initialize(self):
        """初始化所有模块"""
        logger.info("="*60)
        logger.info("初始化弹幕播报系统")
        logger.info("="*60)

        # 1. 加载配置
        logger.info(f"加载配置: {self.config_path}")
        self.config = load_config(self.config_path)

        # 2. 加载ttwid
        logger.info("加载Cookie...")
        self.cookie_manager = CookieManager()
        self.ttwid = self.cookie_manager.load_from_file()

        if not self.ttwid:
            logger.error("无法加载ttwid，请检查 cookies.txt")
            logger.info("提示：从浏览器获取ttwid并保存到 cookies.txt")
            return False

        logger.info(f"ttwid加载成功 (长度: {len(self.ttwid)})")

        # 3. 初始化消息解析器
        logger.info("初始化消息解析器...")
        self.parser = MessageParser()

        # 4. 初始化TTS引擎
        logger.info("初始化TTS引擎...")
        self.tts = EdgeTTSEngine(
            voice=self.config.tts.voice,
            rate=self.config.tts.rate,
            volume=self.config.tts.volume
        )
        logger.info(f"音色: {self.config.tts.voice}")
        logger.info(f"语速: {self.config.tts.rate}")
        logger.info(f"音量: {self.config.tts.volume}")

        # 5. 初始化播放器
        logger.info("初始化播放器...")
        self.player = PygamePlayer(volume=self.config.playback.volume)
        logger.info(f"播放音量: {self.config.playback.volume}")

        # 6. 初始化连接器
        if self.use_mock:
            logger.info("使用Mock连接器（测试模式）")
            self.connector = DouyinConnectorMock(self.room_id, self.ttwid)
            self.parser = MessageParser()
        elif self.use_real:
            logger.info("使用真实连接器（Playwright）")
            logger.info("  提示: 需要Chrome在调试模式下运行")
            logger.info("  启动命令: chrome.exe --remote-debugging-port=9222")
            self.connector = DouyinConnectorReal(self.room_id, self.ttwid)
            self.parser = RealtimeMessageParser()
        else:
            logger.info("使用标准WebSocket连接器...")
            self.connector = DouyinConnector(self.room_id, self.ttwid)
            self.parser = MessageParser()

        logger.info("="*60)
        logger.info("初始化完成")
        logger.info("="*60)
        return True

    async def handle_message(self, raw_message):
        """
        处理接收到的消息

        流程: 解析 → TTS → 播放

        Args:
            raw_message: 原始消息（字典或二进制）
        """
        try:
            self.stats["messages_received"] += 1

            # 1. 解析消息
            if isinstance(raw_message, dict):
                # Mock连接器返回的是字典格式
                parsed = self.parser.parse_test_message(raw_message)
            elif isinstance(raw_message, bytes):
                # 真实连接器返回的是二进制数据
                if self.use_real:
                    parsed = self.parser.parse_message(raw_message)
                else:
                    parsed = await self.parser.parse_message(raw_message)
            else:
                logger.warning(f"未知消息类型: {type(raw_message)}")
                return

            if not parsed:
                logger.debug("消息解析失败，跳过")
                return

            logger.info(f"收到消息: {parsed.method}")

            # 只处理聊天消息
            if parsed.method != "WebChatMessage":
                logger.debug(f"跳过非聊天消息: {parsed.method}")
                return

            # 2. 提取弹幕内容
            if not parsed.content:
                logger.debug("消息内容为空，跳过")
                return

            user_name = parsed.user.nickname if parsed.user else "用户"
            content = parsed.content

            logger.info(f"[{user_name}]: {content}")

            # 3. 转换为语音
            logger.debug("开始转换语音...")
            audio_path = await self.tts.convert_with_cache(
                text=content,
                cache_dir=Path("cache")
            )

            if not audio_path:
                logger.warning("语音转换失败，跳过播放")
                return

            # 4. 播放语音
            logger.debug("开始播放语音...")
            success = self.player.play(audio_path, blocking=False)

            if success:
                self.stats["messages_played"] += 1
                logger.info(f"播报成功 (总计: {self.stats['messages_played']})")
            else:
                logger.warning("播放失败")

        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            self.stats["errors"] += 1

    async def run(self):
        """运行主循环"""
        try:
            # 连接直播间
            logger.info(f"正在连接直播间: {self.room_id}")
            connected = await self.connector.connect()

            if not connected:
                logger.error("连接直播间失败")
                if self.use_mock:
                    logger.info("提示：Mock模式已启用")
                elif self.use_real:
                    logger.info("提示：真实连接失败，请检查:")
                    logger.info("  1. Chrome是否在调试模式下运行？")
                    logger.info("  2. 启动命令: chrome.exe --remote-debugging-port=9222")
                else:
                    logger.info("提示：可以使用 --mock 或 --real 参数")
                    logger.info("  --mock: Mock模式（不需要Chrome）")
                    logger.info("  --real: 真实模式（需要Chrome调试模式）")
                return False

            self.is_running = True
            logger.info("连接成功！开始监听弹幕...")
            logger.info("按 Ctrl+C 退出")

            # 监听消息
            await self.connector.listen(self.handle_message)

        except asyncio.CancelledError:
            logger.info("任务被取消")
        except KeyboardInterrupt:
            logger.info("用户中断")
        except Exception as e:
            logger.error(f"运行异常: {e}")
        finally:
            await self.shutdown()

    async def shutdown(self):
        """优雅关闭"""
        logger.info("="*60)
        logger.info("正在关闭...")
        logger.info("="*60)

        self.is_running = False

        # 断开连接
        if self.connector:
            await self.connector.disconnect()

        # 清理播放器
        if self.player:
            self.player.cleanup()

        # 打印统计信息
        logger.info("运行统计:")
        logger.info(f"  接收消息: {self.stats['messages_received']}")
        logger.info(f"  播报消息: {self.stats['messages_played']}")
        logger.info(f"  错误次数: {self.stats['errors']}")

        if self.stats['messages_received'] > 0:
            success_rate = (self.stats['messages_played'] / self.stats['messages_received']) * 100
            logger.info(f"  成功率: {success_rate:.1f}%")

        logger.info("="*60)
        logger.info("已安全退出")
        logger.info("="*60)


def parse_arguments():
    """解析命令行参数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="抖音弹幕语音播报工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py 728804746624
  python main.py 728804746624 --mock      # 使用Mock模式
  python main.py 728804746624 --real       # 使用真实连接（需要Chrome调试模式）
  python main.py 728804746624 --debug
  python main.py 728804746624 --config custom.ini

注意：
  --real 模式需要Chrome在调试模式下运行:
  启动命令: chrome.exe --remote-debugging-port=9222
        """
    )

    parser.add_argument(
        "room_id",
        help="直播间房间ID"
    )

    parser.add_argument(
        "--mock",
        action="store_true",
        help="使用Mock连接器（不连接真实直播间）"
    )

    parser.add_argument(
        "--real",
        action="store_true",
        help="使用真实连接器（需要Chrome调试模式）"
    )

    parser.add_argument(
        "--config",
        default="config.ini",
        help="配置文件路径 (默认: config.ini)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试日志"
    )

    parser.add_argument(
        "--voice",
        help="TTS音色 (如: zh-CN-XiaoxiaoNeural)"
    )

    parser.add_argument(
        "--rate",
        default="+0%",
        help="TTS语速 (如: +20%%, -10%%)"
    )

    parser.add_argument(
        "--volume",
        type=float,
        default=0.7,
        help="播放音量 (0.0-1.0, 默认: 0.7)"
    )

    return parser.parse_args()


def setup_logging(level: str = "INFO", enable_debug: bool = False):
    """设置日志"""
    if enable_debug:
        level = "DEBUG"

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%H:%M:%S"
    )


def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════╗
║     抖音弹幕语音播报工具 v0.1.0                  ║
║     LiveStreamInfoRetrievalProject               ║
╚══════════════════════════════════════════════════╝
"""
    print(banner)


async def main_async():
    """异步主函数"""
    # 解析参数
    args = parse_arguments()

    # 设置日志
    setup_logging(enable_debug=args.debug)

    # 创建编排器
    orchestrator = DanmakuOrchestrator(
        room_id=args.room_id,
        config_path=args.config,
        use_mock=args.mock,
        use_real=args.real
    )

    # 初始化
    if not await orchestrator.initialize():
        logger.error("初始化失败")
        return 1

    # 设置信号处理（仅Unix系统）
    if sys.platform != "win32":
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(orchestrator.shutdown()))

    # 运行主循环
    await orchestrator.run()

    return 0


def main():
    """主程序入口"""
    print_banner()

    try:
        exit_code = asyncio.run(main_async())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n用户中断，正在退出...")
        sys.exit(0)


if __name__ == "__main__":
    main()
