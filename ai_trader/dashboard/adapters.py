from __future__ import annotations

"""Read-only adapters providing access to core trading data and control events."""

from typing import Any
import threading
import time

# Optional imports from the core. Adapters must not raise if modules are missing.
try:  # pragma: no cover - optional dependency
    from ai_trader import data_handler, notifications, learning
except Exception:  # pragma: no cover - dashboard must degrade gracefully
    data_handler = notifications = learning = None

_lock = threading.RLock()


class TradingDataAdapter:
    """Expose read-only data from the trading core.

    Each method acquires a global re-entrant lock to avoid race conditions with
    the running agent. All getters fall back to safe defaults when the core
    objects are not available.
    """

    def get_overview(self) -> dict:
        with _lock:
            balance = getattr(data_handler, "get_balance", lambda: 0.0)()
            daily_pnl = getattr(data_handler, "get_daily_pnl", lambda: 0.0)()
            total_trades = getattr(data_handler, "get_total_trades", lambda: 0)()
            total_pnl = getattr(data_handler, "get_total_pnl", lambda: 0.0)()
            win_rate = getattr(data_handler, "get_win_rate", lambda: 0.0)()
            open_positions = len(self.get_positions())
            last_orders = getattr(data_handler, "get_last_orders", lambda n=10: [])(10)
            return {
                "balance": balance,
                "daily_pnl": daily_pnl,
                "total_trades": total_trades,
                "total_pnl": total_pnl,
                "win_rate": win_rate,
                "open_positions": open_positions,
                "last_orders": last_orders,
            }

    def get_equity_series(self, window: str = "7d") -> list[dict]:
        with _lock:
            f = getattr(data_handler, "get_equity_series", None)
            if f:
                return f(window)
            # fallback mock series
            now = int(time.time() * 1000)
            return [{"ts": now - i * 60000, "equity": 10000 + i * 5} for i in range(120)]

    def get_logs(self, level: str = "info", limit: int = 200) -> list[dict]:
        with _lock:
            f = getattr(data_handler, "get_logs", None)
            return f(level, limit) if f else []

    def get_positions(self) -> list[dict]:
        with _lock:
            f = getattr(data_handler, "get_open_positions", None)
            return f() if f else []

    def get_kpis(self) -> dict:
        from .kpis import compute_kpis

        with _lock:
            return compute_kpis(self)

    def get_signals(self, limit: int = 200) -> list[dict]:
        with _lock:
            f = getattr(learning, "get_recent_signals", None)
            return f(limit) if f else []

    def get_alerts(self) -> list[dict]:
        with _lock:
            f = getattr(notifications, "get_alerts", None)
            return f() if f else []


class ControlAdapter:
    """Publish control events to the core through a thread-safe queue."""

    def _publish(self, kind: str, payload: dict[str, Any] | None = None) -> None:
        from .stream import publish_event

        publish_event(kind, payload or {})

    def start(self, reason: str | None = None) -> None:
        self._publish("control", {"action": "start", "reason": reason})

    def stop(self, reason: str | None = None) -> None:
        self._publish("control", {"action": "stop", "reason": reason})

    def pause(self, reason: str | None = None) -> None:
        self._publish("control", {"action": "pause", "reason": reason})

    def resume(self, reason: str | None = None) -> None:
        self._publish("control", {"action": "resume", "reason": reason})

    def set_mode(self, mode: str) -> None:
        self._publish("mode", {"mode": mode})

    def set_strategy(self, name: str, params: dict) -> None:
        self._publish("strategy", {"name": name, "params": params})
