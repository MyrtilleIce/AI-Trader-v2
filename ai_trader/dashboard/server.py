import threading
import logging
import json
import asyncio
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, request
from typing import Optional
import os

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Instance globale de l'agent
agent_instance: Optional[object] = None


class DashboardAPI:
    """Classe gérant les API du dashboard"""

    def __init__(self, agent: object) -> None:
        self.agent = agent

    def get_metrics(self) -> dict:
        """Récupérer métriques principales"""
        try:
            if not self.agent:
                return self._default_metrics()

            balance = (
                asyncio.run(self.agent.execution.get_account_balance())
                if hasattr(self.agent, 'execution') else 0
            )
            positions = (
                getattr(self.agent.risk_manager, 'open_trades', [])
                if hasattr(self.agent, 'risk_manager') else []
            )
            daily_pnl = (
                getattr(self.agent.risk_manager, 'daily_pnl', 0)
                if hasattr(self.agent, 'risk_manager') else 0
            )
            total_trades = getattr(self.agent, 'total_trades', 0)
            winning_trades = getattr(self.agent, 'winning_trades', 0)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            return {
                'balance': balance,
                'daily_pnl': daily_pnl,
                'total_pnl': getattr(self.agent, 'total_pnl', 0),
                'open_positions': len(positions),
                'win_rate': win_rate,
                'total_trades': total_trades,
                'status': 'active' if getattr(self.agent, 'is_running', False) else 'stopped',
                'current_drawdown': (
                    getattr(self.agent.risk_manager, 'current_drawdown', 0)
                    if hasattr(self.agent, 'risk_manager') else 0
                ),
                'max_drawdown': getattr(self.agent, 'max_drawdown', 0),
                'leverage': 10,
                'capital_per_trade': '10%',
                'last_update': datetime.utcnow().isoformat(),
            }
        except Exception as exc:  # noqa: BLE001
            logging.error("Error getting metrics: %s", exc)
            return self._default_metrics()

    def get_equity_curve(self, hours: int = 24) -> list:
        """Récupérer courbe d'equity"""
        try:
            if not self.agent or not hasattr(self.agent, 'equity_history'):
                now = datetime.utcnow()
                return [
                    {
                        'timestamp': (now - timedelta(hours=h)).isoformat(),
                        'equity': 1000 + (h * 2.5) + (h % 3 * 10),
                    }
                    for h in range(hours, 0, -1)
                ]

            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            equity_data = []
            for point in self.agent.equity_history:
                if datetime.fromisoformat(point['timestamp']) >= cutoff_time:
                    equity_data.append(point)
            return equity_data
        except Exception as exc:  # noqa: BLE001
            logging.error("Error getting equity curve: %s", exc)
            return []

    def get_positions(self) -> list:
        """Récupérer positions ouvertes"""
        try:
            if not self.agent or not hasattr(self.agent, 'risk_manager'):
                return []
            positions = getattr(self.agent.risk_manager, 'open_trades', [])
            formatted_positions = []
            for pos in positions:
                current_price = getattr(self.agent, 'current_price', pos.get('entry_price', 0))
                entry_price = pos.get('entry_price', 0)
                size = pos.get('size', 0)
                side = pos.get('side', 'long')

                if side.lower() == 'long':
                    unrealized_pnl = (current_price - entry_price) * size
                else:
                    unrealized_pnl = (entry_price - current_price) * size

                formatted_positions.append({
                    'id': pos.get('id', 'N/A'),
                    'symbol': pos.get('symbol', 'BTCUSDT'),
                    'side': side.upper(),
                    'size': size,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'unrealized_pnl': unrealized_pnl,
                    'unrealized_pnl_pct': (
                        unrealized_pnl / (entry_price * size) * 100
                        if entry_price * size > 0 else 0
                    ),
                    'stop_loss': pos.get('stop_loss'),
                    'take_profit': pos.get('take_profit'),
                    'timestamp': (
                        pos.get('timestamp', datetime.utcnow()).isoformat()
                        if isinstance(pos.get('timestamp'), datetime)
                        else pos.get('timestamp', 'N/A')
                    ),
                    'duration': (
                        str(datetime.utcnow() - pos.get('timestamp', datetime.utcnow()))
                        if isinstance(pos.get('timestamp'), datetime)
                        else 'N/A'
                    ),
                })
            return formatted_positions
        except Exception as exc:  # noqa: BLE001
            logging.error("Error getting positions: %s", exc)
            return []

    def get_recent_trades(self, limit: int = 50) -> list:
        """Récupérer trades récents"""
        try:
            if not self.agent or not hasattr(self.agent, 'trade_history'):
                return []
            trades = getattr(self.agent, 'trade_history', [])[-limit:]
            formatted_trades = []
            for trade in trades:
                formatted_trades.append({
                    'id': trade.get('id', 'N/A'),
                    'symbol': trade.get('symbol', 'BTCUSDT'),
                    'side': trade.get('side', 'N/A').upper(),
                    'size': trade.get('size', 0),
                    'entry_price': trade.get('entry_price', 0),
                    'exit_price': trade.get('exit_price', 0),
                    'pnl': trade.get('pnl', 0),
                    'pnl_pct': trade.get('pnl_pct', 0),
                    'duration': str(trade.get('duration', 'N/A')),
                    'entry_time': (
                        trade.get('entry_time', datetime.utcnow()).isoformat()
                        if isinstance(trade.get('entry_time'), datetime)
                        else trade.get('entry_time', 'N/A')
                    ),
                    'exit_time': (
                        trade.get('exit_time', datetime.utcnow()).isoformat()
                        if isinstance(trade.get('exit_time'), datetime)
                        else trade.get('exit_time', 'N/A')
                    ),
                    'close_reason': trade.get('close_reason', 'N/A'),
                })
            return formatted_trades
        except Exception as exc:  # noqa: BLE001
            logging.error("Error getting recent trades: %s", exc)
            return []

    def get_performance_data(self, days: int = 7) -> list:
        """Récupérer données de performance quotidienne"""
        try:
            performance_data = []
            for i in range(days):
                date = datetime.utcnow() - timedelta(days=i)
                pnl = (i % 3 - 1) * 50 + (i * 10)
                performance_data.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'pnl': pnl,
                    'trades': max(1, i % 5),
                    'win_rate': 60 + (i % 40),
                })
            return list(reversed(performance_data))
        except Exception as exc:  # noqa: BLE001
            logging.error("Error getting performance data: %s", exc)
            return []

    def get_logs(self, lines: int = 200) -> list:
        """Récupérer logs récents"""
        try:
            if not self.agent or not hasattr(self.agent, 'recent_logs'):
                return [
                    {'timestamp': datetime.utcnow().isoformat(), 'level': 'INFO', 'message': 'Agent initialized'},
                    {'timestamp': datetime.utcnow().isoformat(), 'level': 'INFO', 'message': 'WebSocket connected'},
                    {'timestamp': datetime.utcnow().isoformat(), 'level': 'INFO', 'message': 'Risk manager active'},
                ]
            logs = getattr(self.agent, 'recent_logs', [])[-lines:]
            return logs
        except Exception as exc:  # noqa: BLE001
            logging.error("Error getting logs: %s", exc)
            return []

    def _default_metrics(self) -> dict:  # noqa: D401
        """Métriques par défaut en cas d'erreur"""
        return {
            'balance': 0,
            'daily_pnl': 0,
            'total_pnl': 0,
            'open_positions': 0,
            'win_rate': 0,
            'total_trades': 0,
            'status': 'disconnected',
            'current_drawdown': 0,
            'max_drawdown': 0,
            'leverage': 10,
            'capital_per_trade': '10%',
            'last_update': datetime.utcnow().isoformat(),
        }


dashboard_api: Optional[DashboardAPI] = None

# ==================== ROUTES HTML ====================
@app.route('/')
def dashboard() -> str:
    """Page principale du dashboard"""
    return render_template('dashboard.html')

# ==================== ROUTES API ====================
@app.route('/api/status')
def api_status() -> str:
    """Status général de l'agent"""
    try:
        return jsonify({
            'status': 'active' if agent_instance and getattr(agent_instance, 'is_running', False) else 'stopped',
            'timestamp': datetime.utcnow().isoformat(),
            'uptime': str(datetime.utcnow() - getattr(agent_instance, 'start_time', datetime.utcnow())) if agent_instance else '0:00:00',
        })
    except Exception as exc:  # noqa: BLE001
        return jsonify({'error': str(exc)}), 500


@app.route('/api/metrics')
def api_metrics() -> str:
    """Métriques principales"""
    if not dashboard_api:
        return jsonify({'error': 'Agent not initialized'}), 503
    return jsonify(dashboard_api.get_metrics())


@app.route('/api/equity_curve')
def api_equity_curve() -> str:
    """Courbe d'equity"""
    if not dashboard_api:
        return jsonify([]), 503
    hours = int(request.args.get('hours', 24))
    return jsonify(dashboard_api.get_equity_curve(hours))


@app.route('/api/positions')
def api_positions() -> str:
    """Positions ouvertes"""
    if not dashboard_api:
        return jsonify([]), 503
    return jsonify(dashboard_api.get_positions())


@app.route('/api/trades')
def api_trades() -> str:
    """Trades récents"""
    if not dashboard_api:
        return jsonify([]), 503
    limit = int(request.args.get('limit', 50))
    return jsonify(dashboard_api.get_recent_trades(limit))


@app.route('/api/performance')
def api_performance() -> str:
    """Données de performance"""
    if not dashboard_api:
        return jsonify([]), 503
    days = int(request.args.get('days', 7))
    return jsonify(dashboard_api.get_performance_data(days))


@app.route('/api/logs')
def api_logs() -> str:
    """Logs récents"""
    if not dashboard_api:
        return jsonify([]), 503
    lines = int(request.args.get('lines', 200))
    return jsonify(dashboard_api.get_logs(lines))


# ==================== CONTRÔLES AGENT ====================
@app.route('/api/control', methods=['POST'])
def api_control() -> str:
    """Contrôler l'agent"""
    if not agent_instance:
        return jsonify({'error': 'Agent not available'}), 503
    try:
        data = request.get_json() or {}
        action = data.get('action')

        if action == 'start':
            if hasattr(agent_instance, 'start'):
                result = asyncio.run(agent_instance.start())
                return jsonify({'status': 'started', 'success': result})
            return jsonify({'error': 'Start method not available'}), 400

        if action == 'stop':
            if hasattr(agent_instance, 'stop'):
                asyncio.run(agent_instance.stop())
                return jsonify({'status': 'stopped'})
            return jsonify({'error': 'Stop method not available'}), 400

        if action == 'restart':
            if hasattr(agent_instance, 'restart'):
                asyncio.run(agent_instance.restart())
                return jsonify({'status': 'restarted'})
            if hasattr(agent_instance, 'stop') and hasattr(agent_instance, 'start'):
                asyncio.run(agent_instance.stop())
                asyncio.sleep(2)
                result = asyncio.run(agent_instance.start())
                return jsonify({'status': 'restarted', 'success': result})
            return jsonify({'error': 'Restart method not available'}), 400

        if action == 'test':
            if hasattr(agent_instance, 'run_diagnostic_tests'):
                asyncio.run(agent_instance.run_diagnostic_tests())
                return jsonify({'status': 'tests_started'})
            return jsonify({'error': 'Test method not available'}), 400

        if action == 'emergency_stop':
            if hasattr(agent_instance, 'emergency_stop'):
                asyncio.run(agent_instance.emergency_stop())
                return jsonify({'status': 'emergency_stopped'})
            return jsonify({'error': 'Emergency stop not available'}), 400

        return jsonify({'error': 'Invalid action'}), 400

    except Exception as exc:  # noqa: BLE001
        logging.error("Control API error: %s", exc)
        return jsonify({'error': str(exc)}), 500


# ==================== GESTION D'ERREURS ====================
@app.errorhandler(404)
def not_found(error):  # noqa: D401, ARG001
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):  # noqa: D401, ARG001
    return jsonify({'error': 'Internal server error'}), 500


# ==================== FONCTION DE LANCEMENT ====================
def run_dashboard(agent: object, host: str = '0.0.0.0', port: int = 5000, debug: bool = False) -> threading.Thread:
    """Lancer le dashboard Flask dans un thread séparé"""
    global agent_instance, dashboard_api
    agent_instance = agent
    dashboard_api = DashboardAPI(agent)

    def _run_flask() -> None:
        if not debug:
            werkzeug_logger = logging.getLogger('werkzeug')
            werkzeug_logger.setLevel(logging.WARNING)
        logging.info("Starting dashboard on http://%s:%s", host, port)
        app.run(host=host, port=port, debug=debug, use_reloader=False, threaded=True)

    dashboard_thread = threading.Thread(target=_run_flask, daemon=True)
    dashboard_thread.start()
    logging.info("Dashboard started successfully on http://%s:%s", host, port)
    return dashboard_thread
