"""Main orchestration loop for the trading agent."""

from __future__ import annotations

import logging
import os
import time

from dotenv import load_dotenv

from .ai_model import SimpleModel
from .data_handler import DataHandler
from .execution import BitgetExecution
from .learning import Researcher
from .memory import Memory
from .risk import RiskManager
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


def run_bot(run_once: bool = True) -> None:
    """Run one trading cycle unless ``run_once`` is ``False``."""
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
    # main loop - runs once when ``run_once`` is True for testing
    while True:
        step += 1
        df = data_handler.fetch_candles()
        df = strategy.apply_indicators(df)
        signal = strategy.generate_signal(df)

        if signal:
            price = df.iloc[-1]["close"]
            sl, tp = risk.dynamic_sl_tp(price, signal)
            size = risk.position_size(price)
            logging.info("Calculated position size: %s", size)
            executor.place_order(symbol, size, signal, sl=sl, tp=tp, leverage=leverage)
            memory.record({
                "timestamp": int(time.time()),
                "side": signal,
                "price": price,
                "qty": size,
                "pnl": 0.0,
            })

        # optional learning
        if step % (60 * 24) == 0:  # once a day assuming loop every minute
            tips = researcher.search("crypto trading strategy")
            summary = researcher.summarize(tips)
            logging.getLogger("Research").info("Daily summary: %s", summary)

        model.train(df)

        if run_once:
            break

        time.sleep(60)


    logging.info("Execution finished")


def main() -> None:
    """Entry point called when executed as a script."""
    run_bot(run_once=True)


if __name__ == "__main__":
    main()

