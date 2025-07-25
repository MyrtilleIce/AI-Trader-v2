"""Trading strategy implementation for ai_trader."""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
from ta.momentum import RSIIndicator

from .notifications import NOTIFIER


class Strategy:
    """Compute technical indicators and generate trade signals."""

    def __init__(self) -> None:
        self.log = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def apply_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Add MA20, MA50 and RSI14 columns to dataframe."""
        df = df.copy()
        df["ma20"] = df["close"].rolling(window=20).mean()
        df["ma50"] = df["close"].rolling(window=50).mean()
        rsi = RSIIndicator(close=df["close"], window=14)
        df["rsi14"] = rsi.rsi()
        return df

    def generate_signal(self, df: pd.DataFrame) -> Optional[str]:
        """Return 'buy', 'sell' or None based on MA crossover and RSI."""
        if df.empty:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else df.iloc[-1]

        # MA cross strategy with RSI filter
        if (
            prev["ma20"] <= prev["ma50"]
            and latest["ma20"] > latest["ma50"]
            and latest["rsi14"] < 70
        ):
            self.log.info("Bullish crossover detected")
            NOTIFIER.notify(
                "indicator_ma_cross",
                "Bullish MA20/MA50 crossover with RSI < 70",
                level="INFO",
            )
            return "buy"
        if (
            prev["ma20"] >= prev["ma50"]
            and latest["ma20"] < latest["ma50"]
            and latest["rsi14"] > 30
        ):
            self.log.info("Bearish crossover detected")
            NOTIFIER.notify(
                "indicator_ma_cross",
                "Bearish MA20/MA50 crossover with RSI > 30",
                level="INFO",
            )
            return "sell"
        return None
