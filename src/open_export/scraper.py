"""Fetch all ChatGPT conversations with pagination and rate limiting."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from open_export.browser import ChatGPTBrowser

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 100
DEFAULT_DELAY = 1.0


@dataclass
class ConversationSummary:
    """Lightweight summary from the conversation list endpoint."""

    id: str
    title: str
    create_time: float
    update_time: float


@dataclass
class DownloadResult:
    """Result of downloading all conversations."""

    conversations: list[dict[str, Any]] = field(default_factory=list)
    failed: list[tuple[str, str, str]] = field(default_factory=list)  # (id, title, error)
    total_listed: int = 0


async def fetch_conversation_list(
    browser: ChatGPTBrowser,
    *,
    page_size: int = DEFAULT_PAGE_SIZE,
    delay: float = DEFAULT_DELAY,
) -> list[ConversationSummary]:
    """Fetch the complete list of conversations with pagination."""
    all_conversations: list[ConversationSummary] = []
    offset = 0

    while True:
        path = f"/backend-api/conversations?offset={offset}&limit={page_size}"
        data = await browser.api_get(path)

        items = data.get("items", [])
        total = data.get("total", 0)

        for item in items:
            summary = ConversationSummary(
                id=item["id"],
                title=item.get("title", "Untitled"),
                create_time=item.get("create_time", 0),
                update_time=item.get("update_time", 0),
            )
            all_conversations.append(summary)

        logger.info(
            "Fetched conversations %d-%d of %d",
            offset + 1,
            offset + len(items),
            total,
        )

        offset += len(items)

        if offset >= total or not items:
            break

        await asyncio.sleep(delay)

    return all_conversations


async def fetch_conversation_detail(
    browser: ChatGPTBrowser,
    conversation_id: str,
) -> dict[str, Any]:
    """Fetch the full detail of a single conversation."""
    path = f"/backend-api/conversation/{conversation_id}"
    return await browser.api_get(path)


async def fetch_all_conversations(
    browser: ChatGPTBrowser,
    *,
    page_size: int = DEFAULT_PAGE_SIZE,
    delay: float = DEFAULT_DELAY,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> DownloadResult:
    """Fetch the list of all conversations, then download each one's full data.

    Args:
        browser: Connected ChatGPTBrowser instance.
        page_size: Number of conversations per page in listing.
        delay: Seconds to wait between individual conversation fetches.
        on_progress: Optional callback called as on_progress(current, total, title)
            after each conversation is fetched (or fails).
    """
    summaries = await fetch_conversation_list(
        browser, page_size=page_size, delay=delay
    )
    total = len(summaries)
    logger.info("Found %d conversations total.", total)

    result = DownloadResult(total_listed=total)

    for i, summary in enumerate(summaries):
        if on_progress:
            on_progress(i + 1, total, summary.title)

        try:
            detail = await fetch_conversation_detail(browser, summary.id)
            result.conversations.append(detail)
        except Exception as e:
            error_msg = str(e)[:200]
            logger.warning(
                "Failed to fetch conversation '%s' (%s): %s",
                summary.title,
                summary.id,
                error_msg,
            )
            result.failed.append((summary.id, summary.title, error_msg))

        if i < total - 1:
            await asyncio.sleep(delay)

    return result
