"""
Handler configuration system for the Telegram bot.

This module defines the command handlers and their aliases in a structured way,
making it easy to add, modify, or remove commands without touching main.py.
"""

from dataclasses import dataclass
from typing import Callable, Awaitable
from telegram import Update
from telegram.ext import ContextTypes


@dataclass
class CommandConfig:
    """Configuration for a single command handler."""
    
    primary_command: str
    handler_function: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]
    aliases: list[str] | None = None
    
    def get_all_commands(self) -> list[str]:
        """Return list of all command names (primary + aliases)."""
        commands = [self.primary_command]
        if self.aliases:
            commands.extend(self.aliases)
        return commands


class HandlersRegistry:
    """Registry to manage all command handlers."""
    
    def __init__(self):
        self.commands: list[CommandConfig] = []
    
    def register(
        self,
        primary_command: str,
        handler_function: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]],
        aliases: list[str] | None = None,
    ) -> None:
        """
        Register a new command handler.
        
        Args:
            primary_command: The main command name (without /)
            handler_function: The async function to handle the command
            aliases: Optional list of command aliases
        """
        config = CommandConfig(
            primary_command=primary_command,
            handler_function=handler_function,
            aliases=aliases,
        )
        self.commands.append(config)
    
    def get_all_commands(self) -> list[CommandConfig]:
        """Get all registered command configurations."""
        return self.commands
    
    def get_command(self, command_name: str) -> CommandConfig | None:
        """Get a specific command configuration by name."""
        for config in self.commands:
            if command_name == config.primary_command or (
                config.aliases and command_name in config.aliases
            ):
                return config
        return None


def create_handlers_config() -> HandlersRegistry:
    """
    Create and return the handlers configuration.
    
    This function imports all handler functions and registers them.
    Modify this function to add, remove, or reconfigure handlers.
    """
    from handlers import (
        start,
        help_command,
        setbudget,
        setdaily,
        setmonthly,
        setyearly,
        rules,
        delrule,
        add,
        undo,
        expenses,
        delexpense,
        status,
        categories,
        export,
        backupdb,
        resetmonth,
        resetall,
    )
    
    registry = HandlersRegistry()
    
    # Setup commands
    registry.register("start", start)
    registry.register("help", help_command, aliases=["h"])
    
    # Budget & Rules commands
    registry.register("setbudget", setbudget, aliases=["sb"])
    registry.register("setdaily", setdaily, aliases=["sd"])
    registry.register("setmonthly", setmonthly, aliases=["sm"])
    registry.register("setyearly", setyearly, aliases=["sy"])
    registry.register("rules", rules, aliases=["r"])
    registry.register("delrule", delrule, aliases=["dr"])
    
    # Status & Report commands
    registry.register("status", status, aliases=["s", "m"])
    registry.register("categories", categories, aliases=["c"])
    
    # Expenses commands
    registry.register("add", add, aliases=["a"])
    registry.register("undo", undo, aliases=["u"])
    registry.register("expenses", expenses, aliases=["e"])
    registry.register("delexpense", delexpense, aliases=["d"])
    
    # Export and backup commands
    registry.register("export", export)
    registry.register("backupdb", backupdb)
    
    # Reset commands
    registry.register("resetmonth", resetmonth, aliases=["rm"])
    registry.register("resetall", resetall)
    
    return registry
