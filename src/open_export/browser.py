"""Connect to a running Chrome instance via CDP and make authenticated API calls."""

from __future__ import annotations

import logging
from types import TracebackType
from typing import Any, Optional

from playwright.async_api import Browser, Page, async_playwright

logger = logging.getLogger(__name__)

CHATGPT_ORIGIN = "https://chatgpt.com"
DEFAULT_CDP_URL = "http://localhost:9222"


class ChatGPTBrowser:
    """Async context manager that connects to a running Chrome via CDP.

    The user must start Chrome with:
        chrome.exe --remote-debugging-port=9222

    Then log into chatgpt.com before running the CLI tool.

    Usage::

        async with ChatGPTBrowser() as browser:
            data = await browser.api_get("/backend-api/conversations?offset=0&limit=100")
    """

    def __init__(self, cdp_url: str = DEFAULT_CDP_URL) -> None:
        self.cdp_url = cdp_url
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._access_token: Optional[str] = None
        self._token_refreshed: bool = False

    async def __aenter__(self) -> ChatGPTBrowser:
        self._playwright = await async_playwright().start()
        try:
            self._browser = await self._playwright.chromium.connect_over_cdp(self.cdp_url)
        except Exception as e:
            await self._playwright.stop()
            raise ConnectionError(
                f"Could not connect to Chrome at {self.cdp_url}. "
                f"Make sure Chrome is running with --remote-debugging-port=9222. "
                f"Error: {e}"
            ) from e

        self._page = await self._find_chatgpt_page()
        logger.info("Connected to Chrome via CDP at %s", self.cdp_url)
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        # Clear sensitive credentials from memory
        self._access_token = None
        self._token_refreshed = False
        # Disconnect CDP without closing the user's Chrome
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Disconnected from Chrome CDP.")

    async def _find_chatgpt_page(self) -> Page:
        """Find an existing browser tab open to chatgpt.com."""
        for context in self._browser.contexts:
            for page in context.pages:
                if page.url.startswith(CHATGPT_ORIGIN):
                    logger.info("Found existing ChatGPT tab: %s", page.url)
                    return page

        # No ChatGPT tab found -- use the first page and navigate
        all_pages = []
        for context in self._browser.contexts:
            all_pages.extend(context.pages)

        if not all_pages:
            raise RuntimeError("No browser pages found. Open at least one tab in Chrome.")

        page = all_pages[0]
        logger.info("No ChatGPT tab found. Navigating to chatgpt.com...")
        await page.goto(CHATGPT_ORIGIN, wait_until="domcontentloaded", timeout=30_000)
        return page

    async def _get_access_token(self) -> str:
        """Extract the access token from ChatGPT's session endpoint."""
        logger.debug("Fetching access token from /api/auth/session...")
        result = await self._page.evaluate(
            """async () => {
                const response = await fetch('/api/auth/session', {
                    credentials: 'include',
                });
                if (!response.ok) {
                    return { __error: true, status: response.status };
                }
                const data = await response.json();
                return data.accessToken || null;
            }"""
        )
        if isinstance(result, dict) and result.get("__error"):
            raise RuntimeError(
                f"Failed to get access token: HTTP {result['status']}. "
                "Make sure you are logged into ChatGPT."
            )
        if not result:
            raise RuntimeError(
                "No access token found. Make sure you are logged into ChatGPT."
            )
        logger.debug("Access token obtained.")
        return result

    async def api_get(self, path: str) -> dict[str, Any]:
        """Execute an authenticated GET request to ChatGPT's backend API.

        Uses page.evaluate() to run fetch() inside the browser context,
        with the Authorization bearer token from the session.
        """
        if self._access_token is None:
            self._access_token = await self._get_access_token()

        url = f"{CHATGPT_ORIGIN}{path}"
        logger.debug("API GET: %s", url)

        result = await self._page.evaluate(
            """async ([url, token]) => {
                const response = await fetch(url, {
                    method: 'GET',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token,
                    },
                });
                if (!response.ok) {
                    return {
                        __error: true,
                        status: response.status,
                        statusText: response.statusText,
                        body: await response.text(),
                    };
                }
                return await response.json();
            }""",
            [url, self._access_token],
        )

        if isinstance(result, dict) and result.get("__error"):
            status = result["status"]
            status_text = result["statusText"]
            body_preview = result.get("body", "")[:200]

            # If 401/403, try refreshing the token once
            if status in (401, 403) and not self._token_refreshed:
                logger.info("Got %d, refreshing access token...", status)
                self._token_refreshed = True
                self._access_token = await self._get_access_token()
                return await self.api_get(path)

            raise RuntimeError(
                f"API request failed: {status} {status_text} - {body_preview}"
            )

        return result
