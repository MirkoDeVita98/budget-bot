from .base import *
from services import (
    add_expense_optional_fx,
    compute_planned_monthly_from_rules,
    compute_spent_this_month,
    delete_last_expense,
    ensure_month_budget,
    parse_amount,
    looks_like_currency,
    month_key,
    list_expenses_filtered,
    delete_expense_by_id,
)
from alerts import check_alerts_after_add


# Load messages from YAML file using relative path
_current_dir = Path(__file__).parent
_messages_path = _current_dir / "messages" / "expenses.yaml"
with open(_messages_path, "r") as file:
    MESSAGES = yaml.safe_load(file)


def _is_month_token(t: str) -> bool:
    return len(t) == 7 and t[4] == "-" and t[:4].isdigit() and t[5:].isdigit()


def _is_int_token(t: str) -> bool:
    try:
        int(t)
        return True
    except Exception:
        return False


@rollover_notify
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
        return await reply(update, context, MESSAGES["usage_add"])

    category = args[0].strip()
    m = month_key()

    # Parse amount/name/currency
    try:
        amount = parse_amount(args[-1])
        currency = BASE_CURRENCY
        name = " ".join(args[1:-1]).strip() or "(no name)"
    except Exception:
        if len(args) < 4:
            return await reply(update, context, MESSAGES["usage_add"])

        currency = args[-1].strip().upper()
        if not looks_like_currency(currency):
            return await reply(update, context, MESSAGES["currency_error"])

        try:
            amount = parse_amount(args[-2])
        except Exception:
            return await reply(update, context, MESSAGES["amount_parse_error"])

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
            MESSAGES["add_success_base"].format(
                category=category, name=name, amount=chf_amount, currency=BASE_CURRENCY
            ),
        )
    else:
        await reply(
            update,
            context,
            MESSAGES["add_success_fx"].format(
                category=category,
                name=name,
                amount=amount,
                currency=currency,
                converted=chf_amount,
                base_currency=BASE_CURRENCY,
                rate=rate,
                fx_date=fx_date,
            ),
        )

    # ✅ Inform about new unplanned category (instead of "category exceeded")
    if is_new_unplanned_category:
        await reply(
            update,
            context,
            MESSAGES["new_unplanned_category"].format(category=category),
            parse_mode="Markdown",
        )

    # Send alerts after confirmation
    for msg in alert_result.messages:
        await reply(update, context, msg, parse_mode="Markdown")


@rollover_notify
async def undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    m = month_key()
    row = delete_last_expense(user_id, m)
    if not row:
        return await reply(update, context, MESSAGES["nothing_to_undo"])

    cur = row["currency"]
    orig = float(row["original_amount"])
    chf = float(row["chf_amount"])

    if cur == BASE_CURRENCY:
        await reply(
            update,
            context,
            MESSAGES["undo_success_base"].format(amount=orig, currency=BASE_CURRENCY),
        )
    else:
        await reply(
            update,
            context,
            MESSAGES["undo_success_fx"].format(
                amount=orig, currency=cur, converted=chf, base_currency=BASE_CURRENCY
            ),
        )


@rollover_silent
async def expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /expenses [YYYY-MM] [limit] ["Category Name"]
    /expenses ["Category Name"] [limit]
    /expenses [YYYY-MM] ["Category Name"] [limit]
    Examples:
      /expenses
      /expenses 2025-12
      /expenses 2025-12 100
      /expenses "Food & Drinks"
      /expenses "Food & Drinks" 100
      /expenses 2025-12 "Food & Drinks" 100
    """
    user_id = update.effective_user.id
    args = parse_quoted_args(update.message.text if update.message else "")

    # defaults
    m = month_key()
    limit = 50
    category = None

    # Parse flexible args
    leftovers = []
    for a in args:
        if _is_month_token(a):
            m = a
        elif _is_int_token(a):
            limit = int(a)
        else:
            leftovers.append(a)

    if leftovers:
        category = " ".join(leftovers).strip()

    if limit <= 0:
        limit = 50
    if limit > 500:
        limit = 500  # prevent huge telegram messages

    # Validate month format
    if not _is_month_token(m):
        return await reply(
            update,
            context,
            'Usage: /expenses [YYYY-MM] [limit] [category]\nExample: /expenses 2025-12 50 "Food & Drinks"',
        )

    rows = list_expenses_filtered(user_id, m, limit=limit, category=category)

    title = MESSAGES["expenses_title"].format(
        month=m, category=f' — "{category}"' if category else ""
    )

    if not rows:
        return await reply(
            update, context, MESSAGES["expenses_no_rows"].format(title=title)
        )

    total = sum(float(r["chf_amount"]) for r in rows)

    lines = [
        MESSAGES["expenses_summary"].format(
            title=title,
            count=min(limit, len(rows)),
            total=total,
            currency=BASE_CURRENCY,
        ),
        "",
    ]

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
                MESSAGES["expenses_row_base"].format(
                    id=eid,
                    category=cat,
                    name=name,
                    amount=chf,
                    currency=BASE_CURRENCY,
                    created=created,
                )
            )
        else:
            lines.append(
                MESSAGES["expenses_row_fx"].format(
                    id=eid,
                    category=cat,
                    name=name,
                    amount=orig,
                    currency=cur,
                    converted=chf,
                    base_currency=BASE_CURRENCY,
                    created=created,
                )
            )

    lines.append("")
    lines.append(MESSAGES["expenses_delete_tip"])

    # Helpful usage tip
    if category is None:
        lines.append(MESSAGES["expenses_filter_tip"])
    else:
        lines.append(
            MESSAGES["expenses_remove_filter_tip"].format(month=m, limit=limit)
        )

    await reply(update, context, "\n".join(lines))


@rollover_notify
async def delexpense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /delexpense <id>
    """
    user_id = update.effective_user.id
    args = get_args(update)

    if not args:
        return await reply(update, context, MESSAGES["delexpense_usage"])

    try:
        eid = int(args[0])
    except Exception:
        return await reply(update, context, MESSAGES["delexpense_id_error"])

    ok = delete_expense_by_id(user_id, eid)
    await reply(
        update,
        context,
        MESSAGES["delexpense_success" if ok else "delexpense_failure"],
    )
