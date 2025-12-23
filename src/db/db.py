import sqlite3
import threading
from contextlib import contextmanager
from config import DB_PATH


class DatabasePool:
    """
    Simple connection pool for SQLite.

    Since SQLite has limited concurrent write support, we use thread-local
    storage to ensure each thread/coroutine gets its own connection.
    This avoids "database is locked" errors and improves performance.
    """

    def __init__(
        self, db_path: str, timeout: float = 30.0, check_same_thread: bool = False
    ):
        self.db_path = db_path
        self.timeout = timeout
        self.check_same_thread = check_same_thread
        self._local = threading.local()

    def get_connection(self) -> sqlite3.Connection:
        """Get or create a connection for the current thread."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path,
                timeout=self.timeout,
                check_same_thread=self.check_same_thread,
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def close_connection(self) -> None:
        """Close the connection for the current thread."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None

    @contextmanager
    def get_db(self):
        """Context manager for getting a database connection."""
        conn = self.get_connection()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise

    def shutdown(self) -> None:
        """Close all connections (for cleanup on exit)."""
        self.close_connection()


# Global connection pool instance
_pool = DatabasePool(DB_PATH)


def db():
    """Get a database connection from the pool."""
    return _pool.get_connection()


def get_db_context():
    """Get a context manager for database operations."""
    return _pool.get_db()


def close_db():
    """Close the current thread's database connection."""
    _pool.close_connection()


def shutdown_db_pool():
    """Shutdown the entire connection pool."""
    _pool.shutdown()


def ensure_column(conn, table: str, col: str, coltype: str):
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if col not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS budgets (
            user_id INTEGER NOT NULL,
            month TEXT NOT NULL,
            amount REAL NOT NULL,
            PRIMARY KEY (user_id, month)
        )
    """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            period TEXT NOT NULL CHECK(period IN ('daily','weekly','monthly','yearly')),
            amount REAL NOT NULL
        )
    """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            month TEXT NOT NULL,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS fx_rates (
            fx_date TEXT NOT NULL,
            from_ccy TEXT NOT NULL,
            to_ccy TEXT NOT NULL,
            rate REAL NOT NULL,
            PRIMARY KEY (fx_date, from_ccy, to_ccy)
        )
    """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_state (
            user_id INTEGER PRIMARY KEY,
            last_seen_month TEXT
        )
    """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS rule_snapshots (
            user_id INTEGER NOT NULL,
            month TEXT NOT NULL,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            period TEXT NOT NULL CHECK(period IN ('daily','weekly','monthly','yearly')),
            amount REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, month, category, name, period)
        )
    """
    )

    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_expenses_user_month ON expenses(user_id, month)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_expenses_user_month_cat ON expenses(user_id, month, category)"
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rules_user ON rules(user_id)")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_rule_snapshots_user_month ON rule_snapshots(user_id, month)"
    )

    # multi-currency expense columns
    ensure_column(conn, "expenses", "currency", "TEXT")
    ensure_column(conn, "expenses", "original_amount", "REAL")
    ensure_column(conn, "expenses", "chf_amount", "REAL")
    ensure_column(conn, "expenses", "fx_rate", "REAL")
    ensure_column(conn, "expenses", "fx_date", "TEXT")

    conn.commit()
