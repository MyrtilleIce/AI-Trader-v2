from datetime import datetime

from ai_trader.dashboard import server


class DummyExecution:
    async def get_account_balance(self):
        return 1000


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


def setup_module(module):
    server.dashboard_api = server.DashboardAPI(DummyAgent())


def test_health_kpis_positions():
    client = server.app.test_client()
    resp = client.get("/api/healthz")
    assert resp.status_code == 200
    resp = client.get("/api/kpis")
    assert resp.status_code == 200
    resp = client.get("/api/positions")
    assert resp.status_code == 200

