"""Create an admin account, or promote an existing account to admin.

Run from the backend folder:
    python -m scripts.create_admin --email admin@example.com

The password is asked for interactively (hidden input). For automation, set
ADMIN_EMAIL / ADMIN_PASSWORD environment variables instead.

There is no --password option on purpose: command-line arguments are saved in
shell history and visible to other users in the process list.

The public /auth/register endpoint always creates viewers, so this script is
the only way to get an admin.
"""

import argparse
import getpass
import os
import sys

from pydantic import ValidationError

from app.database import SessionLocal
from app.models import Account, Role
from app.repositories import account_repository
from app.schemas import RegisterRequest
from app.security import hash_password


def read_password() -> str:
    password = os.getenv("ADMIN_PASSWORD")
    if password:
        return password

    password = getpass.getpass("Password (min 8 characters): ")
    if getpass.getpass("Repeat password: ") != password:
        sys.exit("Passwords do not match.")
    return password


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL"), help="or set ADMIN_EMAIL")
    args = parser.parse_args()

    if not args.email:
        parser.error("give --email or set ADMIN_EMAIL")

    with SessionLocal() as db:
        existing = account_repository.get_by_email(db, args.email)

        if existing is not None:
            if existing.role == Role.ADMIN:
                print(f"{existing.email} is already an admin. Nothing changed.")
                return
            existing.role = Role.ADMIN.value
            db.commit()
            print(f"Promoted {existing.email} to admin (password unchanged).")
            return

        # Reuse the API's rules, so admins follow the same email/password policy.
        try:
            data = RegisterRequest(email=args.email, password=read_password())
        except ValidationError as error:
            problems = "; ".join(f"{e['loc'][0]}: {e['msg']}" for e in error.errors())
            sys.exit(f"Invalid input: {problems}")

        account = Account(
            email=data.email,
            hashed_password=hash_password(data.password),
            role=Role.ADMIN.value,
        )
        account_repository.add_account(db, account)
        print(f"Created admin {account.email} (id {account.id}).")


if __name__ == "__main__":
    main()
