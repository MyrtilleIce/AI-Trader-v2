"""Enhanced trading strategy with multi-indicator confluence."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Optional

import numpy as np
import pandas as pd
import pandas_ta as ta


class EnhancedStrategy:
    """Generate trade signals based on a confluence of indicators."""

    def __init__(self, config: Optional[Dict[str, any]] = None) -> None:
        self.log = logging.getLogger(self.__class__.__name__)
        self.indicators = {
            "ema_short": 12,
            "ema_long": 26,
            "ema_trend": 50,
            "rsi_period": 14,
            "bb_period": 20,
            "atr_period": 14,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_sma": 20,
        }
        self.session_multipliers = {
            "asian": 0.8,
            "european": 1.2,
            "american": 1.5,
        }
        if config:
            self.indicators.update(config.get("indicators", {}))
            self.session_multipliers.update(config.get("session_multipliers", {}))
        self.confluence_threshold = config.get("confluence_threshold", 0.75) if config else 0.75

    # ------------------------------------------------------------------
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return dataframe with all indicators applied."""
        df = df.copy()
        df["ema_12"] = ta.ema(df["close"], length=self.indicators["ema_short"])
        df["ema_26"] = ta.ema(df["close"], length=self.indicators["ema_long"])
        df["ema_50"] = ta.ema(df["close"], length=self.indicators["ema_trend"])

        df["rsi"] = ta.rsi(df["close"], length=self.indicators["rsi_period"])

        macd = ta.macd(
            df["close"],
            fast=self.indicators["macd_fast"],
            slow=self.indicators["macd_slow"],
            signal=self.indicators["macd_signal"],
        )
        df["macd"] = macd["MACD_12_26_9"]
        df["macd_signal"] = macd["MACDs_12_26_9"]
        df["macd_hist"] = macd["MACDh_12_26_9"]

        bb = ta.bbands(df["close"], length=self.indicators["bb_period"])
        df["bb_upper"] = bb["BBU_20_2.0"]
        df["bb_middle"] = bb["BBM_20_2.0"]
        df["bb_lower"] = bb["BBL_20_2.0"]
        df["bb_squeeze"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]

        df["atr"] = ta.atr(
            df["high"], df["low"], df["close"], length=self.indicators["atr_period"]
        )

        df["volume_sma"] = df["volume"].rolling(self.indicators["volume_sma"]).mean()
        df["vwap"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()
        return df

    # ------------------------------------------------------------------
    def _get_session_multiplier(self, ts: datetime) -> float:
        hour = ts.hour
        if 0 <= hour < 8:
            return self.session_multipliers.get("asian", 1)
        if 8 <= hour < 15:
            return self.session_multipliers.get("european", 1)
        return self.session_multipliers.get("american", 1)

    # ------------------------------------------------------------------
    def confluence_score(self, df: pd.DataFrame) -> Dict[str, any]:
        """Return action suggestion with confidence score."""
        if len(df) < 2:
            return {"action": None, "confidence": 0.0}

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        signals = []

        # Trend based on EMAs
        if latest["ema_12"] > latest["ema_26"] > latest["ema_50"]:
            signals.append(0.3)
        elif latest["ema_12"] > latest["ema_26"]:
            signals.append(0.15)
        elif latest["ema_12"] < latest["ema_26"]:
            signals.append(-0.15)

        # RSI momentum
        if latest["rsi"] < 30:
            signals.append(0.25)
        elif latest["rsi"] > 70:
            signals.append(-0.25)

        # MACD
        if latest["macd"] > latest["macd_signal"] and prev["macd"] <= prev["macd_signal"]:
            signals.append(0.2)
        elif latest["macd"] < latest["macd_signal"] and prev["macd"] >= prev["macd_signal"]:
            signals.append(-0.2)

        # Bollinger position
        if latest["close"] < latest["bb_lower"] * 1.01:
            signals.append(0.15)
        elif latest["close"] > latest["bb_upper"] * 0.99:
            signals.append(-0.15)

        # Volume confirmation
        if latest["volume"] > latest["volume_sma"] * 1.2:
            signals.append(0.1)

        confluence = np.clip(sum(signals), -1, 1)
        multiplier = self._get_session_multiplier(datetime.utcnow())
        final_score = confluence * multiplier

        if final_score > self.confluence_threshold:
            return {"action": "buy", "confidence": float(final_score)}
        if final_score < -self.confluence_threshold:
            return {"action": "sell", "confidence": float(abs(final_score))}
        return {"action": None, "confidence": float(final_score)}
