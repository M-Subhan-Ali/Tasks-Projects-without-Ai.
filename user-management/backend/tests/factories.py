from typing import Any


def user_payload(**overrides: Any) -> dict[str, Any]:
    """A valid POST /users body; pass keyword arguments to change fields."""
    payload: dict[str, Any] = {
        "name": "Ali Raza",
        "email": "ali.raza@example.com",
        "phone": "0321-1234567",
        "city": "Lahore",
        "company": {"name": "Cloud Pacer"},
    }
    payload.update(overrides)
    return payload
