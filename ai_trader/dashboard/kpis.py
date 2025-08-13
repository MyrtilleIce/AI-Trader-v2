"""Computation helpers for dashboard KPIs.

These functions operate purely on numeric data and do not depend on Dash or
Flask. They may use ``numpy`` if available but fall back to Python lists if the
library is missing.
"""

from __future__ import annotations

import math
from typing import Iterable

try:  # pragma: no cover - optional dependency
    import numpy as np
except Exception:  # pragma: no cover
    np = None


def _to_array(values: Iterable[float]):
    if np is None:
        return list(values)
    return np.array(list(values), dtype=float)


def compute_kpis(adapter) -> dict:
    """Compute basic risk metrics from the equity series."""

    series = adapter.get_equity_series("30d")
    eq = _to_array(p["equity"] for p in series)
    if len(eq) < 2:
        return {
            "pnl_total": 0.0,
            "pnl_daily": 0.0,
            "drawdown_max": 0.0,
            "sharpe": 0.0,
            "trades_count": 0,
            "max_consec_loss": 0,
            "max_consec_win": 0,
        }

    if np is None:
        # simple pure-python implementation
        ret = [eq[i + 1] - eq[i] for i in range(len(eq) - 1)]
        peak = float("-inf")
        ddmax = 0.0
        for v in eq:
            peak = max(peak, v)
            ddmax = max(ddmax, peak - v)
        mean_ret = sum(ret) / len(ret)
        std_ret = (sum((r - mean_ret) ** 2 for r in ret) / (len(ret) - 1)) ** 0.5
    else:
        ret = np.diff(eq)
        peak = float("-inf")
        ddmax = 0.0
        for v in eq:
            peak = max(peak, v)
            ddmax = max(ddmax, peak - v)
        mean_ret = float(ret.mean())
        std_ret = float(ret.std())

    sharpe = (mean_ret / (std_ret + 1e-9)) * math.sqrt(252)
    return {
        "pnl_total": float(eq[-1] - eq[0]),
        "pnl_daily": float(ret[-1] if len(ret) else 0.0),
        "drawdown_max": float(ddmax),
        "sharpe": float(sharpe),
        "trades_count": 0,
        "max_consec_loss": 0,
        "max_consec_win": 0,
    }
