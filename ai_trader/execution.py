"""Order execution module interacting with Bitget API."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

import requests
import aiohttp

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
                "trade_opened",
                "",
                level="INFO",
                side=side,
                size=size,
                symbol=symbol,
                entry_price=float(data["priceAvg"]),
                stop_loss=sl,
                take_profit=tp,
            )
        return data

    # ------------------------------------------------------------------
    async def _make_authenticated_request(
        self, method: str, endpoint: str, params: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Perform an authenticated HTTP request asynchronously."""

        url = f"{self.BASE_URL}{endpoint}"
        headers = self._headers(method, endpoint, "")

        async with aiohttp.ClientSession() as session:
            try:
                if method.upper() == "GET":
                    async with session.get(url, params=params, headers=headers, timeout=10) as resp:
                        return await resp.json()
                async with session.post(url, json=params, headers=headers, timeout=10) as resp:
                    return await resp.json()
            except Exception as exc:  # noqa: BLE001
                self.log.error("Async request failed: %s", exc)
                return {}

    # ------------------------------------------------------------------
    async def set_leverage_x10(self, symbol: str = "BTCUSDT") -> bool:
        """Configure leverage to 10x for the given symbol."""

        endpoint = "/api/v2/mix/account/set-leverage"
        params = {
            "symbol": symbol,
            "productType": "USDT-FUTURES",
            "marginCoin": "USDT",
            "leverage": "10",
            "holdSide": "long",
        }

        response = await self._make_authenticated_request("POST", endpoint, params)
        if response.get("code") == "00000":
            self.log.info("Leverage set to 10x for %s", symbol)
            NOTIFIER.notify("leverage_configured", f"✅ Levier configuré à 10x pour {symbol}")
            return True

        self.log.error("Failed to set leverage: %s", response)
        NOTIFIER.notify("leverage_error", f"❌ Erreur configuration levier: {response}")
        return False

    # ------------------------------------------------------------------
    async def verify_leverage_configuration(self, symbol: str = "BTCUSDT") -> bool:
        """Check if leverage is correctly set to 10x."""

        endpoint = "/api/v2/mix/account/account"
        params = {"symbol": symbol, "productType": "USDT-FUTURES", "marginCoin": "USDT"}

        response = await self._make_authenticated_request("GET", endpoint, params)
        if response.get("code") == "00000":
            leverage = response.get("data", {}).get("leverage", "1")
            if str(leverage) == "10":
                self.log.info("Leverage verification successful: %sx", leverage)
                return True
            self.log.warning("Leverage mismatch: expected 10x, got %sx", leverage)
            return False
        return False

    # ------------------------------------------------------------------
    def get_account_balance(self) -> float:
        """Wrapper to fetch account balance conveniently."""
        return self.available_balance("BTCUSDT")
