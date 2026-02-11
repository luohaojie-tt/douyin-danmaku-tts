# GUI Module - 抖音弹幕语音播报工具图形界面

## 模块结构

```
src/gui/
├── __init__.py           # 包初始化
├── main_window.py        # 主窗口
├── control_panel.py      # 控制面板
├── danmaku_widget.py     # 弹幕显示组件
├── log_widget.py         # 日志输出组件
├── status_bar.py         # 状态栏
└── settings_dialog.py    # 设置对话框
```

## 组件说明

### MainWindow (main_window.py)
主应用程序窗口，整合所有UI组件。

**特性:**
- 菜单栏 (文件/设置/帮助)
- 分割器布局 (左侧控制，右侧弹幕)
- 日志输出区域
- 状态栏
- 深色主题

**关键方法:**
- `_init_ui()`: 初始化UI布局
- `_apply_theme()`: 应用深色主题
- `_export_txt()`: 导出TXT (待实现)
- `_export_json()`: 导出JSON (待实现)

### ControlPanel (control_panel.py)
用户控制界面。

**信号:**
- `connect_requested(str)`: 请求连接 (参数: 房间号)
- `disconnect_requested()`: 请求断开
- `tts_enabled_changed(bool)`: TTS开关变化
- `speech_rate_changed(int)`: 语速变化 (-50 到 +100)
- `volume_changed(int)`: 音量变化 (0-100)

**关键方法:**
- `get_room_id()`: 获取房间号
- `set_connected(bool)`: 设置连接状态
- `open_settings_dialog()`: 打开设置对话框

### DanmakuWidget (danmaku_widget.py)
弹幕显示列表。

**信号:**
- `count_changed(int)`: 消息数量变化

**关键方法:**
- `add_danmaku(username, content, timestamp)`: 添加弹幕
- `clear_danmaku()`: 清空所有弹幕
- `get_message_count()`: 获取消息数量
- `get_all_messages()`: 获取所有消息

### LogWidget (log_widget.py)
日志输出显示。

**关键方法:**
- `add_log(level, message, source)`: 添加日志
- `info(message, source)`: INFO级别
- `warning(message, source)`: WARNING级别
- `error(message, source)`: ERROR级别
- `debug(message, source)`: DEBUG级别

### StatusBar (status_bar.py)
状态栏显示。

**关键方法:**
- `set_connected(bool, room_id)`: 设置连接状态
- `set_message_count(int)`: 设置消息计数
- `increment_message_count()`: 消息计数+1
- `set_error_count(int)`: 设置错误计数
- `increment_error_count()`: 错误计数+1
- `show_message(message, timeout)`: 显示临时消息

### SettingsDialog (settings_dialog.py)
设置对话框。

**标签页:**
- 过滤器: 关键词黑名单、用户黑名单
- 高级: 高级设置 (待实现)
- 关于: 版本信息

## 使用方法

### 启动GUI

```bash
python main_gui.py
```

### 主题样式

深色主题位于 `resources/styles/dark_theme.qss`

### 信号连接示例

```python
# 连接控制面板信号
control_panel.signals.connect_requested.connect(self.on_connect)
control_panel.signals.disconnect_requested.connect(self.on_disconnect)
control_panel.signals.tts_enabled_changed.connect(self.on_tts_changed)

# 连接弹幕组件信号
danmaku_widget.signals.count_changed.connect(self.on_count_changed)
```

## 线程安全注意

⚠️ **重要**: PyQt5的GUI更新必须在主线程进行。

从异步后端更新GUI时，使用 `QThread.currentThread()` 检查或使用信号/槽机制确保线程安全。

```python
# 正确: 使用信号
self.danmaku_signal.emit(username, content)

# 错误: 直接从后台线程调用
self.danmaku_widget.add_danmaku(username, content)  # 可能崩溃
```

## 依赖

- PyQt5==5.15.10
- PyQt5-Qt5==5.15.2
- PyQt5-sip==12.13.0

## 开发状态

✅ Phase 1: 基础设置完成
✅ Phase 3: UI组件完成
⏳ Phase 4: 信号集成 (Backend Developer)
⏳ Phase 5: 导出功能
⏳ Phase 6: 测试和代码审查
