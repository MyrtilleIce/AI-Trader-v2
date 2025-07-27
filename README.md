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

## Git configuration

Set up your Git identity to use the correct email for commits:

```bash
git config --global user.email "perraultsacha@gmail.com"
git config user.email "perraultsacha@gmail.com"
```

In Visual Studio Code you can update this via *Preferences: Open Settings (UI)*,
search for **git user email**, and enter `perraultsacha@gmail.com`. Alternatively
use the command palette (`Ctrl+Shift+P`) and select **Git: Set User Email**.
