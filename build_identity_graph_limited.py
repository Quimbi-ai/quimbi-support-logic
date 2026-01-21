"""
Identity Graph Builder for Quimbi (FULL VERSION)

This builds the identity graph with ALL Shopify customers using optimized batch processing.
"""

import asyncio
import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import json

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:XzLuopeMhZwurhlOWaObisBJxiTFViCb@turntable.proxy.rlwy.net:30126/railway"
)

LIMIT_SHOPIFY_CUSTOMERS = None  # None = process ALL customers


async def generate_quimbi_id():
    """Generate a unique QuimbiID using 32-digit hexadecimal"""
    import secrets
    # Generate 16 random bytes = 32 hex characters
    hex_id = secrets.token_hex(16)
    return f"QID_{hex_id}"


async def build_identity_graph_batch(session):
    """Build the entire identity graph in optimized batches"""
    print("\n" + "="*80)
    print("BUILDING IDENTITY GRAPH (Batch Mode)")
    print("="*80)

    # STEP 1: Get distinct Shopify customers
    if LIMIT_SHOPIFY_CUSTOMERS:
        print(f"\nFetching first {LIMIT_SHOPIFY_CUSTOMERS:,} Shopify customers from combined_sales...")
        limit_clause = f"LIMIT {LIMIT_SHOPIFY_CUSTOMERS}"
    else:
        print(f"\nFetching ALL Shopify customers from combined_sales...")
        limit_clause = ""

    result = await session.execute(text(f"""
        SELECT DISTINCT customer_id
        FROM public.combined_sales
        WHERE customer_id IS NOT NULL
        ORDER BY customer_id
        {limit_clause}
    """))
    shopify_customers = [str(row[0]) for row in result.fetchall()]
    print(f"✓ Found {len(shopify_customers):,} Shopify customers")

    # STEP 2: Get all Gorgias customers with emails
    print(f"\nFetching customers from public.customers...")
    result = await session.execute(text("""
        SELECT id, email, name
        FROM public.customers
        WHERE email IS NOT NULL
        ORDER BY id
    """))
    gorgias_customers = result.fetchall()
    print(f"✓ Found {len(gorgias_customers)} Gorgias customers")

    # STEP 3: Build email index from combined_sales
    print(f"\nBuilding email index from sales data...")
    # Note: combined_sales doesn't have email, we'll get it from customer_profiles if available
    # For now, we'll just create identities for Shopify IDs

    # Create identities and links in batches
    print(f"\nCreating QuimbiIDs and identity links...")

    identities_created = 0
    links_created = 0

    # Batch insert QuimbiIDs for Shopify customers
    batch_size = 100
    for i in range(0, len(shopify_customers), batch_size):
        batch = shopify_customers[i:i+batch_size]

        # Prepare batch data
        values = []
        for shopify_id in batch:
            quimbi_id = await generate_quimbi_id()
            temp_email = f"shopify_{shopify_id}@temp.quimbi.com"
            values.append(f"('{quimbi_id}', '{temp_email}', NULL)")

        # Batch insert QuimbiIDs
        values_str = ", ".join(values)
        await session.execute(text(f"""
            INSERT INTO public.quimbi_identities (quimbi_id, primary_email, primary_name)
            VALUES {values_str}
        """))

        identities_created += len(batch)

        # Now insert the identity graph links
        # First, get the QuimbiIDs we just created
        emails_list = [f"shopify_{sid}@temp.quimbi.com" for sid in batch]
        emails_str = "', '".join(emails_list)

        result = await session.execute(text(f"""
            SELECT quimbi_id, primary_email FROM public.quimbi_identities
            WHERE primary_email IN ('{emails_str}')
        """))
        quimbi_map = {row[1]: row[0] for row in result.fetchall()}

        # Insert identity graph links
        link_values = []
        for idx, shopify_id in enumerate(batch):
            temp_email = f"shopify_{shopify_id}@temp.quimbi.com"
            quimbi_id = quimbi_map.get(temp_email)
            if quimbi_id:
                link_values.append(f"('{quimbi_id}', 'shopify', '{shopify_id}', 'combined_sales', 1.0, TRUE)")

        if link_values:
            link_values_str = ", ".join(link_values)
            await session.execute(text(f"""
                INSERT INTO public.identity_graph (quimbi_id, id_type, id_value, source, confidence_score, verified)
                VALUES {link_values_str}
                ON CONFLICT (id_type, id_value) DO NOTHING
            """))
            links_created += len(link_values)

        await session.commit()

        if (i + batch_size) % 500 == 0:
            print(f"  Processed {min(i + batch_size, len(shopify_customers)):,}/{len(shopify_customers):,} Shopify customers...")

    print(f"\n✓ Created {identities_created:,} QuimbiIDs for Shopify customers")
    print(f"✓ Created {links_created:,} Shopify identity links")

    # STEP 4: Link Gorgias customers
    print(f"\nLinking {len(gorgias_customers)} Gorgias customers...")

    gorgias_linked = 0
    gorgias_new = 0

    for customer in gorgias_customers:
        customer_id = str(customer[0])
        email = customer[1]
        name = customer[2]

        # Check if this customer_id is already linked as a Shopify ID
        result = await session.execute(
            text("SELECT quimbi_id FROM public.identity_graph WHERE id_type = 'shopify' AND id_value = :id"),
            {"id": customer_id}
        )
        existing_shopify = result.fetchone()

        if existing_shopify:
            # This is a Shopify ID - update email and add email link
            quimbi_id = existing_shopify[0]

            await session.execute(
                text("UPDATE public.quimbi_identities SET primary_email = :email, primary_name = :name WHERE quimbi_id = :qid"),
                {"qid": quimbi_id, "email": email, "name": name}
            )

            # Add email link
            await session.execute(
                text("""
                    INSERT INTO public.identity_graph (quimbi_id, id_type, id_value, source, confidence_score, verified)
                    VALUES (:qid, 'email', :email, 'public.customers', 1.0, TRUE)
                    ON CONFLICT (id_type, id_value) DO NOTHING
                """),
                {"qid": quimbi_id, "email": email}
            )

            gorgias_linked += 1
        else:
            # Check if email already exists
            result = await session.execute(
                text("SELECT quimbi_id FROM public.identity_graph WHERE id_type = 'email' AND id_value = :email"),
                {"email": email}
            )
            existing_email = result.fetchone()

            if existing_email:
                quimbi_id = existing_email[0]
            else:
                # Create new QuimbiID
                quimbi_id = await generate_quimbi_id()
                await session.execute(
                    text("INSERT INTO public.quimbi_identities (quimbi_id, primary_email, primary_name) VALUES (:qid, :email, :name)"),
                    {"qid": quimbi_id, "email": email, "name": name}
                )
                gorgias_new += 1

            # Link Gorgias ID
            await session.execute(
                text("""
                    INSERT INTO public.identity_graph (quimbi_id, id_type, id_value, source, confidence_score, verified)
                    VALUES (:qid, 'gorgias', :gid, 'public.customers', 1.0, TRUE)
                    ON CONFLICT (id_type, id_value) DO NOTHING
                """),
                {"qid": quimbi_id, "gid": customer_id}
            )

            # Link email
            await session.execute(
                text("""
                    INSERT INTO public.identity_graph (quimbi_id, id_type, id_value, source, confidence_score, verified)
                    VALUES (:qid, 'email', :email, 'public.customers', 1.0, TRUE)
                    ON CONFLICT (id_type, id_value) DO NOTHING
                """),
                {"qid": quimbi_id, "email": email}
            )

            gorgias_linked += 1

    await session.commit()
    print(f"✓ Linked {gorgias_linked} Gorgias customers ({gorgias_new} new identities)")


async def generate_statistics(session):
    """Generate statistics about the identity graph"""
    print("\n" + "="*80)
    print("IDENTITY GRAPH STATISTICS")
    print("="*80)

    # Total QuimbiIDs
    result = await session.execute(text("SELECT COUNT(*) FROM public.quimbi_identities WHERE is_active = TRUE"))
    total_identities = result.scalar()
    print(f"\nTotal active QuimbiIDs: {total_identities:,}")

    # Total identity links
    result = await session.execute(text("SELECT COUNT(*) FROM public.identity_graph"))
    total_links = result.scalar()
    print(f"Total identity links: {total_links:,}")

    # Breakdown by ID type
    result = await session.execute(text("""
        SELECT id_type, COUNT(*) as count
        FROM public.identity_graph
        GROUP BY id_type
        ORDER BY count DESC
    """))
    print(f"\nBreakdown by ID type:")
    for row in result.fetchall():
        print(f"  {row[0]:<20} {row[1]:>10,}")

    # Identities with multiple ID types
    result = await session.execute(text("""
        SELECT quimbi_id, COUNT(DISTINCT id_type) as type_count, array_agg(DISTINCT id_type) as types
        FROM public.identity_graph
        GROUP BY quimbi_id
        HAVING COUNT(DISTINCT id_type) > 1
        ORDER BY type_count DESC
        LIMIT 10
    """))
    multi_id_samples = result.fetchall()

    print(f"\nSample QuimbiIDs with multiple ID types:")
    print("-" * 80)
    for row in multi_id_samples:
        quimbi_id, type_count, types = row
        print(f"  {quimbi_id}: {type_count} types - {', '.join(types)}")

        # Get details
        result2 = await session.execute(text("""
            SELECT id_type, id_value
            FROM public.identity_graph
            WHERE quimbi_id = :qid
        """), {"qid": quimbi_id})
        print(f"    Identities:")
        for id_row in result2.fetchall():
            print(f"      - {id_row[0]}: {id_row[1]}")


async def main():
    print("="*80)
    print("QUIMBI IDENTITY GRAPH BUILDER - FULL BUILD")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if LIMIT_SHOPIFY_CUSTOMERS:
        print(f"Processing first {LIMIT_SHOPIFY_CUSTOMERS:,} Shopify customers")
    else:
        print(f"Processing ALL Shopify customers")

    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Build identity graph
        await build_identity_graph_batch(session)

        # Generate statistics
        await generate_statistics(session)

    print("\n" + "="*80)
    print("IDENTITY GRAPH BUILD COMPLETE")
    print("="*80)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    asyncio.run(main())
