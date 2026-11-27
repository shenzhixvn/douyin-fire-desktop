"""扫码登录：打开浏览器轮询登录态，成功后保存 storage-state.json。

被桌面面板（进程内调用）与命令行脚本 scripts/login_auto.py 共用。
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

DOUYIN_URL = "https://www.douyin.com/"
TIMEOUT_SECONDS = 180
POLL_INTERVAL = 2


async def _open_login(page) -> None:
    login = page.get_by_text("登录", exact=True)
    if await login.count():
        try:
            await login.first.click(timeout=10_000)
        except Exception:
            pass

    qr_login = page.get_by_text("扫码登录", exact=True)
    if await qr_login.count():
        try:
            await qr_login.first.click(timeout=5_000)
        except Exception:
            pass


async def _is_logged_in(page) -> bool:
    login = page.get_by_text("登录", exact=True)
    if not await login.count():
        return True
    try:
        return not await login.first.is_visible()
    except Exception:
        return False


async def login() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(locale="zh-CN")
        page = await context.new_page()
        await page.goto(DOUYIN_URL, wait_until="domcontentloaded")
        await _open_login(page)

        waited = 0
        logged_in = False
        while waited < TIMEOUT_SECONDS:
            await asyncio.sleep(POLL_INTERVAL)
            waited += POLL_INTERVAL
            if await _is_logged_in(page):
                logged_in = True
                break

        if not logged_in:
            await browser.close()
            raise RuntimeError("登录超时：未检测到扫码成功，请重新运行。")

        await page.goto(DOUYIN_URL, wait_until="domcontentloaded")
        if not await _is_logged_in(page):
            await browser.close()
            raise RuntimeError("未检测到登录成功，请重新扫码。")

        await context.storage_state(path="storage-state.json.tmp")
        await browser.close()
        Path("storage-state.json.tmp").replace("storage-state.json")
