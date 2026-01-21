"""
Delete all Gorgias-imported tickets to prepare for re-import with proper customer IDs.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Database configuration
DATABASE_URL = "postgresql+asyncpg://postgres:XzLuopeMhZwurhlOWaObisBJxiTFViCb@turntable.proxy.rlwy.net:30126/railway"


async def delete_gorgias_tickets():
    """Delete all tickets that start with 'gorgias_'."""
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Count tickets
        count_result = await session.execute(
            text("SELECT COUNT(*) FROM public.tickets WHERE id LIKE 'gorgias_%'")
        )
        ticket_count = count_result.scalar()

        # Count messages
        msg_count_result = await session.execute(
            text("SELECT COUNT(*) FROM public.messages WHERE ticket_id LIKE 'gorgias_%'")
        )
        message_count = msg_count_result.scalar()

        print(f"Found {ticket_count} Gorgias tickets with {message_count} messages")

        if ticket_count == 0:
            print("No Gorgias tickets to delete.")
            return

        # Delete messages first (foreign key constraint)
        await session.execute(
            text("DELETE FROM public.messages WHERE ticket_id LIKE 'gorgias_%'")
        )
        print(f"✓ Deleted {message_count} messages")

        # Delete tickets
        await session.execute(
            text("DELETE FROM public.tickets WHERE id LIKE 'gorgias_%'")
        )
        print(f"✓ Deleted {ticket_count} tickets")

        await session.commit()
        print("\n✓ All Gorgias tickets deleted successfully")


if __name__ == "__main__":
    asyncio.run(delete_gorgias_tickets())
