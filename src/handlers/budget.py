from .base import *
from services import (
    upsert_budget,
    parse_amount,
    get_month_budget,
    ensure_month_budget,
    month_key,
    compute_planned_monthly_from_rules,
    compute_spent_this_month,
)


# Load messages from YAML file using relative path
_current_dir = Path(__file__).parent
_messages_path = _current_dir / "messages" / "budget.yaml"
with open(_messages_path, "r") as file:
    MESSAGES = yaml.safe_load(file)


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

    m = month_key()
    upsert_budget(user_id, m, amount)
    return await reply(
        update,
        context,
        MESSAGES["set_budget_success"].format(
            month=m, amount=amount, currency=BASE_CURRENCY
        ),
    )


@rollover_silent
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    m = month_key()

    overall_budget, carried, carried_from = ensure_month_budget(user_id, m)
    if overall_budget is None:
        return await reply(update, context, MESSAGES["no_budget_set"].format(month=m))

    planned_by_cat, planned_total = compute_planned_monthly_from_rules(user_id, m)
    spent_by_cat, spent_total = compute_spent_this_month(user_id, m)

    # args support quotes and smart quotes (via textparse)
    args = get_args(update)

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
                    MESSAGES["category_not_found"].format(
                        category=cat,
                        categories="\n".join(f"- {c}" for c in known_cats_sorted),
                    ),
                    parse_mode="Markdown",
                )
            return await reply(
                update,
                context,
                MESSAGES["category_not_found_no_categories"].format(category=cat),
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
            MESSAGES["category_details"].format(
                month=m,
                category=cat,
                planned_label=planned_label,
                spent=spent,
                tag=tag,
                remaining=remaining,
                currency=BASE_CURRENCY,
            ),
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

    summary_type = "Full" if want_full else "Summary"
    lines = [MESSAGES["status_summary"].format(month=m, summary_type=summary_type)]

    if carried:
        lines.append(
            MESSAGES["budget_carried"].format(
                carried_from=carried_from,
                overall_budget=overall_budget,
                currency=BASE_CURRENCY,
            )
        )

    lines += [
        "",
        MESSAGES["status_budget"].format(
            overall_budget=overall_budget, currency=BASE_CURRENCY
        ),
        MESSAGES["status_planned"].format(
            planned_total=planned_total, currency=BASE_CURRENCY
        ),
        MESSAGES["status_spent"].format(
            spent_total=spent_total, currency=BASE_CURRENCY
        ),
        MESSAGES["status_unplanned"].format(
            unplanned_spent=unplanned_spent, currency=BASE_CURRENCY
        ),
        MESSAGES["status_overspend"].format(
            overspend_total=overspend_total, currency=BASE_CURRENCY
        ),
        MESSAGES["status_separator"],
        MESSAGES["status_remaining"].format(
            remaining_tag=remaining_tag,
            remaining_overall=remaining_overall,
            currency=BASE_CURRENCY,
        ),
        "",
    ]

    if not want_full and len(cats_sorted) > TOP_N:
        lines.append(
            MESSAGES["status_top_categories"].format(
                top_n=TOP_N, total=len(cats_sorted)
            )
        )
        lines.append("")

    if not show_cats:
        lines.append(MESSAGES["status_no_categories"])
    else:
        # Separate planned and unplanned categories
        planned_cats = [c for c in show_cats if planned_by_cat.get(c, 0.0) > 0.0]
        unplanned_cats = [c for c in show_cats if planned_by_cat.get(c, 0.0) == 0.0]

        if planned_cats:
            lines.append(MESSAGES["status_by_category_planned"])
            for c in planned_cats:
                p = planned_by_cat.get(c, 0.0)
                s = spent_by_cat.get(c, 0.0)
                r = p - s

                r_tag = "✅" if r >= 0 else "⚠️"
                over = overspend_by_cat.get(c, 0.0)
                over_str = f"  (+{over:.2f} over)" if over > 0 else ""

                lines.append(
                    f"- {c}: {p:.2f} | {s:.2f} | {r_tag} {r:.2f} {BASE_CURRENCY}{over_str}"
                )

        if unplanned_cats:
            if planned_cats:
                lines.append("")
            lines.append(MESSAGES["status_by_category_unplanned"])
            for c in unplanned_cats:
                s = spent_by_cat.get(c, 0.0)

                lines.append(f"- {c}: {s:.2f} {BASE_CURRENCY}")

    # small footer hint
    if not want_full:
        lines += [
            "",
            MESSAGES["status_header_tips"],
            MESSAGES["status_tip_quotes"],
            MESSAGES["status_tip_full"],
        ]

    await reply(update, context, "\n".join(lines), parse_mode="Markdown")


@rollover_silent
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
            MESSAGES["categories_usage"],
        )

    planned_by_cat, _ = compute_planned_monthly_from_rules(user_id, m)
    spent_by_cat, _ = compute_spent_this_month(user_id, m)

    cats = sorted(set(planned_by_cat.keys()) | set(spent_by_cat.keys()))
    if not cats:
        return await reply(
            update, context, MESSAGES["categories_no_categories"].format(month=m)
        )

    # Optional: show which are planned vs unplanned
    lines = [MESSAGES["categories_header"].format(month=m)]
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
    lines.append(MESSAGES["categories_tip"])
    await reply(update, context, "\n".join(lines))


@rollover_silent
async def month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = get_args(update)

    if not args:
        return await reply(update, context, MESSAGES["month_usage"])

    m = args[0].strip()
    if len(m) != 7 or m[4] != "-":
        return await reply(update, context, MESSAGES["month_usage"])

    overall_budget = get_month_budget(user_id, m)

    if overall_budget is None:
        return await reply(update, context, MESSAGES["month_no_budget"].format(month=m))

    planned_by_cat, planned_total = compute_planned_monthly_from_rules(user_id, m)
    spent_by_cat, spent_total = compute_spent_this_month(user_id, m)

    all_cats = set(planned_by_cat.keys()) | set(spent_by_cat.keys())

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

    # Sort by "importance": overspend desc, spent desc, name asc
    def sort_key(c: str):
        return (-overspend_by_cat.get(c, 0.0), -spent_by_cat.get(c, 0.0), c.lower())

    cats_sorted = sorted(all_cats, key=sort_key)
    TOP_N = 8
    show_cats = cats_sorted[:TOP_N]

    lines = [MESSAGES["month_header"].format(month=m)]

    lines += [
        "",
        MESSAGES["month_budget"].format(
            overall_budget=overall_budget, currency=BASE_CURRENCY
        ),
        MESSAGES["month_planned"].format(
            planned_total=planned_total, currency=BASE_CURRENCY
        ),
        MESSAGES["month_spent"].format(spent_total=spent_total, currency=BASE_CURRENCY),
        MESSAGES["month_unplanned"].format(
            unplanned_spent=unplanned_spent, currency=BASE_CURRENCY
        ),
        MESSAGES["month_overspend"].format(
            overspend_total=overspend_total, currency=BASE_CURRENCY
        ),
        MESSAGES["month_separator"],
        MESSAGES["month_remaining"].format(
            remaining_tag=remaining_tag,
            remaining_overall=remaining_overall,
            currency=BASE_CURRENCY,
        ),
        "",
    ]

    if len(cats_sorted) > TOP_N:
        lines.append(
            MESSAGES["month_top_categories"].format(top_n=TOP_N, total=len(cats_sorted))
        )
        lines.append("")

    lines.append(MESSAGES["month_by_category"])

    if not show_cats:
        lines.append(MESSAGES["month_no_categories"])
    else:
        for c in show_cats:
            p = planned_by_cat.get(c, 0.0)
            s = spent_by_cat.get(c, 0.0)
            r = p - s

            label = c
            if p == 0.0 and s > 0.0:
                label = f"{c} (unplanned)"

            r_tag = "✅" if r >= 0 else "⚠️"
            over = overspend_by_cat.get(c, 0.0)
            over_str = f"  (+{over:.2f} over)" if over > 0 else ""

            lines.append(
                f"- {label}: {p:.2f} | {s:.2f} | {r_tag} {r:.2f} {BASE_CURRENCY}{over_str}"
            )

    await reply(update, context, "\n".join(lines), parse_mode="Markdown")
