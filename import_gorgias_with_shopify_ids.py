"""
Import Gorgias tickets with Shopify customer IDs extracted from integration data.
"""
import asyncio
import httpx
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import uuid

# Database configuration
DATABASE_URL = "postgresql+asyncpg://postgres:XzLuopeMhZwurhlOWaObisBJxiTFViCb@turntable.proxy.rlwy.net:30126/railway"

# Gorgias API configuration
GORGIAS_DOMAIN = "lindas"
GORGIAS_USERNAME = "lindas.quimbiai@proton.me"
GORGIAS_API_KEY = "14324b3a387404726a2dc1e2332fcc2a59fb0a79c9aecdca694028087864d735"


async def fetch_gorgias_tickets(limit=10):
    """Fetch tickets from Gorgias API."""
    url = f"https://{GORGIAS_DOMAIN}.gorgias.com/api/tickets?limit={limit}&order_by=created_datetime:desc"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, auth=(GORGIAS_USERNAME, GORGIAS_API_KEY))
            response.raise_for_status()
            data = response.json()
            return data.get('data', [])
        except Exception as e:
            print(f"Error fetching tickets: {e}")
            return []


async def fetch_gorgias_customer(customer_id):
    """Fetch full customer data from Gorgias API including integration data."""
    url = f"https://{GORGIAS_DOMAIN}.gorgias.com/api/customers/{customer_id}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, auth=(GORGIAS_USERNAME, GORGIAS_API_KEY))
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            print(f"    ⚠ Error fetching customer {customer_id}: {e}")
            return None


def extract_shopify_customer_id(customer_data):
    """Extract Shopify customer ID from Gorgias integration data."""
    if not customer_data:
        return None

    # Check integrations data for Shopify customer ID
    integrations = customer_data.get('integrations', {})

    # Iterate through integration IDs (like 82185 for Shopify)
    for integration_id, integration_data in integrations.items():
        orders = integration_data.get('orders', [])
        if orders:
            # Get customer ID from first order
            first_order = orders[0]
            customer = first_order.get('customer', {})
            shopify_id = customer.get('id')
            if shopify_id:
                return shopify_id

    return None


async def fetch_ticket_messages(ticket_id):
    """Fetch messages for a specific ticket."""
    url = f"https://{GORGIAS_DOMAIN}.gorgias.com/api/tickets/{ticket_id}/messages"

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, auth=(GORGIAS_USERNAME, GORGIAS_API_KEY))
            response.raise_for_status()
            data = response.json()
            return data.get('data', [])
        except Exception as e:
            print(f"  ⚠ Error fetching messages: {e}")
            return []


async def import_ticket_to_database(session, ticket_data, customer_data):
    """Import a single ticket with its messages into the database."""

    # Extract Gorgias customer info
    customer = ticket_data.get('customer', {})
    gorgias_customer_id = customer.get('id')
    customer_email = customer.get('email', 'unknown@email.com')
    customer_name = customer.get('name', 'Unknown Customer')

    # Extract Shopify customer ID from integration data
    shopify_customer_id = extract_shopify_customer_id(customer_data)

    if shopify_customer_id:
        customer_id = str(shopify_customer_id)
        print(f"\n  ✓ Found Shopify ID {customer_id} from Gorgias integration data")
    else:
        customer_id = customer.get('external_id') or str(gorgias_customer_id) or str(uuid.uuid4())
        print(f"\n  ⚠ No Shopify ID found, using Gorgias ID {customer_id}")

    # Extract ticket info
    gorgias_ticket_id = ticket_data.get('id')
    subject = ticket_data.get('subject', 'No Subject')
    status = ticket_data.get('status', 'open')
    channel = ticket_data.get('channel', 'email')
    priority = 'normal'

    # Map Gorgias status
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
    try:
        await session.execute(
            text("""
                INSERT INTO public.customers (id, email, name, lifetime_value, total_orders, churn_risk_score)
                VALUES (:id, :email, :name, 0.0, 0, 0.0)
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": customer_id,
                "email": customer_email,
                "name": customer_name
            }
        )
    except Exception as e:
        # Customer might exist with same email but different ID
        await session.rollback()
        await session.begin()

        # Look up existing customer by email
        result = await session.execute(
            text("SELECT id FROM public.customers WHERE email = :email"),
            {"email": customer_email}
        )
        existing_customer = result.fetchone()

        if existing_customer:
            old_id = existing_customer[0]

            # If we have a Shopify ID and it's different from the existing ID, update the record
            if customer_id != old_id and customer_id != str(old_id):
                print(f"    ⚠ Customer with email {customer_email} exists with ID {old_id}")
                print(f"    ✓ Updating to use Shopify ID: {customer_id}")

                # Update the customer ID to use the Shopify ID
                await session.execute(
                    text("UPDATE public.customers SET id = :new_id, name = :name WHERE id = :old_id"),
                    {"new_id": customer_id, "old_id": old_id, "name": customer_name}
                )

                # Update any existing tickets to use the new customer ID
                await session.execute(
                    text("UPDATE public.tickets SET customer_id = :new_id WHERE customer_id = :old_id"),
                    {"new_id": customer_id, "old_id": old_id}
                )
            else:
                customer_id = old_id
                print(f"    ✓ Using existing customer ID: {customer_id}")

    # Parse datetimes
    created_dt = datetime.fromisoformat(ticket_data.get('created_datetime', datetime.now().isoformat()).replace('Z', '+00:00'))
    updated_dt = datetime.fromisoformat(ticket_data.get('updated_datetime', datetime.now().isoformat()).replace('Z', '+00:00'))

    # Create ticket
    ticket_id = f"gorgias_{gorgias_ticket_id}"
    await session.execute(
        text("""
            INSERT INTO public.tickets (id, customer_id, subject, status, priority, channel, created_at, updated_at)
            VALUES (:id, :customer_id, :subject, :status, :priority, :channel, :created_at, :updated_at)
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at
        """),
        {
            "id": ticket_id,
            "customer_id": customer_id,
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

    for msg in messages:
        msg_id = f"gorgias_msg_{msg.get('id')}"
        msg_created = datetime.fromisoformat(msg.get('created_datetime', datetime.now().isoformat()).replace('Z', '+00:00'))

        # Extract from_email safely
        from_email = None
        if msg.get('from'):
            from_field = msg.get('from')
            if isinstance(from_field, dict):
                from_email = from_field.get('address')

        # Determine if from agent
        from_agent = msg.get('source', {}).get('type') != 'customer'

        await session.execute(
            text("""
                INSERT INTO public.messages (id, ticket_id, content, from_agent, from_email, created_at)
                VALUES (:id, :ticket_id, :content, :from_agent, :from_email, :created_at)
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": msg_id,
                "ticket_id": ticket_id,
                "content": msg.get('body_text', '') or msg.get('body_html', ''),
                "from_agent": from_agent,
                "from_email": from_email,
                "created_at": msg_created.replace(tzinfo=None)
            }
        )

    print(f"    ✓ Imported successfully")


async def main():
    print("=" * 80)
    print("IMPORTING GORGIAS TICKETS WITH SHOPIFY CUSTOMER IDS")
    print("=" * 80)

    print("Fetching 10 tickets from Gorgias...")
    tickets = await fetch_gorgias_tickets(limit=10)
    print(f"✓ Fetched {len(tickets)} tickets from Gorgias\n")

    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        for ticket in tickets:
            # Fetch full customer data
            customer = ticket.get('customer', {})
            customer_id = customer.get('id')

            customer_data = None
            if customer_id:
                customer_data = await fetch_gorgias_customer(customer_id)

            await import_ticket_to_database(session, ticket, customer_data)

            # Commit after each ticket to avoid losing data on errors
            await session.commit()

        print(f"\n✓ All {len(tickets)} tickets committed to database")

    print("\n" + "=" * 80)
    print(f"IMPORT COMPLETE: {len(tickets)}/{len(tickets)} tickets imported successfully")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
