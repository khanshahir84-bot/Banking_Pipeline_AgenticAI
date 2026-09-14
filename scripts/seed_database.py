#!/usr/bin/env python3
"""Create an idempotent local banking demonstration database with 50 transactions.

Usage: python scripts/seed_database.py --database /data/banking_chat.db
"""
import argparse
import sqlite3
from datetime import date, timedelta
from pathlib import Path


def seed(database_path: str, reset: bool = False) -> None:
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as conn:
        conn.executescript("""
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY, customer_id TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY, customer_id TEXT NOT NULL, account_number TEXT NOT NULL UNIQUE,
                currency TEXT NOT NULL, available_balance TEXT NOT NULL, status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL, booking_date TEXT NOT NULL,
                description TEXT NOT NULL, amount TEXT NOT NULL, currency TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES accounts(id)
            );
        """)
        existing = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        if existing and not reset:
            print(f"Database already contains {existing} transactions; use --reset to recreate demo data")
            return
        conn.execute("DELETE FROM transactions")
        conn.execute("DELETE FROM accounts")
        conn.execute("DELETE FROM customers")
        customer_numbers = (42, 2, 3, 4, 5, 6, 7, 8, 9, 10)
        customers = [(index, f"customer-{number}", f"Demo Customer {number}") for index, number in enumerate(customer_numbers, start=1)]
        conn.executemany("INSERT INTO customers(id, customer_id, display_name) VALUES (?, ?, ?)", customers)
        accounts = [(index, customer_id, f"90000000{index:04d}", "USD", f"{1250 + index * 103:.2f}", "active") for index, customer_id, _ in customers]
        conn.executemany("INSERT INTO accounts(id, customer_id, account_number, currency, available_balance, status) VALUES (?, ?, ?, ?, ?, ?)", accounts)
        descriptions = ("Salary credit", "Grocer", "Electric utility", "Coffee shop", "Transit pass")
        rows = []
        start = date(2026, 9, 12)
        for customer in range(1, 11):
            for offset, description in enumerate(descriptions):
                amount = "2500.00" if offset == 0 else f"-{(offset * 11.25 + customer):.2f}"
                rows.append(((customer - 1) * 5 + offset + 1, customer, str(start - timedelta(days=offset)), description, amount, "USD"))
        conn.executemany("INSERT INTO transactions(id, account_id, booking_date, description, amount, currency) VALUES (?, ?, ?, ?, ?, ?)", rows)
    print(f"Seeded {len(customers)} customers, {len(accounts)} accounts, and {len(rows)} transactions in {database_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="/data/banking_chat.db")
    parser.add_argument("--reset", action="store_true", help="replace existing demo banking records")
    arguments = parser.parse_args()
    seed(arguments.database, arguments.reset)
