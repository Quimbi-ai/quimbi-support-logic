#!/usr/bin/env python3
"""
Create Test Tickets for Chat and SMS

Creates demo tickets to showcase multi-channel support with customer intelligence.
"""
import asyncio
import os
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/railway")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_chat_ticket():
    """Create a live chat ticket from a power buyer customer."""
    async with AsyncSessionLocal() as db:
        # Use Debby Stanford-Miller (our power buyer with 52 orders)
        customer_id = "4595328254127"  # Debby's Shopify ID

        ticket_id = "chat_live_001"
        subject = "Live Chat: Question about bulk order discount"

        # Create ticket
        await db.execute(
            text("""
                INSERT INTO public.tickets
                    (id, subject, status, priority, channel, customer_id, created_at, updated_at)
                VALUES
                    (:id, :subject, 'open', 'normal', 'chat', :customer_id, :created_at, :updated_at)
                ON CONFLICT (id) DO UPDATE SET
                    subject = EXCLUDED.subject,
                    status = EXCLUDED.status,
                    channel = EXCLUDED.channel,
                    customer_id = EXCLUDED.customer_id,
                    updated_at = EXCLUDED.updated_at
            """),
            {
                "id": ticket_id,
                "subject": subject,
                "customer_id": customer_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        )

        # Create initial message
        await db.execute(
            text("""
                INSERT INTO public.messages
                    (id, ticket_id, content, from_email, from_agent, created_at)
                VALUES
                    (:id, :ticket_id, :content, :from_email, false, :created_at)
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": f"{ticket_id}_msg_001",
                "ticket_id": ticket_id,
                "content": "Hi! I'm placing another large order (around 20 pantographs). Do you offer any bulk discounts for customers who order frequently? I've ordered from you many times before.",
                "from_email": "debbymiller@centurylink.net",
                "created_at": datetime.utcnow()
            }
        )

        await db.commit()
        print(f"✅ Created chat ticket: {ticket_id}")
        print(f"   Customer: Debby Stanford-Miller (52 orders, $1,235 LTV)")
        print(f"   Channel: Live Chat")
        print(f"   Subject: {subject}")
        return ticket_id


async def create_sms_ticket():
    """Create an SMS ticket from a customer with order history."""
    async with AsyncSessionLocal() as db:
        # Find a customer with some orders for SMS demo
        # Let's use customer_id that we know exists
        customer_id = "4595328254127"  # Using same customer for demo

        ticket_id = "sms_support_001"
        subject = "SMS: Tracking number request"

        # Create ticket
        await db.execute(
            text("""
                INSERT INTO public.tickets
                    (id, subject, status, priority, channel, customer_id, created_at, updated_at)
                VALUES
                    (:id, :subject, 'open', 'high', 'sms', :customer_id, :created_at, :updated_at)
                ON CONFLICT (id) DO UPDATE SET
                    subject = EXCLUDED.subject,
                    status = EXCLUDED.status,
                    channel = EXCLUDED.channel,
                    customer_id = EXCLUDED.customer_id,
                    updated_at = EXCLUDED.updated_at
            """),
            {
                "id": ticket_id,
                "subject": subject,
                "customer_id": customer_id,
                "created_at": datetime.utcnow() - timedelta(hours=2),
                "updated_at": datetime.utcnow() - timedelta(hours=2)
            }
        )

        # Create initial SMS message
        await db.execute(
            text("""
                INSERT INTO public.messages
                    (id, ticket_id, content, from_email, from_agent, created_at)
                VALUES
                    (:id, :ticket_id, :content, :from_email, false, :created_at)
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": f"{ticket_id}_msg_001",
                "ticket_id": ticket_id,
                "content": "Hi, I ordered 3 days ago but haven't gotten a tracking number yet. Order was placed on your website. Can you check status?",
                "from_email": "sms:+15551234567",  # SMS phone number format
                "created_at": datetime.utcnow() - timedelta(hours=2)
            }
        )

        await db.commit()
        print(f"✅ Created SMS ticket: {ticket_id}")
        print(f"   Customer: Debby Stanford-Miller (power buyer)")
        print(f"   Channel: SMS")
        print(f"   Subject: {subject}")
        return ticket_id


async def create_google_groups_ticket():
    """Create a Google Groups email ticket demonstrating PII extraction."""
    async with AsyncSessionLocal() as db:
        # This ticket has NO customer_id - will use PII extraction
        ticket_id = "google_groups_001"
        subject = "Question from Linda's Electric Quilters group"

        # Create ticket WITHOUT customer_id
        await db.execute(
            text("""
                INSERT INTO public.tickets
                    (id, subject, status, priority, channel, created_at, updated_at)
                VALUES
                    (:id, :subject, 'open', 'normal', 'email', :created_at, :updated_at)
                ON CONFLICT (id) DO UPDATE SET
                    subject = EXCLUDED.subject,
                    status = EXCLUDED.status,
                    channel = EXCLUDED.channel,
                    updated_at = EXCLUDED.updated_at
            """),
            {
                "id": ticket_id,
                "subject": subject,
                "created_at": datetime.utcnow() - timedelta(hours=4),
                "updated_at": datetime.utcnow() - timedelta(hours=4)
            }
        )

        # Create message with Google Groups format - PII in content
        await db.execute(
            text("""
                INSERT INTO public.messages
                    (id, ticket_id, content, from_email, from_agent, created_at)
                VALUES
                    (:id, :ticket_id, :content, :from_email, false, :created_at)
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": f"{ticket_id}_msg_001",
                "ticket_id": ticket_id,
                "content": """Debby Stanford-Miller (debbymiller@centurylink.net) wrote:

I ordered 4 pantographs last week but only received 2 in the mail. The packing slip showed all 4 items, but the box only had 2. Can you please check on this and send the missing 2 pantographs?

I've been a customer for years and this is the first time I've had an issue. Usually your shipping is perfect!

Thanks,
Debby""",
                "from_email": "linda@lindaselectricquilters.com",  # Google Groups forwarding address
                "created_at": datetime.utcnow() - timedelta(hours=4)
            }
        )

        await db.commit()
        print(f"✅ Created Google Groups ticket: {ticket_id}")
        print(f"   From: linda@lindaselectricquilters.com (Google Groups)")
        print(f"   PII in body: Debby Stanford-Miller (debbymiller@centurylink.net)")
        print(f"   Will demonstrate PII extraction → hash lookup → customer intelligence")
        print(f"   Channel: Email")
        print(f"   Subject: {subject}")
        return ticket_id


async def main():
    """Create all test tickets."""
    print("=" * 80)
    print("Creating Test Tickets for Multi-Channel Demo")
    print("=" * 80)
    print()

    # Create tickets
    chat_id = await create_chat_ticket()
    print()

    sms_id = await create_sms_ticket()
    print()

    groups_id = await create_google_groups_ticket()
    print()

    print("=" * 80)
    print("✅ All test tickets created!")
    print("=" * 80)
    print()
    print("You can now view these tickets in the frontend:")
    print(f"  • Chat:          http://localhost:5173/tickets/{chat_id}")
    print(f"  • SMS:           http://localhost:5173/tickets/{sms_id}")
    print(f"  • Google Groups: http://localhost:5173/tickets/{groups_id}")
    print()
    print("Features demonstrated:")
    print("  ✅ Multi-channel support (Email, Chat, SMS)")
    print("  ✅ Customer intelligence across all channels")
    print("  ✅ PII extraction from Google Groups emails")
    print("  ✅ Privacy-preserving hash-based identity resolution")
    print("  ✅ Personalized AI responses based on purchase history")


if __name__ == "__main__":
    asyncio.run(main())
