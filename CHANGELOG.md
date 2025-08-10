# Changelog

## Dashboard
- Introduced optional Flask dashboard with environment flag `ENABLE_DASHBOARD`.
- Added metrics service and REST endpoints (`/api/healthz`, `/api/version`, `/api/kpis`, etc.).
- Added tests ensuring dashboard integration does not block trading.

## Compat & Deps Hardening
- Added NumPy 2 shim for pandas_ta and centralised in `ai_trader.compat`.
- Introduced lazy, flag-guarded imports for TensorFlow/Keras, OpenAI, Optuna and Prometheus.
- Added `scripts/bootstrap_dev.sh` and `ai_trader.tools.preflight` for cross-machine setup.
- Pinned requirements and provided `constraints-3.11.txt` for older Python environments.
