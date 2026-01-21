#!/usr/bin/env python3
"""
Populate PII Hashes in Identity Graph

This script adds privacy-preserving hashed identifiers to the identity graph
for existing Shopify customers. This enables identity resolution across channels
without storing PII in plaintext.

Adds:
- email_hash: Hashed email addresses
- name_hash: Hashed customer names
- address_hash: Hashed physical addresses (if available)

Usage:
    python3 populate_pii_hashes.py [--limit N]
"""

import asyncio
import argparse
import sys
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.pii_hash import hash_email, hash_name, hash_address


# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/railway")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def populate_pii_hashes(limit: int = None):
    """
    Populate identity_graph with hashed PII identifiers.

    For each Shopify customer:
    1. Hash their email address
    2. Hash their name
    3. Add hashes to identity_graph linked to their QuimbiID

    Args:
        limit: Maximum number of customers to process (None = all)
    """
    async with AsyncSessionLocal() as db:
        # Get all customers with QuimbiIDs from quimbi_identities table
        query = """
            SELECT DISTINCT
                qi.quimbi_id,
                qi.primary_email as email,
                qi.primary_name as name
            FROM public.quimbi_identities qi
            WHERE qi.is_active = TRUE
                AND qi.primary_email IS NOT NULL
                AND qi.primary_name IS NOT NULL
                AND qi.primary_email NOT LIKE '%@temp.quimbi.com'
        """

        if limit:
            query += f" LIMIT {limit}"

        result = await db.execute(text(query))
        customers = result.fetchall()

        print(f"Found {len(customers)} customers to process")

        added_count = 0
        skipped_count = 0

        for customer in customers:
            quimbi_id, email, name = customer

            try:
                # Hash PII
                email_h = hash_email(email)
                name_h = hash_name(name)

                # Check if email_hash already exists
                check_email = await db.execute(
                    text("SELECT 1 FROM public.identity_graph WHERE id_type = 'email_hash' AND id_value = :hash LIMIT 1"),
                    {"hash": email_h}
                )
                email_exists = check_email.fetchone() is not None

                # Check if name_hash already exists
                check_name = await db.execute(
                    text("SELECT 1 FROM public.identity_graph WHERE id_type = 'name_hash' AND id_value = :hash LIMIT 1"),
                    {"hash": name_h}
                )
                name_exists = check_name.fetchone() is not None

                # Insert email_hash if not exists
                if not email_exists:
                    await db.execute(
                        text("""
                            INSERT INTO public.identity_graph
                                (quimbi_id, id_type, id_value, source, confidence_score, verified)
                            VALUES
                                (:quimbi_id, 'email_hash', :hash, 'shopify_customer', 1.0, true)
                        """),
                        {"quimbi_id": quimbi_id, "hash": email_h}
                    )
                    added_count += 1
                else:
                    skipped_count += 1

                # Insert name_hash if not exists
                if not name_exists:
                    await db.execute(
                        text("""
                            INSERT INTO public.identity_graph
                                (quimbi_id, id_type, id_value, source, confidence_score, verified)
                            VALUES
                                (:quimbi_id, 'name_hash', :hash, 'shopify_customer', 0.9, true)
                        """),
                        {"quimbi_id": quimbi_id, "hash": name_h}
                    )
                    added_count += 1
                else:
                    skipped_count += 1

                # Commit every 100 customers
                if (added_count + skipped_count) % 100 == 0:
                    await db.commit()
                    print(f"Processed {added_count + skipped_count} customers... (added: {added_count}, skipped: {skipped_count})")

            except Exception as e:
                print(f"Error processing customer {quimbi_id}: {e}")
                continue

        # Final commit
        await db.commit()

        print(f"\n✅ Complete!")
        print(f"   Total customers processed: {len(customers)}")
        print(f"   Hashes added: {added_count}")
        print(f"   Hashes skipped (already exist): {skipped_count}")

        # Show sample of what was added
        sample = await db.execute(
            text("""
                SELECT id_type, COUNT(*)
                FROM public.identity_graph
                WHERE id_type IN ('email_hash', 'name_hash', 'address_hash')
                GROUP BY id_type
            """)
        )
        print(f"\n📊 Identity Graph PII Hash Summary:")
        for row in sample.fetchall():
            print(f"   {row[0]}: {row[1]:,} entries")


async def main():
    parser = argparse.ArgumentParser(description="Populate PII hashes in identity graph")
    parser.add_argument("--limit", type=int, help="Limit number of customers to process (for testing)")
    args = parser.parse_args()

    print("🔐 Populating PII hashes in identity graph...")
    print(f"   Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'localhost'}")

    if args.limit:
        print(f"   Limit: {args.limit} customers (test mode)")

    print()

    await populate_pii_hashes(limit=args.limit)


if __name__ == "__main__":
    asyncio.run(main())
