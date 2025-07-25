"""Order execution module interacting with Bitget API."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

import requests

from .notifications import NOTIFIER

from .utils.security import auth_headers


class BitgetExecution:
    """Handle order execution and account interactions."""

    BASE_URL = "https://api.bitget.com/api/v2"

    def __init__(self) -> None:
        self.session = requests.Session()
        self.log = logging.getLogger(self.__class__.__name__)
        self._fail_count = 0

    # --- utility methods -------------------------------------------------
    @staticmethod
    def _headers(method: str, endpoint: str, params: str) -> Dict[str, str]:
        """Wrapper around :func:`auth_headers`."""
        return auth_headers(method, endpoint, params)

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
            self._fail_count = 0
            return data.get("data", {})
        except Exception as exc:  # pylint: disable=broad-except
            self.log.error("Account fetch failed: %s", exc)
            self._fail_count += 1
            if self._fail_count >= 3:
                NOTIFIER.notify(
                    "api_failure",
                    "Repeated API failures when fetching account data",
                    level="CRITICAL",
                )
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
            self._fail_count = 0
            if data.get("priceAvg"):
                NOTIFIER.notify(
                    "order_executed",
                    f"Order executed avg price {data['priceAvg']}",
                    level="INFO",
                )
            return data
        except Exception as exc:  # pylint: disable=broad-except
            self.log.error("Order failed: %s", exc)
            self._fail_count += 1
            if self._fail_count >= 3:
                NOTIFIER.notify(
                    "api_failure",
                    "Repeated API failures when placing orders",
                    level="CRITICAL",
                )
            return None
