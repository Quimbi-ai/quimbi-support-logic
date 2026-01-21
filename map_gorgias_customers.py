"""
Map specific Gorgias customer emails to Shopify customer IDs.
Uses Shopify search API to find customers by email.
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

# Gorgias customer emails to map
GORGIAS_EMAILS = [
    'mrsjulieruch@gmail.com',
    'bdomoe@att.net',
    'amymseibert@gmail.com',
]


async def search_shopify_customer_by_email(email):
    """Search for a customer in Shopify by email address."""
    url = f"https://{SHOPIFY_STORE}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/customers/search.json?query=email:{email}"

    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                customers = data.get('customers', [])
                return customers[0] if customers else None
            else:
                print(f"  ⚠ Error searching for {email}: {response.status_code}")
                return None
        except Exception as e:
            print(f"  ⚠ Exception searching for {email}: {e}")
            return None


async def add_customer_mapping(session, customer, email):
    """Add a customer email → Shopify ID mapping to customer_alias table."""
    customer_id = str(customer.get('id'))
    first_name = customer.get('first_name', '')
    last_name = customer.get('last_name', '')
    name = f"{first_name} {last_name}".strip()

    # Get LTV and order count
    ltv_result = await session.execute(
        text("""
            SELECT lifetime_value, total_orders
            FROM fact_customer_current
            WHERE customer_id = :id
        """),
        {"id": customer_id}
    )
    ltv_row = ltv_result.fetchone()

    ltv = ltv_row[0] if (ltv_row and ltv_row[0]) else 0
    orders = ltv_row[1] if (ltv_row and ltv_row[1]) else 0

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
            "notes": f"Gorgias customer - {name} - LTV ${float(ltv):,.2f}, {int(orders)} orders"
        }
    )


async def main():
    print("=" * 80)
    print("MAPPING GORGIAS CUSTOMER EMAILS TO SHOPIFY")
    print("=" * 80)

    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    mapped = 0
    not_found = 0

    async with async_session() as session:
        for email in GORGIAS_EMAILS:
            print(f"\nSearching for: {email}")

            customer = await search_shopify_customer_by_email(email)

            if customer:
                customer_id = customer.get('id')
                name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
                print(f"  ✓ FOUND: Shopify ID {customer_id} - {name}")

                await add_customer_mapping(session, customer, email)
                mapped += 1
                print(f"  ✓ Mapped to customer_alias table")
            else:
                print(f"  ✗ NOT FOUND in Shopify")
                not_found += 1

        await session.commit()

    print("\n" + "=" * 80)
    print(f"✓ Mapped {mapped} customers")
    print(f"✗ Not found: {not_found} customers")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
