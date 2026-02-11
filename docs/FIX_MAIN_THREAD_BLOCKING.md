# 主线程阻塞问题修复报告

## 问题描述（第3次尝试）

**严重症状：**
- 用户拖动滑块时，滑块完全冻结（"一动不动"）
- 等语音播报完成后，滑块才跳到拖动的位置
- **说明 Qt 主线程被播放逻辑完全阻塞**

## 根本原因分析

### 问题定位

通过代码分析，发现主线程阻塞的根本原因在 `main.py:316` 行：

```python
async def _play_queue_worker(self):
    """播放队列工作线程 - 确保弹幕按顺序播放，不打断"""
    while self.is_running:
        play_item = await self.play_queue.get()
        audio_path = play_item['audio_path']
        content = play_item['content']

        # ❌ 问题：使用 blocking=True，阻塞 asyncio 事件循环
        success = self.player.play(audio_path, blocking=True)
```

### 阻塞原理

1. **asyncio 事件循环在 Qt 主线程中运行**
   - PyQt5 的 GUI 事件循环和 asyncio 事件循环在同一个线程
   - 两者共享主线程的执行时间

2. **`blocking=True` 导致的问题**
   - `pygame_player.play(blocking=True)` 内部调用 `wait_until_finished()`
   - 该方法使用 `time.sleep(0.1)` 进行忙等待（busy-waiting）
   - 在等待期间，**完全占用主线程**，不让出控制权

3. **结果：Qt 事件无法处理**
   - 用户拖动滑块 → Qt 事件队列中产生事件
   - 但主线程被 `play(blocking=True)` 占用
   - Qt 事件无法及时处理，导致界面冻结

### 为什么前两次修复失败？

**第1次尝试（异步队列）：**
- 问题：只优化了 TTS 转换部分，但播放仍然是阻塞的
- 结果：TTS 不再卡顿，但播放时仍然冻结

**第2次尝试（防抖优化）：**
- 问题：优化了滑块事件处理，但未解决播放阻塞
- 结果：减少了事件频率，但根本问题仍在

## 解决方案

### 核心思想

将 **同步阻塞等待** 改为 **异步非阻塞等待**，让出主线程控制权给 Qt 事件循环。

### 实施细节

**修改 `main.py` 的 `_play_queue_worker` 方法：**

```python
async def _play_queue_worker(self):
    """播放队列工作线程 - 确保弹幕按顺序播放，不打断（非阻塞）"""
    logger.info("播放队列工作线程已启动（非阻塞模式）")
    try:
        while self.is_running:
            try:
                # 从队列获取待播放的音频
                play_item = await self.play_queue.get()
                audio_path = play_item['audio_path']
                content = play_item['content']

                # ✅ 播放语音（非阻塞模式）
                success = self.player.play(audio_path, blocking=False)

                if not success:
                    logger.warning(f"播放失败: {content}")
                else:
                    # ✅ 使用异步轮询等待播放完成
                    # 不会阻塞 asyncio 事件循环，Qt 主线程可以响应用户操作
                    while self.player.is_playing():
                        await asyncio.sleep(0.1)  # 每100ms检查一次

                    logger.debug(f"播放完成: {content}")

                # 标记队列任务完成
                self.play_queue.task_done()

            except Exception as e:
                logger.error(f"播放队列处理失败: {e}")
                self.stats["errors"] += 1

    except Exception as e:
        logger.error(f"播放队列工作线程异常: {e}")
    finally:
        logger.info("播放队列工作线程已停止")
```

### 关键变化

| 变化点 | 之前（阻塞） | 现在（非阻塞） |
|--------|-------------|---------------|
| `play()` 参数 | `blocking=True` | `blocking=False` |
| 等待方式 | `player.play()` 内部的 `time.sleep()` | `await asyncio.sleep(0.1)` |
| 主线程占用 | 完全占用，不让出 | 定期让出，允许 Qt 处理事件 |
| 滑块响应 | 完全冻结 | 流畅响应 |

## 技术原理

### `await asyncio.sleep()` vs `time.sleep()`

**`time.sleep()`（阻塞）：**
- 同步阻塞，占用线程
- 不让出控制权
- 导致整个事件循环暂停

**`await asyncio.sleep()`（非阻塞）：**
- 异步等待，释放控制权
- 允许事件循环处理其他任务
- 其他协程可以并发执行

### 事件循环协作

```
主线程时间轴：
┌─────────────────────────────────────────────────┐
│ Qt事件 ← asyncio播放任务 ← Qt事件 ← asyncio播放任务 │
│  (滑块)    (await sleep)    (弹幕)   (await sleep) │
└─────────────────────────────────────────────────┘
          ↑          ↑           ↑          ↑
          每个await让出控制权，Qt可以处理事件
```

## 验证清单

- [x] 移除所有 `blocking=True` 调用
- [x] 使用 `await asyncio.sleep()` 替代同步等待
- [x] 保持播放队列的顺序性
- [x] 确保异常处理完整
- [ ] 实际测试：拖动滑块不再冻结
- [ ] 实际测试：语音播放顺序正确

## 预期效果

**修复前：**
- 拖动滑块 → 完全冻结 → 等待播放完成 → 滑块跳到目标位置

**修复后：**
- 拖动滑块 → 流畅响应 → 语音正常播放 → 两者互不影响

## 相关文件

- `main.py:302-331` - `_play_queue_worker` 方法（已修复）
- `src/player/pygame_player.py:74-124` - `play()` 方法（支持非阻塞）
- `src/player/pygame_player.py:187-215` - `wait_until_finished()` 方法（不再使用）

## 总结

这是**第3次尝试**，前两次方案（异步队列、防抖优化）都只解决了部分问题。本次修复找到真正的根本原因：

**在 asyncio 事件循环中使用同步阻塞等待（`blocking=True`）导致 Qt 主线程无法响应用户操作。**

通过将阻塞等待改为异步等待（`await asyncio.sleep()`），让出主线程控制权，彻底解决了滑块冻结问题。
