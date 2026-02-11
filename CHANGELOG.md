# 变更日志 (CHANGELOG)

本文档记录项目所有重要变更。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 规范。

---

## [Unreleased]

### 计划中
- 自动更新检查功能
- 更多音色支持
- 弹幕翻译功能
- 录制直播功能

---

## [0.1.0] - 2026-02-11

### 新增 (Added)

- ✨ **GUI界面** - 完整的PyQt5图形用户界面
  - 主窗口、控制面板、弹幕显示、日志输出
  - 菜单栏、状态栏
  - 深色主题样式

- ✨ **配置管理** - GUI配置管理器
  - 自动记住房间号
  - 保存窗口大小和位置
  - 黑名单管理

- ✨ **数据导出** - 弹幕记录导出功能
  - 导出为TXT格式
  - 导出为JSON格式（包含统计信息）
  - 支持清空历史记录

- ✨ **Chrome集成** - 自动启动Chrome调试模式
  - 自动检测Chrome是否运行
  - 一键启动调试模式
  - 连接状态提示

- ✨ **打包支持** - PyInstaller Windows可执行文件
  - onedir目录模式（启动快）
  - 资源文件正确打包
  - 独立运行，无需Python环境

### 改进 (Improved)

- 🎨 **深色主题** - 优化暗色UI样式
  - 统一配色方案
  - 改善可读性

- ⚡ **性能优化** - 异步队列避免竞态条件
  - 音量设置使用异步队列
  - TTS设置智能应用机制
  - 避免播放时拖动滑块导致卡顿

### 修复 (Fixed)

- 🐛 **音量设置竞态** - 修复pygame音量设置的线程安全问题
  - 实现异步队列更新音量
  - 避免与播放线程冲突

- 🐛 **播放卡顿** - 修复TTS转换时拖动滑块导致卡死
  - 添加转换锁机制
  - 设置缓存避免转换时修改

- 🐛 **主线程阻塞** - 修复播放语音时拖动滑块导致程序无响应
  - 优化滑块防抖时间
  - 减少响应延迟

### 文档 (Documentation)

- 📝 **用户手册** - 添加完整用户使用指南 (`docs/USER_GUIDE.md`)
  - 界面介绍
  - 功能说明
  - 常见问题解答

- 📝 **开发指南** - 添加开发者文档 (`docs/DEVELOPMENT_GUIDE.md`)
  - 环境搭建
  - 架构设计
  - 代码规范
  - 贡献流程

- 📝 **打包说明** - 在README添加打包章节
  - 下载和运行指南
  - 更新策略说明
  - 常见问题解答

### 技术细节 (Technical)

- **Python版本** - 兼容 Python 3.8+ (测试到 3.14.0)
- **依赖更新** - 锁定关键依赖版本
  - PyQt5==5.15.10
  - PyInstaller==6.18.0
  - edge-tts==6.1.9

- **构建系统** - 添加一键构建脚本
  - `build.bat` - Windows批处理脚本
  - `build.spec` - PyInstaller配置文件

---

## [0.0.x] - 2026-02-01 至 2026-02-10

### 新增 (Added)

- ✨ **WebSocket监听器** - WebSocket监听连接器 (`src/douyin/connector_websocket_listener.py`)
  - 通过Chrome CDP注入WebSocket监听
  - 低延迟，高稳定性
  - 自动重连机制

- ✨ **智能消息解析** - Protocol Buffers消息解析
  - 支持多种消息类型
  - 自动过滤系统消息
  - 提取用户昵称和内容

- ✨ **TTS缓存** - edge-tts音频缓存机制
  - 相同内容复用音频文件
  - 显著提升性能
  - 节省网络流量

- ✨ **黑名单过滤** - 用户和关键词黑名单
  - 实时过滤生效
  - GUI管理界面
  - 配置持久化

### 改进 (Improved)

- ⚡ **TTS转换优化** - 转换重试机制
  - 最多重试2次
  - 10秒超时
  - 失败不影响后续弹幕

- ⚡ **播放队列** - 异步播放队列系统
  - 确保顺序播放
  - 避免相互打断
  - 完整句子播放

### 修复 (Fixed)

- 🐛 **消息拆分** - 修复长弹幕被拆分成多条的问题
  - 完整句子播报
  - 标点符号处理

- 🐛 **Cookie过期** - 添加Cookie有效期检测
  - 提示用户重新获取
  - 优雅降级到HTTP模式

---

## [0.0.1] - 2026-01-20

### 新增 (Added)

- ✨ **HTTP轮询连接器** - HTTP轮询模式 (`src/douyin/connector_http.py`)
  - 作为WebSocket备选方案
  - 兼容性更好

- ✨ **Playwright连接器** - 真实浏览器连接 (`src/douyin/connector_real.py`)
  - 完全模拟真实用户行为
  - 绕过反爬虫机制

- ✨ **Mock测试连接器** - 测试用连接器 (`src/douyin/connector_mock.py`)
  - 不依赖网络
  - 快速功能测试

### 修复 (Fixed)

- 🐛 **连接稳定性** - 修复WebSocket自动断连问题
  - 心跳机制
  - 异常自动重连

---

## 版本说明

### 版本编号规则

项目采用 [语义化版本](https://semver.org/lang/zh-CN/)：

```
主版本号.次版本号.修订号 (MAJOR.MINOR.PATCH)

- MAJOR: 不兼容的API修改
- MINOR: 向下兼容的功能新增
- PATCH: 向下兼容的问题修复
```

### 下载特定版本

```bash
# 使用Git
git clone --branch v0.1.0 https://github.com/yourusername/yourrepo.git

# 或从Releases下载
# 访问: https://github.com/yourusername/yourrepo/releases
# 下载: 抖音弹幕语音播报工具-v0.1.0-win64.zip
```

---

## 贡献者

感谢所有贡献者的努力！

- **Claude Code** - 架构设计、打包实现、文档编写
- **ocean-lhj** - 项目创始人、核心功能实现

---

## 相关链接

- **GitHub仓库**: https://github.com/yourusername/yourrepo
- **Issue跟踪**: https://github.com/yourusername/yourrepo/issues
- **更新日志**: https://github.com/yourusername/yourrepo/blob/main/CHANGELOG.md
