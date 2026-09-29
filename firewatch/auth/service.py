"""Administrator authentication (REQ-8.2 to 8.4).

- Passwords are checked against bcrypt hashes (the salt is inside the hash).
- After MAX_FAILED_LOGINS wrong passwords in a row for a username, that
  username is blocked for LOCKOUT_MINUTES.
- Wrong username and wrong password are indistinguishable to the caller.
"""
from datetime import datetime, timedelta
from functools import lru_cache
from math import ceil

import bcrypt
from sqlalchemy import select

from firewatch.config import LOCKOUT_MINUTES, MAX_FAILED_LOGINS
from firewatch.db.models import AdminUser
from firewatch.db.session import session_scope


class LoginLocked(Exception):
    """Raised while a username is temporarily blocked."""

    def __init__(self, minutes: int):
        self.minutes = minutes
        super().__init__(f"Login blocked for {minutes} more minute(s)")


@lru_cache(maxsize=1)
def _dummy_hash() -> bytes:
    # Checked when the username doesn't exist, so response time doesn't reveal it.
    return bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt())


def _verify(password: str, password_hash: bytes) -> bool:
    pw = password.encode()
    if len(pw) > 72:                       # bcrypt limit; create_admin rejects these too
        return False
    try:
        return bcrypt.checkpw(pw, password_hash)
    except ValueError:                     # malformed stored hash
        return False


def authenticate(username: str, password: str):
    """Returns the admin_id on success, None for invalid credentials.
    Raises LoginLocked while the username is blocked."""
    username = (username or "").strip()
    now = datetime.now()
    locked_minutes = None

    with session_scope() as db:
        admin = db.scalar(select(AdminUser).where(AdminUser.username == username))
        if admin is None:
            _verify(password or "", _dummy_hash())
            return None

        if admin.locked_until and admin.locked_until > now:
            raise LoginLocked(ceil((admin.locked_until - now).total_seconds() / 60))
        if admin.locked_until:             # block has expired: start fresh
            admin.locked_until, admin.failed_attempts = None, 0

        if _verify(password or "", admin.password_hash.encode()):
            admin.failed_attempts, admin.locked_until = 0, None
            return admin.admin_id

        admin.failed_attempts += 1
        if admin.failed_attempts >= MAX_FAILED_LOGINS:
            admin.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            admin.failed_attempts = 0
            locked_minutes = LOCKOUT_MINUTES
    # raised after the with-block so the lock is committed, not rolled back
    if locked_minutes:
        raise LoginLocked(locked_minutes)
    return None