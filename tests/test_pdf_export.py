from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi import HTTPException

from backend import app as app_module
from backend import pdf_export
from backend import storage
from backend.account_api import CreateReq, OpenReq, create_account, open_account
from backend.app import ResultIn, save_result
from backend.auth_local import TEACHER_ACCOUNT, TEACHER_PIN, ensure_teacher


def sample_result(main_type: str = "D") -> ResultIn:
    return ResultIn(
        answers={"q1": "A"},
        final={"M": 19, "A": 21, "H": 17, "D": 23, "I": 20},
        pcts={"M": 19, "A": 21, "H": 17, "D": 23, "I": 20},
        dimNorm={"E": {"D": 64}, "K": {"D": 79}, "I": {"D": 50}, "L": {"D": 63}, "P": {"D": 78}},
        sorted=[[main_type, 23], ["A", 21], ["I", 20], ["M", 19], ["H", 17]],
        mainType=main_type,
        secondType="A",
        mainTypeName="数据管理者",
        secondTypeName="AI赋能者",
        isDouble=False,
        level=3,
        levelName="AI专业深化",
        kRate=70,
        stylePct={"social": 25, "practice": 35, "structure": 20, "research": 20},
        topStyle="practice",
        topStyleName="实操型",
        warns=[],
    )


class LatestResultPdfTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_db_path = storage.DB_PATH
        self.temp_dir = TemporaryDirectory(ignore_cleanup_errors=True)
        storage.DB_PATH = Path(self.temp_dir.name) / "mahid.db"
        storage.init_db()
        ensure_teacher()

    def tearDown(self) -> None:
        storage.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def create_student_token(self) -> str:
        created = create_account(
            CreateReq(
                email="student@example.com",
                pin="student123",
                display_name="测试学生",
                company_name="测试公司",
                job_title="测试岗位",
            )
        )
        return created["accessToken"]

    def test_student_downloads_latest_result_pdf(self) -> None:
        token = self.create_student_token()
        auth = f"Bearer {token}"
        save_result(sample_result("D"), authorization=auth)
        save_result(sample_result("I"), authorization=auth)

        with patch.object(app_module, "render_result_pdf", return_value=b"%PDF-1.4\nfake") as render:
            response = app_module.latest_result_pdf(authorization=auth)

        self.assertEqual("application/pdf", response.media_type)
        self.assertIn("attachment;", response.headers["content-disposition"])
        self.assertIn("MAHDI-report", response.headers["content-disposition"])
        self.assertEqual(b"%PDF-1.4\nfake", response.body)
        self.assertEqual("I", render.call_args.args[0]["mainType"])

    def test_student_without_result_gets_404(self) -> None:
        token = self.create_student_token()

        with self.assertRaises(HTTPException) as caught:
            app_module.latest_result_pdf(authorization=f"Bearer {token}")

        self.assertEqual(404, caught.exception.status_code)

    def test_instructor_cannot_download_student_pdf(self) -> None:
        opened = open_account(OpenReq(email=TEACHER_ACCOUNT, pin=TEACHER_PIN, role="instructor"))

        with self.assertRaises(HTTPException) as caught:
            app_module.latest_result_pdf(authorization=f"Bearer {opened['accessToken']}")

        self.assertEqual(403, caught.exception.status_code)

    def test_windows_render_delegates_to_subprocess(self) -> None:
        payload = sample_result().model_dump()

        with (
            patch.object(pdf_export.sys, "platform", "win32"),
            patch.object(pdf_export, "_render_result_pdf_direct", side_effect=AssertionError("direct render should not run")),
            patch.object(pdf_export, "_render_result_pdf_in_subprocess", return_value=b"%PDF-1.4\nfake") as render,
        ):
            pdf_bytes = pdf_export.render_result_pdf(payload)

        self.assertEqual(b"%PDF-1.4\nfake", pdf_bytes)
        self.assertEqual(payload, render.call_args.args[0])

    def test_report_html_includes_full_recommendation_sections(self) -> None:
        html = pdf_export.build_report_html(sample_result("D").model_dump())

        self.assertIn("个性化转型路径建议", html)
        self.assertIn("优先学习内容推荐", html)
        self.assertIn("完成数据合规底座", html)
        self.assertIn("AI与数据关系：数据是AI系统的核心燃料", html)
        self.assertIn("用你对数据的专业敏感度", html)
        self.assertIn(".section { border: 1px solid #E8DFEA; border-radius: 12px; padding: 16px; }", html)
        self.assertNotIn("–", html)


if __name__ == "__main__":
    unittest.main()
