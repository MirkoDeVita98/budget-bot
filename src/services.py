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
def get_month_budget(user_id: int, month: str):
    conn = db()
    row = conn.execute(
        "SELECT amount FROM budgets WHERE user_id=? AND month=?",
        (user_id, month),
    ).fetchone()
    conn.close()
    return float(row["amount"]) if row else None


def ensure_month_budget(
    user_id: int, month: str
) -> Tuple[Optional[float], bool, Optional[str]]:
    """
    Returns (amount, was_carried, carried_from_month).

    - If budget exists for `month` -> (amount, False, None)
    - If not, copies the most recent previous budget into `month` (persisting it),
      then -> (amount, True, <previous_month>)
    - If no previous budget exists -> (None, False, None)
    """
    conn = db()

    # 1) Already exists
    row = conn.execute(
        "SELECT amount FROM budgets WHERE user_id=? AND month=?",
        (user_id, month),
    ).fetchone()
    if row:
        conn.close()
        return float(row["amount"]), False, None

    # 2) Find most recent prior budget
    row = conn.execute(
        "SELECT month, amount FROM budgets WHERE user_id=? ORDER BY month DESC LIMIT 1",
        (user_id,),
    ).fetchone()

    if not row:
        conn.close()
        return None, False, None

    prev_month = str(row["month"])
    amount = float(row["amount"])

    # 3) Persist into requested month
    conn.execute(
        "INSERT INTO budgets(user_id, month, amount) VALUES (?, ?, ?)",
        (user_id, month, amount),
    )
    conn.commit()
    conn.close()

    return amount, True, prev_month


def upsert_budget(user_id: int, month: str, amount: float) -> None:
    conn = db()
    conn.execute(
        "INSERT INTO budgets(user_id, month, amount) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id, month) DO UPDATE SET amount=excluded.amount",
        (user_id, month, amount),
    )
    conn.commit()
    conn.close()


# ---- Rules ----
def add_rule(
    user_id: int, category: str, name: str, period: str, amount_chf: float
) -> None:
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


def compute_planned_monthly_from_rules(
    user_id: int, month: str
) -> Tuple[Dict[str, float], float]:
    d = days_in_month(month)

    # Use snapshot if it exists for that month, otherwise fallback to current rules
    rows, used_snapshot = get_rules_for_month(user_id, month)

    planned_by_cat: Dict[str, float] = {}
    for r in rows:
        cat = r["category"]
        period = r["period"]
        amt = float(r["amount"])  # stored in BASE_CURRENCY

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
            user_id,
            month,
            category,
            name,
            chf_amount,
            datetime.now().isoformat(timespec="seconds"),
            currency,
            original_amount,
            chf_amount,
            fx_rate,
            fx_date,
        ),
    )
    conn.commit()
    conn.close()


def compute_spent_this_month(
    user_id: int, month: str
) -> Tuple[Dict[str, float], float]:
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


def list_expenses_filtered(
    user_id: int, month: str, *, limit: int = 50, category: str | None = None
):
    conn = db()

    if category:
        rows = conn.execute(
            """
            SELECT id, month, category, name, created_at,
                   COALESCE(currency, ?) AS currency,
                   COALESCE(original_amount, COALESCE(chf_amount, amount)) AS original_amount,
                   COALESCE(chf_amount, amount) AS chf_amount
            FROM expenses
            WHERE user_id=? AND month=? AND category=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (BASE_CURRENCY, user_id, month, category, int(limit)),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, month, category, name, created_at,
                   COALESCE(currency, ?) AS currency,
                   COALESCE(original_amount, COALESCE(chf_amount, amount)) AS original_amount,
                   COALESCE(chf_amount, amount) AS chf_amount
            FROM expenses
            WHERE user_id=? AND month=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (BASE_CURRENCY, user_id, month, int(limit)),
        ).fetchall()

    conn.close()
    return rows


def delete_expense_by_id(user_id: int, expense_id: int) -> bool:
    conn = db()
    cur = conn.execute(
        "DELETE FROM expenses WHERE user_id=? AND id=?",
        (user_id, int(expense_id)),
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


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
    cur = conn.execute(
        "DELETE FROM expenses WHERE user_id=? AND month=?", (user_id, month)
    )
    conn.commit()
    conn.close()
    return cur.rowcount


def delete_budget_for_month(user_id: int, month: str) -> int:
    conn = db()
    cur = conn.execute(
        "DELETE FROM budgets WHERE user_id=? AND month=?",
        (user_id, month),
    )
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


# ---- Rule creation with optional FX ----
async def add_rule_named_fx(
    user_id: int,
    rule_name: str,
    amount: float,
    currency: str,
    category: str,
    period: str = "monthly",
):
    """Add a rule with optional FX conversion. Period can be 'daily', 'monthly', or 'yearly'."""
    currency = currency.upper()
    if currency == BASE_CURRENCY:
        fx_date = today_key()
        rate = 1.0
        chf = float(amount)
    else:
        fx_date, rate = await get_fx_rate(currency, BASE_CURRENCY)
        chf = float(amount) * float(rate)

    add_rule(user_id, category, rule_name, period, chf)
    return fx_date, rate, chf


# ---- Expense creation with optional FX ----
async def add_expense_optional_fx(
    user_id: int, category: str, name: str, amount: float, currency: str, month: str
):
    currency = currency.upper()
    if currency == BASE_CURRENCY:
        fx_date = today_key()
        rate = 1.0
        chf = float(amount)
    else:
        fx_date, rate = await get_fx_rate(currency, BASE_CURRENCY)
        chf = float(amount) * float(rate)

    insert_expense(
        user_id,
        month,
        category,
        name,
        chf,
        currency,
        float(amount),
        float(rate),
        str(fx_date),
    )
    return fx_date, rate, chf


# --- Snapshots for rules ---
def get_last_seen_month(user_id: int) -> str | None:
    conn = db()
    row = conn.execute(
        "SELECT last_seen_month FROM user_state WHERE user_id=?",
        (user_id,),
    ).fetchone()
    conn.close()
    return row["last_seen_month"] if row else None


def set_last_seen_month(user_id: int, month: str) -> None:
    conn = db()
    conn.execute(
        """
        INSERT INTO user_state(user_id, last_seen_month)
        VALUES(?, ?)
        ON CONFLICT(user_id) DO UPDATE SET last_seen_month=excluded.last_seen_month
        """,
        (user_id, month),
    )
    conn.commit()
    conn.close()


def snapshot_rules_for_month_if_missing(user_id: int, month: str) -> bool:
    """
    Creates rule snapshots for `month` if they don't exist.
    Returns True if snapshot was created, False if already existed (or no rules).
    """
    conn = db()

    exists = conn.execute(
        "SELECT 1 FROM rule_snapshots WHERE user_id=? AND month=? LIMIT 1",
        (user_id, month),
    ).fetchone()
    if exists:
        conn.close()
        return False

    rules = conn.execute(
        "SELECT category, name, period, amount FROM rules WHERE user_id=?",
        (user_id,),
    ).fetchall()

    if not rules:
        conn.close()
        return False

    conn.executemany(
        """
        INSERT OR IGNORE INTO rule_snapshots(user_id, month, category, name, period, amount)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (user_id, month, r["category"], r["name"], r["period"], float(r["amount"]))
            for r in rules
        ],
    )
    conn.commit()
    conn.close()
    return True


def ensure_rollover_snapshot(
    user_id: int, current_month: str
) -> tuple[bool, str | None]:
    """
    Call this at the start of EVERY command.
    If user crossed into a new month since last time, snapshot the previous month rules.
    Returns: (snapshot_created, snapshotted_month)
    """
    last = get_last_seen_month(user_id)

    # First ever interaction: just store current month
    if last is None:
        set_last_seen_month(user_id, current_month)
        return False, None

    if last == current_month:
        return False, None

    # Month changed: snapshot the last seen month (the month we just left)
    created = snapshot_rules_for_month_if_missing(user_id, last)
    set_last_seen_month(user_id, current_month)
    return created, last


def get_rules_for_month(user_id: int, month: str):
    """
    Returns (rows, used_snapshot: bool)
    rows are dict-like rows with: category, name, period, amount
    """
    conn = db()
    snap = conn.execute(
        "SELECT category, name, period, amount FROM rule_snapshots WHERE user_id=? AND month=?",
        (user_id, month),
    ).fetchall()

    if snap:
        conn.close()
        return snap, True

    # fallback to current rules if no snapshot exists
    rules = conn.execute(
        "SELECT category, name, period, amount FROM rules WHERE user_id=?",
        (user_id,),
    ).fetchall()
    conn.close()
    return rules, False
