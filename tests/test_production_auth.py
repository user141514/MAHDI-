from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException

from backend import account_api, auth_local, storage
from backend.account_api import AnswerResetReq, CreateReq, EmailReq, OpenReq
from backend.passwords import hash_password, is_password_hash, verify_password
from backend.session_local import get_current


class ProductionAuthTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.db = patch.object(storage, "DB_PATH", Path(self.temp.name) / "auth.db")
        self.db.start()
        storage.init_db()

    def tearDown(self):
        self.db.stop()
        self.temp.cleanup()

    def create(self):
        return account_api.create_account(CreateReq(
            email="student@example.invalid", pin="test-pass-1234", display_name="Test",
            company_name="Test", job_title="Test", rq="Question", ra="Answer",
        ))

    def stored_user(self):
        with storage.connect() as conn:
            return conn.execute("SELECT * FROM users WHERE email=?", ("student@example.invalid",)).fetchone()

    def test_registered_password_is_hashed_and_login_checks_it(self):
        self.create()
        value = self.stored_user()["password_hash"]
        self.assertNotEqual(value, "test-pass-1234")
        self.assertTrue(verify_password("test-pass-1234", value))
        account_api.open_account(OpenReq(email="student@example.invalid", pin="test-pass-1234"))
        with self.assertRaises(HTTPException) as caught:
            account_api.open_account(OpenReq(email="student@example.invalid", pin="incorrect"))
        self.assertEqual(caught.exception.status_code, 401)

    def test_existing_plaintext_account_is_upgraded_without_resetting_password(self):
        self.create()
        with storage.connect() as conn:
            conn.execute("UPDATE users SET password_hash=?", ("legacy-password",))
        account_api.open_account(OpenReq(email="student@example.invalid", pin="legacy-password"))
        value = self.stored_user()["password_hash"]
        self.assertTrue(is_password_hash(value))
        self.assertTrue(verify_password("legacy-password", value))

    def test_password_reset_hashes_password_and_revokes_old_sessions(self):
        created = self.create()
        account_api.recover_reset(AnswerResetReq(email="student@example.invalid", recovery_answer="answer", new_pin="new-pass-9876"))
        self.assertTrue(verify_password("new-pass-9876", self.stored_user()["password_hash"]))
        with self.assertRaises(HTTPException) as caught:
            get_current("Bearer " + created["accessToken"])
        self.assertEqual(caught.exception.status_code, 401)
        account_api.open_account(OpenReq(email="student@example.invalid", pin="new-pass-9876"))

    def test_missing_recovery_answer_returns_auth_error(self):
        self.create()
        with self.assertRaises(HTTPException) as caught:
            account_api.recover_reset(AnswerResetReq(email="student@example.invalid", new_pin="new-pass-9876"))
        self.assertEqual(caught.exception.status_code, 401)

    def test_production_rejects_missing_or_short_teacher_password(self):
        for value in ("", "short", "meitai123456"):
            with self.subTest(value=value), patch.dict(os.environ, {"MAHDI_ENV":"production", "MAHDI_TEACHER_PASSWORD":value}):
                with self.assertRaises(RuntimeError):
                    auth_local.ensure_teacher()

    def test_production_teacher_uses_configured_password_hash(self):
        password = "test-only-teacher-password-93725"
        with patch.dict(os.environ, {"MAHDI_ENV":"production", "MAHDI_TEACHER_PASSWORD":password}), patch.object(auth_local, "TEACHER_PIN", password):
            auth_local.ensure_teacher()
        with storage.connect() as conn:
            row = conn.execute("SELECT password_hash FROM users WHERE role='instructor'").fetchone()
        self.assertNotEqual(row[0], password)
        self.assertTrue(verify_password(password, row[0]))

    def test_production_mail_without_configuration_does_not_issue_token(self):
        self.create()
        with patch.dict(os.environ, {"MAHDI_ENV":"production"}), patch.object(account_api, "mail_ready", return_value=False):
            with self.assertRaises(HTTPException) as caught:
                account_api.mail_start(EmailReq(email="student@example.invalid"))
        self.assertEqual(caught.exception.status_code, 503)
        self.assertIsNone(self.stored_user()["reset_token"])

    def test_production_mail_never_returns_debug_link_even_if_sending_returns_false(self):
        self.create()
        with patch.dict(os.environ, {"MAHDI_ENV":"production"}), patch.object(account_api, "mail_ready", return_value=True), patch.object(account_api, "send_reset_link", return_value=False):
            response = account_api.mail_start(EmailReq(email="student@example.invalid"))
        self.assertIsNone(response["resetUrl"])

    def test_hashes_are_salted_and_malformed_hashes_are_rejected(self):
        self.assertNotEqual(hash_password("example"), hash_password("example"))
        self.assertFalse(verify_password("example", "pbkdf2_sha256$bad$salt$hash"))

    def test_frontend_does_not_embed_teacher_password_or_interpolate_recovery_html(self):
        source = next(Path(__file__).resolve().parents[1].glob("MAHDI*.html")).read_text(encoding="utf-8")
        self.assertNotIn("meitai123456", source)
        self.assertNotIn("DEFAULT_INSTRUCTOR.password", source)
        self.assertIn("${escHtml(data.recoveryQuestion)}", source)
