"""Security helpers for Bitget API interactions."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Dict, Optional


def bitget_signature(
    method: str,
    endpoint: str,
    params: str,
    timestamp: str,
    secret: Optional[str] = None,
) -> str:
    """Return HMAC-SHA256 signature required by Bitget."""
    secret_key = secret or os.getenv("BITGET_SECRET", "")
    message = f"{timestamp}{method.upper()}{endpoint}{params}"
    return hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()


def auth_headers(
    method: str,
    endpoint: str,
    params: str = "",
    api_key: Optional[str] = None,
    passphrase: Optional[str] = None,
) -> Dict[str, str]:
    """Generate authentication headers for Bitget REST endpoints."""
    ts = str(int(time.time() * 1000))
    api_key = api_key or os.getenv("BITGET_KEY", "")
    passphrase = passphrase or os.getenv("BITGET_PASSPHRASE", "")
    sign = bitget_signature(method, endpoint, params, ts)
    return {
        "ACCESS-KEY": api_key,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": ts,
        "ACCESS-PASSPHRASE": passphrase,
        "Content-Type": "application/json",
    }
