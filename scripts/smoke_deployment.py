"""Verify a disposable deployment. Use only with an isolated test database.

Usage: MAHDI_SMOKE_TEACHER_PASSWORD=<local test secret> python scripts/smoke_deployment.py http://127.0.0.1:18901
No passwords, tokens or answer records are printed. Creates synthetic results.
"""
from __future__ import annotations

import json
import os
import secrets
import sys
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener


def main():
    base = sys.argv[1].rstrip("/")
    http = build_opener(ProxyHandler({}))

    def request(path, body=None, token=None, expected=200):
        headers = {}
        if token:
            headers["Authorization"] = "Bearer " + token
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = Request(base + path, data=json.dumps(body).encode("utf-8") if body is not None else None, headers=headers)
        try:
            response = http.open(req, timeout=90)
        except HTTPError as error:
            assert error.code == expected, f"{path}: HTTP {error.code}, expected {expected}"
            return None
        with response:
            assert response.status == expected, f"{path}: unexpected status"
            value = response.read()
            return json.loads(value) if "application/json" in response.headers.get("Content-Type", "") else value

    config = request("/api/assessment/config")
    assert config["lite_question_count"] == 12 and config["full_question_count"] == 44
    assert b"<html" in request("/").lower()
    request("/api/instructor/results", expected=401)
    email = "smoke-" + secrets.token_hex(6) + "@example.invalid"
    password = secrets.token_urlsafe(18)
    created = request("/api/account/create", {"email":email, "pin":password, "display_name":"Smoke Student", "company_name":"Smoke Company", "job_title":"Tester", "rq":"Smoke question", "ra":"Smoke answer"})
    opened = request("/api/account/open", {"email":email, "pin":password})
    token = opened["accessToken"]
    assert request("/api/account/me", token=token)["user"]["id"] == created["user"]["id"]
    request("/api/instructor/results", token=token, expected=403)
    selected = request("/api/assessment/selections", {"version":"lite"}, token)
    lite = request("/api/assessment/evaluate", {"selection_id":selected["selection"]["id"], "answers":{q["key"]:0 for q in selected["questions"]}}, token)["result"]
    upgrade = request("/api/assessment/selections", {"version":"full", "source_result_id":lite["id"]}, token)
    assert len(upgrade["questions"]) == 32
    full = request("/api/assessment/evaluate", {"selection_id":upgrade["selection"]["id"], "answers":{q["key"]:0 for q in upgrade["questions"]}}, token)["result"]
    assert len(full["answers"]) == 44
    pdf_sizes = {}
    for version, result in (("lite", lite), ("full", full)):
        pdf = request("/api/results/latest/pdf?result_id=" + result["id"], token=token)
        assert pdf.startswith(b"%PDF-") and len(pdf) > 10000
        pdf_sizes[version] = len(pdf)
    teacher = request("/api/account/open", {"email":"teacher", "pin":os.environ["MAHDI_SMOKE_TEACHER_PASSWORD"], "role":"instructor"})
    teacher_token = teacher["accessToken"]
    assert len(request("/api/instructor/results", token=teacher_token)["results"]) == 2
    assert request("/api/instructor/version-stats", token=teacher_token)["total_selections"] == 2
    request("/api/account/mail/start", {"email":email}, expected=503)
    reset_password = secrets.token_urlsafe(18)
    request("/api/account/recover/reset", {"email":email, "recovery_answer":"Smoke answer", "new_pin":reset_password})
    request("/api/account/me", token=token, expected=401)
    request("/api/account/open", {"email":email, "pin":reset_password})
    print(json.dumps({"smoke_passed":True, "question_counts":[12,32,44], "pdf_bytes":pdf_sizes, "teacher_statistics":True, "production_debug_link_blocked":True, "reset_revokes_session":True}, indent=2))


if __name__ == "__main__":
    main()
