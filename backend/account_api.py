from __future__ import annotations

import secrets
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from .auth_local import TEACHER_ACCOUNT, public_user, now_iso
from .session_local import get_current, issue
from .storage import connect

router = APIRouter(prefix="/api/account")


class CreateReq(BaseModel):
    email: str = Field(min_length=1)
    pin: str = Field(min_length=6)
    display_name: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    job_title: str = Field(min_length=1)


class OpenReq(BaseModel):
    email: str = Field(min_length=1)
    pin: str = Field(min_length=1)
    role: str = "student"


@router.post("/create")
def create_account(data: CreateReq) -> Dict[str, Any]:
    email = data.email.strip().lower()
    with connect() as conn:
        if conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
            raise HTTPException(409, "该账号已被注册。")
        uid = "user_" + secrets.token_hex(8)
        conn.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, email, data.pin, data.display_name.strip(), data.company_name.strip(), data.job_title.strip(), "student", now_iso()),
        )
        row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        sid = issue(conn, uid)
    return {"accessToken": sid, "user": public_user(row)}


@router.post("/open")
def open_account(data: OpenReq) -> Dict[str, Any]:
    email = data.email.strip().lower()
    role = "instructor" if data.role == "instructor" else "student"
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email=? AND role=?", (email, role)).fetchone()
        if row is None or row[2] != data.pin:
            raise HTTPException(401, "账号或密码错误。")
        sid = issue(conn, row["id"])
    return {"accessToken": sid, "user": public_user(row)}


@router.get("/me")
def current_account(authorization: str = Header(default=None)) -> Dict[str, Any]:
    row = get_current(authorization)
    return {"user": public_user(row)}
