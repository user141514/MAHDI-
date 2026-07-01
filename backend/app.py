from __future__ import annotations

import json
import secrets
from typing import Any, Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .account_api import router as account_router
from .auth_local import TEACHER_ACCOUNT, TEACHER_PIN, ensure_teacher, now_iso, public_user
from .pdf_export import render_result_pdf
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
def save_result(data: ResultIn, authorization: str = Header(default=None)) -> Dict[str, Any]:
    current = get_current(authorization)
    if current["role"] != "student":
        raise HTTPException(403, "讲师账号不能提交学员测评。")
    payload = data.model_dump()
    result_id = "result_" + secrets.token_hex(8)
    created_at = now_iso()
    payload.pop("userId", None)
    payload.pop("userName", None)
    payload.pop("email", None)
    payload.pop("companyName", None)
    payload.pop("jobTitle", None)
    user_id = current["id"]
    user_name = current["display_name"]
    email = current["email"]
    company_name = current["company_name"] or ""
    job_title = current["job_title"] or ""
    payload.update({"id": result_id, "userId": user_id, "userName": user_name, "email": email, "companyName": company_name, "jobTitle": job_title, "createdAt": created_at})
    with connect() as conn:
        conn.execute("INSERT INTO results VALUES (?, ?, ?, ?)", (result_id, user_id, dump_json(payload), created_at))
    return {"result": payload}


@app.get("/api/results/latest/pdf")
def latest_result_pdf(authorization: str = Header(default=None)) -> Response:
    current = get_current(authorization)
    if current["role"] != "student":
        raise HTTPException(403, "仅学员可导出个人测评报告。")
    with connect() as conn:
        row = conn.execute(
            "SELECT payload FROM results WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
            (current["id"],),
        ).fetchone()
    if row is None:
        raise HTTPException(404, "当前账号还没有可导出的测评结果。")
    payload = load_json(row["payload"])
    try:
        pdf_bytes = render_result_pdf(payload)
    except Exception as exc:
        raise HTTPException(500, f"PDF生成失败：{type(exc).__name__}: {exc}") from exc
    created_date = str(payload.get("createdAt") or "latest")[:10] or "latest"
    filename = f"MAHDI-report-{created_date}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/instructor/results")
def instructor_results(authorization: str = Header(default=None)) -> Dict[str, Any]:
    current = get_current(authorization)
    if current["role"] != "instructor":
        raise HTTPException(403, "仅讲师可访问。")
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
def clear_results(authorization: str = Header(default=None)) -> Dict[str, bool]:
    current = get_current(authorization)
    if current["role"] != "instructor":
        raise HTTPException(403, "仅讲师可访问。")
    with connect() as conn:
        conn.execute("DELETE FROM results")
    return {"ok": True}
