# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 - 抖音自动续火花
构建命令: pyinstaller douyin-auto-fire.spec
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 收集 Playwright 的数据文件
playwright_data = collect_data_files("playwright")

# 收集 Playwright 的子模块
playwright_hidden = collect_submodules("playwright")

a = Analysis(
    ["gui.py"],
    pathex=[],
    binaries=[],
    datas=[
        # 包含配置模板
        ("config.example.json", "."),
        ("app", "app"),
        ("scripts", "scripts"),
    ] + playwright_data,
    hiddenimports=[
        "panel_store",
        "playwright",
        "playwright.async_api",
        "playwright.sync_api",
        "dotenv",
    ] + playwright_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块，减小体积
        "pytest",
        "unittest",
        "test",
        "tests",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="抖音自动续火花",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI 程序，不显示控制台窗口
    icon=None,  # 可以换成 .ico 文件路径
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="抖音自动续火花",
)
