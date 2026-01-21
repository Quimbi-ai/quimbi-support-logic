"""
Sync Shopify customer emails to customer_alias table for Gorgias integration.
This creates the critical email → Shopify customer ID mapping.
"""
import asyncio
import sys
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Database configuration
DATABASE_URL = "postgresql+asyncpg://postgres:XzLuopeMhZwurhlOWaObisBJxiTFViCb@turntable.proxy.rlwy.net:30126/railway"

# Shopify API configuration
SHOPIFY_STORE = "lindas-electric-quilters"  # Store domain
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")  # Load from environment
SHOPIFY_API_VERSION = "2024-10"


async def fetch_shopify_customers(limit=1000):
    """Fetch customers from Shopify API (limited for safety)."""
    customers = []
    url = f"https://{SHOPIFY_STORE}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/customers.json?limit=250"

    # Use X-Shopify-Access-Token header for Admin API
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        while url and len(customers) < limit:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

                batch = data.get('customers', [])
                customers.extend(batch)
                print(f"  Fetched {len(batch)} customers (total: {len(customers)})")

                # Debug: print first customer on first batch
                if len(customers) == len(batch) and batch:
                    first = batch[0]
                    print(f"  Sample customer: ID={first.get('id')}, Email={first.get('email')}, Name={first.get('first_name')} {first.get('last_name')}")

                # Stop if we've hit our safety limit
                if len(customers) >= limit:
                    print(f"  Reached safety limit of {limit} customers")
                    break

                # Check for next page
                link_header = response.headers.get('Link', '')
                if 'rel="next"' in link_header:
                    # Extract next URL from Link header
                    next_link = link_header.split('<')[1].split('>')[0]
                    url = next_link
                else:
                    url = None

            except Exception as e:
                print(f"Error fetching customers: {e}")
                break

    return customers


async def populate_customer_alias(customers):
    """Populate customer_alias table with email → Shopify ID mappings."""
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    added = 0
    skipped = 0

    async with async_session() as session:
        for customer in customers:
            customer_id = str(customer.get('id'))
            email = customer.get('email')
            name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()

            if not email:
                skipped += 1
                continue

            # Check if mapping already exists
            result = await session.execute(
                text("SELECT 1 FROM customer_alias WHERE LOWER(email) = LOWER(:email)"),
                {"email": email}
            )
            exists = result.fetchone()

            if exists:
                skipped += 1
                continue

            # Get LTV and order count for notes
            ltv_result = await session.execute(
                text("""
                    SELECT lifetime_value, total_orders
                    FROM fact_customer_current
                    WHERE customer_id = :id
                """),
                {"id": customer_id}
            )
            ltv_row = ltv_result.fetchone()

            ltv = ltv_row[0] if ltv_row else 0
            orders = ltv_row[1] if ltv_row else 0

            # Insert mapping
            await session.execute(
                text("""
                    INSERT INTO customer_alias (
                        support_customer_id,
                        ecommerce_customer_id,
                        email,
                        shopify_customer_id,
                        notes
                    ) VALUES (
                        :support_id,
                        :ecommerce_id,
                        :email,
                        :shopify_id,
                        :notes
                    )
                """),
                {
                    "support_id": f"shopify_{customer_id}",
                    "ecommerce_id": int(customer_id),
                    "email": email,
                    "shopify_id": int(customer_id),
                    "notes": f"Synced from Shopify - {name} - LTV ${ltv:,.2f}, {orders} orders"
                }
            )
            added += 1

            if added % 100 == 0:
                await session.commit()
                print(f"  Saved {added} mappings...")

        await session.commit()

    print(f"\n✓ Added {added} new email mappings")
    print(f"  Skipped {skipped} (no email or already exists)")


async def main():
    print("=" * 80)
    print("SYNCING SHOPIFY CUSTOMER EMAILS TO DATABASE")
    print("=" * 80)

    # API credentials configured

    print("\n1. Fetching customers from Shopify...")
    customers = await fetch_shopify_customers()
    print(f"   ✓ Fetched {len(customers)} total customers")

    print("\n2. Populating customer_alias table...")
    await populate_customer_alias(customers)

    print("\n" + "=" * 80)
    print("SYNC COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
