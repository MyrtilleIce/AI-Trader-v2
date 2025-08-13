"""Dash layout for the dashboard UI."""

from __future__ import annotations

import os
import json
import requests
from dash import html, dcc, dash_table, callback, Output, Input, State
import plotly.graph_objects as go

BASE = lambda: f"http://localhost:{os.getenv('DASHBOARD_PORT','5000')}"


def build_layout():
    return html.Div(
        [
            html.H3("AI-Trader-v2 — Dashboard"),
            dcc.Store(id="window", data="7d"),
            dcc.Store(id="theme", data="light", storage_type="local"),
            dcc.Interval(id="tick", interval=3000, n_intervals=0),
            html.Div(id="kpi_row"),
            html.Div(
                [
                    dcc.RadioItems(id="win_sel", options=["1d", "7d", "30d", "all"], value="7d"),
                    dcc.Graph(id="equity_fig"),
                ]
            ),
            html.H4("Activity Logs"),
            html.Pre(id="log_box", style={"height": "200px", "overflowY": "scroll"}),
            html.H4("Open Positions"),
            dash_table.DataTable(id="pos_table"),
            html.H4("KPIs"),
            html.Pre(id="kpi_detail"),
            html.H4("Signals"),
            dash_table.DataTable(id="signal_table"),
            html.H4("Alerts"),
            html.Ul(id="alert_list"),
            html.H4("News"),
            html.Ul(id="news_list"),
            html.H4("Control"),
            html.Div(
                [
                    html.Button("Start", id="btn_start"),
                    html.Button("Stop", id="btn_stop"),
                    html.Button("Pause", id="btn_pause"),
                    html.Button("Resume", id="btn_resume"),
                    dcc.Dropdown(
                        id="mode_sel",
                        options=[{"label": m.title(), "value": m} for m in ["backtest", "paper", "live"]],
                        value="paper",
                    ),
                    html.Input(id="strategy_name", placeholder="strategy name"),
                    dcc.Textarea(id="strategy_params", placeholder="{\n}\n"),
                    html.Button("Apply Strategy", id="btn_strategy"),
                ]
            ),
            html.H4("Exports"),
            html.Div(
                [
                    html.A("Trades CSV", href="/api/export/trades.csv"),
                    html.Span(" | "),
                    html.A("Metrics XLSX", href="/api/export/metrics.xlsx"),
                    html.Span(" | "),
                    html.A("Report PDF", href="/api/export/report.pdf"),
                ]
            ),
        ],
        id="root",
    )


# ----------------------------- Callbacks ------------------------------------


@callback(Output("kpi_row", "children"), Input("tick", "n_intervals"))
def _kpis(_):
    try:
        r = requests.get(BASE() + "/api/overview", timeout=2)
        d = r.json()["data"]
        return (
            f"Balance: {d['balance']} | DailyPnL: {d['daily_pnl']} | Trades: {d['total_trades']} | "
            f"WinRate: {d['win_rate']} | Open: {d['open_positions']}"
        )
    except Exception:
        return "API indisponible"


@callback(Output("equity_fig", "figure"), Input("win_sel", "value"), Input("tick", "n_intervals"))
def _equity(win, _):
    try:
        r = requests.get(BASE() + f"/api/equity?window={win}", timeout=2)
        series = r.json()["data"]["series"]
        fig = go.Figure()
        if series:
            xs = [p["ts"] for p in series]
            ys = [p["equity"] for p in series]
            fig.add_scatter(x=xs, y=ys, mode="lines")
        fig.update_layout(margin=dict(l=20, r=20, t=10, b=20))
        return fig
    except Exception:
        return go.Figure()


@callback(Output("log_box", "children"), Input("tick", "n_intervals"))
def _logs(_):
    try:
        r = requests.get(BASE() + "/api/logs?level=info&limit=200", timeout=2)
        lines = [l.get("msg", "") for l in r.json()["data"]]
        return "\n".join(lines)
    except Exception:
        return ""


@callback(Output("pos_table", "data"), Input("tick", "n_intervals"))
def _positions(_):
    try:
        r = requests.get(BASE() + "/api/positions", timeout=2)
        return r.json()["data"]
    except Exception:
        return []


@callback(Output("kpi_detail", "children"), Input("tick", "n_intervals"))
def _kpi_details(_):
    try:
        r = requests.get(BASE() + "/api/kpis", timeout=2)
        return json.dumps(r.json()["data"], indent=2)
    except Exception:
        return "{}"


@callback(Output("signal_table", "data"), Input("tick", "n_intervals"))
def _signals(_):
    try:
        r = requests.get(BASE() + "/api/signals?limit=200", timeout=2)
        return r.json()["data"]
    except Exception:
        return []


@callback(Output("alert_list", "children"), Input("tick", "n_intervals"))
def _alerts(_):
    try:
        r = requests.get(BASE() + "/api/alerts", timeout=2)
        return [html.Li(a.get("msg", "")) for a in r.json()["data"]]
    except Exception:
        return []


@callback(Output("news_list", "children"), Input("tick", "n_intervals"))
def _news(_):
    try:
        r = requests.get(BASE() + "/api/news", timeout=2)
        return [html.Li(n["title"]) for n in r.json()["data"]]
    except Exception:
        return []


# Control callbacks ----------------------------------------------------------


@callback(Output("btn_start", "n_clicks"), Input("btn_start", "n_clicks"), prevent_initial_call=True)
def _start(n):
    if n:
        try:
            requests.post(BASE() + "/api/control/start", json={})
        except Exception:
            pass
    return 0


@callback(Output("btn_stop", "n_clicks"), Input("btn_stop", "n_clicks"), prevent_initial_call=True)
def _stop(n):
    if n:
        try:
            requests.post(BASE() + "/api/control/stop", json={})
        except Exception:
            pass
    return 0


@callback(Output("btn_pause", "n_clicks"), Input("btn_pause", "n_clicks"), prevent_initial_call=True)
def _pause(n):
    if n:
        try:
            requests.post(BASE() + "/api/control/pause", json={})
        except Exception:
            pass
    return 0


@callback(Output("btn_resume", "n_clicks"), Input("btn_resume", "n_clicks"), prevent_initial_call=True)
def _resume(n):
    if n:
        try:
            requests.post(BASE() + "/api/control/resume", json={})
        except Exception:
            pass
    return 0


@callback(Output("mode_sel", "value"), Input("mode_sel", "value"), prevent_initial_call=True)
def _mode(mode):
    try:
        requests.post(BASE() + "/api/mode", json={"mode": mode})
    except Exception:
        pass
    return mode


@callback(Output("btn_strategy", "n_clicks"), Input("btn_strategy", "n_clicks"), State("strategy_name", "value"), State("strategy_params", "value"), prevent_initial_call=True)
def _strategy(n, name, params):
    if n:
        try:
            payload = {"name": name or "", "params": json.loads(params or "{}")}
            requests.post(BASE() + "/api/strategy", json=payload)
        except Exception:
            pass
    return 0
