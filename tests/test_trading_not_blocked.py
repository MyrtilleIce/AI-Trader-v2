import time
from datetime import datetime

from ai_trader.dashboard import server


class DummyExecution:
    async def get_account_balance(self):
        return 0


class DummyRisk:
    open_trades = []
    daily_pnl = 0
    current_drawdown = 0


class DummyAgent:
    execution = DummyExecution()
    risk_manager = DummyRisk()
    total_pnl = 0
    total_trades = 0
    winning_trades = 0
    is_running = True
    start_time = datetime.utcnow()
    equity_history = []
    trade_history = []
    recent_logs = []


def _run_loop() -> float:
    start = time.time()
    for _ in range(5):
        time.sleep(0.01)
    return time.time() - start


def test_trading_not_blocked():
    baseline = _run_loop()
    server.run_dashboard(DummyAgent(), port=5056)
    with_dash = _run_loop()
    assert with_dash - baseline < 0.5

