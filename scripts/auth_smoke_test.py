"""Checks login, lockout and reset. Run: python -m scripts.auth_smoke_test
Creates a throwaway admin and deletes it afterwards."""
from datetime import datetime, timedelta

import bcrypt

from firewatch.auth.service import LoginLocked, authenticate
from firewatch.config import MAX_FAILED_LOGINS
from firewatch.db.models import AdminUser
from firewatch.db.session import backend_name, session_scope

USER, PW = "auth_test_admin", "correct-horse-battery"


def main():
    print(f"Database: {backend_name()}")
    hashed = bcrypt.hashpw(PW.encode(), bcrypt.gensalt()).decode()
    with session_scope() as db:
        a = AdminUser(username=USER, password_hash=hashed)
        db.add(a); db.flush(); aid = a.admin_id
    try:
        assert authenticate(USER, PW) == aid;                 print("Correct login: OK")
        assert authenticate(USER, "wrong") is None;           print("Wrong password rejected: OK")
        assert authenticate("nobody", PW) is None;            print("Unknown username rejected: OK")
        assert authenticate(USER, PW) == aid;                 print("Success resets the counter: OK")

        for _ in range(MAX_FAILED_LOGINS - 1):
            assert authenticate(USER, "wrong") is None
        try:
            authenticate(USER, "wrong"); raise AssertionError("no lockout")
        except LoginLocked:
            print(f"Locked after {MAX_FAILED_LOGINS} failures: OK")
        try:
            authenticate(USER, PW); raise AssertionError("correct password worked while locked")
        except LoginLocked:
            print("Correct password blocked while locked: OK")

        with session_scope() as db:                           # pretend the block has expired
            db.get(AdminUser, aid).locked_until = datetime.now() - timedelta(seconds=1)
        assert authenticate(USER, PW) == aid;                 print("Login works after lock expires: OK")
        print("All checks passed.")
    finally:
        with session_scope() as db:
            db.delete(db.get(AdminUser, aid))


if __name__ == "__main__":
    main()