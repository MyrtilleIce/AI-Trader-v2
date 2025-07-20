"""Risk management utilities."""

from __future__ import annotations

import logging
from typing import Tuple

from .execution import BitgetExecution


class RiskManager:
    """Calculate position size based on account balance and manage SL/TP."""

    def __init__(
        self,
        executor: BitgetExecution,
        symbol: str,
        leverage: int = 10,
        portion: float = 0.1,
    ) -> None:
        self.executor = executor
        self.symbol = symbol
        self.leverage = leverage
        self.portion = portion
        self.log = logging.getLogger(self.__class__.__name__)

    def get_available_balance(self) -> float:
        """Fetch available USDT balance for the configured symbol."""
        balance = self.executor.available_balance(self.symbol)
        self.log.debug("Fetched balance: %s", balance)
        return balance

    def position_size(self, price: float) -> float:
        """Calculate size using a portion of the available balance."""
        balance = self.get_available_balance()
        trade_amount = balance * self.portion
        qty = (trade_amount * self.leverage) / price
        self.log.debug(
            "Position size calculated: price=%s portion=%s qty=%s",
            price,
            self.portion,
            qty,
        )
        return max(qty, 0.0)

    @staticmethod
    def dynamic_sl_tp(price: float, side: str) -> Tuple[float, float]:
        """Simple SL/TP calculation based on side and price."""
        if side == "buy":
            sl = price * 0.99
            tp = price * 1.02
        else:
            sl = price * 1.01
            tp = price * 0.98
        return sl, tp

