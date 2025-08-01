"""Persistent trade logging and performance tracking."""

from __future__ import annotations

import asyncio
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
            writer = csv.DictWriter(
                csvfile, fieldnames=["timestamp", "side", "price", "qty", "pnl"]
            )
            writer.writerow(info)
        self.log.info("Trade recorded: %s", info)

    async def async_record(self, info: Dict[str, float]) -> None:
        """Asynchronously append trade information to CSV."""
        await asyncio.to_thread(self.record, info)

    def load(self) -> List[Dict[str, str]]:
        with self.path.open() as csvfile:
            reader = csv.DictReader(csvfile)
            return list(reader)

    async def async_load(self) -> List[Dict[str, str]]:
        """Asynchronously load trade history."""
        return await asyncio.to_thread(self.load)

    # ------------------------------------------------------------------
    def send_daily_summary(self) -> None:
        """Compute daily PnL summary and send notification."""
        rows = self.load()
        if not rows:
            return
        pnl = sum(float(r["pnl"]) for r in rows)
        wins = sum(1 for r in rows if float(r["pnl"]) > 0)
        losses = sum(1 for r in rows if float(r["pnl"]) <= 0)
        winrate = (wins / len(rows)) * 100 if rows else 0
        NOTIFIER.notify(
            "daily_summary",
            f"Daily PnL: {pnl:.2f} across {len(rows)} trades",
            level="INFO",
            pnl=pnl,
            win=wins,
            loss=losses,
            winrate=winrate,
            max_dd=0,
            period="journalier",
        )
        # TODO: implement weekly summary with success rate and drawdown stats
