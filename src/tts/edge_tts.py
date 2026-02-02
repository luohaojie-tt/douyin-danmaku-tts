"""
Edge-TTS 文字转语音引擎

封装 Microsoft Edge Text-to-Speech API，提供异步文字转语音功能。
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import edge_tts

logger = logging.getLogger(__name__)


class EdgeTTSEngine:
    """
    Edge-TTS 文字转语音引擎

    封装 edge-tts 库，提供简化的异步接口
    """

    # 默认音色（中文女声）
    DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"

    # 可用音色列表（常用）
    AVAILABLE_VOICES = {
        "zh-CN-XiaoxiaoNeural": "晓晓（女声，温柔）",
        "zh-CN-YunxiNeural": "云希（男声，温和）",
        "zh-CN-YunyangNeural": "云扬（男声，沉稳）",
        "zh-CN-XiaoyiNeural": "晓伊（女声，亲切）",
        "zh-CN-YunjianNeural": "云健（男声，稳重）",
        "zh-CN-XiaohanNeural": "晓涵（女声，清新）",
        "zh-CN-XiaomengNeural": "晓梦（女声，可爱）",
        "zh-CN-XiaoxuanNeural": "晓萱（女声，成熟）",
        "zh-CN-XiaoruiNeural": "晓睿（女声，知性）",
    }

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        rate: str = "+0%",
        volume: str = "+0%"
    ):
        """
        初始化 TTS 引擎

        Args:
            voice: 音色名称，默认 "zh-CN-XiaoxiaoNeural"
            rate: 语速调整，格式 "+0%" (范围 -50% 到 +100%)
            volume: 音量调整，格式 "+0%" (范围 -50% 到 +100%)
        """
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self._validate_parameters()

        # 统计信息
        self.total_conversions = 0
        self.total_chars = 0

    def _validate_parameters(self):
        """验证参数"""
        if self.voice not in self.AVAILABLE_VOICES:
            logger.warning(f"未知音色: {self.voice}，使用默认音色")
            self.voice = self.DEFAULT_VOICE

        # 验证 rate 格式
        if not isinstance(self.rate, str) or not self.rate.endswith("%"):
            logger.warning(f"rate 格式错误: {self.rate}，使用默认值 +0%")
            self.rate = "+0%"

        # 验证 volume 格式
        if not isinstance(self.volume, str) or not self.volume.endswith("%"):
            logger.warning(f"volume 格式错误: {self.volume}，使用默认值 +0%")
            self.volume = "+0%"

    async def convert(self, text: str) -> Optional[bytes]:
        """
        将文本转换为音频数据（MP3格式）

        Args:
            text: 要转换的文本

        Returns:
            bytes: MP3 音频数据，失败返回 None
        """
        if not text or not text.strip():
            logger.warning("文本为空，跳过转换")
            return None

        try:
            logger.debug(f"开始转换文本: {text[:50]}...")

            # 创建 communicate 对象
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                volume=self.volume
            )

            # 获取音频数据（异步生成器）
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])

            # 合并音频数据
            audio_data = b"".join(audio_chunks)

            # 更新统计
            self.total_conversions += 1
            self.total_chars += len(text)

            logger.debug(f"转换成功: {len(audio_data)} 字节")
            return audio_data

        except Exception as e:
            logger.error(f"转换失败: {e}")
            return None

    async def convert_to_file(
        self,
        text: str,
        output_path: Path
    ) -> bool:
        """
        将文本转换为音频文件

        Args:
            text: 要转换的文本
            output_path: 输出文件路径（.mp3）

        Returns:
            bool: 是否成功
        """
        if not text or not text.strip():
            logger.warning("文本为空，跳过转换")
            return False

        try:
            # 确保输出目录存在
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            logger.debug(f"开始转换到文件: {output_path}")

            # 创建 communicate 对象
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                volume=self.volume
            )

            # 保存到文件
            await communicate.save(str(output_path))

            # 更新统计
            self.total_conversions += 1
            self.total_chars += len(text)

            logger.info(f"音频已保存: {output_path}")
            return True

        except Exception as e:
            logger.error(f"保存音频失败: {e}")
            return False

    async def convert_with_cache(
        self,
        text: str,
        cache_dir: Path = Path("cache")
    ) -> Optional[Path]:
        """
        转换文本为音频文件（带缓存）

        根据文本内容生成缓存键，如果缓存存在则直接返回

        Args:
            text: 要转换的文本
            cache_dir: 缓存目录

        Returns:
            Path: 音频文件路径，失败返回 None
        """
        import hashlib

        # 生成缓存键（文本 + 音色 + 语速）
        cache_key = f"{text}_{self.voice}_{self.rate}"
        cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
        cache_file = cache_dir / f"{cache_hash}.mp3"

        # 检查缓存
        if cache_file.exists():
            logger.debug(f"缓存命中: {cache_file.name}")
            return cache_file

        # 转换并保存
        if await self.convert_to_file(text, cache_file):
            return cache_file

        return None

    @classmethod
    def get_available_voices(cls) -> dict:
        """获取可用音色列表"""
        return cls.AVAILABLE_VOICES.copy()

    @classmethod
    def print_voices(cls):
        """打印可用音色列表"""
        print("\n可用音色列表:")
        print("-" * 50)
        for voice_id, voice_name in cls.AVAILABLE_VOICES.items():
            print(f"  {voice_id:30} : {voice_name}")
        print("-" * 50)

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_conversions": self.total_conversions,
            "total_chars": self.total_chars,
            "voice": self.voice,
            "rate": self.rate,
            "volume": self.volume,
        }


# 默认 TTS 引擎实例
default_tts = EdgeTTSEngine()
