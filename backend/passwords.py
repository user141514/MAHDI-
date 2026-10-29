from __future__ import annotations

import hashlib
import hmac
import secrets

PREFIX = "pbkdf2_sha256"
ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), ITERATIONS).hex()
    return f"{PREFIX}${ITERATIONS}${salt}${digest}"


def is_password_hash(value: str) -> bool:
    return value.startswith(PREFIX + "$")


def verify_password(password: str, stored: str) -> bool:
    if not is_password_hash(stored):
        # Existing local accounts are upgraded after successful authentication.
        return hmac.compare_digest(password.encode("utf-8"), stored.encode("utf-8"))
    try:
        _, iterations, salt, expected = stored.split("$")
        rounds = int(iterations)
        if not 1 <= rounds <= 2_000_000:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), rounds).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, UnicodeError):
        return False
