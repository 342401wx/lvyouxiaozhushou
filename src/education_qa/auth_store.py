from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .app_config import get_config
from .paths import PROJECT_ROOT


DB_PATH = PROJECT_ROOT / "data" / "tourism_app.sqlite"
USERNAME_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9]{6,}$")
PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9]{8,}$")
SESSION_DAYS = 7
PBKDF2_ITERATIONS = 260_000


def validate_username(username: str) -> str | None:
    if not USERNAME_RE.fullmatch(username or ""):
        return "账号需为英文和数字组合，至少 6 位。"
    return None


def validate_password(password: str) -> str | None:
    if not PASSWORD_RE.fullmatch(password or ""):
        return "密码需为英文和数字组合，至少 8 位。"
    return None


class AuthStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.init_db()

    def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_memories_user_created
                    ON memories(user_id, created_at DESC);
                """
            )

    def register(self, username: str, password: str) -> tuple[dict[str, Any] | None, str | None]:
        username = (username or "").strip()
        password = password or ""
        if error := validate_username(username):
            return None, error
        if error := validate_password(password):
            return None, error

        salt = secrets.token_hex(16)
        password_hash = _hash_password(password, salt)
        now = _now()
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    "INSERT INTO users(username, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
                    (username, password_hash, salt, now),
                )
                user_id = int(cursor.lastrowid)
        except sqlite3.IntegrityError:
            return None, "账号已存在，请换一个。"
        return {"id": user_id, "username": username}, None

    def login(self, username: str, password: str) -> tuple[dict[str, Any] | None, str | None]:
        username = (username or "").strip()
        password = password or ""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, username, password_hash, salt FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if row is None:
            return None, "账号或密码不正确。"
        expected = _hash_password(password, row["salt"])
        if not hmac.compare_digest(expected, row["password_hash"]):
            return None, "账号或密码不正确。"
        return {"id": int(row["id"]), "username": row["username"]}, None

    def create_session(self, user_id: int) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=SESSION_DAYS)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions(token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (token, user_id, _iso(now), _iso(expires)),
            )
        return token, expires

    def user_from_session(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        now = _now()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT users.id, users.username, sessions.expires_at
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token = ?
                """,
                (token,),
            ).fetchone()
            if row is None:
                return None
            if row["expires_at"] <= now:
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
                return None
        return {"id": int(row["id"]), "username": row["username"]}

    def delete_session(self, token: str | None) -> None:
        if not token:
            return
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))

    def add_memory(self, user_id: int, kind: str, title: str, summary: str, payload: dict[str, Any]) -> None:
        payload_text = json.dumps(payload, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memories(user_id, kind, title, summary, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, kind, title[:120], summary[:500], payload_text, _now()),
            )

    def list_memories(self, user_id: int, *, limit: int = 12) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, kind, title, summary, created_at
                FROM memories
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "kind": row["kind"],
                "title": row["title"],
                "summary": row["summary"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def get_memory(self, user_id: int, memory_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, kind, title, summary, payload, created_at
                FROM memories
                WHERE user_id = ? AND id = ?
                """,
                (user_id, memory_id),
            ).fetchone()
        if row is None:
            return None

        try:
            payload = json.loads(row["payload"])
        except json.JSONDecodeError:
            payload = {}

        return {
            "id": int(row["id"]),
            "kind": row["kind"],
            "title": row["title"],
            "summary": row["summary"],
            "payload": payload,
            "created_at": row["created_at"],
        }

    def _connect(self) -> sqlite3.Connection:
        timeout = get_config().sqlite_timeout
        conn = sqlite3.connect(self.db_path, timeout=timeout)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(f"PRAGMA busy_timeout = {timeout * 1000}")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn


def summarize_intent(intent: dict[str, Any]) -> tuple[str, str]:
    city = str(intent.get("city") or "未指定目的地")
    days = intent.get("days") or 1
    interests = "、".join(intent.get("interests") or [])
    title = f"{city} {days}天需求"
    summary = f"偏好：{interests or '未指定'}；预算：{intent.get('budget') or '未提供'}；城际：{intent.get('intercity_transportation') or '未确定'}"
    return title, summary


def summarize_plan(plan: dict[str, Any]) -> tuple[str, str]:
    city = str(plan.get("city") or "未指定目的地")
    days = plan.get("days_count") or 1
    title = f"{city} {days}天攻略"
    stops = []
    for day in plan.get("days") or []:
        stops.extend(stop.get("name", "") for stop in day.get("stops") or [] if stop.get("scheduled") is not False)
    stop_text = "、".join([item for item in stops if item][:6])
    summary = f"行程点：{stop_text or '暂无'}；预算估算：{(plan.get('budget') or {}).get('total', 0)}元"
    return title, summary


def _hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS,
    )
    return digest.hex()


def _now() -> str:
    return _iso(datetime.now(timezone.utc))


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()
