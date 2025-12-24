from .base import *
from db.services import (
    get_month_budget,
    ensure_month_budget,
    month_key,
    compute_planned_monthly_from_rules,
    compute_spent_this_month,
)
from dataclasses import dataclass
from typing import Dict


# Load messages from YAML file using relative path
_current_dir = Path(__file__).parent
_messages_path = _current_dir / "messages" / "report.yaml"
with open(_messages_path, "r") as file:
    MESSAGES = yaml.safe_load(file)

TOP_N = 8


@dataclass
class BudgetMetrics:
    """Container for calculated budget metrics."""

    overall_budget: float
    planned_total: float
    spent_total: float
    overspend_total: float
    remaining_overall: float
    unplanned_spent: float
    overspend_by_cat: Dict[str, float]

    @property
    def remaining_tag(self) -> str:
        """Get the emoji tag for remaining balance."""
        return "✅" if self.remaining_overall >= 0 else "🚨"


class BudgetReport:
    """Shared utility class for generating budget reports."""

    def __init__(
        self,
        planned_by_cat: Dict[str, float],
        spent_by_cat: Dict[str, float],
        overall_budget: float,
        currency: str = BASE_CURRENCY,
    ):
        self.planned_by_cat = planned_by_cat
        self.spent_by_cat = spent_by_cat
        self.overall_budget = overall_budget
        self.currency = currency
        self.all_cats = set(planned_by_cat.keys()) | set(spent_by_cat.keys())

    def calculate_metrics(self) -> BudgetMetrics:
        """Calculate all budget metrics (overspend, remaining, etc.)."""
        planned_total = sum(self.planned_by_cat.values())
        spent_total = sum(self.spent_by_cat.values())

        # Calculate overspend by category
        overspend_by_cat = {}
        overspend_total = 0.0
        for c in self.all_cats:
            p = self.planned_by_cat.get(c, 0.0)
            s = self.spent_by_cat.get(c, 0.0)
            over = max(0.0, s - p)
            overspend_by_cat[c] = over
            overspend_total += over

        # Calculate remaining and unplanned
        remaining_overall = self.overall_budget - planned_total - overspend_total
        unplanned_spent = sum(
            self.spent_by_cat.get(c, 0.0)
            for c in self.spent_by_cat.keys()
            if self.planned_by_cat.get(c, 0.0) == 0.0
        )

        return BudgetMetrics(
            overall_budget=self.overall_budget,
            planned_total=planned_total,
            spent_total=spent_total,
            overspend_total=overspend_total,
            remaining_overall=remaining_overall,
            unplanned_spent=unplanned_spent,
            overspend_by_cat=overspend_by_cat,
        )

    def sort_categories(self) -> list[str]:
        """Sort categories by importance: overspend desc, spent desc, name asc."""
        metrics = self.calculate_metrics()

        def sort_key(c: str):
            return (
                -metrics.overspend_by_cat.get(c, 0.0),
                -self.spent_by_cat.get(c, 0.0),
                c.lower(),
            )

        return sorted(self.all_cats, key=sort_key)

    def format_category_line(
        self, category: str, metrics: BudgetMetrics, show_unplanned_label: bool = False
    ) -> str:
        """Format a single category as a report line."""
        p = self.planned_by_cat.get(category, 0.0)
        s = self.spent_by_cat.get(category, 0.0)
        r = p - s

        label = category
        if show_unplanned_label and p == 0.0 and s > 0.0:
            label = f"{category} (unplanned)"

        r_tag = "✅" if r >= 0 else "⚠️"
        over = metrics.overspend_by_cat.get(category, 0.0)
        over_str = f"  (+{over:.2f} over)" if over > 0 else ""

        return (
            f"- {label}: {p:.2f} | {s:.2f} | {r_tag} {r:.2f} {self.currency}{over_str}"
        )

    def get_category_summary_lines(
        self,
        cats_to_show: list[str],
        metrics: BudgetMetrics,
        separate_planned: bool = True,
    ) -> list[str]:
        """Generate category summary lines, optionally separating planned/unplanned."""
        lines = []

        if not cats_to_show:
            lines.append(
                MESSAGES["status_no_categories"]
                if separate_planned
                else MESSAGES["month_no_categories"]
            )
            return lines

        if separate_planned:
            # Separate planned and unplanned
            planned_cats = [
                c for c in cats_to_show if self.planned_by_cat.get(c, 0.0) > 0.0
            ]
            unplanned_cats = [
                c for c in cats_to_show if self.planned_by_cat.get(c, 0.0) == 0.0
            ]

            if planned_cats:
                lines.append(MESSAGES["status_by_category_planned"])
                for c in planned_cats:
                    lines.append(self.format_category_line(c, metrics))

            if unplanned_cats:
                if planned_cats:
                    lines.append("")
                lines.append(MESSAGES["status_by_category_unplanned"])
                for c in unplanned_cats:
                    s = self.spent_by_cat.get(c, 0.0)
                    lines.append(f"- {c}: {s:.2f} {self.currency}")
        else:
            # Show all together (for month report)
            lines.append(MESSAGES["month_by_category"])
            for c in cats_to_show:
                lines.append(
                    self.format_category_line(c, metrics, show_unplanned_label=True)
                )

        return lines


@rollover_silent
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # args support quotes and smart quotes
    args = get_args(update)

    # Modes:
    # - /status                      -> compact current month
    # - /status full                 -> full current month
    # - /status <category...>        -> category detail for current month
    # - /status YYYY-MM              -> compact historical month
    # - /status YYYY-MM full         -> full historical month
    # - /status YYYY-MM <category>   -> category detail for historical month

    # Extract month from args if provided (YYYY-MM format)
    m = month_key()  # default to current month
    want_full = False
    filtered_args = list(args)

    if args and len(args[0]) == 7 and args[0][4] == "-":
        # First arg is a month (YYYY-MM format)
        m = args[0].strip()
        filtered_args = args[1:]

    # Check for "full" or "all" in remaining args
    want_full = any(a.lower() in ("full", "all") for a in filtered_args)
    filtered_args = [a for a in filtered_args if a.lower() not in ("full", "all")]

    # For historical months, use get_month_budget; for current, use ensure_month_budget
    is_current_month = m == month_key()

    if is_current_month:
        overall_budget, carried, carried_from = ensure_month_budget(user_id, m)
    else:
        overall_budget = get_month_budget(user_id, m)
        carried = False
        carried_from = None

    if overall_budget is None:
        # Different messages based on whether it's current month or historical
        if is_current_month:
            # Current month: show missing budget message and rules
            lines = [MESSAGES["no_budget_set"].format(month=m), ""]

            # Get and show current rules
            planned_by_cat, _ = compute_planned_monthly_from_rules(user_id, m)
            if planned_by_cat:
                lines.append("Current rules:")
                for cat in sorted(planned_by_cat.keys()):
                    lines.append(
                        f"  • {cat}: {planned_by_cat[cat]:.2f} {BASE_CURRENCY}"
                    )
            else:
                lines.append("(no rules configured yet)")

            return await reply(update, context, "\n".join(lines), parse_mode="Markdown")
        else:
            # Historical month: show "data not recorded" message
            return await reply(
                update, context, MESSAGES["historical_month_no_data"].format(month=m)
            )

    planned_by_cat, planned_total = compute_planned_monthly_from_rules(user_id, m)
    spent_by_cat, spent_total = compute_spent_this_month(user_id, m)

    # Create report generator
    report = BudgetReport(planned_by_cat, spent_by_cat, overall_budget)
    metrics = report.calculate_metrics()

    known_cats_sorted = sorted(report.all_cats)

    # If user provided something besides "full", treat it as a category query
    if filtered_args:
        cat = " ".join(filtered_args).strip()

        if cat not in report.all_cats:
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

    # Generate main report
    cats_sorted = report.sort_categories()
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
            planned_total=metrics.planned_total, currency=BASE_CURRENCY
        ),
        MESSAGES["status_spent"].format(
            spent_total=metrics.spent_total, currency=BASE_CURRENCY
        ),
        MESSAGES["status_unplanned"].format(
            unplanned_spent=metrics.unplanned_spent, currency=BASE_CURRENCY
        ),
        MESSAGES["status_overspend"].format(
            overspend_total=metrics.overspend_total, currency=BASE_CURRENCY
        ),
        MESSAGES["status_separator"],
        MESSAGES["status_remaining"].format(
            remaining_tag=metrics.remaining_tag,
            remaining_overall=metrics.remaining_overall,
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

    lines.extend(
        report.get_category_summary_lines(show_cats, metrics, separate_planned=True)
    )

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
