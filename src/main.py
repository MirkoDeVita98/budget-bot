from telegram.ext import Application, CommandHandler

from config import BOT_TOKEN
from db import init_db
from handlers import *


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Missing BOT_TOKEN in .env")

    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("h", help_command))
    app.add_handler(CommandHandler("setbudget", setbudget))
    app.add_handler(CommandHandler("sb", setbudget))
    app.add_handler(CommandHandler("setdaily", setdaily))
    app.add_handler(CommandHandler("sd", setdaily))
    app.add_handler(CommandHandler("setmonthly", setmonthly))
    app.add_handler(CommandHandler("sm", setmonthly))
    app.add_handler(CommandHandler("setyearly", setyearly))
    app.add_handler(CommandHandler("sy", setyearly))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("r", rules))
    app.add_handler(CommandHandler("delrule", delrule))
    app.add_handler(CommandHandler("dr", delrule))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("a", add))
    app.add_handler(CommandHandler("undo", undo))
    app.add_handler(CommandHandler("u", undo))
    app.add_handler(CommandHandler("expenses", expenses))
    app.add_handler(CommandHandler("e", expenses))
    app.add_handler(CommandHandler("delexpense", delexpense))
    app.add_handler(CommandHandler("d", delexpense))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("s", status))
    app.add_handler(CommandHandler("categories", categories))
    app.add_handler(CommandHandler("c", categories))
    app.add_handler(CommandHandler("month", month))
    app.add_handler(CommandHandler("m", month))
    app.add_handler(CommandHandler("export", export))
    app.add_handler(CommandHandler("backupdb", backupdb))
    app.add_handler(CommandHandler("resetmonth", resetmonth))
    app.add_handler(CommandHandler("rm", resetmonth))
    app.add_handler(CommandHandler("resetall", resetall))

    app.run_polling()


if __name__ == "__main__":
    main()
