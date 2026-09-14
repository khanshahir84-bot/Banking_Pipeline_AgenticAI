"""SQLite store for user-bound sessions, sanitized history, and workflow audit events."""
import sqlite3
from pathlib import Path
from typing import Any

from .config import settings


def connection() -> sqlite3.Connection:
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, role TEXT NOT NULL,
            content TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES sessions(session_id)
        );
        CREATE TABLE IF NOT EXISTS workflow_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT, trace_id TEXT NOT NULL, user_id TEXT NOT NULL,
            intent TEXT, tool TEXT, outcome TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)
    return conn


def ensure_session(session_id: str, user_id: str) -> None:
    """Create a session or reject an attempt to access another customer's session."""
    with connection() as conn:
        row = conn.execute("SELECT user_id FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row is None:
            conn.execute("INSERT INTO sessions(session_id, user_id) VALUES (?, ?)", (session_id, user_id))
        elif row["user_id"] != user_id:
            raise PermissionError("session does not belong to authenticated user")


def add_message(session_id: str, role: str, content: str) -> None:
    if role not in {"user", "assistant"}:
        raise ValueError("unsupported message role")
    with connection() as conn:
        conn.execute("INSERT INTO messages(session_id, role, content) VALUES(?, ?, ?)", (session_id, role, content))


def history(session_id: str, limit: int | None = None) -> list[dict[str, str]]:
    limit = limit or settings.max_history_messages
    with connection() as conn:
        rows = conn.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?", (session_id, limit)).fetchall()
    return [dict(row) for row in reversed(rows)]


def audit_workflow(trace_id: str, user_id: str, intent: str | None, tool: str | None, outcome: str) -> None:
    with connection() as conn:
        conn.execute("INSERT INTO workflow_audit(trace_id, user_id, intent, tool, outcome) VALUES (?, ?, ?, ?, ?)", (trace_id, user_id, intent, tool, outcome))
