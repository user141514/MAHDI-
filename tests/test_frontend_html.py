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


if __name__ == "__main__":
    unittest.main()
