"""
Pagination system for handling large lists of expenses and other items.
Uses inline buttons for navigation instead of text-based limits.
"""

from dataclasses import dataclass
from typing import List, Callable, Any, Optional, Tuple


@dataclass
class PaginationState:
    """Tracks pagination state for a single list view."""

    items: List[Any]  # All items
    current_page: int = 0  # 0-indexed
    items_per_page: int = 10
    filter_category: Optional[str] = None
    filter_month: Optional[str] = None
    callback_prefix: str = "expenses"  # For callback query routing

    @property
    def total_pages(self) -> int:
        """Total number of pages."""
        if not self.items:
            return 1
        return (len(self.items) + self.items_per_page - 1) // self.items_per_page

    @property
    def has_previous(self) -> bool:
        """Can go to previous page."""
        return self.current_page > 0

    @property
    def has_next(self) -> bool:
        """Can go to next page."""
        return self.current_page < self.total_pages - 1

    @property
    def current_page_items(self) -> List[Any]:
        """Get items for current page."""
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        return self.items[start:end]

    def next_page(self) -> bool:
        """Go to next page. Returns True if successful."""
        if self.has_next:
            self.current_page += 1
            return True
        return False

    def previous_page(self) -> bool:
        """Go to previous page. Returns True if successful."""
        if self.has_previous:
            self.current_page -= 1
            return True
        return False

    def reset(self) -> None:
        """Reset to first page."""
        self.current_page = 0

    def to_dict(self) -> dict:
        """Convert to dict for storage in context.user_data."""
        return {
            "items": self.items,
            "current_page": self.current_page,
            "items_per_page": self.items_per_page,
            "filter_category": self.filter_category,
            "filter_month": self.filter_month,
            "callback_prefix": self.callback_prefix,
        }

    @staticmethod
    def from_dict(data: dict) -> "PaginationState":
        """Restore from dict stored in context.user_data."""
        return PaginationState(
            items=data.get("items", []),
            current_page=data.get("current_page", 0),
            items_per_page=data.get("items_per_page", 10),
            filter_category=data.get("filter_category"),
            filter_month=data.get("filter_month"),
            callback_prefix=data.get("callback_prefix", "expenses"),
        )


def get_pagination_buttons(
    prefix: str,
    current_page: int,
    total_pages: int,
    has_previous: bool,
    has_next: bool,
) -> Tuple[List[Tuple[str, str]], str]:
    """
    Generate inline button definitions for pagination.

    Returns:
        Tuple of (buttons_data, footer_text)
        buttons_data: List of (label, callback_data) tuples
        footer_text: "Page X/Y" text
    """
    buttons = []

    if has_previous:
        buttons.append(("⬅️ Previous", f"{prefix}_prev"))

    # Add page indicator
    buttons.append((f"{current_page + 1}/{total_pages}", f"{prefix}_info"))

    if has_next:
        buttons.append(("Next ➡️", f"{prefix}_next"))

    footer = f"Page {current_page + 1}/{total_pages}"

    return buttons, footer


def format_pagination_footer(
    current_page: int,
    total_pages: int,
    item_count: int,
    items_per_page: int,
) -> str:
    """
    Format a footer string showing pagination info.

    Example: "Page 2/5 (showing items 11-20 of 48)"
    """
    start_item = current_page * items_per_page + 1
    end_item = min((current_page + 1) * items_per_page, item_count)

    return f"Page {current_page + 1}/{total_pages} (showing items {start_item}-{end_item} of {item_count})"


def get_period_emoji(period: str) -> str:
    """
    Convert period name to emoji indicator.

    Args:
        period: Period name (daily, weekly, monthly, yearly)

    Returns:
        Emoji (☀️, 📆, 📅, 📊) or original if unknown
    """
    emoji_map = {
        "daily": "☀️",
        "weekly": "📆",
        "monthly": "📅",
        "yearly": "📊",
    }
    return emoji_map.get(period, period)
