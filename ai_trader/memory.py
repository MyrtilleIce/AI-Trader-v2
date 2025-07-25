"""Persistent trade logging and performance tracking."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Dict, List

from .notifications import NOTIFIER


class Memory:
    """Handle trade history storage."""

    def __init__(self, file_path: str = "ai_trader/logs/trades.csv") -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("timestamp,side,price,qty,pnl\n")
        self.log = logging.getLogger(self.__class__.__name__)

    def record(self, info: Dict[str, float]) -> None:
        """Append trade information to CSV."""
        with self.path.open("a", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["timestamp", "side", "price", "qty", "pnl"])
            writer.writerow(info)
        self.log.info("Trade recorded: %s", info)

    def load(self) -> List[Dict[str, str]]:
        with self.path.open() as csvfile:
            reader = csv.DictReader(csvfile)
            return list(reader)

    # ------------------------------------------------------------------
    def send_daily_summary(self) -> None:
        """Compute daily PnL summary and send notification."""
        rows = self.load()
        if not rows:
            return
        pnl = sum(float(r["pnl"]) for r in rows)
        NOTIFIER.notify(
            "daily_summary",
            f"Daily PnL: {pnl:.2f} across {len(rows)} trades",
            level="INFO",
        )
        # TODO: implement weekly summary with success rate and drawdown stats

