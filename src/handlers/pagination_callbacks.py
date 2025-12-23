"""
Pagination callback handlers for inline buttons in expenses and rules lists.

This module handles the Previous/Next button callbacks for pagination
in the expenses and rules commands.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.pagination import PaginationState, get_pagination_buttons, get_period_emoji
from pathlib import Path
from config import BASE_CURRENCY
import yaml

# Load messages from YAML files using relative path
_current_dir = Path(__file__).parent
_expenses_messages_path = _current_dir / "commands" / "messages" / "expenses.yaml"
_rules_messages_path = _current_dir / "commands" / "messages" / "rules.yaml"

with open(_expenses_messages_path, "r") as file:
    EXPENSES_MESSAGES = yaml.safe_load(file)
with open(_rules_messages_path, "r") as file:
    RULES_MESSAGES = yaml.safe_load(file)


async def expenses_pagination_prev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Previous button click for expenses pagination."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Get the stored pagination state
    state_dict = context.user_data.get("expenses_pagination", {})
    if not state_dict:
        await query.answer("Pagination state not found. Please refresh by running /expenses again.")
        return
    
    # Restore state from dict
    state = PaginationState.from_dict(state_dict)
    
    # Go to previous page
    if not state.previous_page():
        await query.answer("Already at first page")
        return
    
    # Format the page
    page_text = _format_expenses_page(state)
    
    # Get pagination buttons
    buttons_data, footer = get_pagination_buttons(
        prefix="expenses",
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
    
    # Update the message
    try:
        await query.edit_message_text(page_text, reply_markup=reply_markup)
    except Exception as e:
        await query.answer(f"Error updating message: {str(e)}")
    
    # Save updated state
    context.user_data["expenses_pagination"] = state.to_dict()
    
    await query.answer()


async def expenses_pagination_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Next button click for expenses pagination."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Get the stored pagination state
    state_dict = context.user_data.get("expenses_pagination", {})
    if not state_dict:
        await query.answer("Pagination state not found. Please refresh by running /expenses again.")
        return
    
    # Restore state from dict
    state = PaginationState.from_dict(state_dict)
    
    # Go to next page
    if not state.next_page():
        await query.answer("Already at last page")
        return
    
    # Format the page
    page_text = _format_expenses_page(state)
    
    # Get pagination buttons
    buttons_data, footer = get_pagination_buttons(
        prefix="expenses",
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
    
    # Update the message
    try:
        await query.edit_message_text(page_text, reply_markup=reply_markup)
    except Exception as e:
        await query.answer(f"Error updating message: {str(e)}")
    
    # Save updated state
    context.user_data["expenses_pagination"] = state.to_dict()
    
    await query.answer()


async def rules_pagination_prev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Previous button click for rules pagination."""
    query = update.callback_query
    
    # Get the stored pagination state
    state_dict = context.user_data.get("rules_pagination", {})
    if not state_dict:
        await query.answer("Pagination state not found. Please refresh by running /rules again.")
        return
    
    # Restore state from dict
    state = PaginationState.from_dict(state_dict)
    
    # Go to previous page
    if not state.previous_page():
        await query.answer("Already at first page")
        return
    
    # Format the page
    page_text = _format_rules_page(state, is_first_page=False)
    
    # Get pagination buttons
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
    
    # Update the message
    try:
        await query.edit_message_text(page_text, reply_markup=reply_markup)
    except Exception as e:
        await query.answer(f"Error updating message: {str(e)}")
    
    # Save updated state
    context.user_data["rules_pagination"] = state.to_dict()
    
    await query.answer()


async def rules_pagination_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Next button click for rules pagination."""
    query = update.callback_query
    
    # Get the stored pagination state
    state_dict = context.user_data.get("rules_pagination", {})
    if not state_dict:
        await query.answer("Pagination state not found. Please refresh by running /rules again.")
        return
    
    # Restore state from dict
    state = PaginationState.from_dict(state_dict)
    
    # Go to next page
    if not state.next_page():
        await query.answer("Already at last page")
        return
    
    # Format the page
    page_text = _format_rules_page(state, is_first_page=False)
    
    # Get pagination buttons
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
    
    # Update the message
    try:
        await query.edit_message_text(page_text, reply_markup=reply_markup)
    except Exception as e:
        await query.answer(f"Error updating message: {str(e)}")
    
    # Save updated state
    context.user_data["rules_pagination"] = state.to_dict()
    
    await query.answer()


def _format_expenses_page(state: PaginationState) -> str:
    """
    Format a single page of expenses from pagination state.
    
    Args:
        state: PaginationState with all expenses
        user_id: User ID (for reference)
    
    Returns:
        Formatted page content
    """
    rows = state.current_page_items
    
    title = EXPENSES_MESSAGES["expenses_title"].format(
        month=state.filter_month or "current",
        category=f' — "{state.filter_category}"' if state.filter_category else ""
    )
    
    if not rows:
        return EXPENSES_MESSAGES["expenses_no_rows"].format(title=title)
    
    # Calculate per-page total
    page_total = sum(float(r["chf_amount"]) for r in rows)
    
    # Calculate grand total from all items
    grand_total = sum(float(r["chf_amount"]) for r in state.items)
    
    lines = [
        EXPENSES_MESSAGES["expenses_summary"].format(
            title=title,
            count=len(rows),
            total=page_total,
            currency=BASE_CURRENCY,
        ),
    ]
    
    # Add grand total if there are more items than shown on this page
    if grand_total != page_total:
        lines.append(f"📊 Total (all pages): {grand_total:.2f} {BASE_CURRENCY}")
    
    lines.append("")
    
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
                f"[{eid:4d}] [{cat}] {name:<30} {chf:>8.2f} {BASE_CURRENCY} ({created})"
            )
        else:
            lines.append(
                f"[{eid:4d}] [{cat}] {name:<30} {orig:>8.2f} {cur} → {chf:>8.2f} {BASE_CURRENCY} ({created})"
            )
    
    lines.append("")
    lines.append(EXPENSES_MESSAGES["expenses_delete_tip"])
    
    if state.filter_category is None:
        lines.append(EXPENSES_MESSAGES["expenses_filter_tip"])
    
    return "\n".join(lines)


def _format_rules_page(state: PaginationState, is_first_page: bool = True) -> str:
    """
    Format a single page of rules from pagination state, grouped by category.
    
    Args:
        state: PaginationState with all rules
        is_first_page: Whether this is the first page (shows legend at end)
    
    Returns:
        Formatted page content with rules grouped by category
    """
    rows = state.current_page_items
    max_name_len = 20  # Cap name length
    
    # Group rules by category
    categories = {}
    for r in rows:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "rules": []}
        categories[cat]["rules"].append(r)
        categories[cat]["total"] += float(r["amount"])
    
    # Build output
    lines = [RULES_MESSAGES["rules_list_header"], ""]
    
    for category in sorted(categories.keys()):
        cat_data = categories[category]
        lines.append(f"📁 {category} — Total: {cat_data['total']:.2f} {BASE_CURRENCY}")
        
        for r in cat_data["rules"]:
            period_emoji = get_period_emoji(r['period'])
            # Cap name and pad to max_name_len
            name = r['name'][:max_name_len].ljust(max_name_len)
            lines.append(
                f"[{r['id']:3d}] {name} {float(r['amount']):>8.2f} {period_emoji}"
            )
        lines.append("")
    
    # Add footer with legend only on first page
    if is_first_page:
        lines.append(RULES_MESSAGES["rules_list_footer"])
    
    return "\n".join(lines)
