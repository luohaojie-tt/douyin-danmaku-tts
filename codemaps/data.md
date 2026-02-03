# Data Models and Schemas Codemap

**Last Updated:** 2026-02-03
**Module:** Data Structures and Configuration

## Overview

This document describes all data models, configuration structures, and message formats used throughout the application.

## Configuration Data Models

### AppConfig (src/config/defaults.py)

```python
@dataclass
class AppConfig:
    """Root configuration container"""
    room: RoomConfig
    tts: TTSConfig
    filter: FilterConfig
    playback: PlaybackConfig
    log: LogConfig
```

### RoomConfig

```python
@dataclass
class RoomConfig:
    """Live stream room settings"""
    room_id: str = ""                      # Room ID (URL parameter)
    cookie_file: str = "cookies.txt"       # Path to ttwid cookie
    auto_reconnect: bool = True            # Auto-reconnect on disconnect
    heartbeat_interval: int = 30           # Heartbeat interval (seconds)
```

### TTSConfig

```python
@dataclass
class TTSConfig:
    """Text-to-speech settings"""
    engine: str = "edge"                   # TTS engine (edge only supported)
    voice: str = "zh-CN-XiaoxiaoNeural"    # Voice name
    rate: str = "+0%"                      # Speech rate (-50% to +100%)
    volume: str = "+0%"                    # Volume (-50% to +100%)
    cache_enabled: bool = True             # Enable audio caching
    cache_days: int = 7                    # Cache retention (days)
```

### FilterConfig

```python
@dataclass
class FilterConfig:
    """Message filtering settings"""
    min_length: int = 1                    # Minimum danmaku length
    max_length: int = 100                  # Maximum danmaku length
    enable_filter: bool = True             # Enable filtering
    users: FilterUserConfig                # User filter settings
    keywords: FilterKeywordConfig          # Keyword filter settings
```

### FilterUserConfig

```python
@dataclass
class FilterUserConfig:
    """User-based filtering"""
    blocked: List[str] = field(default_factory=list)  # Blocked user list
    only_vip: bool = False                                  # Only VIP users
```

### FilterKeywordConfig

```python
@dataclass
class FilterKeywordConfig:
    """Keyword-based filtering"""
    blocked: List[str] = field(default_factory=list)  # Blocked keywords
    only: List[str] = field(default_factory=list)      # Whitelist keywords
```

### PlaybackConfig

```python
@dataclass
class PlaybackConfig:
    """Audio playback settings"""
    max_queue_size: int = 10              # Maximum queued audio
    play_interval: float = 0.5            # Interval between plays (seconds)
    volume: float = 0.7                   # Playback volume (0.0-1.0)
```

### LogConfig

```python
@dataclass
class LogConfig:
    """Logging settings"""
    level: str = "INFO"                    # Log level
    enable_console: bool = True           # Console output
    enable_file: bool = False             # File output
    file_path: str = "logs/danmu.log"     # Log file path
```

## Message Data Models

### UserInfo (Multiple definitions)

```python
@dataclass
class UserInfo:
    """User information"""
    id: str                               # User ID
    nickname: str                         # Display name
    level: int = 1                        # User level (optional)
    badge: Optional[str] = None           # User badge/title (optional)
```

### ParsedMessage (Multiple definitions)

```python
@dataclass
class ParsedMessage:
    """Parsed danmaku message"""
    method: str                           # Message type
    user: Optional[UserInfo] = None       # Sender info
    content: Optional[str] = None         # Danmaku text
    gift_name: Optional[str] = None       # Gift name (if gift)
    gift_count: Optional[int] = None      # Gift count
    timestamp: int = 0                    # Message timestamp
    raw: bool = False                     # Whether raw/unparsed
    raw_data: Optional[bytes] = None      # Raw bytes (v2)
    raw_strings: Optional[List[dict]] = None  # Extracted strings (v2)
```

### DanmakuMessage (message_parser.py)

```python
class DanmakuMessage:
    """Legacy danmaku message"""

    def __init__(self, content: str, user: str, user_id: str = "", timestamp: int = 0):
        self.content = content
        self.user = user
        self.user_id = user_id
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "user": self.user,
            "user_id": self.user_id,
            "timestamp": self.timestamp
        }
```

## Protobuf Data Structures

### PushFrame (src/douyin/protobuf.py)

```python
@dataclass
class PushFrame:
    """WebSocket PushFrame structure (Douyin proprietary)"""
    seq_id: Optional[int] = None          # Field 1: Sequence ID
    log_id: Optional[int] = None          # Field 2: Log ID
    service: Optional[int] = None         # Field 3: Service type
    method: Optional[int] = None          # Field 4: Method
    headers_list: Optional[Dict[str, str]] = None  # Field 5: Headers
    payload_encoding: Optional[str] = None        # Field 6: Payload encoding
    payload_type: Optional[str] = None           # Field 7: "hb", "ack", "msg", "close"
    payload: Optional[bytes] = None              # Field 8: Gzip-compressed protobuf
    lod_id_new: Optional[str] = None            # Field 9: Log ID (new format)
```

### PushFrame Wire Format

```
Each field is encoded as (tag, value) where:
  tag = (field_number << 3) | wire_type
  wire_type: 0=varint, 1=64bit, 2=length-delimited, 5=32bit

Field 1 (seq_id):      varint
Field 2 (log_id):      varint
Field 3 (service):     varint
Field 4 (method):      varint
Field 5 (headers):     map<string, string> (nested)
Field 6 (encoding):    string (length-delimited)
Field 7 (type):        string (length-delimited)
Field 8 (payload):     bytes (length-delimited, usually gzip)
Field 9 (lod_id_new):  string (length-delimited)
```

### Varint Encoding

```python
def _encode_varint(value: int) -> bytes:
    """Encode integer as varint"""
    result = bytearray()
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)  # Set continuation bit
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)
```

## Message Type Constants

### WebSocket Message Types

| Type String | Description | Parser |
|-------------|-------------|--------|
| WebChatMessage | Chat/danmaku message | All parsers |
| WebGiftMessage | Gift notification | parser.py |
| WebLiveEndEvent | Stream ended | parser.py |
| WebcastRoomStatsMessage | Room statistics | parser_real.py |
| WebcastRoomUserSeqMessage | User sequence | parser_real.py |
| WebcastLikeMessage | Like notification | parser_real.py |
| MemberMessage | Member joined | parser_real.py |
| ControlMessage | Control message | parser_real.py |
| WebcastRoomRankMessage | Ranking update | parser_v2.py |
| WebcastSocialMessage | Social interaction | parser_v2.py |
| WebcastInRoomBannerMessage | Banner display | parser_v2.py |
| Unknown | Unrecognized type | All parsers |

## WebSocket URL Parameters

### Standard WebSocket Parameters

```
wss://webcast5-ws-web-lf.douyin.com/webcast/im/push/v2/?
    app_name=douyin_web
    &version_code=180800
    &webcast_sdk_version=1.0.15
    &compress=gzip
    &device_platform=web
    &cookie_enabled=true
    &screen_width=2560
    &screen_height=1440
    &browser_language=zh-CN
    &browser_platform=Win32
    &browser_name=Mozilla
    &browser_version=5.0 (Windows NT 10.0; Win64; x64) ...
    &browser_online=true
    &tz_name=Asia/Shanghai
    &cursor={cursor}
    &internal_ext={internal_ext}
    &host=https://live.douyin.com
    &aid=6383
    &live_id=1
    &did_rule=3
    &endpoint=live_pc
    &support_wrds=1
    &user_unique_id={unique_id}
    &im_path=/webcast/im/fetch/
    &identity=audience
    &need_persist_msg_count=15
    &room_id={room_id}
    &heartbeatDuration=0
    &signature={signature}
```

### Cursor Format

```
t-{timestamp}_r-{room_id}_d-{device_id}_u-{user_id}_h-{hash}
```

### Internal Ext Format

```
internal_src:dim|
wss_push_room_id:{room_id}|
wss_push_did:{unique_id}|
first_req_ms:{timestamp}|
fetch_time:{timestamp}|
seq:1|
wss_info:0-{timestamp}-0-0
```

## Cookie Format

### ttwid Cookie

```
Format: ttwid=<value>

Location:
  - File: cookies.txt (in project root)
  - Browser: https://live.douyin.com Cookies

Validation:
  - Minimum length: 50 characters
  - Allowed characters: [a-zA-Z0-9_%-]
  - Pattern: ^[\w\-%]+$
```

### Example cookies.txt

```
# Douyin ttwid cookie
ttwid=1%7CaB3k4XyZ...
```

## Cache Data Structure

### Audio Cache

```
cache/
├── {md5_hash}.mp3
    - Hash = md5(text + voice + rate)
    - Filename: 32 character hex string
    - Retention: cache_days (default 7 days)
```

### Cache Key Generation

```python
cache_key = f"{text}_{self.voice}_{self.rate}"
cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
cache_file = cache_dir / f"{cache_hash}.mp3"
```

## Statistics Data

### DanmakuOrchestrator Stats

```python
self.stats = {
    "messages_received": int,      # Total messages received
    "messages_played": int,        # Total messages converted to audio
    "errors": int,                  # Total errors encountered
}
```

### EdgeTTSEngine Stats

```python
self.total_conversions = int       # Total TTS conversions
self.total_chars = int             # Total characters converted
```

### PygamePlayer Stats

```python
self.total_played = int            # Total audio plays
self.total_duration = float        # Total audio duration (seconds)
```

## Data Flow Transformation

```
1. Raw WebSocket Message (bytes)
   |
   v
2. PushFrame (protobuf decode)
   |
   v
3. Extract Field 8 (gzip decompress)
   |
   v
4. Protobuf Message (parse fields)
   |
   v
5. Extract Strings (UTF-8 decode)
   |
   v
6. Detect Message Type (pattern match)
   |
   v
7. ParsedMessage (user, content, method)
   |
   v
8. Filter (length, keywords, users)
   |
   v
9. TTS Input (text only)
   |
   v
10. Audio Output (MP3 file)
```

## Related Areas

- [Architecture Codemap](architecture.md) - System architecture
- [Backend Codemap](backend.md) - Connector implementation details

## Notes

- Protobuf schemas are reverse-engineered, not official
- Message formats may change without notice
- Always include timestamp in logged data
- Use UTF-8 encoding for all text processing
