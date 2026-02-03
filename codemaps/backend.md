# Backend Codemap

**Last Updated:** 2026-02-03
**Module:** Douyin Live Stream Connectors
**Primary Language:** Python 3.x

## Overview

The backend module (`src/douyin/`) handles all interactions with Douyin's live streaming platform, including WebSocket connections, HTTP requests, message parsing, and cookie management.

## Module Structure

```
src/douyin/
├── __init__.py                 # Public exports
├── cookie.py                   # Cookie management
├── connector.py                # Base WebSocket connector
├── connector_real.py           # Playwright-based connector
├── connector_http.py           # HTTP polling connector
├── connector_websocket_listener.py  # Browser WS listener
├── connector_v2.py             # Alternative implementation
├── connector_v3.py             # URL capture implementation
├── connector_v4.py             # Chat detection implementation
├── parser.py                   # Basic message parser
├── parser_real.py              # Real-time message parser
├── parser_http.py              # HTTP response parser
├── parser_v2.py                # Improved message parser
├── message_parser.py           # Legacy message parser
├── protobuf.py                 # PushFrame codec
├── websocket_extractor.py      # WebSocket extraction utilities
└── api.py                      # HTTP API client
```

## Connector Architecture

### Base Connector (connector.py)

```python
class DouyinConnector:
    """Standard WebSocket connection"""

    WS_SERVERS = [
        "wss://webcast5-ws-web-lf.douyin.com/webcast/im/push/v2/",
        "wss://webcast5-ws-web-hl.douyin.com/webcast/im/push/v2/",
        "wss://webcast3-ws-web-lf.douyin.com/webcast/im/push/v2/",
        "wss://webcast.amemv.com/webcast/im/push/v2/",
    ]

    Methods:
    - connect() -> bool
    - listen(callback: Callable) -> None
    - disconnect() -> None
    - _parse_message(raw_data: bytes) -> Optional[dict]
```

### Real Connector (connector_real.py)

Uses Playwright to:
1. Connect to Chrome CDP (localhost:9222)
2. Extract roomId and uniqueId from `__pace_f[24]`
3. Generate signature via `byted_acrawler.frontierSign`
4. Create IM cursor and internal_ext
5. Establish WebSocket with protobuf PushFrame

```python
class DouyinConnectorReal:
    """Playwright-based with signature generation"""

    Key Methods:
    - _get_signature() -> bool     # Extract X-Bogus from browser
    - _connect_websocket() -> bool # Connect with generated params
    - _start_heartbeat() -> None   # Send periodic heartbeats
    - _send_ack_if_needed() -> None  # Acknowledge received messages

    Dependencies:
    - playwright.async_api
    - websockets
    - src.douyin.protobuf (PushFrameCodec)
```

### HTTP Connector (connector_http.py)

Polls `/webcast/im/fetch` via browser JavaScript:

```python
class DouyinHTTPConnector:
    """HTTP polling via Playwright"""

    Methods:
    - connect() -> bool
    - _handle_response(response) -> None
    - _poll_messages() -> None
    - listen(message_handler: Callable) -> None

    Features:
    - Auto-retry on consecutive errors
    - Browser health monitoring
    - Message queue with asyncio.Queue
```

### WebSocket Listener (connector_websocket_listener.py)

Injects JavaScript to intercept browser WebSocket:

```python
class WebSocketListenerConnector:
    """Listen to browser WebSocket messages"""

    Key Features:
    - Overrides window.WebSocket in page init script
    - Extracts danmaku from binary messages
    - Filters system messages
    - Returns ParsedMessage objects directly
```

## Message Parser Architecture

### Parser Hierarchy

```
MessageParser (parser.py)
    - Basic protobuf field parsing
    - Text extraction with regex
    - Message type detection

RealtimeMessageParser (parser_real.py)
    - Field 8 extraction with gzip decompression
    - String extraction from protobuf
    - Danmaku content extraction

HTTPResponseParser (parser_http.py)
    - HTTP response body parsing
    - Regex pattern matching for danmaku
    - System message filtering

ImprovedMessageParser (parser_v2.py)
    - Enhanced string extraction
    - User nickname detection
    - Better system message filtering
```

### Message Data Structures

```python
@dataclass
class UserInfo:
    id: str
    nickname: str
    level: int = 1
    badge: Optional[str] = None

@dataclass
class ParsedMessage:
    method: str                          # "WebChatMessage", etc.
    user: Optional[UserInfo]
    content: Optional[str]               # Danmaku text
    gift_name: Optional[str]
    gift_count: Optional[int]
    timestamp: int = 0
    raw: bool = False
```

## Protobuf Handling (protobuf.py)

### PushFrame Structure

```python
@dataclass
class PushFrame:
    seq_id: Optional[int]        # Field 1
    log_id: Optional[int]        # Field 2
    service: Optional[int]       # Field 3
    method: Optional[int]        # Field 4
    headers_list: Optional[Dict] # Field 5
    payload_encoding: Optional[str]  # Field 6
    payload_type: Optional[str]  # Field 7: "hb", "ack", "msg", "close"
    payload: Optional[bytes]     # Field 8 (gzip compressed protobuf)
    lod_id_new: Optional[str]    # Field 9
```

### Codec Operations

```python
class PushFrameCodec:
    @staticmethod
    def encode(frame: PushFrame) -> bytes

    @staticmethod
    def decode(data: bytes) -> Optional[PushFrame]

class PushFrameFactory:
    @staticmethod
    def create_heartbeat() -> bytes

    @staticmethod
    def create_ack(internal_ext: str, log_id: Optional[int]) -> bytes
```

## Cookie Management (cookie.py)

```python
class CookieManager:
    """ttwid cookie validation and storage"""

    MIN_TTWID_LENGTH = 50

    Methods:
    - load_from_file(path: str) -> Optional[str]
    - load_from_string(ttwid: str) -> Optional[str]
    - validate_ttwid(ttwid: str) -> bool
    - save_to_file(ttwid: str, path: str) -> bool

    Supported Formats:
    - ttwid=xxx
    - ttwid = xxx
    - # ttwid=xxx (commented line)
```

## API Client (api.py)

```python
class DouyinAPI:
    """HTTP API for live stream info"""

    Methods:
    - get_live_info(room_id: str) -> Optional[Dict]
    - get_im_info(room_id: str, unique_id: str) -> Optional[Dict]

    Endpoints:
    - GET /{room_id} - Room HTML (extract roomId/uniqueId)
    - GET /webcast/im/fetch/ - IM initialization
```

## Message Type Detection

| Message Type | String Pattern | Handler |
|-------------|---------------|---------|
| WebChatMessage | WebcastChatMessage | parser_real.py |
| WebChatMessage (topic) | WebcastRoomCommentTopicMessage | parser_real.py |
| WebGiftMessage | WebcastGiftMessage | parser.py |
| RoomStats | WebcastRoomStatsMessage | parser_real.py |
| UserSeq | WebcastRoomUserSeqMessage | parser_real.py |
| Like | WebcastLikeMessage | parser_real.py |
| Member | MemberMessage | parser_real.py |
| Control | ControlMessage | parser_real.py |
| Unknown | (no pattern) | All parsers |

## Connection Flow Comparison

| Connector | Chrome Required | Signature | Reliability | Latency |
|-----------|----------------|-----------|-------------|---------|
| Mock | No | None | N/A | N/A |
| Standard | No | Optional | Medium | Low |
| Real | Yes | Generated | High | Medium |
| HTTP | Yes | Browser | High | High |
| WS Listener | Yes | Browser | High | Low |

## Error Handling

```python
# Connection retry with multiple servers
for ws_url in WS_SERVERS:
    try:
        ws = await websockets.connect(ws_url, headers=headers)
        return True
    except Exception:
        continue
return False

# Message parsing with graceful degradation
try:
    decompressed = gzip.decompress(raw_data)
except gzip.BadGzipFile:
    decompressed = raw_data  # Use raw data

# protobuf parsing with skip on error
while pos < len(data):
    try:
        tag, pos = read_varint(data, pos)
        # ... process field
    except Exception:
        break  # Skip malformed data
```

## Dependencies

```
Internal:
  - src.config (configuration)
  - src.utils (utilities, stub)

External:
  - websockets (WebSocket client)
  - aiohttp (HTTP client)
  - playwright (browser automation)
  - gzip (compression)
  - hashlib (signature generation)
```

## Related Areas

- [Architecture Codemap](architecture.md) - Overall system architecture
- [Data Codemap](data.md) - Message structures and protobuf schemas

## Notes

- All connectors are async/await based
- Playwright-based connectors require Chrome with `--remote-debugging-port=9222`
- Signature generation is complex; using browser's JavaScript is recommended
- Protobuf schemas are not official; reverse-engineered from network captures
