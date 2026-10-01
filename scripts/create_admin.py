"""Creates an administrator account (there is no self-registration, REQ-8.6).

Run from the project root:   python -m scripts.create_admin
"""
from getpass import getpass

import bcrypt
from sqlalchemy import select

from firewatch.db.models import AdminUser
from firewatch.db.session import backend_name, session_scope


def main():
    print(f"Database: {backend_name()}")
    username = input("Admin username: ").strip()
    if not username or len(username) > 50:
        raise SystemExit("Username must be 1-50 characters.")

    password = getpass("Password (min 8 characters): ")
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters.")
    if len(password.encode()) > 72:
        raise SystemExit("Password is too long (bcrypt limit is 72 bytes).")
    if password != getpass("Repeat password: "):
        raise SystemExit("Passwords did not match.")

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()   # salt included
    with session_scope() as db:
        if db.scalar(select(AdminUser).where(AdminUser.username == username)):
            raise SystemExit(f"'{username}' already exists.")
        db.add(AdminUser(username=username, password_hash=hashed))
    print(f"Admin '{username}' created.")


if __name__ == "__main__":
    main()