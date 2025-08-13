# AI Trader

Autonomous trading agent for Bitget Futures.

## Installation

```bash
# Core + dev (sans UI)
pip install -e .[dev]

# Avec dashboard
pip install -e .[dashboard,dev]

# ML (dans un venv dédié conseillé)
pip install -e .[ml]
```

Listez les dépendances privées éventuelles dans `requirements.private.txt` et installez-les manuellement.
Copiez ensuite `.env.example` vers `.env` et fournissez vos identifiants API, puis lancez l'agent :

```bash
python -m ai_trader.main
```

### Environment flags

The agent lazily imports heavy optional libraries based on ENV flags:

| Flag | Default | Purpose |
| ---- | ------- | ------- |
| `ENABLE_LEARNING` | `true` | Enable Keras/TensorFlow based models |
| `ENABLE_OPENAI` | `true` | Allow OpenAI powered research |
| `ENABLE_OPTUNA` | `true` | Enable Optuna optimisation |
| `ENABLE_METRICS_EXPORT` | `false` | Export Prometheus metrics |
| `ENABLE_DASHBOARD` | `false` | Start web dashboard |

Unset or set a flag to `false` to avoid importing the corresponding dependency.

Run a preflight check manually with:

```bash
python -m ai_trader.tools.preflight
```

### Python versions

TensorFlow may lag behind the latest Python releases. If problems occur with
Python 3.13 install, use Python 3.11 via `pyenv` and the supplied
`constraints-3.11.txt` file:

```bash
pip install -r requirements.txt -c constraints-3.11.txt
```

### Dependencies

| Category | Packages |
| -------- | -------- |
| Core | requests, pandas, numpy, python-dotenv |
| Dashboard (extra) | Flask, Flask-Cors, dash, dash-bootstrap-components, plotly, flask-socketio |
| Dev (extra) | pytest, pytest-cov, requests-mock |
| ML (extra) | keras, tensorflow |

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

You can also start the agent with the dashboard directly via the helper script:

```bash
python3 start_agent.py --enable-dashboard
```

Then browse to `http://localhost:5000` (the port will automatically increment if
already in use).

### API endpoints

All responses follow the JSON structure `{ "ok": bool, "data": ..., "error": null|{code,msg} }`.

| Endpoint | Description |
| -------- | ----------- |
| `GET /api/overview` | high level balances and stats |
| `GET /api/equity?window=1d|7d|30d|all` | equity curve |
| `GET /api/logs?level=info&limit=200` | recent log lines |
| `GET /api/positions` | open positions |
| `GET /api/kpis` | computed KPIs |
| `GET /api/signals` | recent AI signals |
| `GET /api/alerts` | alert notifications |
| `POST /api/control/<start|stop|pause|resume>` | publish control events |
| `POST /api/mode` | change mode (`backtest`, `paper`, `live`) |
| `POST /api/strategy` | switch trading strategy |
| `GET /api/export/trades.csv` | download trades |
| `GET /api/export/metrics.xlsx` | download metrics sheet |
| `GET /api/export/report.pdf` | download PDF report |

Example:

```bash
curl http://localhost:5000/api/overview
```

A screenshot of the overview and equity sections:

![dashboard screenshot](docs/dashboard_overview.png)

Run the test suite with:

```bash
pytest -q
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

