from .base import *
from db.services import (
    add_rule,
    delete_rule,
    list_rules,
    parse_amount,
    looks_like_currency,
    add_rule_named_fx,
    upsert_budget,
    month_key,
)

from ..pagination_callbacks import _format_rules_page
from utils.validators import (
    validate_budget,
    validate_amount,
    validate_category,
    validate_name,
    BudgetValidationError,
    AmountValidationError,
    CategoryValidationError,
    NameValidationError,
)


# Load messages from YAML file using relative path
_current_dir = Path(__file__).parent
_messages_path = _current_dir / "messages" / "rules.yaml"
_error_messages_path = _current_dir / "messages" / "errors.yaml"
with open(_messages_path, "r") as file:
    MESSAGES = yaml.safe_load(file)
with open(_error_messages_path, "r") as file:
    ERROR_MESSAGES = yaml.safe_load(file)


@rollover_notify
async def setbudget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = get_args(update)

    if not args:
        return await reply(update, context, MESSAGES["usage_setbudget"])

    try:
        amount = parse_amount(args[0])
    except ValueError:
        return await reply(update, context, MESSAGES["parse_amount_error"])

    # Validate budget amount
    try:
        amount = validate_budget(amount)
    except BudgetValidationError as e:
        return await reply(update, context, ERROR_MESSAGES.get(e.message, MESSAGES.get("parse_amount_error", "Invalid budget")))

    m = month_key()
    upsert_budget(user_id, m, amount)
    return await reply(
        update,
        context,
        MESSAGES["set_budget_success"].format(
            month=m, amount=amount, currency=BASE_CURRENCY
        ),
    )


async def _handle_rule_setter(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    args: list,
    period: str,
    cmd: str,
    abbr: str,
):
    """
    Generic handler for setdaily/setweekly/setmonthly/setyearly.

    Supports two modes:
    1. Legacy: /cmd <category> <amount>
    2. Named: /cmd <category> <name> <amount> [currency]
    """
    # Map period to human-readable names
    period_map = {
        "daily": {"name": "Daily", "label": "day"},
        "weekly": {"name": "Weekly", "label": "week"},
        "monthly": {"name": "Monthly", "label": "month"},
        "yearly": {"name": "Yearly", "label": "year"},
    }
    period_info = period_map.get(period, {"name": "Unknown", "label": period})

    if len(args) < 2:
        return await reply(
            update,
            context,
            MESSAGES["usage_rule"].format(cmd=cmd, abbr=abbr),
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
                MESSAGES["parse_amount_error_rule"].format(cmd=cmd, abbr=abbr),
            )

        # Validate inputs
        try:
            amt = validate_amount(amt, field_name="amount")
            category = validate_category(category)
        except (AmountValidationError, CategoryValidationError) as e:
            return await reply(update, context, ERROR_MESSAGES.get(e.message, "Invalid input"))

        add_rule(user_id, category, f"{category} {period}", period, amt)
        return await reply(
            update,
            context,
            MESSAGES["rule_success_base"].format(
                category=category,
                rule_name=f"{category} {period}",
                amount=amt,
                currency=BASE_CURRENCY,
                period_name=period_info["name"],
                period_label=period_info["label"],
                extra="",
            ),
        )

    # Named mode: first arg is category, rest is name amount [currency]
    category = args[0].strip()
    currency = BASE_CURRENCY
    
    # Check if second-to-last arg is currency
    if len(args) >= 4 and looks_like_currency(args[-1]):
        currency = args[-1].strip().upper()
        amount_index = -2
        name_end_index = -2
    else:
        amount_index = -1
        name_end_index = -1

    try:
        amount = parse_amount(args[amount_index])
    except Exception:
        return await reply(
            update,
            context,
            MESSAGES["parse_amount_error_rule"].format(cmd=cmd, abbr=abbr),
        )

    rule_name = " ".join(args[1:name_end_index]).strip() or "(no name)"

    # Validate inputs
    try:
        amount = validate_amount(amount, field_name="amount")
        category = validate_category(category)
        if rule_name != "(no name)":
            rule_name = validate_name(rule_name, field_name="name")
    except (AmountValidationError, CategoryValidationError, NameValidationError) as e:
        return await reply(update, context, ERROR_MESSAGES.get(e.message, "Invalid input"))

    fx_date, rate, chf_amount = await add_rule_named_fx(
        user_id, rule_name, amount, currency, category, period
    )

    if currency == BASE_CURRENCY:
        return await reply(
            update,
            context,
            MESSAGES["rule_success_base"].format(
                category=category,
                rule_name=rule_name,
                amount=chf_amount,
                currency=BASE_CURRENCY,
                name=rule_name,  # for yearly
                monthly=chf_amount / 12 if period == "yearly" else None,
                period_name=period_info["name"],
                period_label=period_info["label"],
                extra="",
            ),
        )
    else:
        return await reply(
            update,
            context,
            MESSAGES["rule_success_fx"].format(
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
                period_name=period_info["name"],
                period_label=period_info["label"],
                extra="",
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
        "setdaily",
        "sd",
    )


@rollover_notify
async def setweekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = get_args(update)

    return await _handle_rule_setter(
        update,
        context,
        user_id,
        args,
        "weekly",
        "setweekly",
        "sw",
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
        "setyearly",
        "sy",
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
        "setmonthly",
        "sm",
    )


@rollover_silent
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    rows = list_rules(user_id)
    if not rows:
        return await reply(update, context, MESSAGES["no_rules"])

    # Setup pagination
    from utils.pagination import PaginationState
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from utils.pagination import get_pagination_buttons
    
    state = PaginationState(
        items=rows,
        items_per_page=10,
        callback_prefix="rules"
    )
    
    # Format first page with grouped display
    page_text = _format_rules_page(state)
    
    # Add pagination info if needed
    if state.total_pages > 1:
        buttons_data, footer = get_pagination_buttons(
            prefix="rules",
            current_page=state.current_page,
            total_pages=state.total_pages,
            has_previous=state.has_previous,
            has_next=state.has_next,
        )
        page_text += f"\n\n{footer}"
        
        # Build keyboard
        keyboard = []
        if buttons_data:
            button_row = []
            for label, callback in buttons_data:
                button_row.append(InlineKeyboardButton(label, callback_data=callback))
            keyboard.append(button_row)
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        # Store pagination state
        context.user_data["rules_pagination"] = state.to_dict()
        
        await reply(update, context, page_text, reply_markup=reply_markup)
    else:
        # No pagination needed
        await reply(update, context, page_text)


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




