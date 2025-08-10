# Contributing

1. Bootstrap the development environment:
   ```bash
   scripts/bootstrap_dev.sh
   ```
2. Run preflight checks and tests before sending a PR:
   ```bash
   python -m ai_trader.tools.preflight
   pytest
   ```
3. Optional features must be protected by `ENABLE_*` flags so the core agent runs
   without those dependencies installed.
