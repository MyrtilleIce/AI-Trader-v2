"""Trading decision logic using indicator confluence."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from .risk_manager import RiskManager
from .ta_engine import TAEngine


@dataclass
class TradeSignal:
    """Container for trade signal information."""

    side: str
    size: float
    sl: float
    tp: float
    score: float


class DecisionEngine:
    """Generate trading decisions based on technical analysis."""

    def __init__(
        self, ta_engine: TAEngine, risk: RiskManager, threshold: float = 0.3
    ) -> None:
        self.ta_engine = ta_engine
        self.risk = risk
        self.threshold = threshold
        self.log = logging.getLogger(self.__class__.__name__)

    def evaluate(self, df: pd.DataFrame) -> Optional[TradeSignal]:
        df = self.ta_engine.apply_indicators(df)
        score = self.ta_engine.confluence_score(df)
        if score is None:
            return None
        price = float(df.iloc[-1]["close"])
        if score > self.threshold:
            sl, tp = self.risk.dynamic_sl_tp(price, "buy")
            size = self.risk.position_size(price)
            return TradeSignal("buy", size, sl, tp, score)
        if score < -self.threshold:
            sl, tp = self.risk.dynamic_sl_tp(price, "sell")
            size = self.risk.position_size(price)
            return TradeSignal("sell", size, sl, tp, score)
        return None
