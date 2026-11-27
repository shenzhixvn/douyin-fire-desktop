"""非交互扫码登录命令行入口（供源码方式运行）。

打包后的桌面面板直接调用 app.login.login()，不经过本脚本。
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.login import login  # noqa: E402


if __name__ == "__main__":
    asyncio.run(login())
