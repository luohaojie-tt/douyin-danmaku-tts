"""
文字转语音模块

包含 Edge-TTS 文字转语音功能。
"""

from src.tts.edge_tts import EdgeTTSEngine, default_tts

__all__ = [
    'EdgeTTSEngine',
    'default_tts',
]
