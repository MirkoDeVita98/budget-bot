from .base import *
from services import (
    add_rule,
    delete_rule,
    list_rules,
    parse_amount,
    looks_like_currency,
    add_rule_named_fx,
)


# Load messages from YAML file using relative path
_current_dir = Path(__file__).parent
_messages_path = _current_dir / "messages" / "rules.yaml"
with open(_messages_path, "r") as file:
    MESSAGES = yaml.safe_load(file)


async def _handle_rule_setter(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    args: list,
    period: str,
    usage_key: str,
    error_key: str,
    success_base_key: str,
    success_fx_key: str,
):
    """
    Generic handler for setdaily/setmonthly/setyearly.

    Supports two modes:
    1. Legacy: /cmd <category> <amount>  (daily/yearly only)
    2. Named: /cmd <name> <amount> [currency] <category>
    """
    if len(args) < 2:
        return await reply(update, context, MESSAGES[usage_key])

    # Legacy mode: exactly 2 args
    if len(args) == 2:
        category = args[0].strip()
        try:
            amt = parse_amount(args[1])
        except Exception:
            return await reply(update, context, MESSAGES[error_key])

        add_rule(user_id, category, f"{category} {period}", period, amt)
        return await reply(
            update,
            context,
            MESSAGES[success_base_key].format(
                category=category,
                rule_name=f"{category} {period}",
                amount=amt,
                currency=BASE_CURRENCY,
            ),
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
        return await reply(update, context, MESSAGES[error_key])

    rule_name = " ".join(args[:amount_index]).strip() or "(no name)"

    fx_date, rate, chf_amount = await add_rule_named_fx(
        user_id, rule_name, amount, currency, category, period
    )

    if currency == BASE_CURRENCY:
        return await reply(
            update,
            context,
            MESSAGES[success_base_key].format(
                category=category,
                rule_name=rule_name,
                amount=chf_amount,
                currency=BASE_CURRENCY,
                name=rule_name,  # for yearly
                monthly=chf_amount / 12 if period == "yearly" else None,
            ),
        )
    else:
        return await reply(
            update,
            context,
            MESSAGES[success_fx_key].format(
                category=category,
                rule_name=rule_name,
                amount=amount,
                currency=currency,
                converted=chf_amount,
                base_currency=BASE_CURRENCY,
                rate=rate,
                fx_date=fx_date,
                name=rule_name,  # for yearly
                monthly=chf_amount / 12 if period == "yearly" else None,
            ),
        )


@rollover_notify
async def setdaily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = get_args(update)

    return await _handle_rule_setter(
        update,
        context,
        user_id,
        args,
        "daily",
        "usage_setdaily",
        "parse_amount_error_setdaily",
        "setdaily_success_base",
        "setdaily_success_fx",
    )


@rollover_notify
async def setyearly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = get_args(update)

    return await _handle_rule_setter(
        update,
        context,
        user_id,
        args,
        "yearly",
        "usage_setyearly",
        "parse_amount_error_setyearly",
        "setyearly_success_base",
        "setyearly_success_fx",
    )


@rollover_notify
async def setmonthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = get_args(update)

    return await _handle_rule_setter(
        update,
        context,
        user_id,
        args,
        "monthly",
        "usage_setmonthly",
        "parse_amount_error_setmonthly",
        "setmonthly_success_base",
        "setmonthly_success_fx",
    )


@rollover_silent
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    rows = list_rules(user_id)
    if not rows:
        return await reply(update, context, MESSAGES["no_rules"])

    lines = [MESSAGES["rules_list_header"].format(currency=BASE_CURRENCY)]
    for r in rows:
        lines.append(
            MESSAGES["rules_list_item"].format(
                id=r["id"],
                category=r["category"],
                name=r["name"],
                amount=float(r["amount"]),
                currency=BASE_CURRENCY,
                period=r["period"],
            )
        )
    lines.append(MESSAGES["rules_list_footer"])
    await reply(update, context, "\n".join(lines))


@rollover_notify
async def delrule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = get_args(update)

    if not args:
        return await reply(update, context, MESSAGES["usage_delrule"])

    try:
        rid = int(args[0])
    except Exception:
        return await reply(update, context, MESSAGES["rule_id_error"])

    ok = delete_rule(user_id, rid)
    await reply(
        update,
        context,
        MESSAGES["delrule_success"] if ok else MESSAGES["delrule_failure"],
    )
