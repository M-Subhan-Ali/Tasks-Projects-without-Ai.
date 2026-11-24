class AppError(Exception):
    """Base class for errors raised by the application's business logic.

    Services raise these instead of HTTPException, so they stay independent of
    FastAPI. main.py turns them into HTTP responses in one place.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UserNotFound(AppError):
    def __init__(self, user_id: int) -> None:
        super().__init__("User not found")
        self.user_id = user_id


class EmailAlreadyExists(AppError):
    def __init__(self, email: str) -> None:
        super().__init__("This email already exists")
        self.email = email


class InvalidCredentials(AppError):
    """Wrong email OR wrong password. One message for both, on purpose:
    a different message would tell an attacker which emails have accounts."""

    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class NotAuthenticated(AppError):
    """Missing, invalid or expired token, or the account no longer exists."""

    def __init__(self, message: str = "Not authenticated") -> None:
        super().__init__(message)
