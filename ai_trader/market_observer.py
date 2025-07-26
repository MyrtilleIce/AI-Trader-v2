"""Market sentiment observer (Fear & Greed, dominance, funding)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

import aiohttp


class MarketObserver:
    """Fetch and cache market sentiment metrics asynchronously."""

    def __init__(self) -> None:
        self.log = logging.getLogger(self.__class__.__name__)
        self.session = aiohttp.ClientSession()
        self.cache: dict[str, dict] = {}
        self.update_interval = 300

    async def _fetch_fear_greed(self) -> Optional[dict]:
        url = "https://api.alternative.me/fng/"
        try:
            async with self.session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("data"):
                        item = data["data"][0]
                        return {
                            "value": int(item["value"]),
                            "classification": item["value_classification"],
                            "timestamp": item["timestamp"],
                        }
        except Exception as exc:  # noqa: BLE001
            self.log.error("Fear & Greed fetch error: %s", exc)
        return None

    async def _fetch_btc_dominance(self) -> Optional[dict]:
        url = "https://api.coingecko.com/api/v3/global"
        try:
            async with self.session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    dom = data.get("data", {}).get("market_cap_percentage", {}).get("btc", 0)
                    return {"value": round(dom, 2), "timestamp": datetime.utcnow().isoformat()}
        except Exception as exc:  # noqa: BLE001
            self.log.error("Dominance fetch error: %s", exc)
        return None

    async def _fetch_funding_rate(self) -> Optional[dict]:
        url = "https://api.bitget.com/api/v2/mix/market/funding-time?symbol=BTCUSDT&productType=umcbl"
        try:
            async with self.session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    fr = float(data.get("data", {}).get("fundingRate", 0))
                    return {
                        "current_rate": fr,
                        "next_funding_time": data.get("data", {}).get("nextFundingTime"),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
        except Exception as exc:  # noqa: BLE001
            self.log.error("Funding rate fetch error: %s", exc)
        return None

    async def update(self) -> None:
        """Fetch all metrics and cache them."""
        fg, dom, fr = await asyncio.gather(
            self._fetch_fear_greed(), self._fetch_btc_dominance(), self._fetch_funding_rate()
        )
        if fg:
            self.cache["fear_greed"] = fg
        if dom:
            self.cache["btc_dominance"] = dom
        if fr:
            self.cache["funding_rate"] = fr
        self.cache["last_update"] = datetime.utcnow().isoformat()

    async def run(self) -> None:
        while True:
            await self.update()
            await asyncio.sleep(self.update_interval)

    def get_cached_sentiment(self) -> dict:
        return self.cache
