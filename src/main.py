import logging
from telegram.ext import Application, CommandHandler
from telegram import Update
from telegram.ext import ContextTypes

from config import BOT_TOKEN
from db import init_db, shutdown_db_pool
from handlers.handlers_config import create_handlers_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress verbose logging from external libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Global error handler for unhandled exceptions.
    Logs the error and attempts to send a message to the user.
    """
    logger.error(
        f"Exception while handling an update:",
        exc_info=context.error,
    )
    
    # Try to send an error message to the user
    try:
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ An error occurred while processing your request. "
                     "The issue has been logged and our team will review it.\n\n"
                     "Please try again in a moment.",
            )
    except Exception as e:
        logger.error(f"Failed to send error message to user: {e}")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Missing BOT_TOKEN in .env")

    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # Add global error handler
    app.add_error_handler(error_handler)

    # Load and register all handlers from config
    handlers_config = create_handlers_config()
    
    for command_config in handlers_config.get_all_commands():
        # Register primary command
        app.add_handler(CommandHandler(command_config.primary_command, command_config.handler_function))
        
        # Register aliases
        if command_config.aliases:
            for alias in command_config.aliases:
                app.add_handler(CommandHandler(alias, command_config.handler_function))

    logger.info("🤖 Bot started successfully")
    try:
        app.run_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    finally:
        # Cleanup database connections on shutdown
        shutdown_db_pool()
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    main()
