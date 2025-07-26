"""Simple real-time dashboard using Flask and Plotly."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime

from flask import Flask, jsonify, render_template, request
import plotly.graph_objects as go


class TradingDashboard:
    """Expose agent metrics through a web dashboard."""

    def __init__(self, agent, host: str = "0.0.0.0", port: int = 5000) -> None:
        self.app = Flask(__name__)
        self.agent = agent
        self.host = host
        self.port = port
        self.setup_routes()

    # ------------------------------------------------------------------
    def setup_routes(self) -> None:
        @self.app.route("/")
        def dashboard() -> str:
            return render_template("dashboard.html")

        @self.app.route("/api/status")
        def get_status() -> str:
            return jsonify({
                "status": "active" if getattr(self.agent, "is_running", False) else "stopped",
                "last_update": datetime.utcnow().isoformat(),
                "version": "2.0.0",
            })

        @self.app.route("/api/metrics")
        def get_metrics() -> str:
            return jsonify({
                "current_balance": getattr(self.agent, "get_balance", lambda: 0.0)(),
            })

        @self.app.route("/api/equity_curve")
        def get_equity_curve() -> str:
            curve = getattr(self.agent, "get_equity_curve", lambda hours=24: [])()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=[p["timestamp"] for p in curve], y=[p["equity"] for p in curve]))
            return fig.to_json()

        @self.app.errorhandler(404)
        def not_found(error):  # noqa: D401, ARG001
            return jsonify({"error": "Endpoint not found"}), 404

    # ------------------------------------------------------------------
    def create_dashboard_template(self) -> None:
        html = """
<!DOCTYPE html>
<html>
<head><title>AI Trader Dashboard</title></head>
<body>
<h1>AI Trader Dashboard</h1>
<div id='chart'></div>
<script src="https://cdn.plot.ly/plotly-2.20.0.min.js"></script>
<script>
fetch('/api/equity_curve').then(r=>r.json()).then(function(data){
  Plotly.newPlot('chart', data.data, data.layout);
});
</script>
</body>
</html>
"""
        import os

        os.makedirs("templates", exist_ok=True)
        with open("templates/dashboard.html", "w", encoding="utf-8") as fh:
            fh.write(html)

    # ------------------------------------------------------------------
    def run(self, debug: bool = False):
        self.create_dashboard_template()
        logging.info("Starting dashboard on http://%s:%s", self.host, self.port)

        def run_flask() -> None:
            self.app.run(host=self.host, port=self.port, debug=debug, use_reloader=False)

        thread = threading.Thread(target=run_flask, daemon=True)
        thread.start()
        return thread
