# AI Trader

Example autonomous trading agent for Bitget Futures.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in API keys.
3. Run the agent:
   ```bash
 python -m ai_trader.main
  ```

Alternatively start the full stack with Postgres and Prometheus using Docker Compose:

```bash
docker-compose up
```

Logs and trade history are saved in `ai_trader/logs/`.

