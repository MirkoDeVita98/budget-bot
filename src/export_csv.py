import csv
import io

from db import db
from config import BASE_CURRENCY


def _rows_to_csv_bytes(headers: list[str], rows: list[list[str]]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def export_expenses_csv(user_id: int, month: str) -> bytes:
    conn = db()
    rows = conn.execute(
        """
        SELECT
            id, created_at, month, category, name,
            COALESCE(currency, ?) AS currency,
            COALESCE(original_amount, COALESCE(chf_amount, amount)) AS original_amount,
            COALESCE(chf_amount, amount) AS chf_amount,
            COALESCE(fx_rate, 1.0) AS fx_rate,
            COALESCE(fx_date, '') AS fx_date
        FROM expenses
        WHERE user_id=? AND month=?
        ORDER BY created_at ASC, id ASC
        """,
        (BASE_CURRENCY, user_id, month),
    ).fetchall()

    out = []
    for r in rows:
        out.append(
            [
                str(r["id"]),
                str(r["created_at"]),
                str(r["month"]),
                str(r["category"]),
                str(r["name"]),
                str(r["currency"]),
                f"{float(r['original_amount']):.2f}",
                f"{float(r['chf_amount']):.2f}",
                f"{float(r['fx_rate']):.6f}",
                str(r["fx_date"]),
            ]
        )

    headers = [
        "id",
        "created_at",
        "month",
        "category",
        "name",
        "currency",
        "original_amount",
        f"{BASE_CURRENCY.lower()}_amount",
        "fx_rate",
        "fx_date",
    ]
    return _rows_to_csv_bytes(headers, out)


def export_rules_csv(user_id: int) -> bytes:
    conn = db()
    rows = conn.execute(
        """
        SELECT id, category, name, period, amount
        FROM rules
        WHERE user_id=?
        ORDER BY category, period, name
        """,
        (user_id,),
    ).fetchall()

    out = []
    for r in rows:
        out.append(
            [
                str(r["id"]),
                str(r["category"]),
                str(r["name"]),
                str(r["period"]),
                f"{float(r['amount']):.2f}",
                BASE_CURRENCY,
            ]
        )

    headers = ["id", "category", "name", "period", "amount", "currency"]
    return _rows_to_csv_bytes(headers, out)


def export_budgets_csv(user_id: int) -> bytes:
    conn = db()
    rows = conn.execute(
        """
        SELECT month, amount
        FROM budgets
        WHERE user_id=?
        ORDER BY month ASC
        """,
        (user_id,),
    ).fetchall()

    out = []
    for r in rows:
        out.append(
            [
                str(r["month"]),
                f"{float(r['amount']):.2f}",
                BASE_CURRENCY,
            ]
        )

    headers = ["month", "amount", "currency"]
    return _rows_to_csv_bytes(headers, out)
