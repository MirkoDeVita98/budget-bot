import io

from telegram import InputFile, Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from alerts import check_alerts_after_add
from config import BASE_CURRENCY, DB_PATH
from export_csv import export_budgets_csv, export_expenses_csv, export_rules_csv
from textparse import parse_quoted_args

from services import (
    add_expense_optional_fx,
    add_monthly_rule_named_fx,
    add_rule,
    compute_planned_monthly_from_rules,
    compute_spent_this_month,
    delete_expense_by_id,
    delete_last_expense,
    delete_rule,
    ensure_month_budget,
    list_expenses,
    list_rules,
    looks_like_currency,
    month_key,
    parse_amount,
    reset_all_user_data,
    reset_month_expenses,
    upsert_budget,
)


async def reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    *,
    parse_mode: str | None = None,
):
    """
    Safe reply helper:
    - uses update.message.reply_text when available
    - falls back to context.bot.send_message when update.message is None
    """
    chat = update.effective_chat
    if update.message is not None:
        return await update.message.reply_text(text, parse_mode=parse_mode)
    if chat is not None:
        return await context.bot.send_message(
            chat_id=chat.id, text=text, parse_mode=parse_mode
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
    """
    Safe document sender:
    - uses update.message.reply_document when available
    - falls back to context.bot.send_document otherwise
    """
    chat = update.effective_chat

    # Ensure Telegram sees a filename (helps clients + downloads)
    if filename and hasattr(fileobj, "name") is False:
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await reply(
        update,
        context,
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
        "/categories [YYYY-MM]\n"
        "/month YYYY-MM\n\n"
        "Export and Backup:\n"
        "/export [expenses|rules|budgets] [YYYY-MM]\n"
        "/backupdb\n\n"
        "Maintenance:\n"
        "/resetmonth\n"
        "/resetall yes\n\n"
        "Help:\n"
        "/help\n\n"
        "Tip (quotes for spaces):\n"
        '/add "Food & Drinks" "Pizza and Coke" 20 EUR\n'
        '/setmonthly "PSN Plus Extra" 16.99 EUR "Subscriptions & Gaming"\n'
        '/status "Food & Drinks"',
    )


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start(update, context)


async def setbudget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = parse_quoted_args(update.message.text)

    if not args:
        return await reply(update, context, "Usage: /setbudget <amount>")

    try:
        amount = parse_amount(args[0])
    except Exception:
        return await reply(
            update, context, "Couldn't parse amount. Example: /setbudget 2500"
        )

    m = month_key()
    upsert_budget(user_id, m, amount)
    await reply(update, context, f"✅ Set budget for {m}: {amount:.2f} {BASE_CURRENCY}")


async def setdaily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = parse_quoted_args(update.message.text)

    if len(args) < 2:
        return await reply(
            update,
            context,
            "Usage: /setdaily <category> <amount_per_day>\n"
            'Example: /setdaily "Food & Drinks" 15',
        )

    category = args[0].strip()
    try:
        amt = parse_amount(args[1])
    except Exception:
        return await reply(
            update,
            context,
            'Couldn\'t parse amount. Example: /setdaily "Food & Drinks" 15',
        )

    add_rule(user_id, category, f"{category} daily", "daily", amt)
    await reply(
        update,
        context,
        f"✅ Daily rule added: {category} = {amt:.2f} {BASE_CURRENCY}/day",
    )


async def setyearly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = parse_quoted_args(update.message.text)

    if len(args) < 2:
        return await reply(
            update,
            context,
            "Usage: /setyearly <name> <amount_per_year> [category]\n"
            'Example: /setyearly "Car Insurance" 600 "Transport & Car"',
        )

    name = args[0].strip()
    try:
        amt = parse_amount(args[1])
    except Exception:
        return await reply(
            update,
            context,
            'Couldn\'t parse amount. Example: /setyearly "Car Insurance" 600',
        )

    category = args[2].strip() if len(args) >= 3 else "Yearly"

    add_rule(user_id, category, name, "yearly", amt)
    await reply(
        update,
        context,
        f"✅ Yearly rule added: {name} ({category}) = {amt:.2f} {BASE_CURRENCY}/year (→ {amt/12:.2f}/month)",
    )


async def setmonthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = parse_quoted_args(update.message.text)

    if len(args) < 2:
        return await reply(
            update,
            context,
            "Usage:\n"
            "1) /setmonthly <category> <amount>\n"
            "2) /setmonthly <name> <amount> [currency] <category>\n"
            "Examples:\n"
            '/setmonthly "Subscriptions" 35\n'
            '/setmonthly "PSN Plus Extra" 16.99 EUR "Subscriptions & Gaming"',
        )

    # Legacy mode: exactly 2 args
    if len(args) == 2:
        category = args[0].strip()
        try:
            amt = parse_amount(args[1])
        except Exception:
            return await reply(
                update,
                context,
                'Couldn\'t parse amount. Example: /setmonthly "Subscriptions" 35',
            )

        add_rule(user_id, category, f"{category} monthly", "monthly", amt)
        return await reply(
            update,
            context,
            f"✅ Monthly rule added: {category} = {amt:.2f} {BASE_CURRENCY}/month",
        )

    # Named mode: last arg is category, optional currency before it
    category = args[-1].strip()
    currency = BASE_CURRENCY
    amount_index = -2

    if len(args) >= 4 and looks_like_currency(args[-2]):
        currency = args[-2].strip().upper()
        amount_index = -3

    try:
        amount = parse_amount(args[amount_index])
    except Exception:
        return await reply(
            update,
            context,
            'Couldn\'t parse amount.\nExample: /setmonthly "PSN Plus Extra" 16.99 EUR "Subscriptions & Gaming"',
        )

    rule_name = " ".join(args[:amount_index]).strip() or "(no name)"

    fx_date, rate, chf_monthly = await add_monthly_rule_named_fx(
        user_id, rule_name, amount, currency, category
    )

    if currency == BASE_CURRENCY:
        await reply(
            update,
            context,
            f"✅ Monthly rule added: [{category}] {rule_name} = {chf_monthly:.2f} {BASE_CURRENCY}/month",
        )
    else:
        await reply(
            update,
            context,
            f"✅ Monthly rule added: [{category}] {rule_name}\n"
            f"{amount:.2f} {currency}/month → {chf_monthly:.2f} {BASE_CURRENCY}/month (rate {rate:.6f}, {fx_date})",
        )


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    rows = list_rules(user_id)
    if not rows:
        return await reply(update, context, "No rules yet.")

    lines = [f"📌 Rules (stored in {BASE_CURRENCY}):"]
    for r in rows:
        lines.append(
            f"- ID {r['id']}: [{r['category']}] {r['name']} — {float(r['amount']):.2f} {BASE_CURRENCY} / {r['period']}"
        )
    lines.append("\nDelete one with: /delrule <id>")
    await reply(update, context, "\n".join(lines))


async def delrule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = parse_quoted_args(update.message.text)

    if not args:
        return await reply(update, context, "Usage: /delrule <id>")

    try:
        rid = int(args[0])
    except Exception:
        return await reply(update, context, "Rule id must be an integer.")

    ok = delete_rule(user_id, rid)
    await reply(update, context, "🗑️ Rule deleted." if ok else "⚠️ Rule not found.")


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /add <category> <name> <amount> [currency]
    Examples:
      /add Food Groceries 62.40
      /add "Food & Drinks" "Taxi to airport" 20 EUR
    """
    user_id = update.effective_user.id
    text = update.message.text if update.message else ""
    args = parse_quoted_args(text)

    if len(args) < 3:
        return await reply(
            update, context, "Usage: /add <category> <name> <amount> [currency]"
        )

    category = args[0].strip()
    m = month_key()

    # Parse amount/name/currency
    try:
        amount = parse_amount(args[-1])
        currency = BASE_CURRENCY
        name = " ".join(args[1:-1]).strip() or "(no name)"
    except Exception:
        if len(args) < 4:
            return await reply(
                update,
                context,
                "Usage: /add <category> <name> <amount> [currency]\nExample: /add Travel Taxi 20 EUR",
            )

        currency = args[-1].strip().upper()
        if not looks_like_currency(currency):
            return await reply(
                update, context, "Currency must be a 3-letter code (EUR, USD, ...)."
            )

        try:
            amount = parse_amount(args[-2])
        except Exception:
            return await reply(
                update,
                context,
                "Couldn't parse amount. Example: /add Travel Taxi 20 EUR",
            )

        name = " ".join(args[1:-2]).strip() or "(no name)"

    # BEFORE insert: baseline for alert crossings
    planned_by_cat, planned_total = compute_planned_monthly_from_rules(user_id, m)
    overall_budget, carried, carried_from = ensure_month_budget(user_id, m)
    prev_spent_by_cat, prev_spent_total = compute_spent_this_month(user_id, m)

    # ✅ Determine unplanned/new category BEFORE insert
    has_plan = planned_by_cat.get(category, 0.0) > 0.0
    had_spend_before = prev_spent_by_cat.get(category, 0.0) > 0.0
    is_new_unplanned_category = (not has_plan) and (not had_spend_before)

    # Insert expense (with optional FX conversion)
    fx_date, rate, chf_amount = await add_expense_optional_fx(
        user_id, category, name, amount, currency, m
    )

    # AFTER insert: recompute spent
    new_spent_by_cat, new_spent_total = compute_spent_this_month(user_id, m)

    # Alerts
    alert_result = check_alerts_after_add(
        category=category,
        prev_planned_by_cat=planned_by_cat,
        prev_spent_by_cat=prev_spent_by_cat,
        new_spent_by_cat=new_spent_by_cat,
        budget=overall_budget,
        planned_total=planned_total,
        new_planned_by_cat=planned_by_cat,  # planned doesn't change on add
    )

    # Confirmation
    if currency == BASE_CURRENCY:
        await reply(
            update,
            context,
            f"✅ Added: [{category}] {name} = {chf_amount:.2f} {BASE_CURRENCY}",
        )
    else:
        await reply(
            update,
            context,
            f"✅ Added: [{category}] {name}\n"
            f"{amount:.2f} {currency} → {chf_amount:.2f} {BASE_CURRENCY} (rate {rate:.6f}, {fx_date})",
        )

    # ✅ Inform about new unplanned category (instead of "category exceeded")
    if is_new_unplanned_category:
        await reply(
            update,
            context,
            f"ℹ️ New *unplanned* category detected: *{category}* (no rule set). "
            f"It will count as unplanned spend until you add a rule.",
            parse_mode="Markdown",
        )

    # Send alerts after confirmation
    for msg in alert_result.messages:
        await reply(update, context, msg, parse_mode="Markdown")


async def undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    m = month_key()
    row = delete_last_expense(user_id, m)
    if not row:
        return await reply(update, context, "Nothing to undo this month.")

    cur = row["currency"]
    orig = float(row["original_amount"])
    chf = float(row["chf_amount"])

    if cur == BASE_CURRENCY:
        await reply(
            update,
            context,
            f"↩️ Undid: [{row['category']}] {row['name']} = {chf:.2f} {BASE_CURRENCY}",
        )
    else:
        await reply(
            update,
            context,
            f"↩️ Undid: [{row['category']}] {row['name']} = {orig:.2f} {cur} (was {chf:.2f} {BASE_CURRENCY})",
        )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    m = month_key()

    overall_budget, carried, carried_from = ensure_month_budget(user_id, m)
    if overall_budget is None:
        return await reply(
            update, context, f"📅 {m}\nNo overall budget set. Use /setbudget <amount>"
        )

    planned_by_cat, planned_total = compute_planned_monthly_from_rules(user_id, m)
    spent_by_cat, spent_total = compute_spent_this_month(user_id, m)

    # args support quotes and smart quotes (via textparse)
    args = parse_quoted_args(update.message.text if update.message else "")

    # Modes:
    # - /status                 -> compact
    # - /status full            -> full
    # - /status <category...>   -> category detail (if category exists), else "not found"
    want_full = any(a.lower() in ("full", "all") for a in args)
    filtered_args = [a for a in args if a.lower() not in ("full", "all")]

    all_cats = set(planned_by_cat.keys()) | set(spent_by_cat.keys())
    known_cats_sorted = sorted(all_cats)

    # If user provided something besides "full", treat it as a category query
    if filtered_args:
        cat = " ".join(filtered_args).strip()

        if cat not in all_cats:
            if known_cats_sorted:
                return await reply(
                    update,
                    context,
                    f"⚠️ Category not found: *{cat}*\n\nAvailable categories:\n"
                    + "\n".join(f"- {c}" for c in known_cats_sorted),
                    parse_mode="Markdown",
                )
            return await reply(
                update, context, f"⚠️ Category not found: {cat}\n(no categories yet)"
            )

        planned = planned_by_cat.get(cat, 0.0)
        spent = spent_by_cat.get(cat, 0.0)
        remaining = planned - spent

        planned_label = (
            f"{planned:.2f} {BASE_CURRENCY}"
            if planned > 0
            else f"0.00 {BASE_CURRENCY} (unplanned)"
        )
        tag = "✅" if remaining >= 0 else "⚠️"

        return await reply(
            update,
            context,
            f"📅 {m} — *{cat}*\n"
            f"Planned: {planned_label}\n"
            f"Spent: {spent:.2f} {BASE_CURRENCY}\n"
            f"{tag} Remaining (category): {remaining:.2f} {BASE_CURRENCY}",
            parse_mode="Markdown",
        )

    # Compute overspend beyond plan (reduces overall)
    overspend_total = 0.0
    overspend_by_cat = {}
    for c in all_cats:
        p = planned_by_cat.get(c, 0.0)
        s = spent_by_cat.get(c, 0.0)
        over = max(0.0, s - p)
        overspend_by_cat[c] = over
        overspend_total += over

    remaining_overall = overall_budget - planned_total - overspend_total
    remaining_tag = "✅" if remaining_overall >= 0 else "🚨"

    unplanned_spent = sum(
        spent_by_cat.get(c, 0.0)
        for c in spent_by_cat.keys()
        if planned_by_cat.get(c, 0.0) == 0.0
    )

    # Sort categories by importance:
    # 1) overspend desc
    # 2) spent desc
    # 3) name asc
    def sort_key(c: str):
        return (-overspend_by_cat.get(c, 0.0), -spent_by_cat.get(c, 0.0), c.lower())

    cats_sorted = sorted(all_cats, key=sort_key)

    # Compact shows only top N categories (overspent + biggest spenders)
    TOP_N = 8
    show_cats = cats_sorted if want_full else cats_sorted[:TOP_N]

    lines = [f"📅 {m} — {'Full' if want_full else 'Summary'}"]

    if carried:
        lines.append(
            f"ℹ️ Budget auto-carried from {carried_from}: {overall_budget:.2f} {BASE_CURRENCY}"
        )

    lines += [
        "",
        f"Budget: {overall_budget:.2f} {BASE_CURRENCY}",
        f"Planned (rules): {planned_total:.2f} {BASE_CURRENCY}",
        f"Spent (all expenses): {spent_total:.2f} {BASE_CURRENCY}",
        f"Unplanned spend: {unplanned_spent:.2f} {BASE_CURRENCY}",
        f"Spent beyond plan: {overspend_total:.2f} {BASE_CURRENCY}",
        "——————————",
        f"{remaining_tag} Remaining overall: {remaining_overall:.2f} {BASE_CURRENCY}",
        "",
    ]

    if not want_full and len(cats_sorted) > TOP_N:
        lines.append(
            f"Top categories (showing {TOP_N}/{len(cats_sorted)}). Use `/status full` for all."
        )
        lines.append("")
    else:
        lines.append("By category (planned | spent | remaining):")

    if not show_cats:
        lines.append("(no categories yet)")
    else:
        lines.append("By category (planned | spent | remaining):")
        for c in show_cats:
            p = planned_by_cat.get(c, 0.0)
            s = spent_by_cat.get(c, 0.0)
            r = p - s

            # mark unplanned categories
            label = c
            if p == 0.0 and s > 0.0:
                label = f"{c} (unplanned)"

            r_tag = "✅" if r >= 0 else "⚠️"
            over = overspend_by_cat.get(c, 0.0)
            over_str = f"  (+{over:.2f} over)" if over > 0 else ""

            lines.append(
                f"- {label}: {p:.2f} | {s:.2f} | {r_tag} {r:.2f} {BASE_CURRENCY}{over_str}"
            )

    # small footer hint
    if not want_full:
        lines += [
            "",
            "Tips:",
            '• Use quotes for spaces: /status "Food & Drinks"',
            "• See all categories: /status full",
        ]

    await reply(update, context, "\n".join(lines), parse_mode="Markdown")


async def categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /categories [YYYY-MM]
    Examples:
      /categories
      /categories 2025-12
    """
    user_id = update.effective_user.id
    args = parse_quoted_args(update.message.text if update.message else "")

    m = month_key()
    if args:
        m = args[0].strip()

    if len(m) != 7 or m[4] != "-":
        return await reply(
            update,
            context,
            "Usage: /categories [YYYY-MM]\nExample: /categories 2025-12",
        )

    planned_by_cat, _ = compute_planned_monthly_from_rules(user_id, m)
    spent_by_cat, _ = compute_spent_this_month(user_id, m)

    cats = sorted(set(planned_by_cat.keys()) | set(spent_by_cat.keys()))
    if not cats:
        return await reply(update, context, f"📅 {m}\nNo categories yet.")

    # Optional: show which are planned vs unplanned
    lines = [f"📂 Categories for {m}:"]
    for c in cats:
        planned = planned_by_cat.get(c, 0.0) > 0.0
        spent = spent_by_cat.get(c, 0.0) > 0.0
        if planned:
            tag = "planned"
        elif spent:
            tag = "unplanned"
        else:
            tag = ""
        lines.append(f"- {c}" + (f" ({tag})" if tag else ""))

    lines.append("")
    lines.append('Tip: /status "Category Name"')
    await reply(update, context, "\n".join(lines))


async def month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = parse_quoted_args(update.message.text)

    if not args:
        return await reply(
            update, context, "Usage: /month YYYY-MM (example: /month 2025-12)"
        )

    m = args[0].strip()
    if len(m) != 7 or m[4] != "-":
        return await reply(
            update, context, "Usage: /month YYYY-MM (example: /month 2025-12)"
        )

    overall_budget, carried, carried_from = ensure_month_budget(user_id, m)
    if overall_budget is None:
        return await reply(
            update, context, f"📅 {m}\nNo overall budget set for this month."
        )

    planned_by_cat, planned_total = compute_planned_monthly_from_rules(user_id, m)
    spent_by_cat, spent_total = compute_spent_this_month(user_id, m)

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

    msg = [f"📅 {m}"]
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

    await reply(update, context, "\n".join(msg))


async def resetmonth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    m = month_key()
    n = reset_month_expenses(user_id, m)
    await reply(update, context, f"🧹 Deleted {n} expenses for {m}.")


async def resetall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = parse_quoted_args(update.message.text)

    if not args or args[0].lower() != "yes":
        return await reply(
            update, context, "⚠️ This will DELETE ALL your data.\nRun: /resetall yes"
        )

    reset_all_user_data(user_id)
    await reply(update, context, "🧨 All your budget data has been reset.")


async def expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /expenses [YYYY-MM] [limit]
    Examples:
      /expenses
      /expenses 2025-12
      /expenses 2025-12 100
    """
    user_id = update.effective_user.id
    args = parse_quoted_args(update.message.text)

    m = month_key()
    limit = 50

    if len(args) >= 1:
        m = args[0].strip()
    if len(args) >= 2:
        try:
            limit = int(args[1])
        except Exception:
            return await reply(
                update,
                context,
                "Limit must be an integer. Example: /expenses 2025-12 50",
            )

    if len(m) != 7 or m[4] != "-":
        return await reply(
            update,
            context,
            "Usage: /expenses [YYYY-MM] [limit]\nExample: /expenses 2025-12 50",
        )

    rows = list_expenses(user_id, m, limit=limit)
    if not rows:
        return await reply(update, context, f"No expenses for {m}.")

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
            lines.append(
                f"- ID {eid}: [{cat}] {name} — {chf:.2f} {BASE_CURRENCY} ({created})"
            )
        else:
            lines.append(
                f"- ID {eid}: [{cat}] {name} — {orig:.2f} {cur} → {chf:.2f} {BASE_CURRENCY} ({created})"
            )

    lines.append("\nDelete one with:")
    lines.append("/delexpense <id>")

    await reply(update, context, "\n".join(lines))


async def delexpense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /delexpense <id>
    """
    user_id = update.effective_user.id
    args = parse_quoted_args(update.message.text)

    if not args:
        return await reply(
            update, context, "Usage: /delexpense <id>\nTip: use /expenses to see IDs."
        )

    try:
        eid = int(args[0])
    except Exception:
        return await reply(
            update, context, "Expense id must be an integer. Example: /delexpense 42"
        )

    ok = delete_expense_by_id(user_id, eid)
    await reply(
        update,
        context,
        "🗑️ Expense deleted." if ok else "⚠️ Expense not found (or not yours).",
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
    args = parse_quoted_args(update.message.text)

    kind = "expenses"
    m = month_key()

    if len(args) >= 1:
        kind = args[0].strip().lower()
    if len(args) >= 2:
        m = args[1].strip()

    if kind not in ("expenses", "rules", "budgets"):
        return await reply(
            update,
            context,
            "Usage:\n"
            "/export\n"
            "/export expenses [YYYY-MM]\n"
            "/export rules\n"
            "/export budgets",
        )

    if kind == "expenses":
        if len(m) != 7 or m[4] != "-":
            return await reply(
                update,
                context,
                "Month must be YYYY-MM (example: /export expenses 2025-12)",
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
    await reply_doc(update, context, InputFile(bio), caption=f"📄 {filename}")


async def backupdb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /backupdb
    Sends the raw SQLite database file. Contains ALL your data.
    """
    with open(DB_PATH, "rb") as f:
        await reply_doc(update, context, f, caption="🗄️ budget.db backup (SQLite)")
