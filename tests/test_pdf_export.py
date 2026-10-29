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
from backend.auth_local import TEACHER_ACCOUNT, TEACHER_PIN, ensure_teacher
from backend.assessment import get_config, load_bank, score_answers, select_question_ids


def sample_result(main_type: str = "D") -> dict:
    return dict(
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

    def seed_legacy_result(self, main_type: str, auth: str) -> dict:
        # Historical rows remain readable after retiring the client-scored writer.
        current = app_module.get_current(auth)
        with storage.connect() as conn:
            index = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
            created_at = f"2026-10-26T06:00:{index:02d}+00:00"
            result = dict(sample_result(main_type), id=f"historical-{index}", userId=current["id"], createdAt=created_at)
            conn.execute("INSERT INTO results VALUES (?, ?, ?, ?)", (result["id"], current["id"], storage.dump_json(result), created_at))
        return result

    def test_student_downloads_latest_result_pdf(self) -> None:
        token = self.create_student_token()
        auth = f"Bearer {token}"
        self.seed_legacy_result("D", auth)
        self.seed_legacy_result("I", auth)

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

    def test_pdf_can_bind_the_displayed_saved_result_instead_of_a_newer_tab(self) -> None:
        token = self.create_student_token()
        auth = f"Bearer {token}"
        shown = self.seed_legacy_result("D", auth)
        self.seed_legacy_result("I", auth)
        with patch.object(app_module, "render_result_pdf", return_value=b"%PDF-1.4 test") as render:
            app_module.latest_result_pdf(authorization=auth, result_id=shown["id"])
        self.assertEqual(render.call_args.args[0]["id"], shown["id"])
        with self.assertRaises(HTTPException) as caught:
            app_module.latest_result_pdf(authorization=auth, result_id="another-users-result")
        self.assertEqual(caught.exception.status_code, 404)

    def test_instructor_cannot_download_student_pdf(self) -> None:
        opened = open_account(OpenReq(email=TEACHER_ACCOUNT, pin=TEACHER_PIN, role="instructor"))

        with self.assertRaises(HTTPException) as caught:
            app_module.latest_result_pdf(authorization=f"Bearer {opened['accessToken']}")

        self.assertEqual(403, caught.exception.status_code)

    def test_windows_render_delegates_to_subprocess(self) -> None:
        payload = sample_result()

        with (
            patch.object(pdf_export.sys, "platform", "win32"),
            patch.object(pdf_export, "_render_result_pdf_direct", side_effect=AssertionError("direct render should not run")),
            patch.object(pdf_export, "_render_result_pdf_in_subprocess", return_value=b"%PDF-1.4\nfake") as render,
        ):
            pdf_bytes = pdf_export.render_result_pdf(payload)

        self.assertEqual(b"%PDF-1.4\nfake", pdf_bytes)
        self.assertEqual(payload, render.call_args.args[0])

    def test_report_html_includes_full_recommendation_sections(self) -> None:
        html = pdf_export.build_report_html(sample_result("D"))

        self.assertIn("个性化转型路径建议", html)
        self.assertIn("优先学习内容推荐", html)
        self.assertIn("完成数据合规底座", html)
        self.assertIn("AI与数据关系：数据是AI系统的核心燃料", html)
        self.assertIn("用你对数据的专业敏感度", html)
        self.assertNotIn("–", html)

    def new_result(self, version="full"):
        config = get_config()
        ids = select_question_ids(config) if version == "lite" else [q["key"] for q in load_bank()["questions"]]
        result = score_answers({key: 0 for key in ids}, version, config)
        result.update(generated_at="2026-10-26T06:00:00+00:00", createdAt="2026-10-26T06:00:00+00:00", userName="测试学员")
        return result

    def test_lite_pdf_has_four_blocks_and_exactly_three_features(self) -> None:
        result = self.new_result("lite")
        html = pdf_export.build_report_html(result)
        self.assertEqual(html.count('data-result-block='), 4)
        self.assertEqual(html.count('data-core-feature='), 3)
        for text in ("主类型结论", "五类得分", "核心特征", "发展建议", result["algorithm_version"], "2026-10-26"):
            self.assertIn(text, html)
        self.assertNotIn("当前AI知识水位", html)
        self.assertNotIn("个性化转型路径建议", html)

    def test_legacy_pdf_displays_the_same_shares_as_the_saved_web_result(self) -> None:
        config = dict(get_config(), algorithm_version="legacy_v1")
        for version in ("lite", "full"):
            ids = select_question_ids(config) if version == "lite" else [q["key"] for q in load_bank()["questions"]]
            result = score_answers({key: 0 for key in ids}, version, config)
            html = pdf_export.build_report_html(result)
            for value in result["pcts"].values():
                self.assertTrue(f'>{value}%</div>' in html, f"PDF must display the saved share {value}%")

    def test_full_pdf_uses_standard_scores_and_preserves_all_report_sections(self) -> None:
        result = self.new_result()
        html = pdf_export.build_report_html(result)
        for text in (result["algorithm_version"], "2026-10-26", "明显倾向" if result["tendency_strength"] == "明显倾向" else result["tendency_strength"], "类型核心特征", "当前AI知识水位", "学习方式偏好", "个性化转型路径建议", "优先学习内容推荐"):
            self.assertIn(text, html)
        for value in result["pcts"].values():
            self.assertIn(f'>{value}分</div>', html)

    def test_mixed_conclusion_and_explanation_are_preserved_in_pdf(self) -> None:
        result = self.new_result()
        result.update(mainType=None, secondType=None, is_mixed=True, isDouble=True, conclusion="复合型 / 待观察", conclusion_reason="多个类型接近，请结合真实项目继续观察。", tendency_strength="倾向不明显")
        html = pdf_export.build_report_html(result)
        self.assertIn("复合型 / 待观察", html)
        self.assertIn("多个类型接近，请结合真实项目继续观察。", html)

    def test_full_radar_title_and_values_use_saved_main_type(self) -> None:
        result = sample_result("A")
        result.update(mainTypeName="AI赋能者", leadingType="M", is_mixed=False)
        result["dimNorm"] = {dim: {"A": value, "M": 90 + index} for index, (dim, value) in enumerate(zip("EKILP", (11, 22, 33, 44, 55)))}
        self.assertEqual(pdf_export.dim_scores(result), dict(zip("EKILP", (11, 22, 33, 44, 55))))
        html = pdf_export.build_report_html(result)
        self.assertIn("AI赋能者五维倾向得分", html)

    def test_mixed_radar_preserves_reference_values_and_neutral_title(self) -> None:
        result = sample_result("A")
        result.update(mainTypeName="AI赋能者", is_mixed=True)
        result["dimNorm"] = {dim: {"A": 11, "M": 91} for dim in "EKILP"}
        self.assertEqual(pdf_export.dim_scores(result), dict.fromkeys("EKILP", 91))
        html = pdf_export.build_report_html(result)
        self.assertIn("五维倾向参考得分（复合型 / 待观察）", html)
        self.assertNotIn("AI赋能者五维倾向得分", html)


if __name__ == "__main__":
    unittest.main()
