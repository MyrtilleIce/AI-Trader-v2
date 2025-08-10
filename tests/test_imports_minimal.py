import os
import sys

os.environ.setdefault("ENABLE_LEARNING", "false")
os.environ.setdefault("ENABLE_OPENAI", "false")
os.environ.setdefault("ENABLE_OPTUNA", "false")
os.environ.setdefault("ENABLE_METRICS_EXPORT", "false")

from ai_trader.compat import ensure_numpy_compat


def test_strategy_and_learning_importable(monkeypatch):
    ensure_numpy_compat()
    try:
        import pandas_ta  # type: ignore  # noqa: F401
    except Exception:  # noqa: BLE001
        import types
        ta = types.ModuleType("pandas_ta")
        monkeypatch.setitem(sys.modules, "pandas_ta", ta)
        import pandas_ta  # type: ignore  # noqa: F401

    from ai_trader.strategy import Strategy
    from ai_trader.learning import Researcher, AutoOptimizer

    Strategy()
    Researcher()
    AutoOptimizer()

    import numpy as np
    assert hasattr(np, "NaN"), "NumPy NaN shim missing"
