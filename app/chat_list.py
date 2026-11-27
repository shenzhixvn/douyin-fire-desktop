"""读取私信会话列表（好友 / 群聊昵称），供桌面面板勾选批量加入。"""
from __future__ import annotations

from app.browser import open_douyin, open_private_messages
from app.config import load_settings

CONVERSATION_ROWS = (
    '[data-e2e="conversation-item"]',
    '[class*="conversationConversationItem"]',
    '[class*="conversation-item"]',
    '[class*="ConversationItem"]',
)

CONVERSATION_TITLES = (
    '[class*="conversationConversationItemtitle"]',
    '[class*="ConversationItemtitle"]',
    '[class*="ConversationItemTitle"]',
    '[class*="conversation-item-title"]',
)


async def list_conversations(timeout_ms: int = 15_000) -> list[str]:
    """打开私信页，提取左侧会话列表中的昵称，去重后按顺序返回。"""
    settings = load_settings(None)
    async with open_douyin(settings) as session:
        page = session.page
        await open_private_messages(page, timeout_ms=timeout_ms)
        await page.wait_for_timeout(1_500)

        names: list[str] = []
        for row_sel in CONVERSATION_ROWS:
            rows = page.locator(row_sel)
            count = await rows.count()
            if count == 0:
                continue
            for i in range(count):
                row = rows.nth(i)
                for title_sel in CONVERSATION_TITLES:
                    node = row.locator(title_sel).first
                    if await node.count() == 0:
                        continue
                    try:
                        text = (await node.inner_text(timeout=500)).strip()
                    except Exception:
                        text = ""
                    if text:
                        names.append(text)
                    break
            if names:
                break

        seen: set[str] = set()
        out: list[str] = []
        for name in names:
            if name not in seen:
                seen.add(name)
                out.append(name)
        return out
