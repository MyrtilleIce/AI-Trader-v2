import asyncio
import os
import sys
import types

import pytest

# Stub sklearn to avoid heavy dependency during tests
sys.modules.setdefault("sklearn", types.ModuleType("sklearn"))
linear_model = types.ModuleType("linear_model")
linear_model.LinearRegression = object
sys.modules["sklearn.linear_model"] = linear_model

# Stub keras as well
keras_module = types.ModuleType("keras")
layers_module = types.ModuleType("layers")
layers_module.Dense = object
keras_module.layers = layers_module
models_module = types.ModuleType("models")
models_module.Sequential = object
keras_module.models = models_module
sys.modules.setdefault("keras", keras_module)
sys.modules["keras.layers"] = layers_module
sys.modules["keras.models"] = models_module
sys.modules.setdefault("openai", types.ModuleType("openai"))
sys.modules.setdefault("optuna", types.ModuleType("optuna"))
prom = types.ModuleType("prometheus_client")
prom.Counter = object
prom.Gauge = object
sys.modules.setdefault("prometheus_client", prom)
sys.modules.setdefault("pandas_ta", types.ModuleType("pandas_ta"))

strategy_stub = types.ModuleType("ai_trader.strategy")

class Strategy:  # minimal placeholder
    def apply_indicators(self, df):
        return df

    def generate_signal(self, df):
        return None


strategy_stub.Strategy = Strategy
sys.modules["ai_trader.strategy"] = strategy_stub

from ai_trader.main import TradingAgent


def test_boot_agent_intact(monkeypatch):
    monkeypatch.setenv("ENABLE_DASHBOARD", "false")

    # Prevent heavy operations
    async def fake_init_telegram(self):
        return None

    async def fake_startup_checks(self):
        return True

    async def fake_start_main_loop(self):
        return None

    monkeypatch.setattr(TradingAgent, "initialize_telegram_control", fake_init_telegram)
    monkeypatch.setattr(TradingAgent, "perform_startup_checks", fake_startup_checks)
    monkeypatch.setattr(TradingAgent, "start_main_loop", fake_start_main_loop)
    async def fake_notify(self, event, message):
        return None
    monkeypatch.setattr(TradingAgent, "notify", fake_notify)

    started_dash = []

    def fake_start_dashboard(self, host="0.0.0.0", port=None):  # noqa: D401
        started_dash.append(True)

    monkeypatch.setattr(TradingAgent, "start_dashboard", fake_start_dashboard)

    def fake_init(self, *args, **kwargs):
        self.is_running = False
        self.start_time = None

    monkeypatch.setattr(TradingAgent, "__init__", fake_init)
    agent = TradingAgent()
    asyncio.run(agent.start())
    asyncio.run(agent.stop())

    assert started_dash == []
