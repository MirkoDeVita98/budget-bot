import shlex
from typing import List, Optional

SMART_QUOTES = {
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
}


def parse_quoted_args(message_text: Optional[str]) -> List[str]:
    """
    Splits Telegram command text into args supporting quotes.

    Examples:
      /add Food Snacks 10
      /add "Food & Drinks" "Taxi to airport" 20 EUR

    Returns only the arguments (command itself removed).
    """
    if not message_text:
        return []

    # normalize smart quotes to ascii quotes
    for k, v in SMART_QUOTES.items():
        message_text = message_text.replace(k, v)

    parts = shlex.split(message_text)
    if not parts:
        return []
    return parts[1:]
