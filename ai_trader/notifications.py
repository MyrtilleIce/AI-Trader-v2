"""Notification utilities for ai_trader.

Provides a single :class:`NotificationManager` which can send messages through
several backends (CoinStats webhook, Telegram bot or email). The channel list is
configured via ``config.yaml`` and every call is rate limited to avoid spam.

This module is intentionally lightweight and can be extended with additional
providers (Slack, Discord...) in the future (see TODOs).
"""

from __future__ import annotations

import logging
import os
import smtplib
import time
from dataclasses import dataclass
import datetime as dt
from collections import defaultdict
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, Optional

import requests
import yaml


@dataclass
class ChannelConfig:
    """Configuration for a notification channel."""

    enabled: bool
    api_key: Optional[str] = None
    webhook_url: Optional[str] = None
    token: Optional[str] = None
    chat_id: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 0
    username: Optional[str] = None
    password: Optional[str] = None
    sender: Optional[str] = None
    recipient: Optional[str] = None


class NotificationManager:
    """Central notification dispatcher used across the project."""

    CONFIG_PATH = Path(os.getenv("CONFIG_FILE", "config.yaml"))

    def __init__(self) -> None:
        self.log = logging.getLogger(self.__class__.__name__)
        self.config = self._load_config()
        self.channels: Dict[str, ChannelConfig] = {}
        self._parse_channels()
        self.last_sent: Dict[str, float] = {}
        self.ratelimit = int(self.config.get("notifications", {})
                             .get("ratelimit", 60))

    # ------------------------------------------------------------------
    def _load_config(self) -> dict:
        if not self.CONFIG_PATH.exists():
            return {}
        try:
            with self.CONFIG_PATH.open("r", encoding="utf-8") as fh:
                return yaml.safe_load(fh) or {}
        except Exception as exc:  # pylint: disable=broad-except
            self.log.error("Failed to load config: %s", exc)
            return {}

    def _parse_channels(self) -> None:
        section = self.config.get("notifications", {}).get("channels", {})
        for name, cfg in section.items():
            self.channels[name] = ChannelConfig(
                enabled=cfg.get("enabled", False),
                api_key=cfg.get("api_key"),
                webhook_url=cfg.get("webhook_url"),
                token=cfg.get("token"),
                chat_id=cfg.get("chat_id"),
                smtp_host=cfg.get("smtp_host"),
                smtp_port=int(cfg.get("smtp_port", 0)),
                username=cfg.get("username"),
                password=cfg.get("password"),
                sender=cfg.get("from"),
                recipient=cfg.get("to"),
            )

    # ------------------------------------------------------------------
    def _should_skip(self, event: str) -> bool:
        now = time.time()
        last = self.last_sent.get(event)
        if last and now - last < self.ratelimit:
            return True
        self.last_sent[event] = now
        return False

    # ------------------------------------------------------------------
    def notify(self, event: str, message: str, level: str = "INFO", **kwargs) -> None:
        """Send a notification for ``event`` with ``message``.

        Parameters
        ----------
        event : str
            Unique identifier of the event type used for rate limiting.
        message : str
            Text message to send.
        level : str, optional
            Severity level (``INFO``, ``WARNING`` or ``CRITICAL``).
        """

        if self._should_skip(event):
            return

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{level}] {timestamp} - {message}"
        tg_msg = self._format_telegram_message(event, message, level=level, **kwargs)

        sent = False
        if self.channels.get("coinstats") and self.channels["coinstats"].enabled:
            sent |= self._send_coinstats(msg)
        if self.channels.get("telegram") and self.channels["telegram"].enabled:
            sent |= self._send_telegram(tg_msg)
        if self.channels.get("email") and self.channels["email"].enabled:
            sent |= self._send_email(msg)

        if not sent:
            self.log.log(getattr(logging, level, logging.INFO), msg)

    # ------------------------------------------------------------------
    def _format_telegram_message(self, event: str, message: str, **kwargs) -> str:
        """Return a nicely formatted Telegram message."""
        now = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        data = defaultdict(str, kwargs)
        data.setdefault("datetime", now)
        # round numeric values
        for key in ["entry_price", "stop_loss", "take_profit", "pnl", "pnl_pct", "drawdown_pct", "winrate", "max_dd"]:
            if key in data and data[key] != "":
                try:
                    data[key] = f"{float(data[key]):.2f}"
                except (ValueError, TypeError):
                    pass
        if "size" in data and data["size"] != "":
            try:
                data["size"] = f"{float(data['size']):.4f}"
            except (ValueError, TypeError):
                pass
        if "error" in data:
            data["error"] = str(data["error"])[:500]

        templates = {
            "trade_opened": (
                "🚀 *Nouveau trade ouvert !*\n"
                "*Sens* : {side}\n"
                "*Taille* : {size} {symbol}\n"
                "*Prix d\u2019entr\xe9e* : {entry_price} USDT\n"
                "*SL* : {stop_loss} / *TP* : {take_profit}\n"
                "*Horodatage* : {datetime}"
            ),
            "trade_closed": (
                "✅ *Trade clôturé*\n"
                "*Sens* : {side} | *Résultat* : {pnl} USDT ({pnl_pct}% )\n"
                "*Durée* : {duration} min\n"
                "*Motif* : {reason}"
            ),
            "error": (
                "⚠️ *Erreur critique / API*\n"
                "_Description_ : {error}\n"
                "*Heure* : {datetime}"
            ),
            "drawdown": (
                "🛑 *Limite de perte journalière atteinte !*\n"
                "*Drawdown* : {drawdown_pct}%\n"
                "*Action* : Trading suspendu pour 24h." 
            ),
            "summary": (
                "📊 *Récapitulatif {period}*\n"
                "PnL total : {pnl} USDT\n"
                "Trades gagnants : {win} / perdants : {loss}\n"
                "Winrate : {winrate}%\n"
                "Max Drawdown : {max_dd}%"
            ),
        }

        # Map event names
        mapping = {
            "order_executed": "trade_opened",
            "trade_opened": "trade_opened",
            "trade_closed": "trade_closed",
            "trading_halt": "drawdown",
            "daily_summary": "summary",
            "api_failure": "error",
            "data_error": "error",
        }
        template_key = mapping.get(event)
        if not template_key:
            return f"*{event}*\n{message}"
        template = templates[template_key]
        data.setdefault("period", "journalier")
        data.setdefault("reason", message)
        return template.format_map(data)

    # ------------------------------------------------------------------
    def _send_coinstats(self, message: str) -> bool:
        cfg = self.channels.get("coinstats")
        if not cfg:
            return False
        url = cfg.webhook_url or "https://coinstats.app/webhook"
        payload = {"alert": message}
        headers = {"X-API-KEY": cfg.api_key} if cfg.api_key else {}
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            response.raise_for_status()
            return True
        except Exception as exc:  # pylint: disable=broad-except
            self.log.error("CoinStats notification failed: %s", exc)
            return False

    def _send_telegram(self, message: str) -> bool:
        cfg = self.channels.get("telegram")
        if not cfg or not (cfg.token and cfg.chat_id):
            return False
        url = f"https://api.telegram.org/bot{cfg.token}/sendMessage"
        payload = {
            "chat_id": cfg.chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }
        try:
            response = requests.post(url, data=payload, timeout=5)
            response.raise_for_status()
            return True
        except Exception as exc:  # pylint: disable=broad-except
            self.log.error("Telegram notification failed: %s", exc)
            return False

    def _send_email(self, message: str) -> bool:
        cfg = self.channels.get("email")
        if not cfg or not (cfg.smtp_host and cfg.recipient):
            return False
        email = EmailMessage()
        email["From"] = cfg.sender or "trader@localhost"
        email["To"] = cfg.recipient
        email["Subject"] = "AI Trader Notification"
        email.set_content(message)
        try:
            with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port or 25, timeout=10) as s:
                if cfg.username and cfg.password:
                    s.starttls()
                    s.login(cfg.username, cfg.password)
                s.send_message(email)
            return True
        except Exception as exc:  # pylint: disable=broad-except
            self.log.error("Email notification failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # TODO: add Slack and Discord channels


# Singleton used by modules
NOTIFIER = NotificationManager()
