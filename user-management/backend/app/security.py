"""Password hashing and JWT helpers.

Passwords: Argon2id is a one-way, salted and deliberately slow hash.
- one-way: the password cannot be recovered from the hash, only checked against it;
- salted: a random salt is stored inside each hash, so two accounts with the same
  password get different hashes and precomputed (rainbow) tables are useless;
- slow and memory-hard: each guess costs real time and RAM, so brute-forcing a
  stolen database is expensive.
The hash string records the algorithm, its parameters and the salt, e.g.
$argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>

Tokens: a JWT is header.payload.signature, each part base64url-encoded.
The payload is NOT encrypted, so anyone can read it: never put secrets in it.
The signature (HMAC-SHA256 with JWT_SECRET) proves the server issued the token
and that nobody changed the payload since.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET

# The library defaults follow the RFC 9106 recommendations.
_password_hasher = PasswordHasher()

# Used when the email does not exist, so a login for an unknown email takes as
# long as a wrong password. Otherwise response time would reveal which emails
# have accounts.
_DUMMY_HASH = _password_hasher.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(hashed_password: str, password: str) -> bool:
    try:
        return _password_hasher.verify(hashed_password, password)
    except (VerificationError, InvalidHashError):
        return False


def burn_password_check_time(password: str) -> None:
    """Spend the same time as a real check, for logins with an unknown email."""
    verify_password(_DUMMY_HASH, password)


def create_access_token(account_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(account_id),  # the JWT spec requires "sub" to be a string
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Return the payload of a valid token.

    Raises jwt.InvalidTokenError if the signature is wrong, the token has
    expired, or a required claim is missing.
    algorithms is pinned: never trust the "alg" written in the token header,
    or an attacker could send alg "none" and skip the signature check.
    """
    return jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "exp", "iat"]},
    )
