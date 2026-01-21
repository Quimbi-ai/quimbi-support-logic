"""
Import 10 actual tickets from Gorgias with real customer data.
Uses email-based customer ID resolution to map to Shopify customer IDs.
"""
import asyncio
import sys
import httpx
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import uuid

# Import customer resolver for ID mapping
from app.services.customer_resolver import customer_resolver

# Gorgias API configuration
GORGIAS_DOMAIN = "lindas"
GORGIAS_USERNAME = "lindas.quimbiai@proton.me"
GORGIAS_API_KEY = "14324b3a387404726a2dc1e2332fcc2a59fb0a79c9aecdca694028087864d735"
GORGIAS_BASE_URL = f"https://{GORGIAS_DOMAIN}.gorgias.com/api"

# Database configuration
DATABASE_URL = "postgresql+asyncpg://postgres:XzLuopeMhZwurhlOWaObisBJxiTFViCb@turntable.proxy.rlwy.net:30126/railway"


async def fetch_gorgias_tickets(limit=10):
    """Fetch recent tickets from Gorgias."""
    print(f"Fetching {limit} tickets from Gorgias...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{GORGIAS_BASE_URL}/tickets",
                auth=(GORGIAS_USERNAME, GORGIAS_API_KEY),
                params={
                    "limit": limit,
                    "order_by": "created_datetime:desc"
                }
            )

            if response.status_code == 200:
                data = response.json()
                tickets = data.get('data', [])
                print(f"✓ Fetched {len(tickets)} tickets from Gorgias")
                return tickets
            else:
                print(f"✗ Failed to fetch tickets: Status {response.status_code}")
                print(f"  Response: {response.text[:200]}")
                return []

        except Exception as e:
            print(f"✗ Error fetching tickets: {e}")
            return []


async def fetch_ticket_messages(ticket_id):
    """Fetch messages for a specific ticket."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{GORGIAS_BASE_URL}/tickets/{ticket_id}/messages",
                auth=(GORGIAS_USERNAME, GORGIAS_API_KEY)
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
            else:
                print(f"  ⚠ Could not fetch messages for ticket {ticket_id}")
                return []

        except Exception as e:
            print(f"  ⚠ Error fetching messages: {e}")
            return []


async def import_ticket_to_database(session, ticket_data):
    """Import a single ticket with its messages into the database."""

    # Extract customer info
    customer = ticket_data.get('customer', {})
    gorgias_customer_id = customer.get('id')
    customer_email = customer.get('email', 'unknown@email.com')
    customer_name = customer.get('name', 'Unknown Customer')

    # CRITICAL: Resolve email to Shopify customer ID for intelligence
    shopify_customer_id = None
    if customer_email and customer_email != 'unknown@email.com':
        shopify_customer_id = await customer_resolver.resolve_by_email(session, customer_email)

    # Use Shopify ID if found, otherwise fallback to Gorgias ID
    if shopify_customer_id:
        customer_id = str(shopify_customer_id)
        print(f"\n  ✓ Resolved {customer_email} → Shopify ID {customer_id}")
    else:
        customer_id = customer.get('external_id') or str(gorgias_customer_id) or str(uuid.uuid4())
        print(f"\n  ⚠ No Shopify mapping for {customer_email}, using Gorgias ID {customer_id}")

    # Extract ticket info
    gorgias_ticket_id = ticket_data.get('id')
    subject = ticket_data.get('subject', 'No Subject')
    status = ticket_data.get('status', 'open')
    channel = ticket_data.get('channel', 'email')
    priority = 'normal'

    # Map Gorgias status to our status
    if status == 'closed':
        our_status = 'closed'
    elif status == 'open':
        our_status = 'open'
    else:
        our_status = 'pending'

    print(f"  Importing ticket #{gorgias_ticket_id}: {subject[:50]}...")
    print(f"    Customer: {customer_name} ({customer_email})")
    print(f"    Customer ID: {customer_id}")

    # Create or get customer
    await session.execute(
        text("""
            INSERT INTO public.customers (id, email, name, lifetime_value, total_orders, churn_risk_score, created_at)
            VALUES (:id, :email, :name, 0.0, 0, 0.0, NOW())
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id": str(customer_id),
            "email": customer_email,
            "name": customer_name
        }
    )

    # Create ticket
    ticket_id = f"gorgias_{gorgias_ticket_id}"

    # Parse datetimes and remove timezone info (database expects naive datetimes)
    created_dt = datetime.fromisoformat(ticket_data.get('created_datetime', datetime.now().isoformat()).replace('Z', '+00:00'))
    updated_dt = datetime.fromisoformat(ticket_data.get('updated_datetime', datetime.now().isoformat()).replace('Z', '+00:00'))

    await session.execute(
        text("""
            INSERT INTO public.tickets
            (id, customer_id, subject, status, priority, channel, created_at, updated_at, customer_sentiment, smart_score, estimated_difficulty)
            VALUES (:id, :customer_id, :subject, :status, :priority, :channel, :created_at, :updated_at, 0.5, 10.0, 0.5)
        """),
        {
            "id": ticket_id,
            "customer_id": str(customer_id),
            "subject": subject,
            "status": our_status,
            "priority": priority,
            "channel": channel,
            "created_at": created_dt.replace(tzinfo=None),
            "updated_at": updated_dt.replace(tzinfo=None)
        }
    )

    # Fetch and import messages
    messages = await fetch_ticket_messages(gorgias_ticket_id)
    print(f"    Messages: {len(messages)}")

    for msg in messages[:5]:  # Import first 5 messages
        body = msg.get('body_text', msg.get('stripped_text', ''))
        if not body:
            continue

        from_agent = msg.get('source', {}).get('type') == 'agent'
        sender = msg.get('sender', {})
        from_name = sender.get('name', customer_name if not from_agent else 'Support Agent')
        from_email = sender.get('email', customer_email if not from_agent else 'support@quimbi.com')

        msg_created_dt = datetime.fromisoformat(msg.get('created_datetime', datetime.now().isoformat()).replace('Z', '+00:00'))

        await session.execute(
            text("""
                INSERT INTO public.messages
                (id, ticket_id, content, from_agent, from_name, from_email, created_at)
                VALUES (:id, :ticket_id, :content, :from_agent, :from_name, :from_email, :created_at)
            """),
            {
                "id": str(uuid.uuid4()),
                "ticket_id": ticket_id,
                "content": body[:1000],  # Limit content length
                "from_agent": from_agent,
                "from_name": from_name,
                "from_email": from_email,
                "created_at": msg_created_dt.replace(tzinfo=None)
            }
        )

    print(f"    ✓ Imported successfully")
    return ticket_id


async def main():
    """Main import function."""
    print("=" * 80)
    print("IMPORTING GORGIAS TICKETS WITH REAL CUSTOMER DATA")
    print("=" * 80)

    # Fetch tickets from Gorgias
    tickets = await fetch_gorgias_tickets(limit=10)

    if not tickets:
        print("\n✗ No tickets fetched. Exiting.")
        return

    # Import to database
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    imported_count = 0
    async with async_session() as session:
        for ticket in tickets:
            try:
                await import_ticket_to_database(session, ticket)
                imported_count += 1
            except Exception as e:
                print(f"    ✗ Error importing ticket: {e}")
                continue

        await session.commit()

    print("\n" + "=" * 80)
    print(f"IMPORT COMPLETE: {imported_count}/{len(tickets)} tickets imported successfully")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
