"""REST API blueprint for the dashboard."""

from __future__ import annotations

from flask import Blueprint, Response, jsonify, request, send_file
import io

from .adapters import TradingDataAdapter, ControlAdapter
from .security import require_auth
from .news import get_news
from .stream import sse_stream
from . import export as export_utils

api_bp = Blueprint("api", __name__)
_adapter = TradingDataAdapter()
_ctrl = ControlAdapter()


def ok(data):
    return jsonify({"ok": True, "data": data, "error": None})


def err(code, msg, status: int = 400):
    return (
        jsonify({"ok": False, "data": None, "error": {"code": code, "msg": msg}}),
        status,
    )


@api_bp.get("/overview")
@require_auth
def overview():
    try:
        return ok(_adapter.get_overview())
    except Exception as e:  # pragma: no cover - defensive
        return err("overview_failed", str(e))


@api_bp.get("/equity")
@require_auth
def equity():
    window = request.args.get("window", "7d")
    try:
        return ok({"series": _adapter.get_equity_series(window), "refresh_s": 3})
    except Exception as e:  # pragma: no cover
        return err("equity_failed", str(e))


@api_bp.get("/logs")
@require_auth
def logs():
    level = request.args.get("level", "info")
    limit = int(request.args.get("limit", 200))
    try:
        return ok(_adapter.get_logs(level, limit))
    except Exception as e:  # pragma: no cover
        return err("logs_failed", str(e))


@api_bp.get("/positions")
@require_auth
def positions():
    try:
        return ok(_adapter.get_positions())
    except Exception as e:
        return err("positions_failed", str(e))


@api_bp.get("/kpis")
@require_auth
def kpis():
    try:
        return ok(_adapter.get_kpis())
    except Exception as e:
        return err("kpis_failed", str(e))


@api_bp.get("/signals")
@require_auth
def signals():
    limit = int(request.args.get("limit", 200))
    try:
        return ok(_adapter.get_signals(limit))
    except Exception as e:
        return err("signals_failed", str(e))


@api_bp.get("/alerts")
@require_auth
def alerts():
    try:
        return ok(_adapter.get_alerts())
    except Exception as e:
        return err("alerts_failed", str(e))


@api_bp.get("/news")
@require_auth
def news():
    try:
        return ok(get_news())
    except Exception as e:
        return err("news_failed", str(e))


@api_bp.post("/control/<action>")
@require_auth
def control(action: str):
    reason = (request.json or {}).get("reason") if request.is_json else None
    try:
        if action == "start":
            _ctrl.start(reason)
        elif action == "stop":
            _ctrl.stop(reason)
        elif action == "pause":
            _ctrl.pause(reason)
        elif action == "resume":
            _ctrl.resume(reason)
        else:
            return err("bad_action", action)
        return ok({"status": action})
    except Exception as e:  # pragma: no cover
        return err("control_failed", str(e))


@api_bp.post("/mode")
@require_auth
def mode():
    data = request.get_json() or {}
    mode = data.get("mode")
    if mode not in {"backtest", "paper", "live"}:
        return err("bad_mode", str(mode))
    try:
        _ctrl.set_mode(mode)
        return ok({"mode": mode})
    except Exception as e:
        return err("mode_failed", str(e))


@api_bp.post("/strategy")
@require_auth
def strategy():
    data = request.get_json() or {}
    name = data.get("name")
    params = data.get("params", {})
    if not name:
        return err("bad_strategy", "missing name")
    try:
        _ctrl.set_strategy(name, params)
        return ok({"name": name})
    except Exception as e:
        return err("strategy_failed", str(e))


# --------------------------- Exports ---------------------------------------
@api_bp.get("/export/trades.csv")
@require_auth
def export_trades():
    rows = _adapter.get_positions()  # placeholder until real trade history
    data = export_utils.trades_csv(rows)
    return send_file(
        io.BytesIO(data),
        mimetype="text/csv",
        as_attachment=True,
        download_name="trades.csv",
    )


@api_bp.get("/export/metrics.xlsx")
@require_auth
def export_metrics():
    data = export_utils.metrics_xlsx(_adapter.get_kpis())
    return send_file(
        io.BytesIO(data),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="metrics.xlsx",
    )


@api_bp.get("/export/report.pdf")
@require_auth
def export_report():
    data = export_utils.report_pdf(_adapter.get_kpis())
    return send_file(
        io.BytesIO(data),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="report.pdf",
    )


# ---------------------------- Streaming ------------------------------------
@api_bp.get("/stream")
@require_auth
def stream_events():
    return sse_stream()
