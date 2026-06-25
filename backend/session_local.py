from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Header, HTTPException

from .storage import connect


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def issue(conn, user_id: str) -> str:
    sid = secrets.token_urlsafe(24)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    conn.execute("INSERT INTO sessions VALUES (?, ?, ?, ?)", (sid, user_id, expires_at, now_iso()))
    return sid


def get_current(authorization = Header(default=None)):
    if not authorization or not isinstance(authorization, str):
        raise HTTPException(401, "请先登录。")
    prefix, _, sid = authorization.partition(" ")
    if prefix.lower() != "bearer" or not sid:
        raise HTTPException(401, "认证格式错误。")
    with connect() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE session_id=?", (sid,)).fetchone()
        if row is None:
            raise HTTPException(401, "登录已失效。")
        if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
            conn.execute("DELETE FROM sessions WHERE session_id=?", (sid,))
            raise HTTPException(401, "登录已过期。")
        user = conn.execute("SELECT * FROM users WHERE id=?", (row["user_id"],)).fetchone()
        if user is None:
            raise HTTPException(401, "用户不存在。")
        return user
