"""Data retrieval module for ai_trader.

Fetches OHLCV data from Bitget Futures API.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd
import requests

from .notifications import NOTIFIER


@dataclass
class Candle:
    """Simple OHLCV candle representation."""

    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class DataHandler:
    """Retrieve market data from Bitget."""

    BASE_URL = "https://api.bitget.com/api/v2"

    def __init__(self, symbol: str, product_type: str = "umcbl") -> None:
        self.symbol = symbol
        self.product_type = product_type
        self.session = requests.Session()
        self.log = logging.getLogger(self.__class__.__name__)

    def fetch_candles(
        self, interval: str = "1m", limit: int = 100
    ) -> pd.DataFrame:
        """Fetch recent candles and return as :class:`pandas.DataFrame`."""
        endpoint = f"{self.BASE_URL}/mix/market/candles"
        params = {
            "symbol": self.symbol,
            "productType": self.product_type,
            "granularity": interval,
            "limit": limit,
        }
        try:
            resp = self.session.get(endpoint, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            self.log.error("HTTP error fetching candles: %s", exc)
            NOTIFIER.notify(
                "data_error",
                f"Failed to fetch candles for {self.symbol}: {exc}",
                level="WARNING",
            )
            return pd.DataFrame(
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )

        candles = [
            Candle(
                timestamp=int(item[0]),
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=float(item[5]),
            )
            for item in data.get("data", [])
        ]
        return pd.DataFrame([c.__dict__ for c in candles])
