#!/usr/bin/env python3
"""
Direct test of Shopify fulfillment service to see what data we're getting.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, '/Users/scottallen/q.ai-customer-support')

from app.integrations.shopify_fulfillment_service import get_fulfillment_service
from app.integrations.ticket_fulfillment_enricher import (
    enrich_ticket_with_fulfillments,
    format_fulfillment_summary_for_ai,
    format_fulfillment_for_internal_note
)
import json

async def test_order_fulfillment():
    """Test fetching fulfillment for a specific order."""

    print("=" * 80)
    print("TESTING SHOPIFY FULFILLMENT SERVICE")
    print("=" * 80)

    # Test with order #1001 from the webhook test
    order_number = 1001

    print(f"\n1. Testing order #{order_number}...")
    print("-" * 80)

    try:
        # Get fulfillment service
        service = get_fulfillment_service()
        print(f"✅ Fulfillment service initialized")
        print(f"   Shop: {service.shop_name}")
        print(f"   API Version: {service.api_version}")

        # Fetch order data
        print(f"\n2. Fetching order #{order_number} from Shopify...")
        order_data = await service.get_order_by_number(order_number)

        if order_data:
            print(f"✅ Order found!")
            print(f"\n   Order Details:")
            print(f"   - Shopify ID: {order_data.get('id')}")
            print(f"   - Order Number: #{order_data.get('order_number')}")
            print(f"   - Fulfillments: {len(order_data.get('fulfillments', []))} shipment(s)")

            # Show fulfillment details
            fulfillments = order_data.get('fulfillments', [])
            for i, f in enumerate(fulfillments, 1):
                print(f"\n   Shipment {i}:")
                print(f"   - Status: {f.get('status')}")
                print(f"   - Tracking: {f.get('tracking_number', 'N/A')}")
                print(f"   - Carrier: {f.get('tracking_company', 'N/A')}")
                print(f"   - Location: {f.get('location_id', 'N/A')}")
                print(f"   - Items: {len(f.get('line_items', []))} item(s)")
        else:
            print(f"⚠️  Order #{order_number} not found in Shopify")
            return

        # Test enrichment
        print(f"\n3. Testing ticket enrichment...")
        print("-" * 80)

        ticket_data = {
            "id": 12345,
            "subject": f"Question about order #{order_number}",
            "messages": [{
                "body_text": f"Where is my order #{order_number}?"
            }]
        }

        enriched = await enrich_ticket_with_fulfillments(
            ticket_data=ticket_data,
            order_number=order_number
        )

        if enriched:
            print(f"✅ Enrichment successful!")
            print(f"\n   Enriched Data:")
            print(f"   - Order #: {enriched.get('order_number')}")
            print(f"   - Shipments: {len(enriched.get('fulfillments', []))}")
            print(f"   - Split Shipment: {enriched.get('has_split_shipment')}")
            print(f"   - Fulfillment Status: {enriched.get('fulfillment_status')}")

            # Test AI formatting
            print(f"\n4. Testing AI context formatting...")
            print("-" * 80)
            ai_context = format_fulfillment_summary_for_ai(enriched)
            print(f"\n{ai_context}")

            # Test internal note formatting (if split shipment)
            if enriched.get('has_split_shipment'):
                print(f"\n5. Testing internal note formatting...")
                print("-" * 80)
                note = format_fulfillment_for_internal_note(enriched)
                print(f"\n{note}")
        else:
            print(f"⚠️  Enrichment returned no data")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_order_fulfillment())
