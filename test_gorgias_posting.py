#!/usr/bin/env python3
"""
Test Gorgias API posting directly.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, '/Users/scottallen/q.ai-customer-support')

from app.services.gorgias_client import gorgias_client

async def test_posting():
    """Test posting to Gorgias."""

    print("=" * 80)
    print("TESTING GORGIAS API POSTING")
    print("=" * 80)

    # Use the real ticket ID from the test
    ticket_id = 246402461

    print(f"\n1. Testing draft reply posting to ticket {ticket_id}...")
    print("-" * 80)

    test_message = """Hi Lori,

Thank you for reaching out! I can help you check on your batting order from December 11th.

Let me look into this for you and I'll provide an update on the shipping status.

Best regards,
Linda's Electric Quilters"""

    try:
        result = await gorgias_client.post_draft_reply(
            ticket_id=ticket_id,
            body_text=test_message
        )

        if result:
            print(f"✅ SUCCESS! Draft posted to ticket {ticket_id}")
            print(f"\n   Response:")
            import json
            print(json.dumps(result, indent=2))
        else:
            print(f"❌ FAILED - No response from Gorgias API")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_posting())
