"""Flask based dashboard exposing read-only metrics from the trading agent."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import threading
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional

from flask import Flask, Response, jsonify, render_template, request

from .. import __version__
from ..backend.metrics_service import MetricsService

# ---------------------------------------------------------------------------
log = logging.getLogger("dashboard")

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)

# Register API blueprint and enable CORS for the dashboard API. The dashboard is
# optional; failures here should not prevent the core agent from running.
try:  # pragma: no cover - optional dependency
    from flask_cors import CORS

    origin = f"http://localhost:{os.getenv('DASHBOARD_PORT', '5000')}"
    CORS(app, resources={r"/api/*": {"origins": origin}})
except Exception:  # pragma: no cover
    pass

try:
    from .routes import api_bp

    app.register_blueprint(api_bp, url_prefix="/api")
except Exception as exc:  # pragma: no cover - blueprint optional
    log.warning("API blueprint not loaded: %s", exc)

# Optional websocket support -------------------------------------------------
try:  # pragma: no cover
    from . import stream as _stream

    _socketio = _stream.socketio
    if _socketio:
        try:
            _stream.attach_socketio(_socketio)
        except Exception:  # pragma: no cover - attaching should be best effort
            log.warning("SocketIO attachment failed", exc_info=True)
except Exception:  # pragma: no cover
    _stream = None
    _socketio = None

# Basic auth configuration --------------------------------------------------
USERNAME = os.getenv("DASHBOARD_USERNAME")
PASSWORD = os.getenv("DASHBOARD_PASSWORD")


def _check_auth(username: str, password: str) -> bool:
    return USERNAME == username and PASSWORD == password


def _authenticate() -> Response:
    return Response(
        "Authentication required",
        401,
        {"WWW-Authenticate": "Basic realm='Dashboard'"},
    )


def requires_auth(func):  # type: ignore[override]
    @wraps(func)
    def wrapped(*args, **kwargs):
        if USERNAME and PASSWORD:
            auth = request.authorization
            if not auth or not _check_auth(auth.username, auth.password):
                return _authenticate()
        return func(*args, **kwargs)

    return wrapped


# Instance globale de l'agent ------------------------------------------------
agent_instance: Optional[object] = None


class DashboardAPI:
    """Wrapper exposing cached metrics via :class:`MetricsService`."""

    def __init__(self, agent: object) -> None:
        self.service = MetricsService(agent)

    def get_metrics(self) -> dict:
        try:
            return self.service.get_kpis()
        except Exception as exc:  # noqa: BLE001
            log.error("Error getting metrics: %s", exc)
            return self.service._default_metrics()

    def get_equity_curve(self, start: datetime, end: datetime) -> list:
        try:
            return self.service.get_equity_curve(start, end)
        except Exception as exc:  # noqa: BLE001
            log.error("Error getting equity curve: %s", exc)
            return []

    def get_positions(self) -> list:
        try:
            return self.service.get_positions()
        except Exception as exc:  # noqa: BLE001
            log.error("Error getting positions: %s", exc)
            return []

    def get_recent_trades(self, limit: int = 50) -> list:
        try:
            return self.service.get_recent_trades(limit)
        except Exception as exc:  # noqa: BLE001
            log.error("Error getting recent trades: %s", exc)
            return []

    def get_performance_data(self, days: int = 7) -> list:
        try:
            return self.service.get_performance_data(days)
        except Exception as exc:  # noqa: BLE001
            log.error("Error getting performance data: %s", exc)
            return []

    def get_logs(self, lines: int = 200) -> list:
        try:
            return self.service.get_logs(lines)
        except Exception as exc:  # noqa: BLE001
            log.error("Error getting logs: %s", exc)
            return []


dashboard_api: Optional[DashboardAPI] = None


# ==================== ROUTES HTML ====================
@app.route("/")
@requires_auth
def dashboard() -> str:
    """Page principale du dashboard"""
    return render_template("dashboard.html")


# ==================== ROUTES API ====================
@app.route("/api/healthz")
@requires_auth
def api_healthz() -> Response:
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


@app.route("/api/version")
@requires_auth
def api_version() -> Response:
    return jsonify({"version": __version__})


@app.route("/api/status")
@requires_auth
def api_status() -> Response:
    try:
        return jsonify(
            {
                "status": "active"
                if agent_instance and getattr(agent_instance, "is_running", False)
                else "stopped",
                "timestamp": datetime.utcnow().isoformat(),
                "uptime": str(
                    datetime.utcnow() - getattr(agent_instance, "start_time", datetime.utcnow())
                )
                if agent_instance
                else "0:00:00",
            }
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500


@app.route("/api/metrics")
@requires_auth
def api_metrics() -> Response:
    if not dashboard_api:
        return jsonify({"error": "Agent not initialized"}), 503
    return jsonify(dashboard_api.get_metrics())


# ==================== GESTION D'ERREURS ====================
@app.errorhandler(404)
def not_found(error):  # noqa: D401, ARG001
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):  # noqa: D401, ARG001
    return jsonify({"error": "Internal server error"}), 500


# ==================== FONCTION DE LANCEMENT ====================
def find_available_port(start_port: int, attempts: int = 10) -> int:
    for port in range(start_port, start_port + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("", port))
                return port
            except OSError:
                continue
    raise OSError("No free port found")


def run_dashboard(
    agent: object,
    host: str = "0.0.0.0",
    port: int = 5000,
    debug: bool = False,
) -> threading.Thread:
    """Lancer le dashboard Flask dans un thread séparé"""
    global agent_instance, dashboard_api
    agent_instance = agent
    dashboard_api = DashboardAPI(agent)

    port = find_available_port(port)

    def _run_flask() -> None:
        if not debug:
            werkzeug_logger = logging.getLogger("werkzeug")
            werkzeug_logger.setLevel(logging.WARNING)
        log.info("Starting dashboard on http://%s:%s", host, port)
        if _stream and _socketio:
            try:
                _stream.attach_socketio(_socketio)
                _socketio.init_app(app, cors_allowed_origins="*")
                _socketio.run(app, host=host, port=port, debug=debug, use_reloader=False)
                return
            except Exception as exc:  # pragma: no cover
                log.warning("SocketIO disabled: %s", exc)
        app.run(host=host, port=port, debug=debug, use_reloader=False, threaded=True)

    dashboard_thread = threading.Thread(target=_run_flask, daemon=True)
    dashboard_thread.start()
    log.info("Dashboard started successfully on http://%s:%s", host, port)
    return dashboard_thread


__all__ = ["run_dashboard", "app", "DashboardAPI"]
