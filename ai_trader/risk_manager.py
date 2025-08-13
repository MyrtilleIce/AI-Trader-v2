"""Advanced risk management for automated crypto trading."""

from __future__ import annotations

import datetime as dt
import logging
import os
from dataclasses import dataclass
try:  # pragma: no cover - Python 3.12+ drops distutils
    from distutils.util import strtobool  # type: ignore
except Exception:  # pragma: no cover
    from setuptools._distutils.util import strtobool  # type: ignore
from pathlib import Path
from typing import Dict, Optional, Tuple

import yaml

ENABLE_METRICS_EXPORT = os.getenv("ENABLE_METRICS_EXPORT", "false").lower() == "true"

if ENABLE_METRICS_EXPORT:
    try:
        from prometheus_client import Counter, Gauge
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning("Prometheus client unavailable: %s", exc)
        ENABLE_METRICS_EXPORT = False

if not ENABLE_METRICS_EXPORT:
    class _DummyMetric:
        def inc(self, *args, **kwargs):
            return None

        def set(self, *args, **kwargs):
            return None

    def Counter(*args, **kwargs):  # type: ignore
        return _DummyMetric()

    def Gauge(*args, **kwargs):  # type: ignore
        return _DummyMetric()

from .execution import BitgetExecution
from .notifications import NOTIFIER


@dataclass
class TradeInfo:
    """Information stored for an open trade."""

    risk: float
    sl: float
    tp: float
    trailing: bool = False


class RiskManager:
    """Manage risk, position sizing and daily drawdown limits."""

    CONFIG_PATH = Path(os.getenv("CONFIG_FILE", "config.yaml"))

    def __init__(
        self, executor: BitgetExecution, symbol: str, leverage: int = 10
    ) -> None:
        self.executor = executor
        self.symbol = symbol
        self.leverage = leverage
        self.log = logging.getLogger(self.__class__.__name__)

        config = self._load_config()
        risk_cfg = config.get("risk", {})
        self.risk_per_trade = float(
            os.getenv("RISK_PER_TRADE", risk_cfg.get("risk_per_trade", 0.01))
        )
        self.atr_factor = float(
            os.getenv("ATR_FACTOR", risk_cfg.get("atr_factor", 1.5))
        )
        self.reward_ratio = float(
            os.getenv("REWARD_RATIO", risk_cfg.get("reward_ratio", 2.0))
        )
        self.max_slippage = float(
            os.getenv("MAX_SLIPPAGE", risk_cfg.get("max_slippage", 0.001))
        )
        self.trailing_stop_enabled = bool(
            strtobool(
                os.getenv("TRAILING_STOP", str(risk_cfg.get("trailing_stop", False)))
            )
        )
        self.daily_drawdown_limit = float(
            os.getenv("DAILY_DRAWDOWN_LIMIT", risk_cfg.get("max_drawdown", 0.05))
        )

        self.day = dt.date.today()
        self.start_balance: float = self.get_available_balance()
        self.daily_pnl = 0.0
        self.open_trades: Dict[str, TradeInfo] = {}

        self.metrics = {
            "open_trades": Gauge("ai_trader_open_trades", "Number of open trades"),
            "daily_pnl": Gauge("ai_trader_daily_pnl", "Daily PnL in USDT"),
            "trades_opened": Counter("ai_trader_trades_opened_total", "Trades opened"),
            "trades_closed": Counter("ai_trader_trades_closed_total", "Trades closed"),
        }

    # ------------------------------------------------------------------
    def _load_config(self) -> Dict[str, dict]:
        """Return configuration from ``CONFIG_PATH``."""
        if not self.CONFIG_PATH.exists():
            return {}
        try:
            with self.CONFIG_PATH.open("r", encoding="utf-8") as fh:
                return yaml.safe_load(fh) or {}
        except Exception as exc:  # pylint: disable=broad-except
            self.log.error("Config load failed: %s", exc)
            return {}

    def _reset_daily(self) -> None:
        today = dt.date.today()
        if today != self.day:
            self.day = today
            self.daily_pnl = 0.0
            self.start_balance = self.get_available_balance()
            self.metrics["daily_pnl"].set(0)
            self.log.info("Daily reset. Start balance: %s", self.start_balance)

    # ------------------------------------------------------------------
    def get_available_balance(self) -> float:
        """Return the available balance for ``symbol``."""
        balance = self.executor.available_balance(self.symbol)
        self.log.debug("Fetched balance: %s", balance)
        return balance

    # ------------------------------------------------------------------
    def can_open_new_trade(self) -> bool:
        """Return ``True`` if a new trade can be opened."""
        self._reset_daily()
        allowed = (self.start_balance + self.daily_pnl) > (
            self.start_balance * (1 - self.daily_drawdown_limit)
        )
        if not allowed:
            self.log.warning("Daily drawdown limit reached")
            dd_pct = 0.0
            if self.start_balance:
                dd_pct = abs(self.daily_pnl) / self.start_balance * 100
            NOTIFIER.notify(
                "trading_halt",
                "Automatic trading halted: daily drawdown limit reached",
                level="WARNING",
                drawdown_pct=dd_pct,
            )
        return allowed

    # ------------------------------------------------------------------
    def position_size(
        self, entry_price: float, stop_loss: float | None = None
    ) -> float:
        """Return trade size based on risk percentage and SL distance.

        When ``stop_loss`` is ``None`` a fixed portion of balance is used.
        """
        balance = self.get_available_balance()
        if stop_loss is None:
            trade_amount = balance * self.risk_per_trade * self.leverage
            qty = trade_amount / entry_price
        else:
            risk_amount = balance * self.risk_per_trade
            distance = abs(entry_price - stop_loss)
            if distance == 0:
                return 0.0
            qty = risk_amount / distance
        self.log.debug(
            "Position size: balance=%s entry=%s sl=%s qty=%s",
            balance,
            entry_price,
            stop_loss,
            qty,
        )
        return max(qty, 0.0)

    # ------------------------------------------------------------------
    def compute_sl_tp(
        self, entry_price: float, side: str, atr: float
    ) -> Tuple[float, float]:
        """Return stop loss and take profit based on ATR."""
        direction = 1 if side == "buy" else -1
        sl = entry_price - direction * self.atr_factor * atr
        distance = abs(entry_price - sl)
        tp = entry_price + direction * distance * self.reward_ratio
        return sl, tp

    @staticmethod
    def dynamic_sl_tp(price: float, side: str) -> Tuple[float, float]:
        """Fallback SL/TP calculation based on a fixed percentage."""
        if side == "buy":
            sl = price * 0.99
            tp = price * 1.02
        else:
            sl = price * 1.01
            tp = price * 0.98
        return sl, tp

    # ------------------------------------------------------------------
    def register_trade(
        self, trade_id: str, risk: float, sl: float, tp: float, ts: bool = False
    ) -> None:
        """Store a newly opened trade."""
        self.open_trades[trade_id] = TradeInfo(risk=risk, sl=sl, tp=tp, trailing=ts)
        self.metrics["open_trades"].set(len(self.open_trades))
        self.metrics["trades_opened"].inc()
        if len(self.open_trades) > 5:
            NOTIFIER.notify(
                "over_exposure",
                f"Too many open trades: {len(self.open_trades)}",
                level="WARNING",
            )

    # ------------------------------------------------------------------
    def update_closed_trade(self, trade_id: str, profit_loss: float) -> None:
        """Update metrics when a trade closes."""
        self._reset_daily()
        self.daily_pnl += profit_loss
        self.metrics["daily_pnl"].set(self.daily_pnl)
        self.open_trades.pop(trade_id, None)
        self.metrics["open_trades"].set(len(self.open_trades))
        self.metrics["trades_closed"].inc()
        self.log.info("Trade %s closed PnL=%s", trade_id, profit_loss)
        NOTIFIER.notify(
            "trade_closed",
            f"Trade {trade_id} closed with PnL {profit_loss:.2f}",
            level="INFO",
            pnl=profit_loss,
        )

    # ------------------------------------------------------------------
    def process_daily_reset(self) -> None:
        """Public wrapper for :func:`_reset_daily`."""
        self._reset_daily()

    def check_slippage(self, expected_price: float, actual_price: float) -> bool:
        """Return True if slippage within acceptable bounds."""
        if expected_price == 0:
            return True
        diff = abs(actual_price - expected_price) / expected_price
        allowed = diff <= self.max_slippage
        if not allowed:
            self.log.warning("Slippage %.5f exceeds limit %.5f", diff, self.max_slippage)
        return allowed

    # ------------------------------------------------------------------
    def apply_trailing_stop(self, trade_id: str, price: float) -> Optional[float]:
        """Move stop loss if trade uses trailing stop."""
        info = self.open_trades.get(trade_id)
        if not info or not info.trailing:
            return None
        # TODO: refine trailing stop logic
        return info.sl

    # ------------------------------------------------------------------
    def calculate_position_size_with_leverage(
        self,
        entry_price: float,
        stop_loss_price: float,
        total_balance: float,
        leverage: int = 10,
    ) -> Dict[str, float]:
        """Return position details using 10% capital and given leverage."""

        capital_per_position = total_balance * 0.10
        required_margin = capital_per_position / leverage
        position_size = capital_per_position / entry_price

        max_loss = abs(entry_price - stop_loss_price) * position_size
        max_allowed_loss = total_balance * 0.02

        if max_loss > max_allowed_loss and abs(entry_price - stop_loss_price) > 0:
            position_size = max_allowed_loss / abs(entry_price - stop_loss_price)
            max_loss = max_allowed_loss

        return {
            "position_size": position_size,
            "required_margin": required_margin,
            "max_loss": max_loss,
            "leverage": leverage,
            "capital_allocated": capital_per_position,
        }

    # ------------------------------------------------------------------
    def calculate_liquidation_price(
        self,
        entry_price: float,
        position_size: float,
        margin: float,
        leverage: int,
        side: str = "long",
    ) -> Dict[str, float]:
        """Return liquidation price info for a position."""

        maintenance_margin_rate = 0.004

        if position_size == 0:
            return {
                "liquidation_price": entry_price,
                "distance_percentage": 0.0,
                "is_safe": False,
            }

        if side == "long":
            liquidation_price = entry_price * (
                1 - (margin / position_size - maintenance_margin_rate)
            )
        else:
            liquidation_price = entry_price * (
                1 + (margin / position_size - maintenance_margin_rate)
            )

        distance_to_liquidation = abs(entry_price - liquidation_price) / entry_price

        return {
            "liquidation_price": liquidation_price,
            "distance_percentage": distance_to_liquidation * 100,
            "is_safe": distance_to_liquidation > 0.05,
        }

    # ------------------------------------------------------------------
    def validate_trade_safety(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        position_data: Dict[str, float],
    ) -> Tuple[Dict[str, bool], bool]:
        """Return detailed safety checks for a proposed trade."""

        checks = {
            "liquidation_distance": False,
            "stop_loss_valid": False,
            "risk_ratio_valid": False,
            "margin_sufficient": False,
        }

        liquidation_info = self.calculate_liquidation_price(
            entry_price,
            position_data.get("position_size", 0.0),
            position_data.get("required_margin", 0.0),
            position_data.get("leverage", self.leverage),
        )
        checks["liquidation_distance"] = liquidation_info["is_safe"]

        liquidation_buffer = abs(stop_loss - liquidation_info["liquidation_price"]) / entry_price
        checks["stop_loss_valid"] = liquidation_buffer > 0.15

        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        risk_reward_ratio = reward / risk if risk > 0 else 0
        checks["risk_ratio_valid"] = risk_reward_ratio >= 1.5

        account_balance = self.get_available_balance()
        checks["margin_sufficient"] = position_data.get("required_margin", 0.0) < account_balance * 0.8

        return checks, all(checks.values())
