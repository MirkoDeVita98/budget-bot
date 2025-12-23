from .base import *
from db.services import reset_month_expenses, delete_budget_for_month, reset_all_user_data


# Load messages from YAML file using relative path
_current_dir = Path(__file__).parent
_messages_path = _current_dir / "messages" / "reset.yaml"
with open(_messages_path, "r") as file:
    MESSAGES = yaml.safe_load(file)


@rollover_notify
async def resetmonth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /resetmonth [YYYY-MM]
    Deletes all expenses AND the overall budget for the given month.
    Examples:
      /resetmonth
      /resetmonth 2025-11
    """
    user_id = update.effective_user.id
    args = parse_quoted_args(update.message.text if update.message else "")

    m = month_key()
    if args:
        m = args[0].strip()

    if len(m) != 7 or m[4] != "-":
        return await reply(update, context, MESSAGES["usage_resetmonth"])

    n_exp = reset_month_expenses(user_id, m)
    n_budget = delete_budget_for_month(user_id, m)

    message = MESSAGES["resetmonth_summary"].format(
        month=m,
        deleted_expenses=n_exp,
        deleted_budget="yes" if n_budget else "no (not set)",
    )
    await reply(update, context, message)


@rollover_notify
async def resetall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = get_args(update)

    if not args or args[0].lower() != "yes":
        return await reply(update, context, MESSAGES["resetall_warning"])

    reset_all_user_data(user_id)
    await reply(update, context, MESSAGES["resetall_success"])
