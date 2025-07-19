"""Risk management utilities."""

from __future__ import annotations

import logging
from typing import Tuple


class RiskManager:
    """Calculate position size and dynamic SL/TP."""

    def __init__(self, balance: float, risk_per_trade: float = 0.01) -> None:
        self.balance = balance
        self.risk_per_trade = risk_per_trade
        self.log = logging.getLogger(self.__class__.__name__)

    def position_size(
        self, price: float, sl_price: float, leverage: int = 10
    ) -> float:
        """Determine position size based on risk percentage."""
        risk_amount = self.balance * self.risk_per_trade
        stop_loss = abs(price - sl_price)
        qty = (risk_amount / stop_loss) * leverage
        self.log.debug(
            "Position size calculated: price=%s sl=%s qty=%s", price, sl_price, qty
        )
        return max(qty, 0)

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

