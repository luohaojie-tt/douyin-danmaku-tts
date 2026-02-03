# Codemap Index

**Last Updated:** 2026-02-03
**Project:** LiveStreamInfoRetrievalProject
**Version:** 0.1.0

## Overview

This directory contains comprehensive code maps documenting the architecture, modules, and data structures of the Douyin (TikTok China) Live Stream Danmaku Voice Broadcast tool.

## Available Codemaps

| Codemap | Description | Status |
|---------|-------------|--------|
| [architecture.md](architecture.md) | Overall system architecture and design | Complete |
| [backend.md](backend.md) | Douyin connector and parser implementations | Complete |
| [frontend.md](frontend.md) | CLI interface and audio output | Complete |
| [data.md](data.md) | Data models, schemas, and configuration | Complete |

## Quick Reference

### Project Structure

```
LiveStreamInfoRetrievalProject/
├── main.py                      # Entry point (CLI)
├── config.ini                   # User configuration (optional)
├── cookies.txt                  # Douyin ttwid cookie
├── cache/                       # TTS audio cache
│
├── codemaps/                    # This directory
│   ├── INDEX.md                 # This file
│   ├── architecture.md          # System architecture
│   ├── backend.md               # Douyin module details
│   ├── frontend.md              # CLI and output
│   └── data.md                  # Data structures
│
├── src/                         # Source code
│   ├── config/                  # Configuration management
│   │   ├── __init__.py
│   │   ├── defaults.py          # Default configuration values
│   │   └── loader.py            # Config file parser
│   │
│   ├── douyin/                  # Douyin integration
│   │   ├── __init__.py
│   │   ├── api.py               # HTTP API client
│   │   ├── cookie.py            # Cookie manager
│   │   ├── protobuf.py          # PushFrame codec
│   │   ├── connector.py         # Base WebSocket connector
│   │   ├── connector_real.py    # Playwright-based connector
│   │   ├── connector_http.py    # HTTP polling connector
│   │   ├── connector_websocket_listener.py  # Browser WS listener
│   │   ├── connector_v2.py      # Alternative implementation
│   │   ├── connector_v3.py      # URL capture implementation
│   │   ├── connector_v4.py      # Chat detection implementation
│   │   ├── parser.py            # Basic message parser
│   │   ├── parser_real.py       # Real-time parser
│   │   ├── parser_http.py       # HTTP response parser
│   │   ├── parser_v2.py         # Improved parser
│   │   ├── message_parser.py    # Legacy parser
│   │   └── websocket_extractor.py
│   │
│   ├── tts/                     # Text-to-speech
│   │   ├── __init__.py
│   │   └── edge_tts.py          # Edge TTS engine
│   │
│   ├── player/                  # Audio playback
│   │   ├── __init__.py
│   │   └── pygame_player.py     # Pygame player
│   │
│   ├── filter/                  # Message filtering (stub)
│   │   └── __init__.py
│   │
│   └── utils/                   # Utilities (stub)
│       └── __init__.py
│
├── tools/                       # Utility scripts
│   ├── capture_websocket.py
│   ├── test_domains.py
│   └── get_room_id.py
│
├── test_*.py                    # Unit/integration tests
└── requirements.txt             # Python dependencies
```

## Key Components

### Entry Point
- **File:** `main.py`
- **Class:** `DanmakuOrchestrator`
- **Purpose:** Coordinates all modules for end-to-end danmaku retrieval and TTS

### Connectors (src/douyin/)
| Connector | Mode | Chrome Required | Stability |
|-----------|------|----------------|-----------|
| DouyinConnectorMock | Mock | No | Test only |
| DouyinConnector | WebSocket | No | Medium |
| DouyinConnectorReal | Playwright | Yes | High |
| DouyinHTTPConnector | HTTP Polling | Yes | High |
| WebSocketListenerConnector | Browser WS | Yes | High |

### Parsers
| Parser | File | Use Case |
|--------|------|----------|
| MessageParser | parser.py | Basic WebSocket |
| RealtimeMessageParser | parser_real.py | Real-time connector |
| HTTPResponseParser | parser_http.py | HTTP polling |
| ImprovedMessageParser | parser_v2.py | Enhanced extraction |

### External Dependencies

```
Core:
  websockets==12.0        # WebSocket protocol
  protobuf==4.25.1        # Binary encoding
  edge-tts==6.1.9         # Text-to-speech
  pygame==2.5.2           # Audio playback

Support:
  aiohttp==3.9.1          # Async HTTP
  playwright              # Browser automation
  configparser==6.0.0     # Config files
```

## Data Flow Summary

```
User Input (room_id)
        |
        v
Config + Cookie Loading
        |
        v
Connector Initialization
        |
        v
WebSocket/HTTP Connection
        |
        v
Binary Message Reception
        |
        v
Protobuf Decoding
        |
        v
Danmaku Extraction
        |
        v
Text-to-Speech Conversion
        |
        v
Audio Playback (queued)
```

## Configuration Reference

### Minimum Setup

1. Create `cookies.txt` with your Douyin ttwid
2. Run: `python main.py <room_id> --ws`

### Full Config (config.ini)

See [data.md](data.md) for complete configuration reference.

## Development Notes

### Adding a New Connector

1. Create `connector_<name>.py` in `src/douyin/`
2. Implement: `connect()`, `listen()`, `disconnect()`
3. Add to `main.py` argument parser
4. Update codemaps

### Adding a New Parser

1. Create `parser_<name>.py` in `src/douyin/`
2. Parse to `ParsedMessage` format
3. Add to connector as needed
4. Update codemaps

## Related Documentation

- [requirements.txt](../requirements.txt) - Python dependencies
- [main.py](../main.py) - Entry point implementation
- [README.md](../README.md) - Project overview (if exists)

## Maintenance

**Update Frequency:** After major structural changes

**Last Review:** 2026-02-03

**Reviewers:**
- Code analysis from source files
- Dependency mapping from imports
- Data structure extraction from dataclasses

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-03 | Initial codemap generation | Claude Code |
