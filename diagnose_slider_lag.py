#!/usr/bin/env python3
"""
诊断滑块卡顿问题的测试脚本

测试场景：
1. 检查pygame mixer是否线程安全
2. 测试音量设置的性能
3. 模拟播放时修改音量
"""

import sys
import time
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_pygame_volume_performance():
    """测试pygame音量设置性能"""
    print("\n" + "="*60)
    print("测试1: Pygame音量设置性能")
    print("="*60)
    
    try:
        import pygame
        import pygame.mixer
        
        pygame.mixer.init()
        
        # 创建一个测试音频文件（静音）
        import tempfile
        import numpy as np
        
        # 生成1秒静音
        sample_rate = 44100
        duration = 1  # 秒
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_data = np.zeros_like(t, dtype=np.int16)
        
        # 保存为临时wav文件
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            temp_file = f.name
        
        # 使用wave模块保存
        import wave
        import struct
        
        with wave.open(temp_file, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        # 测试音量设置性能
        sound = pygame.mixer.Sound(temp_file)
        
        print("\n测试A: 不播放时设置音量（1000次）")
        start = time.time()
        for i in range(1000):
            sound.set_volume(i / 1000)
        elapsed = time.time() - start
        print(f"耗时: {elapsed:.3f}秒")
        print(f"平均: {elapsed*1000:.3f}毫秒/次")
        print(f"频率: {1000/elapsed:.0f}次/秒")
        
        print("\n测试B: 播放时设置音量（1000次）")
        sound.play()
        start = time.time()
        for i in range(1000):
            sound.set_volume(i / 1000)
        elapsed = time.time() - start
        print(f"耗时: {elapsed:.3f}秒")
        print(f"平均: {elapsed*1000:.3f}毫秒/次")
        print(f"频率: {1000/elapsed:.0f}次/秒")
        
        sound.stop()
        
        # 清理
        import os
        os.unlink(temp_file)
        pygame.mixer.quit()
        
        print("\n结论: 如果测试B明显比测试A慢，说明pygame.mixer在播放时音量设置有性能问题")
        
    except ImportError as e:
        print(f"pygame未安装: {e}")
        return False
    except Exception as e:
        print(f"测试失败: {e}")
        return False
    
    print("\n" + "="*60)
    return True


def test_signal_slot_performance():
    """测试Qt信号槽性能"""
    print("\n" + "="*60)
    print("测试2: Qt信号槽性能")
    print("="*60)
    
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QObject, pyqtSignal
        
        app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
        
        class TestEmitter(QObject):
            test_signal = pyqtSignal(float)
        
        class TestReceiver(QObject):
            def __init__(self):
                super().__init__()
                self.call_count = 0
            
            def on_test_signal(self, value: float):
                # 模拟set_tts_volume的操作
                self.call_count += 1
        
        emitter = TestEmitter()
        receiver = TestReceiver()
        emitter.test_signal.connect(receiver.on_test_signal)
        
        print("\n测试: 信号发射性能（1000次）")
        start = time.time()
        for i in range(1000):
            emitter.test_signal.emit(i / 1000)
        elapsed = time.time() - start
        
        print(f"耗时: {elapsed:.3f}秒")
        print(f"平均: {elapsed*1000:.3f}毫秒/次")
        print(f"频率: {1000/elapsed:.0f}次/秒")
        print(f"接收次数: {receiver.call_count}")
        
        print("\n结论: 如果这个测试很慢，说明Qt信号槽本身有性能问题")
        
    except Exception as e:
        print(f"测试失败: {e}")
        return False
    
    print("\n" + "="*60)
    return True


def test_asyncio_queue_performance():
    """测试asyncio队列性能"""
    print("\n" + "="*60)
    print("测试3: AsyncIO队列性能")
    print("="*60)
    
    async def test():
        queue = asyncio.Queue()
        
        print("\n测试: put_nowait性能（1000次）")
        start = time.time()
        for i in range(1000):
            queue.put_nowait(i / 1000)
        elapsed = time.time() - start
        
        print(f"耗时: {elapsed:.3f}秒")
        print(f"平均: {elapsed*1000:.3f}毫秒/次")
        print(f"频率: {1000/elapsed:.0f}次/秒")
        
        print("\n测试: 队列处理性能（1000次）")
        processed = 0
        start = time.time()
        while not queue.empty():
            value = queue.get_nowait()
            # 模拟设置操作
            processed += 1
        elapsed = time.time() - start
        
        print(f"耗时: {elapsed:.3f}秒")
        print(f"处理数量: {processed}")
        
        print("\n结论: 队列操作应该非常快（微秒级）")
    
    try:
        asyncio.run(test())
        return True
    except Exception as e:
        print(f"测试失败: {e}")
        return False
    
    print("\n" + "="*60)
    return True


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("滑块卡顿问题诊断工具")
    print("="*60)
    
    results = []
    
    # 测试1: Pygame性能
    results.append(("Pygame音量设置", test_pygame_volume_performance()))
    
    # 测试2: Qt信号槽
    results.append(("Qt信号槽", test_signal_slot_performance()))
    
    # 测试3: AsyncIO队列
    results.append(("AsyncIO队列", test_asyncio_queue_performance()))
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    for name, success in results:
        status = "✅ 完成" if success else "❌ 失败"
        print(f"{name}: {status}")
    
    print("\n请将结果发送给开发者进行分析")
    print("="*60)


if __name__ == "__main__":
    main()
