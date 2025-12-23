from datetime import datetime
from typing import Tuple, Set
from collections import OrderedDict
import httpx

from db.db import db
from config import BASE_CURRENCY


class InvalidCurrencyError(Exception):
    """Raised when an invalid currency code is provided."""

    pass


class CurrencyFormatError(InvalidCurrencyError):
    """Raised when currency code has invalid format (not 3 letters)."""

    pass


class CurrencyNotSupportedError(InvalidCurrencyError):
    """Raised when currency code is not supported by the exchange service."""

    pass


class BoundedLRUCache:
    """
    Simple bounded LRU (Least Recently Used) cache.
    When max_size is reached, the least recently used item is evicted.

    Useful for FX rates which grow unbounded if not managed.
    """

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = OrderedDict()

    def get(self, key):
        """Get value and mark as recently used."""
        if key not in self.cache:
            return None
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key, value):
        """Put value and evict LRU item if needed."""
        if key in self.cache:
            # Move to end if already exists
            self.cache.move_to_end(key)
        self.cache[key] = value

        # Evict LRU item if over capacity
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def __contains__(self, key):
        return key in self.cache

    def __len__(self):
        return len(self.cache)


# In-memory cache for FX rates: (cache_day, from_ccy, to_ccy) -> rate
# Limited to 1000 entries to prevent unbounded memory growth
_FX_MEM_CACHE = BoundedLRUCache(max_size=1000)

# Cache of available currencies from Frankfurter API
_AVAILABLE_CURRENCIES: Set[str] | None = None


async def _fetch_available_currencies() -> Set[str]:
    """Fetch available currencies from Frankfurter API."""
    global _AVAILABLE_CURRENCIES

    if _AVAILABLE_CURRENCIES is not None:
        return _AVAILABLE_CURRENCIES

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://api.frankfurter.dev/v1/currencies")
            r.raise_for_status()
            data = r.json()
            # API returns dict like {"EUR": "Euro", "USD": "US Dollar", ...}
            _AVAILABLE_CURRENCIES = set(data.keys())
            return _AVAILABLE_CURRENCIES
    except Exception:
        # If API fails, return empty set - will use 1.0 rate without validation
        _AVAILABLE_CURRENCIES = set()
        return _AVAILABLE_CURRENCIES


def today_key(dt: datetime | None = None) -> str:
    dt = dt or datetime.now()
    return dt.strftime("%Y-%m-%d")


def _is_valid_currency_format(code: str) -> bool:
    """Check if currency code has valid format (3 uppercase letters)."""
    return (
        isinstance(code, str) and len(code) == 3 and code.isalpha() and code.isupper()
    )


async def get_fx_rate(from_ccy: str, to_ccy: str = BASE_CURRENCY) -> Tuple[str, float]:
    from_ccy = from_ccy.upper()
    to_ccy = to_ccy.upper()

    # First: validate format (3 uppercase letters)
    if not _is_valid_currency_format(from_ccy):
        raise CurrencyFormatError(
            f"Currency must be 3 letters (e.g., EUR, USD). Got: {from_ccy}"
        )
    if not _is_valid_currency_format(to_ccy):
        raise CurrencyFormatError(
            f"Currency must be 3 letters (e.g., EUR, USD). Got: {to_ccy}"
        )

    # Second: validate availability against the API list
    available = await _fetch_available_currencies()

    # If API failed to fetch currencies (empty set), skip validation and return 1.0
    if not available:
        return today_key(), 1.0

    # Only validate if we successfully fetched the list from API
    if from_ccy not in available:
        raise CurrencyNotSupportedError(f"Currency not supported: {from_ccy}")
    if to_ccy not in available:
        raise CurrencyNotSupportedError(f"Currency not supported: {to_ccy}")

    if from_ccy == to_ccy:
        return today_key(), 1.0

    cache_day = today_key()
    mem_key = (cache_day, from_ccy, to_ccy)

    # Check in-memory cache first
    cached_rate = _FX_MEM_CACHE.get(mem_key)
    if cached_rate is not None:
        return cache_day, cached_rate

    # Check database
    conn = db()
    row = conn.execute(
        "SELECT rate FROM fx_rates WHERE fx_date=? AND from_ccy=? AND to_ccy=?",
        (cache_day, from_ccy, to_ccy),
    ).fetchone()

    if row:
        rate = float(row["rate"])
        _FX_MEM_CACHE.put(mem_key, rate)
        return cache_day, rate

    # Fetch from API
    url = "https://api.frankfurter.dev/v1/latest"
    params = {"from": from_ccy, "to": to_ccy}

    async with httpx.AsyncClient(timeout=12) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    api_date = str(data.get("date") or cache_day)
    rate = float(data["rates"][to_ccy])

    # Store in database
    conn = db()
    conn.execute(
        "INSERT OR REPLACE INTO fx_rates(fx_date, from_ccy, to_ccy, rate) VALUES (?, ?, ?, ?)",
        (cache_day, from_ccy, to_ccy, rate),
    )
    conn.commit()

    # Store in memory cache (with LRU eviction)
    _FX_MEM_CACHE.put(mem_key, rate)
    return api_date, rate
