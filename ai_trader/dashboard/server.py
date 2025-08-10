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


@app.route("/api/kpis")
@requires_auth
def api_kpis() -> Response:
    return api_metrics()


@app.route("/api/metrics/<name>")
@requires_auth
def api_metric(name: str) -> Response:
    if not dashboard_api:
        return jsonify({"error": "Agent not initialized"}), 503
    metrics = dashboard_api.get_metrics()
    if name not in metrics:
        return jsonify({"error": "metric not found"}), 404
    return jsonify({name: metrics[name]})


@app.route("/api/equity_curve")
@requires_auth
def api_equity_curve() -> Response:
    if not dashboard_api:
        return jsonify([]), 503
    start_str = request.args.get("from")
    end_str = request.args.get("to")
    if start_str and end_str:
        start = datetime.fromisoformat(start_str)
        end = datetime.fromisoformat(end_str)
    else:
        hours = int(request.args.get("hours", 24))
        end = datetime.utcnow()
        start = end - timedelta(hours=hours)
    return jsonify(dashboard_api.get_equity_curve(start, end))


@app.route("/api/positions")
@requires_auth
def api_positions() -> Response:
    if not dashboard_api:
        return jsonify([]), 503
    return jsonify(dashboard_api.get_positions())


@app.route("/api/orders")
@requires_auth
def api_orders() -> Response:
    if not dashboard_api:
        return jsonify([]), 503
    limit = int(request.args.get("limit", 50))
    return jsonify(dashboard_api.get_recent_trades(limit))


@app.route("/api/trades")
@requires_auth
def api_trades() -> Response:
    return api_orders()


@app.route("/api/performance")
@requires_auth
def api_performance() -> Response:
    if not dashboard_api:
        return jsonify([]), 503
    days = int(request.args.get("days", 7))
    return jsonify(dashboard_api.get_performance_data(days))


@app.route("/api/logs")
@requires_auth
def api_logs() -> Response:
    if not dashboard_api:
        return jsonify([]), 503
    lines = int(request.args.get("lines", 200))
    return jsonify(dashboard_api.get_logs(lines))


@app.route("/api/control", methods=["POST"])
@requires_auth
def api_control() -> Response:
    if not agent_instance:
        return jsonify({"error": "Agent not available"}), 503
    try:
        data = request.get_json() or {}
        action = data.get("action")

        if action == "start" and hasattr(agent_instance, "start"):
            result = asyncio.run(agent_instance.start())
            return jsonify({"status": "started", "success": result})

        if action == "stop" and hasattr(agent_instance, "stop"):
            asyncio.run(agent_instance.stop())
            return jsonify({"status": "stopped"})

        if action == "restart":
            if hasattr(agent_instance, "restart"):
                asyncio.run(agent_instance.restart())
                return jsonify({"status": "restarted"})
            if hasattr(agent_instance, "stop") and hasattr(agent_instance, "start"):
                asyncio.run(agent_instance.stop())
                asyncio.sleep(2)
                result = asyncio.run(agent_instance.start())
                return jsonify({"status": "restarted", "success": result})
            return jsonify({"error": "Restart method not available"}), 400

        if action == "test" and hasattr(agent_instance, "run_diagnostic_tests"):
            asyncio.run(agent_instance.run_diagnostic_tests())
            return jsonify({"status": "tests_started"})

        if action == "emergency_stop" and hasattr(agent_instance, "emergency_stop"):
            asyncio.run(agent_instance.emergency_stop())
            return jsonify({"status": "emergency_stopped"})

        return jsonify({"error": "Invalid action"}), 400

    except Exception as exc:  # noqa: BLE001
        log.error("Control API error: %s", exc)
        return jsonify({"error": str(exc)}), 500


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
        app.run(host=host, port=port, debug=debug, use_reloader=False, threaded=True)

    dashboard_thread = threading.Thread(target=_run_flask, daemon=True)
    dashboard_thread.start()
    log.info("Dashboard started successfully on http://%s:%s", host, port)
    return dashboard_thread


__all__ = ["run_dashboard", "app", "DashboardAPI"]
