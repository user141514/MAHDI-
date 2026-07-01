from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML_FILE = next(ROOT.glob("MAHDI*.html"))


class FrontendHtmlTests(unittest.TestCase):
    def test_defines_esc_html_before_instructor_dashboard_uses_it(self) -> None:
        source = HTML_FILE.read_text(encoding="utf-8")

        define_pos = source.find("function escHtml")
        render_pos = source.find("function renderInstructorDashboard")

        self.assertNotEqual(-1, define_pos)
        self.assertNotEqual(-1, render_pos)
        self.assertLess(define_pos, render_pos)

    def test_instructor_login_does_not_display_default_password(self) -> None:
        source = HTML_FILE.read_text(encoding="utf-8")

        self.assertNotIn("teacher / meitai123456", source)
        self.assertNotIn("默认密码：", source)

    def test_result_page_has_pdf_export_button_and_handler(self) -> None:
        source = HTML_FILE.read_text(encoding="utf-8")

        self.assertIn('id="pdfBtn"', source)
        self.assertIn("function exportLatestPdf", source)
        self.assertIn("/api/results/latest/pdf", source)

    def test_has_temporary_latest_result_shortcut_without_resaving(self) -> None:
        source = HTML_FILE.read_text(encoding="utf-8")

        self.assertIn('id="latestResultBtn"', source)
        self.assertIn("function showLatestStoredResult", source)
        self.assertIn("skipSave", source)
        self.assertIn("options.skipSave ? null : saveAssessmentResult", source)


if __name__ == "__main__":
    unittest.main()
