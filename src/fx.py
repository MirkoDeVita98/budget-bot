from datetime import datetime
from typing import Tuple
import httpx

from db import db
from config import BASE_CURRENCY

_FX_MEM_CACHE = {}  # (cache_day, from_ccy, to_ccy) -> rate


def today_key(dt: datetime | None = None) -> str:
    dt = dt or datetime.now()
    return dt.strftime("%Y-%m-%d")


async def get_fx_rate(from_ccy: str, to_ccy: str = BASE_CURRENCY) -> Tuple[str, float]:
    from_ccy = from_ccy.upper()
    to_ccy = to_ccy.upper()
    if from_ccy == to_ccy:
        return today_key(), 1.0

    cache_day = today_key()
    mem_key = (cache_day, from_ccy, to_ccy)
    if mem_key in _FX_MEM_CACHE:
        return cache_day, _FX_MEM_CACHE[mem_key]

    conn = db()
    row = conn.execute(
        "SELECT rate FROM fx_rates WHERE fx_date=? AND from_ccy=? AND to_ccy=?",
        (cache_day, from_ccy, to_ccy),
    ).fetchone()
    conn.close()

    if row:
        rate = float(row["rate"])
        _FX_MEM_CACHE[mem_key] = rate
        return cache_day, rate

    url = "https://api.frankfurter.dev/v1/latest"
    params = {"from": from_ccy, "to": to_ccy}

    async with httpx.AsyncClient(timeout=12) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    api_date = str(data.get("date") or cache_day)
    rate = float(data["rates"][to_ccy])

    conn = db()
    conn.execute(
        "INSERT OR REPLACE INTO fx_rates(fx_date, from_ccy, to_ccy, rate) VALUES (?, ?, ?, ?)",
        (cache_day, from_ccy, to_ccy, rate),
    )
    conn.commit()
    conn.close()

    _FX_MEM_CACHE[mem_key] = rate
    return api_date, rate
