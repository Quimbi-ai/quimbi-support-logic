"""
Create realistic demo support tickets with QuimbiID integration

This creates proper customer support tickets for customers with real purchase history
and tracking information to demonstrate the full QuimbiID system capabilities.
"""

import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:XzLuopeMhZwurhlOWaObisBJxiTFViCb@turntable.proxy.rlwy.net:30126/railway"


async def create_demo_tickets(session):
    """Create realistic demo support tickets"""

    # First, find customers with good purchase history
    result = await session.execute(text("""
        SELECT DISTINCT
            ig.quimbi_id,
            qi.primary_email,
            qi.primary_name,
            ig.id_value as shopify_id,
            cp.lifetime_value
        FROM public.identity_graph ig
        JOIN public.quimbi_identities qi ON ig.quimbi_id = qi.quimbi_id
        JOIN platform.customer_profiles cp ON ig.id_value = cp.customer_id::text
        WHERE ig.id_type = 'shopify'
        AND qi.primary_email IS NOT NULL
        AND qi.primary_email NOT LIKE '%temp.quimbi.com'
        AND cp.total_orders > 50
        AND cp.lifetime_value > 1000
        ORDER BY cp.lifetime_value DESC
        LIMIT 3
    """))

    high_value_customers = result.fetchall()

    if not high_value_customers:
        print("No suitable customers found for demo tickets")
        return

    print(f"Found {len(high_value_customers)} high-value customers for demo tickets\n")

    # Demo Ticket 1: Product quality issue
    customer = high_value_customers[0]
    quimbi_id, email, name, shopify_id, ltv = customer

    ticket_id_1 = "demo_ticket_001"

    # Get a recent order for this customer
    result = await session.execute(text("""
        SELECT DISTINCT order_number, order_date, order_total
        FROM public.combined_sales
        WHERE customer_id = :cid
        ORDER BY order_date DESC
        LIMIT 1
    """), {"cid": int(shopify_id)})

    recent_order = result.fetchone()
    order_num = recent_order[0] if recent_order else "114-XXXXXXX-XXXXXXX"
    order_date = recent_order[1] if recent_order else datetime.now() - timedelta(days=7)

    # Create ticket
    await session.execute(text("""
        INSERT INTO public.tickets (id, customer_id, subject, status, priority, channel, created_at, updated_at)
        VALUES (:id, :cid, :subject, 'open', 'high', 'email', :created, :updated)
        ON CONFLICT (id) DO UPDATE SET
            subject = EXCLUDED.subject,
            updated_at = EXCLUDED.updated_at
    """), {
        "id": ticket_id_1,
        "cid": shopify_id,
        "subject": "Thread color mismatch - need exchange",
        "created": datetime.now() - timedelta(hours=2),
        "updated": datetime.now() - timedelta(hours=2)
    })

    # Create message
    message_content_1 = f"""Hi there,

I ordered some quilting thread last week (Order #{order_num}) and I'm having an issue with one of the items.
The thread color I received doesn't match what was shown on the website - I ordered "Deep Burgundy" but
received what looks more like a bright red.

I've been ordering from you for years and this is the first time I've had an issue. I'd like to exchange
it for the correct color if possible. I still have the original packaging.

Can you help me with this?

Thanks,
{name}"""

    await session.execute(text("""
        INSERT INTO public.messages (id, ticket_id, content, from_agent, from_email, created_at)
        VALUES (:id, :tid, :content, false, :email, :created)
        ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content
    """), {
        "id": f"{ticket_id_1}_msg1",
        "tid": ticket_id_1,
        "content": message_content_1,
        "email": email,
        "created": datetime.now() - timedelta(hours=2)
    })

    print(f"✓ Created Ticket 1: Product Quality Issue")
    print(f"  Customer: {name} ({email})")
    print(f"  QuimbiID: {quimbi_id}")
    print(f"  Shopify ID: {shopify_id}\n")

    # Demo Ticket 2: Where is my order?
    if len(high_value_customers) > 1:
        customer = high_value_customers[1]
        quimbi_id, email, name, shopify_id, ltv = customer

        ticket_id_2 = "demo_ticket_002"

        # Get recent order
        result = await session.execute(text("""
            SELECT DISTINCT order_number, order_date, order_total
            FROM public.combined_sales
            WHERE customer_id = :cid
            ORDER BY order_date DESC
            LIMIT 1
        """), {"cid": int(shopify_id)})

        recent_order = result.fetchone()
        order_num = recent_order[0] if recent_order else "114-XXXXXXX-XXXXXXX"
        order_date = recent_order[1] if recent_order else datetime.now() - timedelta(days=10)

        await session.execute(text("""
            INSERT INTO public.tickets (id, customer_id, subject, status, priority, channel, created_at, updated_at)
            VALUES (:id, :cid, :subject, 'open', 'normal', 'email', :created, :updated)
            ON CONFLICT (id) DO UPDATE SET
                subject = EXCLUDED.subject,
                updated_at = EXCLUDED.updated_at
        """), {
            "id": ticket_id_2,
            "cid": shopify_id,
            "subject": "Order still hasn't arrived - tracking shows delivered?",
            "created": datetime.now() - timedelta(hours=5),
            "updated": datetime.now() - timedelta(hours=5)
        })

        message_content_2 = f"""Hello,

I placed an order about 10 days ago (Order #{order_num}) and according to the tracking information,
it says it was delivered 3 days ago. However, I haven't received anything and there's no package
at my door or mailbox.

I've checked with my neighbors and the leasing office - nobody has seen it. The tracking shows it
was left at the front door, but there's nothing here.

This is really frustrating because I needed these supplies for a project I'm working on. Can you
please look into this and let me know what happened?

Thanks,
{name}"""

        await session.execute(text("""
            INSERT INTO public.messages (id, ticket_id, content, from_agent, from_email, created_at)
            VALUES (:id, :tid, :content, false, :email, :created)
            ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content
        """), {
            "id": f"{ticket_id_2}_msg1",
            "tid": ticket_id_2,
            "content": message_content_2,
            "email": email,
            "created": datetime.now() - timedelta(hours=5)
        })

        print(f"✓ Created Ticket 2: Missing Package")
        print(f"  Customer: {name} ({email})")
        print(f"  QuimbiID: {quimbi_id}")
        print(f"  Shopify ID: {shopify_id}\n")

    # Demo Ticket 3: Product recommendation
    if len(high_value_customers) > 2:
        customer = high_value_customers[2]
        quimbi_id, email, name, shopify_id, ltv = customer

        ticket_id_3 = "demo_ticket_003"

        await session.execute(text("""
            INSERT INTO public.tickets (id, customer_id, subject, status, priority, channel, created_at, updated_at)
            VALUES (:id, :cid, :subject, 'open', 'normal', 'email', :created, :updated)
            ON CONFLICT (id) DO UPDATE SET
                subject = EXCLUDED.subject,
                updated_at = EXCLUDED.updated_at
        """), {
            "id": ticket_id_3,
            "cid": shopify_id,
            "subject": "Looking for batting recommendation for queen size quilt",
            "created": datetime.now() - timedelta(hours=1),
            "updated": datetime.now() - timedelta(hours=1)
        })

        message_content_3 = f"""Hi,

I'm working on a queen-size quilt for my daughter's wedding gift and I'm not sure which batting to use.
I want something that's warm but not too heavy, and it needs to be machine washable.

I've ordered from you many times before and always been happy with your products. I was looking at your
website but there are so many options! Can you recommend what would work best for a queen-size quilt
that will be used regularly?

Also, do you have any tutorials or tips on basting large quilts? This will be my biggest project yet.

Thanks for your help!
{name}"""

        await session.execute(text("""
            INSERT INTO public.messages (id, ticket_id, content, from_agent, from_email, created_at)
            VALUES (:id, :tid, :content, false, :email, :created)
            ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content
        """), {
            "id": f"{ticket_id_3}_msg1",
            "tid": ticket_id_3,
            "content": message_content_3,
            "email": email,
            "created": datetime.now() - timedelta(hours=1)
        })

        print(f"✓ Created Ticket 3: Product Recommendation")
        print(f"  Customer: {name} ({email})")
        print(f"  QuimbiID: {quimbi_id}")
        print(f"  Shopify ID: {shopify_id}\n")

    await session.commit()
    print("=" * 80)
    print("✓ All demo tickets created successfully!")
    print("=" * 80)


async def main():
    """Main function"""
    print("=" * 80)
    print("CREATING DEMO SUPPORT TICKETS")
    print("=" * 80)
    print()

    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        await create_demo_tickets(session)

    print("\nYou can now view these tickets using:")
    print("  python3 demo_ticket_with_quimbi_id.py")


if __name__ == "__main__":
    asyncio.run(main())
