from .base import *
import io
from utils.export_csv import export_expenses_csv, export_rules_csv, export_budgets_csv


# Load messages from YAML file using relative path
_current_dir = Path(__file__).parent
_messages_path = _current_dir / "messages" / "export.yaml"
with open(_messages_path, "r") as file:
    MESSAGES = yaml.safe_load(file)


@rollover_silent
async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /export [expenses|rules|budgets] [YYYY-MM]
    Defaults:
      /export -> expenses for current month
      /export rules
      /export budgets
      /export expenses 2025-12
    """
    user_id = update.effective_user.id
    args = get_args(update)

    kind = "expenses"
    m = month_key()

    if len(args) >= 1:
        kind = args[0].strip().lower()
    if len(args) >= 2:
        m = args[1].strip()

    if kind not in ("expenses", "rules", "budgets"):
        return await reply(update, context, MESSAGES["usage_export"])

    if kind == "expenses":
        if len(m) != 7 or m[4] != "-":
            return await reply(update, context, MESSAGES["invalid_month"])
        data = export_expenses_csv(user_id, m)
        filename = f"expenses_{m}.csv"
    elif kind == "rules":
        data = export_rules_csv(user_id)
        filename = "rules.csv"
    else:
        data = export_budgets_csv(user_id)
        filename = "budgets.csv"

    bio = io.BytesIO(data)
    bio.name = filename
    bio.seek(0)
    await reply_doc(
        update,
        context,
        InputFile(bio),
        caption=MESSAGES["export_caption"].format(filename=filename),
    )


@rollover_silent
async def backupdb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /backupdb
    Sends the raw SQLite database file. Contains ALL your data.
    """
    with open(DB_PATH, "rb") as f:
        await reply_doc(update, context, f, caption=MESSAGES["backup_caption"])
