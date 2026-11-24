"""Settings read from the environment (.env), checked once at startup.

If a security setting is missing or weak, the app refuses to start. Failing
loudly at startup is better than running with tokens anyone could forge.
"""

import os

from dotenv import load_dotenv

load_dotenv()

MIN_SECRET_LENGTH = 32


def _read_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "")

    if len(secret) < MIN_SECRET_LENGTH:
        raise RuntimeError(
            f"JWT_SECRET must be set and at least {MIN_SECRET_LENGTH} characters long. "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
    if secret.startswith("change-me"):
        raise RuntimeError("JWT_SECRET is still the placeholder from .env.example. Generate a real one.")

    return secret


def _read_expire_minutes() -> int:
    raw = os.getenv("JWT_EXPIRE_MINUTES", "30")

    try:
        minutes = int(raw)
    except ValueError:
        raise RuntimeError(f"JWT_EXPIRE_MINUTES must be a whole number, got {raw!r}") from None
    if minutes < 1:
        raise RuntimeError("JWT_EXPIRE_MINUTES must be at least 1")

    return minutes


def _read_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes"}


JWT_SECRET = _read_jwt_secret()
JWT_EXPIRE_MINUTES = _read_expire_minutes()
JWT_ALGORITHM = "HS256"

# The login token is stored in this httpOnly cookie.
AUTH_COOKIE_NAME = "access_token"
# Secure = only sent over HTTPS. Browsers treat http://localhost as secure, so
# this works in development too; set COOKIE_SECURE=false only if your browser
# refuses the cookie on plain http.
COOKIE_SECURE = _read_bool("COOKIE_SECURE", default=True)
