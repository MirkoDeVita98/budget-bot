import logging
from functools import wraps
from pathlib import Path
from telegram import InputFile, Update
from telegram.ext import ContextTypes
from db.services import ensure_rollover_snapshot, month_key
from utils.textparse import parse_quoted_args
from config import BASE_CURRENCY, DB_PATH
import yaml

# Load messages from YAML files using relative path
_current_dir = Path(__file__).parent
_base_messages_path = _current_dir / "messages" / "base.yaml"

with open(_base_messages_path, "r") as file:
    MESSAGES = yaml.safe_load(file)

logger = logging.getLogger(__name__)


def get_args(update: Update):
    return parse_quoted_args(update.message.text if update.message else "")


async def reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    *,
    parse_mode: str | None = None,
    reply_markup=None,
):
    chat = update.effective_chat
    if update.message is not None:
        return await update.message.reply_text(
            text, parse_mode=parse_mode, reply_markup=reply_markup
        )
    if chat is not None:
        return await context.bot.send_message(
            chat_id=chat.id, text=text, parse_mode=parse_mode, reply_markup=reply_markup
        )
    return None


async def reply_doc(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    fileobj,
    *,
    filename: str | None = None,
    caption: str | None = None,
):
    chat = update.effective_chat

    if filename and not hasattr(fileobj, "name"):
        try:
            fileobj.name = filename
        except Exception:
            pass

    if update.message is not None:
        return await update.message.reply_document(document=fileobj, caption=caption)
    if chat is not None:
        return await context.bot.send_document(
            chat_id=chat.id, document=fileobj, caption=caption
        )
    return None


def _rollover_common(*, notify: bool):
    def decorator(fn):
        @wraps(fn)
        async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
        ):
            if update is None:
                return

            user = update.effective_user
            if user is not None:
                user_id = user.id
                current_month = month_key()

                created, snap_month = ensure_rollover_snapshot(user_id, current_month)
                if notify and created and snap_month:
                    await reply(
                        update,
                        context,
                        MESSAGES["snapshot_created"].format(snap_month=snap_month),
                        parse_mode="Markdown",
                    )

            return await fn(update, context, *args, **kwargs)

        return wrapper

    return decorator


def rollover_silent(fn):
    """Use for read-only commands: snapshots happen but no message is shown."""
    return _rollover_common(notify=False)(fn)


def rollover_notify(fn):
    """Use for write commands: snapshots happen and a message is shown once."""
    return _rollover_common(notify=True)(fn)
