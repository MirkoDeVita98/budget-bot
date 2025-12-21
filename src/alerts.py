from dataclasses import dataclass
from typing import Dict, Tuple

from config import BASE_CURRENCY


@dataclass
class AlertResult:
    messages: list[str]


def compute_overspend_total(
    planned_by_cat: Dict[str, float], spent_by_cat: Dict[str, float]
) -> float:
    all_cats = set(planned_by_cat.keys()) | set(spent_by_cat.keys())
    total = 0.0
    for c in all_cats:
        p = planned_by_cat.get(c, 0.0)
        s = spent_by_cat.get(c, 0.0)
        total += max(0.0, s - p)
    return total


def compute_unplanned_spend(
    planned_by_cat: Dict[str, float], spent_by_cat: Dict[str, float]
) -> float:
    total = 0.0
    for c, s in spent_by_cat.items():
        if planned_by_cat.get(c, 0.0) == 0.0:
            total += s
    return total


def compute_remaining_overall(
    budget: float,
    planned_total: float,
    planned_by_cat: Dict[str, float],
    spent_by_cat: Dict[str, float],
) -> Tuple[float, float]:
    """
    Returns (remaining_overall, overspend_total)
    remaining = budget - planned_total - Σ max(0, spent_c - planned_c)
    """
    overspend_total = compute_overspend_total(planned_by_cat, spent_by_cat)
    remaining = budget - planned_total - overspend_total
    return remaining, overspend_total


def check_alerts_after_add(
    *,
    category: str,
    prev_planned_by_cat: Dict[str, float],
    prev_spent_by_cat: Dict[str, float],
    new_spent_by_cat: Dict[str, float],
    budget: float | None,
    planned_total: float,
    new_planned_by_cat: Dict[str, float],
) -> AlertResult:
    """
    Alerts:
    - Category exceeded (crossing from >=0 to <0 for that category remaining)
    - Overall remaining became negative (crossing)
    - Optional: warn when overall remaining drops below 10% of budget
    """
    msgs: list[str] = []

    # CATEGORY alert
    p = prev_planned_by_cat.get(category, 0.0)
    s_prev = prev_spent_by_cat.get(category, 0.0)
    s_new = new_spent_by_cat.get(category, 0.0)

    prev_remaining_cat = p - s_prev
    new_remaining_cat = p - s_new

    # Only alert category exceeded if the category is planned (p > 0)
    if p > 0 and prev_remaining_cat >= 0 and new_remaining_cat < 0:
        msgs.append(
            f"⚠️ Category exceeded: *{category}*\n"
            f"Planned: {p:.2f} {BASE_CURRENCY}\n"
            f"Spent: {s_new:.2f} {BASE_CURRENCY}\n"
            f"Over: {abs(new_remaining_cat):.2f} {BASE_CURRENCY}"
        )

    # OVERALL alerts (only if a budget exists)
    if budget is not None:
        prev_overall, _ = compute_remaining_overall(
            budget, planned_total, prev_planned_by_cat, prev_spent_by_cat
        )
        new_overall, _ = compute_remaining_overall(
            budget, planned_total, new_planned_by_cat, new_spent_by_cat
        )

        if prev_overall >= 0 and new_overall < 0:
            msgs.append(
                f"🚨 Overall budget exceeded!\n"
                f"Remaining overall is now: {new_overall:.2f} {BASE_CURRENCY}"
            )

        # Optional warning at 10% remaining
        if budget > 0:
            threshold = 0.10 * budget
            if (
                prev_overall >= threshold
                and new_overall < threshold
                and new_overall >= 0
            ):
                msgs.append(
                    f"🔔 Low budget warning\n"
                    f"Remaining overall: {new_overall:.2f} {BASE_CURRENCY} (< 10% of budget)"
                )

    return AlertResult(messages=msgs)
