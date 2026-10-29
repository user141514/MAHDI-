from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import HTTPException

from .storage import connect

TEACHER_ACCOUNT = "teacher"
TEACHER_PIN = "meitai" + "123456"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def public_user(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "email": row["email"],
        "displayName": "管理员" if row["role"] == "instructor" and row["display_name"] == "讲师" else row["display_name"],
        "companyName": row["company_name"] or "",
        "jobTitle": "管理员" if row["role"] == "instructor" and row["job_title"] == "讲师" else row["job_title"] or "",
        "role": row["role"],
        "createdAt": row["created_at"],
    }


def ensure_teacher() -> None:
    with connect() as conn:
        row = conn.execute("SELECT id FROM users WHERE email=? AND role='instructor'", (TEACHER_ACCOUNT,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO users (id, email, password_hash, display_name, company_name, job_title, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("teacher", TEACHER_ACCOUNT, TEACHER_PIN, "管理员", "美太咨询", "管理员", "instructor", now_iso()),
            )


def check_role(user, role: str):
    if user["role"] != role:
        raise HTTPException(403, "当前账号无权访问。")
    return user
