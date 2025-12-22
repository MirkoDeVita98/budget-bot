from .base import *


# Load messages from YAML file using relative path
_current_dir = Path(__file__).parent
_messages_path = _current_dir / "messages" / "setup.yaml"
with open(_messages_path, "r") as file:
    MESSAGES = yaml.safe_load(file)


@rollover_silent
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await reply(
        update, context, MESSAGES["start_message"], parse_mode="Markdown"
    )


@rollover_silent
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start(update, context)
