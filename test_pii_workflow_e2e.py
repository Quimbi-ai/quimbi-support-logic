#!/usr/bin/env python3
"""
End-to-End PII Hash Workflow Test

Demonstrates the complete workflow for using PII hashing to resolve customer
identities from unstructured data (like Google Groups emails).

Flow:
1. Customer email arrives from Google Groups (no structured from_email)
2. Extract name/email from message body
3. Use PII hash lookup to find existing QuimbiID
4. Load complete customer profile with intelligence
5. Generate personalized AI response using customer data
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.quimbi_id_service import get_complete_customer_profile

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/railway")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def test_google_groups_workflow():
    """
    Simulate processing a Google Groups email with customer PII in body.
    """
    print("=" * 80)
    print("PII Hash Workflow: Google Groups Email Processing")
    print("=" * 80)

    # SCENARIO: Email from Google Groups
    print("\n📧 Incoming Email:")
    print("   From: linda@lindaselectricquilters.com (Google Groups)")
    print("   Subject: Question about order")
    print("   Body: 'Debby Stanford-Miller (debbymiller@centurylink.net) wrote:")
    print("          I ordered 4 pantographs but only received 2...'")

    # STEP 1: Extract PII from message body
    print("\n🔍 Step 1: Extract PII from message body")
    customer_name = "Debby Stanford-Miller"
    customer_email = "debbymiller@centurylink.net"
    print(f"   Extracted name: {customer_name}")
    print(f"   Extracted email: {customer_email}")

    # STEP 2: Lookup customer using PII hash
    print("\n🔐 Step 2: PII Hash Lookup")
    async with AsyncSessionLocal() as db:
        # Use the new PII hash lookup parameters
        profile = await get_complete_customer_profile(
            db,
            email=customer_email,
            name=customer_name
        )

        if not profile:
            print("   ❌ No customer found via PII hash")
            print("   Would create new QuimbiID and customer record")
            return

        print(f"   ✅ Found QuimbiID: {profile['quimbi_id']}")

        # STEP 3: Display customer profile
        print("\n👤 Step 3: Customer Profile Retrieved")
        print(f"   Name: {profile.get('name')}")
        print(f"   Email: {profile.get('email')}")
        print(f"   Customer since: {profile.get('customer_since', 'N/A')}")

        # STEP 4: Display customer intelligence
        intelligence = profile.get('intelligence') or {}
        print("\n🧠 Step 4: Customer Intelligence")
        print(f"   Lifetime Value: ${intelligence.get('lifetime_value', 0):,.2f}")
        print(f"   Total Orders: {intelligence.get('total_orders', 0)}")
        print(f"   Average Order Value: ${intelligence.get('average_order_value', 0):,.2f}")
        print(f"   Days Since Last Purchase: {intelligence.get('days_since_last_purchase', 'N/A')}")

        # Display behavioral segments
        segments = intelligence.get('dominant_segments', {})
        if segments:
            print("\n📊 Behavioral Segments:")
            for segment_type, segment_value in segments.items():
                print(f"   {segment_type}: {segment_value}")

        # Display archetype
        archetype = intelligence.get('archetype', 'Unknown')
        print(f"\n🎭 Customer Archetype: {archetype}")

        # Display recent orders
        recent_orders = profile.get('recent_orders', [])
        if recent_orders:
            print(f"\n📦 Recent Orders ({len(recent_orders)}):")
            for i, order in enumerate(recent_orders[:3], 1):
                print(f"   {i}. Order #{order.get('order_number', 'N/A')}")
                print(f"      Date: {order.get('created_at', 'N/A')}")
                print(f"      Total: ${order.get('total_price', 0):,.2f}")
                products = order.get('products', [])
                if products:
                    print(f"      Products: {', '.join(products[:3])}")

        # STEP 5: Generate personalized response
        print("\n💬 Step 5: AI Response Personalization")
        print("   With this customer intelligence, the AI can:")
        print("   ✅ Address customer by name")
        print(f"   ✅ Acknowledge their {intelligence.get('total_orders', 0)} previous orders")
        print(f"   ✅ Reference their ${intelligence.get('lifetime_value', 0):,.2f} lifetime value")
        if archetype != "Unknown":
            print(f"   ✅ Use {archetype} archetype communication style")
        if segments.get('purchase_frequency') == 'power_buyer':
            print("   ✅ Recognize them as a power buyer (VIP treatment)")

        print("\n📝 Example AI Response:")
        print("   'Hi Debby,")
        print()
        print("   Thank you for reaching out! I can see you're one of our valued")
        print(f"   customers with {intelligence.get('total_orders', 0)} orders over the past")
        print("   few years.")
        print()
        print("   I'm looking into your recent pantograph order right now. Could you")
        print("   please provide your order number so I can track down exactly what")
        print("   happened and ensure we get the missing 2 pantographs to you ASAP?")
        print()
        print("   We appreciate your continued support!'")

    print("\n" + "=" * 80)
    print("✅ PII Hash Workflow Complete!")
    print("=" * 80)


async def test_fallback_scenario():
    """
    Test what happens when PII hash lookup fails (new customer).
    """
    print("\n" + "=" * 80)
    print("PII Hash Workflow: New Customer (No Match)")
    print("=" * 80)

    print("\n📧 Incoming Email:")
    print("   From: linda@lindaselectricquilters.com (Google Groups)")
    print("   Subject: First time buyer question")
    print("   Body: 'Jane Doe (jane.doe@newcustomer.com) wrote:")
    print("          I'm interested in ordering...'")

    print("\n🔍 Step 1: Extract PII from message body")
    customer_name = "Jane Doe"
    customer_email = "jane.doe@newcustomer.com"
    print(f"   Extracted name: {customer_name}")
    print(f"   Extracted email: {customer_email}")

    print("\n🔐 Step 2: PII Hash Lookup")
    async with AsyncSessionLocal() as db:
        profile = await get_complete_customer_profile(
            db,
            email=customer_email,
            name=customer_name
        )

        if not profile:
            print("   ❌ No customer found via PII hash")
            print("\n🆕 Step 3: Create New Customer Flow")
            print("   Would:")
            print("   1. Generate new QuimbiID")
            print("   2. Create identity_graph entries (email_hash, name_hash)")
            print("   3. Create quimbi_identities record")
            print("   4. Return new profile with no intelligence (first-time customer)")
            print("\n💬 Step 4: AI Response (Generic, No Personalization)")
            print("   Since no customer history exists, AI provides standard response")
        else:
            print("   ✅ Unexpectedly found customer!")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_google_groups_workflow())
    asyncio.run(test_fallback_scenario())
