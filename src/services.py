import calendar
from datetime import datetime
from typing import Optional, Dict, Tuple

from db import db
from config import BASE_CURRENCY
from fx import get_fx_rate, today_key

def month_key(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.now()
    return dt.strftime("%Y-%m")

def days_in_month(month: str) -> int:
    y = int(month[:4])
    m = int(month[5:7])
    return calendar.monthrange(y, m)[1]

def parse_amount(s: str) -> float:
    return float(s.strip().replace(",", "."))

def looks_like_currency(s: str) -> bool:
    s = s.strip().upper()
    return len(s) == 3 and s.isalpha()

# ---- Budgets ----
def upsert_budget(user_id: int, month: str, amount: float) -> None:
    conn = db()
    conn.execute(
        "INSERT INTO budgets(user_id, month, amount) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id, month) DO UPDATE SET amount=excluded.amount",
        (user_id, month, amount),
    )
    conn.commit()
    conn.close()

def get_month_budget(user_id: int, month: str) -> Optional[float]:
    conn = db()
    row = conn.execute("SELECT amount FROM budgets WHERE user_id=? AND month=?", (user_id, month)).fetchone()
    conn.close()
    return float(row["amount"]) if row else None

# ---- Rules ----
def add_rule(user_id: int, category: str, name: str, period: str, amount_chf: float) -> None:
    conn = db()
    conn.execute(
        "INSERT INTO rules(user_id, category, name, period, amount) VALUES (?, ?, ?, ?, ?)",
        (user_id, category, name, period, amount_chf),
    )
    conn.commit()
    conn.close()

def list_rules(user_id: int):
    conn = db()
    rows = conn.execute(
        "SELECT id, category, name, period, amount FROM rules WHERE user_id=? ORDER BY category, period, name",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows

def delete_rule(user_id: int, rule_id: int) -> bool:
    conn = db()
    cur = conn.execute("DELETE FROM rules WHERE user_id=? AND id=?", (user_id, rule_id))
    conn.commit()
    conn.close()
    return cur.rowcount > 0

def compute_planned_monthly_from_rules(user_id: int, month: str) -> Tuple[Dict[str, float], float]:
    d = days_in_month(month)
    conn = db()
    rows = conn.execute("SELECT category, period, amount FROM rules WHERE user_id=?", (user_id,)).fetchall()
    conn.close()

    planned_by_cat: Dict[str, float] = {}
    for r in rows:
        cat = r["category"]
        period = r["period"]
        amt = float(r["amount"])  # CHF stored

        if period == "daily":
            monthly = amt * d
        elif period == "monthly":
            monthly = amt
        else:  # yearly
            monthly = amt / 12.0

        planned_by_cat[cat] = planned_by_cat.get(cat, 0.0) + monthly

    return planned_by_cat, sum(planned_by_cat.values())

# ---- Expenses ----
def insert_expense(
    user_id: int,
    month: str,
    category: str,
    name: str,
    chf_amount: float,
    currency: str,
    original_amount: float,
    fx_rate: float,
    fx_date: str,
) -> None:
    conn = db()
    conn.execute(
        """
        INSERT INTO expenses(
            user_id, month, category, name,
            amount, created_at,
            currency, original_amount, chf_amount, fx_rate, fx_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id, month, category, name,
            chf_amount, datetime.now().isoformat(timespec="seconds"),
            currency, original_amount, chf_amount, fx_rate, fx_date
        ),
    )
    conn.commit()
    conn.close()

def compute_spent_this_month(user_id: int, month: str) -> Tuple[Dict[str, float], float]:
    conn = db()
    rows = conn.execute(
        """
        SELECT category, SUM(COALESCE(chf_amount, amount)) AS s
        FROM expenses
        WHERE user_id=? AND month=?
        GROUP BY category
        """,
        (user_id, month),
    ).fetchall()
    conn.close()

    spent_by_cat = {r["category"]: float(r["s"] or 0.0) for r in rows}
    return spent_by_cat, sum(spent_by_cat.values())

def delete_last_expense(user_id: int, month: str):
    conn = db()
    row = conn.execute(
        """
        SELECT id, category, name,
               COALESCE(currency, ?) AS currency,
               COALESCE(original_amount, COALESCE(chf_amount, amount)) AS original_amount,
               COALESCE(chf_amount, amount) AS chf_amount
        FROM expenses
        WHERE user_id=? AND month=?
        ORDER BY id DESC
        LIMIT 1
        """,
        (BASE_CURRENCY, user_id, month),
    ).fetchone()

    if not row:
        conn.close()
        return None

    conn.execute("DELETE FROM expenses WHERE id=?", (row["id"],))
    conn.commit()
    conn.close()
    return row

def reset_month_expenses(user_id: int, month: str) -> int:
    conn = db()
    cur = conn.execute("DELETE FROM expenses WHERE user_id=? AND month=?", (user_id, month))
    conn.commit()
    conn.close()
    return cur.rowcount

def reset_all_user_data(user_id: int) -> None:
    conn = db()
    conn.execute("DELETE FROM budgets WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM rules WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM expenses WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

# ---- Rule creation with optional FX (named monthly) ----
async def add_monthly_rule_named_fx(user_id: int, rule_name: str, amount: float, currency: str, category: str):
    currency = currency.upper()
    if currency == BASE_CURRENCY:
        fx_date = today_key()
        rate = 1.0
        chf = float(amount)
    else:
        fx_date, rate = await get_fx_rate(currency, BASE_CURRENCY)
        chf = float(amount) * float(rate)

    add_rule(user_id, category, rule_name, "monthly", chf)
    return fx_date, rate, chf

# ---- Expense creation with optional FX ----
async def add_expense_optional_fx(user_id: int, category: str, name: str, amount: float, currency: str, month: str):
    currency = currency.upper()
    if currency == BASE_CURRENCY:
        fx_date = today_key()
        rate = 1.0
        chf = float(amount)
    else:
        fx_date, rate = await get_fx_rate(currency, BASE_CURRENCY)
        chf = float(amount) * float(rate)

    insert_expense(user_id, month, category, name, chf, currency, float(amount), float(rate), str(fx_date))
    return fx_date, rate, chf
