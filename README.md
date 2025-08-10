# AI Trader

Autonomous trading agent for Bitget Futures.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and provide your API credentials.
3. Run the agent:
   ```bash
   python -m ai_trader.main
   ```

Alternatively start the full stack with Postgres and Prometheus using Docker Compose:

```bash
docker-compose up
```

Logs and trade history are stored in `ai_trader/logs/`.

## Features

- Modular architecture with clear separation between data, strategy and execution.
- Advanced risk management with daily drawdown limits and trailing stops.
- Optional machine learning helpers (Optuna optimisation and simple dense model).

## Tests

Run the unit tests with:

```bash
python -m unittest
```

## Dashboard

An optional web dashboard exposes runtime metrics. Enable it via environment variables:

```bash
export ENABLE_DASHBOARD=true
export DASHBOARD_PORT=5000  # optional
```

Then start the agent normally and browse to `http://localhost:5000` (the port will
automatically increment if already in use).

Key API endpoints include `/api/healthz`, `/api/kpis`, `/api/positions` and
`/api/orders`. Basic authentication is available when `DASHBOARD_USERNAME` and
`DASHBOARD_PASSWORD` are set.

Run the dashboard tests with:

```bash
pytest -q tests/test_boot_agent_intact.py
pytest -q tests/test_dashboard_endpoints.py
pytest -q tests/test_trading_not_blocked.py
```

## Git configuration

Set up your Git identity to use the correct email for commits:

```bash
git config --global user.email "perraultsacha@gmail.com"
git config user.email "perraultsacha@gmail.com"
```

In Visual Studio Code you can update this via *Preferences: Open Settings (UI)*,
search for **git user email**, and enter `perraultsacha@gmail.com`. Alternatively
use the command palette (`Ctrl+Shift+P`) and select **Git: Set User Email**.

## Navigation Troubleshooting

If you cloned the repository but cannot `cd` into the folder, run the diagnostic scripts:

```bash
python3 fix_directory_navigation.py
# or
./find_project.sh
```

They will search for the `AI-Trader-v2` directory and give you the exact command to navigate to it.

