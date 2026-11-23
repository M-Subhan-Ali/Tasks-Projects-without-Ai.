"""Insert sample users when the users table is empty.

Run from the backend folder:  python -m scripts.seed
"""

import logging

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User

logger = logging.getLogger(__name__)

SAMPLE_USERS: list[dict[str, str]] = [
    {"name": "John Smith", "email": "john@example.com", "phone": "0300-1234567", "city": "Karachi", "company_name": "Tech Solutions"},
    {"name": "Sarah Johnson", "email": "sarah@example.com", "phone": "0301-2345678", "city": "Lahore", "company_name": "Creative Studio"},
    {"name": "David Brown", "email": "david@example.com", "phone": "0302-3456789", "city": "Islamabad", "company_name": "Data Systems"},
    {"name": "Michael Wilson", "email": "michael@example.com", "phone": "0303-4567890", "city": "Rawalpindi", "company_name": "Cloud Works"},
    {"name": "Emily Davis", "email": "emily@example.com", "phone": "0304-5678901", "city": "Faisalabad", "company_name": "Market Hub"},
    {"name": "James Taylor", "email": "james@example.com", "phone": "0305-6789012", "city": "Multan", "company_name": "Finance Pro"},
]


def seed_users() -> None:
    with SessionLocal() as db:
        if db.scalars(select(User)).first() is not None:
            logger.info("Users table is not empty, skipping seed")
            return

        db.add_all([User(**data) for data in SAMPLE_USERS])
        db.commit()
        logger.info("Inserted %d sample users", len(SAMPLE_USERS))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_users()
