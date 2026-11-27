@echo off
chcp 65001 >nul
title 抖音自动续火花

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 选择 Python 解释器：优先项目虚拟环境，其次 py 启动器，最后 PATH 中的 python
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    where py >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON=py"
    ) else (
        set "PYTHON=python"
    )
)

:: 检查 Python 是否可用
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到可用的 Python，请先安装 Python 3.11+ 并勾选 Add Python to PATH。
    pause
    exit /b 1
)

:: 首次运行检测：检查依赖是否安装
%PYTHON% -c "import playwright, dotenv, tzdata" >nul 2>&1
if errorlevel 1 (
    echo 首次运行，正在安装依赖...
    %PYTHON% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请检查网络后重试。
        pause
        exit /b 1
    )
    %PYTHON% -m playwright install chromium
)

:: 启动 GUI
%PYTHON% gui.py
pause
