"""Main orchestration loop for the trading agent."""

from __future__ import annotations

import asyncio
import logging
import os
import time

from dotenv import load_dotenv

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
