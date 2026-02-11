"""
滑块卡顿问题深度分析报告

## 诊断结果

### 测试数据：
1. pygame.mixer.set_volume() 性能：
   - 不播放时：469万次/秒
   - 播放时：1657万次/秒（快3.5倍！）
   
2. Qt信号槽：139万次/秒（非常快）
3. AsyncIO队列：507万次/秒（非常快）

### 关键发现：
**pygame.mixer.set_volume()本身不是瓶颈！**

播放时的音量设置反而更快，说明：
- pygame mixer内部有优化
- 不存在线程安全问题
- 不是跨线程访问导致的卡顿

## 可能的真正原因

### 原因1：LogWidget节流失效
**症状**：每次滑块移动都可能触发UI更新

**检查**：
```bash
grep -n "log_widget" src/gui/main_window.py | grep volume
```

如果MainWindow中仍有log_widget调用，那会导致：
- LogWidget节流（50ms）在频繁调用时仍然会累积
- HTML插入、光标移动、滚动等操作在主线程执行
- 阻塞Qt事件循环

### 原因2：asyncio事件循环阻塞
**症状**：播放器在blocking=True模式，等待播放完成

**问题**：
```python
# main.py:316
success = self.player.play(audio_path, blocking=True)
```

这意味着：
- _play_queue_worker在asyncio任务中阻塞等待
- 如果从Qt主线程调用任何asyncio相关操作，可能会有延迟

但是，set_tts_volume现在使用put_nowait()，应该是非阻塞的...

### 原因3：Qt信号槽的AutoConnection
**症状**：默认连接方式可能导致槽函数在发送者线程执行

**当前连接**：
```python
# main_window.py
self.control_panel.signals.volume_changed.connect(self._on_volume_changed)
```

默认是Qt.AutoConnection，这意味着：
- 如果信号和槽在同一线程：直接调用
- 如果在不同线程：QueuedConnection

但都在Qt主线程，所以是直接调用（同步）！

### 原因4：防抖timer本身的问题
**症状**：QTimer在主线程事件循环中执行

**问题**：
```python
self._volume_debounce_timer.start(300)  # 300ms后发射信号
```

如果在300ms内：
- 主线程处理其他事件（播放器、网络、弹幕）
- 定时器到期时，事件循环忙碌
- 导致延迟感

## 最可能的原因组合

**用户感觉卡顿的真实原因**：

1. **视觉延迟**：300ms防抖 + 事件循环处理时间 = 用户感觉到延迟
2. **UI更新累积**：即使移除了MainWindow的log_widget.info，LogWidget仍在接收其他信号
3. **播放器阻塞**：虽然blocking在asyncio任务中，但可能影响整体性能

## 建议的修复方向

### 立即修复：
1. **检查是否还有UI日志更新**
   ```bash
   grep -rn "log_widget\." src/gui/main_window.py | grep -v "#"
   ```

2. **减少防抖时间**：300ms → 150ms
   - 100ms太短（之前验证过）
   - 150ms可能是最佳平衡点

3. **添加loading状态指示**
   - 拖动时显示"设置中..."
   - 给用户明确反馈

### 深度优化：
1. **将播放器改为非阻塞模式**
   ```python
   # 不使用blocking=True
   # 改为使用事件回调
   ```

2. **使用QApplication.processEvents()**
   - 在长时间操作中定期处理事件

3. **性能分析**
   - 使用Python profiler找出真正的瓶颈
   - 使用Qt的QElapsedTiming测量各部分耗时

## 下一步

请用户运行 diagnose_slider_lag.py 并提供输出，同时：
1. 检查是否有其他log_widget调用
2. 尝试将防抖时间改为150ms
3. 在播放时不拖动滑块，观察是否还卡顿
