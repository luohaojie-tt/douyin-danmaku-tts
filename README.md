# 抖音弹幕语音播报工具

一个**极简的Python命令行工具**，用于实时捕获抖音直播间的弹幕，并转换成语音播放。

**核心价值**：解放双眼，用耳朵听弹幕。

## 特性

- ✅ **单机运行**：无需服务器，本地Python脚本
- ✅ **开箱即用**：配置一次，永久使用
- ✅ **轻量级**：核心代码 < 1000行
- ✅ **免费**：使用免费的Edge-TTS
- ✅ **实时性**：弹幕延迟 < 2秒

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置Cookie

1. 打开浏览器访问 https://live.douyin.com
2. 按F12打开开发者工具
3. Application → Cookies → 复制 `ttwid` 的值
4. 将值粘贴到 `cookies.txt` 文件中

### 3. 运行程序

```bash
python main.py <room_id>
```

例如：
```bash
python main.py 728804746624
```

## 配置说明

编辑 `config.ini` 文件可以自定义以下设置：

### 直播间配置
```ini
[room]
room_id = 728804746624          # 房间ID
cookie_file = cookies.txt        # Cookie文件
auto_reconnect = true           # 自动重连
```

### 语音配置
```ini
[tts]
voice = zh-CN-XiaoxiaoNeural    # 音色
rate = +0%                      # 语速
volume = +0%                    # 音量
cache_enabled = true            # 启用缓存
```

### 过滤规则
```ini
[filter]
min_length = 1                  # 最小长度
max_length = 100                # 最大长度
blocked = 垃圾,广告,刷屏         # 屏蔽关键词
```

## 系统要求

- **操作系统**：Windows 10/11, macOS 11+, Linux (Ubuntu 20.04+)
- **Python版本**：Python 3.11 或更高
- **硬件**：CPU双核及以上，内存2GB+
- **网络**：稳定的互联网连接

## 项目结构

```
LiveStreamInfoRetrievalProject/
├── main.py                 # 程序入口
├── config.ini              # 配置文件
├── requirements.txt        # 依赖包
├── cookies.txt            # Cookie配置
│
├── src/                   # 源代码
│   ├── config/           # 配置管理
│   ├── douyin/           # 抖音连接
│   ├── tts/              # 文字转语音
│   ├── player/           # 音频播放
│   ├── filter/           # 弹幕过滤
│   └── utils/            # 工具函数
│
├── tests/                # 测试代码
├── cache/                # 音频缓存
└── logs/                 # 日志文件
```

## 开发状态

当前版本：v0.1.0（开发中）

- [x] 项目架构设计
- [x] 实施计划制定
- [ ] 核心功能开发
- [ ] 测试和优化

## 文档

- [架构设计文档](ARCHITECTURE.md) - v2.1.0
- [实施计划文档](IMPLEMENTATION_PLAN.md) - v1.3
- [开发日志](DEVELOPMENT_LOG.md)

## 许可证

MIT License

## 联系方式

项目地址：[GitHub](https://github.com/your-repo/LiveStreamInfoRetrievalProject)
