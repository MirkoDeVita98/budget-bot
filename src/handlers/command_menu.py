"""
Command menu handler for setting up Telegram's native command menu.

This module uses setMyCommands to register commands with Telegram,
which displays them in the native command UI when users type '/'.
"""

import logging
from telegram import BotCommand
from telegram.ext import Application

from handlers.handlers_config import create_handlers_config

logger = logging.getLogger(__name__)


def _get_command_descriptions() -> dict[str, str]:
    """
    Build a dictionary of command descriptions.
    Maps command names to their user-friendly descriptions.
    """
    descriptions = {
        "start": "🚀 Begin using the bot",
        "help": "❓ Show this command menu",
        "setbudget": "💰 Set your monthly budget",
        "setdaily": "☀️ Add a daily spending rule",
        "setweekly": "📆 Add a weekly spending rule",
        "setmonthly": "📅 Add a monthly spending rule",
        "setyearly": "📊 Add a yearly spending rule",
        "rules": "📋 List all your spending rules",
        "delrule": "🗑️ Delete a spending rule",
        "status": "📈 View budget summary & spending",
        "categories": "🏷️ List all expense categories",
        "add": "➕ Record a new expense",
        "undo": "↩️ Undo the last expense",
        "expenses": "📝 List expenses by category",
        "delexpense": "❌ Delete an expense",
        "export": "📥 Export expenses, rules, or budgets",
        "backupdb": "💾 Backup your database",
        "resetmonth": "🔄 Clear current month data",
        "resetall": "⚠️ Delete all data",
    }
    return descriptions


async def setup_command_menu(app: Application) -> None:
    """
    Register all bot commands with Telegram using setMyCommands.

    This displays the native command menu when users type '/' in the chat.
    Should be called when the bot starts up.
    """
    try:
        handlers_config = create_handlers_config()
        descriptions = _get_command_descriptions()

        # Build list of BotCommand objects
        commands = []
        for config in handlers_config.get_all_commands():
            description = descriptions.get(config.primary_command, "")
            if description:
                description = description[:100]  # Telegram max is 256 but keep shorter

            commands.append(
                BotCommand(
                    command=config.primary_command,
                    description=description or "Execute this command",
                )
            )

        # Set commands via Telegram API
        await app.bot.set_my_commands(commands)
        logger.info(f"✅ Registered {len(commands)} commands with Telegram")

    except Exception as e:
        logger.error(f"❌ Failed to setup command menu: {e}")
