"""Simple Bitget WebSocket client with auto reconnect."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator, Iterable

import websockets


class BitgetWebSocket:
    """Receive real time market data from Bitget."""

    def __init__(self, symbol: str, channels: Iterable[str], url: str = "wss://ws.bitget.com/v2/ws/public") -> None:
        self.symbol = symbol
        self.channels = list(channels)
        self.url = url
        self.log = logging.getLogger(self.__class__.__name__)
        self.reconnect_interval = 5
        self._active = False

    async def _subscribe(self, ws: websockets.WebSocketClientProtocol) -> None:
        for ch in self.channels:
            msg = {
                "op": "subscribe",
                "args": [{"instType": "mc", "channel": ch, "instId": self.symbol}],
            }
            await ws.send(json.dumps(msg))

    async def connect(self) -> AsyncIterator[dict]:
        """Yield messages from the websocket with reconnect logic."""
        self._active = True
        while self._active:
            try:
                async with websockets.connect(self.url, ping_interval=20) as ws:
                    await self._subscribe(ws)
                    async for message in ws:
                        yield json.loads(message)
            except Exception as exc:  # noqa: BLE001
                self.log.error("WebSocket error: %s", exc)
                await asyncio.sleep(self.reconnect_interval)

    def stop(self) -> None:
        self._active = False
