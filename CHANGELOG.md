# Changelog

## Dashboard
- Introduced optional Flask dashboard with environment flag `ENABLE_DASHBOARD`.
- Added metrics service and REST endpoints (`/api/healthz`, `/api/version`, `/api/kpis`, etc.).
- Added tests ensuring dashboard integration does not block trading.
