# 抖音WebSocket连接器 - 问题追踪文档

## 文档信息

| 项目 | 信息 |
|-----|------|
| **问题ID** | ISSUE-001 |
| **模块** | WebSocket连接器 (src/douyin/connector.py) |
| **优先级** | P0 - 核心功能 |
| **状态** | ⏸️ 暂停，待深入研究 |
| **创建日期** | 2025-02-02 |
| **最后更新** | 2025-02-02 |

---

## 问题描述

### 目标
实现抖音直播间WebSocket连接，实时接收弹幕消息。

### 当前状态
❌ **无法建立WebSocket连接**

---

## 问题详情

### 尝试1: 从HTML提取WebSocket URL

**实施日期**: 2025-02-02

**方法**:
```python
# 从直播间HTML中提取WebSocket URL
url = f"https://live.douyin.com/{self.room_id}"
async with session.get(url, headers=headers) as resp:
    html = await resp.text()
    ws_matches = re.findall(r'"wss://([^"]+)"', html)
```

**结果**: ❌ **失败**

**问题分析**:
1. ✅ HTML成功获取（1.25MB）
2. ✅ ttwid cookie有效
3. ❌ WebSocket URL不直接在HTML中
4. ❌ URL通过JavaScript动态生成

**调试信息**:
- HTML包含195个'webcast'关键词
- HTML包含1个'websocket'关键词
- 但没有`wss://`格式的URL
- URL可能在混淆的JavaScript代码中

**调试文件**: `debug_page.html` (已保存)

---

### 尝试2: 使用已验证的WebSocket服务器地址

**实施日期**: 2025-02-02

**参考来源**:
- GitHub: `zeusec/DouyinLive`
- GitHub: `reqbat/douyin-live`

**使用的服务器列表**:
```python
WS_SERVERS = [
    "wss://webcast5-ws-web-lf.amemv.com/webcast/im/push/v2/",
    "wss://webcast5-ws-web-hl.amemv.com/webcast/im/push/v2/",
    "wss://webcast3-ws-web-lf.amemv.com/webcast/im/push/v2/",
    "wss://webcast62-ws-web-lf.amemv.com/webcast/im/push/v2/",
]
```

**测试ttwid**:
```
1%7CYlCMjX02ZOR2HqYrdJCB7PTikyVrzsXt8tWCYsVpYgA%7C1770031932%7Cbea202516c970c8f6848050ffc06b3c0f45ca8a4785ba6a0099a6e0446aa0c02
```

**结果**: ❌ **DNS解析失败**

**错误信息**:
```
[Errno 11001] getaddrinfo failed
```

**问题分析**:
1. ✅ websockets库API使用正确（`additional_headers`）
2. ✅ ttwid加载成功（长度127）
3. ❌ 所有4个服务器都无法解析
4. ❌ 可能原因：
   - 服务器地址已过时
   - 网络环境限制（DNS污染/GFW）
   - 需要额外的认证步骤

---

## 当前实现状态

### ✅ 已实现的功能

1. **WebSocket连接框架**
   - 文件: `src/douyin/connector.py`
   - 类: `DouyinConnector`
   - 行数: ~300行

2. **核心方法**
   - ✅ `connect()` - 连接逻辑（服务器无法解析）
   - ✅ `listen()` - 消息监听
   - ✅ `disconnect()` - 断开连接
   - ✅ `_heartbeat_loop()` - 心跳保活
   - ✅ `_parse_message()` - 消息解析（待完善）

3. **Mock连接器**
   - 类: `DouyinConnectorMock`
   - ✅ Mock测试通过
   - ✅ 验证了代码框架正确性

### ❌ 未实现的功能

1. **WebSocket URL获取**
   - 从HTML提取: 失败
   - 使用已知地址: DNS解析失败

2. **认证消息序列化**
   - protobuf序列化: 未实现（步骤1.7）
   - 认证协议: 未明确

3. **消息解析**
   - gzip解压: 已实现
   - protobuf反序列化: 未实现（步骤1.7）

---

## 技术细节

### 抖音协议分析

**协议类型**: WebSocket + Protobuf

**消息格式**:
```
[包头][序列号][消息类型][protobuf数据]
```

**消息类型**（推测）:
- WebChatMessage - 聊天消息
- WebGiftMessage - 礼物消息
- WebcastAuthMessage - 认证消息
- WebLiveEndEvent - 直播结束

**压缩**:
- 部分消息使用gzip压缩
- 需要检测并解压

### WebSocket服务器

**已知服务器**:
```
webcast5-ws-web-lf.amemv.com
webcast5-ws-web-hl.amemv.com
webcast3-ws-web-lf.amemv.com
webcast62-ws-web-lf.amemv.com
```

**问题**: 这些地址可能已过时或受网络限制

---

## 尝试过的解决方案

### 方案1: HTML解析 ✗
- 使用正则表达式提取
- 无法找到WebSocket URL

### 方案2: 已知服务器地址 ✗
- 使用GitHub项目中的地址
- DNS解析失败

### 方案3: JavaScript执行 (未尝试)
- 使用Selenium/Playwright
- 执行页面JavaScript获取URL
- **未实施原因**: 需要额外依赖

---

## 下一步建议

### 短期方案（当前）
1. ⏸️ **暂停连接器开发**
2. ✅ 先完成其他模块（TTS、播放器）
3. ✅ 使用Mock数据验证整体流程
4. 📝 **记录本文档供后续参考**

### 中期方案（步骤1.7完成后）
1. 📚 深入研究protobuf协议
2. 🔍 抓包分析真实WebSocket通信
3. 🧪 尝试不同的认证方式

### 长期方案
1. **方案A**: 使用Selenium获取动态URL
2. **方案B**: 研究最新的抖音协议（可能有变化）
3. **方案C**: 寻找维护中的第三方库
4. **方案D**: 考虑使用其他直播平台（协议更简单）

---

## 参考资料

### GitHub项目
1. **zeusec/DouyinLive**
   - URL: https://github.com/zeusec/DouyinLive
   - 状态: 未知（可能已停止维护）
   - 参考: WebSocket服务器列表

2. **reqbat/douyin-live**
   - URL: https://github.com/reqbat/douyin-live
   - 状态: 未知
   - 参考: 协议实现

### 技术文档
1. **Protobuf Schema**
   - 位置: `IMPLEMENTATION_PLAN.md` Appendix A
   - 内容: 消息结构定义

2. **协议实现指南**
   - 位置: `IMPLEMENTATION_PLAN.md` 步骤1.6
   - 内容: 详细的连接流程

### 测试文件
- `test_connector.py` - 基础测试
- `test_real_connection.py` - 真实连接测试
- `debug_room_info.py` - HTML调试脚本
- `debug_page.html` - 保存的页面HTML

---

## 测试记录

### 测试环境
- **Python版本**: 3.14
- **操作系统**: Windows
- **网络环境**: 可能受GFW影响
- **测试日期**: 2025-02-02

### 测试ttwid
```
1%7CYlCMjX02ZOR2HqYrdJCB7PTikyVrzsXt8tWCYsVpYgA%7C1770031932%7Cbea202516c970c8f6848050ffc06b3c0f45ca8a4785ba6a0099a6e0446aa0c02
```
- **长度**: 127字符
- **来源**: 用户提供的真实ttwid
- **有效性**: ✅ 通过Cookie验证

### 测试结果

| 测试项 | 结果 | 说明 |
|--------|------|------|
| ttwid加载 | ✅ 通过 | 长度127，格式正确 |
| HTML获取 | ✅ 通过 | 1.25MB |
| WebSocket URL提取 | ❌ 失败 | URL不在HTML中 |
| 已知服务器连接 | ❌ 失败 | DNS解析失败 |
| Mock连接器 | ✅ 通过 | 代码框架正确 |

---

## 依赖项

### Python包
```python
websockets>=12.0
aiohttp>=3.9.0
```

### 步骤依赖
- ✅ 步骤1.5: Cookie管理器（已完成）
- ⏸️ 步骤1.7: 消息解析器（protobuf解析，未完成）

---

## 附加信息

### 网络请求示例
```
GET https://live.douyin.com/728804746624 HTTP/1.1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...
Cookie: ttwid=1%7CYlCMjX02ZOR2HqYrdJCB7PTikyVrzsXt8tWCYsVpYgA%7C...

Status: 200 OK
Content-Length: 1253325
```

### HTML关键词统计
```
'webcast': 195 次
'websocket': 1 次
'room_id': 2 次
'roomid': 2 次
```

### 已保存的调试文件
- `debug_page.html` - 完整的页面HTML（1.25MB）
- `test_connector.py` - 连接器测试
- `test_real_connection.py` - 真实连接测试
- `debug_room_info.py` - HTML分析脚本

---

## 变更历史

| 日期 | 变更内容 | 作者 |
|------|---------|------|
| 2025-02-02 | 创建文档，记录初始问题 | Claude |
| 2025-02-02 | 添加尝试2的结果和DNS失败分析 | Claude |

---

## 备注

### 为什么暂停而不是继续？

**原因**:
1. 连接器是最复杂的部分
2. 其他模块（TTS、播放器）相对独立
3. 可以先用Mock数据验证整体流程
4. 避免在一个困难点上花费太多时间

### 何时继续？

**触发条件**:
- ✅ 其他模块（TTS、播放器）完成后
- ✅ 步骤1.7（protobuf解析）完成后
- ✅ 有更多时间深入研究
- ✅ 或找到新的参考资料

### 风险评估

**如果连接器无法实现**:
- **影响**: 核心功能缺失
- **备选方案**:
  1. 使用其他直播平台
  2. 使用录制的弹幕数据
  3. 等待第三方库更新
  4. 寻求社区帮助

---

## 附录：可能的解决思路

### 思路1: 抓包分析
使用Wireshark或Fiddler抓取真实的抖音直播WebSocket通信，获取：
- 真实的WebSocket URL
- 认证消息格式
- 消息结构

### 思路2: Selenium方案
```python
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

driver = webdriver.Chrome()
driver.get("https://live.douyin.com/728804746624")

# 执行JavaScript获取WebSocket URL
ws_url = driver.execute_script("return window.webcast.ws_url")
```

### 思路3: 查找最新实现
- 搜索GitHub新项目
- 查看技术论坛（如V2EX、知乎）
- 联系相关开发者

### 思路4: 协议逆向
- 使用charles/whistle抓包
- 分析JavaScript代码
- 研究protobuf定义文件

---

**文档结束**

**下次继续时，请先阅读本文档，了解已尝试的方案和当前状态。**
