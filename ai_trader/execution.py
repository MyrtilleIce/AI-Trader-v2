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

    # ------------------------------------------------------------------
    def _request(
        self, method: str, url: str, **kwargs
    ) -> Optional[requests.Response]:
        """Perform an HTTP request with basic retry logic."""
        for attempt in range(3):
            try:
                response = self.session.request(
                    method, url, timeout=10, **kwargs
                )
                response.raise_for_status()
                self._fail_count = 0
                return response
            except requests.RequestException as exc:  # noqa: BLE001
                self._fail_count += 1
                self.log.warning("API request failed (%s): %s", attempt + 1, exc)
                time.sleep(1)
        NOTIFIER.notify(
            "api_failure",
            "Repeated API failures while contacting Bitget",
            level="CRITICAL",
        )
        return None

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
        response = self._request("GET", url, headers=headers)
        if not response:
            return None
        data = response.json()
        self.log.debug("Account data: %s", data)
        return data.get("data", {})

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
        expected_price: float | None = None,
        risk_manager: Optional["RiskManager"] = None,
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
        response = self._request("POST", url, headers=headers, data=params)
        if not response:
            return None
        data = response.json()
        self.log.info("Order response: %s", data)
        if data.get("priceAvg"):
            if expected_price and risk_manager and not risk_manager.check_slippage(expected_price, float(data["priceAvg"])):
                NOTIFIER.notify("slippage_warning", "High slippage detected", level="WARNING")
            NOTIFIER.notify(
                "order_executed",
                f"Order executed avg price {data['priceAvg']}",
                level="INFO",
            )
        return data
