"""Read-only repository for the demonstration core-banking dataset.

The production replacement should preserve these method contracts while calling a
bank-approved system of record over mTLS rather than opening the chat database.
"""
import sqlite3
from pathlib import Path

from .config import settings


def _connection() -> sqlite3.Connection:
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    return conn


def balance_for(customer_id: str) -> dict[str, str]:
    with _connection() as conn:
        row = conn.execute("SELECT account_number, currency, available_balance FROM accounts WHERE customer_id = ? AND status = 'active' ORDER BY id LIMIT 1", (customer_id,)).fetchone()
    if row is None:
        raise LookupError("No active account found for customer")
    # Account number remains in the tool response for a trusted channel, but the
    # coordinator removes it before forwarding any data to the third-party LLM.
    return dict(row)


def recent_transactions_for(customer_id: str, limit: int = 10) -> list[dict[str, str]]:
    with _connection() as conn:
        rows = conn.execute("""
            SELECT t.booking_date AS date, t.description, t.amount, t.currency
            FROM transactions t JOIN accounts a ON a.id = t.account_id
            WHERE a.customer_id = ? ORDER BY t.booking_date DESC, t.id DESC LIMIT ?
        """, (customer_id, limit)).fetchall()
    return [dict(row) for row in rows]
