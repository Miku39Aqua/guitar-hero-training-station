"""用户认证与提取历史的数据库层。"""
import json
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "auth_history.db"
_db_lock = threading.Lock()

RESET_TOKEN_TTL_HOURS = 1


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_tables():
    with _db_lock, _get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                username        TEXT NOT NULL UNIQUE,
                email           TEXT NOT NULL UNIQUE,
                password_hash   TEXT NOT NULL,
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS extraction_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER,
                task_id         TEXT NOT NULL UNIQUE,
                filename        TEXT NOT NULL,
                source          TEXT,
                extraction_type TEXT,
                status          TEXT DEFAULT 'pending',
                progress        TEXT,
                zip_path        TEXT,
                created_at      TEXT DEFAULT (datetime('now')),
                completed_at    TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_history_user_created
                ON extraction_history(user_id, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_history_task
                ON extraction_history(task_id);

            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                token           TEXT NOT NULL UNIQUE,
                expires_at      TEXT NOT NULL,
                used_at         TEXT,
                created_at      TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_reset_token
                ON password_reset_tokens(token);
            """
        )


def create_user(username: str, email: str, password_hash: str) -> int:
    with _db_lock, _get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash),
        )
        return cur.lastrowid


def get_user_by_username(username: str) -> Optional[sqlite3.Row]:
    with _db_lock, _get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ? LIMIT 1", (username,)
        ).fetchone()


def get_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    with _db_lock, _get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE id = ? LIMIT 1", (user_id,)
        ).fetchone()


def create_history_record(
    task_id: str,
    filename: str,
    source: str,
    extraction_type: list[str],
    user_id: Optional[int] = None,
    status: str = "pending",
    progress: str = "",
) -> int:
    with _db_lock, _get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO extraction_history
            (user_id, task_id, filename, source, extraction_type, status, progress)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                task_id,
                filename,
                source,
                json.dumps(extraction_type, ensure_ascii=False),
                status,
                progress,
            ),
        )
        return cur.lastrowid


def update_history_status(
    task_id: str,
    status: str,
    progress: Optional[str] = None,
    zip_path: Optional[str] = None,
):
    with _db_lock, _get_conn() as conn:
        params = [status]
        sets = ["status = ?"]
        if progress is not None:
            sets.append("progress = ?")
            params.append(progress)
        if zip_path is not None:
            sets.append("zip_path = ?")
            params.append(zip_path)
        if status in ("done", "failed"):
            sets.append("completed_at = datetime('now')")
        params.append(task_id)
        conn.execute(
            f"UPDATE extraction_history SET {', '.join(sets)} WHERE task_id = ?",
            params,
        )


def get_history_by_user(
    user_id: int, page: int = 1, page_size: int = 20
) -> tuple[list[dict], int]:
    offset = (page - 1) * page_size
    with _db_lock, _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, task_id, filename, source, extraction_type, status, progress,
                   zip_path, created_at, completed_at
            FROM extraction_history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, page_size, offset),
        ).fetchall()

        total = conn.execute(
            "SELECT COUNT(*) FROM extraction_history WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]

    return [dict(r) for r in rows], total


def get_history_by_task(task_id: str) -> Optional[dict]:
    with _db_lock, _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM extraction_history WHERE task_id = ? LIMIT 1",
            (task_id,),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    with _db_lock, _get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE email = ? LIMIT 1", (email,)
        ).fetchone()


def create_reset_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_TTL_HOURS)).isoformat()
    with _db_lock, _get_conn() as conn:
        conn.execute(
            "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
            (user_id, token, expires_at),
        )
    return token


def get_reset_token(token: str) -> Optional[dict]:
    with _db_lock, _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM password_reset_tokens WHERE token = ? LIMIT 1", (token,)
        ).fetchone()
    return dict(row) if row else None


def mark_reset_token_used(token: str):
    with _db_lock, _get_conn() as conn:
        conn.execute(
            "UPDATE password_reset_tokens SET used_at = datetime('now') WHERE token = ?",
            (token,),
        )


def update_user_password(user_id: int, password_hash: str):
    with _db_lock, _get_conn() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE id = ?",
            (password_hash, user_id),
        )
