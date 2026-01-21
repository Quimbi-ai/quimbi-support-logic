"""
Sync customer emails ONLY for customers who have made purchases (in combined_sales).
This is much more efficient than syncing all Shopify customers.
"""
import asyncio
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Database configuration
DATABASE_URL = "postgresql+asyncpg://postgres:XzLuopeMhZwurhlOWaObisBJxiTFViCb@turntable.proxy.rlwy.net:30126/railway"

# Shopify API configuration
SHOPIFY_STORE = "lindas-electric-quilters"
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")  # Load from environment
SHOPIFY_API_VERSION = "2024-10"


async def get_customer_ids_from_sales():
    """Get unique customer IDs from combined_sales table."""
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(text("""
            SELECT DISTINCT customer_id
            FROM public.combined_sales
            WHERE customer_id IS NOT NULL
            ORDER BY customer_id
        """))
        rows = result.fetchall()
        customer_ids = [row[0] for row in rows]
        return customer_ids


async def fetch_shopify_customer(customer_id):
    """Fetch a single customer from Shopify API by ID."""
    url = f"https://{SHOPIFY_STORE}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/customers/{customer_id}.json"

    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data.get('customer')
            elif response.status_code == 404:
                # Customer not found in Shopify (might be deleted)
                return None
            else:
                print(f"  ⚠ Error fetching customer {customer_id}: {response.status_code}")
                return None
        except Exception as e:
            print(f"  ⚠ Exception fetching customer {customer_id}: {e}")
            return None


async def populate_customer_alias(customers):
    """Populate customer_alias table with email → Shopify ID mappings."""
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    added = 0
    skipped = 0

    async with async_session() as session:
        for customer in customers:
            if not customer:
                skipped += 1
                continue

            customer_id = str(customer.get('id'))
            email = customer.get('email')
            first_name = customer.get('first_name', '')
            last_name = customer.get('last_name', '')
            name = f"{first_name} {last_name}".strip()

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
                    "notes": f"From combined_sales - {name} - LTV ${ltv:,.2f}, {orders} orders"
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
    print("SYNCING CUSTOMER EMAILS FOR CUSTOMERS WITH PURCHASES")
    print("=" * 80)

    print("\n1. Getting customer IDs from combined_sales...")
    customer_ids = await get_customer_ids_from_sales()
    print(f"   ✓ Found {len(customer_ids)} unique customers with purchases")

    print("\n2. Fetching customer details from Shopify...")
    customers = []
    batch_size = 10  # Fetch in parallel batches

    for i in range(0, len(customer_ids), batch_size):
        batch = customer_ids[i:i + batch_size]
        tasks = [fetch_shopify_customer(cid) for cid in batch]
        batch_customers = await asyncio.gather(*tasks)
        customers.extend([c for c in batch_customers if c])

        if (i + batch_size) % 100 == 0:
            print(f"   Fetched {min(i + batch_size, len(customer_ids))}/{len(customer_ids)} customers...")

    print(f"   ✓ Fetched {len(customers)} customers from Shopify")

    print("\n3. Populating customer_alias table...")
    await populate_customer_alias(customers)

    print("\n" + "=" * 80)
    print("SYNC COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
