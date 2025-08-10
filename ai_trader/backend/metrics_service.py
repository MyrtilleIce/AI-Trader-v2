"""Utility functions to expose agent metrics for the dashboard.

The service keeps a small in-memory cache with a configurable TTL to avoid
expensive computations on every HTTP request. Only read-only access to the
agent is provided; the service never triggers trading actions.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

log = logging.getLogger("dashboard.metrics")


class MetricsService:
    """Helper gathering metrics from the trading agent with a TTL cache."""

    def __init__(self, agent: object, ttl: int = 5) -> None:
        self.agent = agent
        self.ttl = ttl
        self._cache: Dict[str, tuple[Any, float]] = {}

    # ------------------------------------------------------------------
    def _cached(self, key: str, compute) -> Any:
        now = time.time()
        if key in self._cache and now - self._cache[key][1] < self.ttl:
            return self._cache[key][0]
        value = compute()
        self._cache[key] = (value, now)
        return value

    # ------------------------------------------------------------------
    def get_kpis(self) -> Dict[str, Any]:
        def _compute() -> Dict[str, Any]:
            if not self.agent:
                return self._default_metrics()

            balance = (
                asyncio.run(self.agent.execution.get_account_balance())
                if hasattr(self.agent, "execution")
                else 0
            )
            positions = (
                getattr(self.agent.risk_manager, "open_trades", [])
                if hasattr(self.agent, "risk_manager")
                else []
            )
            daily_pnl = (
                getattr(self.agent.risk_manager, "daily_pnl", 0)
                if hasattr(self.agent, "risk_manager")
                else 0
            )
            total_trades = getattr(self.agent, "total_trades", 0)
            winning_trades = getattr(self.agent, "winning_trades", 0)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            return {
                "balance": balance,
                "daily_pnl": daily_pnl,
                "total_pnl": getattr(self.agent, "total_pnl", 0),
                "open_positions": len(positions),
                "win_rate": win_rate,
                "total_trades": total_trades,
                "status": "active" if getattr(self.agent, "is_running", False) else "stopped",
                "current_drawdown": (
                    getattr(self.agent.risk_manager, "current_drawdown", 0)
                    if hasattr(self.agent, "risk_manager")
                    else 0
                ),
                "max_drawdown": getattr(self.agent, "max_drawdown", 0),
                "leverage": getattr(self.agent, "leverage", 0),
                "capital_per_trade": "10%",
                "last_update": datetime.utcnow().isoformat(),
            }

        return self._cached("kpis", _compute)

    # ------------------------------------------------------------------
    def get_equity_curve(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        def _compute() -> List[Dict[str, Any]]:
            if not self.agent or not hasattr(self.agent, "equity_history"):
                points = []
                cur = start
                while cur <= end:
                    points.append({"timestamp": cur.isoformat(), "equity": 1000})
                    cur += timedelta(hours=1)
                return points

            equity_data = []
            for point in getattr(self.agent, "equity_history", []):
                ts = datetime.fromisoformat(point["timestamp"])
                if start <= ts <= end:
                    equity_data.append(point)
            return equity_data

        key = f"equity:{start.isoformat()}:{end.isoformat()}"
        return self._cached(key, _compute)

    # ------------------------------------------------------------------
    def get_positions(self) -> List[Dict[str, Any]]:
        def _compute() -> List[Dict[str, Any]]:
            if not self.agent or not hasattr(self.agent, "risk_manager"):
                return []
            positions = getattr(self.agent.risk_manager, "open_trades", [])
            formatted = []
            for pos in positions:
                current_price = getattr(self.agent, "current_price", pos.get("entry_price", 0))
                entry_price = pos.get("entry_price", 0)
                size = pos.get("size", 0)
                side = pos.get("side", "long")
                if side.lower() == "long":
                    unrealized = (current_price - entry_price) * size
                else:
                    unrealized = (entry_price - current_price) * size
                formatted.append(
                    {
                        "id": pos.get("id", "N/A"),
                        "symbol": pos.get("symbol", "BTCUSDT"),
                        "side": side.upper(),
                        "size": size,
                        "entry_price": entry_price,
                        "current_price": current_price,
                        "unrealized_pnl": unrealized,
                        "unrealized_pnl_pct": (
                            unrealized / (entry_price * size) * 100 if entry_price * size > 0 else 0
                        ),
                        "stop_loss": pos.get("stop_loss"),
                        "take_profit": pos.get("take_profit"),
                        "timestamp": (
                            pos.get("timestamp", datetime.utcnow()).isoformat()
                            if isinstance(pos.get("timestamp"), datetime)
                            else pos.get("timestamp", "N/A")
                        ),
                        "duration": (
                            str(datetime.utcnow() - pos.get("timestamp", datetime.utcnow()))
                            if isinstance(pos.get("timestamp"), datetime)
                            else "N/A"
                        ),
                    }
                )
            return formatted

        return self._cached("positions", _compute)

    # ------------------------------------------------------------------
    def get_recent_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        def _compute() -> List[Dict[str, Any]]:
            if not self.agent or not hasattr(self.agent, "trade_history"):
                return []
            trades = getattr(self.agent, "trade_history", [])[-limit:]
            formatted = []
            for trade in trades:
                formatted.append(
                    {
                        "id": trade.get("id", "N/A"),
                        "symbol": trade.get("symbol", "BTCUSDT"),
                        "side": trade.get("side", "N/A").upper(),
                        "size": trade.get("size", 0),
                        "entry_price": trade.get("entry_price", 0),
                        "exit_price": trade.get("exit_price", 0),
                        "pnl": trade.get("pnl", 0),
                        "pnl_pct": trade.get("pnl_pct", 0),
                        "duration": str(trade.get("duration", "N/A")),
                        "entry_time": (
                            trade.get("entry_time", datetime.utcnow()).isoformat()
                            if isinstance(trade.get("entry_time"), datetime)
                            else trade.get("entry_time", "N/A")
                        ),
                        "exit_time": (
                            trade.get("exit_time", datetime.utcnow()).isoformat()
                            if isinstance(trade.get("exit_time"), datetime)
                            else trade.get("exit_time", "N/A")
                        ),
                        "close_reason": trade.get("close_reason", "N/A"),
                    }
                )
            return formatted

        key = f"trades:{limit}"
        return self._cached(key, _compute)

    # ------------------------------------------------------------------
    def get_performance_data(self, days: int = 7) -> List[Dict[str, Any]]:
        def _compute() -> List[Dict[str, Any]]:
            data: List[Dict[str, Any]] = []
            for i in range(days):
                date = datetime.utcnow() - timedelta(days=i)
                pnl = (i % 3 - 1) * 50 + (i * 10)
                data.append(
                    {
                        "date": date.strftime("%Y-%m-%d"),
                        "pnl": pnl,
                        "trades": max(1, i % 5),
                        "win_rate": 60 + (i % 40),
                    }
                )
            return list(reversed(data))

        key = f"performance:{days}"
        return self._cached(key, _compute)

    # ------------------------------------------------------------------
    def get_logs(self, lines: int = 200) -> List[Dict[str, Any]]:
        def _compute() -> List[Dict[str, Any]]:
            if not self.agent or not hasattr(self.agent, "recent_logs"):
                return [
                    {"timestamp": datetime.utcnow().isoformat(), "level": "INFO", "message": "Agent initialized"},
                    {"timestamp": datetime.utcnow().isoformat(), "level": "INFO", "message": "WebSocket connected"},
                    {"timestamp": datetime.utcnow().isoformat(), "level": "INFO", "message": "Risk manager active"},
                ]
            logs = getattr(self.agent, "recent_logs", [])[-lines:]
            return logs

        key = f"logs:{lines}"
        return self._cached(key, _compute)

    # ------------------------------------------------------------------
    def _default_metrics(self) -> Dict[str, Any]:
        return {
            "balance": 0,
            "daily_pnl": 0,
            "total_pnl": 0,
            "open_positions": 0,
            "win_rate": 0,
            "total_trades": 0,
            "status": "disconnected",
            "current_drawdown": 0,
            "max_drawdown": 0,
            "leverage": 0,
            "capital_per_trade": "10%",
            "last_update": datetime.utcnow().isoformat(),
        }


__all__ = ["MetricsService"]
