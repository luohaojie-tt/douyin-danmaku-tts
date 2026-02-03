# 抖音弹幕语音播报工具

实时提取抖音直播间弹幕，并使用 Microsoft Edge TTS 转换为语音播放。

## 功能特性

- ✅ **实时弹幕提取** - 支持多种连接方式（WebSocket、HTTP轮询、浏览器监听）
- ✅ **智能消息过滤** - 自动过滤系统消息，只保留真实用户弹幕
- ✅ **完整句子播放** - 确保一条弹幕完整播放，不会被拆分
- ✅ **顺序不中断播放** - 弹幕按顺序排队播放，不会相互打断
- ✅ **语音缓存** - 相同内容复用音频文件，提升性能
- ✅ **多种音色支持** - 支持所有 Edge TTS 音色
- ✅ **可配置参数** - 语速、音量、音色均可自定义

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 获取 Cookie

1. 打开浏览器访问抖音直播间
2. 打开开发者工具 (F12) → Application → Cookies
3. 找到 `ttwid` cookie，复制其值
4. 将值保存到项目根目录的 `cookies.txt` 文件中

### 3. 启动 Chrome（调试模式）

```bash
# Windows
chrome.exe --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222

# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

### 4. 运行程序

```bash
# 使用 WebSocket 监听模式（推荐）
python main.py <直播间ID> --ws

# 使用 HTTP 轮询模式
python main.py <直播间ID> --http

# 使用 Mock 模式（测试）
python main.py <直播间ID> --mock

# 启用调试日志
python main.py <直播间ID> --ws --debug
```

## 获取直播间 ID

### 方法1：从 URL 获取

直播间的 URL 格式为：
```
https://live.douyin.com/123456789
```

最后面的数字部分就是直播间 ID（如：`123456789`）

### 方法2：使用工具脚本

```bash
python tools/get_room_id.py
```

## 配置说明

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `room_id` | 直播间房间ID（必需） | - |
| `--ws` | 使用WebSocket监听模式（推荐） | 否 |
| `--http` | 使用HTTP轮询模式 | 否 |
| `--real` | 使用Playwright真实连接模式 | 否 |
| `--mock` | 使用Mock测试模式 | 否 |
| `--debug` | 启用调试日志 | 否 |
| `--config` | 配置文件路径 | config.ini |
| `--voice` | TTS音色 | zh-CN-XiaoxiaoNeural |
| `--rate` | TTS语速 | +0% |
| `--volume` | 播放音量 (0.0-1.0) | 0.7 |

### 配置文件 (config.ini)

```ini
[tts]
voice = zh-CN-XiaoxiaoNeural
rate = +0%
volume = +0%

[playback]
volume = 0.7
```

## 项目结构

```
LiveStreamInfoRetrievalProject/
├── main.py                      # 主程序入口
├── config.ini                   # 配置文件
├── cookies.txt                  # Cookie文件
├── cache/                       # TTS音频缓存
│
├── codemaps/                    # 代码映射文档
│   ├── architecture.md          # 系统架构
│   ├── backend.md               # 后端实现
│   ├── frontend.md              # CLI接口
│   └── data.md                  # 数据结构
│
├── src/
│   ├── config/                  # 配置管理
│   ├── douyin/                  # 抖音模块
│   │   ├── connector_*.py       # 各种连接器实现
│   │   └── parser_*.py          # 各种解析器实现
│   ├── tts/                     # 文字转语音
│   │   └── edge_tts.py
│   └── player/                  # 音频播放
│       └── pygame_player.py
│
└── tools/                       # 工具脚本
```

## 连接器对比

| 连接器 | 模式 | Chrome必需 | 稳定性 | 推荐度 |
|--------|------|-----------|--------|--------|
| WebSocketListenerConnector | 浏览器WS监听 | ✅ | ⭐⭐⭐⭐⭐ | 最推荐 |
| DouyinHTTPConnector | HTTP轮询 | ✅ | ⭐⭐⭐⭐ | 推荐 |
| DouyinConnectorReal | Playwright | ✅ | ⭐⭐⭐⭐ | 推荐 |
| DouyinConnector | 标准WS | ❌ | ⭐⭐⭐ | 备选 |
| DouyinConnectorMock | Mock测试 | ❌ | ⭐⭐⭐ | 测试用 |

## 技术栈

- **Python 3.8+**
- **websockets** - WebSocket 协议支持
- **playwright** - 浏览器自动化
- **edge-tts** - Microsoft Edge 文字转语音
- **pygame-ce** - 音频播放
- **protobuf** - Protocol Buffers 解码

## 开发说明

### 添加新的连接器

1. 在 `src/douyin/` 创建 `connector_<name>.py`
2. 实现接口：`connect()`, `listen()`, `disconnect()`
3. 在 `main.py` 中添加命令行参数
4. 更新文档

### 添加新的解析器

1. 在 `src/douyin/` 创建 `parser_<name>.py`
2. 解析为 `ParsedMessage` 格式
3. 在连接器中集成
4. 更新文档

## 常见问题

### Q: 找不到 ttwid？
A: 确保已在 Chrome 中登录抖音账号，然后在开发者工具中查找 Cookie。

### Q: 连接失败？
A: 检查 Chrome 是否在调试模式下运行（`--remote-debugging-port=9222`）

### Q: 没有声音？
A: 检查系统音量和配置文件中的音量设置。

### Q: 弹幕被拆分成多条？
A: 已在最新版本中修复，确保使用最新代码。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 致谢

- [edge-tts](https://github.com/rany2/edge-tts) - Microsoft Edge TTS 引擎
- [pygame-ce](https://github.com/pygame-community/pygame-ce) - 音频播放库
- [playwright](https://playwright.dev/) - 浏览器自动化
