"""
Identity Graph Query Tool

Provides easy lookups and queries for the identity graph.
"""

import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import json

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:XzLuopeMhZwurhlOWaObisBJxiTFViCb@turntable.proxy.rlwy.net:30126/railway"
)


async def find_customer_by_any_id(session, identifier):
    """Find a customer by any identifier (email, Shopify ID, Gorgias ID, QuimbiID)"""
    print(f"\nSearching for: {identifier}")
    print("=" * 80)

    # First, try to find in identity_graph
    result = await session.execute(
        text("""
            SELECT quimbi_id, id_type, id_value
            FROM public.identity_graph
            WHERE id_value = :identifier OR quimbi_id = :identifier
        """),
        {"identifier": identifier}
    )
    matches = result.fetchall()

    if not matches:
        print("❌ No matches found")
        return None

    # Get the QuimbiID
    quimbi_id = matches[0][0]

    # Get full identity information
    result = await session.execute(
        text("""
            SELECT qi.quimbi_id, qi.primary_email, qi.primary_name, qi.created_at
            FROM public.quimbi_identities qi
            WHERE qi.quimbi_id = :qid AND qi.is_active = TRUE
        """),
        {"qid": quimbi_id}
    )
    identity = result.fetchone()

    if not identity:
        print("❌ QuimbiID found but identity is inactive or missing")
        return None

    # Get all linked identifiers
    result = await session.execute(
        text("""
            SELECT id_type, id_value, source, confidence_score, verified, created_at
            FROM public.identity_graph
            WHERE quimbi_id = :qid
            ORDER BY id_type, created_at
        """),
        {"qid": quimbi_id}
    )
    identifiers = result.fetchall()

    # Print results
    print(f"\n✓ Found Customer Identity")
    print("-" * 80)
    print(f"QuimbiID:      {identity[0]}")
    print(f"Email:         {identity[1] if identity[1] else '(none)'}")
    print(f"Name:          {identity[2] if identity[2] else '(none)'}")
    print(f"Created:       {identity[3]}")

    print(f"\nLinked Identifiers ({len(identifiers)}):")
    print("-" * 80)
    for id_info in identifiers:
        id_type, id_value, source, confidence, verified, created = id_info
        verified_mark = "✓" if verified else "?"
        print(f"  [{verified_mark}] {id_type:<12} {id_value:<30} (from: {source}, confidence: {confidence})")

    # Check if customer has purchase history
    shopify_ids = [str(i[1]) for i in identifiers if i[0] == 'shopify']
    if shopify_ids:
        # Build the IN clause manually since asyncpg doesn't support tuple binding well
        ids_str = ','.join(shopify_ids)
        result = await session.execute(
            text(f"""
                SELECT COUNT(*) as order_count, SUM(line_item_sales) as total_sales
                FROM public.combined_sales
                WHERE customer_id IN ({ids_str})
            """)
        )
        sales = result.fetchone()
        if sales and sales[0] > 0:
            print(f"\n📊 Purchase History:")
            print(f"   Orders: {sales[0]}")
            print(f"   Total Sales: ${sales[1]:,.2f}" if sales[1] else "   Total Sales: $0.00")

    # Check if customer has tickets
    result = await session.execute(
        text("""
            SELECT COUNT(*) FROM public.tickets t
            WHERE t.customer_id = ANY(:ids)
        """),
        {"ids": [str(i[1]) for i in identifiers]}
    )
    ticket_count = result.scalar()
    if ticket_count > 0:
        print(f"\n🎫 Support Tickets: {ticket_count}")

    return quimbi_id


async def stats_summary(session):
    """Show overall identity graph statistics"""
    print("\n" + "=" * 80)
    print("IDENTITY GRAPH SUMMARY")
    print("=" * 80)

    # Total identities
    result = await session.execute(text("SELECT COUNT(*) FROM public.quimbi_identities WHERE is_active = TRUE"))
    total = result.scalar()
    print(f"\nTotal Active Customers: {total:,}")

    # By type
    result = await session.execute(text("""
        SELECT id_type, COUNT(*) as count
        FROM public.identity_graph
        GROUP BY id_type
        ORDER BY count DESC
    """))
    print(f"\nIdentifiers by Type:")
    for row in result.fetchall():
        print(f"  {row[0]:<15} {row[1]:>10,}")

    # Multi-system customers
    result = await session.execute(text("""
        SELECT COUNT(*) FROM (
            SELECT quimbi_id
            FROM public.identity_graph
            GROUP BY quimbi_id
            HAVING COUNT(DISTINCT id_type) > 1
        ) t
    """))
    multi = result.scalar()
    print(f"\nCustomers with Multiple ID Types: {multi:,}")

    # Shopify + Gorgias linkages
    result = await session.execute(text("""
        SELECT COUNT(DISTINCT ig1.quimbi_id)
        FROM public.identity_graph ig1
        INNER JOIN public.identity_graph ig2 ON ig1.quimbi_id = ig2.quimbi_id
        WHERE ig1.id_type = 'shopify' AND ig2.id_type = 'gorgias'
    """))
    both = result.scalar()
    print(f"Customers with BOTH Shopify + Gorgias IDs: {both:,}")


async def find_linked_customers(session):
    """Show customers that have both Shopify and Gorgias IDs"""
    print("\n" + "=" * 80)
    print("CUSTOMERS WITH BOTH SHOPIFY AND GORGIAS IDs")
    print("=" * 80)

    result = await session.execute(text("""
        SELECT
            qi.quimbi_id,
            qi.primary_email,
            qi.primary_name,
            ig_shopify.id_value as shopify_id,
            ig_gorgias.id_value as gorgias_id
        FROM public.quimbi_identities qi
        INNER JOIN public.identity_graph ig_shopify ON qi.quimbi_id = ig_shopify.quimbi_id AND ig_shopify.id_type = 'shopify'
        INNER JOIN public.identity_graph ig_gorgias ON qi.quimbi_id = ig_gorgias.quimbi_id AND ig_gorgias.id_type = 'gorgias'
        WHERE qi.is_active = TRUE
        ORDER BY qi.created_at DESC
    """))

    customers = result.fetchall()
    print(f"\nFound {len(customers)} customers with both IDs:\n")

    for cust in customers:
        quimbi_id, email, name, shopify_id, gorgias_id = cust
        print(f"  QuimbiID: {quimbi_id}")
        print(f"    Email: {email}")
        print(f"    Name: {name if name else '(none)'}")
        print(f"    Shopify ID: {shopify_id}")
        print(f"    Gorgias ID: {gorgias_id}")
        print()


async def main():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # If argument provided, search for that identifier
        if len(sys.argv) > 1:
            identifier = sys.argv[1]
            await find_customer_by_any_id(session, identifier)
        else:
            # Show summary stats
            await stats_summary(session)
            await find_linked_customers(session)

            print("\n" + "=" * 80)
            print("USAGE:")
            print("  python3 query_identity_graph.py                # Show summary")
            print("  python3 query_identity_graph.py <identifier>   # Find customer by any ID")
            print("\nExamples:")
            print("  python3 query_identity_graph.py debbymiller@centurylink.net")
            print("  python3 query_identity_graph.py 4595328254127")
            print("  python3 query_identity_graph.py QID_1768865976_239396")
            print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
