from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from .auth_local import TEACHER_ACCOUNT, public_user, now_iso
from .mail_local import build_reset_url, send_reset_link
from .session_local import get_current, issue
from .storage import connect, update_user_value

router = APIRouter(prefix="/api/account")


def answer_hash(value: str) -> str:
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


class CreateReq(BaseModel):
    email: str = Field(min_length=1)
    pin: str = Field(min_length=6)
    display_name: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    job_title: str = Field(min_length=1)
    recovery_question: Optional[str] = None
    recovery_answer: Optional[str] = None
    rq: Optional[str] = None
    ra: Optional[str] = None


class OpenReq(BaseModel):
    email: str = Field(min_length=1)
    pin: str = Field(min_length=1)
    role: str = "student"


class EmailReq(BaseModel):
    email: str = Field(min_length=1)


class AnswerResetReq(BaseModel):
    email: Optional[str] = None
    recovery_answer: Optional[str] = None
    new_pin: str = Field(min_length=6)
    token: Optional[str] = None


@router.post("/create")
def create_account(data: CreateReq) -> Dict[str, Any]:
    email = data.email.strip().lower()
    with connect() as conn:
        if conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
            raise HTTPException(409, "该账号已被注册。")
        uid = "user_" + secrets.token_hex(8)
        conn.execute(
            "INSERT INTO users (id, email, password_hash, display_name, company_name, job_title, role, created_at, recovery_question, recovery_answer_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, email, data.pin, data.display_name.strip(), data.company_name.strip(), data.job_title.strip(), "student", now_iso(), (data.recovery_question or data.rq or "").strip() or None, answer_hash(data.recovery_answer or data.ra or "") if (data.recovery_answer or data.ra or "").strip() else None),
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


@router.post("/recover/question")
def recover_question(data: EmailReq) -> Dict[str, Any]:
    email = data.email.strip().lower()
    with connect() as conn:
        row = conn.execute("SELECT email, recovery_question FROM users WHERE email=? AND role='student'", (email,)).fetchone()
    if row is None or not row["recovery_question"]:
        raise HTTPException(404, "该账号未设置找回问题，请联系讲师。")
    return {"email": row["email"], "recoveryQuestion": row["recovery_question"]}


@router.post("/recover/reset")
def recover_reset(data: AnswerResetReq) -> Dict[str, bool]:
    email = (data.email or "").strip().lower()
    with connect() as conn:
        if data.token:
            marker = "token-ok"
            row = conn.execute("SELECT id, reset_token_expires_at, ? AS recovery_answer_hash FROM users WHERE reset_token=? AND role='student'", (answer_hash(marker), data.token)).fetchone()
            if row is not None and row["reset_token_expires_at"] and datetime.fromisoformat(row["reset_token_expires_at"]) < datetime.now(timezone.utc):
                raise HTTPException(400, "重置链接已过期。")
            data.recovery_answer = marker
        else:
            row = conn.execute("SELECT id, recovery_answer_hash FROM users WHERE email=? AND role='student'", (email,)).fetchone()
        if row is None or not row["recovery_answer_hash"] or row["recovery_answer_hash"] != answer_hash(data.recovery_answer):
            raise HTTPException(401, "找回答案不正确。")
        conn.execute("UPDATE users SET password_hash=?, reset_token=NULL, reset_token_expires_at=NULL WHERE id=?", (data.new_pin, row["id"]))
    return {"ok": True}


@router.post("/mail/start")
def mail_start(data: EmailReq) -> Dict[str, Any]:
    email = data.email.strip().lower()
    token = secrets.token_urlsafe(24)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    with connect() as conn:
        row = conn.execute("SELECT id FROM users WHERE email=? AND role='student'", (email,)).fetchone()
        if row is None:
            raise HTTPException(404, "该账号不存在。")
        conn.execute("UPDATE users SET reset_token=?, reset_token_expires_at=? WHERE id=?", (token, expires_at, row["id"]))
    sent = send_reset_link(email, token)
    return {"ok": True, "sent": sent, "resetUrl": None if sent else build_reset_url(token)}
