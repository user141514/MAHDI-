from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend import storage
from backend.auth_local import TEACHER_ACCOUNT, TEACHER_PIN, ensure_teacher


class EnsureTeacherTests(unittest.TestCase):
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
