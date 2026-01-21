"""
Identity Graph Builder for Quimbi

This script builds the identity graph by:
1. Creating QuimbiIDs for all unique customers
2. Linking Shopify customer IDs from combined_sales
3. Linking Gorgias customer IDs from public.customers
4. Linking emails as identifiers
5. Resolving conflicts and merging identities based on email matching
"""

import asyncio
import os
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from collections import defaultdict

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:XzLuopeMhZwurhlOWaObisBJxiTFViCb@turntable.proxy.rlwy.net:30126/railway"
)


async def generate_quimbi_id(session):
    """Generate a unique QuimbiID"""
    result = await session.execute(text("SELECT generate_quimbi_id()"))
    return result.scalar()


async def create_identity(session, email, name=None):
    """Create a new QuimbiID identity"""
    quimbi_id = await generate_quimbi_id(session)

    await session.execute(
        text("""
            INSERT INTO public.quimbi_identities (quimbi_id, primary_email, primary_name)
            VALUES (:quimbi_id, :email, :name)
        """),
        {"quimbi_id": quimbi_id, "email": email, "name": name}
    )

    # Log the creation (skip for performance during bulk import)
    # await session.execute(
    #     text("""
    #         INSERT INTO public.identity_resolution_log (quimbi_id, resolution_type, details, performed_by)
    #         VALUES (:quimbi_id, 'new', :details::jsonb, 'build_identity_graph')
    #     """),
    #     {
    #         "quimbi_id": quimbi_id,
    #         "details": json.dumps({"email": email, "name": name})
    #     }
    # )

    return quimbi_id


async def link_identity(session, quimbi_id, id_type, id_value, source, confidence=1.0):
    """Link an identifier to a QuimbiID"""
    if not id_value or id_value == 'None':
        return

    await session.execute(
        text("""
            INSERT INTO public.identity_graph (quimbi_id, id_type, id_value, source, confidence_score, verified)
            VALUES (:quimbi_id, :id_type, :id_value, :source, :confidence, TRUE)
            ON CONFLICT (id_type, id_value) DO UPDATE
            SET quimbi_id = EXCLUDED.quimbi_id,
                confidence_score = GREATEST(identity_graph.confidence_score, EXCLUDED.confidence_score),
                updated_at = NOW()
        """),
        {
            "quimbi_id": quimbi_id,
            "id_type": id_type,
            "id_value": str(id_value),
            "source": source,
            "confidence": confidence
        }
    )


async def build_from_combined_sales(session):
    """Build identities from Shopify combined_sales data"""
    print("\n" + "="*80)
    print("STEP 1: Building identities from combined_sales (Shopify)")
    print("="*80)

    # Get all unique Shopify customer IDs from combined_sales
    # We'll create one QuimbiID per Shopify customer
    result = await session.execute(text("""
        SELECT DISTINCT customer_id
        FROM public.combined_sales
        WHERE customer_id IS NOT NULL
        ORDER BY customer_id
    """))
    shopify_customers = result.fetchall()

    print(f"\nFound {len(shopify_customers):,} unique Shopify customers in combined_sales")

    created_count = 0
    for idx, row in enumerate(shopify_customers, 1):
        shopify_id = str(row[0])

        # Create a QuimbiID for this Shopify customer
        # Use a temporary email format for now (we'll update it later if we find the real email)
        temp_email = f"shopify_{shopify_id}@temp.quimbi.com"
        quimbi_id = await create_identity(session, temp_email, name=None)

        # Link the Shopify ID
        await link_identity(session, quimbi_id, "shopify", shopify_id, "combined_sales", confidence=1.0)

        created_count += 1

        if idx % 1000 == 0:
            await session.commit()
            print(f"  Processed {idx:,}/{len(shopify_customers):,} Shopify customers...")

    await session.commit()
    print(f"\n✓ Created {created_count:,} identities from Shopify data")


async def link_gorgias_customers(session):
    """Link Gorgias customer IDs to existing QuimbiIDs"""
    print("\n" + "="*80)
    print("STEP 2: Linking Gorgias customer IDs")
    print("="*80)

    # Get all customers from public.customers
    result = await session.execute(text("""
        SELECT id, email, name
        FROM public.customers
        ORDER BY id
    """))
    customers = result.fetchall()

    print(f"\nFound {len(customers)} customers in public.customers")

    linked_count = 0
    new_count = 0

    for customer in customers:
        customer_id = str(customer[0])
        email = customer[1]
        name = customer[2]

        # Check if this is a Shopify ID (already in identity graph)
        result = await session.execute(
            text("SELECT quimbi_id FROM public.identity_graph WHERE id_type = 'shopify' AND id_value = :id"),
            {"id": customer_id}
        )
        existing = result.fetchone()

        if existing:
            # This is a Shopify ID - link email and name
            quimbi_id = existing[0]

            # Update the primary email/name if we have better data
            if email and email != f"shopify_{customer_id}@temp.quimbi.com":
                await session.execute(
                    text("UPDATE public.quimbi_identities SET primary_email = :email, primary_name = :name WHERE quimbi_id = :quimbi_id"),
                    {"quimbi_id": quimbi_id, "email": email, "name": name}
                )

            # Link email
            if email:
                await link_identity(session, quimbi_id, "email", email, "public.customers", confidence=1.0)

            linked_count += 1
        else:
            # This is a Gorgias ID - check if we can match by email
            quimbi_id = None

            if email:
                # Try to find existing QuimbiID by email
                result = await session.execute(
                    text("SELECT quimbi_id FROM public.identity_graph WHERE id_type = 'email' AND id_value = :email"),
                    {"email": email}
                )
                match = result.fetchone()
                if match:
                    quimbi_id = match[0]

            if not quimbi_id:
                # Create new identity
                quimbi_id = await create_identity(session, email, name)
                new_count += 1

            # Link the Gorgias ID
            await link_identity(session, quimbi_id, "gorgias", customer_id, "public.customers", confidence=1.0)

            # Link email
            if email:
                await link_identity(session, quimbi_id, "email", email, "public.customers", confidence=1.0)

            linked_count += 1

    await session.commit()
    print(f"\n✓ Linked {linked_count} Gorgias customers ({new_count} new identities)")


async def resolve_email_conflicts(session):
    """Find and merge identities that share the same email"""
    print("\n" + "="*80)
    print("STEP 3: Resolving email conflicts and merging identities")
    print("="*80)

    # Find emails that are linked to multiple QuimbiIDs
    result = await session.execute(text("""
        SELECT id_value, array_agg(DISTINCT quimbi_id) as quimbi_ids
        FROM public.identity_graph
        WHERE id_type = 'email'
        GROUP BY id_value
        HAVING COUNT(DISTINCT quimbi_id) > 1
    """))
    conflicts = result.fetchall()

    print(f"\nFound {len(conflicts)} emails with multiple QuimbiIDs")

    merged_count = 0
    for email, quimbi_ids in conflicts:
        # Keep the first QuimbiID, merge others into it
        primary_qid = quimbi_ids[0]
        merge_qids = quimbi_ids[1:]

        print(f"\n  Merging {len(merge_qids)} identities into {primary_qid} for email {email}")

        for merge_qid in merge_qids:
            # Move all identity links to the primary QuimbiID
            await session.execute(
                text("""
                    UPDATE public.identity_graph
                    SET quimbi_id = :primary_qid
                    WHERE quimbi_id = :merge_qid
                    ON CONFLICT (id_type, id_value) DO NOTHING
                """),
                {"primary_qid": primary_qid, "merge_qid": merge_qid}
            )

            # Mark the merged identity as inactive
            await session.execute(
                text("""
                    UPDATE public.quimbi_identities
                    SET is_active = FALSE, merged_from = :merge_qid
                    WHERE quimbi_id = :merge_qid
                """),
                {"merge_qid": merge_qid}
            )

            # Log the merge (skip for performance during bulk import)
            # await session.execute(
            #     text("""
            #         INSERT INTO public.identity_resolution_log (quimbi_id, resolution_type, details, performed_by)
            #         VALUES (:primary_qid, 'merge', :details::jsonb, 'build_identity_graph')
            #     """),
            #     {
            #         "primary_qid": primary_qid,
            #         "details": json.dumps({"merged_from": merge_qid, "reason": "email_match", "email": email})
            #     }
            # )

            merged_count += 1

    await session.commit()
    print(f"\n✓ Merged {merged_count} duplicate identities")


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
        SELECT COUNT(DISTINCT quimbi_id)
        FROM (
            SELECT quimbi_id, COUNT(DISTINCT id_type) as type_count
            FROM public.identity_graph
            GROUP BY quimbi_id
            HAVING COUNT(DISTINCT id_type) > 1
        ) t
    """))
    multi_id = result.scalar()
    print(f"\nQuimbiIDs with multiple ID types: {multi_id:,}")

    # Sample identities with complete linkages
    result = await session.execute(text("""
        SELECT *
        FROM public.customer_identity_view
        WHERE jsonb_array_length(identities) > 1
        LIMIT 5
    """))
    print(f"\nSample identities with multiple linkages:")
    print("-" * 80)
    for row in result.fetchall():
        print(f"\n  QuimbiID: {row[0]}")
        print(f"  Email: {row[1]}")
        print(f"  Name: {row[2] if row[2] else '(none)'}")
        print(f"  Linked IDs:")
        import json
        identities = json.loads(row[3]) if isinstance(row[3], str) else row[3]
        for identity in identities:
            print(f"    - {identity['id_type']}: {identity['id_value']} (confidence: {identity['confidence']})")


async def main():
    print("="*80)
    print("QUIMBI IDENTITY GRAPH BUILDER")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Build from Shopify data
        await build_from_combined_sales(session)

        # Link Gorgias customers
        await link_gorgias_customers(session)

        # Resolve conflicts
        await resolve_email_conflicts(session)

        # Generate statistics
        await generate_statistics(session)

    print("\n" + "="*80)
    print("IDENTITY GRAPH BUILD COMPLETE")
    print("="*80)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    asyncio.run(main())
