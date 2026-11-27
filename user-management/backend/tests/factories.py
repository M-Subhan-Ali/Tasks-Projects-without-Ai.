from typing import Any

# A public internet address (example.com's), for webhook URLs and the fake DNS.
# The documentation ranges such as 203.0.113.0/24 can't be used: Python rightly
# says they are not global. Never contacted: no test opens a real socket.
PUBLIC_IP = "93.184.215.14"


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
