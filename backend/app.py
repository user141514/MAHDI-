from __future__ import annotations

import secrets
import hashlib
from typing import Any, Dict, List, Literal, Optional
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from .account_api import router as account_router
from .assessment import get_config as get_assessment_config, load_bank as load_assessment_bank, score_answers, select_question_ids
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


@app.on_event("startup")
def startup() -> None:
    init_db()
    ensure_teacher()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(HTML_FILE)


@app.post("/api/results")
def save_result(authorization: str = Header(default=None)) -> None:
    get_current(authorization)
    raise HTTPException(410, "旧版结果提交已停用，请刷新页面后重新开始测评。")


@app.get("/api/results/latest/pdf")
def latest_result_pdf(authorization: str = Header(default=None), result_id: Optional[str] = None) -> Response:
    current = get_current(authorization)
    if current["role"] != "student":
        raise HTTPException(403, "仅学员可导出个人测评报告。")
    with connect() as conn:
        if result_id:
            row = conn.execute("SELECT payload FROM results WHERE id=? AND user_id=?", (result_id, current["id"])).fetchone()
        else:
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


@app.get("/api/results/latest")
def latest_result(authorization: str = Header(default=None)) -> Dict[str, Any]:
    current = get_current(authorization)
    if current["role"] != "student":
        raise HTTPException(403, "仅学员可查看个人最近报告。")
    with connect() as conn:
        row = conn.execute("SELECT payload FROM results WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (current["id"],)).fetchone()
    if row is None:
        raise HTTPException(404, "当前账号还没有已保存的测评结果。")
    return {"result": load_json(row["payload"])}


@app.get("/api/instructor/results")
def instructor_results(authorization: str = Header(default=None)) -> Dict[str, Any]:
    current = get_current(authorization)
    if current["role"] != "instructor":
        raise HTTPException(403, "仅管理员可访问。")
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
        raise HTTPException(403, "仅管理员可访问。")
    with connect() as conn:
        conn.execute("DELETE FROM results")
        conn.execute("DELETE FROM assessment_selections")
    return {"ok": True}


class SelectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal["lite", "full"]
    agent_type: Literal["mahid"] = "mahid"
    client_request_id: Optional[str] = Field(default=None, min_length=1, max_length=128)
    source_result_id: Optional[str] = Field(default=None, min_length=1, max_length=128)


class EvaluationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selection_id: str = Field(min_length=1, max_length=128)
    answers: Dict[str, StrictInt]


def public_questions(ids: List[str]) -> List[Dict[str, Any]]:
    return [{key: value for key, value in question.items() if key not in ("sc", "correct")} for question in load_assessment_bank()["questions"] if question["key"] in ids]


@app.get("/api/assessment/config")
def assessment_config() -> Dict[str, Any]:
    config = get_assessment_config()
    bank = load_assessment_bank()
    ids = [question["key"] for question in bank["questions"]]
    return {
        "agent_type": "mahid", "algorithm_version": config["algorithm_version"],
        "question_bank_version": bank["bank_version"], "types": bank["types"],
        "lite_question_count": config["lite_question_count"], "full_question_count": len(ids),
        "questions": public_questions(ids),
    }


@app.post("/api/assessment/selections")
def select_assessment(data: SelectionIn, authorization: str = Header(default=None)) -> Dict[str, Any]:
    current = get_current(authorization)
    if current["role"] != "student":
        raise HTTPException(403, "管理员账号不能填写测评。")
    bank = load_assessment_bank()
    config = get_assessment_config()
    inherited = {}
    if data.source_result_id:
        if data.version != "full":
            raise HTTPException(422, "仅完整版可继承精简版答案。")
        with connect() as conn:
            source_row = conn.execute("SELECT payload FROM results WHERE id=? AND user_id=?", (data.source_result_id, current["id"])).fetchone()
        if source_row is None:
            raise HTTPException(404, "未找到可继承的测评结果。")
        source = load_json(source_row["payload"])
        if source.get("version") != "lite":
            raise HTTPException(422, "请选择精简版结果继续深度测评。")
        if source.get("question_bank_version") != bank["bank_version"]:
            raise HTTPException(409, "题库版本已更新，无法继承旧版答案，请重新开始完整版测评。")
        inherited = source["answers"]
        config = source["scoring_config"]
    token = data.client_request_id or secrets.token_hex(16)
    selection_id = "selection_" + hashlib.sha256(f"{current['id']}:{token}".encode()).hexdigest()[:32]
    ids = select_question_ids(config) if data.version == "lite" else [q["key"] for q in bank["questions"]]
    selection = {
        "id": selection_id, "agent_type": "mahid", "version": data.version,
        "config": config, "question_bank_version": bank["bank_version"], "question_ids": ids,
        "source_result_id": data.source_result_id, "inherited_answers": inherited,
        "created_at": now_iso(),
    }
    with connect() as conn:
        conn.execute("INSERT OR IGNORE INTO assessment_selections VALUES (?, ?, ?, ?)", (selection_id, current["id"], dump_json(selection), selection["created_at"]))
        selection = load_json(conn.execute("SELECT payload FROM assessment_selections WHERE id=? AND user_id=?", (selection_id, current["id"])).fetchone()["payload"])
    if selection["version"] != data.version or selection["source_result_id"] != data.source_result_id:
        raise HTTPException(409, "该请求已用于另一版本选择，请重新选择。")
    if selection["question_bank_version"] != bank["bank_version"]:
        raise HTTPException(409, "题库版本已更新，请重新开始测评。")
    remaining = [key for key in selection["question_ids"] if key not in selection["inherited_answers"]]
    return {"selection": selection, "questions": public_questions(remaining), "types": bank["types"]}


@app.post("/api/assessment/evaluate")
def evaluate_assessment(data: EvaluationIn, authorization: str = Header(default=None)) -> Dict[str, Any]:
    current = get_current(authorization)
    if current["role"] != "student":
        raise HTTPException(403, "管理员账号不能提交测评。")
    with connect() as conn:
        row = conn.execute("SELECT payload FROM assessment_selections WHERE id=? AND user_id=?", (data.selection_id, current["id"])).fetchone()
    if row is None:
        raise HTTPException(404, "未找到本次测评，请重新选择版本。")
    selection = load_json(row["payload"])
    inherited = selection["inherited_answers"]
    if any(key in inherited and inherited[key] != value for key, value in data.answers.items()):
        raise HTTPException(422, "升级时请保留精简版已答题目的答案。")
    answers = {**inherited, **data.answers}
    result_id = "result_" + data.selection_id.removeprefix("selection_")
    with connect() as conn:
        existing = conn.execute("SELECT payload FROM results WHERE id=? AND user_id=?", (result_id, current["id"])).fetchone()
    if existing is not None:
        stored = load_json(existing["payload"])
        if stored["answers"] != answers:
            raise HTTPException(409, "本次测评已经提交；如需修改答案，请重新开始。")
        return {"result": stored}
    if selection["question_bank_version"] != load_assessment_bank()["bank_version"]:
        raise HTTPException(409, "题库版本已更新，请重新开始测评。")
    try:
        payload = score_answers(answers, selection["version"], selection["config"])
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    created_at = now_iso()
    payload.update({
        "id": result_id, "selection_id": data.selection_id,
        "source_result_id": selection["source_result_id"], "scoring_config": selection["config"],
        "userId": current["id"], "userName": current["display_name"], "email": current["email"],
        "companyName": current["company_name"] or "", "jobTitle": current["job_title"] or "",
        "createdAt": created_at, "generated_at": created_at,
    })
    with connect() as conn:
        conn.execute("INSERT OR IGNORE INTO results VALUES (?, ?, ?, ?)", (result_id, current["id"], dump_json(payload), created_at))
        stored = load_json(conn.execute("SELECT payload FROM results WHERE id=? AND user_id=?", (result_id, current["id"])).fetchone()["payload"])
    if stored["answers"] != answers:
        raise HTTPException(409, "本次测评已经提交；如需修改答案，请重新开始。")
    return {"result": stored}


@app.get("/api/instructor/version-stats")
def assessment_version_stats(authorization: str = Header(default=None)) -> Dict[str, Any]:
    current = get_current(authorization)
    if current["role"] != "instructor":
        raise HTTPException(403, "仅管理员可访问。")
    with connect() as conn:
        choices = conn.execute("SELECT id, payload FROM assessment_selections").fetchall()
        completed = {row["id"] for row in conn.execute("SELECT id FROM results").fetchall()}
    versions = {version: {"selections": 0, "completed": 0, "share": 0.0} for version in ("lite", "full")}
    for row in choices:
        version = load_json(row["payload"])["version"]
        versions[version]["selections"] += 1
        versions[version]["completed"] += "result_" + row["id"].removeprefix("selection_") in completed
    for values in versions.values():
        values["share"] = values["selections"] / len(choices) if choices else 0.0
    return {"agent_type": "mahid", "total_selections": len(choices), "versions": versions}
