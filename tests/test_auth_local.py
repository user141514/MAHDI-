from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend import storage
from backend.auth_local import TEACHER_ACCOUNT, TEACHER_PIN, ensure_teacher, public_user


class EnsureTeacherTests(unittest.TestCase):
    def test_legacy_administrator_display_preserves_stored_identity_and_custom_names(self) -> None:
        stored = dict(id="teacher", email=TEACHER_ACCOUNT, display_name="讲师", company_name="美太咨询", job_title="讲师", role="instructor", created_at="2026-10-26")
        shown = public_user(stored)
        self.assertEqual((shown["displayName"], shown["jobTitle"]), ("管理员", "管理员"))
        self.assertEqual((shown["id"], shown["email"], shown["role"]), ("teacher", TEACHER_ACCOUNT, "instructor"))
        self.assertEqual((stored["display_name"], stored["job_title"]), ("讲师", "讲师"))
        self.assertEqual(public_user(dict(stored, display_name="王老师"))["displayName"], "王老师")
        self.assertEqual(public_user(dict(stored, role="student"))["displayName"], "讲师")

    def test_creates_teacher_when_users_table_has_migration_columns(self) -> None:
        original_db_path = storage.DB_PATH
        with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            storage.DB_PATH = Path(temp_dir) / "mahid.db"
            try:
                storage.init_db()

                with storage.connect() as conn:
                    columns = conn.execute("PRAGMA table_info(users)").fetchall()
                self.assertEqual(12, len(columns))

                ensure_teacher()

                with storage.connect() as conn:
                    row = conn.execute(
                        "SELECT * FROM users WHERE email=? AND role='instructor'",
                        (TEACHER_ACCOUNT,),
                    ).fetchone()

                self.assertIsNotNone(row)
                self.assertEqual(TEACHER_PIN, row["password_hash"])
                self.assertIsNone(row["recovery_question"])
                self.assertIsNone(row["reset_token"])
            finally:
                storage.DB_PATH = original_db_path


if __name__ == "__main__":
    unittest.main()
