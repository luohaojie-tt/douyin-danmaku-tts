# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 收集所有src子模块
src_modules = collect_submodules('src')

a = Analysis(
    ['main_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.ini', '.'),
        ('cookies.txt.example', '.'),
        ('resources/styles/dark_theme.qss', 'resources/styles'),
        # 收集整个src目录
        ('src', 'src'),
    ],
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'edge_tts',
        'websockets',
        'websockets.client',
        'websockets.server',
        'aiohttp',
        'pygame',
        'pygame.mixer',
        'pygame._sdl2',
        'configparser',
        'protobuf',
        'google.protobuf',
        # 主入口模块
        'main',
        # src模块 - 显式导入所有子模块
        'src',
        'src.__init__',
        # backend
        'src.backend',
        'src.backend.__init__',
        'src.backend.chrome_debug_manager',
        'src.backend.gui_config_manager',
        'src.backend.gui_orchestrator',
        'src.backend.signal_handler',
        # config
        'src.config',
        'src.config.__init__',
        'src.config.defaults',
        'src.config.loader',
        # douyin
        'src.douyin',
        'src.douyin.__init__',
        'src.douyin.api',
        'src.douyin.connector',
        'src.douyin.connector_http',
        'src.douyin.connector_real',
        'src.douyin.connector_v2',
        'src.douyin.connector_v3',
        'src.douyin.connector_v4',
        'src.douyin.connector_websocket_listener',
        'src.douyin.cookie',
        'src.douyin.message_parser',
        'src.douyin.parser',
        'src.douyin.parser_http',
        'src.douyin.parser_real',
        'src.douyin.parser_v2',
        'src.douyin.protobuf',
        'src.douyin.websocket_extractor',
        # filter
        'src.filter',
        'src.filter.__init__',
        # gui
        'src.gui',
        'src.gui.__init__',
        'src.gui.control_panel',
        'src.gui.danmaku_widget',
        'src.gui.log_widget',
        'src.gui.main_window',
        'src.gui.settings_dialog',
        'src.gui.status_bar',
        # player
        'src.player',
        'src.player.__init__',
        'src.player.pygame_player',
        # tts
        'src.tts',
        'src.tts.__init__',
        'src.tts.edge_tts',
        # utils
        'src.utils',
        'src.utils.__init__',
    ] + src_modules,  # 添加自动收集的子模块
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'pandas',
        'numpy',
        'scipy',
        'PIL',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='抖音弹幕播报',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # 暂时启用控制台用于调试
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='抖音弹幕播报',
)
