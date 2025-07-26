"""Simple backtesting framework for strategies."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import pandas as pd

from .strategy import EnhancedStrategy


@dataclass
class TradeResult:
    entry_time: datetime
    exit_time: datetime
    side: str
    entry_price: float
    exit_price: float
    pnl: float


class Backtester:
    """Backtest trading strategies on historical data."""

    def __init__(self, df: pd.DataFrame, strategy: Optional[EnhancedStrategy] = None, initial_capital: float = 1000.0) -> None:
        self.df = df
        self.strategy = strategy or EnhancedStrategy()
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.trades: List[TradeResult] = []
        self.log = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    def run(self) -> None:
        df = self.strategy.calculate_indicators(self.df)
        position = None
        entry_price = 0.0
        entry_time = None
        for i in range(2, len(df)):
            window = df.iloc[: i + 1]
            signal = self.strategy.confluence_score(window)
            price = df.iloc[i]["close"]
            ts = df.index[i]
            if not position and signal["action"] in {"buy", "sell"}:
                position = signal["action"]
                entry_price = price
                entry_time = ts
            elif position == "buy" and signal["action"] == "sell":
                pnl = price - entry_price
                self.current_capital += pnl
                self.trades.append(
                    TradeResult(entry_time, ts, "buy", entry_price, price, pnl)
                )
                position = None
            elif position == "sell" and signal["action"] == "buy":
                pnl = entry_price - price
                self.current_capital += pnl
                self.trades.append(
                    TradeResult(entry_time, ts, "sell", entry_price, price, pnl)
                )
                position = None
        if position:
            pnl = (df.iloc[-1]["close"] - entry_price) if position == "buy" else (entry_price - df.iloc[-1]["close"])
            self.current_capital += pnl
            self.trades.append(
                TradeResult(entry_time, df.index[-1], position, entry_price, df.iloc[-1]["close"], pnl)
            )

    # ------------------------------------------------------------------
    def summary(self) -> dict:
        total_pnl = sum(t.pnl for t in self.trades)
        win_trades = [t for t in self.trades if t.pnl > 0]
        loss_trades = [t for t in self.trades if t.pnl <= 0]
        win_rate = (len(win_trades) / len(self.trades)) * 100 if self.trades else 0
        return {
            "trades": len(self.trades),
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "final_capital": round(self.current_capital, 2),
        }
