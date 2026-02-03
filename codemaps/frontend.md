# Frontend Codemap

**Last Updated:** 2026-02-03
**Module:** Command-Line Interface and Output
**Primary Language:** Python 3.x

## Overview

This is a **headless CLI application** with no graphical frontend. The "frontend" consists of the command-line interface in `main.py` and audio output through the system speakers.

## CLI Architecture

```
main.py (Entry Point)
    |
    +-> parse_arguments()      # argparse
    +-> setup_logging()        # logging configuration
    +-> print_banner()         # ASCII art banner
    |
    v
main_async()
    |
    +-> DanmakuOrchestrator
    |       |
    |       +-> initialize()
    |       +-> run()
    |       +-> shutdown()
    |
    v
    sys.exit(exit_code)
```

## Command-Line Interface

### Arguments

```bash
python main.py <room_id> [options]

Positional Arguments:
  room_id                    Live stream room ID (required)

Options:
  --mock                      Use mock connector (no real connection)
  --real                      Use real connector (requires Chrome debug mode)
  --http                      Use HTTP polling connector (requires Chrome)
  --ws                        Use WebSocket listener (requires Chrome)
  --config PATH               Config file path (default: config.ini)
  --debug                     Enable debug logging
  --voice VOICE               TTS voice (e.g., zh-CN-XiaoxiaoNeural)
  --rate RATE                 TTS rate (e.g., +20%)
  --volume VOLUME             Playback volume 0.0-1.0 (default: 0.7)
```

### Usage Examples

```bash
# Standard mode (direct WebSocket)
python main.py 728804746624

# Mock mode for testing
python main.py 728804746624 --mock

# WebSocket listener (recommended)
python main.py 728804746624 --ws

# HTTP polling mode
python main.py 728804746624 --http

# With custom TTS settings
python main.py 728804746624 --voice zh-CN-YunxiNeural --rate +10% --volume 0.8

# Debug mode
python main.py 728804746624 --debug
```

## Output Formats

### Console Output

```
============================================================
     抖音弹幕语音播报工具 v0.1.0
     LiveStreamInfoRetrievalProject
============================================================

[INFO] 正在连接直播间: 728804746624
[INFO] WebSocket连接成功！
[INFO] 连接成功！开始监听弹幕...

============================================================
[弹幕] 用户昵称
[内容] 弹幕内容在这里
============================================================
```

### Danmaku Display (Windows)

```python
# Windows-compatible ASCII art
print()
print("=" * 60)
print(f"[弹幕] {user_name}")
print(f"[内容] {content}")
print("=" * 60)
print()
```

### Danmaku Display (Non-Windows)

```python
# With emoji support
print()
print("=" * 60)
print(f"📺 弹幕: [{user_name}]")
print(f"💬 内容: {content}")
print("=" * 60)
print()
```

## Logging Configuration

```python
def setup_logging(level: str = "INFO", enable_debug: bool = False):
    """Configure logging output"""

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%H:%M:%S"
    )
```

### Log Levels

| Level | Usage | Example |
|-------|-------|---------|
| DEBUG | Detailed protocol info | WebSocket frames, protobuf bytes |
| INFO | Normal operation | Connection status, danmaku count |
| WARNING | Non-critical issues | Failed parse, retry |
| ERROR | Critical failures | Connection lost, TTS failed |

## Audio Output

### TTS Engine

```python
class EdgeTTSEngine:
    """Microsoft Edge Text-to-Speech"""

    Available Voices:
      - zh-CN-XiaoxiaoNeural (女声，温柔)
      - zh-CN-YunxiNeural (男声，温和)
      - zh-CN-YunyangNeural (男声，沉稳)
      - zh-CN-XiaoyiNeural (女声，亲切)
      - zh-CN-YunjianNeural (男声，稳重)
      - zh-CN-XiaohanNeural (女声，清新)
      - zh-CN-XiaomengNeural (女声，可爱)
      - zh-CN-XiaoxuanNeural (女声，成熟)
      - zh-CN-XiaoruiNeural (女声，知性)

    Parameters:
      - voice: Voice name
      - rate: Speech rate (+0% default, -50% to +100%)
      - volume: Audio volume (+0% default, -50% to +100%)
```

### Audio Player

```python
class PygamePlayer:
    """Pygame-based audio playback"""

    Methods:
      - play(audio_path: Path, blocking: bool) -> bool
      - play_bytes(audio_data: bytes, blocking: bool) -> bool
      - stop() -> None
      - set_volume(volume: float) -> None
      - wait_until_finished(timeout: float) -> None

    Audio Queue:
      - asyncio.Queue for message buffering
      - Sequential playback (no interruption)
      - Automatic cache management
```

## Configuration File

### config.ini Format

```ini
[room]
room_id = 728804746624
cookie_file = cookies.txt
auto_reconnect = true
heartbeat_interval = 30

[tts]
engine = edge
voice = zh-CN-XiaoxiaoNeural
rate = +0%
volume = +0%
cache_enabled = true
cache_days = 7

[filter]
min_length = 1
max_length = 100
enable_filter = true

[filter.users]
blocked = user1,user2
only_vip = false

[filter.keywords]
blocked = 广告,刷屏
only =

[playback]
max_queue_size = 10
play_interval = 0.5
volume = 0.7

[log]
level = INFO
enable_console = true
enable_file = false
file_path = logs/danmu.log
```

## Signal Handling

```python
# Unix systems only
for sig in (signal.SIGINT, signal.SIGTERM):
    loop.add_signal_handler(sig, lambda: asyncio.create_task(orchestrator.shutdown()))

# Windows (keyboard interrupt)
try:
    await orchestrator.run()
except KeyboardInterrupt:
    logger.info("用户中断")
```

## User Interaction Flow

```
1. User runs: python main.py <room_id>
   |
   v
2. Display banner and initialize
   |
   v
3. Load configuration (config.ini or defaults)
   |
   v
4. Load cookie (cookies.txt)
   |
   v
5. Connect to live stream (based on --mode)
   |
   v
6. Display: "连接成功！开始监听弹幕..."
   |
   v
7. Listen loop:
   - Receive danmaku
   - Display: "[弹幕] nickname"
   - Display: "[内容] content"
   - Convert to speech (TTS)
   - Play audio (queue)
   |
   v
8. User presses Ctrl+C
   |
   v
9. Shutdown:
   - Stop queue worker
   - Disconnect WebSocket
   - Cleanup player
   - Display statistics
```

## Shutdown Sequence

```python
async def shutdown(self):
    """Graceful shutdown"""

    1. Set is_running = False
    2. Wait for play_queue to complete (5s timeout)
    3. Cancel play_task
    4. Disconnect connector
    5. Cleanup player (pygame.mixer.quit())
    6. Print statistics:
       - messages_received
       - messages_played
       - errors
       - success_rate
```

## Statistics Output

```
============================================================
正在关闭...
============================================================
等待播放队列完成...
已断开连接
运行统计:
  接收消息: 42
  播报消息: 38
  错误次数: 4
  成功率: 90.5%
============================================================
已安全退出
============================================================
```

## Related Areas

- [Architecture Codemap](architecture.md) - Overall system design
- [Backend Codemap](backend.md) - Douyin connector implementation

## Notes

- No GUI components; all output is console-based
- Audio playback uses system default audio device
- Pygame supports both `pygame` and `pygame-ce`
- Audio files are cached in `cache/` directory with MD5 hash
- UTF-8 encoding for emoji support on non-Windows platforms
