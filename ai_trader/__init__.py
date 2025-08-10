"""ai_trader package.

This module exposes the package version which is used by the dashboard
and the API endpoint ``/api/version``.
"""

from __future__ import annotations

__all__ = ["__version__"]

# Public version of the project. It is imported by the dashboard to report
# the running software revision. Update whenever a release is made.
__version__ = "0.1.0"


