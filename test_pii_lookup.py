#!/usr/bin/env python3
"""
Test PII Hash Lookup

Tests the find_quimbi_id_by_pii_hash() function to ensure it can find
customers by email and name hashes.
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.quimbi_id_service import find_quimbi_id_by_pii_hash

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/railway")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def test_pii_lookup():
    """Test PII hash lookup with known customer data."""
    async with AsyncSessionLocal() as db:
        print("Testing PII Hash Lookup Function")
        print("=" * 80)

        # Test 1: Find customer by email (case insensitive)
        print("\n1. Testing email lookup (case insensitive)...")
        email_test = "debbymiller@centurylink.net"
        result = await find_quimbi_id_by_pii_hash(db, email=email_test)
        if result:
            print(f"   ✅ Found QuimbiID via email '{email_test}': {result}")
        else:
            print(f"   ❌ No QuimbiID found for email '{email_test}'")

        # Test 2: Find customer by email with different case
        print("\n2. Testing email lookup (different case)...")
        email_test_upper = "DEBBYMILLER@CENTURYLINK.NET"
        result2 = await find_quimbi_id_by_pii_hash(db, email=email_test_upper)
        if result2:
            print(f"   ✅ Found QuimbiID via email '{email_test_upper}': {result2}")
            if result == result2:
                print(f"   ✅ Same QuimbiID as lowercase test - normalization working!")
        else:
            print(f"   ❌ No QuimbiID found for email '{email_test_upper}'")

        # Test 3: Find customer by name
        print("\n3. Testing name lookup...")
        name_test = "Debby Stanford-Miller"
        result3 = await find_quimbi_id_by_pii_hash(db, name=name_test)
        if result3:
            print(f"   ✅ Found QuimbiID via name '{name_test}': {result3}")
            if result == result3:
                print(f"   ✅ Same QuimbiID as email test - correct customer!")
        else:
            print(f"   ❌ No QuimbiID found for name '{name_test}'")

        # Test 4: Find customer by name with different punctuation
        print("\n4. Testing name lookup (different format)...")
        name_test_alt = "debby stanford miller"
        result4 = await find_quimbi_id_by_pii_hash(db, name=name_test_alt)
        if result4:
            print(f"   ✅ Found QuimbiID via name '{name_test_alt}': {result4}")
            if result == result4:
                print(f"   ✅ Same QuimbiID - name normalization working!")
        else:
            print(f"   ❌ No QuimbiID found for name '{name_test_alt}'")

        # Test 5: Combined lookup (email + name)
        print("\n5. Testing combined lookup (email + name)...")
        result5 = await find_quimbi_id_by_pii_hash(
            db,
            email=email_test,
            name=name_test
        )
        if result5:
            print(f"   ✅ Found QuimbiID: {result5}")
            print(f"   Email match takes precedence (most reliable)")
        else:
            print(f"   ❌ No QuimbiID found")

        # Test 6: Non-existent customer
        print("\n6. Testing with non-existent customer...")
        result6 = await find_quimbi_id_by_pii_hash(
            db,
            email="fake@notreal.com",
            name="Fake Person"
        )
        if result6:
            print(f"   ❌ ERROR: Found QuimbiID {result6} for fake customer!")
        else:
            print(f"   ✅ Correctly returned None for non-existent customer")

        print("\n" + "=" * 80)
        print("PII Hash Lookup Tests Complete!")


if __name__ == "__main__":
    asyncio.run(test_pii_lookup())
