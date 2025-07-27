"""Main orchestration loop for the trading agent."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
import yaml

from .ai_model import SimpleModel
from .data_handler import DataHandler
from .execution import BitgetExecution
from .learning import Researcher
from .memory import Memory
from .notifications import NOTIFIER
from .risk_manager import RiskManager
from .strategy import Strategy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("ai_trader/logs/agent.log"),
        logging.StreamHandler(),
    ],
)

load_dotenv()


async def perform_startup_checks(executor: BitgetExecution, config: dict) -> bool:
    """Run startup safety verifications before trading."""

    checks = {
        "api_connection": False,
        "leverage_configured": False,
        "balance_sufficient": False,
        "risk_parameters": False,
        "notifications_active": False,
    }

    try:
        balance = await asyncio.to_thread(executor.get_account_balance)
        checks["api_connection"] = balance is not None

        checks["leverage_configured"] = await executor.verify_leverage_configuration()
        if not checks["leverage_configured"]:
            await executor.set_leverage_x10()
            checks["leverage_configured"] = await executor.verify_leverage_configuration()

        if balance is not None:
            checks["balance_sufficient"] = balance >= 100
            if balance < 500:
                NOTIFIER.notify(
                    "low_balance_warning",
                    f"\u26a0\ufe0f Solde faible pour levier x10: {balance:.2f} USDT",
                )

        risk_cfg = config.get("risk", {})
        checks["risk_parameters"] = all(
            [
                risk_cfg.get("max_loss_per_trade", 0) <= 0.02,
                risk_cfg.get("liquidation_buffer", 0) >= 0.15,
                risk_cfg.get("leverage_monitoring", False),
            ]
        )

        NOTIFIER.notify("startup_check", "\ud83d\udd27 V\u00e9rifications de d\u00e9marrage en cours...")
        checks["notifications_active"] = True

        all_passed = all(checks.values())
        status_msg = "\u2705 Toutes les v\u00e9rifications pass\u00e9es" if all_passed else "\u274c Certaines v\u00e9rifications ont \u00e9chou\u00e9"

        NOTIFIER.notify(
            "startup_complete",
            f"\n\ud83d\ude80 Agent IA Pr\u00eat - Configuration Levier x10\n{status_msg}",
        )

        return all_passed

    except Exception as exc:  # noqa: BLE001
        NOTIFIER.notify("startup_error", f"\u274c Erreur lors des v\u00e9rifications: {exc}")
        return False


async def continuous_safety_monitoring(executor: BitgetExecution, risk: RiskManager) -> None:
    """Monitor open positions and alert on liquidation risks."""

    while True:
        try:
            for trade_id, info in risk.open_trades.items():
                current_price = await asyncio.to_thread(lambda: 0.0)
                liquidation_info = risk.calculate_liquidation_price(
                    current_price,
                    info.risk,
                    info.risk,
                    10,
                )
                distance_pct = abs(current_price - liquidation_info["liquidation_price"]) / max(current_price, 1) * 100
                if distance_pct < 10:
                    NOTIFIER.notify(
                        "liquidation_risk",
                        NOTIFIER._format_leverage_alert(
                            "liquidation_risk",
                            {
                                "current_price": current_price,
                                "liquidation_price": liquidation_info["liquidation_price"],
                                "distance": distance_pct,
                            },
                        ),
                    )
                elif distance_pct < 20:
                    NOTIFIER.notify(
                        "margin_warning",
                        NOTIFIER._format_leverage_alert(
                            "margin_warning",
                            {
                                "margin_used": (info.risk / max(risk.get_available_balance(), 1)) * 100,
                                "liquidation_distance": distance_pct,
                            },
                        ),
                    )
            await asyncio.sleep(30)
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).error("Error in safety monitoring: %s", exc)
            await asyncio.sleep(60)


async def run_bot(run_once: bool = True) -> None:
    """Run a single trading cycle when ``run_once`` is ``True``."""
    symbol = os.getenv("SYMBOL", "BTCUSDT")
    leverage = int(os.getenv("LEVERAGE", "10"))

    data_handler = DataHandler(symbol)
    strategy = Strategy()
    executor = BitgetExecution()
    risk = RiskManager(executor, symbol, leverage)
    memory = Memory()
    model = SimpleModel()
    researcher = Researcher()

    config_path = Path(os.getenv("CONFIG_FILE", "config.yaml"))
    config = yaml.safe_load(config_path.read_text()) if config_path.exists() else {}
    await perform_startup_checks(executor, config)
    asyncio.create_task(continuous_safety_monitoring(executor, risk))

    step = 0

    while True:
        step += 1
        df = await asyncio.to_thread(data_handler.fetch_candles)
        df = strategy.apply_indicators(df)
        signal = strategy.generate_signal(df)

        if signal:
            price = df.iloc[-1]["close"]
            sl, tp = risk.dynamic_sl_tp(price, signal)
            size = risk.position_size(price)
            logging.info("Calculated position size: %s", size)
            await asyncio.to_thread(
                executor.place_order,
                symbol,
                size,
                signal,
                sl=sl,
                tp=tp,
                leverage=leverage,
            )
            await memory.async_record(
                {
                    "timestamp": int(time.time()),
                    "side": signal,
                    "price": price,
                    "qty": size,
                    "pnl": 0.0,
                }
            )

        # optional learning
        if step % (60 * 24) == 0:  # once a day assuming loop every minute
            tips = await asyncio.to_thread(researcher.search, "crypto trading strategy")
            summary = await asyncio.to_thread(researcher.summarize, tips)
            logging.getLogger("Research").info("Daily summary: %s", summary)
            await asyncio.to_thread(memory.send_daily_summary)

        model.train(df)

        if run_once:
            break

        await asyncio.sleep(60)

    logging.info("Execution finished")
    NOTIFIER.notify("bot_stop", "Execution finished", level="INFO")


def main() -> None:
    """Entry point used when the module is executed as a script."""
    asyncio.run(run_bot(run_once=True))


if __name__ == "__main__":
    main()
