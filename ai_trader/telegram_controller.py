import asyncio
import logging
from datetime import datetime


class TelegramController:
    """Handle Telegram commands to control the agent."""

    def __init__(self, agent, notification_manager) -> None:
        self.agent = agent
        self.notification_manager = notification_manager
        self.authorized_users: list[str] = []
        self.logger = logging.getLogger(self.__class__.__name__)
        self.commands = {
            "/start": self.cmd_start_agent,
            "/stop": self.cmd_stop_agent,
            "/status": self.cmd_get_status,
            "/test": self.cmd_run_tests,
            "/balance": self.cmd_get_balance,
            "/positions": self.cmd_get_positions,
            "/restart": self.cmd_restart_agent,
            "/emergency": self.cmd_emergency_stop,
            "/help": self.cmd_show_help,
            "/config": self.cmd_show_config,
        }

    # ------------------------------------------------------------------
    def add_authorized_user(self, chat_id: str) -> None:
        if chat_id not in self.authorized_users:
            self.authorized_users.append(chat_id)

    def is_authorized(self, chat_id: str) -> bool:
        return chat_id in self.authorized_users or not self.authorized_users

    async def process_telegram_command(self, message_text: str, chat_id: str) -> bool:
        if not self.is_authorized(chat_id):
            await self.send_response("\u274c Non autorisé", chat_id)
            return False

        message_text = message_text.strip()
        command = message_text.split()[0].lower()

        if command in self.commands:
            try:
                await self.commands[command](message_text, chat_id)
                return True
            except Exception as exc:  # noqa: BLE001
                await self.send_response(f"\u274c Erreur commande: {exc}", chat_id)
                return False
        await self.send_response("\u2753 Commande inconnue. Tapez /help pour aide.", chat_id)
        return False

    # ------------------------------------------------------------------
    async def cmd_start_agent(self, message: str, chat_id: str) -> None:
        if getattr(self.agent, "is_running", False):
            await self.send_response("\u26a0\ufe0f Agent déjà en cours", chat_id)
            return

        await self.send_response("\ud83d\ude80 **Démarrage de l'agent...**", chat_id)
        try:
            success = await self.agent.start()
            if success:
                await self.send_response(
                    "\u2705 Agent démarré avec succès !", chat_id
                )
            else:
                await self.send_response("\u274c Échec du démarrage", chat_id)
        except Exception as exc:  # noqa: BLE001
            await self.send_response(f"\u274c Erreur démarrage: {exc}", chat_id)

    async def cmd_stop_agent(self, message: str, chat_id: str) -> None:
        if not getattr(self.agent, "is_running", False):
            await self.send_response("\u26a0\ufe0f Agent déjà arrêté", chat_id)
            return

        await self.send_response("\ud83d\udcdb **Arrêt de l'agent...**", chat_id)
        try:
            await self.agent.stop()
            await self.send_response("\u2705 Agent arrêté", chat_id)
        except Exception as exc:  # noqa: BLE001
            await self.send_response(f"\u274c Erreur arrêt: {exc}", chat_id)

    async def cmd_get_status(self, message: str, chat_id: str) -> None:
        try:
            status = "\U0001F7E2 ACTIF" if getattr(self.agent, "is_running", False) else "\U0001F534 ARRÊTÉ"
            balance = 0.0
            if hasattr(self.agent, "execution"):
                balance = await self.agent.execution.get_account_balance()
            open_positions = len(getattr(self.agent.risk_manager, "open_trades", []))

            uptime = ""
            if getattr(self.agent, "start_time", None):
                uptime_seconds = (datetime.utcnow() - self.agent.start_time).total_seconds()
                uptime = f"{uptime_seconds//3600:.0f}h {(uptime_seconds%3600)//60:.0f}m"

            response = (
                "\n\ud83d\udcca STATUS AGENT IA\n"
                f"\u26a1 Status : {status}\n"
                f"\ud83d\udcb0 Solde : {balance:.2f} USDT\n"
                f"\ud83d\udcc8 Positions ouvertes : {open_positions}\n"
                f"\u23f1 Uptime : {uptime}\n"
                f"\ud83d\udcca Derniere MAJ : {datetime.utcnow().strftime('%H:%M:%S')} UTC"
            )
            await self.send_response(response, chat_id)
        except Exception as exc:  # noqa: BLE001
            await self.send_response(f"\u274c Erreur récupération status: {exc}", chat_id)

    async def cmd_run_tests(self, message: str, chat_id: str) -> None:
        await self.send_response("\U0001F9EA **Lancement des tests...**", chat_id)
        try:
            await self.agent.run_diagnostic_tests()
        except Exception as exc:  # noqa: BLE001
            await self.send_response(f"\u274c Erreur tests: {exc}", chat_id)

    async def cmd_get_balance(self, message: str, chat_id: str) -> None:
        try:
            balance = await self.agent.execution.get_account_balance()
            margin_used = 0.0
            if hasattr(self.agent.execution, "get_margin_usage"):
                margin_used = await self.agent.execution.get_margin_usage()

            response = (
                "\n\ud83d\udcb0 SOLDE DU COMPTE\n"
                f"\ud83d\udcb5 Solde disponible : {balance:.2f} USDT\n"
                f"\ud83d\udcca Marge utilisée : {margin_used:.2f} USDT\n"
                f"\ud83c\udfaf Capital/trade (10%) : {balance * 0.1:.2f} USDT\n"
                "\u2699 Levier configuré : x10"
            )
            await self.send_response(response, chat_id)
        except Exception as exc:  # noqa: BLE001
            await self.send_response(f"\u274c Erreur solde: {exc}", chat_id)

    async def cmd_get_positions(self, message: str, chat_id: str) -> None:
        try:
            positions = getattr(self.agent.risk_manager, "open_trades", [])
            if not positions:
                await self.send_response("\ud83d\udcca **Aucune position ouverte**", chat_id)
                return
            response = f"\ud83d\udcc8 **POSITIONS OUVERTES** ({len(positions)})\n\n"
            for i, pos in enumerate(positions, 1):
                pnl = pos.get("unrealized_pnl", 0)
                emoji = "\U0001F7E2" if pnl >= 0 else "\U0001F534"
                response += (
                    f"Position #{i}\n"
                    f"{emoji} {pos.get('symbol', 'BTCUSDT')} | {pos.get('side', 'LONG')}\n"
                    f"\ud83d\udcb0 Taille : {pos.get('size', 0):.4f}\n"
                    f"\ud83d\udccc Prix entrée : {pos.get('entry_price', 0):.2f}\n"
                    f"\ud83d\udcca PnL : {pnl:.2f} USDT\n"
                )
            await self.send_response(response, chat_id)
        except Exception as exc:  # noqa: BLE001
            await self.send_response(f"\u274c Erreur positions: {exc}", chat_id)

    async def cmd_restart_agent(self, message: str, chat_id: str) -> None:
        await self.send_response("\ud83d\udd04 **Redémarrage de l'agent...**", chat_id)
        try:
            if getattr(self.agent, "is_running", False):
                await self.agent.stop()
                await asyncio.sleep(2)
            success = await self.agent.start()
            if success:
                await self.send_response("\u2705 Agent redémarré", chat_id)
            else:
                await self.send_response("\u274c Échec du redémarrage", chat_id)
        except Exception as exc:  # noqa: BLE001
            await self.send_response(f"\u274c Erreur redémarrage: {exc}", chat_id)

    async def cmd_emergency_stop(self, message: str, chat_id: str) -> None:
        await self.send_response("\ud83d\udea8 **ARRÊT D'URGENCE**", chat_id)
        try:
            await self.agent.emergency_stop()
            await self.send_response(
                "\n\u2705 Agent arrêté\n\u2705 Positions fermées", chat_id
            )
        except Exception as exc:  # noqa: BLE001
            await self.send_response(f"\u274c Erreur urgence: {exc}", chat_id)

    async def cmd_show_help(self, message: str, chat_id: str) -> None:
        help_text = (
            "\n\ud83e\udd16 COMMANDES DISPONIBLES\n"
            "* /start - Démarrer l'agent\n"
            "* /stop - Arrêter l'agent\n"
            "* /restart - Redémarrer l'agent\n"
            "* /emergency - Arrêt d'urgence\n"
            "* /status - Status de l'agent\n"
            "* /balance - Solde du compte\n"
            "* /positions - Positions ouvertes\n"
            "* /config - Configuration actuelle\n"
            "* /test - Lancer tests complets\n"
            "* /help - Cette aide"
        )
        await self.send_response(help_text, chat_id)

    async def cmd_show_config(self, message: str, chat_id: str) -> None:
        try:
            config = self.agent.config
            response = (
                "\n\u2699\ufe0f CONFIGURATION ACTUELLE\n"
                f"* Symbole : {config.get('bitget', {}).get('symbol', 'BTCUSDT')}\n"
                f"* Levier : x{config.get('bitget', {}).get('leverage', 10)}\n"
                f"* Capital/trade : {config.get('trading', {}).get('capital_per_position', 0.1)*100:.0f}%\n"
                f"* Max loss/trade : {config.get('risk', {}).get('max_loss_per_trade', 0.02)*100:.1f}%\n"
                f"* Max drawdown/jour : {config.get('risk', {}).get('max_daily_drawdown', 0.05)*100:.0f}%\n"
            )
            await self.send_response(response, chat_id)
        except Exception as exc:  # noqa: BLE001
            await self.send_response(f"\u274c Erreur config: {exc}", chat_id)

    # ------------------------------------------------------------------
    async def send_response(self, message: str, chat_id: str | None = None) -> None:
        try:
            if chat_id:
                await self.notification_manager._send_telegram_direct(message, chat_id)
            else:
                await self.notification_manager.notify("telegram_response", message)
        except Exception as exc:  # noqa: BLE001
            self.logger.error("Failed to send Telegram response: %s", exc)
