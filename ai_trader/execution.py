"""Order execution module interacting with Bitget API."""

from __future__ import annotations

import hmac
import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional

import requests
from dotenv import dotenv_values


class BitgetExecution:
    """Handle order execution and account interactions."""

    BASE_URL = "https://api.bitget.com/api/v2"

    def __init__(self, config_path: str = ".env") -> None:
        self.cfg = dotenv_values(config_path)
        self.session = requests.Session()
        self.log = logging.getLogger(self.__class__.__name__)

    # --- utility methods -------------------------------------------------
    def _sign(self, method: str, endpoint: str, params: str, timestamp: str) -> str:
        """Create Bitget signature."""
        message = timestamp + method.upper() + endpoint + params
        secret_key = self.cfg.get("BITGET_SECRET", "")
        return hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()

    def _headers(self, method: str, endpoint: str, params: str) -> Dict[str, str]:
        ts = str(int(time.time() * 1000))
        sign = self._sign(method, endpoint, params, ts)
        return {
            "ACCESS-KEY": self.cfg.get("BITGET_KEY", ""),
            "ACCESS-SIGN": sign,
            "ACCESS-TIMESTAMP": ts,
            "ACCESS-PASSPHRASE": self.cfg.get("BITGET_PASSPHRASE", ""),
            "Content-Type": "application/json",
        }

    # --- public API ------------------------------------------------------

    def get_account(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Return account information for a given symbol."""
        endpoint = "/api/mix/v1/account/account"
        params = f"symbol={symbol}&marginCoin=USDT"
        url = f"{self.BASE_URL}{endpoint}?{params}"
        headers = self._headers("GET", endpoint, params)
        try:
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.log.debug("Account data: %s", data)
            return data.get("data", {})
        except Exception as exc:  # pylint: disable=broad-except
            self.log.error("Account fetch failed: %s", exc)
            return None

    def available_balance(self, symbol: str) -> float:
        """Convenience method to get available USDT balance for a symbol."""
        account = self.get_account(symbol)
        if account is None:
            return 0.0
        try:
            return float(account.get("availableBalance", 0))
        except (TypeError, ValueError):
            return 0.0

    def place_order(
        self,
        symbol: str,
        size: float,
        side: str,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        leverage: int = 10,
    ) -> Optional[Dict[str, str]]:
        """Place a market order with optional SL/TP."""
        endpoint = "/api/mix/v1/order/place-order"
        url = f"{self.BASE_URL}{endpoint}"
        payload = {
            "symbol": symbol,
            "marginCoin": "USDT",
            "size": size,
            "side": side,
            "orderType": "market",
            "force": "gtc",
            "leverage": leverage,
        }
        if sl:
            payload["presetStopLossPrice"] = sl
        if tp:
            payload["presetTakeProfitPrice"] = tp
        params = json.dumps(payload)
        headers = self._headers("POST", endpoint, params)
        try:
            response = self.session.post(url, headers=headers, data=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.log.info("Order response: %s", data)
            return data
        except Exception as exc:  # pylint: disable=broad-except
            self.log.error("Order failed: %s", exc)
            return None

