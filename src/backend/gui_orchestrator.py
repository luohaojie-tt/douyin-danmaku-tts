"""
GUI Orchestrator - PyQt5 signal-enabled wrapper for DanmakuOrchestrator

This module wraps the CLI-based DanmakuOrchestrator to emit Qt signals
for GUI integration while preserving all existing functionality.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from .chrome_debug_manager import ChromeDebugManager

logger = logging.getLogger(__name__)


class GUIOrchestrator(QObject):
    """
    GUI-enabled orchestrator that wraps DanmakuOrchestrator with Qt signals

    This class uses composition (not inheritance) to wrap DanmakuOrchestrator
    and add Qt signal emission capabilities.

    Signals:
        message_received: Emitted when a danmaku message is received
            Args:
                user_name (str): Username
                content (str): Message content
                timestamp (str): ISO format timestamp

        connection_changed: Emitted when connection status changes
            Args:
                connected (bool): Connection status
                message (str): Status message

        error_occurred: Emitted when an error occurs
            Args:
                error_type (str): Type of error
                error_message (str): Error details

        stats_updated: Emitted when statistics are updated
            Args:
                stats (dict): Statistics dictionary with keys:
                    - messages_received (int)
                    - messages_played (int)
                    - errors (int)
    """

    # Qt signals definition
    message_received = pyqtSignal(str, str, str)  # user_name, content, timestamp
    connection_changed = pyqtSignal(bool, str)    # connected, message
    error_occurred = pyqtSignal(str, str)         # error_type, error_message
    stats_updated = pyqtSignal(dict)              # stats dictionary

    def __init__(
        self,
        room_id: str,
        config_path: str = "config.ini",
        use_mock: bool = False,
        use_real: bool = False,
        use_http: bool = False,
        use_ws: bool = False
    ):
        """
        Initialize GUI Orchestrator

        Args:
            room_id: 直播间房间ID
            config_path: 配置文件路径
            use_mock: 是否使用Mock连接器
            use_real: 是否使用真实连接器（Playwright）
            use_http: 是否使用HTTP轮询连接器
            use_ws: 是否使用WebSocket监听连接器（推荐）
        """
        super().__init__()

        # Import DanmakuOrchestrator here to avoid circular imports
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from main import DanmakuOrchestrator

        # Create the base orchestrator instance (composition)
        self._orchestrator = DanmakuOrchestrator(
            room_id=room_id,
            config_path=config_path,
            use_mock=use_mock,
            use_real=use_real,
            use_http=use_http,
            use_ws=use_ws
        )

        # Message history for export functionality
        self.message_history: list[Dict[str, Any]] = []

        # Timer for asyncio event loop integration
        self._asyncio_timer = None
        self._loop = None

        # Chrome debug mode manager
        self._chrome_manager = ChromeDebugManager()

        # TTS enabled state
        self._tts_enabled = True

        # TTS settings cache（避免直接修改TTS对象）
        self._tts_rate_pending = None  # 待应用的rate设置
        self._tts_volume_pending = None  # 待应用的volume设置

        # TTS conversion state lock
        self._tts_conversion_lock = asyncio.Lock()
        self._tts_converting_count = 0

        logger.info("GUIOrchestrator initialized")

    # ========== Property Accessors (delegate to base orchestrator) ==========

    @property
    def room_id(self) -> str:
        """Get room ID"""
        return self._orchestrator.room_id

    @property
    def stats(self) -> dict:
        """Get statistics dictionary"""
        return self._orchestrator.stats

    @property
    def is_running(self) -> bool:
        """Check if orchestrator is running"""
        return self._orchestrator.is_running

    # ========== Public Methods ==========

    async def initialize(self):
        """
        Initialize all modules

        Returns:
            bool: True if initialization successful
        """
        try:
            success = await self._orchestrator.initialize()

            if success:
                logger.info("GUIOrchestrator initialization complete")
                self.connection_changed.emit(True, "初始化完成")
            else:
                logger.error("GUIOrchestrator initialization failed")
                self.connection_changed.emit(False, "初始化失败")
                self.error_occurred.emit("InitializationError", "Failed to initialize orchestrator")

            return success

        except Exception as e:
            logger.error(f"Initialization failed with exception: {e}")
            self.connection_changed.emit(False, "初始化失败")
            self.error_occurred.emit("InitializationError", str(e))
            return False

    async def handle_message(self, raw_message):
        """
        Handle incoming message and emit Qt signals

        Args:
            raw_message: Raw message from connector
        """
        # Create background task for message processing
        asyncio.create_task(self._process_message_with_signals(raw_message))

    async def _process_message_with_signals(self, raw_message):
        """
        Process message and emit Qt signals (GUI version)

        This extends the base orchestrator's logic by:
        1. Emitting message_received signal
        2. Storing message in history for export
        3. Emitting stats_updated signal
        4. Emitting error_occurred signal on errors
        """
        try:
            # Parse message (reuse base logic)
            from src.douyin.parser_http import ParsedMessage as HttpParsedMessage
            from src.douyin.connector_websocket_listener import ParsedMessage as WsParsedMessage

            parser = self._orchestrator.parser

            if isinstance(raw_message, (HttpParsedMessage, WsParsedMessage)):
                parsed = raw_message
            elif isinstance(raw_message, dict):
                # Mock连接器返回的是字典格式
                parsed = parser.parse_test_message(raw_message)
            elif isinstance(raw_message, bytes):
                # 真实连接器返回的是二进制数据
                if self._orchestrator.use_real:
                    parsed = parser.parse_message(raw_message)
                else:
                    parsed = await parser.parse_message(raw_message)
            else:
                logger.warning(f"未知消息类型: {type(raw_message)}")
                return

            if not parsed:
                logger.debug("消息解析失败，跳过")
                return

            self._orchestrator.stats["messages_received"] += 1
            logger.info(f"收到消息: {parsed.method}")

            # 只处理聊天消息
            if parsed.method != "WebChatMessage":
                logger.debug(f"跳过非聊天消息: {parsed.method}")
                return

            # 提取弹幕内容
            if not parsed.content:
                logger.debug("消息内容为空，跳过")
                return

            user_name = parsed.user.nickname if parsed.user else "用户"
            content = parsed.content
            timestamp = datetime.now().isoformat()

            # ========== EMIT SIGNAL: Message Received ==========
            self.message_received.emit(user_name, content, timestamp)

            # ========== Store in history for export ==========
            self.message_history.append({
                "timestamp": timestamp,
                "user_name": user_name,
                "content": content,
                "method": parsed.method
            })

            # ========== Print to console (keep CLI output for debugging) ==========
            import sys
            if sys.platform == 'win32':
                print()
                print("=" * 60)
                print(f"[弹幕] {user_name}")
                print(f"[内容] {content}")
                print("=" * 60)
                print()
            else:
                print()
                print("=" * 60)
                print(f"📺 弹幕: [{user_name}]")
                print(f"💬 内容: {content}")
                print("=" * 60)
                print()

            # ========== TTS Conversion ==========
            logger.info(f"正在转换语音: {content}")

            # 获取TTS转换锁（避免设置时打断正在进行的转换）
            async with self._tts_conversion_lock:
                self._tts_converting_count += 1
                logger.debug(f"TTS转换计数: {self._tts_converting_count}")

                # 在转换前应用缓存的设置（如果有）
                if self._tts_rate_pending:
                    self._orchestrator.tts.rate = self._tts_rate_pending
                    logger.info(f"应用缓存的rate设置: {self._tts_rate_pending}")
                    self._tts_rate_pending = None

                if self._tts_volume_pending:
                    self._orchestrator.player.volume = self._tts_volume_pending
                    logger.info(f"应用缓存的volume设置: {self._tts_volume_pending}")
                    self._tts_volume_pending = None

                # TTS转换带重试机制
                tts = self._orchestrator.tts
                audio_path = None
                max_retries = 2

                for attempt in range(max_retries):
                try:
                    audio_path = await asyncio.wait_for(
                        tts.convert_with_cache(
                            text=content,
                            cache_dir=Path("cache")
                        ),
                        timeout=10.0  # 增加到10秒，减少超时
                    )

                    if audio_path:
                        break

                except asyncio.TimeoutError:
                    if attempt < max_retries - 1:
                        logger.warning(f"TTS转换超时（10秒），第{attempt + 1}次重试: {content}")
                        await asyncio.sleep(0.5)
                    else:
                        error_msg = f"TTS转换超时，已重试{max_retries}次: {content}"
                        logger.error(error_msg)
                        self.error_occurred.emit("TTSTimeout", error_msg)
                        # 不return，继续处理后续弹幕，只是这条不播报语音
                        logger.info(f"弹幕将显示但不播报语音: {content}")
                except Exception as e:
                    error_msg = f"TTS转换失败: {e}: {content}"
                    logger.warning(error_msg)
                    self.error_occurred.emit("TTSError", str(e))
                    # 不return，继续处理后续弹幕，只是这条不播报语音
                    logger.info(f"弹幕将显示但不播报语音: {content}")

                # ========== Add to play queue ==========
                if audio_path:
                    # 只有成功转换才加入播放队列
                    await self._orchestrator.play_queue.put({
                        'audio_path': audio_path,
                        'content': content
                    })

                    self._orchestrator.stats["messages_played"] += 1
                    logger.info(f"加入播放队列 (总计: {self._orchestrator.stats['messages_played']})")
                else:
                    # TTS失败，记录但不影响弹幕显示
                    logger.warning(f"该弹幕未播放语音: {content}")

                # 释放锁
                self._tts_converting_count -= 1
                logger.debug(f"TTS转换完成，剩余计数: {self._tts_converting_count}")
            # lock自动释放（async with）

            # ========== EMIT SIGNAL: Stats Updated ==========
            self.stats_updated.emit(self._orchestrator.stats.copy())

        except Exception as e:
            error_msg = f"处理消息失败: {e}"
            logger.error(error_msg)
            self._orchestrator.stats["errors"] += 1
            self.error_occurred.emit("MessageProcessingError", str(e))
            self.stats_updated.emit(self._orchestrator.stats.copy())

    async def run(self):
        """
        Run main loop

        Returns:
            bool: True if run completed successfully
        """
        try:
            # 连接直播间
            logger.info(f"正在连接直播间: {self._orchestrator.room_id}")

            # Replace the orchestrator's handle_message with our signal-emitting version
            original_handle = self._orchestrator.handle_message
            self._orchestrator.handle_message = self.handle_message

            connected = await self._orchestrator.connector.connect()

            if not connected:
                error_msg = "连接直播间失败"
                logger.error(error_msg)
                self.connection_changed.emit(False, error_msg)
                self.error_occurred.emit("ConnectionError", error_msg)
                # Restore original handler
                self._orchestrator.handle_message = original_handle
                return False

            self._orchestrator.is_running = True
            success_msg = "连接成功！开始监听弹幕..."
            logger.info(success_msg)
            self.connection_changed.emit(True, success_msg)

            # 监听消息
            await self._orchestrator.connector.listen(self.handle_message)

        except asyncio.CancelledError:
            logger.info("任务被取消")
            self.connection_changed.emit(False, "任务已取消")
        except KeyboardInterrupt:
            logger.info("用户中断")
            self.connection_changed.emit(False, "用户中断")
        except Exception as e:
            error_msg = f"运行异常: {e}"
            logger.error(error_msg)
            self.connection_changed.emit(False, f"运行异常: {str(e)}")
            self.error_occurred.emit("RuntimeError", str(e))
        finally:
            await self.shutdown()

        return True

    async def shutdown(self):
        """Graceful shutdown with signal emission"""
        logger.info("="*60)
        logger.info("正在关闭GUI编排器...")
        logger.info("="*60)

        self._orchestrator.is_running = False

        # Stop playback queue
        if self._orchestrator.play_task:
            logger.info("等待播放队列完成...")
            try:
                await asyncio.wait_for(self._orchestrator.play_queue.join(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("播放队列未在5秒内完成，强制停止")
            except Exception as e:
                logger.error(f"等待播放队列完成时出错: {e}")

            self._orchestrator.play_task.cancel()
            try:
                await self._orchestrator.play_task
            except asyncio.CancelledError:
                pass

        # Disconnect connector
        if self._orchestrator.connector:
            await self._orchestrator.connector.disconnect()

        # Cleanup player
        if self._orchestrator.player:
            self._orchestrator.player.cleanup()

        # Emit final stats
        self.stats_updated.emit(self._orchestrator.stats.copy())

        # Emit connection closed signal
        self.connection_changed.emit(False, "已断开连接")

        # Print statistics
        logger.info("运行统计:")
        logger.info(f"  接收消息: {self._orchestrator.stats['messages_received']}")
        logger.info(f"  播报消息: {self._orchestrator.stats['messages_played']}")
        logger.info(f"  错误次数: {self._orchestrator.stats['errors']}")
        logger.info(f"  历史记录数: {len(self.message_history)}")

        if self._orchestrator.stats['messages_received'] > 0:
            success_rate = (self._orchestrator.stats['messages_played'] / self._orchestrator.stats['messages_received']) * 100
            logger.info(f"  成功率: {success_rate:.1f}%")

        logger.info("="*60)
        logger.info("GUI编排器已安全退出")
        logger.info("="*60)

    def export_to_txt(self, filepath: str) -> bool:
        """
        Export message history to TXT file

        Args:
            filepath: Output file path

        Returns:
            bool: True if export successful
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("弹幕记录导出\n")
                f.write(f"房间ID: {self._orchestrator.room_id}\n")
                f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"消息总数: {len(self.message_history)}\n")
                f.write("=" * 60 + "\n\n")

                for msg in self.message_history:
                    f.write(f"[{msg['timestamp']}] ")
                    f.write(f"{msg['user_name']}: ")
                    f.write(f"{msg['content']}\n")

            logger.info(f"导出TXT成功: {filepath}")
            return True

        except Exception as e:
            logger.error(f"导出TXT失败: {e}")
            self.error_occurred.emit("ExportError", f"Failed to export TXT: {str(e)}")
            return False

    def export_to_json(self, filepath: str) -> bool:
        """
        Export message history to JSON file

        Args:
            filepath: Output file path

        Returns:
            bool: True if export successful
        """
        try:
            import json

            export_data = {
                "room_id": self._orchestrator.room_id,
                "export_time": datetime.now().isoformat(),
                "total_messages": len(self.message_history),
                "stats": self._orchestrator.stats,
                "messages": self.message_history
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            logger.info(f"导出JSON成功: {filepath}")
            return True

        except Exception as e:
            logger.error(f"导出JSON失败: {e}")
            self.error_occurred.emit("ExportError", f"Failed to export JSON: {str(e)}")
            return False

    def get_message_history(self) -> list[Dict[str, Any]]:
        """
        Get message history

        Returns:
            List of message dictionaries
        """
        return self.message_history.copy()

    def clear_history(self):
        """Clear message history"""
        self.message_history.clear()
        logger.info("消息历史已清空")

    def set_tts_enabled(self, enabled: bool):
        """
        Enable/disable TTS playback

        Args:
            enabled: Whether TTS should be enabled
        """
        # Store the setting (actual implementation would need to integrate with player)
        self._tts_enabled = enabled
        logger.info(f"TTS {'enabled' if enabled else 'disabled'}")

    def set_tts_rate(self, rate: str):
        """
        Set TTS playback rate（缓存设置，等待当前转换完成）

        Args:
            rate: Rate string (e.g., "+20%", "-10%")
        """
        if self._orchestrator.tts:
            # 缓存设置，等待当前转换完成后再应用
            self._tts_rate_pending = rate
            logger.info(f"TTS rate已缓存: {rate} (将在下次转换时应用)")

    def set_tts_volume(self, volume: float):
        """
        Set TTS playback volume（缓存设置，等待当前转换完成）

        Args:
            volume: Volume level (0.0-1.0)
        """
        if self._orchestrator.player:
            # 缓存设置，等待当前转换完成后再应用
            self._tts_volume_pending = volume
            logger.info(f"TTS volume已缓存: {volume} (将在下次转换时应用)")

    # ========== Chrome Debug Mode Management ==========

    def check_chrome_debug_mode(self) -> bool:
        """
        Check if Chrome is running in debug mode

        Returns:
            True if Chrome debug port is accessible
        """
        return self._chrome_manager.is_chrome_debug_running()

    def ensure_chrome_debug_mode(
        self,
        kill_existing: bool = False,
        wait_timeout: int = 10
    ) -> tuple[bool, str]:
        """
        Ensure Chrome debug mode is running (start if not)

        This method checks if Chrome is running with remote debugging enabled
        and automatically starts it if needed. Emits appropriate signals for
        UI feedback.

        Args:
            kill_existing: Whether to kill existing Chrome processes first
            wait_timeout: Maximum seconds to wait for Chrome to start

        Returns:
            Tuple of (success, message)
        """
        logger.info("正在检查Chrome调试模式...")

        # Check if already running
        if self._chrome_manager.is_chrome_debug_running():
            msg = "Chrome调试模式已在运行"
            logger.info(msg)
            self.connection_changed.emit(True, msg)
            return True, msg

        # Need to start Chrome
        logger.info("Chrome调试模式未运行，正在启动...")
        self.connection_changed.emit(False, "正在启动Chrome调试模式...")

        success, message = self._chrome_manager.ensure_chrome_debug_mode(
            kill_existing=kill_existing,
            wait_timeout=wait_timeout
        )

        if success:
            logger.info(f"✓ {message}")
            self.connection_changed.emit(True, message)
        else:
            logger.error(f"✗ {message}")
            self.connection_changed.emit(False, message)
            self.error_occurred.emit("ChromeDebugError", message)

        return success, message

    def get_chrome_version(self) -> Optional[str]:
        """
        Get Chrome version

        Returns:
            Chrome version string if found, None otherwise
        """
        return self._chrome_manager.get_chrome_version()
