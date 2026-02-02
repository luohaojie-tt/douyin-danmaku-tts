"""
Pygame 音频播放器

基于 pygame.mixer 实现音频播放功能。
"""

import logging
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PygamePlayer:
    """
    Pygame 音频播放器

    支持播放 MP3/WAV 等音频文件
    """

    def __init__(self, volume: float = 0.7):
        """
        初始化播放器

        Args:
            volume: 音量 (0.0 - 1.0)
        """
        self.volume = volume
        self._initialized = False
        self._current_sound = None
        self._is_playing = False

        # 统计信息
        self.total_played = 0
        self.total_duration = 0.0

        self._initialize()

    def _initialize(self):
        """初始化 pygame mixer"""
        try:
            # 尝试导入 pygame 或 pygame-ce
            try:
                import pygame
                import pygame.mixer
                pygame_module = pygame
                pygame_mixer_module = pygame.mixer
            except ImportError:
                import pygame_ce as pygame
                import pygame_ce.mixer as pygame_mixer
                pygame_module = pygame
                pygame_mixer_module = pygame_mixer

            # 初始化 pygame mixer
            pygame_mixer_module.init(frequency=44100, size=-16, channels=2, buffer=512)

            # 设置音量
            pygame_mixer_module.music.set_volume(self.volume)

            self._initialized = True
            self._pygame = pygame_module
            self._pygame_mixer = pygame_mixer_module

            logger.info(f"Pygame播放器初始化成功 (音量: {self.volume})")

        except ImportError:
            logger.error("pygame 未安装，请运行: pip install pygame-ce")
            raise
        except Exception as e:
            logger.error(f"初始化 pygame 失败: {e}")
            raise

    def play(self, audio_path: Path, blocking: bool = False) -> bool:
        """
        播放音频文件

        Args:
            audio_path: 音频文件路径
            blocking: 是否阻塞等待播放完成

        Returns:
            bool: 是否开始播放
        """
        if not self._initialized:
            logger.error("播放器未初始化")
            return False

        audio_path = Path(audio_path)

        if not audio_path.exists():
            logger.error(f"音频文件不存在: {audio_path}")
            return False

        try:
            # 停止当前播放
            self.stop()

            # 加载音频文件
            logger.debug(f"加载音频: {audio_path.name}")
            self._current_sound = self._pygame_mixer.Sound(str(audio_path))

            # 设置音量
            self._current_sound.set_volume(self.volume)

            # 播放
            self._current_sound.play()
            self._is_playing = True

            logger.info(f"开始播放: {audio_path.name}")

            # 更新统计
            self.total_played += 1

            # 如果需要阻塞等待
            if blocking:
                self.wait_until_finished()

            return True

        except Exception as e:
            logger.error(f"播放失败: {e}")
            self._is_playing = False
            return False

    def play_bytes(self, audio_data: bytes, blocking: bool = False) -> bool:
        """
        播放音频数据（bytes）

        注意: pygame.mixer.Sound 需要 WAV 格式，MP3 不支持直接从 bytes 播放

        Args:
            audio_data: 音频数据（bytes）
            blocking: 是否阻塞等待播放完成

        Returns:
            bool: 是否开始播放
        """
        if not self._initialized:
            logger.error("播放器未初始化")
            return False

        if not audio_data:
            logger.error("音频数据为空")
            return False

        try:
            # 停止当前播放
            self.stop()

            # 从 bytes 创建 Sound 对象
            import io
            audio_file = io.BytesIO(audio_data)
            self._current_sound = self._pygame_mixer.Sound(audio_file)

            # 设置音量
            self._current_sound.set_volume(self.volume)

            # 播放
            self._current_sound.play()
            self._is_playing = True

            logger.info("开始播放音频数据")

            # 更新统计
            self.total_played += 1

            # 如果需要阻塞等待
            if blocking:
                self.wait_until_finished()

            return True

        except Exception as e:
            logger.error(f"播放音频数据失败: {e}")
            logger.warning("注意: pygame 只支持 WAV 格式的 bytes，MP3 请使用文件路径")
            self._is_playing = False
            return False

    def stop(self):
        """停止当前播放"""
        if self._current_sound and self._is_playing:
            self._current_sound.stop()
            self._is_playing = False
            logger.debug("播放已停止")

    def wait_until_finished(self, timeout: Optional[float] = None):
        """
        等待播放完成

        Args:
            timeout: 超时时间（秒），None 表示无限等待
        """
        if not self._is_playing:
            return

        start_time = time.time()

        while self._is_playing:
            if timeout and (time.time() - start_time) > timeout:
                logger.warning(f"等待播放超时: {timeout}秒")
                break

            time.sleep(0.1)

            # 检查是否还在播放
            if self._current_sound:
                # pygame.mixer.Sound.get_length() 获取音频长度
                # 但无法直接检测是否播放完成，这里用简单方法
                # 实际项目中可能需要更精确的检测
                if not self._pygame_mixer.get_busy():
                    self._is_playing = False
                    break

        logger.debug("播放完成")

    def set_volume(self, volume: float):
        """
        设置音量

        Args:
            volume: 音量 (0.0 - 1.0)
        """
        if not (0.0 <= volume <= 1.0):
            logger.warning(f"音量值 {volume} 超出范围 [0.0, 1.0]，已限制")
            volume = max(0.0, min(1.0, volume))

        self.volume = volume

        if self._initialized:
            self._pygame_mixer.music.set_volume(volume)
            if self._current_sound:
                self._current_sound.set_volume(volume)

        logger.debug(f"音量设置为: {volume}")

    def get_volume(self) -> float:
        """获取当前音量"""
        return self.volume

    def is_playing(self) -> bool:
        """是否正在播放"""
        if self._initialized:
            return self._pygame_mixer.get_busy() and self._is_playing
        return False

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_played": self.total_played,
            "total_duration": self.total_duration,
            "volume": self.volume,
            "is_playing": self.is_playing(),
        }

    def cleanup(self):
        """清理资源"""
        self.stop()
        if self._initialized:
            self._pygame_mixer.quit()
            self._pygame.quit()
            self._initialized = False
            logger.info("Pygame播放器已清理")


# 播放器单例
_default_player: Optional[PygamePlayer] = None


def get_default_player() -> PygamePlayer:
    """获取默认播放器实例"""
    global _default_player
    if _default_player is None:
        _default_player = PygamePlayer()
    return _default_player


def play_audio_file(audio_path: Path, volume: float = 0.7, blocking: bool = False) -> bool:
    """
    便捷函数：播放音频文件

    Args:
        audio_path: 音频文件路径
        volume: 音量 (0.0 - 1.0)
        blocking: 是否阻塞等待

    Returns:
        bool: 是否成功播放
    """
    player = get_default_player()
    player.set_volume(volume)
    return player.play(audio_path, blocking=blocking)
