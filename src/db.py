import sqlite3
from config import DB_PATH

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_column(conn, table: str, col: str, coltype: str):
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if col not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")

def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            user_id INTEGER NOT NULL,
            month TEXT NOT NULL,
            amount REAL NOT NULL,
            PRIMARY KEY (user_id, month)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            period TEXT NOT NULL CHECK(period IN ('daily','monthly','yearly')),
            amount REAL NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            month TEXT NOT NULL,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fx_rates (
            fx_date TEXT NOT NULL,
            from_ccy TEXT NOT NULL,
            to_ccy TEXT NOT NULL,
            rate REAL NOT NULL,
            PRIMARY KEY (fx_date, from_ccy, to_ccy)
        )
    """)

    # multi-currency expense columns
    ensure_column(conn, "expenses", "currency", "TEXT")
    ensure_column(conn, "expenses", "original_amount", "REAL")
    ensure_column(conn, "expenses", "chf_amount", "REAL")
    ensure_column(conn, "expenses", "fx_rate", "REAL")
    ensure_column(conn, "expenses", "fx_date", "TEXT")

    conn.commit()
    conn.close()
