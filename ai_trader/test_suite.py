import asyncio
import logging
from datetime import datetime
from typing import Dict


class AgentTestSuite:
    """Run comprehensive diagnostics for the trading agent."""

    def __init__(self, agent) -> None:
        self.agent = agent
        self.test_results: Dict[str, Dict] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    async def run_complete_test_suite(self) -> Dict[str, Dict]:
        """Run all critical tests and return a summary."""
        tests = [
            ("api_connection", self.test_api_connection),
            ("leverage_config", self.test_leverage_configuration),
            ("risk_calculations", self.test_risk_calculations),
            ("websocket_stream", self.test_websocket_connection),
            ("strategy_generation", self.test_strategy_generation),
            ("notification_system", self.test_notification_system),
            ("position_sizing", self.test_position_sizing),
            ("safety_monitoring", self.test_safety_monitoring),
            ("balance_verification", self.test_balance_verification),
            ("liquidation_protection", self.test_liquidation_protection),
        ]

        await self.agent.notify(
            "test_start",
            "\U0001F9EA **Démarrage Tests Complets**\nValidation de tous les modules...",
        )

        for test_name, test_func in tests:
            try:
                result = await test_func()
                self.test_results[test_name] = {
                    "passed": result,
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": f"Test {test_name} {'\u2705 PASSED' if result else '\u274c FAILED'}",
                }
                await asyncio.sleep(1)
            except Exception as exc:  # noqa: BLE001
                self.test_results[test_name] = {
                    "passed": False,
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(exc),
                    "details": f"Test {test_name} \u274c ERROR: {exc}",
                }

        await self.send_test_report()
        return self.test_results

    async def test_api_connection(self) -> bool:
        """Test API connectivity."""
        try:
            balance = await self.agent.execution.get_account_balance()
            return balance is not None and balance > 0
        except Exception:  # noqa: BLE001
            return False

    async def test_leverage_configuration(self) -> bool:
        """Verify leverage is correctly set."""
        try:
            return await self.agent.execution.verify_leverage_configuration()
        except Exception:  # noqa: BLE001
            return False

    async def test_risk_calculations(self) -> bool:
        """Check risk calculation logic."""
        try:
            entry_price = 50000.0
            stop_loss = 49000.0
            balance = 1000.0

            position_data = self.agent.risk_manager.calculate_position_size_with_leverage(
                entry_price, stop_loss, balance, 10
            )

            return (
                position_data["capital_allocated"] == balance * 0.1
                and position_data["leverage"] == 10
                and position_data["position_size"] > 0
            )
        except Exception:  # noqa: BLE001
            return False

    async def test_websocket_connection(self) -> bool:
        """Check that websocket connection exists."""
        try:
            if hasattr(self.agent, "websocket") and self.agent.websocket:
                return getattr(self.agent.websocket, "is_connected", False)
            return False
        except Exception:  # noqa: BLE001
            return False

    async def test_strategy_generation(self) -> bool:
        """Ensure the strategy can generate a signal."""
        try:
            mock_data = self.create_mock_market_data()
            signal = self.agent.strategy.generate_signal(mock_data)
            return signal is not None and "action" in signal
        except Exception:  # noqa: BLE001
            return False

    async def test_notification_system(self) -> bool:
        """Send a test notification."""
        try:
            await self.agent.notify("test_notification", "\U0001F9EA Test notification système")
            return True
        except Exception:  # noqa: BLE001
            return False

    async def test_position_sizing(self) -> bool:
        """Validate position sizing logic."""
        try:
            balance = await self.agent.execution.get_account_balance()
            if not balance:
                return False

            position_data = self.agent.risk_manager.calculate_position_size_with_leverage(
                50000.0, 49000.0, balance, 10
            )

            expected_capital = balance * 0.1
            return abs(position_data["capital_allocated"] - expected_capital) < 0.01
        except Exception:  # noqa: BLE001
            return False

    async def test_safety_monitoring(self) -> bool:
        """Verify liquidation price calculation."""
        try:
            liquidation_info = self.agent.risk_manager.calculate_liquidation_price(
                50000.0, 0.002, 100.0, 10, "long"
            )
            return liquidation_info["liquidation_price"] > 0
        except Exception:  # noqa: BLE001
            return False

    async def test_balance_verification(self) -> bool:
        """Ensure balance is sufficient for trading."""
        try:
            balance = await self.agent.execution.get_account_balance()
            return balance is not None and balance >= 100
        except Exception:  # noqa: BLE001
            return False

    async def test_liquidation_protection(self) -> bool:
        """Validate safety checks for a trade."""
        try:
            checks, _ = self.agent.risk_manager.validate_trade_safety(
                50000.0,
                49000.0,
                52000.0,
                {
                    "position_size": 0.002,
                    "required_margin": 100.0,
                    "leverage": 10,
                },
            )
            return "liquidation_distance" in checks
        except Exception:  # noqa: BLE001
            return False

    # ------------------------------------------------------------------
    def create_mock_market_data(self):
        """Return synthetic market data for strategy tests."""
        import pandas as pd
        import numpy as np

        dates = pd.date_range(start="2024-01-01", periods=100, freq="1H")
        prices = 50000 + np.random.randn(100).cumsum() * 100

        return pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices,
                "high": prices * 1.01,
                "low": prices * 0.99,
                "close": prices,
                "volume": np.random.randint(100, 1000, 100),
            }
        )

    async def send_test_report(self) -> None:
        """Send a summary report via the agent's notifier."""
        passed_tests = sum(1 for r in self.test_results.values() if r["passed"])
        total_tests = len(self.test_results)

        report = (
            f"\n\U0001F9EA RAPPORT DE TESTS COMPLET\n"
            f"\u2705 Tests réussis : {passed_tests}/{total_tests}\n"
            f"\ud83d\udcca Taux de réussite : {(passed_tests/total_tests)*100:.1f}%\n"
            f"Détails :"
        )

        for name, result in self.test_results.items():
            status = "\u2705 PASS" if result["passed"] else "\u274c FAIL"
            report += f"\n{status} `{name}`"
            if not result["passed"] and "error" in result:
                report += f"\n   \u2514\u2500 Error: {result['error'][:50]}..."

        report += (
            f"\nStatus Agent : {'\U0001F7E2 PRÊT POUR TRADING' if passed_tests == total_tests else '\U0001F534 CORRECTIONS REQUISES'}"
            f"\nTimestamp : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        )

        await self.agent.notify("test_complete", report)
