"""
Seed script to create initial admin agent.
"""
import asyncio
import sys
from app.models.database import get_db, Base, engine
from app.models.agent import Agent, AgentRole, AgentStatus
from app.services.auth import AuthService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


async def create_admin():
    """Create initial admin agent."""
    print("Creating admin agent...")

    # Create session
    async with AsyncSession(engine) as session:
        # Check if admin already exists
        result = await session.execute(select(Agent).where(Agent.email == "admin@example.com"))
        existing = result.scalar_one_or_none()

        if existing:
            print("❌ Admin agent already exists!")
            print(f"   Email: {existing.email}")
            print(f"   Name: {existing.name}")
            print(f"   Role: {existing.role.value}")
            return

        # Create admin agent
        admin = Agent(
            email="admin@example.com",
            hashed_password=AuthService.hash_password("admin123"),
            name="Admin User",
            role=AgentRole.ADMIN,
            department="Management",
            status=AgentStatus.OFFLINE,
            max_concurrent_tickets=20,
            specializations=["all"],
        )

        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        print("✅ Admin agent created successfully!")
        print(f"   Email: {admin.email}")
        print(f"   Password: admin123")
        print(f"   Role: {admin.role.value}")
        print(f"   ID: {admin.id}")
        print()
        print("You can now login with these credentials:")
        print("POST /api/agents/login")
        print('{"email": "admin@example.com", "password": "admin123"}')


if __name__ == "__main__":
    asyncio.run(create_admin())
