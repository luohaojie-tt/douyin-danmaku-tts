# 故障排除指南

本文档帮助用户和开发者诊断和解决常见问题。

---

## 📋 目录

1. [安装问题](#安装问题)
2. [连接问题](#连接问题)
3. [播放问题](#播放问题)
4. [性能问题](#性能问题)
5. [打包问题](#打包问题)
6. [调试技巧](#调试技巧)

---

## 安装问题

### 错误：Python not found

**症状：**
```
'python' 不是内部或外部命令
```

**解决方案：**

1. **安装Python**
   - 下载：https://www.python.org/downloads/
   - 推荐：Python 3.14.0 (64位)
   - 安装时勾选 "Add Python to PATH"

2. **验证安装**
   ```bash
   python --version
   # 应显示: Python 3.14.0
   ```

3. **手动添加到PATH**（如果需要）
   - 控制面板 → 系统 → 高级系统设置
   - 环境变量 → Path → 编辑
   - 添加 Python 安装路径

### 错误：Module not found

**症状：**
```
ModuleNotFoundError: No module named 'PyQt5'
```

**解决方案：**

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **检查虚拟环境**
   ```bash
   # 确保在正确的环境中
   pip list | grep PyQt5
   ```

3. **重新安装**
   ```bash
   pip uninstall PyQt5
   pip install PyQt5==5.15.10
   ```

### 错误：Chrome not found

**症状：**
```
RuntimeError: Chrome not installed or not found
```

**解决方案：**

1. **安装Google Chrome**
   - 下载：https://www.google.com/chrome/
   - 完成安装后重启电脑

2. **添加到PATH**（Linux）
   ```bash
   export PATH="$PATH:/opt/google/chrome/chrome"
   ```

3. **指定Chrome路径**（如果非标准位置）
   ```python
   # 在config.ini中设置
   [chrome]
   path = C:/Users/Username/AppData/Local/Google/Chrome/Application/chrome.exe
   ```

### 错误：DLL文件缺失

**症状：**
```
ImportError: DLL load failed: 找不到指定的模块
```

**解决方案：**

1. **安装 Visual C++ Redistributable**
   - 下载：https://aka.ms/vs/17/release/vc_redist.x64.exe
   - 运行安装程序
   - 重启电脑

2. **验证安装**
   - 控制面板 → 程序和功能
   - 查看 "Microsoft Visual C++ 2015-2022 Redistributable"

---

## 连接问题

### 错误：Connection timeout

**症状：**
```
TimeoutError: 连接超时，请检查网络
```

**诊断步骤：**

1. **检查网络连接**
   ```bash
   ping live.douyin.com
   ```

2. **检查防火墙**
   - 允许Python通过防火墙
   - 检查公司/学校网络限制

3. **使用代理**（如果在受限网络）
   ```bash
   set HTTP_PROXY=http://proxy.example.com:8080
   set HTTPS_PROXY=http://proxy.example.com:8080
   ```

4. **切换连接模式**
   - 尝试使用 `--http` 参数（HTTP轮询模式）
   - WebSocket可能被网络策略阻止

### 错误：Invalid room ID

**症状：**
```
ValueError: 无效的房间号
```

**解决方案：**

1. **验证房间号**
   - 访问直播间页面
   - 从URL提取：`https://live.douyin.com/123456789`
   - 只取数字部分

2. **检查直播间状态**
   - 房间可能已关闭
   - 用户可能被禁播

3. **使用工具获取**
   ```bash
   python tools/get_room_id.py
   ```

### 错误：Cookie expired

**症状：**
```
AuthenticationError: Cookie已过期或无效
```

**解决方案：**

1. **重新获取Cookie**
   - 打开Chrome → 访问抖音
   - F12 → Application → Cookies
   - 复制新的 ttwid 值

2. **更新cookies.txt**
   ```
   ttwid=1%2C新值...
   ```

3. **验证格式**
   - 只包含 ttwid 字段
   - 不要包含其他Cookie字段
   - 确保UTF-8编码

### 错误：Chrome debug port in use

**症状：**
```
OSError: [Errno 48] Address already in use
```

**解决方案：**

1. **关闭现有Chrome进程**
   ```bash
   # Windows
   taskkill /F /IM chrome.exe

   # Linux/macOS
   pkill -f chrome
   ```

2. **使用不同端口**
   - 修改 `src/backend/chrome_debug_manager.py`
   - 更改端口号（默认9222）

3. **程序自动管理**
   - 新版本会自动检测并提示
   - 无需手动操作

---

## 播放问题

### 错误：No sound output

**症状：**
```
播放完成但没有声音
```

**诊断步骤：**

1. **检查系统音量**
   - 点击系统托盘音量图标
   - 确保没有静音

2. **检查播放器音量**
   - GUI音量滑块是否> 0
   - config.ini中volume值

3. **测试音频播放**
   ```bash
   # 播放测试音频
   python -c "import pygame; pygame.mixer.init(); pygame.mixer.music.load('test.mp3').play()"
   ```

4. **检查音频设备**
   - 控制面板 → 声音 → 播放设备
   - 确保选择了正确的输出设备

### 错误：TTS conversion failed

**症状：**
```
TTSError: 转换失败，超过重试次数
```

**解决方案：**

1. **检查网络连接**
   ```bash
   ping edge-tts-gw.bj.baidubce.com
   ```

2. **检查edge-tts服务**
   - 访问：https://speech.microsoft.com/
   - 测试语音合成功能

3. **使用代理**（如果需要）
   ```bash
   set HTTP_PROXY=你的代理地址
   python main.py <room_id>
   ```

4. **清理缓存重试**
   ```bash
   # 删除缓存
   rm -rf cache/*.mp3
   ```

5. **增加超时时间**
   - 修改 `src/backend/gui_orchestrator.py`
   - 增加 `timeout=10.0` 到 `timeout=20.0`

### 错误：Playback queue stuck

**症状：**
```
播放队列卡住，后续弹幕无法播放
```

**解决方案：**

1. **重启程序**
   - 关闭程序
   - 重新启动

2. **清空播放队列**
   - 点击"断开"按钮
   - 重新连接

3. **检查音频文件**
   ```bash
   # 检查损坏的音频文件
   ls -lh cache/
   ```

---

## 性能问题

### 问题：高CPU占用

**症状：**
- CPU使用率 > 50%
- 电脑风扇噪音大

**优化方法：**

1. **降低轮询频率**（HTTP模式）
   ```python
   # 在config.ini中设置
   [http]
   interval = 5  # 增加间隔到5秒
   ```

2. **启用缓存**
   - 确保 `cache/` 目录可写
   - 相同内容复用缓存

3. **使用黑名单**
   - 过滤不需要的用户
   - 减少TTS和播放次数

4. **禁用日志**
   ```bash
   # 不使用 --debug 参数
   python main.py <room_id> --ws
   ```

### 问题：内存占用持续增长

**症状：**
- 程序运行时间长后内存占用增长
- 最终导致程序崩溃

**解决方案：**

1. **定期清理缓存**
   ```bash
   # 删除旧缓存
   find cache/ -name "*.mp3" -mtime +7 -delete
   ```

2. **导出并清空历史**
   - 定期导出弹幕记录
   - 清空内存中的历史列表

3. **限制历史记录数量**
   - GUI自动管理（最新1000条）
   - 自动删除旧记录

### 问题：TTS转换缓慢

**症状：**
- 每条弹幕延迟 > 5秒
- 严重跟不上弹幕速度

**优化方法：**

1. **使用缓存**
   - 缓存命中率 > 80% 应正常

2. **降低音质**（可接受的话）
   ```python
   # 在config.ini中
   [tts]
   # 部分音色音质更好但更快
   voice = zh-CN-XiaoxiaoNeural
   ```

3. **调整并发设置**
   ```python
   # 增加TTS并发数
   # 在src/backend/danmaku_orchestrator.py中
   ```

---

## 打包问题

### 错误：ModuleNotFoundError when running exe

**症状：**
```
ModuleNotFoundError: No module named 'src.backend.gui_orchestrator'
```

**解决方案：**

1. **检查hiddenimports**
   - 编辑 `build.spec`
   - 确保包含所有src模块
   ```python
   hiddenimports=[
       'src.backend.gui_orchestrator',
       'src.gui.main_window',
       # ... 所有其他模块
   ]
   ```

2. **使用onedir模式**
   - 不使用onefile模式
   - 目录模式更可靠

3. **检查Python路径**
   ```python
   # 在main_gui.py中
   import sys
   print(sys.path)  # 调试输出
   ```

### 错误：Missing resource files

**症状：**
```
FileNotFoundError: resources/styles/dark_theme.qss
```

**解决方案：**

1. **检查datas配置**
   ```python
   # build.spec中
   datas = [
       ('resources/styles', 'resources/styles'),
   ]
   ```

2. **验证dist目录结构**
   ```
   dist/抖音弹幕播报/
   ├── 抖音弹幕播报.exe
   ├── _internal/
   │   └── resources/styles/dark_theme.qss
   ```

3. **修复路径检测**
   ```python
   # 在main_gui.py和main_window.py中
   def get_resource_path(relative_path):
       if getattr(sys, 'frozen', False):
           return Path(sys.executable).parent / "_internal"
       return Path(__file__).parent.parent.parent
   ```

### 错误：exe crashes on startup

**症状：**
- 双击exe立即崩溃
- 无错误提示

**诊断步骤：**

1. **从命令行运行**
   ```bash
   cd dist/抖音弹幕播报
   抖音弹幕播报.exe > output.txt 2>&1
   ```

2. **检查错误输出**
   - 查看output.txt中的堆栈跟踪
   - 确定具体错误位置

3. **在开发环境测试**
   ```bash
   python main_gui.py  # 不打包直接运行
   ```

4. **逐步调试**
   - 添加 `print()` 语句
   - 确定崩溃的代码行

---

## 调试技巧

### 启用详细日志

**方法1：命令行参数**
```bash
python main.py <room_id> --ws --debug
python main_gui.py  # 默认启用INFO日志
```

**方法2：配置文件**
```ini
[logging]
level = DEBUG
```

### 使用Python调试器

```bash
# VS Code
python -m debugpy --listen 5678 main_gui.py

# PyCharm
# 在Run Configuration中添加Python Debug配置
```

### Chrome DevTools集成

1. **启动Chrome调试模式**
   ```bash
   chrome.exe --remote-debugging-port=9222
   ```

2. **打开DevTools**
   - 访问：http://localhost:9222
   - 查看Network标签
   - 监控WebSocket连接

3. **检查注入脚本**
   - 在Console标签查看
   - 查找WebSocket监听代码

### 检查点技巧

**在代码中添加断点：**
```python
import pdb; pdb.set_trace()

# 或使用ipdb（更好的IPython）
import ipdb; ipdb.set_trace()
```

**查看变量值：**
```python
logger.debug(f"变量值: {variable=}")
print(f"调试信息: {some_dict}")
```

### 性能分析

```bash
# 使用cProfile
python -m cProfile -o profile.stats main.py <room_id>
python -m pstats_tools profile.stats

# 使用内存分析
pip install memory_profiler
python -m memory_profiler main.py
```

---

## 获取帮助

如果问题未在此文档中覆盖：

1. **查看日志**
   - GUI日志区域
   - `logs/` 目录下的文件

2. **查看已有Issue**
   - https://github.com/yourusername/yourrepo/issues
   - 搜索类似问题

3. **提交新Issue**
   - 提供详细的错误信息
   - 附带日志文件
   - 说明系统和环境信息

**Issue模板：**
```
**问题描述**
简要描述遇到的问题

**复现步骤**
1.
2.
3.

**期望行为**
应该发生什么

**实际行为**
实际发生了什么

**环境信息**
- OS: Windows 10/11
- Python版本: 3.14.0
- 程序版本: v0.1.0
- Chrome版本: 121.0.6165.144

**日志输出**
```
相关错误信息

---

**最后更新：** 2026-02-11
