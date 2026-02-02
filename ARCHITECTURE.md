# 抖音弹幕语音播报工具 - 架构设计文档

## 文档信息

| 项目 | 信息 |
|-----|------|
| **项目名称** | LiveStreamInfoRetrievalProject |
| **文档版本** | v2.1.0 (简化版 + 实现细节) |
| **创建日期** | 2024-02-02 |
| **最后更新** | 2024-02-02 |
| **架构师** | Claude Architect Agent |
| **文档状态** | 详细设计版 |
| **定位** | 个人使用的轻量级弹幕语音播报工具 |

---

## 📋 目录

1. [系统概述](#1-系统概述)
2. [需求分析](#2-需求分析)
3. [系统架构](#3-系统架构)
4. [技术栈](#4-技术栈)
5. [模块设计](#5-模块设计)
6. [数据流](#6-数据流)
7. [配置管理](#7-配置管理)
8. [部署方案](#8-部署方案)

---

## 1. 系统概述

### 1.1 项目简介

一个**极简的Python命令行工具**，用于实时捕获抖音直播间的弹幕，并转换成语音播放。

**核心价值**：解放双眼，用耳朵听弹幕。

### 1.2 设计原则

```
简单 > 复杂
实用 > 完美
够用 > 过度设计
```

### 1.3 系统特点

- ✅ **单机运行**：无需服务器，本地Python脚本
- ✅ **开箱即用**：配置一次，永久使用
- ✅ **轻量级**：核心代码 < 1000行
- ✅ **免费**：使用免费的Edge-TTS
- ✅ **实时性**：弹幕延迟 < 2秒

---

## 2. 需求分析

### 2.1 功能需求

```
核心功能（必须）
├─ 连接抖音直播间
├─ 实时捕获弹幕
├─ 文字转语音 (TTS)
├─ 语音播放
└─ 基本配置（语速、音色）

可选功能（nice to have）
├─ 弹幕过滤（关键词、用户）
├─ 播放队列（避免重叠）
├─ 播放历史记录
└─ 简单的日志输出
```

### 2.2 非功能需求

| 需求 | 指标 | 说明 |
|-----|------|------|
| **延迟** | < 2秒 | 从弹幕到语音播放 |
| **准确性** | > 95% | 弹幕捕获率 |
| **稳定性** | 自动重连 | 断线自动恢复 |
| **资源占用** | < 200MB RAM | 低内存占用 |
| **易用性** | 一行命令启动 | `python main.py <room_id>` |

### 2.3 不做的事情

```
❌ 不做Web界面
❌ 不做数据库存储
❌ 不做数据分析
❌ 不做多房间管理
❌ 不做用户认证
❌ 不做云部署
```

---

## 3. 系统架构

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     单机应用程序                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   抖音服务器                                                  │
│      │                                                       │
│      │ WebSocket (Protobuf)                                 │
│      │                                                       │
│      ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Python 主程序                            │    │
│  │                                                      │    │
│  │  ┌────────────┐   ┌────────────┐   ┌────────────┐   │    │
│  │  │ 连接管理   │──▶│ 弹幕处理   │──▶│ TTS转换    │   │    │
│  │  │            │   │            │   │            │   │    │
│  │  │ - WebSocket│   │ - 消息解析 │   │ - edge-tts │   │    │
│  │  │ - 心跳保活 │   │ - 过滤规则 │   │ - 音频生成 │   │    │
│  │  │ - 自动重连 │   │ - 去重     │   │ - 本地缓存 │   │    │
│  │  └────────────┘   └────────────┘   └────────────┘   │    │
│  │                                                      │    │
│  │  ┌────────────┐   ┌────────────┐                    │    │
│  │  │ 播放队列   │   │ 音频播放   │                    │    │
│  │  │            │   │            │                    │    │
│  │  │ - 内存队列 │   │ - pygame   │                    │    │
│  │  │ - 优先级   │   │ - 音量控制 │                    │    │
│  │  │ - 去重合并 │   │ - 播放状态 │                    │    │
│  │  └────────────┘   └────────────┘                    │    │
│  │                                                      │    │
│  │  ┌────────────┐                                    │    │
│  │  │ 配置管理   │                                    │    │
│  │  │ - config.ini│                                    │    │
│  │  └────────────┘                                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  输出：控制台日志 + 音频播放                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 数据流图

```
抖音直播间
    │
    │ WebSocket (弹幕消息)
    │
    ▼
┌─────────────┐
│ 连接管理模块 │
│ - WebSocket 连接
│ - Protobuf 解码
│ - 心跳保活
└──────┬──────┘
       │
       │ 原始弹幕
       ▼
┌─────────────┐
│ 弹幕处理模块 │
│ - 解析消息   │
│ - 过滤规则   │
│ - 去重判断   │
└──────┬──────┘
       │
       │ 符合规则的弹幕
       ▼
┌─────────────┐
│  TTS 转换   │
│ - 文本预处理 │
│ - 检查缓存   │
│ - edge-tts   │
│ - 生成音频   │
└──────┬──────┘
       │
       │ 音频数据
       ▼
┌─────────────┐
│ 播放队列     │
│ - 加入队列   │
│ - 优先级排序 │
│ - 去重合并   │
└──────┬──────┘
       │
       │ 按顺序播放
       ▼
┌─────────────┐
│ pygame播放  │
│ - 音频输出   │
│ - 音量控制   │
└─────────────┘
       │
       ▼
   🎵 听到弹幕
```

### 3.3 目录结构

```
LiveStreamInfoRetrievalProject/
├── main.py                 # 程序入口
├── config.ini              # 配置文件
├── requirements.txt        # 依赖包
│
├── src/                    # 源代码
│   ├── __init__.py
│   │
│   ├── config/            # 配置管理
│   │   ├── __init__.py
│   │   └── settings.py    # 配置加载
│   │
│   ├── douyin/            # 抖音模块
│   │   ├── __init__.py
│   │   ├── connector.py   # WebSocket连接
│   │   ├── protocol.py    # 协议解析
│   │   └── cookie.py      # Cookie管理
│   │
│   ├── tts/               # TTS模块
│   │   ├── __init__.py
│   │   ├── engine.py      # TTS引擎
│   │   ├── edge_tts.py    # Edge-TTS
│   │   └── cache.py       # 音频缓存
│   │
│   ├── player/            # 播放模块
│   │   ├── __init__.py
│   │   ├── queue.py       # 播放队列
│   │   └── pygame_player.py # pygame播放
│   │
│   ├── filter/            # 过滤模块
│   │   ├── __init__.py
│   │   └── rules.py       # 过滤规则
│   │
│   └── utils/             # 工具函数
│       ├── __init__.py
│       ├── logger.py      # 日志
│       └── helpers.py     # 辅助函数
│
├── logs/                   # 日志目录
├── cache/                  # 音频缓存目录
└── README.md               # 说明文档
```

**代码规模估算**：
- `main.py`: ~50行
- 每个模块: ~100-200行
- **总计**: ~800-1200行代码

---

## 4. 技术栈

### 4.1 核心技术

| 组件 | 技术选型 | 版本 | 说明 |
|-----|---------|------|------|
| **编程语言** | Python | 3.11+ | 简单易用 |
| **异步框架** | asyncio | 内置 | 异步I/O |
| **WebSocket** | websockets | 12+ | 轻量级 |
| **Protobuf** | protobuf | 4+ | 协议解析 |
| **TTS引擎** | edge-tts | 6.1+ | 免费高质量 |
| **音频播放** | pygame | 2.5+ | 简单可靠 |

### 4.2 依赖包

```
requirements.txt
═════════════════════════════════════════════

# 核心依赖
websockets==12.0           # WebSocket客户端
protobuf==4.25.1           # Protobuf解析
edge-tts==6.1.9            # 微软Edge TTS
pygame==2.5.2              # 音频播放

# 辅助依赖
aiohttp==3.9.1             # HTTP客户端
asyncio-mqtt==0.16.1       # MQTT（可选）

# 配置管理
configparser==6.0.0        # 配置文件解析
python-dotenv==1.0.0       # 环境变量

# 日志
colorlog==6.8.0            # 彩色日志输出
```

### 4.3 技术选择理由

| 技术 | 为什么选择它 |
|-----|-------------|
| **Python** | 简单、库丰富、快速开发 |
| **asyncio** | 原生支持、无需额外框架 |
| **edge-tts** | 免费、高质量、无需API密钥 |
| **pygame** | 成熟、跨平台、音频播放简单 |
| **配置文件** | 无需数据库，人类可读 |

---

## 5. 模块设计

### 5.1 连接管理模块

```python
# src/douyin/connector.py

class DouyinConnector:
    """抖音直播间连接器"""

    def __init__(self, room_id: str):
        self.room_id = room_id
        self.ws = None
        self.heartbeat_interval = 30

    async def connect(self) -> bool:
        """连接到直播间"""
        # 1. 获取直播间信息
        # 2. 建立 WebSocket 连接
        # 3. 发送心跳包
        pass

    async def listen(self):
        """监听消息"""
        # 持续接收消息并yield
        async for message in self.ws:
            yield message

    async def disconnect(self):
        """断开连接"""
        if self.ws:
            await self.ws.close()
```

**关键功能**：
- ✅ WebSocket 长连接
- ✅ 心跳保活（30秒）
- ✅ 自动重连（指数退避）
- ✅ Protobuf 消息解码

### 5.2 弹幕处理模块

```python
# src/filter/rules.py

class MessageFilter:
    """弹幕过滤器"""

    def __init__(self, config):
        self.min_length = config.get('min_length', 1)
        self.max_length = config.get('max_length', 100)
        self.blocked_users = set(config.get('blocked_users', []))
        self.blocked_keywords = config.get('blocked_keywords', [])

    def should_play(self, message: dict) -> bool:
        """判断是否应该播放"""
        # 1. 检查用户黑名单
        # 2. 检查敏感词
        # 3. 检查消息长度
        # 4. 检查消息类型
        return True
```

### 5.3 TTS 转换模块

```python
# src/tts/edge_tts.py

import edge_tts

class EdgeTTSEngine:
    """Edge-TTS 引擎"""

    def __init__(self, config):
        self.voice = config.get('voice', 'zh-CN-XiaoxiaoNeural')
        self.rate = config.get('rate', '+0%')  # 语速
        self.volume = config.get('volume', '+0%')  # 音量
        self.cache_dir = Path('cache')
        self.cache_dir.mkdir(exist_ok=True)

    async def convert(self, text: str) -> Path:
        """文字转语音"""
        # 1. 生成缓存key（MD5(text+voice)）
        # 2. 检查缓存
        # 3. 如果没有缓存，调用 edge-tts
        # 4. 保存到本地
        # 5. 返回音频文件路径
        pass

    def _get_cache_path(self, text: str) -> Path:
        """生成缓存文件路径"""
        import hashlib
        key = hashlib.md5(f"{text}{self.voice}".encode()).hexdigest()
        return self.cache_dir / f"{key}.mp3"
```

**关键特性**：
- ✅ 本地文件缓存（避免重复转换）
- ✅ 支持断点续传
- ✅ 异步转换（不阻塞主流程）

### 5.4 播放队列模块

```python
# src/player/queue.py

import asyncio
from collections import deque

class PlaybackQueue:
    """播放队列"""

    def __init__(self, max_size=10):
        self.queue = deque(maxlen=max_size)
        self.playing = False
        self.current = None

    async def add(self, audio_path: Path, text: str):
        """添加到队列"""
        item = {
            'audio_path': audio_path,
            'text': text,
            'timestamp': time.time()
        }
        self.queue.append(item)

    async def start(self, player):
        """开始播放队列"""
        while True:
            if not self.queue.empty():
                item = self.queue.popleft()
                await player.play(item['audio_path'])
                await asyncio.sleep(0.5)  # 播放间隔
            else:
                await asyncio.sleep(0.1)
```

### 5.5 音频播放模块

```python
# src/player/pygame_player.py

import pygame

class PygamePlayer:
    """pygame 音频播放器"""

    def __init__(self, volume=0.7):
        pygame.mixer.init()
        self.volume = volume

    def play(self, audio_path: Path):
        """播放音频"""
        sound = pygame.mixer.Sound(str(audio_path))
        sound.set_volume(self.volume)
        sound.play()

        # 等待播放完成
        while pygame.mixer.get_busy():
            pygame.time.Clock().tick(10)

    def stop(self):
        """停止播放"""
        pygame.mixer.stop()
```

---

## 6. 数据流

### 6.1 完整流程

```python
# 主程序流程

async def main():
    # 1. 加载配置
    config = load_config('config.ini')

    # 2. 初始化模块
    connector = DouyinConnector(room_id)
    filter = MessageFilter(config)
    tts = EdgeTTSEngine(config)
    player = PygamePlayer()
    queue = PlaybackQueue()

    # 3. 启动播放队列
    asyncio.create_task(queue.start(player))

    # 4. 连接直播间
    await connector.connect()

    # 5. 监听弹幕
    async for message in connector.listen():
        # 5.1 过滤
        if not filter.should_play(message):
            continue

        # 5.2 转换
        audio_path = await tts.convert(message['content'])

        # 5.3 加入队列
        await queue.add(audio_path, message['content'])

        # 5.4 输出日志
        print(f"[播放] {message['user']['nickname']}: {message['content']}")
```

### 6.2 错误处理

```python
# 错误处理策略

错误类型              处理方式
═══════════════════════════════════════
网络断开              自动重连（指数退避）
TTS转换失败           跳过该弹幕，记录日志
音频播放失败          跳过，继续下一条
配置文件错误          使用默认配置，提示用户
直播间已结束          优雅退出，打印统计信息
```

---

## 7. 关键实现细节 🆕

### 7.1 抖音连接方案

#### 7.1.1 方案选择

**方案A: 使用现成库（推荐）**

```python
# 使用第三方库 douyin-live
# GitHub: https://github.com/float-io/douyin-live

from douyin_live import DouyinLive

live = DouyinLive(room_id)
async for message in live:
    print(message.content)
```

**优势**:
- ✅ 开箱即用
- ✅ 维护活跃
- ✅ 处理了协议细节

**方案B: 自己实现协议**

如果需要自己实现，需要：

```python
import aiohttp
import asyncio

class DouyinConnector:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.ttwid = None  # 需要获取
        self.ws_url = None

    async def _get_room_info(self):
        """获取直播间信息"""
        url = f"https://live.douyin.com/{self.room_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                # 从HTML中提取 ttwid 和 ws_url
                html = await resp.text()
                # 解析逻辑...
                pass

    async def connect(self):
        """连接WebSocket"""
        await self._get_room_info()
        self.ws = await websockets.connect(self.ws_url)
```

**推荐**: 使用方案A，节省开发时间。

#### 7.1.2 Cookie获取

抖音连接需要 `ttwid` cookie：

```python
# 方案1: 手动获取（简单但麻烦）
# 1. 打开浏览器，访问 live.douyin.com
# 2. F12 → Application → Cookies → 复制 ttwid
# 3. 保存到 config.ini

# 方案2: 自动获取（需要selenium）
from selenium import webdriver

def get_ttwid():
    driver = webdriver.Chrome()
    driver.get("https://live.douyin.com")
    cookies = driver.get_cookies()
    ttwid = next(c['value'] for c in cookies if c['name'] == 'ttwid')
    driver.quit()
    return ttwid
```

**推荐**: MVP使用方案1，后续可优化为方案2。

---

### 7.2 音频播放并发问题

#### 7.2.1 问题分析

pygame 的 `play()` 是阻塞的：

```python
# ❌ 有问题的实现
def play(self, audio_path: Path):
    sound = pygame.mixer.Sound(str(audio_path))
    sound.play()
    # 阻塞等待播放完成！
    while pygame.mixer.get_busy():
        pygame.time.Clock().tick(10)
```

**问题**:
- ⚠️ 高峰期弹幕密集时，队列积压
- ⚠️ 无法快速跳过当前音频
- ⚠️ 主线程被阻塞

#### 7.2.2 解决方案：异步非阻塞播放

```python
import pygame
import threading
import asyncio

class AsyncAudioPlayer:
    """异步音频播放器"""

    def __init__(self):
        pygame.mixer.init()
        self.queue = asyncio.Queue()
        self.current_audio = None
        self.playing = False
        self.lock = threading.Lock()

        # 启动播放线程
        self.thread = threading.Thread(target=self._play_loop, daemon=True)
        self.thread.start()

    async def play(self, audio_path: Path):
        """添加到播放队列（非阻塞）"""
        await self.queue.put(audio_path)

    def _play_loop(self):
        """播放线程（在后台运行）"""
        while True:
            # 从队列获取音频（带超时）
            try:
                audio_path = asyncio.run(
                    self.queue.get(timeout=0.1)
                )
                self._play_audio(audio_path)
            except asyncio.TimeoutError:
                continue

    def _play_audio(self, audio_path: Path):
        """实际播放音频"""
        with self.lock:
            sound = pygame.mixer.Sound(str(audio_path))
            sound.play()
            self.current_audio = sound

            # 等待播放完成
            while pygame.mixer.get_busy():
                pygame.time.Clock().tick(10)

    def skip(self):
        """跳过当前音频"""
        with self.lock:
            pygame.mixer.stop()
            self.current_audio = None
```

**优势**:
- ✅ 主线程不被阻塞
- ✅ 可以随时 skip()
- ✅ 队列管理简单

---

### 7.3 播放队列优化

#### 7.3.1 智能去重

短时间内收到相同弹幕，只播一次：

```python
from collections import deque
import time

class SmartPlaybackQueue:
    """智能播放队列"""

    def __init__(self, window_seconds=5):
        self.queue = deque()
        self.played_history = deque()
        self.window = window_seconds  # 时间窗口

    async def add(self, text: str, audio_path: Path):
        # 检查最近是否播放过相同内容
        now = time.time()
        self._clean_history(now)

        # 检查去重
        for played_text, played_time in self.played_history:
            if played_text == text and (now - played_time) < self.window:
                print(f"[跳过] 重复弹幕: {text}")
                return

        # 添加到队列
        self.queue.append((text, audio_path, now))
        self.played_history.append((text, now))

    def _clean_history(self, now):
        """清理过期历史"""
        cutoff = now - self.window
        while self.played_history and self.played_history[0][1] < cutoff:
            self.played_history.popleft()
```

#### 7.3.2 队列优先级

VIP用户的弹幕优先播放：

```python
import heapq

class PriorityQueue:
    """优先级播放队列"""

    def __init__(self):
        self.queue = []
        self.counter = 0  # 用于保持FIFO顺序

    async def add(self, text: str, audio_path: Path, priority=0):
        """
        priority:
            2: VIP用户
            1: 普通用户
            0: 系统消息
        """
        heapq.heappush(self.queue, (priority, self.counter, text, audio_path))
        self.counter += 1

    async def get(self):
        """获取优先级最高的"""
        if self.queue:
            return heapq.heappop(self.queue)
        return None
```

---

### 7.4 错误处理详细设计

#### 7.4.1 错误分类

```python
class DanmuException(Exception):
    """弹幕异常基类"""
    pass

class ConnectionError(DanmuException):
    """连接异常"""
    pass

class TTSError(DanmuException):
    """TTS转换异常"""
    pass

class PlaybackError(DanmuException):
    """播放异常"""
    pass

class FilterError(DanmuException):
    """过滤异常"""
    pass
```

#### 7.4.2 错误处理策略

```python
import logging

logger = logging.getLogger(__name__)

async def safe_convert(tts_engine, text: str):
    """带错误处理的TTS转换"""
    try:
        audio_path = await tts_engine.convert(text)
        return audio_path

    except ConnectionError as e:
        # TTS API连接失败
        logger.error(f"TTS API连接失败: {e}")
        # 降级策略：跳过该弹幕
        return None

    except TTSError as e:
        # TTS转换失败
        logger.warning(f"TTS转换失败 [{text[:20]}...]: {e}")
        # 降级策略：跳过该弹幕
        return None

    except Exception as e:
        # 未知错误
        logger.error(f"未知错误: {e}")
        return None

async def safe_play(player, audio_path):
    """带错误处理的音频播放"""
    try:
        await player.play(audio_path)
        return True

    except PlaybackError as e:
        logger.error(f"播放失败 [{audio_path}]: {e}")
        return False

    except Exception as e:
        logger.error(f"播放异常: {e}")
        return False
```

#### 7.4.3 重试机制

```python
import asyncio

async def retry_with_backoff(func, max_retries=3, base_delay=1):
    """指数退避重试"""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                # 最后一次尝试也失败了
                raise

            # 计算延迟时间（指数退避）
            delay = base_delay * (2 ** attempt)
            logger.warning(f"重试 {attempt + 1}/{max_retries}, {delay}秒后: {e}")
            await asyncio.sleep(delay)

    return None
```

---

### 7.5 配置文件默认值

#### 7.5.1 默认配置

```python
# src/config/settings.py

from dataclasses import dataclass
from typing import List

@dataclass
class RoomConfig:
    room_id: str = ""
    auto_reconnect: bool = True
    heartbeat_interval: int = 30

@dataclass
class TTSConfig:
    engine: str = "edge"
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: str = "+0%"
    volume: str = "+0%"
    cache_enabled: bool = True
    cache_days: int = 7

@dataclass
class FilterConfig:
    min_length: int = 1
    max_length: int = 100
    enable_filter: bool = True
    blocked_users: List[str] = None
    blocked_keywords: List[str] = None

    def __post_init__(self):
        if self.blocked_users is None:
            self.blocked_users = []
        if self.blocked_keywords is None:
            self.blocked_keywords = []

@dataclass
class PlaybackConfig:
    max_queue_size: int = 10
    play_interval: float = 0.5
    volume: float = 0.7

@dataclass
class LogConfig:
    level: str = "INFO"
    enable_console: bool = True
    enable_file: bool = False

@dataclass
class AppConfig:
    room: RoomConfig = None
    tts: TTSConfig = None
    filter: FilterConfig = None
    playback: PlaybackConfig = None
    log: LogConfig = None

    def __post_init__(self):
        if self.room is None:
            self.room = RoomConfig()
        if self.tts is None:
            self.tts = TTSConfig()
        if self.filter is None:
            self.filter = FilterConfig()
        if self.playback is None:
            self.playback = PlaybackConfig()
        if self.log is None:
            self.log = LogConfig()

# 默认配置实例
DEFAULT_CONFIG = AppConfig()
```

#### 7.5.2 配置加载

```python
# src/config/loader.py

import configparser
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def load_config(path: str = "config.ini") -> AppConfig:
    """加载配置文件"""
    config_path = Path(path)

    # 检查文件是否存在
    if not config_path.exists():
        logger.warning(f"配置文件不存在: {config_path}")
        logger.info("使用默认配置")
        return DEFAULT_CONFIG

    # 解析配置文件
    parser = configparser.ConfigParser()
    try:
        parser.read(config_path, encoding='utf-8')
    except Exception as e:
        logger.error(f"配置文件解析失败: {e}")
        logger.info("使用默认配置")
        return DEFAULT_CONFIG

    # 转换为 AppConfig 对象
    try:
        config = AppConfig(
            room=RoomConfig(**parser['room']),
            tts=TTSConfig(**parser['tts']),
            filter=FilterConfig(**parser['filter']),
            playback=PlaybackConfig(**parser['playback']),
            log=LogConfig(**parser['log'])
        )
        logger.info(f"配置加载成功: {config_path}")
        return config

    except Exception as e:
        logger.error(f"配置转换失败: {e}")
        logger.info("使用默认配置")
        return DEFAULT_CONFIG
```

---

### 7.6 完整错误处理流程图

```
抖音直播间
    │
    ▼
连接失败？
├─ 是 → 自动重连（指数退避）
│         └─ 最多重试3次，失败后退出
└─ 否 → 继续

收到弹幕
    │
    ▼
过滤检查？
├─ 不符合规则 → 跳过，记录日志
└─ 符合规则 → 继续

TTS转换
    │
    ▼
转换失败？
├─ 是 → 跳过该弹幕，记录警告
│         └─ 继续处理下一条
└─ 否 → 继续

加入队列
    │
    ▼
队列已满？
├─ 是 → 删除最旧的弹幕
│         └─ 记录日志
└─ 否 → 加入队列

播放音频
    │
    ▼
播放失败？
├─ 是 → 跳过，记录错误
│         └─ 继续下一条
└─ 否 → 继续

循环处理...
```

---

## 8. 配置管理

### 7.1 配置文件 (config.ini)

```ini
[room]
room_id = 728804746624
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
blocked = user1,user2,user3
only_vip = false

[filter.keywords]
blocked = 垃圾,广告,刷屏
only =

[playback]
max_queue_size = 10
play_interval = 0.5
volume = 0.7

[log]
level = INFO
enable_console = true
enable_file = true
```

### 7.2 命令行参数

```bash
# 基本用法
python main.py <room_id>

# 指定配置文件
python main.py <room_id> --config custom.ini

# 调试模式
python main.py <room_id> --debug

# 指定音色
python main.py <room_id> --voice zh-CN-YunxiNeural

# 指定语速
python main.py <room_id> --rate +20%
```

---

## 8. 开发策略 🆕

### 8.1 MVP优先原则

**核心思想**: 先跑通核心流程，再逐步完善功能。

#### Phase 1: 最小可行版本 (MVP) - 2-3天

**目标**: 能够连接直播间、收到弹幕、听到语音

```
最简实现（忽略所有优化）：
┌─────────────────────────────────────┐
│  main.py (~100行代码)             │
│                                     │
│  1. 连接抖音直播间                 │
│     └─ 使用 douyin-live 库        │
│                                     │
│  2. 监听弹幕                       │
│     └─ async for message in live  │
│                                     │
│  3. TTS转换                        │
│     └─ edge_tts.Communicate()     │
│                                     │
│  4. 播放音频                       │
│     └─ pygame.mixer.Sound.play()  │
│                                     │
└─────────────────────────────────────┘

暂时不做：
❌ 播放队列（收到就播）
❌ 过滤规则（全部播放）
❌ 音频缓存（每次都转）
❌ 错误处理（简单print）
```

**验收标准**:
```bash
# 能够运行并听到语音
$ python main.py 728804746624
[INFO] 连接到直播间 728804746624
[INFO] 收到弹幕: 主播好厉害！
[播放] 主播好厉害！  ← 听到语音
```

#### Phase 2: 功能完善 - 3-4天

**目标**: 添加必要功能，提升可用性

```
功能清单：
├─ 配置文件管理 (config.ini)
│   └─ 解析配置，使用默认值
│
├─ 播放队列
│   ├─ 避免音频重叠
│   └─ 智能去重
│
├─ 弹幕过滤
│   ├─ 长度过滤
│   └─ 用户黑名单
│
├─ 音频缓存
│   └─ 避免重复转换
│
└─ 日志系统
    ├─ 彩色输出
    └─ 日志文件
```

#### Phase 3: 优化提升 - 2-3天

**目标**: 性能优化和用户体验

```
优化项：
├─ 异步非阻塞播放
│   └─ 独立播放线程
│
├─ 优先级队列
│   └─ VIP用户优先
│
├─ 错误处理
│   ├─ 自动重连
│   ├─ TTS失败降级
│   └─ 播放失败处理
│
├─ 性能优化
│   ├─ 减少延迟
│   └─ 资源占用优化
│
└─ 用户体验
    ├─ 统计信息
    └─ 优雅退出
```

### 8.2 开发顺序建议

```
第1天: 环境搭建
├─ 创建项目结构
├─ 安装依赖包
├─ 测试 douyin-live 库
└─ 测试 edge-tts

第2天: 核心功能
├─ 实现连接模块
├─ 实现TTS转换
├─ 实现pygame播放
└─ 集成到 main.py

第3天: 基本功能
├─ 添加配置管理
├─ 添加日志系统
├─ 添加简单过滤
└─ 测试完整流程

第4-5天: 完善功能
├─ 播放队列实现
├─ 音频缓存实现
├─ 高级过滤规则
└─ 错误处理

第6-7天: 优化测试
├─ 性能优化
├─ 稳定性测试
├─ 边界情况处理
└─ 文档完善
```

### 8.3 技术难点和解决方案

| 难点 | 解决方案 |
|-----|---------|
| **抖音协议复杂** | 使用现成库 `douyin-live` |
| **pygame 阻塞** | 使用独立播放线程 |
| **TTS 限流** | 本地缓存 + 智能去重 |
| **音频重叠** | 播放队列管理 |
| **连接不稳定** | 自动重连 + 心跳保活 |
| **高延迟** | 异步处理 + 管道优化 |

---

## 9. 部署方案

### 8.1 本地运行

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/LiveStreamInfoRetrievalProject.git
cd LiveStreamInfoRetrievalProject

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置
cp config.ini.example config.ini
# 编辑 config.ini，设置房间ID

# 4. 运行
python main.py 728804746624
```

### 8.2 打包为可执行文件

```bash
# 使用 PyInstaller 打包
pip install pyinstaller
pyinstaller --onefile --windowed main.py

# 生成 dist/main.exe (Windows) 或 dist/main (Linux/Mac)
```

### 8.3 系统要求

```
操作系统：
- Windows 10/11
- macOS 11+
- Linux (Ubuntu 20.04+)

Python版本：
- Python 3.11 或更高

硬件要求：
- CPU: 双核及以上
- 内存: 2GB+
- 磁盘: 500MB (用于音频缓存)
- 网络: 稳定的互联网连接
```

---

## 9. 开发计划

### 9.1 开发阶段

| 阶段 | 任务 | 预计时间 |
|-----|------|---------|
| **Phase 1** | 基础框架 | 2-3天 |
| ├─ 项目初始化 | 创建目录结构 | 0.5天 |
| ├─ 配置管理 | 实现配置加载 | 0.5天 |
| ├─ 日志系统 | 实现日志输出 | 0.5天 |
| └─ 主程序框架 | main.py 基础流程 | 1天 |
| **Phase 2** | 核心功能 | 3-4天 |
| ├─ 抖音连接 | WebSocket 连接 | 1天 |
| ├─ 协议解析 | Protobuf 解码 | 1天 |
| ├─ 弹幕过滤 | 过滤规则 | 0.5天 |
| └─ 消息处理 | 异步处理流程 | 1天 |
| **Phase 3** | TTS功能 | 2-3天 |
| ├─ edge-tts 集成 | 文字转语音 | 1天 |
| ├─ 音频缓存 | 本地缓存 | 0.5天 |
| └─ 音频优化 | 音质、速度优化 | 1天 |
| **Phase 4** | 播放功能 | 2天 |
| ├─ pygame 集成 | 音频播放 | 1天 |
| ├─ 播放队列 | 队列管理 | 0.5天 |
| └─ 播放控制 | 播放/停止/暂停 | 0.5天 |
| **Phase 5** | 测试优化 | 2-3天 |
| ├─ 功能测试 | 端到端测试 | 1天 |
| ├─ 性能优化 | 延迟优化 | 1天 |
| └─ 文档完善 | README + 使用说明 | 1天 |
| **总计** | | **11-15天** |

### 9.2 MVP功能范围

**第一个版本（MVP）包含**：
```
✅ 连接抖音直播间
✅ 捕获弹幕消息
✅ 文字转语音 (edge-tts)
✅ 语音播放
✅ 基本过滤（长度、黑名单用户）
✅ 命令行启动
✅ 日志输出
```

**未来版本可添加**：
```
📋 GUI界面 (Tkinter/PyQt)
📋 多房间支持
📋 播放历史记录
📋 统计分析
📋 录音功能
```

---

## 10. 附录

### 10.1 常见问题

**Q1: 如何获取抖音直播间ID？**
```
方法1: 打开直播间，URL中的数字就是room_id
方法2: 使用工具提取
```

**Q2: 支持哪些音色？**
```
edge-tts 支持所有微软Edge语音
常用中文音色:
- zh-CN-XiaoxiaoNeural (女声，温柔)
- zh-CN-YunxiNeural (男声，稳重)
- zh-CN-XiaoyiNeural (女声，活泼)
```

**Q3: 可以同时监听多个房间吗？**
```
MVP版本不支持
未来版本可以考虑多进程实现
```

### 10.2 限制和约束

```
当前限制：
├─ 单房间监听
├─ 单线程播放（不支持混音）
├─ 无Web界面
└─ 仅支持中文语音

技术限制：
├─ edge-tts 需要网络连接
├─ 音频缓存会占用磁盘空间
└─ 高峰期可能有播放延迟
```

### 10.3 参考资源

- [edge-tts 文档](https://github.com/rany2/edge-tts)
- [pygame 文档](https://www.pygame.org/docs/)
- [websockets 文档](https://websockets.readthedocs.io/)
- [抖音直播协议](https://github.com/zeusec/DouyinLive)

---

## 文档变更记录

| 版本 | 日期 | 变更说明 |
|-----|------|---------|
| v1.0.0 | 2024-02-01 | 初始版本（复杂架构） |
| v2.0.0 | 2024-02-02 | 简化架构（个人工具） |
| v2.1.0 | 2024-02-02 | **补充关键实现细节** |

---

## v2.1.0 更新说明 🆕

### 新增内容

1. **第7章：关键实现细节**
   - 抖音连接方案（使用现成库 vs 自己实现）
   - Cookie 获取方法
   - 音频播放并发问题解决方案
   - 智能播放队列（去重、优先级）
   - 完整的错误处理策略
   - 配置文件默认值

2. **第8章：开发策略**
   - MVP 优先原则
   - 三阶段开发计划
   - 具体开发顺序建议
   - 技术难点和解决方案对照表

### 关键决策

| 决策 | 选择 | 理由 |
|-----|------|------|
| **抖音连接** | 使用 `douyin-live` 库 | 节省开发时间 |
| **Cookie获取** | 手动获取（MVP） | 简单可靠 |
| **播放方式** | 异步非阻塞 | 避免主线程阻塞 |
| **错误处理** | 分层处理 + 降级策略 | 提高稳定性 |
| **开发顺序** | MVP → 完善功能 → 优化 | 快速验证可行性 |

### 架构完整性

```
✅ 系统架构     - 清晰明确
✅ 技术栈       - 精简合理
✅ 模块设计     - 详细的伪代码
✅ 数据流       - 完整流程图
✅ 配置管理     - 有默认值
✅ 错误处理     - 详细策略
✅ 开发策略     - MVP优先
✅ 部署方案     - 单机运行
```

### 可以直接实施了！

这份架构文档现在包含：
- ✅ 清晰的系统设计
- ✅ 具体的实现方案
- ✅ 详细的代码示例（伪代码）
- ✅ 完整的错误处理
- ✅ 明确的开发路径

**下一步**: 开始实施 MVP 版本！

---

**文档版本**: v2.1.0
**最后更新**: 2024-02-02
**更新内容**: 补充关键实现细节和开发策略
**维护者**: LiveStreamInfoRetrievalProject
**定位**: 简单实用的个人弹幕语音播报工具
