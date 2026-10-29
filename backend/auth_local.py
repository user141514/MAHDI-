from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import HTTPException

from .storage import connect
from .passwords import hash_password

TEACHER_ACCOUNT = "teacher"
TEACHER_PIN = os.getenv("MAHDI_TEACHER_PASSWORD", "meitai" + "123456")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def public_user(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "email": row["email"],
        "displayName": row["display_name"],
        "companyName": row["company_name"] or "",
        "jobTitle": row["job_title"] or "",
        "role": row["role"],
        "createdAt": row["created_at"],
    }


def ensure_teacher() -> None:
    if os.getenv("MAHDI_ENV") == "production":
        configured = os.getenv("MAHDI_TEACHER_PASSWORD", "")
        if len(configured) < 16 or configured == "meitai" + "123456":
            raise RuntimeError("Production requires a configured teacher password of at least 16 characters.")
    with connect() as conn:
        row = conn.execute("SELECT id FROM users WHERE email=? AND role='instructor'", (TEACHER_ACCOUNT,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO users (id, email, password_hash, display_name, company_name, job_title, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("teacher", TEACHER_ACCOUNT, hash_password(TEACHER_PIN), "讲师", "美太咨询", "讲师", "instructor", now_iso()),
            )


def check_role(user, role: str):
    if user["role"] != role:
        raise HTTPException(403, "当前账号无权访问。")
    return user
