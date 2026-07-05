"""Database seeding script to initialize default system records."""

import asyncio
import logging

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserRole

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_database() -> None:
    """Seed the database with a default administrator if one doesn't exist."""
    async with SessionLocal() as db:
        # Check if an admin user already exists
        query = select(User).where(User.role == UserRole.ADMIN)
        result = await db.execute(query)
        admin = result.scalar_one_or_none()

        if admin:
            logger.info("Database already seeded: Admin user exists.")
            return

        # Create default admin user
        default_admin = User(
            email="admin@enterprise.com",
            hashed_password=hash_password("adminpassword123"),
            full_name="System Administrator",
            is_active=True,
            role=UserRole.ADMIN,
        )
        db.add(default_admin)
        await db.commit()
        logger.info("Database seeded successfully: Default administrator created.")


if __name__ == "__main__":
    asyncio.run(seed_database())
