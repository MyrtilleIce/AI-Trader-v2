"""Enhanced risk management utilities."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Tuple

from .execution import BitgetExecution


class RiskManager:
    """Manage position sizing and daily drawdown limits."""

    def __init__(
        self,
        executor: BitgetExecution,
        symbol: str,
        leverage: int = 10,
        portion: float = 0.1,
        max_drawdown: float = 0.02,
    ) -> None:
        self.executor = executor
        self.symbol = symbol
        self.leverage = leverage
        self.portion = portion
        self.max_drawdown = max_drawdown
        self.daily_pnl = 0.0
        self.day = dt.date.today()
        self.log = logging.getLogger(self.__class__.__name__)

    def _reset_daily(self) -> None:
        today = dt.date.today()
        if today != self.day:
            self.day = today
            self.daily_pnl = 0.0

    def update_pnl(self, pnl: float) -> None:
        self._reset_daily()
        self.daily_pnl += pnl

    def allowed(self) -> bool:
        self._reset_daily()
        if self.daily_pnl <= -self.max_drawdown:
            self.log.warning("Daily drawdown limit reached")
            return False
        return True

    def get_available_balance(self) -> float:
        balance = self.executor.available_balance(self.symbol)
        self.log.debug("Fetched balance: %s", balance)
        return balance

    def position_size(self, price: float) -> float:
        balance = self.get_available_balance()
        trade_amount = balance * self.portion
        qty = (trade_amount * self.leverage) / price
        return max(qty, 0.0)

    @staticmethod
    def dynamic_sl_tp(price: float, side: str) -> Tuple[float, float]:
        if side == "buy":
            sl = price * 0.99
            tp = price * 1.02
        else:
            sl = price * 1.01
            tp = price * 0.98
        return sl, tp
