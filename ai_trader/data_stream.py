"""Asynchronous market data streaming from Bitget."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

import websockets

PUBLIC_WS_URL = "wss://ws.bitget.com/v2/stream"


class DataStream:
    """Subscribe to public WebSocket and push data into a queue."""

    def __init__(self, symbol: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self.symbol = symbol
        self.queue = queue
        self.log = logging.getLogger(self.__class__.__name__)

    async def _subscribe(self, ws: websockets.WebSocketClientProtocol) -> None:
        msg = {
            "op": "subscribe",
            "args": [
                {
                    "instType": "mc",
                    "channel": "ticker",
                    "instId": self.symbol,
                }
            ],
        }
        await ws.send(json.dumps(msg))

    async def stream(self) -> AsyncIterator[dict[str, Any]]:
        """Yield ticker updates indefinitely."""
        while True:
            try:
                async with websockets.connect(PUBLIC_WS_URL, ping_interval=20) as ws:
                    await self._subscribe(ws)
                    async for message in ws:
                        data = json.loads(message)
                        await self.queue.put(data)
                        yield data
            except Exception as exc:  # noqa: BLE001
                self.log.error("Stream error: %s", exc)
                await asyncio.sleep(5)
