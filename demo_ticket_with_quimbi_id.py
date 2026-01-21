"""
Ticket Demo with QuimbiID Integration

This demo shows how QuimbiID links customer intelligence, purchase history,
and order tracking across the entire support system.
"""

import asyncio
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:XzLuopeMhZwurhlOWaObisBJxiTFViCb@turntable.proxy.rlwy.net:30126/railway"


async def get_customer_by_quimbi_id(session, quimbi_id):
    """Get complete customer profile using QuimbiID"""

    # Get QuimbiID details
    result = await session.execute(
        text("""
            SELECT quimbi_id, primary_email, primary_name, created_at
            FROM public.quimbi_identities
            WHERE quimbi_id = :qid AND is_active = TRUE
        """),
        {"qid": quimbi_id}
    )
    identity = result.fetchone()

    if not identity:
        return None

    # Get all linked identifiers
    result = await session.execute(
        text("""
            SELECT id_type, id_value, source, confidence_score, verified
            FROM public.identity_graph
            WHERE quimbi_id = :qid
            ORDER BY id_type
        """),
        {"qid": quimbi_id}
    )
    identifiers = result.fetchall()

    # Get Shopify IDs
    shopify_ids = [str(row[1]) for row in identifiers if row[0] == 'shopify']

    customer_data = {
        "quimbi_id": identity[0],
        "email": identity[1],
        "name": identity[2],
        "identifiers": [
            {
                "type": row[0],
                "value": row[1],
                "source": row[2],
                "confidence": float(row[3]),
                "verified": row[4]
            } for row in identifiers
        ],
        "intelligence": None,
        "recent_orders": []
    }

    # Get customer intelligence
    if shopify_ids:
        result = await session.execute(
            text("""
                SELECT customer_id, lifetime_value, total_orders, churn_risk_score,
                       avg_order_value, days_since_last_order, predicted_next_purchase_days
                FROM platform.customer_profiles
                WHERE customer_id = :sid
            """),
            {"sid": shopify_ids[0]}
        )
        intel = result.fetchone()

        if intel:
            customer_data["intelligence"] = {
                "lifetime_value": float(intel[1]) if intel[1] else 0.0,
                "total_orders": int(intel[2]) if intel[2] else 0,
                "churn_risk_score": float(intel[3]) if intel[3] else 0.0,
                "avg_order_value": float(intel[4]) if intel[4] else 0.0,
                "days_since_last_order": int(intel[5]) if intel[5] else 0,
                "predicted_next_purchase_days": int(intel[6]) if intel[6] else 0
            }

        # Get recent orders
        result = await session.execute(
            text("""
                SELECT DISTINCT
                    order_id,
                    order_number,
                    order_date,
                    order_total,
                    financial_status,
                    fulfillment_status
                FROM public.combined_sales
                WHERE customer_id = ANY(:ids)
                ORDER BY order_date DESC
                LIMIT 5
            """),
            {"ids": [int(sid) for sid in shopify_ids]}
        )

        customer_data["recent_orders"] = [
            {
                "order_id": row[0],
                "order_number": row[1],
                "order_date": row[2].strftime("%Y-%m-%d") if row[2] else None,
                "total": float(row[3]) if row[3] else 0.0,
                "financial_status": row[4],
                "fulfillment_status": row[5]
            } for row in result.fetchall()
        ]

    return customer_data


async def get_ticket_with_context(session, ticket_id):
    """Get ticket with full QuimbiID-linked context"""

    # Get ticket details
    result = await session.execute(
        text("""
            SELECT t.id, t.customer_id, t.subject, t.status, t.priority,
                   t.channel, t.created_at, t.updated_at
            FROM public.tickets t
            WHERE t.id = :tid
        """),
        {"tid": ticket_id}
    )
    ticket = result.fetchone()

    if not ticket:
        return None

    ticket_data = {
        "id": ticket[0],
        "customer_id": ticket[1],
        "subject": ticket[2],
        "status": ticket[3],
        "priority": ticket[4],
        "channel": ticket[5],
        "created_at": ticket[6].strftime("%Y-%m-%d %H:%M:%S") if ticket[6] else None,
        "updated_at": ticket[7].strftime("%Y-%m-%d %H:%M:%S") if ticket[7] else None,
        "customer": None,
        "messages": [],
        "tracking_info": []
    }

    # Find QuimbiID for this customer
    customer_id_str = str(ticket[1])
    result = await session.execute(
        text("""
            SELECT quimbi_id FROM public.identity_graph
            WHERE id_value = :cid
            LIMIT 1
        """),
        {"cid": customer_id_str}
    )
    quimbi_match = result.fetchone()

    if quimbi_match:
        quimbi_id = quimbi_match[0]
        customer_data = await get_customer_by_quimbi_id(session, quimbi_id)
        ticket_data["customer"] = customer_data

    # Get first message only (no responses)
    result = await session.execute(
        text("""
            SELECT id, content, from_agent, from_email, created_at
            FROM public.messages
            WHERE ticket_id = :tid
            ORDER BY created_at ASC
            LIMIT 1
        """),
        {"tid": ticket_id}
    )
    first_msg = result.fetchone()

    if first_msg:
        ticket_data["messages"] = [{
            "id": first_msg[0],
            "content": first_msg[1],
            "from_agent": first_msg[2],
            "from_email": first_msg[3],
            "created_at": first_msg[4].strftime("%Y-%m-%d %H:%M:%S") if first_msg[4] else None
        }]

    # Get tracking information for recent orders
    if ticket_data["customer"] and ticket_data["customer"]["recent_orders"]:
        for order in ticket_data["customer"]["recent_orders"][:3]:  # Just first 3
            result = await session.execute(
                text("""
                    SELECT tracking_number, tracking_company, tracking_url, shipped_date
                    FROM public.order_fulfillments
                    WHERE order_id = :oid
                """),
                {"oid": order["order_id"]}
            )
            tracking = result.fetchall()

            for track in tracking:
                ticket_data["tracking_info"].append({
                    "order_number": order["order_number"],
                    "tracking_number": track[0],
                    "carrier": track[1],
                    "tracking_url": track[2],
                    "shipped_date": track[3].strftime("%Y-%m-%d") if track[3] else None
                })

    return ticket_data


async def display_ticket_demo(ticket_id):
    """Display comprehensive ticket demo"""

    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        ticket_data = await get_ticket_with_context(session, ticket_id)

        if not ticket_data:
            print(f"❌ Ticket {ticket_id} not found")
            return

        print("=" * 100)
        print(f"SUPPORT TICKET DEMO - QuimbiID Integration")
        print("=" * 100)

        # Ticket Info
        print(f"\n📋 TICKET INFORMATION")
        print(f"{'─' * 100}")
        print(f"  Ticket ID:      {ticket_data['id']}")
        print(f"  Subject:        {ticket_data['subject']}")
        print(f"  Status:         {ticket_data['status'].upper()}")
        print(f"  Priority:       {ticket_data['priority'].upper()}")
        print(f"  Channel:        {ticket_data['channel'].upper()}")
        print(f"  Created:        {ticket_data['created_at']}")

        # Customer Identity
        if ticket_data['customer']:
            cust = ticket_data['customer']
            print(f"\n👤 CUSTOMER IDENTITY (QuimbiID System)")
            print(f"{'─' * 100}")
            print(f"  QuimbiID:       {cust['quimbi_id']}")
            print(f"  Name:           {cust['name']}")
            print(f"  Email:          {cust['email']}")

            print(f"\n  Linked Identifiers:")
            for ident in cust['identifiers']:
                verified = "✓" if ident['verified'] else "?"
                print(f"    [{verified}] {ident['type']:<12} {ident['value']:<30} (confidence: {ident['confidence']:.2f})")

            # Customer Intelligence
            if cust['intelligence']:
                intel = cust['intelligence']
                print(f"\n💡 CUSTOMER INTELLIGENCE")
                print(f"{'─' * 100}")
                print(f"  Lifetime Value:           ${intel['lifetime_value']:,.2f}")
                print(f"  Total Orders:             {intel['total_orders']}")
                print(f"  Average Order Value:      ${intel['avg_order_value']:,.2f}")
                print(f"  Days Since Last Order:    {intel['days_since_last_order']} days")
                print(f"  Churn Risk Score:         {intel['churn_risk_score']:.2f}")
                if intel['predicted_next_purchase_days']:
                    print(f"  Predicted Next Purchase:  {intel['predicted_next_purchase_days']} days")

            # Recent Orders
            if cust['recent_orders']:
                print(f"\n🛍️  RECENT PURCHASE HISTORY")
                print(f"{'─' * 100}")
                for idx, order in enumerate(cust['recent_orders'], 1):
                    print(f"  Order #{order['order_number']}:")
                    print(f"    Date:              {order['order_date']}")
                    print(f"    Total:             ${order['total']:,.2f}")
                    print(f"    Payment Status:    {order['financial_status']}")
                    print(f"    Fulfillment:       {order['fulfillment_status']}")
                    if idx < len(cust['recent_orders']):
                        print()

        # Tracking Information
        if ticket_data['tracking_info']:
            print(f"\n📦 ORDER TRACKING")
            print(f"{'─' * 100}")
            for track in ticket_data['tracking_info']:
                print(f"  Order #{track['order_number']}:")
                print(f"    Carrier:           {track['carrier']}")
                print(f"    Tracking Number:   {track['tracking_number']}")
                print(f"    Shipped Date:      {track['shipped_date']}")
                if track['tracking_url']:
                    print(f"    Tracking URL:      {track['tracking_url']}")
                print()

        # Original Message
        if ticket_data['messages']:
            msg = ticket_data['messages'][0]
            print(f"\n💬 CUSTOMER MESSAGE")
            print(f"{'─' * 100}")
            print(f"  From:      {msg['from_email']}")
            print(f"  Sent:      {msg['created_at']}")
            print(f"\n  Message:")
            print(f"  {msg['content'][:500]}...")

        # AI Context Summary
        print(f"\n🤖 AI ASSISTANT CONTEXT")
        print(f"{'─' * 100}")
        if ticket_data['customer'] and ticket_data['customer']['intelligence']:
            intel = ticket_data['customer']['intelligence']
            cust = ticket_data['customer']

            print(f"  Using QuimbiID: {cust['quimbi_id']}")
            print(f"\n  KNOWN CUSTOMER DATA:")
            print(f"    • High-value customer: ${intel['lifetime_value']:,.2f} LTV across {intel['total_orders']} orders")
            print(f"    • Average spend per order: ${intel['avg_order_value']:,.2f}")
            print(f"    • Last purchase: {intel['days_since_last_order']} days ago")
            if intel['churn_risk_score'] > 0.5:
                print(f"    • ⚠️  ELEVATED CHURN RISK: {intel['churn_risk_score']:.2%}")

            if cust['recent_orders']:
                print(f"\n  RECENT ORDERS:")
                for order in cust['recent_orders'][:3]:
                    print(f"    • Order #{order['order_number']}: ${order['total']:.2f} on {order['order_date']} ({order['fulfillment_status']})")

            if ticket_data['tracking_info']:
                print(f"\n  TRACKING AVAILABLE:")
                for track in ticket_data['tracking_info']:
                    print(f"    • Order #{track['order_number']}: {track['carrier']} - {track['tracking_number']}")

            print(f"\n  AI SHOULD:")
            print(f"    ✓ Reference specific order numbers and tracking information")
            print(f"    ✓ Acknowledge customer loyalty ({intel['total_orders']} previous orders)")
            print(f"    ✓ Use [PLACEHOLDER] for any unknown information")
            print(f"    ✓ Offer VIP-level service due to high LTV")

        print(f"\n{'=' * 100}\n")


async def main():
    """Run ticket demos"""

    # Find a good demo ticket
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Find a Gorgias ticket with a high-value customer
        result = await session.execute(text("""
            SELECT t.id, t.subject
            FROM public.tickets t
            WHERE t.id LIKE 'gorgias_%'
            LIMIT 1
        """))
        ticket = result.fetchone()

        if ticket:
            print(f"\nDemonstrating ticket: {ticket[0]}")
            print(f"Subject: {ticket[1]}\n")
            await display_ticket_demo(ticket[0])
        else:
            print("No Gorgias tickets found for demo")


if __name__ == "__main__":
    asyncio.run(main())
