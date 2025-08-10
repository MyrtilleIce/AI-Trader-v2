"""Environment preflight checks for ai_trader."""

from __future__ import annotations

import importlib
import os
import platform
import sys
from typing import List

from ai_trader.compat import ensure_numpy_compat


def _check_module(name: str, *, optional: bool = False, enabled: bool = True) -> bool:
    if not enabled:
        print(f"[SKIP] {name} (disabled)")
        return True
    try:
        mod = importlib.import_module(name)
        version = getattr(mod, "__version__", "unknown")
        print(f"[OK] {name} {version}")
        return True
    except Exception as exc:  # noqa: BLE001
        level = "optional" if optional else "required"
        print(f"[FAIL] {name} ({level}): {exc}")
        return optional


def main() -> int:
    print(f"Python {platform.python_version()} on {platform.system()} {platform.machine()}")
    enable_learning = os.getenv("ENABLE_LEARNING", "true").lower() == "true"
    enable_openai = os.getenv("ENABLE_OPENAI", "true").lower() == "true"
    enable_optuna = os.getenv("ENABLE_OPTUNA", "true").lower() == "true"
    enable_metrics = os.getenv("ENABLE_METRICS_EXPORT", "false").lower() == "true"

    ok = True
    ok &= _check_module("numpy")
    ensure_numpy_compat()
    ok &= _check_module("pandas")
    ok &= _check_module("pandas_ta")
    ok &= _check_module("flask")
    ok &= _check_module("dash")
    ok &= _check_module("plotly")
    ok &= _check_module("sklearn")
    ok &= _check_module("openai", optional=True, enabled=enable_openai)
    ok &= _check_module("tensorflow", optional=True, enabled=enable_learning)
    ok &= _check_module("keras", optional=True, enabled=enable_learning)
    ok &= _check_module("optuna", optional=True, enabled=enable_optuna)
    ok &= _check_module("prometheus_client", optional=True, enabled=enable_metrics)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
