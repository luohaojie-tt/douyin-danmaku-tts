# Architecture Codemap

**Last Updated:** 2026-02-03
**Project:** LiveStreamInfoRetrievalProject (Douyin Danmaku Voice Broadcast)
**Version:** 0.1.0
**Language:** Python 3.x

## Project Overview

A Python-based tool for retrieving live stream danmaku (chat messages) from Douyin (TikTok China) and broadcasting them using text-to-speech. The project uses WebSocket connections to intercept live chat messages and converts them to audio using Microsoft Edge TTS.

## Architecture Diagram

```
+---------------------------------------------------------------+
|                       main.py (Entry Point)                   |
|                   DanmakuOrchestrator (Coordinator)           |
+---------------------------+-----------------------------------+
                            |
        +-------------------+-------------------+
        |                   |                   |
        v                   v                   v
+----------------+  +----------------+  +------------------+
| Config Module  |  | Douyin Module  |  | TTS Module       |
| - loader.py    |  | - connector*.py|  | - edge_tts.py     |
| - defaults.py  |  | - parser*.py   |  +------------------+
+----------------+  | - cookie.py    |           |
                   | - protobuf.py  |           v
                   | - api.py       |  +------------------+
                   +----------------+  | Player Module    |
                                      | - pygame_player.py|
                                      +------------------+
```

## Data Flow

```
User Input (room_id)
        |
        v
+-------------------+
| DanmakuOrchestrator|
+-------------------+
        |
        +-> Load Config (src/config/)
        |       - defaults.py (default values)
        |       - loader.py (config.ini parsing)
        |
        +-> Load Cookie (src/douyin/cookie.py)
        |       - ttwid from cookies.txt
        |
        +-> Initialize Connector (src/douyin/connector*.py)
        |       |
        |       +-- Mock Mode (DouyinConnectorMock)
        |       +-- WebSocket Mode (DouyinConnector)
        |       +-- Real Mode (DouyinConnectorReal) [Playwright]
        |       +-- HTTP Polling (DouyinHTTPConnector) [Playwright]
        |       +-- WS Listener (WebSocketListenerConnector) [Playwright]
        |
        +-> Initialize Parser (src/douyin/parser*.py)
        |       - parser.py (basic protobuf parsing)
        |       - parser_real.py (real-time parsing)
        |       - parser_http.py (HTTP response parsing)
        |
        +-> Initialize TTS (src/tts/edge_tts.py)
        |       - EdgeTTSEngine with voice/rate/volume
        |
        +-> Initialize Player (src/player/pygame_player.py)
        |       - PygamePlayer with audio queue
        |
        v
+-------------------+
| Message Loop      |
+-------------------+
        |
        +-> connector.listen() -> WebSocket/HTTP messages
        |
        +-> parser.parse_message() -> Extract danmaku content
        |
        +-> Filter (length, keywords, users)
        |
        +-> tts.convert_with_cache() -> Generate MP3
        |
        +-> player.play() -> Queue and play audio
        |
        v
    [Audio Output]
```

## Key Modules

| Module | Purpose | Entry Point | Dependencies |
|--------|---------|-------------|--------------|
| Config | Configuration management | src/config/__init__.py | configparser, dataclasses |
| Douyin | Live stream connection | src/douyin/__init__.py | websockets, playwright, protobuf |
| TTS | Text-to-speech conversion | src/tts/__init__.py | edge-tts |
| Player | Audio playback | src/player/__init__.py | pygame/pygame-ce |
| Filter | Message filtering | src/filter/__init__.py | (stub, not fully implemented) |
| Utils | Utility functions | src/utils/__init__.py | (stub) |

## External Dependencies

```
Core:
  websockets==12.0        # WebSocket client
  protobuf==4.25.1        # Protocol buffer encoding
  edge-tts==6.1.9         # Microsoft Edge TTS
  pygame==2.5.2           # Audio playback

Support:
  aiohttp==3.9.1          # Async HTTP client
  configparser==6.0.0     # INI file parsing
  python-dotenv==1.0.0    # Environment variables
  colorlog==6.8.0         # Colored logging

Browser Automation (optional):
  playwright              # Browser automation for signature
```

## Connector Variants

The project implements multiple connection strategies:

1. **DouyinConnectorMock** - Test mode without real connection
2. **DouyinConnector** - Direct WebSocket connection
3. **DouyinConnectorReal** - Playwright-based with signature generation
4. **DouyinConnectorHTTP** - HTTP polling via browser
5. **WebSocketListenerConnector** - Listen to browser WebSocket
6. **DouyinConnectorV2/V3/V4** - Experimental versions

## Message Parsing

Multiple parser implementations for different data sources:

1. **MessageParser** (parser.py) - Basic protobuf with text extraction
2. **RealtimeMessageParser** (parser_real.py) - Field 8 extraction with gzip
3. **HTTPResponseParser** (parser_http.py) - HTTP response regex parsing
4. **ImprovedMessageParser** (parser_v2.py) - Enhanced danmaku extraction

## Configuration System

```
config.ini (optional)
    |
    v
load_config() -> src/config/loader.py
    |
    +-> Merge with DEFAULT_CONFIG (src/config/defaults.py)
    |
    v
AppConfig {
    room: RoomConfig
    tts: TTSConfig
    filter: FilterConfig
    playback: PlaybackConfig
    log: LogConfig
}
```

## Error Handling Strategy

1. **Connection Failures**: Multiple server retry with fallback
2. **Parsing Failures**: Return partial data, log errors
3. **TTS Failures**: Skip message, continue processing
4. **Player Failures**: Queue with timeout, graceful degradation

## Threading Model

```
Main Thread (asyncio event loop)
    |
    +-> Playwright Thread (browser automation)
    |
    +-> Play Queue Worker (asyncio.Task)
    |       - Sequential audio playback
    |       - Non-blocking queue operations
    |
    +-> WebSocket Listener (asyncio)
    |       - Message reception
    |       - Callback dispatch
    |
    +-> Heartbeat Task (asyncio.Task)
            - Periodic ping/pong
```

## Testing Structure

```
test_*.py (root level)
    - test_config.py
    - test_cookie.py
    - test_connector.py
    - test_parser.py
    - test_edge_tts.py
    - test_pygame_player.py
    - test_*.py (various integration tests)
```

## Related Areas

- [Backend Codemap](backend.md) - Douyin connector implementations
- [Data Codemap](data.md) - Message structures and protobuf schemas

## Notes

- Requires Chrome in debug mode for Playwright-based connectors
- ttwid cookie must be manually obtained from browser
- Audio files are cached in `cache/` directory
- Logs can be enabled for debugging with `--debug` flag
