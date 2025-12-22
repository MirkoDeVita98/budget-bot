from telegram.ext import Application, CommandHandler

from config import BOT_TOKEN
from db import init_db, shutdown_db_pool
from handlers.handlers_config import create_handlers_config


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Missing BOT_TOKEN in .env")

    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # Load and register all handlers from config
    handlers_config = create_handlers_config()
    
    for command_config in handlers_config.get_all_commands():
        # Register primary command
        app.add_handler(CommandHandler(command_config.primary_command, command_config.handler_function))
        
        # Register aliases
        if command_config.aliases:
            for alias in command_config.aliases:
                app.add_handler(CommandHandler(alias, command_config.handler_function))

    try:
        app.run_polling()
    finally:
        # Cleanup database connections on shutdown
        shutdown_db_pool()


if __name__ == "__main__":
    main()
