"""Service that fetches and caches free VLESS subscriptions from zieng2."""

import asyncio
import logging
import random
from typing import Optional, List

import aiohttp

log = logging.getLogger(__name__)

FEED_URL = "https://raw.githubusercontent.com/zieng2/wl/refs/heads/main/vless_lite.txt"
REFRESH_INTERVAL = 3600  # 1 hour


class FreeSubService:
    def __init__(self):
        self._links: List[str] = []
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        await self._fetch()
        self._task = asyncio.create_task(self._loop())
        log.info("FreeSubService started, %d links loaded", len(self._links))

    async def stop(self):
        if self._task:
            self._task.cancel()
            self._task = None

    def get_random_link(self) -> Optional[str]:
        if not self._links:
            return None
        return random.choice(self._links)

    @property
    def count(self) -> int:
        return len(self._links)

    async def _fetch(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(FEED_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        log.warning("Failed to fetch free subs: HTTP %d", resp.status)
                        return
                    text = await resp.text()
            links = [
                line.strip() for line in text.splitlines()
                if line.strip() and line.strip().startswith("vless://")
            ]
            if links:
                self._links = links
                log.info("Fetched %d free VLESS links", len(links))
            else:
                log.warning("No valid VLESS links found in feed")
        except Exception:
            log.exception("Error fetching free subs")

    async def _loop(self):
        while True:
            await asyncio.sleep(REFRESH_INTERVAL)
            await self._fetch()
