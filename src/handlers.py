from telegram import Update
from telegram.ext import ContextTypes

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
        "/undo\n\n"
        "Reports:\n"
        "/status [category]\n"
        "/month YYYY-MM\n\n"
        "Maintenance:\n"
        "/resetmonth\n"
        "/resetall yes\n"
    )


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
    """
    user_id = update.effective_user.id
    args = context.args
    if len(args) < 3:
        return await update.message.reply_text(
            "Usage: /add <category> <name> <amount> [currency]"
        )

    category = args[0].strip()
    m = month_key()

    # Try last token as amount => CHF
    try:
        amount = parse_amount(args[-1])
        currency = BASE_CURRENCY
        name = " ".join(args[1:-1]).strip() or "(no name)"
    except Exception:
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

    fx_date, rate, chf_amount = await add_expense_optional_fx(
        user_id, category, name, amount, currency, m
    )

    if currency == BASE_CURRENCY:
        await update.message.reply_text(
            f"✅ Added: [{category}] {name} = {chf_amount:.2f} {BASE_CURRENCY}"
        )
    else:
        await update.message.reply_text(
            f"✅ Added: [{category}] {name}\n"
            f"{amount:.2f} {currency} → {chf_amount:.2f} {BASE_CURRENCY} (rate {rate:.6f}, {fx_date})"
        )


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

    overall_budget = get_month_budget(user_id, m)
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
        remaining = planned - spent  # can go negative (overspend)
        return await update.message.reply_text(
            f"📅 {m} — Category: {cat}\n"
            f"Planned: {planned:.2f} {BASE_CURRENCY}\n"
            f"Spent: -{spent:.2f} {BASE_CURRENCY}\n"
            f"Remaining (category): {remaining:.2f} {BASE_CURRENCY}"
        )

    # do NOT subtract planned and spent together
    reserved = planned_total
    overspend = max(0.0, spent_total - planned_total)
    remaining_overall = overall_budget - reserved - overspend
    # equivalent: overall_budget - max(planned_total, spent_total)

    cats = sorted(set(planned_by_cat.keys()) | set(spent_by_cat.keys()))
    lines = [
        f"📅 {m}",
        f"Overall budget: {overall_budget:.2f} {BASE_CURRENCY}",
        f"Reserved (planned rules): -{reserved:.2f} {BASE_CURRENCY}",
        f"Spent (entered): -{spent_total:.2f} {BASE_CURRENCY}",
        f"Overspend vs plan: -{overspend:.2f} {BASE_CURRENCY}",
        "——————————",
        f"Remaining overall: {remaining_overall:.2f} {BASE_CURRENCY}",
        "",
        "By category (planned → spent → remaining):",
    ]

    if not cats:
        lines.append("(no categories yet)")
    else:
        for c in cats:
            p = planned_by_cat.get(c, 0.0)
            s = spent_by_cat.get(c, 0.0)
            lines.append(f"- {c}: {p:.2f} → {s:.2f} → {(p - s):.2f} {BASE_CURRENCY}")

    await update.message.reply_text("\n".join(lines))

    remaining_overall = overall_budget - planned_total - spent_total
    cats = sorted(set(planned_by_cat.keys()) | set(spent_by_cat.keys()))

    lines = [
        f"📅 {m}",
        f"Overall budget: {overall_budget:.2f} {BASE_CURRENCY}",
        f"Planned from rules: -{planned_total:.2f} {BASE_CURRENCY}",
        f"Spent (entered): -{spent_total:.2f} {BASE_CURRENCY}",
        "——————————",
        f"Remaining overall: {remaining_overall:.2f} {BASE_CURRENCY}",
        "",
        "By category (planned → spent → remaining):",
    ]
    if not cats:
        lines.append("(no categories yet)")
    else:
        for c in cats:
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

    overall_budget = get_month_budget(user_id, m)
    if overall_budget is None:
        return await update.message.reply_text(
            f"📅 {m}\nNo overall budget set for this month."
        )

    planned_by_cat, planned_total = compute_planned_monthly_from_rules(user_id, m)
    spent_by_cat, spent_total = compute_spent_this_month(user_id, m)

    # ✅ FIX: do NOT subtract planned and spent together
    reserved = planned_total
    overspend = max(0.0, spent_total - planned_total)
    remaining_overall = overall_budget - reserved - overspend
    # equivalent: overall_budget - max(planned_total, spent_total)

    await update.message.reply_text(
        f"📅 {m}\n"
        f"Overall budget: {overall_budget:.2f} {BASE_CURRENCY}\n"
        f"Reserved (planned rules): -{reserved:.2f} {BASE_CURRENCY}\n"
        f"Spent: -{spent_total:.2f} {BASE_CURRENCY}\n"
        f"Overspend vs plan: -{overspend:.2f} {BASE_CURRENCY}\n"
        f"Remaining: {remaining_overall:.2f} {BASE_CURRENCY}"
    )


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
