#!/usr/bin/env python3
"""
Add mock tracking data to combined_sales table for demo purposes.

This adds tracking columns to the combined_sales table and populates
tracking information for recent orders.
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/railway")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def add_tracking_columns():
    """Add tracking columns to combined_sales table if they don't exist."""
    async with AsyncSessionLocal() as db:
        # Check if columns exist
        result = await db.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'combined_sales'
                AND column_name IN ('tracking_number', 'tracking_url', 'shipping_carrier')
            """)
        )
        existing_cols = {row[0] for row in result.fetchall()}

        if 'tracking_number' not in existing_cols:
            print("Adding tracking_number column...")
            await db.execute(
                text("ALTER TABLE public.combined_sales ADD COLUMN tracking_number VARCHAR(255)")
            )
            await db.commit()
            print("✅ Added tracking_number column")

        if 'tracking_url' not in existing_cols:
            print("Adding tracking_url column...")
            await db.execute(
                text("ALTER TABLE public.combined_sales ADD COLUMN tracking_url TEXT")
            )
            await db.commit()
            print("✅ Added tracking_url column")

        if 'shipping_carrier' not in existing_cols:
            print("Adding shipping_carrier column...")
            await db.execute(
                text("ALTER TABLE public.combined_sales ADD COLUMN shipping_carrier VARCHAR(100)")
            )
            await db.commit()
            print("✅ Added shipping_carrier column")


async def add_mock_tracking():
    """Add mock tracking data to recent orders."""
    async with AsyncSessionLocal() as db:
        # Add tracking to order 204712 (Debby's recent order from Oct 28)
        await db.execute(
            text("""
                UPDATE public.combined_sales
                SET
                    tracking_number = 'TK789456123',
                    tracking_url = 'https://tools.usps.com/go/TrackConfirmAction?tLabels=TK789456123',
                    shipping_carrier = 'USPS'
                WHERE order_number = 204712
            """)
        )

        # Add tracking to a few more recent orders for demo
        await db.execute(
            text("""
                UPDATE public.combined_sales
                SET
                    tracking_number = 'UPS123456789012',
                    tracking_url = 'https://www.ups.com/track?loc=en_US&tracknum=UPS123456789012',
                    shipping_carrier = 'UPS'
                WHERE order_number = 198481
            """)
        )

        await db.commit()
        print("✅ Added mock tracking data to orders 204712 and 198481")


async def verify_tracking():
    """Verify tracking data was added correctly."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("""
                SELECT
                    order_number,
                    tracking_number,
                    shipping_carrier,
                    product_name
                FROM public.combined_sales
                WHERE order_number IN (204712, 198481)
                LIMIT 5
            """)
        )

        print("\nVerification - Orders with tracking:")
        print("-" * 80)
        for row in result.fetchall():
            print(f"Order #{row[0]}: {row[1]} ({row[2]}) - {row[3][:50]}")


async def main():
    """Main execution."""
    print("=" * 80)
    print("Adding Mock Tracking Data to combined_sales")
    print("=" * 80)
    print()

    # Step 1: Add columns if needed
    await add_tracking_columns()
    print()

    # Step 2: Add mock tracking data
    print("Adding mock tracking data...")
    await add_mock_tracking()
    print()

    # Step 3: Verify
    await verify_tracking()
    print()

    print("=" * 80)
    print("✅ Mock tracking data added successfully!")
    print("=" * 80)
    print()
    print("The Last Purchase box should now display tracking information")
    print("for orders 204712 and 198481")


if __name__ == "__main__":
    asyncio.run(main())
