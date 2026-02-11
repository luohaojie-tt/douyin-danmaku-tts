@echo off
chcp 65001 >nul
echo ====================================
echo   抖音弹幕语音播报工具 - 打包脚本
echo ====================================
echo.

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python环境
    pause
    exit /b 1
)

REM 安装PyInstaller
echo [1/5] 检查PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo 正在安装PyInstaller...
    pip install pyinstaller==6.18.0
)

REM 清理旧的构建文件
echo [2/5] 清理旧的构建文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

REM 执行打包
echo [3/5] 开始打包...
pyinstaller build.spec

if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

REM 复制必要文件到dist目录
echo [4/5] 复制配置文件...
if exist "config.ini" copy /y "config.ini" "dist\config.ini" >nul
if exist "cookies.txt.example" copy /y "cookies.txt.example" "dist\cookies.txt.example" >nul

REM 验证并复制资源文件
if not exist "dist\resources\styles" mkdir "dist\resources\styles"
if exist "resources\styles\dark_theme.qss" copy /y "resources\styles\dark_theme.qss" "dist\resources\styles\dark_theme.qss" >nul

REM 创建必要的目录结构
echo [5/5] 创建目录结构...
if not exist "dist\cache" mkdir "dist\cache"
if not exist "dist\logs" mkdir "dist\logs"

echo.
echo ====================================
echo   打包完成！
echo ====================================
echo.
echo 可执行文件位置: dist\抖音弹幕播报.exe
echo.
pause
