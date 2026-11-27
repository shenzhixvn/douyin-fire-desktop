@echo off
chcp 65001 >nul
title 抖音自动续火花 - 一键构建脚本

echo ==========================================
echo   抖音自动续火花 - Windows 一键打包脚本
echo ==========================================
echo.

:: [1/7] 选择 Python 解释器
echo [1/7] 检查 Python 环境...
set "PYTHON="
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
if not defined PYTHON (
    where py >nul 2>&1 && set "PYTHON=py"
)
if not defined PYTHON (
    where python >nul 2>&1 && set "PYTHON=python"
)
if not defined PYTHON (
    echo ❌ 未检测到 Python，请先安装 Python 3.11+
    echo    下载地址: https://www.python.org/downloads/
    echo    安装时务必勾选 "Add Python to PATH"
    pause
    exit /b 1
)
%PYTHON% --version
echo ✅ Python 已安装
echo.

:: [2/7] 创建虚拟环境
echo [2/7] 检查虚拟环境...
if exist ".venv\Scripts\python.exe" (
    echo    虚拟环境已存在，跳过创建
) else (
    %PYTHON% -m venv .venv
    if errorlevel 1 (
        echo ❌ 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo ✅ 虚拟环境创建完成
)
set "VPY=.venv\Scripts\python.exe"
echo.

:: [3/7] 安装依赖
echo [3/7] 安装 Python 依赖...
%VPY% -m pip install --upgrade pip -q
%VPY% -m pip install -r requirements.txt -q
%VPY% -m pip install pyinstaller -q
if errorlevel 1 (
    echo ❌ Python 依赖安装失败，请检查网络后重试
    pause
    exit /b 1
)
echo ✅ 依赖安装完成
echo.

:: [4/7] 安装 Playwright Chromium
echo [4/7] 安装 Chromium 浏览器（首次需要下载，约 150MB）...
%VPY% -m playwright install chromium
if errorlevel 1 (
    echo ❌ Chromium 安装失败，请检查网络后重试
    pause
    exit /b 1
)
echo ✅ Chromium 安装完成
echo.

:: [5/7] 清理旧的构建产物
echo [5/7] 清理旧构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo ✅ 清理完成
echo.

:: [6/7] 打包
echo [6/7] 开始打包（可能需要几分钟）...
%VPY% -m PyInstaller douyin-auto-fire.spec --noconfirm
if errorlevel 1 (
    echo ❌ 打包失败，请检查上方错误信息
    pause
    exit /b 1
)
echo ✅ 打包完成
echo.

:: [7/7] 复制 Chromium 到输出目录
echo [7/7] 复制 Chromium 浏览器到输出目录...
set "CHROMIUM_SRC=%LOCALAPPDATA%\ms-playwright"
set "OUTPUT_DIR=dist\抖音自动续火花-桌面"

if exist "%CHROMIUM_SRC%" (
    echo    正在复制 Chromium 文件...
    xcopy "%CHROMIUM_SRC%" "%OUTPUT_DIR%\ms-playwright\" /E /I /Q /Y >nul
    echo ✅ Chromium 已复制到输出目录
) else (
    echo ⚠️ 未找到默认 Chromium 路径，将使用系统默认位置
)

:: 创建配置模板
echo.
echo 创建配置模板...
if not exist "%OUTPUT_DIR%\config.json" (
    copy config.example.json "%OUTPUT_DIR%\config.json" >nul
)

:: 创建 .env 文件
> "%OUTPUT_DIR%\.env" echo # 浏览器配置
>> "%OUTPUT_DIR%\.env" echo HEADLESS=false
>> "%OUTPUT_DIR%\.env" echo # PLAYWRIGHT_BROWSERS_PATH=ms-playwright
>> "%OUTPUT_DIR%\.env" echo.
>> "%OUTPUT_DIR%\.env" echo # 抖音认证（二选一）
>> "%OUTPUT_DIR%\.env" echo # DOUYIN_COOKIE=
>> "%OUTPUT_DIR%\.env" echo # DOUYIN_STORAGE_STATE=storage-state.json

:: 创建使用说明
> "%OUTPUT_DIR%\使用说明.txt" echo 抖音自动续火花 - 使用说明
>> "%OUTPUT_DIR%\使用说明.txt" echo ================================
>> "%OUTPUT_DIR%\使用说明.txt" echo.
>> "%OUTPUT_DIR%\使用说明.txt" echo 1. 双击 "抖音自动续火花-桌面.exe" 启动图形界面
>> "%OUTPUT_DIR%\使用说明.txt" echo.
>> "%OUTPUT_DIR%\使用说明.txt" echo 2. 首次使用请先点击 "📱 扫码登录"
>> "%OUTPUT_DIR%\使用说明.txt" echo    在弹出的浏览器中扫码登录抖音
>> "%OUTPUT_DIR%\使用说明.txt" echo.
>> "%OUTPUT_DIR%\使用说明.txt" echo 3. 在表格中 "➕ 添加好友 / ✏️ 修改表情 / 🗑 删除选中"，再点 "💾 保存配置"
>> "%OUTPUT_DIR%\使用说明.txt" echo.
>> "%OUTPUT_DIR%\使用说明.txt" echo 4. 先运行 "🧪 Dry Run 测试" 确认配置正确
>> "%OUTPUT_DIR%\使用说明.txt" echo.
>> "%OUTPUT_DIR%\使用说明.txt" echo 5. 确认无误后点击 "🚀 正式运行"
>> "%OUTPUT_DIR%\使用说明.txt" echo.
>> "%OUTPUT_DIR%\使用说明.txt" echo 6. 日志和截图保存在 artifacts 文件夹
>> "%OUTPUT_DIR%\使用说明.txt" echo.
>> "%OUTPUT_DIR%\使用说明.txt" echo 注意事项:
>> "%OUTPUT_DIR%\使用说明.txt" echo - storage-state.json 是登录凭证，请勿分享
>> "%OUTPUT_DIR%\使用说明.txt" echo - 登录失效后重新扫码登录即可
>> "%OUTPUT_DIR%\使用说明.txt" echo - 整个文件夹可以拷贝到其他 Windows 电脑使用

echo.
echo ==========================================
echo   ✅ 构建完成！
echo ==========================================
echo.
echo   输出目录: dist\抖音自动续火花-桌面\
echo.
pause
