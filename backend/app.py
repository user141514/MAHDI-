from __future__ import annotations

import json
import secrets
from typing import Any, Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .account_api import router as account_router
from .auth_local import TEACHER_ACCOUNT, TEACHER_PIN, ensure_teacher, now_iso, public_user
from .session_local import get_current, issue
from .storage import connect, dump_json, init_db, load_json

ROOT = Path(__file__).resolve().parents[1]
HTML_FILE = ROOT / "MAHDI五类人才模型测评工具(1).html"

app = FastAPI(title="MAHDI Assessment API")
app.include_router(account_router)


class RegisterIn(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=6)
    display_name: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    job_title: str = Field(min_length=1)


class LoginIn(BaseModel):
    email: str = Field(min_length=1)
    password: Optional[str] = None
    pin: Optional[str] = None
    role: str = "student"


class ResultIn(BaseModel):
    userId: Optional[str] = None
    userName: Optional[str] = None
    email: Optional[str] = None
    companyName: Optional[str] = None
    jobTitle: Optional[str] = None
    answers: Dict[str, Any]
    final: Dict[str, Any]
    pcts: Dict[str, Any]
    dimNorm: Optional[Dict[str, Any]] = None
    sorted: Optional[List[Any]] = None
    mainType: str
    secondType: Optional[str] = None
    mainTypeName: Optional[str] = None
    secondTypeName: Optional[str] = None
    isDouble: bool = False
    level: int
    levelName: Optional[str] = None
    kRate: float = 0
    stylePct: Optional[Dict[str, Any]] = None
    topStyle: Optional[str] = None
    topStyleName: Optional[str] = None
    warns: List[Dict[str, Any]] = []


@app.on_event("startup")
def startup() -> None:
    init_db()
    ensure_teacher()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(HTML_FILE)


@app.post("/api/results")
def save_result(data: ResultIn) -> Dict[str, Any]:
    payload = data.model_dump()
    result_id = "result_" + secrets.token_hex(8)
    created_at = now_iso()
    user_id = str(payload.pop("userId", "local_user"))
    user_name = str(payload.pop("userName", "未命名用户"))
    email = str(payload.pop("email", ""))
    company_name = str(payload.pop("companyName", ""))
    job_title = str(payload.pop("jobTitle", ""))
    payload.update({"id": result_id, "userId": user_id, "userName": user_name, "email": email, "companyName": company_name, "jobTitle": job_title, "createdAt": created_at})
    with connect() as conn:
        conn.execute("INSERT INTO results VALUES (?, ?, ?, ?)", (result_id, user_id, dump_json(payload), created_at))
    return {"result": payload}


@app.get("/api/instructor/results")
def instructor_results() -> Dict[str, Any]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM results ORDER BY created_at DESC").fetchall()
    results = [load_json(row["payload"]) for row in rows]
    users = []
    seen = set()
    for item in results:
        uid = item.get("userId") or item.get("email") or item.get("userName")
        if uid in seen:
            continue
        seen.add(uid)
        users.append({"id": uid, "email": item.get("email", ""), "displayName": item.get("userName", ""), "companyName": item.get("companyName", ""), "jobTitle": item.get("jobTitle", ""), "role": "student", "createdAt": item.get("createdAt", "")})
    return {"users": users, "results": results}


@app.delete("/api/instructor/results")
def clear_results() -> Dict[str, bool]:
    with connect() as conn:
        conn.execute("DELETE FROM results")
    return {"ok": True}
