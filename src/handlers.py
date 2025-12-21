import io
from telegram import Update
from telegram.ext import ContextTypes
from telegram import InputFile
from alerts import check_alerts_after_add
from export_csv import export_expenses_csv, export_rules_csv, export_budgets_csv

from config import BASE_CURRENCY
from services import (
    month_key,
    parse_amount,
    looks_like_currency,
    upsert_budget,
    get_month_budget,
    add_rule,
    list_rules,
    delete_rule,
    compute_planned_monthly_from_rules,
    compute_spent_this_month,
    add_monthly_rule_named_fx,
    add_expense_optional_fx,
    delete_last_expense,
    reset_month_expenses,
    reset_all_user_data,
    list_expenses,
    delete_expense_by_id,
    ensure_month_budget,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💸 Budget Bot\n\n"
        "Setup:\n"
        "/setbudget <amount>\n"
        "/setdaily <category> <amount_per_day>\n"
        "/setmonthly <category> <amount>\n"
        "/setmonthly <name> <amount> [currency] <category>\n"
        "/setyearly <name> <amount_per_year> [category]\n"
        "/rules\n"
        "/delrule <id>\n\n"
        "Spending:\n"
        "/add <category> <name> <amount> [currency]\n"
        "/expenses [YYYY-MM] [limit]\n"
        "/delexpense <id>\n"
        "/undo\n\n"
        "Reports:\n"
        "/status [category]\n"
        "/month YYYY-MM\n\n"
        "Export and Backup:\n"
        "/export [expenses|rules|budgets] [YYYY-MM]\n"
        "/backupdb\n"
        "Maintenance:\n"
        "/resetmonth\n"
        "/resetall yes\n\n"
        "Help:\n"
        "/help"
    )


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start(update, context)


async def setbudget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("Usage: /setbudget <amount>")
    try:
        amount = parse_amount(context.args[0])
    except Exception:
        return await update.message.reply_text(
            "Couldn't parse amount. Example: /setbudget 2500"
        )

    m = month_key()
    upsert_budget(user_id, m, amount)
    await update.message.reply_text(
        f"✅ Set budget for {m}: {amount:.2f} {BASE_CURRENCY}"
    )


async def setdaily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) < 2:
        return await update.message.reply_text(
            "Usage: /setdaily <category> <amount_per_day>\nExample: /setdaily Food 15"
        )
    category = context.args[0].strip()
    try:
        amt = parse_amount(context.args[1])
    except Exception:
        return await update.message.reply_text(
            "Couldn't parse amount. Example: /setdaily Food 15"
        )

    add_rule(user_id, category, f"{category} daily", "daily", amt)
    await update.message.reply_text(
        f"✅ Daily rule added: {category} = {amt:.2f} {BASE_CURRENCY}/day"
    )


async def setyearly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) < 2:
        return await update.message.reply_text(
            "Usage: /setyearly <name> <amount_per_year> [category]"
        )
    name = context.args[0].strip()
    try:
        amt = parse_amount(context.args[1])
    except Exception:
        return await update.message.reply_text(
            "Couldn't parse amount. Example: /setyearly CarInsurance 600"
        )

    category = context.args[2].strip() if len(context.args) >= 3 else "Yearly"
    add_rule(user_id, category, name, "yearly", amt)
    await update.message.reply_text(
        f"✅ Yearly rule added: {name} ({category}) = {amt:.2f} {BASE_CURRENCY}/year (→ {amt/12:.2f}/month)"
    )


async def setmonthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Supports:
    1) /setmonthly <category> <amount>
    2) /setmonthly <name> <amount> [currency] <category>
       Example: /setmonthly PSN 16.99 EUR Subscription
    """
    user_id = update.effective_user.id
    args = context.args
    if len(args) < 2:
        return await update.message.reply_text(
            "Usage:\n"
            "1) /setmonthly <category> <amount>\n"
            "2) /setmonthly <name> <amount> [currency] <category>\n"
            "Example: /setmonthly PSN 16.99 EUR Subscription"
        )

    # Legacy mode
    if len(args) == 2:
        category = args[0].strip()
        try:
            amt = parse_amount(args[1])
        except Exception:
            return await update.message.reply_text(
                "Couldn't parse amount. Example: /setmonthly Subscriptions 35"
            )
        add_rule(user_id, category, f"{category} monthly", "monthly", amt)
        return await update.message.reply_text(
            f"✅ Monthly rule added: {category} = {amt:.2f} {BASE_CURRENCY}/month"
        )

    # New mode: last token is category, optional currency before it
    category = args[-1].strip()
    currency = BASE_CURRENCY
    amount_index = -2

    if len(args) >= 4 and looks_like_currency(args[-2]):
        currency = args[-2].strip().upper()
        amount_index = -3

    try:
        amount = parse_amount(args[amount_index])
    except Exception:
        return await update.message.reply_text(
            "Couldn't parse amount. Example: /setmonthly PSN 16.99 EUR Subscription"
        )

    rule_name = " ".join(args[:amount_index]).strip() or "(no name)"

    fx_date, rate, chf_monthly = await add_monthly_rule_named_fx(
        user_id, rule_name, amount, currency, category
    )

    if currency == BASE_CURRENCY:
        await update.message.reply_text(
            f"✅ Monthly rule added: [{category}] {rule_name} = {chf_monthly:.2f} {BASE_CURRENCY}/month"
        )
    else:
        await update.message.reply_text(
            f"✅ Monthly rule added: [{category}] {rule_name}\n"
            f"{amount:.2f} {currency}/month → {chf_monthly:.2f} {BASE_CURRENCY}/month (rate {rate:.6f}, {fx_date})"
        )


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    rows = list_rules(user_id)
    if not rows:
        return await update.message.reply_text("No rules yet.")
    lines = ["📌 Rules (stored in CHF):"]
    for r in rows:
        lines.append(
            f"- ID {r['id']}: [{r['category']}] {r['name']} — {float(r['amount']):.2f} CHF / {r['period']}"
        )
    lines.append("\nDelete one with: /delrule <id>")
    await update.message.reply_text("\n".join(lines))


async def delrule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("Usage: /delrule <id>")
    try:
        rid = int(context.args[0])
    except Exception:
        return await update.message.reply_text("Rule id must be an integer.")
    ok = delete_rule(user_id, rid)
    await update.message.reply_text("🗑️ Rule deleted." if ok else "⚠️ Rule not found.")


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /add <category> <name> <amount> [currency]
    Examples:
      /add Food Groceries 62.40
      /add Travel Taxi 20 EUR
    """
    user_id = update.effective_user.id
    args = context.args
    if len(args) < 3:
        return await update.message.reply_text(
            "Usage: /add <category> <name> <amount> [currency]"
        )

    category = args[0].strip()
    m = month_key()

    # -------- Parse amount/name/currency --------
    # Try last token as amount => CHF
    try:
        amount = parse_amount(args[-1])
        currency = BASE_CURRENCY
        name = " ".join(args[1:-1]).strip() or "(no name)"
    except Exception:
        # Last token must be currency, second last is amount
        if len(args) < 4:
            return await update.message.reply_text(
                "Usage: /add <category> <name> <amount> [currency]\nExample: /add Travel Taxi 20 EUR"
            )

        currency = args[-1].strip().upper()
        if not looks_like_currency(currency):
            return await update.message.reply_text(
                "Currency must be a 3-letter code (EUR, USD, ...)."
            )

        try:
            amount = parse_amount(args[-2])
        except Exception:
            return await update.message.reply_text(
                "Couldn't parse amount. Example: /add Travel Taxi 20 EUR"
            )

        name = " ".join(args[1:-2]).strip() or "(no name)"

    # -------- BEFORE insert: capture baseline for alert crossings --------
    planned_by_cat, planned_total = compute_planned_monthly_from_rules(user_id, m)

    # ensure budget exists (auto-carry) so overall alerts work
    overall_budget, carried, carried_from = ensure_month_budget(user_id, m)

    prev_spent_by_cat, prev_spent_total = compute_spent_this_month(user_id, m)

    # -------- Insert expense (with optional FX conversion) --------
    fx_date, rate, chf_amount = await add_expense_optional_fx(
        user_id, category, name, amount, currency, m
    )

    # -------- AFTER insert: recompute spent --------
    new_spent_by_cat, new_spent_total = compute_spent_this_month(user_id, m)

    # -------- Alerts (category + overall crossing) --------
    alert_result = check_alerts_after_add(
        category=category,
        prev_planned_by_cat=planned_by_cat,
        prev_spent_by_cat=prev_spent_by_cat,
        new_spent_by_cat=new_spent_by_cat,
        budget=overall_budget,  # can be None if never set any budget
        planned_total=planned_total,
        new_planned_by_cat=planned_by_cat,  # planned doesn't change on add
    )

    # -------- Confirmation message --------
    if currency == BASE_CURRENCY:
        await update.message.reply_text(
            f"✅ Added: [{category}] {name} = {chf_amount:.2f} {BASE_CURRENCY}"
        )
    else:
        await update.message.reply_text(
            f"✅ Added: [{category}] {name}\n"
            f"{amount:.2f} {currency} → {chf_amount:.2f} {BASE_CURRENCY} (rate {rate:.6f}, {fx_date})"
        )

    # -------- Send alerts after confirmation (Markdown enabled) --------
    for msg in alert_result.messages:
        await update.message.reply_text(msg, parse_mode="Markdown")


async def undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    m = month_key()
    row = delete_last_expense(user_id, m)
    if not row:
        return await update.message.reply_text("Nothing to undo this month.")

    cur = row["currency"]
    orig = float(row["original_amount"])
    chf = float(row["chf_amount"])
    if cur == BASE_CURRENCY:
        await update.message.reply_text(
            f"↩️ Undid: [{row['category']}] {row['name']} = {chf:.2f} {BASE_CURRENCY}"
        )
    else:
        await update.message.reply_text(
            f"↩️ Undid: [{row['category']}] {row['name']} = {orig:.2f} {cur} (was {chf:.2f} {BASE_CURRENCY})"
        )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    m = month_key()

    overall_budget, carried, carried_from = ensure_month_budget(user_id, m)

    if overall_budget is None:
        return await update.message.reply_text(
            f"📅 {m}\nNo overall budget set. Use /setbudget <amount>"
        )

    planned_by_cat, planned_total = compute_planned_monthly_from_rules(user_id, m)
    spent_by_cat, spent_total = compute_spent_this_month(user_id, m)

    # Optional: /status Food
    if context.args:
        cat = " ".join(context.args).strip()
        planned = planned_by_cat.get(cat, 0.0)
        spent = spent_by_cat.get(cat, 0.0)
        remaining = planned - spent  # can go negative
        return await update.message.reply_text(
            f"📅 {m} — Category: {cat}\n"
            f"Planned: {planned:.2f} {BASE_CURRENCY}\n"
            f"Spent: -{spent:.2f} {BASE_CURRENCY}\n"
            f"Remaining (category): {remaining:.2f} {BASE_CURRENCY}"
        )

    # category-aware overspend (includes unplanned categories)
    all_cats = set(planned_by_cat.keys()) | set(spent_by_cat.keys())
    overspend_total = 0.0
    for c in all_cats:
        p = planned_by_cat.get(c, 0.0)
        s = spent_by_cat.get(c, 0.0)
        overspend_total += max(0.0, s - p)

    remaining_overall = overall_budget - planned_total - overspend_total

    # Nice extra: explicitly show unplanned spend amount
    unplanned_spent = sum(
        spent_by_cat.get(c, 0.0)
        for c in spent_by_cat.keys()
        if planned_by_cat.get(c, 0.0) == 0.0
    )

    cats_sorted = sorted(all_cats)
    lines = [
        f"📅 {m}",
    ]

    if carried:
        lines.append(
            f"ℹ️ Budget auto-carried from {carried_from}: {overall_budget:.2f} {BASE_CURRENCY}"
        )

    lines += [
        f"Overall budget: {overall_budget:.2f} {BASE_CURRENCY}",
        f"Reserved (planned rules): -{planned_total:.2f} {BASE_CURRENCY}",
        f"Spent (entered): -{spent_total:.2f} {BASE_CURRENCY}",
        f"Unplanned spend: -{unplanned_spent:.2f} {BASE_CURRENCY}",
        f"Overspend vs plan: -{overspend_total:.2f} {BASE_CURRENCY}",
        "——————————",
        f"Remaining overall: {remaining_overall:.2f} {BASE_CURRENCY}",
        "",
        "By category (planned → spent → remaining):",
    ]

    if not cats_sorted:
        lines.append("(no categories yet)")
    else:
        for c in cats_sorted:
            p = planned_by_cat.get(c, 0.0)
            s = spent_by_cat.get(c, 0.0)
            lines.append(f"- {c}: {p:.2f} → {s:.2f} → {(p - s):.2f} {BASE_CURRENCY}")

    await update.message.reply_text("\n".join(lines))


async def month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        return await update.message.reply_text(
            "Usage: /month YYYY-MM (example: /month 2025-12)"
        )

    m = context.args[0].strip()
    if len(m) != 7 or m[4] != "-":
        return await update.message.reply_text(
            "Usage: /month YYYY-MM (example: /month 2025-12)"
        )

    overall_budget, carried, carried_from = ensure_month_budget(user_id, m)

    if overall_budget is None:
        return await update.message.reply_text(
            f"📅 {m}\nNo overall budget set for this month."
        )

    planned_by_cat, planned_total = compute_planned_monthly_from_rules(user_id, m)
    spent_by_cat, spent_total = compute_spent_this_month(user_id, m)

    # category-aware overspend (includes unplanned categories)
    all_cats = set(planned_by_cat.keys()) | set(spent_by_cat.keys())
    overspend_total = 0.0
    for c in all_cats:
        p = planned_by_cat.get(c, 0.0)
        s = spent_by_cat.get(c, 0.0)
        overspend_total += max(0.0, s - p)

    remaining_overall = overall_budget - planned_total - overspend_total

    unplanned_spent = sum(
        spent_by_cat.get(c, 0.0)
        for c in spent_by_cat.keys()
        if planned_by_cat.get(c, 0.0) == 0.0
    )

    msg = [
        f"📅 {m}",
    ]
    if carried:
        msg.append(
            f"ℹ️ Budget auto-carried from {carried_from}: {overall_budget:.2f} {BASE_CURRENCY}"
        )

    msg += [
        f"Overall budget: {overall_budget:.2f} {BASE_CURRENCY}",
        f"Reserved (planned rules): -{planned_total:.2f} {BASE_CURRENCY}",
        f"Spent: -{spent_total:.2f} {BASE_CURRENCY}",
        f"Unplanned spend: -{unplanned_spent:.2f} {BASE_CURRENCY}",
        f"Overspend vs plan: -{overspend_total:.2f} {BASE_CURRENCY}",
        f"Remaining: {remaining_overall:.2f} {BASE_CURRENCY}",
    ]

    await update.message.reply_text("\n".join(msg))


async def resetmonth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    m = month_key()
    n = reset_month_expenses(user_id, m)
    await update.message.reply_text(f"🧹 Deleted {n} expenses for {m}.")


async def resetall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args or context.args[0].lower() != "yes":
        return await update.message.reply_text(
            "⚠️ This will DELETE ALL your data.\nRun: /resetall yes"
        )
    reset_all_user_data(user_id)
    await update.message.reply_text("🧨 All your budget data has been reset.")


async def expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /expenses [YYYY-MM] [limit]
    Examples:
      /expenses
      /expenses 2025-12
      /expenses 2025-12 100
    """
    user_id = update.effective_user.id

    # defaults
    m = month_key()
    limit = 50

    if len(context.args) >= 1:
        m = context.args[0].strip()
    if len(context.args) >= 2:
        try:
            limit = int(context.args[1])
        except Exception:
            return await update.message.reply_text(
                "Limit must be an integer. Example: /expenses 2025-12 50"
            )

    # basic validation for month format
    if len(m) != 7 or m[4] != "-":
        return await update.message.reply_text(
            "Usage: /expenses [YYYY-MM] [limit]\nExample: /expenses 2025-12 50"
        )

    rows = list_expenses(user_id, m, limit=limit)
    if not rows:
        return await update.message.reply_text(f"No expenses for {m}.")

    lines = [f"🧾 Expenses for {m} (latest {min(limit, len(rows))}):"]
    for r in rows:
        eid = r["id"]
        cat = r["category"]
        name = r["name"]
        cur = r["currency"]
        orig = float(r["original_amount"])
        chf = float(r["chf_amount"])
        created = (r["created_at"] or "")[:19].replace("T", " ")

        if cur == BASE_CURRENCY:
            lines.append(f"- ID {eid}: [{cat}] {name} — {chf:.2f} CHF ({created})")
        else:
            lines.append(
                f"- ID {eid}: [{cat}] {name} — {orig:.2f} {cur} → {chf:.2f} CHF ({created})"
            )

    lines.append("\nDelete one with:")
    lines.append("/delexpense <id>")

    await update.message.reply_text("\n".join(lines))


async def delexpense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /delexpense <id>
    """
    user_id = update.effective_user.id
    if not context.args:
        return await update.message.reply_text(
            "Usage: /delexpense <id>\nTip: use /expenses to see IDs."
        )

    try:
        eid = int(context.args[0])
    except Exception:
        return await update.message.reply_text(
            "Expense id must be an integer. Example: /delexpense 42"
        )

    ok = delete_expense_by_id(user_id, eid)
    await update.message.reply_text(
        "🗑️ Expense deleted." if ok else "⚠️ Expense not found (or not yours)."
    )


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

    kind = "expenses"
    m = month_key()

    if len(context.args) >= 1:
        kind = context.args[0].strip().lower()

    if len(context.args) >= 2:
        m = context.args[1].strip()

    if kind not in ("expenses", "rules", "budgets"):
        return await update.message.reply_text(
            "Usage:\n"
            "/export\n"
            "/export expenses [YYYY-MM]\n"
            "/export rules\n"
            "/export budgets"
        )

    if kind == "expenses":
        if len(m) != 7 or m[4] != "-":
            return await update.message.reply_text(
                "Month must be YYYY-MM (example: /export expenses 2025-12)"
            )
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
    await update.message.reply_document(
        document=InputFile(bio), caption=f"📄 {filename}"
    )


async def backupdb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /backupdb
    Sends the raw SQLite database file. Contains ALL your data.
    """
    from config import DB_PATH

    bio = open(DB_PATH, "rb")
    try:
        await update.message.reply_document(
            document=bio, caption="🗄️ budget.db backup (SQLite)"
        )
    finally:
        bio.close()
