"""Technical analysis indicator computations."""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
import pandas_ta as ta


class TAEngine:
    """Compute indicators and confluence scores."""

    def __init__(self) -> None:
        self.log = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def apply_indicators(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["ema20"] = ta.ema(df["close"], length=20)
        df["ema50"] = ta.ema(df["close"], length=50)
        df["rsi14"] = ta.rsi(df["close"], length=14)
        macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
        df = df.join(macd)
        bbands = ta.bbands(df["close"], length=20)
        df = df.join(bbands)
        df["vwap"] = ta.vwap(df["high"], df["low"], df["close"], df["volume"])
        return df

    @staticmethod
    def confluence_score(df: pd.DataFrame) -> Optional[float]:
        if df.empty:
            return None
        row = df.iloc[-1]
        score = 0.0
        if row["close"] > row["ema20"]:
            score += 0.2
        if row["ema20"] > row["ema50"]:
            score += 0.2
        if row["MACD_12_26_9"] > row["MACDs_12_26_9"]:
            score += 0.2
        if row["rsi14"] > 50:
            score += 0.2
        if row["close"] > row["BBL_20_2.0"] and row["close"] < row["BBU_20_2.0"]:
            score += 0.2
        return max(min(score, 1.0), -1.0)
