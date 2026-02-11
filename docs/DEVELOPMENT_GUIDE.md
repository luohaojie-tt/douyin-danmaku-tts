# 开发者指南

## 📋 目录

1. [开发环境搭建](#开发环境搭建)
2. [项目结构](#项目结构)
3. [架构设计](#架构设计)
4. [添加新功能](#添加新功能)
5. [测试指南](#测试指南)
6. [打包发布](#打包发布)
7. [代码规范](#代码规范)

---

## 开发环境搭建

### 系统要求

- **Python**: 3.8+ (推荐 3.14.0)
- **操作系统**: Windows 10/11, Linux, macOS
- **浏览器**: Google Chrome (用于真实连接测试)
- **IDE**: Visual Studio Code, PyCharm 等

### 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/yourrepo.git
cd LiveStreamInfoRetrievalProject

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行CLI版本
python main.py <room_id> --ws

# 5. 运行GUI版本
python main_gui.py
```

### 依赖说明

**核心依赖：**
```txt
websockets==16.0          # WebSocket协议
edge-tts==6.1.9          # Microsoft Edge TTS
pygame-ce==2.5.0         # 音频播放
protobuf==4.25.1          # Protocol Buffers
playwright==1.40.0         # 浏览器自动化
aiohttp==3.9.1            # HTTP客户端
PyQt5==5.15.10           # GUI框架
PyInstaller==6.18.0         # 打包工具
```

**开发工具：**
```txt
pytest                      # 单元测试
pytest-asyncio             # 异步测试
pytest-qt                 # PyQt测试
black                       # 代码格式化
pylint                      # 代码检查
```

---

## 项目结构

```
LiveStreamInfoRetrievalProject/
├── main.py                    # CLI入口程序
├── main_gui.py                # GUI入口程序
├── config.ini                 # 配置文件
├── requirements.txt            # Python依赖
├── build.spec                 # PyInstaller配置
├── build.bat                  # 一键构建脚本
│
├── src/                      # 源代码目录
│   ├── config/                # 配置管理
│   │   ├── settings.py       # 配置加载和保存
│   │   └── constants.py      # 常量定义
│   │
│   ├── douyin/                # 抖音模块
│   │   ├── __init__.py
│   │   ├── connector_*.py    # 连接器实现
│   │   ├── parser_*.py       # 消息解析器
│   │   └── models.py         # 数据模型
│   │
│   ├── tts/                   # 文字转语音
│   │   ├── __init__.py
│   │   └── edge_tts.py       # Edge TTS封装
│   │
│   ├── player/                # 音频播放
│   │   ├── __init__.py
│   │   └── pygame_player.py   # Pygame播放器
│   │
│   ├── backend/               # 后端业务逻辑
│   │   ├── danmaku_orchestrator.py  # 核心编排器
│   │   ├── gui_orchestrator.py      # GUI版本
│   │   ├── gui_config_manager.py     # GUI配置
│   │   └── chrome_debug_manager.py  # Chrome管理
│   │
│   └── gui/                   # PyQt5界面
│       ├── __init__.py
│       ├── main_window.py     # 主窗口
│       ├── control_panel.py   # 控制面板
│       ├── danmaku_widget.py  # 弹幕显示
│       ├── log_widget.py      # 日志输出
│       └── status_bar.py      # 状态栏
│
├── resources/                # 资源文件
│   └── styles/
│       └── dark_theme.qss   # 深色主题
│
├── tools/                   # 工具脚本
│   ├── get_room_id.py        # 获取房间号
│   └── capture_websocket.py  # WebSocket抓包
│
├── docs/                    # 文档
│   ├── ARCHITECTURE.md       # 架构设计
│   ├── USER_GUIDE.md        # 用户手册
│   └── DEVELOPMENT_GUIDE.md  # 开发指南
│
├── cache/                   # TTS音频缓存（运行时生成）
└── logs/                    # 日志文件（运行时生成）
```

---

## 架构设计

### 三层架构

```
┌─────────────────────────────────────────────────┐
│              表现层 (Presentation)            │
│  ┌─────────────┬──────────────┐       │
│  │   CLI界面    │   GUI界面      │       │
│  │ (main.py)   │ (main_gui.py) │       │
│  └─────────────┴──────────────┘       │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│              业务逻辑层 (Business)           │
│  ┌──────────────────────────────────┐       │
│  │   DanmakuOrchestrator      │       │
│  │   - 消息处理                 │       │
│  │   - TTS转换                  │       │
│  │   - 播放队列                  │       │
│  └──────────────────────────────────┘       │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│              数据访问层 (Data)               │
│  ┌──────────────┬──────────────┐       │
│  │  连接器        │  解析器       │       │
│  │  Connector     │  Parser       │       │
│  └──────────────┴──────────────┘       │
└─────────────────────────────────────────────────┘
```

### 核心组件

#### 1. 连接器 (Connector)

**职责：**
- 连接到抖音直播间
- 监听/轮询消息
- 断开连接
- 错误处理

**接口定义：**
```python
class Connector(ABC):
    @abstractmethod
    async def connect(self) -> bool:
        """连接到直播间"""

    @abstractmethod
    async def listen(self, callback):
        """监听消息"""

    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
```

**实现类：**
- `DouyinConnectorMock` - Mock测试连接器
- `DouyinHTTPConnector` - HTTP轮询连接器
- `DouyinConnectorReal` - Playwright真实连接器
- `WebSocketListenerConnector` - WebSocket监听连接器（推荐）

#### 2. 解析器 (Parser)

**职责：**
- 解析原始消息数据
- 提取用户名、内容、时间戳
- 统一输出格式

**接口定义：**
```python
class ParsedMessage:
    method: str      # 消息类型
    user: UserInfo    # 用户信息
    content: str      # 消息内容
    timestamp: str   # 时间戳
```

#### 3. TTS引擎 (EdgeTTS)

**职责：**
- 文字转语音
- 音频缓存
- 音色/语速管理

**关键方法：**
```python
class EdgeTTS:
    async def convert_with_cache(self, text: str, cache_dir: Path) -> Path:
        """转换语音（带缓存）"""

    @property
    def voice(self) -> str:
        """获取/设置音色"""

    @property
    def rate(self) -> str:
        """获取/设置语速"""
```

#### 4. 播放器 (PygamePlayer)

**职责：**
- 音频文件播放
- 音量控制
- 队列管理

**关键方法：**
```python
class PygamePlayer:
    async def play(self, audio_path: Path):
        """异步播放音频"""

    def set_volume(self, volume: float):
        """设置音量（线程安全）"""

    def cleanup(self):
        """释放资源"""
```

### 数据流

```
抖音直播间
    ↓
Connector连接
    ↓
接收原始消息（bytes/dict）
    ↓
Parser解析
    ↓
ParsedMessage（用户名+内容）
    ↓
过滤黑名单
    ↓
TTS转换（带缓存）
    ↓
音频文件（.mp3）
    ↓
Player播放队列
    ↓
音频输出
```

---

## 添加新功能

### 添加新的连接器

**步骤：**

1. **创建文件** `src/douyin/connector_yourname.py`

2. **实现接口**
```python
from src.douyin.connector_base import Connector

class YourConnector(Connector):
    async def connect(self) -> bool:
        # 实现连接逻辑
        pass

    async def listen(self, callback):
        # 实现监听逻辑
        pass

    async def disconnect(self):
        # 实现断开逻辑
        pass
```

3. **注册到main.py**
```python
# 添加命令行参数
parser.add_argument('--yourmode', action='store_true')

# 实例化
if args.yourmode:
    connector = YourConnector(room_id, config)
```

4. **更新文档**
   - 在 README.md 添加说明
   - 更新连接器对比表

### 添加新的TTS引擎

**步骤：**

1. **创建文件** `src/tts/your_tts.py`

2. **实现接口**
```python
class YourTTS:
    async def convert(self, text: str) -> Path:
        # 返回音频文件路径
        pass

    def set_voice(self, voice: str):
        # 设置音色
        pass
```

3. **集成到DanmakuOrchestrator**
```python
from src.tts.your_tts import YourTTS

# 在 __init__ 中
self.tts = YourTTS(voice, rate)
```

### 添加GUI功能

**步骤：**

1. **在src/gui/中创建新组件**

2. **定义Qt信号**
```python
from PyQt5.QtCore import QObject, pyqtSignal

class YourWidget(QObject):
    # 定义信号
    data_changed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        # 初始化UI
```

3. **连接到MainWindow**
```python
# 在 MainWindow.__init__ 中
self.your_widget = YourWidget()
self.your_widget.data_changed.connect(self._on_data_changed)
```

4. **更新样式表**
```css
/* 在 resources/styles/dark_theme.qss */
YourWidget {
    background-color: #2b2b2b;
    border: 1px solid #3d3d3d;
}
```

---

## 测试指南

### 单元测试

**运行测试：**
```bash
# 运行所有测试
pytest

# 运行特定文件
pytest tests/test_connector.py

# 带覆盖率报告
pytest --cov=src --cov-report=html
```

**测试示例：**
```python
import pytest
from src.douyin.connector_mock import DouyinConnectorMock

@pytest.mark.asyncio
async def test_mock_connector():
    connector = DouyinConnectorMock("123456789")
    assert await connector.connect() == True
    assert connector.is_connected == True

    await connector.disconnect()
    assert connector.is_connected == False
```

### 集成测试

**手动测试清单：**

- [ ] 各连接器都能正常工作
- [ ] TTS转换成功并播放
- [ ] 播放队列按顺序执行
- [ ] 黑名单过滤生效
- [ ] 配置保存和加载正常
- [ ] GUI所有按钮可点击
- [ ] 异常情况下程序不崩溃

### 端到端测试

**测试场景：**

1. **正常流程**
   - 连接直播间 → 接收弹幕 → 语音播报 → 断开连接

2. **错误处理**
   - 无效房间号 → 网络断开 → Cookie过期

3. **边界情况**
   - 长弹幕内容 → 特殊字符 → 快速连续消息

---

## 打包发布

### 本地构建

```bash
# 方法1：使用脚本
build.bat

# 方法2：手动打包
python -m PyInstaller build.spec
```

### 构建配置

**build.spec 关键配置：**

```python
# 工作目录和路径
base_path = Path.cwd()

# 数据收集
datas = [
    ('config.ini', '.'),                    # 配置文件
    ('cookies.txt.example', '.'),             # Cookie示例
    ('resources/styles', 'resources/styles'), # 样式表
]

# 隐藏导入（重要！）
hiddenimports = [
    'src.*',                                # 所有项目模块
    'main',                                 # main模块
    'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
]

# 排除不需要的模块（减小体积）
excludes = ['tkinter', 'matplotlib', 'pandas']
```

### 发布流程

**版本发布检查清单：**

- [ ] 更新版本号（README.md, main_gui.py）
- [ ] 运行完整测试
- [ ] 构建成功无错误
- [ ] 在干净系统测试exe
- [ ] 准备发布说明
- [ ] 创建Git Tag
- [ ] 推送到GitHub
- [ ] 创建GitHub Release

**创建Release：**
```bash
# 1. 打标签
git tag v0.2.0
git push origin v0.2.0

# 2. 构建分发包
cd dist/抖音弹幕播报
zip -r ../../抖音弹幕语音播报工具-v0.2.0-win64.zip .

# 3. 在GitHub创建Release
# 上传 zip 文件
# 填写变更日志
```

---

## 代码规范

### Python代码风格

**命名规范：**
```python
# 类名：大驼峰
class DouyinConnector:

# 函数/方法：小写+下划线
def connect_to_room():

# 常量：全大写+下划线
DEFAULT_ROOM_ID = "123456789"

# 私有成员：单下划线开头
self._internal_state
```

**类型提示：**
```python
from typing import Optional, List, Dict

def get_messages(count: int) -> List[Dict]:
    """函数必须有类型提示"""
    pass
```

**文档字符串：**
```python
def process_message(raw_message: bytes) -> Optional[ParsedMessage]:
    """
    处理原始消息

    Args:
        raw_message: 原始消息字节流

    Returns:
        解析后的消息对象，解析失败返回None

    Raises:
        ValueError: 消息格式错误
    """
    pass
```

### 异步编程规范

**使用asyncio：**
```python
import asyncio

async def main():
    # 创建任务
    task1 = asyncio.create_task(func1())
    task2 = asyncio.create_task(func2())

    # 等待完成
    await asyncio.gather(task1, task2)

# 运行
asyncio.run(main())
```

**错误处理：**
```python
try:
    await risky_operation()
except SpecificError as e:
    logger.error(f"特定错误: {e}")
    # 处理错误
except Exception as e:
    logger.exception(f"未知错误: {e}")
    # 优雅降级
```

### Git提交规范

**提交消息格式：**
```
<type>: <subject>

<body>
```

**类型（type）：**
- `feat` - 新功能
- `fix` - Bug修复
- `refactor` - 代码重构
- `perf` - 性能优化
- `docs` - 文档更新
- `test` - 测试相关
- `chore` - 构建/工具更新

**示例：**
```
feat: 添加WebSocket连接器

实现WebSocket监听模式，提供更低延迟的弹幕接收。
支持自动重连和错误恢复。

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### 日志规范

**日志级别使用：**
```python
logger.debug("详细调试信息")      # 开发调试
logger.info("一般信息")           # 正常流程
logger.warning("警告信息")          # 可恢复的问题
logger.error("错误信息")            # 需要关注的错误
logger.exception("异常堆栈")       # 异常跟踪
```

**日志内容：**
```python
# ✅ 好的日志
logger.info(f"连接成功: {room_id}")

# ❌ 不好的日志
logger.info("连接成功")
```

---

## 贡献指南

### Pull Request流程

1. **Fork仓库**
2. **创建分支** `git checkout -b feature/your-feature`
3. **编写代码** 遵循代码规范
4. **编写测试** 确保覆盖率 > 80%
5. **提交代码** 使用规范的提交消息
6. **Push到Fork** `git push origin feature/your-feature`
7. **创建PR** 填写PR模板

### Code Review检查清单

- [ ] 代码符合风格指南
- [ ] 包含单元测试
- [ ] 测试全部通过
- [ ] 文档已更新
- [ ] 没有引入新的警告
- [ ] Git历史清晰

---

## 资源链接

**官方文档：**
- [PyQt5](https://www.riverbankcomputing.com/static/Docs/PyQt5/)
- [edge-tts](https://github.com/rany2/edge-tts)
- [playwright](https://playwright.dev/python/)
- [asyncio](https://docs.python.org/3/library/asyncio.html)

**社区资源：**
- [PyInstaller文档](https://pyinstaller.org/en/stable/)
- [Python类型提示](https://docs.python.org/3/library/typing.html)
- [异步编程最佳实践](https://docs.python.org/3/howto/asyncio.html)

---

**最后更新：** 2026-02-11
**维护者：** LiveStreamInfoRetrievalProject Team
