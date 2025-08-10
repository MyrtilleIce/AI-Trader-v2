"""Compatibility shims for NumPy 2.x breaking changes."""

from __future__ import annotations

import logging
import numpy as np

LOG = logging.getLogger("compat")


def ensure_numpy_compat() -> None:
    """Ensure deprecated NumPy attributes exist.

    NumPy 2 removed the ``np.NaN`` alias which ``pandas_ta`` expects.
    This shim reintroduces it when missing so downstream libraries
    continue to function without modification.
    """
    if not hasattr(np, "NaN"):
        LOG.debug("Adding np.NaN shim for numpy %s", np.__version__)
        np.NaN = np.nan  # type: ignore[attr-defined]
