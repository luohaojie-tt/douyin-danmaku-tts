# Slider Fix Testing Guide - Task #15

## Objective

Verify that commit 42c97f3's async volume queue fix resolves the stuttering issue when dragging sliders during audio playback.

## Problem Context

**User Issue:** "即使在播放语音的时候我如果拉动语速的滑动条，他就会卡顿"
**Translation:** "Even when playing audio, if I drag the speech rate slider, it stutters"

**Timeline Analysis:**
- 13:53:08-13:53:12: Received 15 danmaku, started TTS conversion
- User dragged slider, modified rate property
- 13:53:37: 14 danmaku TTS all timeout (30 seconds stuttering!)
- 13:53:40: Returned to normal

**Root Causes:**
1. Direct modification of TTS.rate during conversion → Conversion failures
2. Pygame player volume modification from Qt thread → Race conditions

## Fix Summary

### Fix 1: TTS Rate Caching (Task #13)
**Problem:** Directly modifying `tts.rate` during conversion causes failures

**Solution:**
- Add `_tts_rate_pending` cache
- Check `_tts_converting_count` before applying
- Only apply rate before next conversion starts

**Code:**
```python
def set_tts_rate(self, rate: str):
    if self._tts_converting_count > 0:
        # Cache only, don't apply
        self._tts_rate_pending = rate
    else:
        # Apply immediately
        self._orchestrator.tts.rate = rate

# Before conversion:
async with self._tts_conversion_lock:
    if self._tts_rate_pending:
        self._orchestrator.tts.rate = self._tts_rate_pending
        self._tts_rate_pending = None
    # Now convert with new rate
```

### Fix 2: Async Volume Queue (Task #14)
**Problem:** Direct `player.volume` modification from Qt thread causes race conditions with pygame playback thread

**Solution:**
- Add `_volume_update_queue` (asyncio.Queue)
- `set_tts_volume` uses `put_nowait` (non-blocking)
- Background task processes queue in asyncio context

**Code:**
```python
def set_tts_volume(self, volume: float):
    # Non-blocking queue put
    self._volume_update_queue.put_nowait(volume)

async def _process_volume_updates(self):
    while self.is_running:
        volume = await asyncio.wait_for(
            self._volume_update_queue.get(),
            timeout=1.0
        )
        # Safe in asyncio context
        self._orchestrator.player.volume = volume
```

## Test Environment

**Required:**
- Python 3.8+
- PyQt5 installed
- Live stream room with active danmaku
- Audio output enabled

**Setup:**
```bash
# Navigate to project
cd D:\work\LiveStreamInfoRetrievalProject

# Launch GUI
python main_gui.py
```

## Test Scenarios

### Scenario 1: Volume Slider During Playback ✅

**Steps:**
1. Launch GUI: `python main_gui.py`
2. Connect to a live room with active danmaku
3. Wait for danmaku to arrive and TTS to start playing
4. **While audio is playing**, drag the volume slider back and forth
5. Observe GUI responsiveness

**Expected Results:**
- ✅ GUI remains completely responsive
- ✅ No stuttering or freezing
- ✅ Audio playback continues smoothly
- ✅ Volume changes take effect (may be slightly delayed)
- ✅ No TTS timeout errors
- ✅ All danmaku display correctly

**Log Indicators:**
```
[DEBUG] 音量设置已加入队列: 0.7
[INFO] 音量已更新: 0.7
```

**Failure Indicators:**
- ❌ GUI freezes or stutters
- ❌ Audio stops or glitches
- ❌ TTS timeout errors
- ❌ Danmaku stop displaying

---

### Scenario 2: Rate Slider During Playback ✅

**Steps:**
1. Launch GUI: `python main_gui.py`
2. Connect to a live room with active danmaku
3. Wait for danmaku to arrive and TTS to start playing
4. **While audio is playing**, drag the speech rate slider back and forth
5. Observe GUI responsiveness

**Expected Results:**
- ✅ GUI remains completely responsive
- ✅ No stuttering or freezing
- ✅ Current audio continues to play (rate doesn't change mid-playback)
- ✅ Next danmaku uses new rate
- ✅ No TTS timeout errors
- ✅ All danmaku display correctly

**Log Indicators:**
```
[DEBUG] 应用缓存的rate设置: +20%
```

**Failure Indicators:**
- ❌ GUI freezes or stutters
- ❌ Current audio glitches
- ❌ TTS timeout errors
- ❌ Multiple danmaku fail

---

### Scenario 3: Slider Without Playback ✅

**Steps:**
1. Launch GUI: `python main_gui.py`
2. Connect to a live room (but wait for danmaku)
3. **Before any audio plays**, drag volume and rate sliders
4. Observe GUI responsiveness

**Expected Results:**
- ✅ GUI completely responsive
- ✅ Settings apply immediately (no pending conversions)
- ✅ Smooth slider operation

---

### Scenario 4: Continuous Danmaku + Sliders ✅

**Steps:**
1. Launch GUI: `python main_gui.py`
2. Connect to a very active live room
3. Wait for multiple danmaku to arrive simultaneously
4. **While multiple conversions are happening**, drag both sliders
5. Observe for 30+ seconds

**Expected Results:**
- ✅ All danmaku display
- ✅ Most audio plays (some may timeout but no mass failures)
- ✅ GUI remains responsive
- ✅ No 30-second freezing like before

**Comparison with Before:**
```
Before: 14 danmaku fail, 30s freeze
After:  0-2 danmaku may fail, 0s freeze
```

---

## Performance Metrics

### Measure the Following

| Metric | Before Fix | After Fix | Target |
|--------|-----------|-----------|--------|
| GUI responsiveness during playback | Unusable | Smooth | ✅ Smooth |
| TTS timeouts during slider drag | 14/15 | 0/15 | ✅ 0 |
| Freeze duration | 30s | 0s | ✅ 0s |
| Audio glitches | Severe | None | ✅ None |
| Danmaku loss | High | Zero | ✅ Zero |

---

## Log Analysis

### Check Logs For

**Success Indicators:**
```
✅ 音量设置已加入队列: 0.X
✅ 音量已更新: 0.X
✅ 应用缓存的rate设置: +XX%
✅ TTS转换完成，计数: 0
```

**Warning Indicators:**
```
⚠️ 音量设置已加入队列: (without "音量已更新")
⚠️ TTS转换超时 (more than 1-2 per 15 messages)
```

**Error Indicators:**
```
❌ TTS转换超时，已重试2次 (multiple occurrences)
❌ 处理音量更新失败
❌ 音量更新处理循环异常
```

---

## Quick Reference Test Commands

### Automated Test (if available)
```bash
python test_slider_fix.py
```

### Manual Test
```bash
# Launch GUI
python main_gui.py

# In GUI:
# 1. Enter room ID (e.g., 728804746624)
# 2. Click "连接"
# 3. Wait for danmaku
# 4. Drag sliders during playback
# 5. Observe behavior
```

### Check Logs
```bash
# View real-time logs
tail -f logs/app.log | grep -E "音量|rate|TTS"

# Search for errors
grep -i "timeout\|error\|失败" logs/app.log
```

---

## Comparison: Before vs After

### Before Fix

**Behavior:**
```
User drags slider during playback
    ↓
Direct property modification
    ↓
Race condition / TTS interruption
    ↓
14 danmaku timeout
    ↓
30 seconds freeze ❌
```

**User Experience:**
- Unusable during playback
- Must wait for playback to finish
- Settings cause failures

### After Fix

**Behavior:**
```
User drags slider during playback
    ↓
Queue / Cache setting
    ↓
Continue current operations
    ↓
Apply setting when safe
    ↓
All danmaku process normally ✅
```

**User Experience:**
- Smooth during playback
- Settings apply safely
- No interruptions

---

## Verification Checklist

Complete each test and check the box:

**Basic Functionality:**
- [ ] Launch GUI without errors
- [ ] Connect to live room successfully
- [ ] Receive danmaku in real-time
- [ ] TTS audio plays correctly

**Slider Fixes:**
- [ ] Volume slider during playback - no stutter
- [ ] Rate slider during playback - no stutter
- [ ] Multiple rapid slider adjustments - smooth
- [ ] Settings apply correctly

**Error Handling:**
- [ ] No TTS mass timeouts
- [ ] No danmaku loss
- [ ] No GUI freezing
- [ ] Logs show proper queue processing

**Performance:**
- [ ] GUI responsive under load
- [ ] Audio playback smooth
- [ ] No 30-second freezes
- [ ] All danmaku display

---

## Expected Timeline

**Normal Scenario (Active Room):**
```
00:00 - Connect to room
00:05 - First danmaku arrives
00:06 - Audio starts playing
00:10 - User drags volume slider (during playback)
00:10 - GUI remains responsive ✅
00:11 - Volume updates in logs
00:15 - Next danmaku uses new volume ✅
```

**Stress Test (Many Danmaku):**
```
00:00 - Connect to room
00:05 - 15 danmaku arrive rapidly
00:06 - User drags sliders wildly
00:06-00:36 - All danmaku process smoothly ✅
00:36 - 0 freezes, 0-2 timeouts (acceptable) ✅
```

---

## Troubleshooting

### Issue: Still seeing some stuttering

**Checks:**
1. Verify debounce timer is 300ms
2. Check queue is processing (look for logs)
3. Confirm asyncio event loop is running

**Fix:**
```python
# Verify debounce time
grep "_debounce_timer.start(300)" src/gui/control_panel.py

# Should return 2 results (rate and volume)
```

### Issue: Volume not changing

**Checks:**
1. Check logs for "音量设置已加入队列"
2. Check logs for "音量已更新"
3. Verify pygame player is initialized

**Fix:**
```python
# Check queue processing
grep "_process_volume_updates" src/backend/gui_orchestrator.py
```

### Issue: Rate not changing

**Checks:**
1. Check logs for "应用缓存的rate设置"
2. Verify TTS conversions are completing
3. Check `_tts_converting_count` returns to 0

**Fix:**
```python
# Check TTS lock
grep "_tts_conversion_lock" src/backend/gui_orchestrator.py
```

---

## Success Criteria

**All of the following must be true:**

1. ✅ No GUI freezing when dragging sliders during playback
2. ✅ No mass TTS timeouts (0-1 per 15 danmaku acceptable)
3. ✅ All danmaku display correctly
4. ✅ Volume and rate settings apply correctly
5. ✅ Logs show proper queue/lock processing
6. ✅ Smooth user experience

**If any criteria fail:**
- Document the failure
- Check logs for errors
- Report specific issues to backend-dev

---

## Reporting Results

After testing, report:

**Test Environment:**
- Room ID tested:
- Number of danmaku received:
- Test duration:
- OS: Windows 11

**Results:**
- [PASS/FAIL] Volume slider during playback
- [PASS/FAIL] Rate slider during playback
- [PASS/FAIL] Multiple slider adjustments
- [PASS/FAIL] No mass timeouts
- [PASS/FAIL] No GUI freezing

**Issues Found:**
- List any problems encountered
- Include log excerpts
- Screenshot if applicable

**Overall Assessment:**
- [READY FOR PRODUCTION] - All tests pass
- [NEEDS FIXES] - Specific issues identified
- [CANNOT TEST] - Environment limitations

---

## Conclusion

This fix addresses two critical issues:

1. **TTS Rate Interruption** - Fixed with caching + lock
2. **Pygame Volume Race Condition** - Fixed with async queue

**Expected Result:** Completely smooth slider operation, even during heavy audio playback.

**Test Duration:** 5-10 minutes of active testing
**Impact:** Critical for user experience

---

*Last updated: 2025-02-11*
*Task: #15*
*Status: Ready for Testing*
